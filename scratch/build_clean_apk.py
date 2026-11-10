import os
import struct
import hashlib
import base64
import datetime
import io
import zlib

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7

KEY_FILE = "apk/vr_private_key.pem"
CERT_FILE = "apk/vr_cert.pem"

def get_or_create_key_and_cert():
    if os.path.exists(KEY_FILE) and os.path.exists(CERT_FILE):
        print(f"Loading existing key and cert from {KEY_FILE} and {CERT_FILE}...")
        with open(KEY_FILE, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)
        with open(CERT_FILE, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        return key, cert

    print("Generating new RSA-2048 key and self-signed certificate...")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"VarantRadar Pro"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"VarantRadar Pro"),
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"TR"),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        now - datetime.timedelta(days=1)
    ).not_valid_after(
        now + datetime.timedelta(days=10000)
    ).sign(key, hashes.SHA256())

    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    with open(KEY_FILE, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    with open(CERT_FILE, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    return key, cert

def build_apk():
    key, cert = get_or_create_key_and_cert()

    # Read base files
    with open("scratch/apk_source/AndroidManifest.xml", "rb") as f:
        manifest_xml = f.read()
    with open("scratch/apk_source/resources.arsc", "rb") as f:
        resources_arsc = f.read()
    with open("scratch/apk_source/ic_launcher.png", "rb") as f:
        icon_png = f.read()
    with open("scratch/classes_patched.dex", "rb") as f:
        classes_dex = f.read()

    # File definitions: (name, data, compress_type)
    # resources.arsc MUST BE STORED (uncompressed) for Android AssetManager!
    # classes.dex and AndroidManifest.xml and png are compressed with DEFLATE (or STORED)
    app_files = [
        ("AndroidManifest.xml", manifest_xml, 8),
        ("classes.dex", classes_dex, 8),
        ("res/mipmap/ic_launcher.png", icon_png, 8),
        ("resources.arsc", resources_arsc, 0), # CRITICAL: MUST BE 0 (STORED)
    ]

    # Sort app files alphabetically
    app_files.sort(key=lambda x: x[0])

    # 1. Generate META-INF/MANIFEST.MF
    mf_lines = [b"Manifest-Version: 1.0\r\nCreated-By: 1.0 (Android)\r\n\r\n"]
    sec_map = {}
    for name, data, _ in app_files:
        h = hashlib.sha256(data).digest()
        b64 = base64.b64encode(h).decode("ascii")
        # In JAR spec, the section ends with \r\n\r\n
        # The section to hash for .SF is the section without the final extra \r\n (or exact section bytes)
        sec_header = f"Name: {name}\r\nSHA-256-Digest: {b64}\r\n".encode("utf-8")
        sec_full = sec_header + b"\r\n"
        mf_lines.append(sec_full)
        sec_map[name] = sec_header

    manifest_mf = b"".join(mf_lines)

    # 2. Generate META-INF/VARANTRA.SF
    # NO X-Android-APK-Signed: 2 (avoids Android looking for non-existent or broken v2 blocks)
    mf_digest = base64.b64encode(hashlib.sha256(manifest_mf).digest()).decode("ascii")
    sf_lines = [
        b"Signature-Version: 1.0\r\n",
        b"Created-By: 1.0 (Android)\r\n",
        f"SHA-256-Digest-Manifest: {mf_digest}\r\n\r\n".encode("utf-8"),
    ]
    for name, data, _ in app_files:
        sec_header = sec_map[name]
        sec_digest = base64.b64encode(hashlib.sha256(sec_header).digest()).decode("ascii")
        sf_lines.append(f"Name: {name}\r\nSHA-256-Digest: {sec_digest}\r\n\r\n".encode("utf-8"))

    varantra_sf = b"".join(sf_lines)

    # 3. Generate META-INF/VARANTRA.RSA (PKCS#7 signature)
    builder = pkcs7.PKCS7SignatureBuilder().set_data(varantra_sf).add_signer(
        cert, key, hashes.SHA256()
    )
    varantra_rsa = builder.sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature])

    all_files = list(app_files)
    # Add META-INF files (can be deflated or stored)
    all_files.append(("META-INF/MANIFEST.MF", manifest_mf, 8))
    all_files.append(("META-INF/VARANTRA.SF", varantra_sf, 8))
    all_files.append(("META-INF/VARANTRA.RSA", varantra_rsa, 8))

    # 4. Write aligned ZIP file manually to ensure EXACT 4-byte alignment
    # Standard ZIP format:
    # Local File Header:
    #   0..3: magic 0x04034b50
    #   4..5: version needed (20 = 2.0 for deflate, 10 for stored)
    #   6..7: general flags (0)
    #   8..9: compression method (0 or 8)
    #   10..13: mod time/date
    #   14..17: crc32
    #   18..21: compressed size
    #   22..25: uncompressed size
    #   26..27: filename length
    #   28..29: extra field length
    #   30..: filename
    #   extra field (padding)
    #   payload
    
    zip_out = bytearray()
    cd_entries = []
    fixed_time = 0x5546 # DOS time
    fixed_date = 0x5d66 # DOS date: 2026-11-06

    for name, raw_data, method in all_files:
        crc = zlib.crc32(raw_data) & 0xffffffff
        uncomp_size = len(raw_data)
        if method == 8:
            # Deflate raw (no zlib header, wbits=-15)
            cobj = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=-15)
            comp_data = cobj.compress(raw_data) + cobj.flush()
            comp_size = len(comp_data)
        else:
            comp_data = raw_data
            comp_size = uncomp_size

        name_bytes = name.encode("utf-8")
        current_offset = len(zip_out)

        # Calculate padding needed for 4-byte alignment of payload:
        # payload_offset = current_offset + 30 + len(name_bytes) + extra_len
        base_header_len = 30 + len(name_bytes)
        if method == 0:
            # Must be 4-byte aligned!
            payload_without_extra = current_offset + base_header_len
            pad = (4 - (payload_without_extra % 4)) % 4
        else:
            pad = 0

        extra_bytes = b"\x00" * pad
        extra_len = len(extra_bytes)

        # Write Local File Header
        lfh = bytearray(30)
        struct.pack_into("<I", lfh, 0, 0x04034b50)
        struct.pack_into("<H", lfh, 4, 20) # version
        struct.pack_into("<H", lfh, 6, 0)  # flags
        struct.pack_into("<H", lfh, 8, method)
        struct.pack_into("<H", lfh, 10, fixed_time)
        struct.pack_into("<H", lfh, 12, fixed_date)
        struct.pack_into("<I", lfh, 14, crc)
        struct.pack_into("<I", lfh, 18, comp_size)
        struct.pack_into("<I", lfh, 22, uncomp_size)
        struct.pack_into("<H", lfh, 26, len(name_bytes))
        struct.pack_into("<H", lfh, 28, extra_len)

        zip_out.extend(lfh)
        zip_out.extend(name_bytes)
        zip_out.extend(extra_bytes)

        # Verify alignment of payload
        actual_payload_offset = len(zip_out)
        if method == 0:
            assert actual_payload_offset % 4 == 0, f"Payload for {name} not 4-byte aligned: {actual_payload_offset}"

        zip_out.extend(comp_data)

        # Save CD entry info
        cd_entries.append({
            "name_bytes": name_bytes,
            "method": method,
            "crc": crc,
            "comp_size": comp_size,
            "uncomp_size": uncomp_size,
            "offset": current_offset,
        })

    # Central Directory
    cd_start_offset = len(zip_out)
    cd_bytes = bytearray()
    for entry in cd_entries:
        cdh = bytearray(46)
        struct.pack_into("<I", cdh, 0, 0x02014b50)
        struct.pack_into("<H", cdh, 4, 20) # version made by
        struct.pack_into("<H", cdh, 6, 20) # version needed
        struct.pack_into("<H", cdh, 8, 0)  # flags
        struct.pack_into("<H", cdh, 10, entry["method"])
        struct.pack_into("<H", cdh, 12, fixed_time)
        struct.pack_into("<H", cdh, 14, fixed_date)
        struct.pack_into("<I", cdh, 16, entry["crc"])
        struct.pack_into("<I", cdh, 20, entry["comp_size"])
        struct.pack_into("<I", cdh, 24, entry["uncomp_size"])
        struct.pack_into("<H", cdh, 28, len(entry["name_bytes"]))
        struct.pack_into("<H", cdh, 30, 0) # extra len in CD is 0
        struct.pack_into("<H", cdh, 32, 0) # comment len
        struct.pack_into("<H", cdh, 34, 0) # disk start
        struct.pack_into("<H", cdh, 36, 0) # internal attr
        struct.pack_into("<I", cdh, 38, 0) # external attr
        struct.pack_into("<I", cdh, 42, entry["offset"]) # local header offset

        cd_bytes.extend(cdh)
        cd_bytes.extend(entry["name_bytes"])

    zip_out.extend(cd_bytes)
    cd_size = len(cd_bytes)

    # End of Central Directory (EOCD)
    eocd = bytearray(22)
    struct.pack_into("<I", eocd, 0, 0x06054b50)
    struct.pack_into("<H", eocd, 4, 0) # disk num
    struct.pack_into("<H", eocd, 6, 0) # cd start disk
    struct.pack_into("<H", eocd, 8, len(cd_entries)) # entries on this disk
    struct.pack_into("<H", eocd, 10, len(cd_entries)) # total entries
    struct.pack_into("<I", eocd, 12, cd_size)
    struct.pack_into("<I", eocd, 16, cd_start_offset)
    struct.pack_into("<H", eocd, 20, 0) # comment len

    zip_out.extend(eocd)
    final_apk = bytes(zip_out)
    print(f"Built clean aligned APK: {len(final_apk)} bytes")

    # Verify with zipfile
    import zipfile
    test_z = zipfile.ZipFile(io.BytesIO(final_apk), "r")
    assert test_z.testzip() is None, "ZIP verification failed"
    for info in test_z.infolist():
        print(f"  {info.filename:30} method={info.compress_type} size={info.file_size:8} comp={info.compress_size:8}")

    for p in ["apk/VarantRadarPro.apk", "ui/apk/VarantRadarPro.apk"]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(final_apk)
        print(f"Successfully wrote {p}")

if __name__ == "__main__":
    build_apk()

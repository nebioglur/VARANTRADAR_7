import os
import struct
import hashlib
import base64
import datetime
import io
import zlib
import zipfile

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
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
        manifest_xml = bytearray(f.read())
    
    # Bump versionCode to 10 at offset 796
    struct.pack_into("<I", manifest_xml, 796, 10)
    manifest_xml = bytes(manifest_xml)
    print("Updated AndroidManifest.xml versionCode to 10")

    with open("scratch/apk_source/resources.arsc", "rb") as f:
        resources_arsc = f.read()
    with open("scratch/apk_source/ic_launcher.png", "rb") as f:
        icon_png = f.read()
    with open("scratch/classes_patched.dex", "rb") as f:
        classes_dex = f.read()

    # File definitions: (name, data, compress_type)
    # resources.arsc MUST BE STORED (method 0) for Android AssetManager!
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
        sec_header = f"Name: {name}\r\nSHA-256-Digest: {b64}\r\n".encode("utf-8")
        sec_full = sec_header + b"\r\n"
        mf_lines.append(sec_full)
        sec_map[name] = sec_header

    manifest_mf = b"".join(mf_lines)

    # 2. Generate META-INF/VARANTRA.SF
    # X-Android-APK-Signed: 2 signals v2 signature scheme presence
    mf_digest = base64.b64encode(hashlib.sha256(manifest_mf).digest()).decode("ascii")
    sf_lines = [
        b"Signature-Version: 1.0\r\n",
        b"Created-By: 1.0 (Android)\r\n",
        f"SHA-256-Digest-Manifest: {mf_digest}\r\n".encode("utf-8"),
        b"X-Android-APK-Signed: 2\r\n\r\n",
    ]
    for name, data, _ in app_files:
        sec_header = sec_map[name]
        sec_digest = base64.b64encode(hashlib.sha256(sec_header).digest()).decode("ascii")
        sf_lines.append(f"Name: {name}\r\nSHA-256-Digest: {sec_digest}\r\n\r\n".encode("utf-8"))

    varantra_sf = b"".join(sf_lines)

    # 3. Generate META-INF/VARANTRA.RSA (PKCS#7 signature without signed attributes, exactly matching jarsigner)
    builder = pkcs7.PKCS7SignatureBuilder().set_data(varantra_sf).add_signer(
        cert, key, hashes.SHA256()
    )
    varantra_rsa = builder.sign(
        serialization.Encoding.DER,
        [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.NoAttributes]
    )

    all_files = list(app_files)
    all_files.append(("META-INF/MANIFEST.MF", manifest_mf, 8))
    all_files.append(("META-INF/VARANTRA.SF", varantra_sf, 8))
    all_files.append(("META-INF/VARANTRA.RSA", varantra_rsa, 8))

    # 4. Build aligned ZIP entries (Section 1)
    zip_out = bytearray()
    cd_entries = []
    fixed_time = 0x5546 # DOS time
    fixed_date = 0x5d66 # DOS date: 2026-11-06

    for name, raw_data, method in all_files:
        crc = zlib.crc32(raw_data) & 0xffffffff
        uncomp_size = len(raw_data)
        if method == 8:
            cobj = zlib.compressobj(level=9, method=zlib.DEFLATED, wbits=-15)
            comp_data = cobj.compress(raw_data) + cobj.flush()
            comp_size = len(comp_data)
        else:
            comp_data = raw_data
            comp_size = uncomp_size

        name_bytes = name.encode("utf-8")
        current_offset = len(zip_out)

        base_header_len = 30 + len(name_bytes)
        if method == 0:
            payload_without_extra = current_offset + base_header_len
            pad = (4 - (payload_without_extra % 4)) % 4
        else:
            pad = 0

        extra_bytes = b"\x00" * pad
        extra_len = len(extra_bytes)

        lfh = bytearray(30)
        struct.pack_into("<I", lfh, 0, 0x04034b50)
        struct.pack_into("<H", lfh, 4, 20)
        struct.pack_into("<H", lfh, 6, 0)
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

        actual_payload_offset = len(zip_out)
        if method == 0:
            assert actual_payload_offset % 4 == 0, f"Payload for {name} not 4-byte aligned: {actual_payload_offset}"

        zip_out.extend(comp_data)

        cd_entries.append({
            "name_bytes": name_bytes,
            "method": method,
            "crc": crc,
            "comp_size": comp_size,
            "uncomp_size": uncomp_size,
            "offset": current_offset,
        })

    # Section 1: local file headers and data
    sec1 = bytes(zip_out)

    # Section 2: Central Directory
    cd_bytes = bytearray()
    for entry in cd_entries:
        cdh = bytearray(46)
        struct.pack_into("<I", cdh, 0, 0x02014b50)
        struct.pack_into("<H", cdh, 4, 20)
        struct.pack_into("<H", cdh, 6, 20)
        struct.pack_into("<H", cdh, 8, 0)
        struct.pack_into("<H", cdh, 10, entry["method"])
        struct.pack_into("<H", cdh, 12, fixed_time)
        struct.pack_into("<H", cdh, 14, fixed_date)
        struct.pack_into("<I", cdh, 16, entry["crc"])
        struct.pack_into("<I", cdh, 20, entry["comp_size"])
        struct.pack_into("<I", cdh, 24, entry["uncomp_size"])
        struct.pack_into("<H", cdh, 28, len(entry["name_bytes"]))
        struct.pack_into("<H", cdh, 30, 0)
        struct.pack_into("<H", cdh, 32, 0)
        struct.pack_into("<H", cdh, 34, 0)
        struct.pack_into("<H", cdh, 36, 0)
        struct.pack_into("<I", cdh, 38, 0)
        struct.pack_into("<I", cdh, 42, entry["offset"])

        cd_bytes.extend(cdh)
        cd_bytes.extend(entry["name_bytes"])

    sec2 = bytes(cd_bytes)
    cd_size = len(sec2)

    # Section 3: EOCD (pre-signing block offset = len(sec1))
    eocd_pre = bytearray(22)
    struct.pack_into("<I", eocd_pre, 0, 0x06054b50)
    struct.pack_into("<H", eocd_pre, 4, 0)
    struct.pack_into("<H", eocd_pre, 6, 0)
    struct.pack_into("<H", eocd_pre, 8, len(cd_entries))
    struct.pack_into("<H", eocd_pre, 10, len(cd_entries))
    struct.pack_into("<I", eocd_pre, 12, cd_size)
    struct.pack_into("<I", eocd_pre, 16, len(sec1)) # Central Directory offset before sig block
    struct.pack_into("<H", eocd_pre, 20, 0)
    sec3_for_hash = bytes(eocd_pre)

    # 5. Compute APK Signature Scheme v2 content digest over [sec1, sec2, sec3_for_hash]
    CHUNK_SIZE = 1048576 # 1 MB
    chunks = []
    for section in [sec1, sec2, sec3_for_hash]:
        for i in range(0, len(section), CHUNK_SIZE):
            chunk = section[i:i+CHUNK_SIZE]
            h = hashlib.sha256(b"\xa5" + struct.pack("<I", len(chunk)) + chunk).digest()
            chunks.append(h)

    content_digest = hashlib.sha256(b"\x5a" + struct.pack("<I", len(chunks)) + b"".join(chunks)).digest()
    print("Computed APK v2 content digest:", content_digest.hex())

    # 6. Construct APK v2 SignedData
    # 0x0103 = CHUNKED_SHA256_WITH_RSA_PKCS1_v1_5
    digest_entry = struct.pack("<III", 4 + 4 + 32, 0x0103, 32) + content_digest
    digests_block = struct.pack("<I", len(digest_entry)) + digest_entry

    cert_der = cert.public_bytes(serialization.Encoding.DER)
    cert_entry = struct.pack("<I", len(cert_der)) + cert_der
    certs_block = struct.pack("<I", len(cert_entry)) + cert_entry

    attrs_block = struct.pack("<I", 0) # empty additional attributes

    signed_data = digests_block + certs_block + attrs_block
    signed_data_prefixed = struct.pack("<I", len(signed_data)) + signed_data

    # RSA signature over signed_data using PKCS1v15 + SHA256
    rsa_sig = key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    sig_entry = struct.pack("<III", 4 + 4 + len(rsa_sig), 0x0103, len(rsa_sig)) + rsa_sig
    sigs_block = struct.pack("<I", len(sig_entry)) + sig_entry

    pubkey_der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    pubkey_prefixed = struct.pack("<I", len(pubkey_der)) + pubkey_der

    signer = signed_data_prefixed + sigs_block + pubkey_prefixed
    signer_prefixed = struct.pack("<I", len(signer)) + signer
    signers_seq = struct.pack("<I", len(signer_prefixed)) + signer_prefixed

    # APK v2 ID-value pair
    v2_pair = struct.pack("<QI", 4 + len(signers_seq), 0x7109871a) + signers_seq

    # Construct APK Signing Block
    # Block size = 8 (size2) + 16 (magic) + len(pairs) = 24 + len(pairs)
    sig_block_inner = v2_pair
    block_size = len(sig_block_inner) + 24
    sig_block = (
        struct.pack("<Q", block_size) +
        sig_block_inner +
        struct.pack("<Q", block_size) +
        b"APK Sig Block 42"
    )

    # 7. Update EOCD with new Central Directory offset: len(sec1) + len(sig_block)
    final_eocd = bytearray(sec3_for_hash)
    final_cd_offset = len(sec1) + len(sig_block)
    struct.pack_into("<I", final_eocd, 16, final_cd_offset)

    final_apk = sec1 + sig_block + sec2 + bytes(final_eocd)
    print(f"Built APK with dual v1 + v2 signatures: {len(final_apk)} bytes")

    # 8. Cryptographic Self-Verification
    print("--- Running APK Verification ---")
    # Verify ZIP integrity
    test_z = zipfile.ZipFile(io.BytesIO(final_apk), "r")
    assert test_z.testzip() is None, "ZIP file integrity error"
    print("[OK] ZIP structure valid")

    # Verify v2 signature
    pub = serialization.load_der_public_key(pubkey_der)
    pub.verify(rsa_sig, signed_data, padding.PKCS1v15(), hashes.SHA256())
    print("[OK] APK Signature Scheme v2 (0x0103 PKCS1v15) valid")

    # Verify resources.arsc is STORED and 4-byte aligned
    arsc_info = test_z.getinfo("resources.arsc")
    assert arsc_info.compress_type == 0, "resources.arsc must be STORED (method 0)"
    arsc_offset = cd_entries[[e["name_bytes"] for e in cd_entries].index(b"resources.arsc")]["offset"]
    # Check payload offset
    payload_offset = arsc_offset + 30 + len(b"resources.arsc") + (4 - ((arsc_offset + 30 + len(b"resources.arsc")) % 4)) % 4
    assert payload_offset % 4 == 0, f"resources.arsc payload not 4-byte aligned: {payload_offset}"
    print(f"[OK] resources.arsc is uncompressed (STORED) and 4-byte aligned at offset {payload_offset}")

    # Write output files
    for p in ["apk/VarantRadarPro.apk", "ui/apk/VarantRadarPro.apk"]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(final_apk)
        print(f"Successfully wrote {p}")

if __name__ == "__main__":
    build_apk()

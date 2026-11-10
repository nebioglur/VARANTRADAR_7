import os
import zipfile
import struct
import hashlib
import base64
import datetime
import io

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

    print(f"Saved key to {KEY_FILE} and cert to {CERT_FILE}")
    return key, cert

def build_apk():
    key, cert = get_or_create_key_and_cert()

    # Read base files from original apk
    with zipfile.ZipFile("apk/VarantRadarPro.apk", "r") as z:
        manifest_xml = z.read("AndroidManifest.xml")
        resources_arsc = z.read("resources.arsc")
        icon_png = z.read("res/mipmap/ic_launcher.png")

    # Read patched DEX
    with open("scratch/classes_patched.dex", "rb") as f:
        classes_dex = f.read()

    files = {
        "AndroidManifest.xml": manifest_xml,
        "classes.dex": classes_dex,
        "res/mipmap/ic_launcher.png": icon_png,
        "resources.arsc": resources_arsc,
    }

    # 1. Generate MANIFEST.MF
    mf_lines = [b"Manifest-Version: 1.0\r\n\r\n"]
    file_names = sorted(files.keys())
    for name in file_names:
        h = hashlib.sha256(files[name]).digest()
        b64 = base64.b64encode(h).decode("ascii")
        sec = f"Name: {name}\r\nSHA-256-Digest: {b64}\r\n\r\n".encode("utf-8")
        mf_lines.append(sec)
    
    manifest_mf = b"".join(mf_lines)

    # 2. Generate VARANTRA.SF
    mf_digest = base64.b64encode(hashlib.sha256(manifest_mf).digest()).decode("ascii")
    sf_lines = [
        b"Signature-Version: 1.0\r\n",
        b"Created-By: 1.0 (Android)\r\n",
        f"SHA-256-Digest-Manifest: {mf_digest}\r\n".encode("utf-8"),
        b"X-Android-APK-Signed: 2\r\n\r\n",
    ]
    for sec in mf_lines[1:]:
        sec_digest = base64.b64encode(hashlib.sha256(sec).digest()).decode("ascii")
        name = sec.splitlines()[0].decode("utf-8")
        sf_lines.append(f"{name}\r\nSHA-256-Digest: {sec_digest}\r\n\r\n".encode("utf-8"))

    varantra_sf = b"".join(sf_lines)

    # 3. Generate VARANTRA.RSA (PKCS#7 detached signature of SF)
    builder = pkcs7.PKCS7SignatureBuilder().set_data(varantra_sf).add_signer(
        cert, key, hashes.SHA256()
    )
    varantra_rsa = builder.sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature])

    # 4. Build standard ZIP archive in memory
    zip_buf = io.BytesIO()
    fixed_time = (2026, 11, 6, 9, 0, 0)
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        # Add core files
        for name in file_names:
            zinfo = zipfile.ZipInfo(filename=name, date_time=fixed_time)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zinfo, files[name])
        
        # Add META-INF files
        meta_files = [
            ("META-INF/MANIFEST.MF", manifest_mf),
            ("META-INF/VARANTRA.SF", varantra_sf),
            ("META-INF/VARANTRA.RSA", varantra_rsa),
        ]
        for name, data in meta_files:
            zinfo = zipfile.ZipInfo(filename=name, date_time=fixed_time)
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zout.writestr(zinfo, data)

    raw_zip = zip_buf.getvalue()

    # 5. Extract Section 1, Section 3, Section 4
    eocd_pos = raw_zip.rfind(b"PK\x05\x06")
    if eocd_pos == -1:
        raise ValueError("EOCD not found in ZIP")

    cd_size, cd_offset = struct.unpack("<II", raw_zip[eocd_pos+12:eocd_pos+20])
    sec1 = raw_zip[:cd_offset]
    sec3 = raw_zip[cd_offset:eocd_pos]
    sec4 = bytearray(raw_zip[eocd_pos:])

    # Align sec1 to 4096-byte boundary by padding with zeroes
    sec1_len = len(sec1)
    sec1_pad_len = (4096 - (sec1_len % 4096)) % 4096
    sec1_padded = sec1 + (b"\x00" * sec1_pad_len)

    # Note: If sec1 is padded, all Central Directory entry offsets in sec3 remain relative to 0
    # because the padding is added at the END of sec1 (right before the signing block)!
    # Now Central Directory offset in sec4 (for hash calculation) is len(sec1_padded)
    sec4_for_hash = bytearray(sec4)
    struct.pack_into("<I", sec4_for_hash, 16, len(sec1_padded))

    CHUNK_SIZE = 1048576 # 1 MB
    chunks = []
    for sec in [sec1_padded, sec3, bytes(sec4_for_hash)]:
        for i in range(0, len(sec), CHUNK_SIZE):
            chunk = sec[i:i+CHUNK_SIZE]
            h = hashlib.sha256(b"\xa5" + struct.pack("<I", len(chunk)) + chunk).digest()
            chunks.append(h)

    apk_digest = hashlib.sha256(b"\x5a" + struct.pack("<I", len(chunks)) + b"".join(chunks)).digest()
    print("Computed APK v2 content digest:", apk_digest.hex())

    # 6. Construct APK v2 SignedData
    # Digest entry: length(4), algo(4), hash_len(4), hash(32)
    digest_entry = struct.pack("<III", 40, 0x0103, 32) + apk_digest
    digests_block = struct.pack("<I", len(digest_entry)) + digest_entry

    # Certificate entry: length(4), cert_len(4), cert_der
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    cert_entry = struct.pack("<I", len(cert_der)) + cert_der
    certs_block = struct.pack("<I", len(cert_entry)) + cert_entry

    # Additional attributes: length(4) = 0
    attrs_block = struct.pack("<I", 0)

    # SignedData: digests_block + certs_block + attrs_block
    signed_data = digests_block + certs_block + attrs_block
    signed_data_prefixed = struct.pack("<I", len(signed_data)) + signed_data

    # Signature: RSA-2048 PKCS#1 v1.5 with SHA-256 over signed_data
    rsa_sig = key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    sig_entry = struct.pack("<III", 4 + 4 + 4 + len(rsa_sig), 0x0103, len(rsa_sig)) + rsa_sig
    sigs_block = struct.pack("<I", len(sig_entry)) + sig_entry

    # Public key: SubjectPublicKeyInfo DER
    pubkey_der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    pubkey_prefixed = struct.pack("<I", len(pubkey_der)) + pubkey_der

    # Signer: signed_data_prefixed + sigs_block + pubkey_prefixed
    signer = signed_data_prefixed + sigs_block + pubkey_prefixed
    signer_prefixed = struct.pack("<I", len(signer)) + signer
    signers_sequence = struct.pack("<I", len(signer_prefixed)) + signer_prefixed

    # APK v2 ID-value pair:
    # pair_len(8): 4 (ID) + len(signers_sequence)
    # ID(4): 0x7109871a
    # value: signers_sequence
    v2_pair = struct.pack("<QI", 4 + len(signers_sequence), 0x7109871a) + signers_sequence

    # Construct complete APK Signing Block
    # Total block bytes = 8 (size1) + len(pairs) + 8 (size2) + 16 (magic) = len(pairs) + 32
    # We want total block bytes to be a multiple of 4096 so Central Directory is also 4096-aligned!
    base_pairs = v2_pair
    # Needed total block len:
    min_total = 32 + len(base_pairs)
    target_total = ((min_total + 4095) // 4096) * 4096
    pad_needed = target_total - min_total
    
    if pad_needed >= 12:
        # Add padding pair (ID 0x42726577)
        # pair: uint64 length (4 + len(pad_payload)), uint32 ID, bytes pad_payload
        pad_payload_len = pad_needed - 12
        pad_pair = struct.pack("<QI", 4 + pad_payload_len, 0x42726577) + (b"\x00" * pad_payload_len)
        all_pairs = base_pairs + pad_pair
    else:
        all_pairs = base_pairs

    block_size = len(all_pairs) + 24 # size excludes size1 (8 bytes)
    sig_block = (
        struct.pack("<Q", block_size) +
        all_pairs +
        struct.pack("<Q", block_size) +
        b"APK Sig Block 42"
    )

    print(f"Total APK Sig Block size: {len(sig_block)} bytes (is multiple of 4096: {len(sig_block) % 4096 == 0})")

    # Update sec4 (EOCD) with new Central Directory offset:
    # New CD offset = len(sec1_padded) + len(sig_block)
    new_cd_offset = len(sec1_padded) + len(sig_block)
    struct.pack_into("<I", sec4, 16, new_cd_offset)
    print(f"New Central Directory offset: {new_cd_offset} (is multiple of 4096: {new_cd_offset % 4096 == 0})")

    # Combine final APK
    final_apk = sec1_padded + sig_block + sec3 + bytes(sec4)
    print(f"Final APK size: {len(final_apk)} bytes")

    # 7. Self-verification
    print("\n--- Running self-verification ---")
    # Verify ZIP readability
    test_z = zipfile.ZipFile(io.BytesIO(final_apk), "r")
    for info in test_z.infolist():
        print(f"  Entry: {info.filename} ({info.file_size} bytes)")
    
    # Verify v2 signature
    magic_idx = final_apk.find(b"APK Sig Block 42")
    assert magic_idx != -1, "Sig block magic missing"
    sb_size = int.from_bytes(final_apk[magic_idx-8:magic_idx], "little")
    sb_start = magic_idx + 16 - 8 - sb_size
    assert sb_start == len(sec1_padded), f"Sig block start mismatch: {sb_start} vs {len(sec1_padded)}"

    # Verify RSA signature with public key
    key.public_key().verify(rsa_sig, signed_data, padding.PKCS1v15(), hashes.SHA256())
    print("  RSA v2 Signature: VALID")

    # Write output to apk/VarantRadarPro.apk and ui/apk/VarantRadarPro.apk
    out_paths = ["apk/VarantRadarPro.apk", "ui/apk/VarantRadarPro.apk"]
    for p in out_paths:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(final_apk)
        print(f"Written {len(final_apk)} bytes to {p}")

    print("\nAPK BUILD AND SIGNING COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    build_apk()

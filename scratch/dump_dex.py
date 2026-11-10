import zipfile, struct

with zipfile.ZipFile('apk/VarantRadarPro.apk', 'r') as z:
    dex = z.read('classes.dex')

magic = dex[:8]
checksum = struct.unpack('<I', dex[8:12])[0]
signature = dex[12:32]
file_size, header_size, endian_tag = struct.unpack('<III', dex[32:44])
string_ids_size, string_ids_off = struct.unpack('<II', dex[56:64])

print(f"file_size={file_size}, string_ids_size={string_ids_size}, string_ids_off={string_ids_off}")

for i in range(string_ids_size):
    str_off = struct.unpack('<I', dex[string_ids_off + i*4 : string_ids_off + i*4 + 4])[0]
    pos = str_off
    # read uleb128 length
    length = 0
    shift = 0
    while True:
        b = dex[pos]
        pos += 1
        length |= (b & 0x7f) << shift
        if not (b & 0x80):
            break
        shift += 7
    s_bytes = dex[pos : pos + length]
    try:
        s = s_bytes.decode('utf-8')
    except Exception:
        s = str(s_bytes)
    print(f"[{i:2d}] @0x{str_off:04x} (len={length}): {s}")

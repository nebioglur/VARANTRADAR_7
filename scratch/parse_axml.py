import zipfile

with zipfile.ZipFile('apk/VarantRadarPro.apk', 'r') as z:
    manifest = z.read('AndroidManifest.xml')

# It's Android binary XML (AXML). Let's extract strings from string pool
import struct

def parse_axml_strings(data):
    # AXML header: 4 bytes magic (0x00080003), 4 bytes file size
    magic, size = struct.unpack('<II', data[:8])
    print(f"AXML Magic: 0x{magic:08x}, size: {size}")
    # String pool chunk starts at offset 8
    chunk_type, chunk_size = struct.unpack('<II', data[8:16])
    print(f"Chunk type: 0x{chunk_type:08x}, size: {chunk_size}")
    if chunk_type != 0x001c0001:
        print("Not a string pool!")
        return []
    string_count, style_count, flags, strings_start, styles_start = struct.unpack('<IIIII', data[16:36])
    print(f"Strings count: {string_count}, flags: 0x{flags:x}, strings_start: {strings_start}")
    string_offsets = struct.unpack(f'<{string_count}I', data[36:36+string_count*4])
    is_utf8 = bool(flags & (1 << 8))
    strings = []
    pool_data = data[8+strings_start:]
    for off in string_offsets:
        if is_utf8:
            # UTF-8: 1 or 2 bytes u16 len, 1 or 2 bytes u8 len, then chars null-terminated
            p = off
            # skip len bytes
            while p < len(pool_data) and pool_data[p] & 0x80: p += 1
            p += 1
            while p < len(pool_data) and pool_data[p] & 0x80: p += 1
            p += 1
            end = pool_data.find(b'\x00', p)
            s = pool_data[p:end].decode('utf-8', errors='ignore')
        else:
            p = off
            u16len = struct.unpack('<H', pool_data[p:p+2])[0]
            p += 2
            s = pool_data[p:p+u16len*2].decode('utf-16le', errors='ignore')
        strings.append(s)
    return strings

strings = parse_axml_strings(manifest)
print("\nManifest Strings in APK:")
for i, s in enumerate(strings):
    if s:
        print(f"  {i}: {s}")

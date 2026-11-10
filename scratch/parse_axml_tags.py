import zipfile, struct

with zipfile.ZipFile('apk/VarantRadarPro.apk', 'r') as z:
    manifest = z.read('AndroidManifest.xml')

# Find START_TAG for uses-sdk
# AXML chunk types:
# 0x00100102: START_TAG
# 0x00100103: END_TAG
idx = 8 + 640 # skip header and string pool
# Resource map is next
chunk_type, chunk_size = struct.unpack('<II', manifest[idx:idx+8])
print(f"Next chunk: 0x{chunk_type:08x}, size: {chunk_size}")
idx += chunk_size

# Now namespace and tags
while idx < len(manifest):
    ctype, csize = struct.unpack('<II', manifest[idx:idx+8])
    if ctype == 0x00100102: # START_TAG
        lineno, comment, ns, name, attr_start, attr_size, attr_count, id_idx, class_idx, style_idx = struct.unpack('<IIIIHHHHHH', manifest[idx+8:idx+36])
        print(f"Tag: string {name}, attrs count: {attr_count}")
        # parse attrs
        attr_offset = idx + 36
        for a in range(attr_count):
            ans, aname, avalue_str, atype, adata = struct.unpack('<IIII I', manifest[attr_offset:attr_offset+20])
            print(f"  attr string {aname}: type={atype >> 24}, data={adata}")
            attr_offset += 20
    idx += csize

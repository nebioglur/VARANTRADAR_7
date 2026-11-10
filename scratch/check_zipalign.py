import zipfile, struct

with open('apk/VarantRadarPro.apk', 'rb') as f:
    data = f.read()

with zipfile.ZipFile('apk/VarantRadarPro.apk', 'r') as z:
    for info in z.infolist():
        # find local header offset in data
        lh_off = info.header_offset
        # local header is: 30 bytes + fn_len + extra_len
        fn_len, extra_len = struct.unpack('<HH', data[lh_off+26:lh_off+30])
        payload_off = lh_off + 30 + fn_len + extra_len
        is_aligned_4 = (payload_off % 4) == 0
        print(f"{info.filename:30} method={info.compress_type} size={info.file_size:8} payload_offset={payload_off:6} 4-aligned={is_aligned_4}")

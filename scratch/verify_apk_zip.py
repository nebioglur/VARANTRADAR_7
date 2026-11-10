import zipfile

with zipfile.ZipFile('apk/VarantRadarPro.apk', 'r') as z:
    bad = z.testzip()
    print("testzip result:", bad)
    for name in z.namelist():
        data = z.read(name)
        print(f"  {name}: {len(data)} bytes, crc32=0x{z.getinfo(name).CRC:08x}")

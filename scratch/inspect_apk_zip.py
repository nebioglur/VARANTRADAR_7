import zipfile

with zipfile.ZipFile('apk/VarantRadarPro.apk', 'r') as z:
    for info in z.infolist():
        print(f"{info.filename:30} size={info.file_size:8} comp={info.compress_size:8}")

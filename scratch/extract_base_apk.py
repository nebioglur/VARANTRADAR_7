import subprocess, zipfile, io, os

p = subprocess.run(['git', 'show', 'dbc822f:apk/VarantRadarPro.apk'], capture_output=True)
z = zipfile.ZipFile(io.BytesIO(p.stdout))

os.makedirs('scratch/apk_source', exist_ok=True)
for name in ['AndroidManifest.xml', 'resources.arsc', 'res/mipmap/ic_launcher.png']:
    data = z.read(name)
    with open(f'scratch/apk_source/{os.path.basename(name)}', 'wb') as f:
        f.write(data)
    print(f"Extracted {name}: {len(data)} bytes")

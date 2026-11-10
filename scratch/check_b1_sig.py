import subprocess, struct

p = subprocess.run(['git', 'show', 'dbc822f:apk/VarantRadarPro.apk'], capture_output=True)
data = p.stdout

eocd_pos = data.rfind(b'PK\x05\x06')
cd_size, cd_offset = struct.unpack('<II', data[eocd_pos+12:eocd_pos+20])
print('b1 EOCD pos:', eocd_pos, 'CD size:', cd_size, 'CD offset:', cd_offset)
sig_magic = data[cd_offset-16:cd_offset]
print('b1 magic:', sig_magic)
if sig_magic == b'APK Sig Block 42':
    print('b1 HAD APK Sig Block!')
else:
    print('b1 did NOT have APK Sig Block!')

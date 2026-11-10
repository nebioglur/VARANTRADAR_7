import struct

with open('apk/VarantRadarPro.apk', 'rb') as f:
    data = f.read()

eocd_pos = data.rfind(b'PK\x05\x06')
print('EOCD pos:', eocd_pos)
cd_size, cd_offset = struct.unpack('<II', data[eocd_pos+12:eocd_pos+20])
print('CD size:', cd_size, 'CD offset:', cd_offset)

# In APK v2, APK Signing Block immediately precedes Central Directory
# The last 16 bytes of the signing block are: 8 bytes size, 8 bytes magic b"APK Sig Block 42"
sig_magic = data[cd_offset-16:cd_offset]
print('16 bytes before CD:', sig_magic)
if sig_magic.endswith(b'APK Sig Block 42'):
    print('Found APK Sig Block magic!')
    block_size = struct.unpack('<Q', sig_magic[:8])[0]
    print('Block size:', block_size)
else:
    print('NO APK Sig Block magic found!')

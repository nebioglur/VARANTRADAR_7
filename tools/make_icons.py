"""VARANTRADAR PWA ikonlarini saf Python ile uretir (PIL gerekmez)."""
import zlib, struct, math, os

BG = (19, 19, 20, 255)          # #131314
GREEN = (0, 230, 118)           # radar yesili
DIM = (0, 140, 80)

def smooth(d, edge, w):
    """1px yumusatik kenar."""
    return max(0.0, min(1.0, (edge + w / 2 - d) / w))

def render(size):
    img = bytearray(BG * (size * size))
    c = size / 2
    R = size * 0.42            # dis halka yariçapi
    lw = max(1.5, size / 110)  # cizgi kalinligi

    def put(x, y, rgba):
        i = (y * size + x) * 4
        a = rgba[3] / 255
        img[i] = int(img[i] * (1 - a) + rgba[0] * a)
        img[i+1] = int(img[i+1] * (1 - a) + rgba[1] * a)
        img[i+2] = int(img[i+2] * (1 - a) + rgba[2] * a)
        img[i+3] = 255

    for y in range(size):
        for x in range(size):
            dx, dy = x - c, y - c
            d = math.hypot(dx, dy)
            # konsantrik halkalar
            for k in (1.0, 0.72, 0.45):
                a = smooth(abs(d - R * k), 0, lw)
                if a > 0:
                    col = GREEN if k == 1.0 else DIM
                    put(x, y, (col[0], col[1], col[2], int(255 * a)))
            # tarama dilimi (sag ust)
            ang = math.degrees(math.atan2(-dy, dx)) % 360
            if 0 <= ang <= 70 and d <= R:
                fade = 1 - ang / 70
                a = 0.35 * fade * fade
                put(x, y, (0, 200, 110, int(255 * a)))
            # yukselen trend oku
            p1 = (-0.30 * size, 0.26 * size)
            p2 = (-0.02 * size, 0.00 * size)
            p3 = (0.30 * size, -0.28 * size)
            def seg_dist(px, py, ax, ay, bx, by):
                vx, vy = bx - ax, by - ay
                t = max(0, min(1, ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)))
                return math.hypot(px - (ax + t * vx), py - (ay + t * vy))
            aw = size / 22
            if seg_dist(dx, dy, p1[0], p1[1], p2[0], p2[1]) < aw or \
               seg_dist(dx, dy, p2[0], p2[1], p3[0], p3[1]) < aw:
                put(x, y, (0, 255, 130, 255))
            # ok ucu
            hx, hy = 0.30 * size, -0.28 * size
            for (ox, oy) in ((-0.11 * size, 0.02 * size), (-0.02 * size, 0.12 * size)):
                if math.hypot(dx - (hx + ox), dy - (hy + oy)) < aw:
                    put(x, y, (0, 255, 130, 255))

    return bytes(img)

def png(path, size):
    raw = b''.join(b'\x00' + render(size)[y * size * 4:(y + 1) * size * 4] for y in range(size))
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    data = (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9))
            + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(data)
    print(path, size, os.path.getsize(path), 'bytes')

os.makedirs('ui/icons', exist_ok=True)
png('ui/icons/icon-512.png', 512)
png('ui/icons/icon-192.png', 192)
png('ui/icons/icon-512-maskable.png', 512)
png('ui/icons/icon-192-maskable.png', 192)
png('ui/icons/icon-64.png', 64)

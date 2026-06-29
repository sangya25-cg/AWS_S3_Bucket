import os
import zlib
import struct

os.makedirs("assets", exist_ok=True)

width, height = 512, 512

pixel_rows = []
for y in range(height):
    row = bytearray()
    ratio_y = y / (height - 1)
    for x in range(width):
        ratio_x = x / (width - 1)
        r = int(18 + 72 * ratio_x + 36 * ratio_y)
        g = int(44 + 120 * ratio_y)
        b = int(92 + 88 * (1 - ratio_x))

        cx = x - 255
        cy = y - 220
        dist = (cx * cx + cy * cy) ** 0.5
        if dist < 70 or ((x - 200) ** 2 + (y - 200) ** 2) ** 0.5 < 65 or ((x - 320) ** 2 + (y - 190) ** 2) ** 0.5 < 72:
            r, g, b = 255, 255, 255
        if 225 < x < 285 and 245 < y < 315:
            r, g, b = 16, 185, 245
        if 235 < x < 275 and 190 < y < 245:
            r, g, b = 16, 185, 245
        if 248 < x < 262 and 275 < y < 289:
            r, g, b = 10, 25, 48

        row.extend((r, g, b, 255))
    pixel_rows.append(b"\x00" + bytes(row))

raw_data = zlib.compress(b"".join(pixel_rows), 9)

with open("assets/logo.png", "wb") as f:
    f.write(b"\x89PNG\r\n\x1a\n")
    f.write(struct.pack("!I", 13))
    f.write(b"IHDR")
    f.write(struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0))
    f.write(struct.pack("!I", zlib.crc32(b"IHDR" + struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0)) & 0xFFFFFFFF))
    f.write(struct.pack("!I", len(raw_data)))
    f.write(b"IDAT")
    f.write(raw_data)
    f.write(struct.pack("!I", zlib.crc32(b"IDAT" + raw_data) & 0xFFFFFFFF))
    f.write(struct.pack("!I", 0))
    f.write(b"IEND")
    f.write(struct.pack("!I", zlib.crc32(b"IEND") & 0xFFFFFFFF))

print("Created assets/logo.png")

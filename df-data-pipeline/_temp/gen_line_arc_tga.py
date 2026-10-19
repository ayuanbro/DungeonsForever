import struct

SIZE = 64
DENS = 4.0
RAD = 6.0 * DENS
LW = 2.5 * DENS
OUT = RAD + LW / 2.0
INN = RAD - LW / 2.0
SS = 8

buf = bytearray()
for j in range(SIZE):
    for i in range(SIZE):
        hit = 0
        for sj in range(SS):
            y = j + (sj + 0.5) / SS
            for si in range(SS):
                x = i + (si + 0.5) / SS
                d = (x * x + y * y) ** 0.5
                if INN <= d <= OUT:
                    hit += 1
        buf += bytes((255, 255, 255, int(round(255.0 * hit / (SS * SS)))))

hdr = struct.pack("<BBBBBBBBHHHHBB", 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, SIZE, SIZE, 32, 0x28)
open("Media/DFLineArc.tga", "wb").write(hdr + bytes(buf))
print("Media/DFLineArc.tga %dx%d  1/4 圆环 r=%.2f 线宽=%.2f  UV=%.6f" % (SIZE, SIZE, RAD, LW, OUT / SIZE))

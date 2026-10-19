import struct, math

SIZE = 64
DENS = 4.0
R = 8.0
HW = 1.25
RIN = R - HW
ROUT = R + HW
SS = 6

maxl = (SIZE - 1) / DENS + 0.5 / DENS
px = [0.0] * (SIZE * SIZE)

for j in range(SIZE):
    for i in range(SIZE):
        hit = 0
        for sj in range(SS):
            for si in range(SS):
                lx = (i + (si + 0.5) / SS) / DENS
                ly = (j + (sj + 0.5) / SS) / DENS
                d = math.sqrt(lx * lx + ly * ly)
                if RIN <= d <= ROUT:
                    hit += 1
        px[j * SIZE + i] = int(round(255.0 * hit / (SS * SS)))

buf = bytearray()
for j in range(SIZE):
    for i in range(SIZE):
        a = px[j * SIZE + i]
        buf += bytes((255, 255, 255, a))

hdr = bytearray()
hdr += bytes((0, 0, 2, 0, 0, 0, 0, 0))
hdr += bytes((0, 0, 0, 0))
hdr += struct.pack("<HH", SIZE, SIZE)
hdr += bytes((32, 0x28))

out = "D:/workspace/DungeonsForever/Media/DFLineFil.tga"
open(out, "wb").write(bytes(hdr) + bytes(buf))
print("saved", out, len(hdr) + len(buf), "rin", RIN, "rout", ROUT, "uv", ROUT / 16.0)

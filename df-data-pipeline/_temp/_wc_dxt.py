"""Lootified BLP2 解码：compression=1 + encoding=2 实为 DXT1 块（调色板区全零，
数据量 = 0.5B/px = DXT1 的 8 字节/块）。块循环解码，简单可靠。"""
import struct

import numpy as np
from PIL import Image


def _rgb565(v):
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b5 = v & 0x1F
    return ((r * 255 + 15) // 31, (g * 255 + 31) // 63, (b5 * 255 + 15) // 31)


def dxt1_decode(data, w, h):
    """data: bytes，DXT1 块流（4x4 块，行优先）→ (h, w, 3) uint8"""
    bw, bh = w // 4, h // 4
    out = np.zeros((h, w, 3), np.uint8)
    pos = 0
    for by in range(bh):
        for bx in range(bw):
            blk = data[pos:pos + 8]
            pos += 8
            c0 = _rgb565(blk[0] | (blk[1] << 8))
            c1 = _rgb565(blk[2] | (blk[3] << 8))
            c2 = tuple((2 * a + b) // 3 for a, b in zip(c0, c1))
            c3 = tuple((a + 2 * b) // 3 for a, b in zip(c0, c1))
            pal = (c0, c1, c2, c3)
            for r in range(4):
                byte = blk[4 + r]
                row = out[by * 4 + r, bx * 4:bx * 4 + 4]
                for c in range(4):
                    row[c] = pal[(byte >> (c * 2)) & 3]
    return out


def lootified_blp(path):
    """Lootified 的「BLP2」（DXT1 数据）→ PIL RGB"""
    b = open(path, "rb").read()
    assert b[:4] == b"BLP2"
    h, w = struct.unpack_from("<II", b, 12)
    off = struct.unpack_from("<I", b, 20)[0]        # mipOffsets[0]
    size = struct.unpack_from("<I", b, 84)[0]       # mipSizes[0]（前 64B 是 offsets 表）
    return Image.fromarray(dxt1_decode(b[off:off + size], w, h)).convert("RGB")


if __name__ == "__main__":
    import os
    LOOT = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/Lootified/Media/Maps/WailingCaverns"
    img = lootified_blp(os.path.join(LOOT, "WailingCaverns1_1.blp"))
    img.save("_temp/_wc_compare/lootified_tile1_dxt.png")
    print("saved", img.size)

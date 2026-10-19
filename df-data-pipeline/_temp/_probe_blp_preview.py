# -*- coding: utf-8 -*-
"""把 BLP2（DXT5/BC3）解码成 PNG，用于肉眼看图标内容。不参与生成链。
用法：python _probe_blp_preview.py <in.blp> <out.png>
"""
import struct
import sys

from PIL import Image


def parse_header(d):
    assert d[:4] == b'BLP2', 'not BLP2: %r' % d[:4]
    typ, enc, adepth, aenc, mips = struct.unpack('<IBBBB', d[4:12])
    w, h = struct.unpack('<II', d[12:20])
    offsets = struct.unpack('<16I', d[20:84])
    lengths = struct.unpack('<16I', d[84:148])
    return dict(type=typ, enc=enc, aDepth=adepth, aEnc=aenc, mips=mips,
                w=w, h=h, offsets=offsets, lengths=lengths)


def rgb565(c):
    return (((c >> 11) & 0x1F) * 255 // 31,
            ((c >> 5) & 0x3F) * 255 // 63,
            (c & 0x1F) * 255 // 31)


def decode_dxt5(data, w, h):
    img = Image.new('RGBA', (w, h))
    px = img.load()
    off = 0
    for by in range(h // 4):
        for bx in range(w // 4):
            a0, a1 = data[off], data[off + 1]
            abits = int.from_bytes(data[off + 2:off + 8], 'little')
            c0, c1 = struct.unpack('<HH', data[off + 8:off + 12])
            cbits = int.from_bytes(data[off + 12:off + 16], 'little')
            off += 16

            al = [a0, a1]
            if a0 > a1:
                al += [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)]
            else:
                al += [((5 - i) * a0 + i * a1) // 5 for i in range(1, 5)]
                al += [0, 255]

            p0, p1 = rgb565(c0), rgb565(c1)
            cl = [p0, p1]
            if c0 > c1:
                cl.append(tuple((2 * p0[k] + p1[k]) // 3 for k in range(3)))
                cl.append(tuple((p0[k] + 2 * p1[k]) // 3 for k in range(3)))
            else:
                cl.append(tuple((p0[k] + p1[k]) // 2 for k in range(3)))
                cl.append((0, 0, 0))

            for i in range(16):
                py, pxi = divmod(i, 4)
                c = cl[(cbits >> (2 * i)) & 0x3]
                px[bx * 4 + pxi, by * 4 + py] = (c[0], c[1], c[2], al[(abits >> (3 * i)) & 0x7])
    return img


def main():
    src, dst = sys.argv[1], sys.argv[2]
    d = open(src, 'rb').read()
    hd = parse_header(d)
    print('%-10s %dx%d enc=%d aDepth=%d aEnc=%d mips=%d  bytes=%d'
          % ('BLP2', hd['w'], hd['h'], hd['enc'], hd['aDepth'], hd['aEnc'], hd['mips'], len(d)))
    off0, len0 = hd['offsets'][0], hd['lengths'][0]
    print('mip0 offset=%d length=%d  期望 DXT5 字节数=%d'
          % (off0, len0, hd['w'] * hd['h']))
    assert hd['enc'] == 2 and hd['aDepth'] == 8 and hd['aEnc'] == 7, '非 DXT5，本脚本不支持'
    assert len0 == hd['w'] * hd['h'], 'mip0 长度异常（DXT5 应为 w*h）'
    img = decode_dxt5(d[off0:off0 + len0], hd['w'], hd['h'])
    img.save(dst)
    # 顺带报告图像统计，便于判断是否「深色方底 + 高饱和主体」
    small = img.resize((32, 32))
    pxs = list(small.getdata())
    op = [p for p in pxs if p[3] > 8]
    avg = tuple(sum(p[k] for p in op) // max(1, len(op)) for k in range(3))
    corners = [img.getpixel(t) for t in ((2, 2), (hd['w'] - 3, 2), (2, hd['h'] - 3), (hd['w'] - 3, hd['h'] - 3))]
    print('不透明像素占比 %.1f%%  主体均值 RGB=%s' % (100.0 * len(op) / len(pxs), avg))
    print('四角像素 %s' % (corners,))
    print('已写出 %s' % dst)


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""截图边距实测 v2：按 L0 精确色值找插件窗口，再量到最外层卡片描边。

L 色阶真值（Hui.lua）：L0=#0A0C10 主窗底 / L1=#10131A 容器卡 / 卡描边=白 10%。
逻辑宽 1000 ⇒ 逻辑像素 = gap_px * 1000 / 窗口内宽_px（与截图缩放/DIP 无关）。
"""
import sys
from PIL import Image

L0 = (0x0A, 0x0C, 0x10)
L1 = (0x10, 0x13, 0x1A)


def is_l0(p):
    return abs(p[0] - L0[0]) <= 5 and abs(p[1] - L0[1]) <= 5 and abs(p[2] - L0[2]) <= 6


def is_l1(p):
    return abs(p[0] - L1[0]) <= 4 and abs(p[1] - L1[1]) <= 4 and abs(p[2] - L1[2]) <= 5


def longest_run(flags):
    best = (0, -1, -1)
    s = None
    for i, f in enumerate(flags):
        if f and s is None:
            s = i
        elif not f and s is not None:
            if i - s > best[0]:
                best = (i - s, s, i - 1)
            s = None
    if s is not None and len(flags) - s > best[0]:
        best = (len(flags) - s, s, len(flags) - 1)
    return best


def main():
    p = sys.argv[1]
    im = Image.open(p).convert('RGB')
    W, H = im.size
    px = im.load()

    rows = []
    for y in range(H):
        flags = [is_l0(px[x, y]) for x in range(W)]
        n, a, b = longest_run(flags)
        rows.append((n, a, b))
    best_rows = [r for r in rows if r[0] > 300]
    if not best_rows:
        print('no L0 window found'); return
    wx0 = min(r[1] for r in best_rows)
    wx1 = max(r[2] for r in best_rows)
    rn = max(r[0] for r in best_rows)
    keep = [i for i, r in enumerate(rows) if r[0] > 0.9 * rn]
    wy0, wy1 = keep[0], keep[-1]
    ww, wh = wx1 - wx0 + 1, wy1 - wy0 + 1
    print('image    = %dx%d' % (W, H))
    print('window   = x %d..%d (w=%d)  y %d..%d (h=%d)' % (wx0, wx1, ww, wy0, wy1, wh))
    print('w/h ratio= %.3f   (窗口逻辑比 1000/708 = 1.412)' % (wh / float(ww)))
    scale = ww / 1000.0
    print('scale    = %.4f px / 逻辑像素' % scale)
    print('window logical h = %.0f (expect 708)' % (wh / scale))

    cy = wy0 + wh // 2
    for label, y in (('top-third', wy0 + wh // 3), ('middle', cy), ('bottom-third', wy0 + 2 * wh // 3)):
        # 窗口内：从 L0 区往右找第一条非 L0 的「描边」像素
        x = wx0 + 2
        while x < wx1 and is_l0(px[x, y]):
            x += 1
        edge = x
        # 跳过描边/圆角，确认其后是卡片内部（L1 系）
        print('  [%s y=%d] 卡片左缘 x=%d  gap=%dpx  => %.1f 逻辑'
              % (label, y, edge, edge - wx0, (edge - wx0) / scale))
    cx = wx0 + ww // 4
    y = wy1 - 2
    while y > wy0 and is_l0(px[cx, y]):
        y -= 1
    print('  [bottom x=%d] 卡片底缘 y=%d  gap=%dpx  => %.1f 逻辑'
          % (cx, y, wy1 - y, (wy1 - y) / scale))
    y = wy0 + 2
    while y < wy1 and is_l0(px[cx, y]):
        y += 1
    print('  [top x=%d] 顶部首个非 L0 件 y=%d  gap=%dpx  => %.1f 逻辑'
          % (cx, y, y - wy0, (y - wy0) / scale))


if __name__ == '__main__':
    main()

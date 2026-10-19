# -*- coding: utf-8 -*-
# 生成 Media/VGradient.tga：16x64 黑色垂直渐隐（顶 alpha=0 → 底 alpha=191）。
# 用途：卡墙卡片底部名牌 plate 顶部融入原画（替代硬边黑 55% 直角条）。
# desc=0x28（top-down + 8bit alpha 声明，对齐 HUIGlass 惯例）。
import struct

S_W, S_H = 16, 64
rows = bytearray()
for y in range(S_H):
    t = y / (S_H - 1)          # 0 顶 → 1 底
    a = round(191 * (t ** 1.35))  # 轻微幂次：底部更实、上部更快隐没
    for _ in range(S_W):
        rows += bytes([0, 0, 0, a])
hdr = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, S_W, S_H, 32, 0x28)
open('Media/VGradient.tga', 'wb').write(hdr + bytes(rows))
print('Media/VGradient.tga OK', S_W, S_H)

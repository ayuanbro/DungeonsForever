# -*- coding: utf-8 -*-
import os, zipfile

ROOT = r"D:\workspace\DungeonsForever"
OUT = os.path.join(ROOT, "_temp", "HUI_UI接入包.zip")

entries = [
    (os.path.join(ROOT, "_temp", "_corner_view", "hui_guide.html"), "HUI接入指南.html"),
    (os.path.join(ROOT, "_temp", "_corner_view", "HUI迁移指令.md"), "HUI迁移指令.md"),
    (os.path.join(ROOT, "Core", "Hui.lua"), "Core/Hui.lua"),
    (os.path.join(ROOT, ".workbuddy", "UI_RULES.md"), "UI_RULES.md"),
]

libhui = os.path.join(ROOT, "Media", "LibHUI")
for fn in sorted(os.listdir(libhui)):
    if fn.lower().endswith(".tga"):
        entries.append((os.path.join(libhui, fn), "Media/LibHUI/" + fn))

readme = """HUI UI 体系接入包
==================

内容清单
- HUI接入指南.html : 接入指南（体系三件套 / 色阶 / 圆角体系 / API 速查 / 军规 / 示例 / 避坑）
- Core/Hui.lua     : UI 体系核心库（唯一需要拷入的 Lua 文件）
- UI_RULES.md      : UI 规则正式版（布局三边距 / 圆角体系 / 层级纪律 / 字号）
- Media/LibHUI/    : 贴图依赖（22 张 tga，含五档圆角 Fill/Ring 超采样贴图）

接入步骤
1. 把 Core/Hui.lua 拷入你的插件目录，并在 .toc 中
   在所有使用 ns.hui 的文件之前加载它。
2. 把 Media/LibHUI/ 整个目录拷入你的插件目录。
3. Hui.lua 内部以 "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\LibHUI\\\\..."
   引用贴图。如果你的插件不叫 DungeonsForever，
   请把 Hui.lua 中的该路径前缀批量替换为你自己的插件名，
   或建立同名目录结构。
4. 初始化：在你的入口处调用 ns.hui 的公开 API
   （BuildRoundedBG / BuildCapsule / BuildRoundBorder / TextColor /
   FontObject / ShowMenu 等，详见接入指南的 API 速查表）。

注意事项
- 圆角件一律使用 64x64 超采样贴图 + UV 取象限（HUIGlassFill/Ring 4/6/8/10/12 五档），
  不要再使用旧的 HUIRoundCorner* 拼接式方案（包内保留仅为兼容回退）。
- 控件边框色统一走 C_CTRL_BORDER 单一真源，勿散落硬编码。
- Hui.lua 依赖 WoW 8.x+ 客户端 API；无 C_Timer 的老端需自行适配。
"""

if os.path.exists(OUT):
    os.remove(OUT)

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    info = zipfile.ZipInfo("README.txt", date_time=(2026, 10, 14, 0, 0, 0))
    z.writestr(info, readme.encode("utf-8-sig"))
    total = 0
    for src, arc in entries:
        z.write(src, arc)
        total += os.path.getsize(src)

print("entries:", len(entries) + 1)
print("raw size: %.1f KB" % (total / 1024))
print("zip size: %.1f KB" % (os.path.getsize(OUT) / 1024))
print("OUT:", OUT)

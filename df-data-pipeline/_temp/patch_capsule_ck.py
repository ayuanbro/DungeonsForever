import sys

P = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"

OLD = "       and '（rev15' in profui)\n"
NEW = ("       and '（rev15' in profui)\n"
       "    # ★★ 2026-10-13 用户拍板：圆角超采样体系扩展到 BuildCapsule（胶囊家族）——\n"
       "    #   四角一律 GLASS_FILL 超采样象限取样（与 BuildRoundedBG 同一体系），\n"
       "    #   角块尺寸 = 原半径（显示半径不变），贴图档位由 SnapCornerR 就近选。\n"
       "    ck('★★ HUI 圆角体系统一：BuildCapsule 四角走 GLASS_FILL 超采样象限贴图（旧 4 张角贴图退役）',\n"
       "       'local GLASS_FILL_TEX = \"Interface/AddOns/DungeonsForever/Media/LibHUI/HUIGlassFill\"' in hui\n"
       "       and 'local function SnapCornerR(r)' in hui\n"
       "       and 'local function CornerQuadUV(point, snap)' in hui\n"
       "       and 'local cornerTex = GLASS_FILL_TEX .. snapR' in hui\n"
       "       and 'tl:SetTexCoord(CornerQuadUV(\"TOPLEFT\", snapR))' in hui\n"
       "       and 'tr:SetTexCoord(CornerQuadUV(\"TOPRIGHT\", snapR))' in hui\n"
       "       and 'bl:SetTexCoord(CornerQuadUV(\"BOTTOMLEFT\", snapR))' in hui\n"
       "       and 'br:SetTexCoord(CornerQuadUV(\"BOTTOMRIGHT\", snapR))' in hui\n"
       "       and 'HUI_CORNER_TL' not in hui.split('local function BuildCapsule')[1].split('local pieces')[0])\n")

d = open(P, "rb").read()
c0 = d.count(b"\r\n"); b0 = d.count(b"\n") - c0
o = OLD.encode("utf-8")
print("hit", d.count(o))
if d.count(o) != 1:
    sys.exit(1)
open(P, "wb").write(d.replace(o, NEW.encode("utf-8")))
d2 = open(P, "rb").read()
print("OK CRLF", c0, "->", d2.count(b"\r\n"), "bareLF", b0, "->", d2.count(b"\n") - d2.count(b"\r\n"))

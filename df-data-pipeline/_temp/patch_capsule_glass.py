import sys

P = r"D:\workspace\DungeonsForever\Core\Hui.lua"

PAIRS = [
    # 四角换超采样贴图 + 象限 UV（与 BuildRoundedBG / DrawRoundBorder 同一体系）
    ("        local tl = f:CreateTexture(nil, \"BACKGROUND\", nil, sl)\n"
     "        tl:SetTexture(HUI_CORNER_TL)\n"
     "        tl:SetSize(cornerSize, cornerSize)\n",
     "        local snapR = SnapCornerR(cornerSize)\n"
     "        local cornerTex = GLASS_FILL_TEX .. snapR\n"
     "        local tl = f:CreateTexture(nil, \"BACKGROUND\", nil, sl)\n"
     "        tl:SetTexture(cornerTex)\n"
     "        tl:SetTexCoord(CornerQuadUV(\"TOPLEFT\", snapR))\n"
     "        tl:SetSize(cornerSize, cornerSize)\n"),
    ("        tr:SetTexture(HUI_CORNER_TR)\n"
     "        tr:SetSize(cornerSize, cornerSize)\n",
     "        tr:SetTexture(cornerTex)\n"
     "        tr:SetTexCoord(CornerQuadUV(\"TOPRIGHT\", snapR))\n"
     "        tr:SetSize(cornerSize, cornerSize)\n"),
    ("        bl:SetTexture(HUI_CORNER_BL)\n"
     "        bl:SetSize(cornerSize, cornerSize)\n",
     "        bl:SetTexture(cornerTex)\n"
     "        bl:SetTexCoord(CornerQuadUV(\"BOTTOMLEFT\", snapR))\n"
     "        bl:SetSize(cornerSize, cornerSize)\n"),
    ("        br:SetTexture(HUI_CORNER_BR)\n"
     "        br:SetSize(cornerSize, cornerSize)\n",
     "        br:SetTexture(cornerTex)\n"
     "        br:SetTexCoord(CornerQuadUV(\"BOTTOMRIGHT\", snapR))\n"
     "        br:SetSize(cornerSize, cornerSize)\n"),
]

d = open(P, "rb").read()
c0 = d.count(b"\r\n"); b0 = d.count(b"\n") - c0
for old, new in PAIRS:
    o = old.encode("utf-8"); n = new.encode("utf-8")
    c = d.count(o)
    print("hit", c, old.split("\n")[0][:40])
    if c != 1:
        sys.exit(1)
    d = d.replace(o, n)
open(P, "wb").write(d)
c1 = d.count(b"\r\n"); b1 = d.count(b"\n") - c1
print("OK Hui.lua CRLF", c0, "->", c1, "bareLF", b0, "->", b1)

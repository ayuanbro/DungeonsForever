# -*- coding: utf-8 -*-
# 2026-10-10 用户：配方名/材料名按物品品质着色（主文件，CRLF 二进制锚定）
import sys

P = r"D:/workspace/DungeonsForever/Core/ProfessionUI.lua"
data = open(P, "rb").read()


def CRLF(s):
    b = s.encode("utf-8")
    return b.replace(b"\n", b"\r\n")


def rep1(old, new):
    global data
    o, n = CRLF(old), CRLF(new)
    c = data.count(o)
    assert c == 1, "anchor count=%d for: %r" % (c, old[:60])
    data = data.replace(o, n)


# 1) PD.QualCached（会话内正向缓存）插在 PaintMatSegs 前
rep1(
    "function PD.PaintMatSegs(r, segs, color)",
    """-- 2026-10-10 用户：名称/材料按物品品质着色。DG.QualOf 走 GetItemInfo（零缓存引擎调用），
--   整页重绘会问几百次 ⇒ 会话内正向缓存（nil 不缓存：数据到货后下次重绘自然拿到）。
local _qCache = {}
function PD.QualCached(id)
    if id == nil then return nil end
    local v = _qCache[id]
    if v == nil then
        v = DG.QualOf(id)
        if v ~= nil then _qCache[id] = v end
    end
    return v
end

function PD.PaintMatSegs(r, segs, color)""",
)

# 2) 材料段按品质着色（…纯段无 id 保持默认色）
rep1(
    "        fs:SetTextColor(Unpack(col))",
    """        -- 2026-10-10 用户：材料名按材料品质着色（…纯段无 id 保持默认色）
        local scol = col
        if segs[i].id then
            local q = PD.QualCached(segs[i].id)
            if q then scol = { DG.QColor(q) } end
        end
        fs:SetTextColor(Unpack(scol))""",
)

# 3) RecipeSpec：qItem = 产物物品 id
rep1(
    '        kind = "row", is_new = r[11], it = { r[2] }, row = r, _mats = r[12],',
    '        kind = "row", is_new = r[11], it = { r[2] }, qItem = r[2], row = r, _mats = r[12],',
)

# 4) CraftedSpec：qItem + matSegs（可制造页材料也走分段链 → 品质色）
rep1(
    "    local mats = PD.MatText(c[8], 4)",
    """    local mats = PD.MatText(c[8], 4)
    local matCol, _, _, matSg = PD.MatCol(c[8], PD.MAT_FS, PD.MAT_W)""",
)
rep1(
    "        mats = PD.MatCol(c[8], PD.MAT_FS, PD.MAT_W),",
    """        mats = matCol,
        matSegs = matSg,""",
)

# 5) EnchantSpec：matSegs（附魔页材料同样品质色）
rep1(
    "function PD.EnchantSpec(en)",
    """function PD.EnchantSpec(en)
    local matCol, _, _, matSg = PD.MatCol(en[9], PD.MAT_FS, PD.MAT_W)""",
)
rep1(
    "        mats = PD.MatCol(en[9], PD.MAT_FS, PD.MAT_W),",
    """        mats = matCol,
        matSegs = matSg,""",
)

# 6) BindRow 通用行：qItem 有品质 → 名称上品质色
rep1(
    "    r.a:SetTextColor(Unpack(spec.nameColor or C_TEXT))",
    """    -- 2026-10-10 用户：配方/可制造名称按产物物品品质着色（无品质数据退回默认色）
    local ncol = spec.nameColor
    if not ncol and spec.qItem then
        local q = PD.QualCached(spec.qItem)
        if q then ncol = { DG.QColor(q) } end
    end
    r.a:SetTextColor(Unpack(ncol or C_TEXT))""",
)

open(P, "wb").write(data)
print("main patch OK")

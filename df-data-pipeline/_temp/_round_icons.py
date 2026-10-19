# -*- coding: utf-8 -*-
"""全仓图标「倒圆角」统一补丁（幂等）。

★★★★★ 已退役（2026-09-30）· 新任务不要再跑 ★★★★★
    本脚本走的是「给每个图标套一层与图标等大的帧（ns.hui.IconTile）」。功能上通，
    但**每行多一个帧** ⇒ 把「新建帧计数 / 材料块不是帧 / 图标尺寸」类动态断言集体打红
    （实测 1062 项里红了 10 项），代价过大 —— 已用 `_round_icons2.py` 反向替换掉。
    正解见 `_round_icons2.py`：RoundIcon 的蒙版锚点从父帧改成**贴图**
    （mask:SetAllPoints(tex)，与官方 Blizzard_* 的 MaskTexture 同构），一行生效、零新增帧。
    本文件保留只为**回滚/引用**（`_round_icons2.py` 会 import 它的 EDITS 做反向替换）。
（以下为原 v1 说明，仅存档案）
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HELPER_ANCHOR = """        tex:AddMaskTexture(mask)
    end

    function ns.hui.RoundImage(tex, radiusFrac)
"""

HELPER_BLOCK = """        tex:AddMaskTexture(mask)
    end

    -- ★ 圆角图标瓦片：图标尺寸 < 父帧尺寸时的唯一正确姿势。
    --   RoundIcon 的蒙版是 mask:SetAllPoints(tex:GetParent()) —— 按**父帧**尺寸裁。父帧比图标大
    --   （行 / 卡片 / 按钮上的小图标）时，圆角落在父帧的四个角上，图标看上去就是「没倒圆角」。
    --   所以这类图标必须单独套一层与图标等大的帧，把贴图 SetAllPoints 上去，再挂蒙版。
    --   用法：local tile, tex = ns.hui.IconTile(row) —— 之后对 **tile** 调
    --   SetSize / SetPoint / ClearAllPoints / SetShown；贴图只调 SetTexture / SetTexCoord /
    --   SetDesaturated / SetAlpha / Show / Hide。
    function ns.hui.IconTile(parent, w, h)
        local fr = CreateFrame("Frame", nil, parent)
        if w then fr:SetSize(w, h or w) end
        local tex = fr:CreateTexture(nil, "ARTWORK")
        tex:SetAllPoints(fr)
        ns.hui.RoundIcon(tex)
        return fr, tex
    end

    function ns.hui.RoundImage(tex, radiusFrac)
"""

# (文件, [(old, new, 期望命中次数), ...])
EDITS = []


def E(path, pairs):
    EDITS.append((path, pairs))


E("Core/Hui.lua", [
    (HELPER_ANCHOR, HELPER_BLOCK, 1),
])

E("Core/ProfessionUI.lua", [
    # ① PD.Row 的行图标（父帧 = 整行 PD.RIGHT_W 宽）
    ("    r.icon = r:CreateTexture(nil, \"ARTWORK\")\n"
     "    r.icon:SetSize(20, 20)\n"
     "    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n",

     "    -- 圆角图标：图标(20 见方)比行宽(PD.RIGHT_W)小得多，必须套一层等大帧才裁得到角\n"
     "    r.iconTile, r.icon = ns.hui.IconTile(r, 20, 20)\n"
     "    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n", 1),
    # ② 行图标的三种布局（普通行 / 升级表行）
    ("    r.icon:SetShown(showIcon)\n"
     "    if showIcon then\n"
     "        r.icon:SetSize(20, 20)\n"
     "        r.icon:ClearAllPoints()\n"
     "        r.icon:SetPoint(\"TOPLEFT\", r, \"TOPLEFT\", 6, -5)\n",

     "    r.iconTile:SetShown(showIcon)\n"
     "    if showIcon then\n"
     "        r.iconTile:SetSize(20, 20)\n"
     "        r.iconTile:ClearAllPoints()\n"
     "        r.iconTile:SetPoint(\"TOPLEFT\", r, \"TOPLEFT\", 6, -5)\n", 1),
    ("        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n"
     "        r.icon:ClearAllPoints()\n"
     "        r.icon:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_ICON_X, 0)\n",

     "        r.iconTile:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n"
     "        r.iconTile:ClearAllPoints()\n"
     "        r.iconTile:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_ICON_X, 0)\n", 1),
    # ③ 职业版对照表的行图标（15 见方）
    ("        r.icon = r:CreateTexture(nil, \"ARTWORK\")\n"
     "        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        r.icon:SetSize(15, 15)\n"
     "        r.icon:SetPoint(\"LEFT\", r, \"LEFT\", 0, 0)\n",

     "        r.iconTile, r.icon = ns.hui.IconTile(r, 15, 15)\n"
     "        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        r.iconTile:SetPoint(\"LEFT\", r, \"LEFT\", 0, 0)\n", 1),
    # ④ 总览卡片图标
    ("            c:EnableMouse(true)            c.icon = c:CreateTexture(nil, \"ARTWORK\")\n"
     "            c.icon:SetSize(PD.IX_ICON, PD.IX_ICON)\n"
     "            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            c.icon:SetPoint(\"LEFT\", c, \"LEFT\", 7, 0)\n",

     "            c:EnableMouse(true)\n"
     "            c.iconTile, c.icon = ns.hui.IconTile(c, PD.IX_ICON, PD.IX_ICON)\n"
     "            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            c.iconTile:SetPoint(\"LEFT\", c, \"LEFT\", 7, 0)\n", 1),
    # ⑤ 左侧专业导航按钮图标
    ("        bt.__icon = bt:CreateTexture(nil, \"ARTWORK\")\n"
     "        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        bt.__icon:SetSize(PD.NAV_ICON, PD.NAV_ICON)\n"
     "        bt.__icon:SetPoint(\"LEFT\", bt, \"LEFT\", 5, 0)\n",

     "        bt.__iconTile, bt.__icon = ns.hui.IconTile(bt, PD.NAV_ICON, PD.NAV_ICON)\n"
     "        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        bt.__iconTile:SetPoint(\"LEFT\", bt, \"LEFT\", 5, 0)\n", 1),
    # ⑥ 右上角齿轮按钮图标
    ("    gear.__icon = gear:CreateTexture(nil, \"ARTWORK\")\n"
     "    gear.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "    gear.__icon:SetSize(14, 14)\n"
     "    gear.__icon:SetPoint(\"CENTER\", gear, \"CENTER\", 0, 0)\n",

     "    gear.__iconTile, gear.__icon = ns.hui.IconTile(gear, 14, 14)\n"
     "    gear.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "    gear.__iconTile:SetPoint(\"CENTER\", gear, \"CENTER\", 0, 0)\n", 1),
    # ⑦ 材料格图标
    ("    b.ic = r:CreateTexture(nil, \"ARTWORK\")\n"
     "    b.ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "    b.ic:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n",

     "    b.icTile, b.ic = ns.hui.IconTile(r, PD.TBL_ICON, PD.TBL_ICON)\n"
     "    b.ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n", 1),
    ("        b.ic:ClearAllPoints()\n"
     "        b.ic:SetPoint(\"RIGHT\", r, \"RIGHT\", -(PD.COL_LW - right), 0)\n",

     "        b.icTile:ClearAllPoints()\n"
     "        b.icTile:SetPoint(\"RIGHT\", r, \"RIGHT\", -(PD.COL_LW - right), 0)\n", 1),
])

E("Core/BisUI.lua", [
    # ① 部位卡片图标
    ("    c.icon = c:CreateTexture(nil, \"ARTWORK\")\n"
     "    c.icon:SetSize(26, 26)\n"
     "    c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n",

     "    c.iconTile, c.icon = ns.hui.IconTile(c, 26, 26)\n"
     "    c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n", 1),
    ("        c.icon:SetPoint(\"TOPLEFT\", c, \"TOPLEFT\", 6, -16)\n"
     "        c.name:SetPoint(\"LEFT\", c.icon, \"RIGHT\", 6, 0)\n",

     "        c.iconTile:SetPoint(\"TOPLEFT\", c, \"TOPLEFT\", 6, -16)\n"
     "        c.name:SetPoint(\"LEFT\", c.iconTile, \"RIGHT\", 6, 0)\n", 1),
    ("        c.icon:SetPoint(\"TOPRIGHT\", c, \"TOPRIGHT\", -6, -16)\n"
     "        c.name:SetPoint(\"RIGHT\", c.icon, \"LEFT\", -6, 0)\n",

     "        c.iconTile:SetPoint(\"TOPRIGHT\", c, \"TOPRIGHT\", -6, -16)\n"
     "        c.name:SetPoint(\"RIGHT\", c.iconTile, \"LEFT\", -6, 0)\n", 1),
    # ② 装等区间列表行图标
    ("        r.icon = r:CreateTexture(nil, \"ARTWORK\")\n"
     "        r.icon:SetSize(30, 30)\n"
     "        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        r.icon:SetPoint(\"LEFT\", r, \"LEFT\", 6, 0)\n",

     "        r.iconTile, r.icon = ns.hui.IconTile(r, 30, 30)\n"
     "        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        r.iconTile:SetPoint(\"LEFT\", r, \"LEFT\", 6, 0)\n", 1),
])

E("Core/ExploreUI.lua", [
    # ① 清单行图标
    ("    r.icon = r:CreateTexture(nil, \"ARTWORK\")\n"
     "    r.icon:SetSize(EG.ICON, EG.ICON)\n"
     "    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "    r.icon:SetPoint(\"LEFT\", r, \"LEFT\", 8 + EG.CHK + 8, 0)\n",

     "    r.iconTile, r.icon = ns.hui.IconTile(r, EG.ICON, EG.ICON)\n"
     "    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "    r.iconTile:SetPoint(\"LEFT\", r, \"LEFT\", 8 + EG.CHK + 8, 0)\n", 1),
    # ② 三个左侧导航按钮图标（40本书 / 背包 / 战斗法师）—— 三段写法完全相同
    ("        bt.__icon = bt:CreateTexture(nil, \"ARTWORK\")\n"
     "        bt.__icon:SetSize(EG.NAV_ICON, EG.NAV_ICON)\n"
     "        bt.__icon:SetPoint(\"LEFT\", bt, \"LEFT\", 5, 0)\n"
     "        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n",

     "        bt.__iconTile, bt.__icon = ns.hui.IconTile(bt, EG.NAV_ICON, EG.NAV_ICON)\n"
     "        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        bt.__iconTile:SetPoint(\"LEFT\", bt, \"LEFT\", 5, 0)\n", 3),
    # ③ 奖励行图标
    ("                row.icon = row:CreateTexture(nil, \"ARTWORK\")\n"
     "                row.icon:SetSize(26, 26)\n"
     "                row.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "                row.icon:SetPoint(\"LEFT\", row, \"LEFT\", 8, 0)\n",

     "                row.iconTile, row.icon = ns.hui.IconTile(row, 26, 26)\n"
     "                row.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "                row.iconTile:SetPoint(\"LEFT\", row, \"LEFT\", 8, 0)\n", 1),
    # ④ 背包清单条目图标
    ("            local ic = nb:CreateTexture(nil, \"ARTWORK\")\n"
     "            ic:SetSize(18, 18)\n"
     "            ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            ic:SetPoint(\"LEFT\", nb, \"LEFT\", 0, 0)\n",

     "            local icTile, ic = ns.hui.IconTile(nb, 18, 18)\n"
     "            ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            icTile:SetPoint(\"LEFT\", nb, \"LEFT\", 0, 0)\n", 1),
    # ⑤ 收藏首件卡片大图标
    ("        local fIcon = fcard:CreateTexture(nil, \"ARTWORK\")\n"
     "        fIcon:SetSize(36, 36)\n"
     "        fIcon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        fIcon:SetPoint(\"TOPLEFT\", fcard, \"TOPLEFT\", 10, -10)\n",

     "        local fIconTile, fIcon = ns.hui.IconTile(fcard, 36, 36)\n"
     "        fIcon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "        fIconTile:SetPoint(\"TOPLEFT\", fcard, \"TOPLEFT\", 10, -10)\n", 1),
    # ⑥ 收藏筛选 chip 图标
    ("            c.icon = c:CreateTexture(nil, \"ARTWORK\")\n"
     "            c.icon:SetSize(24, 24)\n"
     "            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            c.icon:SetPoint(\"LEFT\", c, \"LEFT\", 4, 0)\n",

     "            c.iconTile, c.icon = ns.hui.IconTile(c, 24, 24)\n"
     "            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            c.iconTile:SetPoint(\"LEFT\", c, \"LEFT\", 4, 0)\n", 1),
    # ⑦ 收藏链节点图标
    ("            nd.icon = nd:CreateTexture(nil, \"ARTWORK\")\n"
     "            nd.icon:SetSize(20, 20)\n"
     "            nd.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            nd.icon:SetPoint(\"TOPLEFT\", nd, \"TOPLEFT\", 6, -7)\n",

     "            nd.iconTile, nd.icon = ns.hui.IconTile(nd, 20, 20)\n"
     "            nd.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            nd.iconTile:SetPoint(\"TOPLEFT\", nd, \"TOPLEFT\", 6, -7)\n", 1),
    # ⑧ 战斗法师套装行图标
    ("            rw.icon = rw:CreateTexture(nil, \"ARTWORK\")\n"
     "            rw.icon:SetSize(18, 18)\n"
     "            rw.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            rw.icon:SetPoint(\"LEFT\", rw, \"LEFT\", 0, 0)\n",

     "            rw.iconTile, rw.icon = ns.hui.IconTile(rw, 18, 18)\n"
     "            rw.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            rw.iconTile:SetPoint(\"LEFT\", rw, \"LEFT\", 0, 0)\n", 1),
    # ⑨ 战斗法师兑换行图标
    ("            rw2.icon = rw2:CreateTexture(nil, \"ARTWORK\")\n"
     "            rw2.icon:SetSize(20, 20)\n"
     "            rw2.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            rw2.icon:SetPoint(\"LEFT\", rw2, \"LEFT\", 8, 0)\n",

     "            rw2.iconTile, rw2.icon = ns.hui.IconTile(rw2, 20, 20)\n"
     "            rw2.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            rw2.iconTile:SetPoint(\"LEFT\", rw2, \"LEFT\", 8, 0)\n", 1),
])

E("Core/DungeonUI.lua", [
    # ① 掉落卡片图标
    ("            r.icon = r:CreateTexture(nil, \"ARTWORK\")\n"
     "            r.icon:SetSize(DG.LOOT_ICON, DG.LOOT_ICON)\n"
     "            r.icon:SetPoint(\"LEFT\", r, \"LEFT\", 6, 0)\n"
     "            r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n",

     "            r.iconTile, r.icon = ns.hui.IconTile(r, DG.LOOT_ICON, DG.LOOT_ICON)\n"
     "            r.iconTile:SetPoint(\"LEFT\", r, \"LEFT\", 6, 0)\n"
     "            r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n", 1),
    # ② 任务详情奖励图标
    ("            r.icon = r:CreateTexture(nil, \"ARTWORK\")\n"
     "            r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            r.icon:SetSize(DG.Q_DET_ICON, DG.Q_DET_ICON)\n"
     "            r.icon:SetPoint(\"LEFT\", r, \"LEFT\", 2, 0)\n"
     "            r.name = MakeFS(r, DG.Q_FS_DET, C_TEXT, \"LEFT\")\n"
     "            r.name:SetPoint(\"LEFT\", r.icon, \"RIGHT\", 6, 0)\n",

     "            r.iconTile, r.icon = ns.hui.IconTile(r, DG.Q_DET_ICON, DG.Q_DET_ICON)\n"
     "            r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "            r.iconTile:SetPoint(\"LEFT\", r, \"LEFT\", 2, 0)\n"
     "            r.name = MakeFS(r, DG.Q_FS_DET, C_TEXT, \"LEFT\")\n"
     "            r.name:SetPoint(\"LEFT\", r.iconTile, \"RIGHT\", 6, 0)\n", 1),
])

E("Core/LootFilterUI.lua", [
    # 图标按钮：帧本身就 size×size，贴图 SetAllPoints 到帧 => 直接挂蒙版即可
    ("    bt.tex = bt:CreateTexture(nil, \"ARTWORK\")\n"
     "    bt.tex:SetAllPoints()\n"
     "    bt.tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n",

     "    bt.tex = bt:CreateTexture(nil, \"ARTWORK\")\n"
     "    bt.tex:SetAllPoints()\n"
     "    bt.tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
     "    -- 按钮帧本身就是 size×size（贴图 SetAllPoints 到帧），圆角蒙版按父帧裁正好落在图标四角。\n"
     "    -- 注意：本页另有一个「翻页箭头按钮」也叫 bt.tex，但那是 arrow.tga 四角旋转，不能圆角。\n"
     "    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.tex) end\n", 1),
])


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    eol = "\r\n" if b"\r\n" in raw else "\n"
    txt = raw.decode("utf-8")
    if eol == "\r\n":
        assert "\n" not in txt.replace("\r\n", ""), "混合行尾: " + path
        txt = txt.replace("\r\n", "\n")
    return txt, eol


def write_text(path, txt, eol):
    out = txt.replace("\n", eol) if eol == "\r\n" else txt
    with open(path, "wb") as f:
        f.write(out.encode("utf-8"))


def main():
    total = 0
    for rel, pairs in EDITS:
        path = os.path.join(ROOT, rel)
        txt, eol = read_text(path)
        for old, new, want in pairs:
            got = txt.count(old)
            if got == 0 and txt.count(new) >= 1:
                print("[SKIP] %s 已打过（锚点已变新形态）" % rel)
                continue
            if got != want:
                print("[FAIL] %s 期望 %d 处命中，实际 %d 处" % (rel, want, got))
                print("       old >>>")
                print("       " + old.replace("\n", "\n       "))
                sys.exit(1)
            txt = txt.replace(old, new)
            total += got
            print("[ OK ] %s x%d" % (rel, got))
        write_text(path, txt, eol)
    print("---- 共改写 %d 处 ----" % total)


if __name__ == "__main__":
    main()

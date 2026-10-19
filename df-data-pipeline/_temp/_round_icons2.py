# -*- coding: utf-8 -*-
"""全仓图标「倒圆角」统一补丁 · v2（幂等）。

★ v1 的错路（`_round_icons.py`，2026-09-30 该轮）：给每个图标套一层「与图标等大」的帧
  （ns.hui.IconTile）。行是能走通，但**每行多一个帧** ⇒ 动态 harness 里所有「新建帧计数」
  「材料块不是帧」「图标尺寸」类断言集体变红，代价过大。

★ v2 的正解：病根不在「帧」而在 **RoundIcon 把蒙版挂到了父帧**：
      mask:SetAllPoints(tex:GetParent())
  父帧（行 / 卡片 / 按钮）远大于图标时，圆角落在父帧四角 ⇒ 图标看着就是方的。
  官方 XML 的做法是把 MaskTexture 锚到**兄弟贴图**上：
      Blizzard_AzeriteEssenceUI.xml  CircleMask: TOPLEFT/BOTTOMRIGHT relativeKey="$parent.Icon"
      Blizzard_ActionBar/ActionButtonTemplate.xml  IconMask: CENTER relativeKey="$parent.icon"
  ⇒ 改一行 `mask:SetAllPoints(tex)` 即全仓生效，零新增帧。

本脚本：
  A) 回滚 v1 的全部改动（把 v1 的 new 换回 old）；
  B) RoundIcon 的蒙版锚点改成贴图（+ 说明），并修正 QuickBar/TierUI/RaidUI 里
     「蒙版按父帧裁」的过时注释；
  C) 在 21 处图标 UV 行后补 `RoundIcon(贴图)` 调用。

行尾：Hui.lua / DungeonUI.lua 为 CRLF，其余 LF —— 逐文件探测后原样还原。
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('ri1', os.path.join(HERE, '_round_icons.py'))
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)
ROOT = v1.ROOT


def read_text(path):
    return v1.read_text(path)


def write_text(path, txt, eol):
    v1.write_text(path, txt, eol)


# ---------------- B) 蒙版锚点 + 过时注释 ----------------
EDITS_B = [
    ("Core/Hui.lua", [
        # ① 蒙版改锚贴图（★ 锚点必须带第三行：RoundImage 里也有同两行，只是 Texture 换 HUIRoundImageMask）
        ("        local mask = f:CreateMaskTexture(nil, \"OVERLAY\")\n"
         "        mask:SetAllPoints(f)\n"
         "        mask:SetTexture(\"Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundRectMask\",\n",

         "        local mask = f:CreateMaskTexture(nil, \"OVERLAY\")\n"
         "        -- ★★ 蒙版必须按**贴图**的尺寸裁，不是父帧的尺寸。\n"
         "        --    图标贴在「行 / 卡片 / 按钮」上时父帧远大于图标 —— 蒙版挂父帧的话圆角落在父帧四个角上，\n"
         "        --    图标看上去就是「没倒圆角」（用户 2026-09-30 实机截图报的正是这个）。\n"
         "        --    锚到贴图与官方 XML 同构（Blizzard_AzeriteEssenceUI 的 CircleMask 用\n"
         "        --    TOPLEFT / BOTTOMRIGHT 锚 relativeKey=\"$parent.Icon\"；动作条 IconMask 用 CENTER）。\n"
         "        mask:SetAllPoints(tex)\n"
         "        mask:SetTexture(\"Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundRectMask\",\n", 1),
    ]),
    ("Core/QuickBar.lua", [
        ("    -- 专业图标：单独一层「与图标等大」的帧 —— RoundIcon 的圆角蒙版按**父帧**尺寸裁，\n"
         "    -- 父帧比图标大就会裁错角（同 TierUI 的 MakeIconTile）。\n",

         "    -- 专业图标：单独一层帧，便于随条目一起 SetShown（wantIcon 分支）。\n"
         "    -- ★ 2026-09-30 起 RoundIcon 的圆角蒙版改成按**贴图**尺寸裁（锚点从父帧挪到贴图），\n"
         "    --   这层「等大帧」已不是必需 —— 保留只为和 TierUI 的 MakeIconTile 同构。\n", 1),
    ]),
    ("Core/TierUI.lua", [
        ("-- ★ 为什么必须单独套一层帧：ns.hui.RoundIcon 把圆角蒙版挂在「图标的父帧」上\n"
         "--   （mask:SetAllPoints(父帧)），父帧若比图标大，蒙版圆角就对不上图标角 —— 等于没裁。\n"
         "--   所以图标尺寸 = 帧尺寸 = 蒙版尺寸，三者同源。\n",

         "-- ★ 单独套一层帧：2026-09-30 之前 ns.hui.RoundIcon 把蒙版挂在「父帧」上\n"
         "--   （mask:SetAllPoints(父帧)），父帧比图标大就对不上角；现在蒙版改按**贴图**尺寸裁\n"
         "--   （mask:SetAllPoints(tex)），这层帧已非必需，保留只为「帧尺寸 = 图标尺寸」同源好读。\n", 1),
    ]),
    ("Core/RaidUI.lua", [
        ("    -- 职业徽记：遮罩是 SetAllPoints 到「贴图的宿主」上的，宿主必须恰好等于图标尺寸\n",

         "    -- 职业徽记：蒙版由 RoundIcon 按**贴图**尺寸裁（mask:SetAllPoints(tex)）；帧与图标等大即可\n", 1),
    ]),
    ("Core/LootFilterUI.lua", [
        ("    bt.tex = bt:CreateTexture(nil, \"ARTWORK\")\n"
         "    bt.tex:SetAllPoints()\n"
         "    bt.tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n",

         "    bt.tex = bt:CreateTexture(nil, \"ARTWORK\")\n"
         "    bt.tex:SetAllPoints()\n"
         "    bt.tex:SetTexCoord(0.07, 0.93, 0.07, 0.93)\n"
         "    -- 图标按钮倒圆角（蒙版按贴图尺寸裁）。★ 本页另有一个「翻页箭头按钮」也叫 bt.tex，\n"
         "    --   那是 arrow.tga 的四角旋转坐标，不能圆角 —— 所以只在 MakeIconButton 里挂。\n"
         "    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(bt.tex) end\n", 1),
    ]),
]

# ---------------- C) 图标 UV 行后补 RoundIcon ----------------
# (文件, 原 UV 行（含缩进）, 期望命中次数)
INSERTS = [
    ("Core/ProfessionUI.lua", '    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 列表行
    ("Core/ProfessionUI.lua", '        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 职业版对照表行
    ("Core/ProfessionUI.lua", '            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 总览卡片
    ("Core/ProfessionUI.lua", '        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 左列导航
    ("Core/ProfessionUI.lua", '    gear.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 设置齿轮
    ("Core/ProfessionUI.lua", '    b.ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 材料格
    ("Core/BisUI.lua", '    c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 部位卡片
    ("Core/BisUI.lua", '        r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 装备清单行
    ("Core/ExploreUI.lua", '    r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 收集清单行
    ("Core/ExploreUI.lua", '        bt.__icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 3),   # 三个导航
    ("Core/ExploreUI.lua", '                row.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 奖励行
    ("Core/ExploreUI.lua", '            ic:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 背包清单
    ("Core/ExploreUI.lua", '        fIcon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 收藏首件
    ("Core/ExploreUI.lua", '            c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 收藏 chip
    ("Core/ExploreUI.lua", '            nd.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 收藏链节点
    ("Core/ExploreUI.lua", '            rw.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 套装行
    ("Core/ExploreUI.lua", '            rw2.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 1),   # 兑换行
    ("Core/DungeonUI.lua", '            r.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)', 2),   # 掉落卡 + 任务奖励
]


def main():
    changed = 0

    # ---- A) 回滚 v1 ----
    print('== A) 回滚 v1 的「等大帧瓦片」改动 ==')
    for rel, pairs in v1.EDITS:
        path = os.path.join(ROOT, rel)
        txt, eol = read_text(path)
        for old, new, want in pairs:
            got = txt.count(new)
            if got == 0:
                # ★ 幂等：v1 的 new 不在了 = 已经回滚过。**别再去看 old 在不在** ——
                #   本脚本 C 段会在旧 UV 行后插一行 RoundIcon，正好把 v1 某些 old 片段打断，
                #   再要求 old 命中就会误报 FAIL（2026-09-30 踩到）。
                print('[SKIP] %s 已是 v1 之前的样子' % rel)
                continue
            if got != want:
                print('[FAIL] 回滚 %s 期望 %d 处，实际 %d 处' % (rel, want, got))
                sys.exit(1)
            txt = txt.replace(new, old)
            changed += got
            print('[ 回滚] %s x%d' % (rel, got))
        write_text(path, txt, eol)

    # ---- B) 蒙版锚点 + 注释 ----
    print('== B) RoundIcon 蒙版改锚贴图 + 修正过时注释 ==')
    for rel, pairs in EDITS_B:
        path = os.path.join(ROOT, rel)
        txt, eol = read_text(path)
        for old, new, want in pairs:
            got = txt.count(old)
            # ★ 幂等必须先判 new 在不在：有几对的 old 是 new 的**前缀**（如 LootFilterUI 的
            #   3 行 UV 块 = new 的开头 3 行），改完 old 依然命中 → 只判 got==0 会重复插入。
            if txt.count(new) >= 1:
                print('[SKIP] %s 已改过' % rel)
                continue
            if got != want:
                print('[FAIL] %s 期望 %d 处，实际 %d 处' % (rel, want, got))
                sys.exit(1)
            txt = txt.replace(old, new)
            changed += got
            print('[  OK ] %s x%d' % (rel, got))
        write_text(path, txt, eol)

    # ---- C) 图标 UV 行后补 RoundIcon ----
    print('== C) 补 RoundIcon 调用 ==')
    for rel, tgt, want in INSERTS:
        path = os.path.join(ROOT, rel)
        txt, eol = read_text(path)
        ind = tgt[:len(tgt) - len(tgt.lstrip())]
        tex = tgt.strip().split(':SetTexCoord')[0]
        # ★ 必须带前导换行 —— 否则 8 空格缩进的那行会把 4 空格缩进当子串命中（缩进就不算数了）
        key = '\n' + tgt
        rep = '\n' + tgt + '\n' + ind + 'if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(%s) end' % tex
        got = txt.count(key)
        if got == 0:
            print('[SKIP] %s %r 没找到' % (rel, tex))
            continue
        # 已经补过的别再补
        if txt.count(rep) >= want:
            print('[SKIP] %s %s 已补过' % (rel, tex))
            continue
        if got != want:
            print('[FAIL] %s %r 期望 %d 处，实际 %d 处' % (rel, tex, want, got))
            sys.exit(1)
        txt = txt.replace(key, rep)
        changed += got
        print('[  OK ] %s %s x%d' % (rel, tex, got))
        write_text(path, txt, eol)

    print('---- 共改写 %d 处 ----' % changed)


if __name__ == '__main__':
    main()

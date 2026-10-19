# -*- coding: utf-8 -*-
"""给「详情页三张卡片可折叠」补 harness：静态断言 + 动态断言 + 变异（含旧锚点跟随重构）。

产物两个：
  _temp/df_dungeon_check.py   —— 改 1 条旧静态断言（卡高公式长了折叠开关）+ 新增 5 条静态 + 1 段动态
  _temp/df_mut_check.py       —— MUT_SKILL_TITLE_GONE 换锚（标题改由 LayoutCardHead 统一摆）+ 新增 6 条变异

用法：python patch_card_collapse_harness.py --check 只体检；不带参数落盘。
"""
import sys

CHK = '_temp/df_dungeon_check.py'
MUT = '_temp/df_mut_check.py'

# ── ① df_dungeon_check.py：旧静态断言跟随重构（卡高公式 / 标题锚点） ──────────────
OLD_H = """ck('★★ ㊳ 三张卡片先按内容定高再自上而下摆；掉落行宽 = innerW − 2×BLK_PAD（卡内左缩 BLK_PAD）',
   'local ltH = M.BLK_HDR + ltContentH + M.BLK_PAD' in _mui3_src
   and 'local skH = M.BLK_HDR + skContentH + M.BLK_PAD' in _mui3_src
   and 'local gdH = M.BLK_HDR + gdTextH + M.BLK_PAD' in _mui3_src
   and 'local rowW = frame.detChildW or (frame.innerW - M.BLK_PAD * 2)' in _mui3_src
   and 'r:SetPoint("TOPLEFT", r:GetParent(), "TOPLEFT", M.BLK_PAD, y)' in _mui3_src)"""

NEW_H = r"""ck('★★ ㊳ 三张卡片先按内容定高再自上而下摆（★ 折叠开关就长在这三条公式上）；掉落行宽 = innerW − 2×BLK_PAD',
   'local ltH = closed.loot and M.BLK_MIN_H or (M.BLK_HDR + ltContentH + M.BLK_PAD)' in _mui3_src
   and 'local skH = closed.skill and M.BLK_MIN_H or (M.BLK_HDR + skContentH + M.BLK_PAD)' in _mui3_src
   and 'local gdH = closed.guide and M.BLK_MIN_H or (M.BLK_HDR + gdTextH + M.BLK_PAD)' in _mui3_src
   and 'local rowW = frame.detChildW or (frame.innerW - M.BLK_PAD * 2)' in _mui3_src
   and 'r:SetPoint("TOPLEFT", r:GetParent(), "TOPLEFT", M.BLK_PAD, y)' in _mui3_src)"""

# 追加的静态断言：挂在「图标左沿取齐」那条之后
OLD_TAIL = r"""ck('★★ ㊳ 图标左沿取齐：掉落行与技能行同在「卡片左沿 + BLK_PAD + 6」上（一致性不靠肉眼）',
   'r:SetPoint("TOPLEFT", blkSkill, "TOPLEFT", M.BLK_PAD + 6, by)' in _mui3_src)"""

NEW_TAIL = r"""ck('★★ ㊳ 图标左沿取齐：掉落行与技能行同在「卡片左沿 + BLK_PAD + 6」上（一致性不靠肉眼）',
   'r:SetPoint("TOPLEFT", blkSkill, "TOPLEFT", M.BLK_PAD + 6, by)' in _mui3_src)

# ---- ㊳b 三张卡片展开 / 折叠（2026-10-01 用户：「这三张卡片呢，我希望都可以支持展开和折叠的」）----
ck('★★★ ㊳b 折叠后只留一行卡头：卡高常量与卡头高同源（M.BLK_MIN_H = M.BLK_HDR，不写第二个 26）',
   'M.BLK_MIN_H = M.BLK_HDR' in _mui3_src
   and 'M.BLK_TITLE_X = 24' in _mui3_src
   and 'M.BLK_ARROW = 10' in _mui3_src)
ck('★★★ ㊳b 卡头热区：三张卡各一条可点按钮（宽随卡两条锚点 + 高 = 一行卡头），点它收起 / 展开并落配置',
   'b.hit = CreateFrame("Button", nil, b)' in _mui3_src
   and 'b.hit:SetHeight(M.BLK_MIN_H)' in _mui3_src
   and 'blk.hit:SetPoint("TOPLEFT", blk, "TOPLEFT", 0, 0)' in _mui3_src
   and 'blk.hit:SetPoint("RIGHT", blk, "RIGHT", 0, 0)' in _mui3_src
   and 'blkLoot.__key, blkSkill.__key, blkGuide.__key = "loot", "skill", "guide"' in _mui3_src
   and 'local c = M.CardClosed()' in _mui3_src
   and 'c[key] = not c[key] or nil' in _mui3_src
   and 'ns.PlaySound(1)' in _mui3_src)
ck('★★ ㊳b 折叠状态存配置（DB().ui.mapCards 缺档整档补齐；读侧「非 true 即展开」⇒ 老存档照样三张全展开）',
   'local c = ui.mapCards' in _mui3_src
   and 'if type(c) ~= "table" then c = {} ui.mapCards = c end' in _mui3_src
   and 'function M.CardClosed()' in _mui3_src)
ck('★★ ㊳b 箭头两态互斥（arrow.tga 原生朝上：▾ 展开中 / ▴ 收起中）+ 标题让出箭头位',
   'blk.arrD:SetShown(not isClosed)' in _mui3_src
   and 'blk.arrU:SetShown(isClosed)' in _mui3_src
   and 'ttl:SetPoint("TOPLEFT", blk, "TOPLEFT", M.BLK_TITLE_X, -M.BLK_TITLE_TOP)' in _mui3_src
   and 'Media\\\\textures\\\\arrow.tga' in _mui3_src)
ck('★★ ㊳b 卡头热区把滚轮转发给详情滚动条（EnableMouse 的按钮不转发 ⇒ 鼠标压在卡头上整页滚不动）',
   'b.hit:EnableMouseWheel(true)' in _mui3_src
   and 'M.WheelScroll(detScroll, detChild, delta)' in _mui3_src)
ck('★★ ㊳b 收起 = 一条不摆 + 尾循环从 1 起把所有行收回池里（含上一轮显示过的，别留残影）',
   'for i = 1, (closed.loot and 0 or nLoot) do' in _mui3_src
   and 'for i = (closed.loot and 1 or nLoot + 1), M.MAX_LOOT do frame.lootRows[i]:Hide() end' in _mui3_src
   and 'for i = 1, (closed.skill and 0 or nSk) do' in _mui3_src
   and 'for i = (closed.skill and 1 or nSk + 1), M.MAX_SKILL do' in _mui3_src
   and 'frame.detLtNote:SetShown(nLoot == 0 and not closed.loot)' in _mui3_src
   and 'if closed.guide then' in _mui3_src)"""

# ── ② 动态断言：挂在 15496 回归块之后 ──────────────────────────────────────────
OLD_DYN_TAIL = """        GetSpellTexture = _oGT
        _M._spellCache[15496] = nil
        U.dungeonMapFrame.pinBtns[1].__scripts.OnClick(U.dungeonMapFrame.pinBtns[1])
      end
"""

NEW_DYN_TAIL = r"""        GetSpellTexture = _oGT
        _M._spellCache[15496] = nil
        U.dungeonMapFrame.pinBtns[1].__scripts.OnClick(U.dungeonMapFrame.pinBtns[1])
      end
      -- ★★ 三张卡片展开 / 折叠（2026-10-01 用户：「这三张卡片呢，我希望都可以支持展开和折叠的」）：
      --   点整条卡头收起 / 展开、收起后卡只剩一行卡头且下方卡片跟着上移、状态落配置。
      do
        U:ShowDungeonDetail(_rfc3)
        U:SetDungeonTab("map")
        local _fr = U.dungeonMapFrame
        local _mc = TF_NS.DB().ui.mapCards
        ck("★★ 折叠位默认全空（非 true 即展开 ⇒ 新档与老存档都是三张全展开）",
           _mc ~= nil and _mc.loot == nil and _mc.skill == nil and _mc.guide == nil,
           tostring(_mc and _mc.loot) .. "/" .. tostring(_mc and _mc.skill)
           .. "/" .. tostring(_mc and _mc.guide))
        -- 选一个「掉落 ≥3 件 + 技能卡 + 攻略卡」都在的 boss（缺一样就会有断言白测）
        _M.ShowList()
        local _sel
        for _i = 1, _M.MAX_PINS do
          local _p = _fr.pinBtns[_i]
          if _p.__shown and _p.__en then
            _p.__scripts.OnClick(_p)
            local _n = 0
            for _j = 1, _M.MAX_LOOT do
              if _fr.lootRows[_j].__shown then _n = _n + 1 end
            end
            if _n >= 3 and _fr.blkSkill.__shown == true and _fr.blkGuide.__shown == true then
              _sel = _p.__en
              break
            end
          end
        end
        ck("★★ 折叠用例选到一个「掉落 ≥3 件 + 技能卡 + 攻略卡」都在的 boss（否则下面几条全是白测）",
           _sel ~= nil, tostring(_sel))
        if _sel then
          ck("★★ 展开态：三张卡都亮、箭头朝下 ▾（收起箭头不亮）、卡高都大于一行卡头",
             _fr.blkLoot.__shown == true and _fr.blkSkill.__shown == true
             and _fr.blkGuide.__shown == true
             and _fr.blkLoot.arrD.__shown == true and _fr.blkLoot.arrU.__shown == false
             and _fr.blkLoot.__h > _M.BLK_MIN_H and _fr.blkSkill.__h > _M.BLK_MIN_H
             and _fr.blkGuide.__h > _M.BLK_MIN_H,
             tostring(_fr.blkLoot.__h) .. "/" .. tostring(_fr.blkSkill.__h)
             .. "/" .. tostring(_fr.blkGuide.__h))
          local _n0, _y0, _f0 = 0, (_fr.blkSkill.__pts or {})[5], FRAMES
          for _j = 1, _M.MAX_LOOT do if _fr.lootRows[_j].__shown then _n0 = _n0 + 1 end end
          _fr.blkLoot.hit.__scripts.OnClick(_fr.blkLoot.hit)
          local _n1, _n2 = 0, 0
          for _j = 1, _M.MAX_LOOT do
            if _fr.lootRows[_j].__shown then _n1 = _n1 + 1 end
            if _fr.lootRows[_j].__sid then _n2 = _n2 + 1 end
          end
          ck("★★ 点掉落卡头 → 卡高缩到一行卡头（M.BLK_MIN_H = 卡头高）",
             _fr.blkLoot.__h == _M.BLK_MIN_H, tostring(_fr.blkLoot.__h))
          ck("★★ 收起后掉落行全收回池里（展开 " .. _n0 .. " 条 → 0 条）",
             _n0 > 0 and _n1 == 0, _n1)
          ck("★★ 收起后箭头翻面（▾ 灭 / ▴ 亮）—— 展开收起一眼看得出",
             _fr.blkLoot.arrU.__shown == true and _fr.blkLoot.arrD.__shown == false,
             tostring(_fr.blkLoot.arrD.__shown) .. "/" .. tostring(_fr.blkLoot.arrU.__shown))
          local _y1 = (_fr.blkSkill.__pts or {})[5]
          ck("★★ 收起后下方卡片跟着上移（技能卡的 y 变浅，让出的正是「展开高 − 一行卡头」）",
             type(_y0) == "number" and type(_y1) == "number" and _y1 > _y0,
             tostring(_y0) .. " → " .. tostring(_y1))
          ck("★★ 收起状态落配置（DB().ui.mapCards.loot == true ⇒ 换 boss / 重开界面都还收着）",
             TF_NS.DB().ui.mapCards.loot == true)
          ck("★ 收起是纯显隐：零新建帧（不重建任何池）", FRAMES == _f0, tostring(FRAMES))
          _fr.blkSkill.hit.__scripts.OnClick(_fr.blkSkill.hit)
          ck("★★ 点技能卡头 → 卡高缩到一行卡头、技能行全收、落配置 skill（三张卡同一套机制）",
             _fr.blkSkill.__h == _M.BLK_MIN_H and TF_NS.DB().ui.mapCards.skill == true
             and _fr.skillRows[1].__shown ~= true,
             tostring(_fr.blkSkill.__h) .. "/" .. tostring(_fr.skillRows[1].__shown))
          _fr.blkGuide.hit.__scripts.OnClick(_fr.blkGuide.hit)
          ck("★★ 点攻略卡头 → 卡高缩到一行卡头、正文收起、落配置 guide",
             _fr.blkGuide.__h == _M.BLK_MIN_H and TF_NS.DB().ui.mapCards.guide == true
             and _fr.detGd.__shown ~= true,
             tostring(_fr.blkGuide.__h) .. "/" .. tostring(_fr.detGd.__shown))
          _fr.blkLoot.hit.__scripts.OnClick(_fr.blkLoot.hit)
          _fr.blkSkill.hit.__scripts.OnClick(_fr.blkSkill.hit)
          _fr.blkGuide.hit.__scripts.OnClick(_fr.blkGuide.hit)
          ck("★★ 再点三次全展开 → 三张卡回满、配置三位都清掉（不留 false）",
             _fr.blkLoot.__h > _M.BLK_MIN_H and _fr.blkSkill.__h > _M.BLK_MIN_H
             and _fr.blkGuide.__h > _M.BLK_MIN_H
             and TF_NS.DB().ui.mapCards.loot == nil
             and TF_NS.DB().ui.mapCards.skill == nil
             and TF_NS.DB().ui.mapCards.guide == nil,
             tostring(_fr.blkLoot.__h) .. "/" .. tostring(TF_NS.DB().ui.mapCards.loot))
        end
      end
"""

# ── ③ df_mut_check.py：旧锚点跟随重构 ──────────────────────────────────────────
OLD_MUT_TITLE = r"""MUT_SKILL_TITLE_GONE = ('Core/MapUI.lua', (
    b'                frame.detSkTtl:SetPoint("TOPLEFT", blkSkill, "TOPLEFT", M.BLK_PAD, -M.BLK_TITLE_TOP)\n',
    b'                -- MUT: skill card title anchor dropped (falls to parent center, covered in game)\n'))"""

NEW_MUT_TITLE = r"""MUT_SKILL_TITLE_GONE = ('Core/MapUI.lua', (
    b'    ttl:SetPoint("TOPLEFT", blk, "TOPLEFT", M.BLK_TITLE_X, -M.BLK_TITLE_TOP)\n',
    b'    -- MUT: card title anchor dropped (falls to parent center, covered in game)\n'))
# ── 卡片展开 / 折叠（2026-10-01 用户：「这三张卡片呢，我希望都可以支持展开和折叠的」）──
MUT_CARD_TOGGLE_DEAD = ('Core/MapUI.lua', (
    b'            c[key] = not c[key] or nil\n',
    b'            -- MUT: card header click does nothing (no state, no relayout)\n'))
MUT_CARD_MINH_OFF = ('Core/MapUI.lua', (
    b'            local ltH = closed.loot and M.BLK_MIN_H or (M.BLK_HDR + ltContentH + M.BLK_PAD)\n',
    b'            local ltH = M.BLK_HDR + ltContentH + M.BLK_PAD -- MUT: collapsed card keeps full height\n'))
MUT_CARD_ARROW_STUCK = ('Core/MapUI.lua', (
    b'    blk.arrU:SetShown(isClosed)\n',
    b'    blk.arrU:SetShown(true) -- MUT: collapsed arrow never turns off\n'))
MUT_CARD_ROWS_KEPT = ('Core/MapUI.lua', (
    b'            for i = 1, (closed.loot and 0 or nLoot) do\n',
    b'            for i = 1, nLoot do -- MUT: collapsed card still lays out its rows\n'))
MUT_CARD_GUIDE_KEEP = ('Core/MapUI.lua', (
    b'                if closed.guide then\n',
    b'                if false then -- MUT: collapsed guide card keeps its body visible\n'))
MUT_CARD_WHEEL_OFF = ('Core/MapUI.lua', (
    b'        b.hit:EnableMouseWheel(true)\n',
    b'        b.hit:EnableMouseWheel(false) -- MUT: header hit zone swallows the wheel\n'))"""

OLD_MUT_REG = r"""    ('技能：boss技能 标题被摘（有技能也不显示）', MUT_SKILL_TITLE_GONE),"""

NEW_MUT_REG = r"""    ('技能：boss技能 标题被摘（有技能也不显示）', MUT_SKILL_TITLE_GONE),
    # ㊳b 三张卡片展开 / 折叠（2026-10-01 用户点名）
    ('折叠：点卡头什么都不做（状态不落、卡片不重排）', MUT_CARD_TOGGLE_DEAD),
    ('折叠：掉落卡收起后仍按展开高排（卡不收、下方卡片不上移）', MUT_CARD_MINH_OFF),
    ('折叠：箭头不翻面（收起后 ▾ 与 ▴ 同时亮）', MUT_CARD_ARROW_STUCK),
    ('折叠：收起后条目照旧摆出来（卡里溢出内容）', MUT_CARD_ROWS_KEPT),
    ('折叠：攻略正文不跟着收（卡只有一行高、正文画到卡外）', MUT_CARD_GUIDE_KEEP),
    ('折叠：卡头热区吞掉滚轮（鼠标压在卡头上整页滚不动）', MUT_CARD_WHEEL_OFF),"""

TARGETS = [(CHK, OLD_H, NEW_H), (CHK, OLD_TAIL, NEW_TAIL), (CHK, OLD_DYN_TAIL, NEW_DYN_TAIL),
           (MUT, OLD_MUT_TITLE, NEW_MUT_TITLE), (MUT, OLD_MUT_REG, NEW_MUT_REG)]


def main():
    files = {}
    for path, _o, _n in TARGETS:
        if path not in files:
            files[path] = open(path, encoding='utf-8').read()
    bad = 0
    for path, old, new in TARGETS:
        n = files[path].count(old)
        if n != 1:
            print('[锚点失配] %s ：命中 %d 次' % (path, n))
            print(old[:90].replace('\n', '\\n'))
            bad += 1
            continue
        files[path] = files[path].replace(old, new, 1)
        print('[OK] %s ← %s' % (path, old.split('\n')[0][:70]))
    if bad:
        print('中止：%d 处锚点不匹配' % bad)
        return 2
    if '--check' in sys.argv:
        print('体检通过（未落盘）')
        return 0
    for path, txt in files.items():
        open(path, 'wb').write(txt.encode('utf-8'))
        print('已落盘 %s' % path)
    return 0


if __name__ == '__main__':
    sys.exit(main())

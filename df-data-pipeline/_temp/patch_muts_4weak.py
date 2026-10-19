# -*- coding: utf-8 -*-
"""全量变异对账（2026-10-08 --all 4/377 未守住）补强：
  ① df_mut_check.py：「装备过滤面板：重新塞回覆盖主窗的遮罩」变异本体改成语法合法
     的 Lua（旧变异在 table 构造器里塞语句 ⇒ loadfile nil ⇒ harness 崩、判「注入
     无效」）。合法化后由既有 LFv7 静态闸（读 beta 源）抓住。
  ② df_dungeon_check.py：徽标占位加精确值闸（既有断言只有 ≥ 下限，28→34 变大不红）。
  ③ df_dungeon_check.py：名单并集第三支「有一句话攻略」+ 点 boss 钉点必须刷右栏
     （两条既有弱断言补运行时行为闸）。
幂等：所有锚点断言恰好命中 1 次；已应用则直接退出。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MUT = os.path.join(HERE, 'df_mut_check.py')
CHK = os.path.join(HERE, 'df_dungeon_check.py')


def patch(path, old, new, tag):
    s = open(path, encoding='utf-8').read()
    n = s.count(old)
    assert n == 1, '%s：锚点 %d 次（须恰好 1）' % (tag, n)
    open(path, 'w', encoding='utf-8', newline='').write(s.replace(old, new))
    print('  ✓ %s' % tag)


# ── ① 变异本体合法化 ─────────────────────────────────────────────────────────
OLD_MUT = ("    ('装备过滤面板：重新塞回覆盖主窗的遮罩（面板又变成抢鼠标的弹窗）', "
           "('Core/LootFilterUI.lua', (b'    local cfg = {\\n        popup = popup,\\n"
           "        page = 0,\\n        collapsed = {},\\n', b'    local cfg = "
           "{ popup = popup, page = 0, collapsed = {},\\n    cfg.shield = "
           "CreateFrame(\"Frame\", nil, host)\\n    cfg.shield:SetAllPoints(host)\\n"
           "    cfg.shield:EnableMouse(true)\\n'))),")
NEW_MUT = ("    ('装备过滤面板：重新塞回覆盖主窗的遮罩（面板又变成抢鼠标的弹窗）', "
           "('Core/LootFilterUI.lua', (b'    local cfg = {\\n        popup = popup,\\n"
           "        page = 0,\\n        collapsed = {},\\n        icons = {},\\n"
           "        toggles = {},\\n        cells = {},\\n        headers = {},\\n"
           "    }\\n', b'    local cfg = {\\n        popup = popup,\\n"
           "        page = 0,\\n        collapsed = {},\\n        icons = {},\\n"
           "        toggles = {},\\n        cells = {},\\n        headers = {},\\n"
           "    }\\n    cfg.shield = CreateFrame(\"Frame\", nil, host)\\n"
           "    cfg.shield:SetAllPoints(host)\\n    cfg.shield:EnableMouse(true)\\n'))),")

s = open(MUT, encoding='utf-8').read()
if NEW_MUT in s:
    print('  · ① 变异本体已合法化，跳过')
else:
    patch(MUT, OLD_MUT, NEW_MUT, '① 变异本体合法化（遮罩回潮 → 完整 cfg 表 + 追加 shield 三行）')

# ── ② 徽标占位精确值闸 ───────────────────────────────────────────────────────
OLD_A = ('    ck("★ 徽标占位真的容得下「新」字（≥ 右内边距 + 徽标字宽 + 4）",\n'
         '       DGn.LOOT_TAG_W >= DGn.LOOT_TEXT_R + DGn.LOOT_FS_TAG + 4,\n'
         '       DGn.LOOT_TAG_W .. " vs " .. (DGn.LOOT_TEXT_R + DGn.LOOT_FS_TAG + 4))\n')
NEW_A = (OLD_A
         + '    -- ★★ 2026-10-08 全量对账补强：上一条只有 ≥ 下限，28→34 变大不红（变大吃掉\n'
         + '    --    最长名的名字宽 ⇒ 名字+「新」徽标被裁）。精确值闸把调优定值钉死。\n'
         + '    ck("★ 徽标占位常量 = 28（调优定值；变大吃名字宽，下限由上一条守）",\n'
         + '       DGn.LOOT_TAG_W == 28, tostring(DGn.LOOT_TAG_W))\n')

s = open(CHK, encoding='utf-8').read()
if '徽标占位常量 = 28' in s:
    print('  · ② 徽标占位精确值闸已就位，跳过')
else:
    patch(CHK, OLD_A, NEW_A, '② 徽标占位精确值闸（DGn.LOOT_TAG_W == 28）')

# ── ③ 名单并集第三支 + 钉点点击刷右栏 ────────────────────────────────────────
OLD_B = ('      ck("★★ HasPins 计入扩展钉点：有 boss 钉的副本 true / 无图副本 false / nil false",\n'
         '         _MM.HasPins("ragefire_chasm") == true\n'
         '         and _MM.HasPins("hall_of_thanes") == true\n'
         '         and _MM.HasPins("the_drowned_city") == false\n'
         '         and _MM.HasPins(nil) == false)\n')
NEW_B = (OLD_B
         + '      do  -- ★★ 2026-10-08 全量对账补强：名单并集第三支「有一句话攻略」。\n'
         + '        --   洛丹伦废墟 6 个 boss 没登记 npcid、也没坐标，全凭攻略入选；摘掉\n'
         + '        --   GuideFor 支 ⇒ 6 个 boss 从名单消失、攻略白写（纯数据闸，不依赖当前图）。\n'
         + '        local _g0 = 0\n'
         + '        for _, _b in ipairs(_MM.BossesFor("ruins_of_lordaeron") or {}) do\n'
         + '          if not _MM.PosFor("ruins_of_lordaeron", _b.en)\n'
         + '             and _MM.GuideFor("ruins_of_lordaeron", _b.en) then\n'
         + '            _g0 = _g0 + 1\n'
         + '          end\n'
         + '        end\n'
         + '        ck("★★ 名单并集 = npcid ∪ 坐标 ∪ 攻略（洛丹伦废墟 6 boss 全靠第三支入选）",\n'
         + '           _g0 == 6, _g0)\n'
         + '        -- ★★ 点 boss 钉点必须刷右栏：M.Select 落 detailEn 后必须 SyncSide\n'
         + '        --   （详情态 detBack 亮、列表收）；只记状态不刷 ⇒ 点了没反应。\n'
         + '        --   先 ShowList 归位列表态，排除此前断言残留的选中态干扰。\n'
         + '        local _fr = U.dungeonMapFrame\n'
         + '        local _bt = _fr and _fr.pinBtns and _fr.pinBtns[1]\n'
         + '        if _bt then\n'
         + '          _MM.ShowList()\n'
         + '          pcall(_bt.__scripts.OnClick, _bt)\n'
         + '          ck("★★ 点 boss 钉点 → 右栏切详情态（detBack 亮 + 列表收；只记不刷 = 点了没反应）",\n'
         + '             _MM.detailEn ~= nil and _fr.detBack ~= nil\n'
         + '             and _fr.detBack.__shown == true and _fr.listScroll.__shown == false,\n'
         + '             tostring(_MM.detailEn) .. "/" .. tostring(_fr.detBack\n'
         + '                                                      and _fr.detBack.__shown))\n'
         + '          _MM.ShowList()   -- 还原列表态，别污染后续断言\n'
         + '        end\n'
         + '      end\n')

s = open(CHK, encoding='utf-8').read()
if '名单并集 = npcid ∪ 坐标 ∪ 攻略' in s:
    print('  · ③ 名单并集 + 钉点点击闸已就位，跳过')
else:
    patch(CHK, OLD_B, NEW_B, '③ 名单并集第三支闸 + 钉点点击刷右栏闸')

print('补强完成。')

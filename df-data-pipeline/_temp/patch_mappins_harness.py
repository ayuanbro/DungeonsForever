# -*- coding: utf-8 -*-
"""图钉扩展（入口/任务/物品/稀有）harness 补丁：
1. df_dungeon_check.py
   - 领主大厅自制图钉点 4 → 7（4 boss + 1 入口 + 2 任务）
   - 新增图钉扩展动态断言（ExtraPinsFor / 合并渲染 / 贴图 / 数据抽查 / HasPins / 任务钉点击跳转）
   - bossBtn 文案断言：L["隐藏boss"]/L["显示boss"] → L["隐藏图钉"]/L["显示图钉"]
   - 静态段（㊲ 后）新增 ㊲b 图钉扩展源码 / 数据 / TOC / 贴图 / 三语断言
2. df_mut_check.py 追加 7 条图钉变异
"""
import io, os, sys

TEMP = os.path.dirname(os.path.abspath(__file__))

def rd(p):
    with io.open(p, 'r', encoding='utf-8', newline='') as f:
        return f.read()

def wr(p, s):
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)

def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s：锚点命中 %d 次（应 1）\n---\n%s' % (tag, n, old[:200])
    return src.replace(old, new, 1)

# ------------------------------------------------------------------ harness
p = os.path.join(TEMP, 'df_dungeon_check.py')
s = rd(p)

# 1a. 领主大厅钉点数 4 → 7，并随后插入图钉扩展动态断言块
old_hall = (
    '      ck("★★ 自制手绘图同样画钉点（领主大厅 → 4 颗亮在自制图上；2026-10-01 修：此前拿「有 ART 层」当地图判据，自制图被当无图 ⇒ 钉点全不显）",\n'
    '         U.dungeonMapFrame.pins.__shown == true and _s0p == 4, _s0p)\n'
)
new_hall = (
    '      ck("★★ 自制手绘图同样画钉点（领主大厅 → 7 颗亮在自制图上 = 4 boss + 1 入口 + 2 任务；"\n'
    '         .. "2026-10-01 修：此前拿「有 ART 层」当地图判据，自制图被当无图 ⇒ 钉点全不显）",\n'
    '         U.dungeonMapFrame.pins.__shown == true and _s0p == 7, _s0p)\n'
    '      -- ★★ 2026-10-04 图钉扩展（入口/任务/物品/稀有，ns.MapPins = fc 站钉点生成物）：\n'
    '      --   boss 在前、extras 按 entrance → quest → object → rare 追加（SyncPins 合并口径）。\n'
    '      ck("★★ 图钉扩展：ExtraPinsFor 领主大厅 3 条（1 入口 + 2 任务；floor=nil 不分层 / floor=1 全出 / floor=2 不出）",\n'
    '         #(_MM.ExtraPinsFor("hall_of_thanes", nil) or {}) == 3\n'
    '         and #(_MM.ExtraPinsFor("hall_of_thanes", 1) or {}) == 3\n'
    '         and _MM.ExtraPinsFor("hall_of_thanes", 2) == nil\n'
    '         and _MM.ExtraPinsFor("ragefire_chasm", nil) == nil\n'
    '         and _MM.ExtraPinsFor(nil, nil) == nil)\n'
    '      ck("★★ 图钉扩展合并渲染：领主大厅第 5 颗 = 入口、第 6/7 颗 = 任务（quest id 96395 / 98423）",\n'
    '         U.dungeonMapFrame.pinBtns[5].__kind == "entrance"\n'
    '         and U.dungeonMapFrame.pinBtns[6].__kind == "quest"\n'
    '         and U.dungeonMapFrame.pinBtns[7].__kind == "quest"\n'
    '         and U.dungeonMapFrame.pinBtns[6].__p.id == 96395\n'
    '         and U.dungeonMapFrame.pinBtns[7].__p.id == 98423, _s0p)\n'
    '      ck("★★ 图钉贴图按类型走：任务 = 客户端黄「!」（AvailableQuestIcon，白染色）/ 入口 = 自制石门 MapDoor / boss 仍是骷髅",\n'
    '         tostring(U.dungeonMapFrame.pinBtns[6].dot.__tex or ""):find("AvailableQuestIcon", 1, true) ~= nil\n'
    '         and tostring(U.dungeonMapFrame.pinBtns[5].dot.__tex or ""):find("MapDoor", 1, true) ~= nil\n'
    '         and tostring(U.dungeonMapFrame.pinBtns[1].dot.__tex or ""):find("BossSkull", 1, true) ~= nil)\n'
    '      ck("★★ 图钉扩展数据抽查：影牙 3（2 任务物品 + 1 稀有「死亡之誓」）/ 监狱 4（Bruegal×4，npcID=0）"\n'
    '         .. " / 死矿 1 / 侏儒 1 / 洛丹伦废墟 2（1 入口 + 1 任务）",\n'
    '         #(_MM.ExtraPinsFor("shadowfang_keep", nil) or {}) == 3\n'
    '         and #(_MM.ExtraPinsFor("the_stockade", nil) or {}) == 4\n'
    '         and #(_MM.ExtraPinsFor("the_deadmines", nil) or {}) == 1\n'
    '         and #(_MM.ExtraPinsFor("gnomeregan", nil) or {}) == 1\n'
    '         and #(_MM.ExtraPinsFor("ruins_of_lordaeron", nil) or {}) == 2\n'
    '         and (_MM.ExtraPinsFor("shadowfang_keep", nil) or {})[3].name == "死亡之誓"\n'
    '         and (_MM.ExtraPinsFor("the_stockade", nil) or {})[1].id == 0)\n'
    '      ck("★★ HasPins 计入扩展钉点：有 boss 钉的副本 true / 无图副本 false / nil false",\n'
    '         _MM.HasPins("ragefire_chasm") == true\n'
    '         and _MM.HasPins("hall_of_thanes") == true\n'
    '         and _MM.HasPins("the_drowned_city") == false\n'
    '         and _MM.HasPins(nil) == false)\n'
    '      do  -- 任务钉点击 → 跳详情任务区并选中该任务（用户拍板口径：点了要能到）\n'
    '        local _qs = U.dungeonQuestSel\n'
    '        local _okC = pcall(U.dungeonMapFrame.pinBtns[6].__scripts.OnClick, U.dungeonMapFrame.pinBtns[6])\n'
    '        ck("★★ 点任务钉 → 跳任务页且选中该任务（dungeonTab=quest / dungeonQuestSel=96395）",\n'
    '           _okC == true and U.dungeonTab == "quest" and U.dungeonQuestSel == 96395,\n'
    '           tostring(U.dungeonTab) .. "/" .. tostring(U.dungeonQuestSel))\n'
    '        U.dungeonQuestSel = _qs\n'
    '        U:ShowDungeonDetail(_hall2)\n'
    '        U:SetDungeonTab("map")\n'
    '      end\n'
)
s = rep1(s, old_hall, new_hall, 'hall 钉点断言')

# 1b. bossBtn 文案断言换新键
old_b1 = (
    '        ck("★ 缺省态：文案「隐藏boss」+ 描边未点亮 + 钉点照常 4 颗",\n'
    '           tostring(_bb.__text) == TF_NS.L["隐藏boss"] and not _outlineOn(_bb) and _n0 == 4,\n'
)
new_b1 = (
    '        ck("★ 缺省态：文案「隐藏图钉」+ 描边未点亮 + 钉点照常 4 颗（2026-10-04 改名：开关从藏 boss 扩成藏全部钉点）",\n'
    '           tostring(_bb.__text) == TF_NS.L["隐藏图钉"] and not _outlineOn(_bb) and _n0 == 4,\n'
)
s = rep1(s, old_b1, new_b1, 'bossBtn 缺省态')

old_b2 = (
    '           and tostring(U.dungeonMapFrame.bossBtn.__text) == TF_NS.L["显示boss"],\n'
)
new_b2 = (
    '           and tostring(U.dungeonMapFrame.bossBtn.__text) == TF_NS.L["显示图钉"],\n'
)
s = rep1(s, old_b2, new_b2, 'bossBtn 换副本保持')

old_b3 = (
    '        ck("★★ 再点开关 → 钉点原样回来（4 颗）+ 文案回「隐藏boss」",\n'
    '           _pins(U.dungeonMapFrame) == 4\n'
    '           and tostring(U.dungeonMapFrame.bossBtn.__text) == TF_NS.L["隐藏boss"],\n'
)
new_b3 = (
    '        ck("★★ 再点开关 → 钉点原样回来（4 颗）+ 文案回「隐藏图钉」",\n'
    '           _pins(U.dungeonMapFrame) == 4\n'
    '           and tostring(U.dungeonMapFrame.bossBtn.__text) == TF_NS.L["隐藏图钉"],\n'
)
s = rep1(s, old_b3, new_b3, 'bossBtn 恢复态')

# 1c. 静态段：㊲ 之后插 ㊲b
old_stat = (
    "ck('★★ ㊲ 自制手绘图也画钉点：SyncPins 多一条 CUSTOM 分支（无 ART 层的副本固定第 1 层取点）',\n"
    "   'elseif M.curId and M.CustomFor(M.curId) then' in _mui3_src\n"
    "   and '        list = M.PinsFor(M.curId, 1)\\n' in _mui3_src)\n"
)
new_stat = old_stat + (
    "\n"
    "# ---- ㊲b 图钉扩展（2026-10-04：入口/任务/物品/稀有，ns.MapPins = fc 站钉点）----\n"
    "ck('★★ ㊲b 图钉贴图常量三件：任务 = 客户端黄「!」/ 入口 = 自制 MapDoor / boss = 插件骷髅',\n"
    "   r'M.PIN_QUEST_TEX = \"Interface\\\\GossipFrame\\\\AvailableQuestIcon\"' in _mui3_src\n"
    "   and r'M.PIN_DOOR_TEX = \"Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\MapDoor\"' in _mui3_src\n"
    "   and r'M.PIN_BOSS_TEX = \"Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\BossSkull\"' in _mui3_src)\n"
    "ck('★★ ㊲b ExtraPinsFor：四类按 entrance→quest→object→rare 遍历 + 第 1 层口径 + 扁平结构（kind/left/top/id/name）',\n"
    "   'function M.ExtraPinsFor(id, floor)' in _mui3_src\n"
    "   and '{ \"entrance\", \"quest\", \"object\", \"rare\" }' in _mui3_src\n"
    "   and 'if floor == nil or floor == 1 then' in _mui3_src\n"
    "   and 'kind = kind, left = p[1], top = p[2], id = p[3],' in _mui3_src\n"
    "   and '(kind == \"rare\") and p[4] or nil' in _mui3_src)\n"
    "ck('★★ ㊲b SyncPins 合并扩展钉点（boss 列表之后追加 extras、floor 口径一致）+ 渲染按 kind 分派',\n"
    "   'local ex = M.ExtraPinsFor(M.curId, floor)' in _mui3_src\n"
    "   and 'list[#list + 1] = ex[i]' in _mui3_src\n"
    "   and 'bt.__kind, bt.__p = kind, p' in _mui3_src\n"
    "   and 'local kind = p.kind or \"boss\"' in _mui3_src)\n"
    "ck('★★ ㊲b 贴图分派：任务 PIN_QUEST_TEX / 入口 PIN_DOOR_TEX / 物品 DG.ItemIcon(p.id) / 稀有银染色',\n"
    "   'bt.dot:SetTexture(M.PIN_QUEST_TEX)' in _mui3_src\n"
    "   and 'bt.dot:SetTexture(M.PIN_DOOR_TEX)' in _mui3_src\n"
    "   and 'bt.dot:SetTexture(DG.ItemIcon(p.id))' in _mui3_src\n"
    "   and 'bt.dot:SetVertexColor(0.72, 0.76, 0.85)' in _mui3_src)\n"
    "ck('★★ ㊲b 名字分派：任务名走 DG.QuestName 金色 / 物品名 DG.ItemName / 入口 L[\"副本入口\"] / 稀有 p.name 银色',\n"
    "   'nm = DG.QuestName(p.id)' in _mui3_src\n"
    "   and 'nm = DG.ItemName(p.id)' in _mui3_src\n"
    "   and 'nm = L[\"副本入口\"]' in _mui3_src\n"
    "   and 'nm = p.name or \"\"' in _mui3_src)\n"
    "ck('★★ ㊲b 开关文案改名「隐藏图钉/显示图钉」（口径从藏 boss 扩成藏全部钉点）',\n"
    "   'bt:SetText(off and L[\"显示图钉\"] or L[\"隐藏图钉\"])' in _mui3_src)\n"
    "ck('★★ ㊲b 点击/悬停/移出三件：boss 选中首领、quest 跳任务区并选中（PinOnClick）、object 走 DG.ShowItemTip',\n"
    "   'function M.PinOnClick(self)' in _mui3_src\n"
    "   and 'U.dungeonQuestSel = p.id' in _mui3_src\n"
    "   and 'U:SetDungeonTab(\"quest\")' in _mui3_src\n"
    "   and 'function M.PinOnEnter(self)' in _mui3_src\n"
    "   and 'DG.ShowItemTip(self, { p.id })' in _mui3_src\n"
    "   and 'function M.PinOnLeave()' in _mui3_src)\n"
    "ck('★★ ㊲b HasPins 计入扩展钉点（extras 只作「有没有」判据，与当前层无关）',\n"
    "   'local ex = M.ExtraPinsFor(id, nil)' in _mui3_src\n"
    "   and 'if ex then n = n + #ex end' in _mui3_src)\n"
    "_pins_src = open(os.path.join(ADDON, 'Core', 'Data', 'Data_MapPins.lua'), encoding='utf-8').read()\n"
    "ck('★★ ㊲b Data_MapPins：6 个副本登记齐全 + 关键 ID 抽查（任务 96395/98423/95250、物品 6895/6283、稀有 6228/3586/3872）',\n"
    "   all(('\"[%s\"] = {' % k) in _pins_src for k in\n"
    "       ('gnomeregan', 'hall_of_thanes', 'ruins_of_lordaeron',\n"
    "        'shadowfang_keep', 'the_deadmines', 'the_stockade'))\n"
    "   and all(_pins_src.count(str(_i)) >= 1 for _i in\n"
    "           (96395, 98423, 95250, 6895, 6283, 6228, 3586, 3872)))\n"
    "_toc_pins_txt = open(TOC, encoding='utf-8', errors='replace').read()\n"
    "ck('★★ ㊲b TOC 三处都挂 Data_MapPins.lua（root/zhTW/enUS，与 Data_BossPos 同款三语链）',\n"
    "   _toc_pins_txt.count('Data_MapPins.lua') == 3\n"
    "   and _toc_pins_txt.count('Data_BossPos.lua') == 3)\n"
    "_door_tga = os.path.join(ADDON, 'Media', 'MapDoor.tga')\n"
    "ck('★★ ㊲b Media/MapDoor.tga 在且不超 64KB（入口钉兜底贴图；在 Media 根、不占 Media/Maps 自制地图四张名额）',\n"
    "   os.path.isfile(_door_tga) and 0 < os.path.getsize(_door_tga) <= 64 * 1024,\n"
    "   str(os.path.getsize(_door_tga)) if os.path.isfile(_door_tga) else 'missing')\n"
    "_tw_loc = open(os.path.join(ADDON, 'Locales', 'zhTW.lua'), encoding='utf-8').read()\n"
    "_en_loc = open(os.path.join(ADDON, 'Locales', 'enUS.lua'), encoding='utf-8').read()\n"
    "ck('★★ ㊲b 三语 L 键：隐藏图钉/显示图钉/点击查看任务详情（EN 缺键会拒绝生成，这里再钉一次）',\n"
    "   '隐藏图钉' in _tw_loc and '显示图钉' in _tw_loc and '点击查看任务详情' in _tw_loc\n"
    "   and '隐藏图钉' in _en_loc and '显示图钉' in _en_loc and '点击查看任务详情' in _en_loc)\n"
)
s = rep1(s, old_stat, new_stat, '静态段 ㊲b')
wr(p, s)
print('df_dungeon_check.py 打补丁完成')

# ------------------------------------------------------------------ 变异
p2 = os.path.join(TEMP, 'df_mut_check.py')
m = rd(p2)

def u8(t):
    return t.encode('utf-8')

new_muts = u8('''
    # ㊟ 图钉扩展（2026-10-04：入口/任务/物品/稀有，ns.MapPins）
    ('图钉扩展：SyncPins 丢弃扩展钉点（入口/任务/物品/稀有全消失，只剩 boss）',
     ('Core/MapUI.lua', (
         u8('        local ex = M.ExtraPinsFor(M.curId, floor)\\n'
            '        if ex then\\n'
            '            for i = 1, #ex do\\n'
            '                list = list or {}\\n'
            '                list[#list + 1] = ex[i]\\n'
            '            end\\n'
            '        end\\n'),
         u8('        -- MUT: extra pins dropped\\n')))),
    ('图钉扩展：任务钉点击死了（不选中任务也不跳任务区）',
     ('Core/MapUI.lua', (
         u8('    elseif kind == "quest" and p and p.id then\\n'
            '        U.dungeonQuestSel = p.id\\n'
            '        U:SetDungeonTab("quest")\\n'),
         u8('    elseif kind == "quest" and p and p.id then\\n'
            '        -- MUT: quest pin click dead\\n')))),
    ('图钉扩展：任务钉贴图换成 boss 骷髅（黄「!」没了，类型失明）',
     ('Core/MapUI.lua', (
         u8('            if kind == "quest" then\\n'
            '                bt.dot:SetTexture(M.PIN_QUEST_TEX)\\n'),
         u8('            if kind == "quest" then\\n'
            '                bt.dot:SetTexture(M.PIN_BOSS_TEX) -- MUT: quest pin as skull\\n')))),
    ('图钉扩展：ExtraPinsFor 层判据坏掉（第 1 层不出、第 2 层反出）',
     ('Core/MapUI.lua', (
         u8('                    if floor == nil or floor == 1 then\\n'),
         u8('                    if floor == nil or floor == 2 then -- MUT: floor guard broken\\n')))),
    ('图钉扩展：扩展钉点 kind 丢失（全部落回 entrance 分派，任务钉画成石门）',
     ('Core/MapUI.lua', (
         u8('                        out[#out + 1] = {\\n'
            '                            kind = kind, left = p[1], top = p[2], id = p[3],\\n'),
         u8('                        out[#out + 1] = {\\n'
            '                            kind = "entrance", left = p[1], top = p[2], id = p[3], -- MUT: kind lost\\n')))),
    ('图钉扩展：HasPins 恒真（无钉点副本也出「隐藏图钉」开关）',
     ('Core/MapUI.lua', (
         u8('    return (n > 0) and true or false\\n'),
         u8('    return true -- MUT: HasPins always true\\n')))),
    ('图钉扩展：开关文案退回旧「隐藏boss/显示boss」（改名回滚）',
     ('Core/MapUI.lua', (
         u8('    bt:SetText(off and L["显示图钉"] or L["隐藏图钉"])\\n'),
         u8('    bt:SetText(off and L["显示boss"] or L["隐藏boss"]) -- MUT: old label\\n')))),
''')

# 追加到 MUTATIONS 列表结尾（列表的闭合 ] 之前）
idx = m.find('\nMUTATIONS = [')
assert idx > 0, '找不到 MUTATIONS 定义'
end = m.find('\n]', idx)
assert end > 0, '找不到 MUTATIONS 列表结尾'
m2 = m[:end] + new_muts.decode('utf-8').rstrip('\n') + m[end:]
wr(p2, m2)
print('df_mut_check.py 追加 7 条变异完成')

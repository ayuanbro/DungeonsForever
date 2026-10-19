# -*- coding: utf-8 -*-
"""把「快捷按钮栏」的静态闸 + 动态断言接进 df_dungeon_check.py，并补 df_mut_check.py 变异。

一次落盘（幂等：重复跑会因锚点命中数 != 1 退出）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

QB_SCRIPT = r'''
QB_SCRIPT = r"""SCRIPT_BODY"""


def qb_guard(lua):
    """快捷按钮栏（Core/QuickBar.lua）动态断言：跑在 df_dungeon_check 的 LUA_SCRIPT 之后。

    依赖 LUA_SCRIPT 已经装好的东西：PLAYER_LEVEL 全局、UnitLevel 桩、桩帧的 __shown。
    """
    section('快捷栏行为断言')
    out = lua.eval(QB_SCRIPT)
    for line in (out or '').split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            ck('快捷栏 Lua 侧输出缺制表符', False, line[:300])
            continue
        ck(parts[1], parts[0] == 'OK', parts[2] if len(parts) > 2 else None)

'''

QB_BODY = r'''
local R = {}
local function ck(n, ok, ex)
  R[#R + 1] = (ok and 'OK' or 'FAIL') .. '\t' .. n .. '\t' .. (ex and tostring(ex) or '')
end

local QB = TF_NS.QuickBar
ck("★ ㊱ 快捷栏模块存在（ns.QuickBar）", QB ~= nil)
if QB == nil then return table.concat(R, '\n') end

local cfg = TF_NS.QuickCfg()
ck("★ ㊱ 快捷栏默认配置（开启 / 三组全开 / 专业只看已学 / 四个探索子页全选）",
   cfg.on == true and cfg.groups.dungeon == true and cfg.groups.prof == true
   and cfg.groups.explore == true and cfg.profMode == 'learned'
   and cfg.expl['books'] == true and cfg.expl['bm'] == true,
   'profMode=' .. tostring(cfg.profMode))

cfg.groups.prof, cfg.groups.explore = false, false
QB:Ensure()
if QB.frame == nil then
  ck("★ ㊱ 快捷栏面板已建（父级 = 主窗口）", false)
  return table.concat(R, '\n')
end
QB:Render()

local DG = TF_NS.ProfHost.DG
local nDun = 0
for _, d in ipairs(TF_NS.DungeonData.dungeons) do
  if d.levelMin and DG.GroupOf(d, PLAYER_LEVEL) == 'rec' then nDun = nDun + 1 end
end
ck("★ ㊱ 副本组 = 当前等级的推荐副本数 + 「全部副本」尾条（推荐口径与副本页同源）",
   QB.counts.dungeon == nDun and QB.rows == nDun + 1,
   'dun=' .. QB.counts.dungeon .. ' rows=' .. QB.rows .. ' 期望 ' .. nDun .. '/' .. (nDun + 1))

cfg.groups.dungeon = false
QB:Render()
ck("★ ㊱ 关掉副本分组 → 该组条目与分组头一并撤下",
   QB.counts.dungeon == 0 and QB.rows == 0 and QB.groups == 0,
   'rows=' .. QB.rows .. ' groups=' .. QB.groups)

cfg.groups.dungeon = true
cfg.on = false
QB:Apply()
ck("★ ㊱ 总开关关闭 → 快捷栏隐藏", QB.frame.__shown == false)
cfg.on = true
QB:Apply()
ck("★ ㊱ 总开关打开 → 快捷栏显示", QB.frame.__shown == true)

local calls = {}
local o1, o2 = TF_NS.OpenPage, TF_NS.ShowDungeonDetail
local PD, EG = TF_NS.ProfModule, TF_NS.ExploreModule
local o3 = PD and PD.Show
local o4 = EG and EG.ShowSub
TF_NS.OpenPage = function(k) calls[#calls + 1] = k end
TF_NS.ShowDungeonDetail = function(id) calls[#calls + 1] = 'detail:' .. tostring(id) end
if PD then PD.Show = function(slug) calls[#calls + 1] = 'show:' .. tostring(slug) end end
if EG then EG.ShowSub = function(k) calls[#calls + 1] = 'sub:' .. tostring(k) end end
QB:Click({ act = 'dungeon', id = 'the_stockade' })
QB:Click({ act = 'prof', slug = 'alchemy' })
QB:Click({ act = 'explore', key = 'bm' })
QB:Click({ act = 'page', key = 'Raids' })
QB:Click(nil)
QB:Click({ dead = true })
TF_NS.OpenPage, TF_NS.ShowDungeonDetail = o1, o2
if PD then PD.Show = o3 end
if EG then EG.ShowSub = o4 end
local got = table.concat(calls, '|')
ck("★ ㊱ 行点击分派（副本→详情 / 专业→Show / 探索→ShowSub / 页级→OpenPage；nil 与 dead 行不动作）",
   got == 'detail:the_stockade|Professions|show:alchemy|Explore|sub:bm|Raids', got)

return table.concat(R, '\n')
'''

STATIC = r'''

# ---- ㊱ 主窗右侧「快捷按钮栏」（Core/QuickBar.lua，手写件）----
# 2026-09-30 用户定：宽 100；走 A 方案 —— 常驻**第二槽**，与「设置」/「装备过滤」并存不互斥；
# 推荐五人本「当前有什么显示什么」、点条目直接进该副本详情；专业列表口径（只看已学 / 全部）
# 只管快捷栏；探索显示哪几个子页由设置多选决定；总开关与各分组开关都在设置面板里。
_qb_src = open(os.path.join(ADDON, 'Core', 'QuickBar.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
_qb_toc = [l.strip().replace('\\', '/') for l in
           open(TOC, encoding='utf-8', errors='replace').read().splitlines()
           if l.strip() and not l.strip().startswith('##')]
ck('★★ ㊱ 快捷栏在 TOC 里、且排在 MainFrame 之后（它要贴 ns.MainFrame、读 ns.SettingsPopup）',
   'Core/QuickBar.lua' in _qb_toc
   and _qb_toc.index('Core/MainFrame.lua') < _qb_toc.index('Core/QuickBar.lua'))
ck('★★ ㊱ 面板几何钉死（宽 100 / 第二槽左缘 236 = 设置槽 220 + 8 + 8 / 顶底与主窗齐平 / 父级 = 主窗口）',
   'QB.W = 100' in _qb_src
   and 'QB.SLOT2 = 236' in _qb_src
   and 'QB.CW = QB.W - QB.PAD * 2' in _qb_src
   and 'f:SetPoint("TOPLEFT", host, "TOPRIGHT", self.SLOT2, 0)' in _qb_src
   and 'f:SetPoint("BOTTOMLEFT", host, "BOTTOMRIGHT", self.SLOT2, 0)' in _qb_src
   and 'local host = ns.MainFrame' in _qb_src)
ck('★★ ㊱ 面板层级 512 + 走 HUI 蒙皮（与「设置」/「装备过滤」同规格）',
   'f:SetFrameLevel(512)' in _qb_src
   and 'ns.hui.SkinPopup(f, 8)' in _qb_src)
ck('★★ ㊱ 字号口径（常量行 16/14/11 + 全文件 Fs(...) 的字号字面量只许 11 / 14 / 16）',
   'QB.FS_HEAD, QB.FS_NAME, QB.FS_AUX = 16, 14, 11' in _qb_src
   and all(int(n) in (11, 14, 16) for n in re.findall(r'\bFs\([^,\n]*,\s*(\d+)\s*,', _qb_src)),
   extra='sizes=%s' % re.findall(r'\bFs\([^,\n]*,\s*(\d+)\s*,', _qb_src))
ck('★★ ㊱ 无裸全局函数（界面层一律挂 QB.* / ns.*；剥离时被同名插件覆盖的根因闸）',
   not re.search(r'^function\s+[A-Za-z_]\w*\s*\(', _qb_src, re.M))
ck('★★ ㊱ 不覆盖主窗（父级挂主窗、只占第二槽；没有盖住主窗的热区）',
   'SetAllPoints' not in _qb_src)
ck('★★ ㊱ 行点击分派口径（副本→ns.ShowDungeonDetail / 专业→ProfModule.Show / 探索→ExploreModule.ShowSub / 页级→ns.OpenPage）',
   'ns.ShowDungeonDetail(spec.id)' in _qb_src
   and 'ns.ProfModule.Show(spec.slug)' in _qb_src
   and 'ns.ExploreModule.ShowSub(spec.key)' in _qb_src
   and 'ns.OpenPage(spec.key)' in _qb_src
   and 'if type(spec) ~= "table" or spec.dead then return end' in _qb_src)
_dg_src = open(os.path.join(ADDON, 'Core', 'DungeonUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
_ex_src = open(os.path.join(ADDON, 'Core', 'ExploreUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
ck('★★ ㊱ 快捷栏依赖的两个新入口在位（DungeonUI 的 ns.ShowDungeonDetail / ExploreUI 的 EG.ShowSub）',
   'function ns.ShowDungeonDetail(id)' in _dg_src
   and 'ns.OpenPage("Dungeons")' in _dg_src
   and 'U:ShowDungeonDetail(d)' in _dg_src
   and 'if U.built and U.dungeonBuilt then' in _dg_src
   and 'function EG.ShowSub(key)' in _ex_src
   and 'SetSub(key)' in _ex_src)
ck('★★ ㊱ 设置面板挂在主窗既有弹窗上（不另开窗口）：走 ns.SettingsPopup',
   'local pop = ns.SettingsPopup' in _qb_src
   and 'ns.SettingsPopup = settingsPop' in _about_src)
ck('★★ ㊱ 设置面板分组齐备（总开关 / 三个分组开关 / 专业口径两枚 / 探索四枚子页）',
   'Header(L["快捷按钮栏"])' in _qb_src
   and 'Header(L["显示分组"])' in _qb_src
   and 'Header(L["专业列表"])' in _qb_src
   and 'Header(L["探索子页"])' in _qb_src
   and '{ key = "dungeon", label = L["推荐五人本"] }' in _qb_src
   and 'if ns.LoadForeverPages or def.key == "dungeon" then' in _qb_src
   and 'Chip(pop, L["只看已学"], 68, 22)' in _qb_src
   and 'ns.QuickCfg().profMode = "learned"' in _qb_src
   and 'ns.QuickCfg().profMode = "all"' in _qb_src
   and 'key = "books",   text = L["40本书"]' in _qb_src
   and 'key = "rewards", text = L["奖励总览"]' in _qb_src
   and 'key = "bag",     text = L["睡袋"]' in _qb_src
   and 'key = "bm",      text = L["战斗法师"]' in _qb_src)
ck('★★ ㊱ 存档走 ns.QuickCfg（版本闸 + 缺失补默认）+ 键表集中定义在 Core.lua',
   'function ns.QuickCfg()' in _core_src
   and 'ns.QUICK_VER = 1' in _core_src
   and 'ns.QUICK_GROUPS = { "dungeon", "prof", "explore" }' in _core_src
   and 'ns.QUICK_EXPLORE = { "books", "rewards", "bag", "bm" }' in _core_src
   and 'if q.profMode ~= "all" then q.profMode = "learned" end' in _core_src
   and 'ns.QuickCfg()' in _qb_src)
ck('★★ ㊱ 主窗显示时刷新快捷栏（OnShow → OnMainShow）+ 升级 / 专业变动重算',
   'if ns.QuickBar then ns.QuickBar:OnMainShow() end' in _about_src
   and 'ev:RegisterEvent("PLAYER_LEVEL_UP")' in _qb_src
   and 'ev:RegisterEvent("SKILL_LINES_CHANGED")' in _qb_src
   and 'if QB.built then QB:Render() end' in _qb_src)
ck('★★ ㊱ 开设置弹窗时同步快捷栏开关态（否则开关显示的是上次的旧状态）',
   'if show and ns.QuickBar then ns.QuickBar:SyncSettings() end' in _about_src
   and 'function QB:SyncSettings()' in _qb_src
   and 'SetChecked(cfg.on and true or false)' in _qb_src)
'''

MUT_NEW = r'''
    # ㊱ 快捷按钮栏（2026-09-30 用户：宽 100、A 方案常驻第二槽、推荐有什么显示什么）
    ('快捷栏：面板挪回设置槽（+8）—— 两栏叠在一起、把设置弹窗压死',
     ('Core/QuickBar.lua', (
         b'    f:SetPoint("TOPLEFT", host, "TOPRIGHT", self.SLOT2, 0)',
         b'    f:SetPoint("TOPLEFT", host, "TOPRIGHT", 8, 0) -- MUT: 抢第一槽\n'))),
    ('快捷栏：不再监听升级事件（推荐五人本停在打开界面那一眼的等级）',
     ('Core/QuickBar.lua', (
         b'    ev:RegisterEvent("PLAYER_LEVEL_UP")',
         b'    ev:RegisterEvent("PLAYER_INVENTORY_CHANGED") -- MUT: 丢了升级事件\n'))),
    ('快捷栏：副本分组的开关被绕过（关掉也照样铺条目）',
     ('Core/QuickBar.lua', (
         b'    if cfg.groups.dungeon then\n        out[#out + 1] = { grp = L["推荐五人本"] }',
         b'    if true then\n        out[#out + 1] = { grp = L["推荐五人本"] }'))),
    ('快捷栏：专业口径默认变成「全部」（新用户第一次打开就铺 13 个专业）',
     ('Core/Core.lua', (
         b'    if q.profMode ~= "all" then q.profMode = "learned" end',
         b'    q.profMode = "all" -- MUT: 默认全部专业\n'))),
'''


def patch(path, pairs):
    with open(path, 'r', encoding='utf-8', newline='') as f:
        data = f.read()
    for old, new in pairs:
        n = data.count(old)
        if n != 1:
            print('!! 锚点命中 %d 次（应为 1）: %s' % (n, path))
            return False
        data = data.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(data)
    print('  已改 %s' % os.path.basename(path))
    return True


def main():
    chk = os.path.join(HERE, 'df_dungeon_check.py')
    mut = os.path.join(HERE, 'df_mut_check.py')

    if open(chk, encoding='utf-8').read().count('qb_guard') > 0:
        print('!! df_dungeon_check.py 已经接过 qb_guard')
        return 1

    qb_block = QB_SCRIPT.replace('SCRIPT_BODY', QB_BODY)
    anchor_main = "def main():\n    section('无限副本手册 · 副本页回归检查"
    anchor_call = "    section('结论')\n    print('通过 %d 项 / 失败 %d 项'"
    anchor_tail = "\nif __name__ == '__main__':\n"
    anchor_mut = "         b'    sh:EnableMouse(true)\\n'))),\n]\n"

    ok = True
    ok &= patch(chk, [
        (anchor_main, qb_block.lstrip('\n') + '\n' + anchor_main),
        (anchor_call, "    qb_guard(lua)\n\n" + anchor_call),
        (anchor_tail, STATIC + anchor_tail),
    ])
    ok &= patch(mut, [(anchor_mut, "         b'    sh:EnableMouse(true)\\n'))),\n" + MUT_NEW + "]\n")])
    print('结果：%s' % ('OK' if ok else 'FAILED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

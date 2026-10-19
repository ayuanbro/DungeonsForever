# -*- coding: utf-8 -*-
"""攻略子页签离线冒烟（卡片式 2×2 布局）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
TOC = os.path.join(ADDON, 'DungeonsForever.toc')
BUILD = 16001

files = [l.strip().replace('\\', '/') for l in
         open(TOC, encoding='utf-8', errors='replace').read().splitlines()
         if l.strip() and not l.strip().startswith('##')]

lua = lua51.LuaRuntime(unpack_returned_tuples=True)
lua.execute(T.STUB)
lua.execute('os = nil')
lua.execute('time = function() return 1796850000 end')
lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
lua.execute('TF_NS = TF_NS or {}')
lua.execute('UIErrorsFrame = { AddMessage = function() end }')
lua.execute('do local o = GetBuildInfo; GetBuildInfo = function(...) '
            'local a, b, c, d = o(...); return a, b, c, %d, e end end' % BUILD)

loadfile = lua.eval(
    'function(rel)\n'
    '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
    '  if not chunk then return nil end\n'
    '  return function() return chunk("DungeonsForever", TF_NS) end\n'
    'end')

for rel in files:
    if rel.lower().endswith('.xml'):
        continue
    ch = loadfile(rel)
    if ch is None:
        print('loadfile 返回 nil：%s' % rel)
        sys.exit(1)
    ch()
print('按 TOC 加载完成（%d 个 Lua）\n' % len([f for f in files if not f.lower().endswith('.xml')]))

out = lua.eval(r'''
(function()
  local R = {}
  local function ck(n, c, e)
    R[#R + 1] = (c and "OK" or "FAIL") .. "\t" .. n
      .. (e ~= nil and ("\t[" .. tostring(e) .. "]") or "")
  end
  local ok, err = pcall(function()
    local ns = TF_NS
    local U = ns.DungeonUI
    if ns.hui then ns.hui.ReskinToggle = function() end end
    PLAYER_LEVEL = 16
    UnitLevel = function() return PLAYER_LEVEL end
    if not U.built then U:Build() end
    ck("界面已构建", U.built == true)
    U:SwitchSub("Dungeons")

    local gd = ns.DungeonGuide
    ck("攻略数据装载（ns.DungeonGuide）", gd ~= nil and gd.ruins_of_lordaeron ~= nil)
    ck("洛丹伦废墟：6 boss / 4 组小怪 / 5 条须知",
       gd ~= nil and gd.ruins_of_lordaeron ~= nil
       and #gd.ruins_of_lordaeron.bosses == 6
       and #gd.ruins_of_lordaeron.trash == 4
       and #gd.ruins_of_lordaeron.tips == 5)

    local tb = U.dungeonTabBtns or {}
    local nt = 0
    for _ in pairs(tb) do nt = nt + 1 end
    ck("详情页签共 3 个（掉落 / 任务 / 攻略）", nt == 3 and tb.guide ~= nil, nt)

    local rol, hall
    for _, d in ipairs(ns.DungeonData.dungeons) do
      if d.id == "ruins_of_lordaeron" then rol = d
      elseif d.id == "hall_of_thanes" then hall = d end
    end
    ck("定位样例副本", rol ~= nil and hall ~= nil)

    local gc0 = U.dungeonGuideChild
    U:ShowDungeonDetail(rol)
    U:SetDungeonTab("guide")
    ck("curTab = guide", U.dungeonTab == "guide", U.dungeonTab)
    ck("攻略滚动区显示", U.dungeonGuideScroll.__shown == true)
    ck("掉落滚动区隐藏", U.dungeonDetailScroll.__shown == false)
    ck("任务列表隐藏", U.dungeonQuestScroll.__shown == false)
    ck("任务详情隐藏", U.dungeonQDet.__shown == false)
    local fv = 0
    for _, b in pairs(U.dungeonFilterBtns or {}) do if b.__shown then fv = fv + 1 end end
    ck("筛选按钮全隐（攻略不分档）", fv == 0, fv)

    local DGx = ns.ProfHost.DG
    local cards = U.dungeonGuidePool.card
    ck("卡片池 = 4 张", #cards == 4, #cards)
    ck("卡宽 = 456（网格 920 / 2 列）", DGx.GUIDE_CARD_W == 456, DGx.GUIDE_CARD_W)
    ck("★ 卡宽不越 edgeFile 崩溃线（760 炸 / 520 安全）",
       DGx.GUIDE_CARD_W <= 520, DGx.GUIDE_CARD_W)

    local lab, nRow, nShow, nRowTxt = {}, 0, 0, 0
    for i = 1, #cards do
      lab[i] = tostring(cards[i].title.__text)
      for _, f in ipairs(cards[i].rows or {}) do
        nRow = nRow + 1
        if f.__shown then nShow = nShow + 1 end
        if f.__text and #f.__text > 0 then nRowTxt = nRowTxt + 1 end
      end
    end
    R[#R + 1] = "INFO\t四张卡标题\t[" .. table.concat(lab, " | ") .. "]"
    ck("四张卡标题文本正确",
       lab[1] == "副本须知" and lab[2] == "怎么进本"
       and lab[3] == "BOSS 打法" and lab[4] == "小怪应对", table.concat(lab, "/"))
    ck("正文总段数 = 34（6 须知 = 定位语 + 5 条，+ 8 进本 + 12 BOSS + 8 小怪）",
       nRow == 34, nRow)
    ck("34 段全部显示", nShow == 34, nShow)
    ck("34 段全部有文本（不是空壳）", nRowTxt == 34, nRowTxt)
    ck("四张卡全部显示",
       cards[1].__shown and cards[2].__shown and cards[3].__shown and cards[4].__shown)

    local p1, p2, p3, p4 = cards[1].__pts, cards[2].__pts, cards[3].__pts, cards[4].__pts
    ck("第一行左卡 x = 8（SIDE 留白）", p1[4] == 8, p1[4])
    ck("第一行右卡 x = 472（SIDE + 卡宽 + 列距）", p2[4] == 472, p2[4])
    ck("第二行左卡 x = 8", p3[4] == 8, p3[4])
    ck("第二行右卡 x = 472", p4[4] == 472, p4[4])
    ck("★★ 网格左右留白对称各 8（右卡右缘 = SIDE + GRID_W）",
       p1[4] == DGx.GUIDE_SIDE
       and p2[4] + DGx.GUIDE_CARD_W == DGx.GUIDE_SIDE + DGx.GUIDE_GRID_W,
       tostring(p2[4] + DGx.GUIDE_CARD_W))
    ck("第二行在第一行下方", p3[5] < p1[5],
       tostring(p3[5]) .. " < " .. tostring(p1[5]))
    ck("★ 行内两卡等高（第一行）", cards[1].__h == cards[2].__h,
       tostring(cards[1].__h) .. " vs " .. tostring(cards[2].__h))
    ck("★ 行内两卡等高（第二行）", cards[3].__h == cards[4].__h,
       tostring(cards[3].__h) .. " vs " .. tostring(cards[4].__h))
    local fit = 0
    for i = 1, #cards do
      local rw = cards[i].rows or {}
      if #rw > 0 and cards[i].__h >= -rw[#rw].__pts[5] + 18 then fit = fit + 1 end
    end
    ck("★★ 四张卡都高到装得下自己最后一行（取行内较高者，不是压矮）", fit == 4, fit)
    ck("第二行高于第一行（BOSS 卡内容最多）", cards[3].__h > cards[1].__h,
       tostring(cards[3].__h) .. " > " .. tostring(cards[1].__h))
    ck("每张卡都有正文段",
       #cards[1].rows > 0 and #cards[2].rows > 0
       and #cards[3].rows > 0 and #cards[4].rows > 0)
    ck("★ 卡内正文锚在卡自身（随卡移动，不锚 child）",
       cards[3].rows[1].__pts[2] == cards[3])
    ck("★ 卡左侧色条已上色（4 张各一色）",
       cards[1].stripe.__ct ~= nil and cards[2].stripe.__ct ~= nil
       and cards[3].stripe.__ct ~= nil and cards[4].stripe.__ct ~= nil
       and cards[1].stripe.__ct[1] ~= cards[3].stripe.__ct[1])
    ck("★★ 卡片紧贴内容区顶部（第一行卡顶 y = 0，上方不再留定位语空档）",
       p1[5] == 0 and p2[5] == 0, tostring(p1[5]) .. "/" .. tostring(p2[5]))
    ck("★★ 攻略区顶常量 = hero + 8（与横幅只留 8px 间距，不吃筛选行空档）",
       DGx.GUIDE_TOP_Y == DGx.HERO_H + 8 and DGx.SCROLL_Y == DGx.FILTER_Y + 34,
       tostring(DGx.GUIDE_TOP_Y))
    ck("★★ 定位语已并入「副本须知」首条（不再是独立一帧）",
       U.dungeonGuidePool.tag == nil
       and tostring(cards[1].rows[1].__text):find("洛丹伦废城地下", 1, true) ~= nil,
       tostring(cards[1].rows[1].__text))
    R[#R + 1] = "INFO\t副本须知首条\t[" .. tostring(cards[1].rows[1].__text) .. "]"

    local GBN = ns.ProfHost.DG.GuideBossName
    ck("BOSS 中文名从掉落表反查（Witherfang → 枯牙）",
       GBN("ruins_of_lordaeron", "Witherfang") == "枯牙",
       tostring(GBN("ruins_of_lordaeron", "Witherfang")))
    ck("掉落表没有的英文名原样回退（不拼半个名字）",
       GBN("ruins_of_lordaeron", "Nobody") == "Nobody",
       tostring(GBN("ruins_of_lordaeron", "Nobody")))
    ck("大小写敏感的英文键也能对上（Rath'mael）",
       GBN("ruins_of_lordaeron", "Rath'mael") == "拉斯玛尔",
       tostring(GBN("ruins_of_lordaeron", "Rath'mael")))
    ck("★ BOSS 卡里渲染的是中文名（枯牙，不是 Witherfang）",
       tostring(cards[3].rows[1].__text):find("枯牙", 1, true) ~= nil,
       tostring(cards[3].rows[1].__text))
    R[#R + 1] = "INFO\t其余 BOSS 名\t[" ..
      tostring(GBN("ruins_of_lordaeron", "The Baron")) .. " / " ..
      tostring(GBN("ruins_of_lordaeron", "The Abandoned")) .. " / " ..
      tostring(GBN("ruins_of_lordaeron", "Bjork")) .. " / " ..
      tostring(GBN("ruins_of_lordaeron", "Viktor the Vile")) .. "]"

    U:ShowDungeonDetail(hall)
    U:SetDungeonTab("guide")
    local nCardShown = 0
    for _, c in ipairs(cards) do if c.__shown then nCardShown = nCardShown + 1 end end
    ck("无攻略副本：卡片全隐", nCardShown == 0, nCardShown)
    ck("无攻略副本：只留 1 句空态",
       U.dungeonGuidePool.note ~= nil and U.dungeonGuidePool.note.__shown == true)
    R[#R + 1] = "INFO\t空态文案\t[" .. tostring(U.dungeonGuidePool.note.__text) .. "]"

    U:ShowDungeonDetail(rol)
    U:SetDungeonTab("loot")
    ck("切回掉落：攻略隐藏 / 掉落实显",
       U.dungeonGuideScroll.__shown == false and U.dungeonDetailScroll.__shown == true)
    ck("攻略子帧恒定（切页签 / 切副本都不重建）", U.dungeonGuideChild == gc0)

    U:SetDungeonTab("guide")
    U:SetDungeonTab("quest")
    U:SetDungeonTab("guide")
    local nRow2 = 0
    for i = 1, #cards do
      for _, f in ipairs(cards[i].rows or {}) do nRow2 = nRow2 + 1 end
    end
    ck("反复切页签后正文池不膨胀（仍 34）", nRow2 == 34, nRow2)
    ck("反复切页签后卡片池不膨胀（仍 4）", #cards == 4, #cards)
  end)
  if not ok then
    R[#R + 1] = "FAIL\tLua 断言块抛异常\t["
      .. tostring(err):gsub("[\r\n]+", " "):sub(1, 400) .. "]"
  end
  return table.concat(R, "\n")
end)()
''')

bad = 0
for line in (out or '').split('\n'):
    if not line.strip():
        continue
    p = line.split('\t')
    tag = p[0]
    extra = p[2] if len(p) > 2 else ''
    if tag == 'FAIL':
        bad += 1
        print('  [FAIL] %-40s %s' % (p[1], extra))
    elif tag == 'INFO':
        print('  [info] %-40s %s' % (p[1], extra))
    else:
        print('  [OK  ] %-40s %s' % (p[1], extra))

print('\n失败 %d 项' % bad)
sys.exit(1 if bad else 0)

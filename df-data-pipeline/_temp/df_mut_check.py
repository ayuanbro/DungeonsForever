# -*- coding: utf-8 -*-
"""副本页 harness 的变异验证（证明断言非恒真）· 无限副本手册。

把历史上真实踩过的**错误写法**注入 beta 副本，重跑 df_dungeon_check.py，要求它必须变红。
分三大类：① 站点数据弃用（2026-09-22 用户决定：站点口径不准，物品属性只认客户端）
        ② 闪退/池化（scroll child 重建）
        ③ 滚轮、提示框、取数口（实机症状）

★ 全量一次性注入：断言若依赖「同批别的可变参数」，会被互相掩盖 —— 需要固定基准
  （harness 里 LOOT 字号那条就专门用了固定 ref3 算卡宽，不取被改的 DG.LOOT_COLS）。

跑完自动用 titan 端（干净）覆盖 beta 还原；跑之前先 sync_beta.py --apply。二进制读写，避免 CRLF 被规范化。

【站点数据弃用类】—— 用户诉求：客户端没数据就明说，绝不回退站点
  · MUT_NAME_SITE    物品名回退站点名字（占位文案不再出）
  · MUT_NAME_ORDER   名字不再走异步取数口（只剩同步口）
  · MUT_META_SITE    部位在客户端无数据时回退站点部位串
  · MUT_ICON_SITE    图标兜底改成固定站点图标名（不再是客户端问号图）
  · MUT_TIP_SITE_BACK 提示框把站点逐行文本接回来
  · MUT_CAT_SITE     分类重新读站点「部位」字段（it[4]）
  · MUT_CAT_OTHER    分类判定整体失效（全归 other）
  · MUT_QUAL_FALLBACK QualOf 重新长出 fallback 形参（站点 q 兜底）
  · MUT_QUAL_ASYNC_ONLY QualOf 不再走同步口（只认异步）
  · MUT_NS_NO_PCALL  NsCall 不再 pcall（未知 id 会抛错掀掉悬停）

【闪退/池化】
  · MUT_LIST_OLD     列表重建 scroll child + child:SetParent(nil)（实机 ERROR #132 根因）
  · MUT_DETAIL_OLD   详情行池每次强制新建行帧

【滚轮】详情容器不绑/不挂、掉落卡/任务行不转发、步进 48->32、上限算错

【提示框】摘 pcall、GetItemInfo 当门槛、预热空转、不注册到货事件

【名字可见性】2026-09-22 第三轮（用户：「图标有、名字没有」= 到货那一下没接住）
  · MUT_EVT_ASYNC_NAME  不再监听 ITEM_DATA_LOAD_RESULT（官方异步系统的到货事件）
  · MUT_NO_SWEEP        不排定时重扫（数据晚到就永远停在占位）
  · MUT_SWEEP_NO_SKIP   重扫不跳过已到货的卡（每轮白刷）
  · MUT_NO_NAMED_MARK   到货不打 __named
  · MUT_NO_NAMED_BIND   绑定时不记 __named（复用的卡漏掉）

【品质/取数口】到货不刷卡片色、色表索引错位、摘命名空间兜底、裸调全局
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TITAN = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
PY = sys.executable

# ---------------- ① 站点数据弃用（2026-09-22 用户决定） ----------------

# 物品名回退站点名：客户端拿不到时不再给占位文案，而是编一个站点名字并当「有名字」上色。
# 期望：静态「名字取不到时用占位文案」+ 三处动态「占位文案 / 占位名灰色」失败。
MUT_NAME_SITE = (
    b'    return L["\xe6\x9a\x82\xe6\x97\xb6\xe6\xb2\xa1\xe6\x9c\x89\xe5\xae\xa2\xe6\x88\xb7\xe7\xab\xaf\xe6\x95\xb0\xe6\x8d\xae"], false\r\n',
    b'    return "\xe6\xb0\xb4\xe8\x9b\x87\xe6\xb3\x95\xe8\xa2\x8d", true   -- MUT: site name fallback\r\n')

# 名字不再走异步取数口（只剩 C_Item 同步口）—— 本端命名空间异步口是真的有数据，
# 少了它首帧就只能靠同步口（部分端没有）。期望：动态「名字取客户端（命名空间兜底生效）」失败。
MUT_NAME_ORDER = (
    b'        local nm = DG.ItemInfo(id)\r\n',
    b'        local nm = nil   -- MUT: async name route skipped\r\n')

# 部位：客户端没数据时回退站点部位串（原为留空）。期望：「客户端无数据时部位行留空」失败。
MUT_META_SITE = (
    b'    if type(a) ~= "string" or a == "" then return "" end\r\n',
    b'    if type(a) ~= "string" or a == "" then return "\xe6\x9d\x82\xe9\xa1\xb9" end   -- MUT: site slot\r\n')

# 图标兜底改成固定站点图标名（不再是客户端自带问号图）。
# 期望：两处「客户端无数据时图标退问号图」失败。
MUT_ICON_SITE = (
    b'    return FALLBACK_ICON\r\n',
    b'    return "Interface\\\\Icons\\\\INV_Misc_Bag_08"   -- MUT: site icon name\r\n')

# 提示框把站点逐行文本接回来。期望：静态「提示框不再引用站点提示数据」+
# 「全文件不再引用站点物品资料」失败。
_ZH_UNSEEN = '    GameTooltip:AddLine(L["客户端未收录此物品"], 0.5, 0.5, 0.5, true)\r\n'.encode('utf-8')

# 提示框把站点出处接回来（用户第二轮明确不许）。期望：静态「提示框活代码不出现站点/掉率字样」
# + 动态「提示框上不出现站点/掉率字样」失败。
MUT_TIP_SITE_BACK = (
    _ZH_UNSEEN,
    '    GameTooltip:AddLine("站点掉率 34%", 1, 1, 1)\r\n'.encode('utf-8') + _ZH_UNSEEN)

# 只把「掉率」行接回来（不出现「站点」二字也能被单独抓住）。期望同上那条动态断言失败。
MUT_TIP_DROP_RATE = (
    _ZH_UNSEEN,
    '    GameTooltip:AddLine("掉率 34%", 1, 1, 1)\r\n'.encode('utf-8') + _ZH_UNSEEN)

# 缓存态原生分支被摘（退回只给占位兜底）。期望：静态「缓存态走 SetHyperlink」
# + 动态「缓存态走 SetHyperlink 出原生内容」失败。
MUT_TIP_NO_BYID = (
    b'    if id and cached and GameTooltip.SetHyperlink then\r\n',
    b'    if false and id and cached and GameTooltip.SetHyperlink then   -- MUT: no native link branch\r\n')

# 末行不再按客户端事实判（恒承诺「加载中」）—— 又变成一句永远兑现不了的承诺。
# 期望：动态「客户端静态数据都没有 → 绝不承诺」失败。
MUT_TIP_PROMISE = (
    b'    if id and DG.ItemInfoInstant(id) then\r\n',
    b'    if true then   -- MUT: always promise refresh\r\n')

# 摘掉请求第④路（官方异步口）。期望：静态「请求第④路」+ 动态「官方异步回调触发后卡片名字
# 刷成客户端真值」失败。
MUT_REQ_ASYNC = (
    b'    DG.ContinueOnItemLoad(id, function() DG.RefreshItemCards(id) end)\r\n',
    b'    -- MUT: official async loader route removed\r\n')

# 预热不再对「名字还没到货」的物品强制重请：客户端缓存会被驱逐，去重会让驱逐后的物品
# 永久卡在占位文案上。期望：静态「名字未到货时强制重请」失败。
MUT_PREWARM_FORCE = (
    b'            local _, hasName = DG.ItemName(it[1])\r\n'
    b'            DG.RequestItem(it[1], not hasName)\r\n',
    b'            DG.RequestItem(it[1])   -- MUT: no force re-request\r\n')

# ★★ 名字可见性（2026-09-22 第三轮，用户：「为什么你有图标但是没有名称呢」）：
#    图标/部位走 GetItemInfoInstant（静态、随叫随有），名字走 GetItemInfo（要等详细数据
#    到货）→ 「图标有、名字没有」= 到货那一下没接住。下面几条把两手补救逐个拆掉。
MUT_EVT_ASYNC_NAME = (
    b'    pcall(ev.RegisterEvent, ev, "ITEM_DATA_LOAD_RESULT")\r\n',
    b'    -- MUT: second arrival event removed\r\n')

MUT_NO_SWEEP = (
    b'    DG.ScheduleNameSweep()\r\n',
    b'    -- MUT: no timed rescan\r\n')

MUT_SWEEP_NO_SKIP = (
    # 死信短路重写后：item 池的未命名分支前置「死信短路」两行（chip 池没有）→ 用它钉 item 池。
    b'            if it and not c.__named then\r\n'
    b'                if DG.__tipDead and DG.__tipDead[it[1]] then\r\n'
    b'                    c.__named = true\r\n',
    b'            if it then -- MUT: sweep rescans named cards\r\n'
    b'                if DG.__tipDead and DG.__tipDead[it[1]] then\r\n'
    b'                    c.__named = true\r\n')

MUT_NO_NAMED_MARK = (
    b'            if c.name then\r\n'
    b'                local nm, hasName = DG.ItemName(itemID)\r\n'
    b'                c.name:SetText(nm)\r\n'
    b'                if hasName then\r\n'
    b'                    c.name:SetTextColor(DG.QColor(DG.QualOf(itemID)))\r\n'
    b'                else\r\n'
    b'                    c.name:SetTextColor(Unpack(C_GREY))\r\n'
    b'                end\r\n'
    b'                c.__named = hasName\r\n',
    b'            if c.name then\r\n'
    b'                local nm, hasName = DG.ItemName(itemID)\r\n'
    b'                c.name:SetText(nm)\r\n'
    b'                if hasName then\r\n'
    b'                    c.name:SetTextColor(DG.QColor(DG.QualOf(itemID)))\r\n'
    b'                else\r\n'
    b'                    c.name:SetTextColor(Unpack(C_GREY))\r\n'
    b'                end\r\n'
    b'                -- MUT: no __named mark\r\n')

# name harvest removed. expect: static harvest assertion fails.
MUT_HARVEST_GONE = (
    # 收割块有两处（item 池 + chip 池），钉单处杀不干净 -> 直接改函数定义名，
    # 两个调用点 guard 同时拿 nil，且 'function DG.HarvestTipName' 子串消失。
    # 注意新名不能含 'HarvestTipName' 前缀（静态断言是子串判定）。
    b'function DG.HarvestTipName(id)\r\n',
    b'function DG.TipHarvestGone_MUT(id)\r\n')

MUT_NO_NAMED_BIND = (
    b'    if c.name then\r\n'
    b'        local nm, hasName = DG.ItemName(itemID)\r\n'
    b'        c.name:SetText(nm)\r\n'
    b'        if hasName then\r\n'
    b'            c.name:SetTextColor(DG.QColor(DG.QualOf(itemID)))\r\n'
    b'        else\r\n'
    b'            c.name:SetTextColor(Unpack(C_GREY))\r\n'
    b'        end\r\n'
    b'        c.__named = hasName\r\n',
    b'    if c.name then\r\n'
    b'        local nm, hasName = DG.ItemName(itemID)\r\n'
    b'        c.name:SetText(nm)\r\n'
    b'        if hasName then\r\n'
    b'            c.name:SetTextColor(DG.QColor(DG.QualOf(itemID)))\r\n'
    b'        else\r\n'
    b'            c.name:SetTextColor(Unpack(C_GREY))\r\n'
    b'        end\r\n'
    b'        -- MUT: no __named mark on bind\r\n')



# 分类重新读站点「部位」字段。期望：静态「卡片分类走客户端 classID」失败（rcode 里又出现 it[4]）。
MUT_CAT_SITE = (
    b'            local cat = DG.CatOf(it[1])\r\n'
    b'            if counts[cat] then counts[cat] = counts[cat] + 1 end',
    b'            local cat = it[4] or DG.CatOf(it[1])\r\n'
    b'            if counts[cat] then counts[cat] = counts[cat] + 1 end')

# 分类判定整体失效（全归 other）。期望：「分类走客户端 classID（4 = 护甲）」+
# 「「任务物品」下只剩 1 行」失败。
MUT_CAT_OTHER = (
    b'    local _, _, _, _, _, classID = DG.ItemInfoInstant(id)\r\n'
    b'    return DG.CAT_BY_CLASS[classID] or "other"',
    b'    return "other"   -- MUT: category always other')

# QualOf 重新长出 fallback 形参（站点 q 兜底）。
# 期望：静态「站点品质彻底弃用（QualOf 不再有 fallback 形参）」失败。
MUT_QUAL_FALLBACK = (
    b'function DG.QualOf(id)\r\n    if id then',
    b'function DG.QualOf(id, fallback)\r\n    if id then   -- MUT: site q fallback')

# QualOf 不再走同步口。期望：「品质只认客户端：异步取数口 → 同步口」静态 +
# 「同步口可用时名字 / 品质照样出得来」动态失败。
MUT_QUAL_ASYNC_ONLY = (
    b'        q = DG.NsCall("GetItemQualityByID", id)\r\n'
    b'        if type(q) == "number" then return q end\r\n',
    b'        -- MUT: sync quality route removed\r\n')

# NsCall 不再 pcall（未知 id 会抛错，掀掉整个 OnEnter）。
# 期望：静态「同步取数口统一走 DG.NsCall（内部 pcall）」失败。
# ⚠️ 锚点必须带上 NsCall 的函数签名行做**函数域限定**：任务页的 DG.QLCall 与它
#    尾部 4 行逐字相同（同为「pcall 取数口」范式）——裸锚点会命中 2 次而拒绝注入
#    （2026-09-22 加任务页后实测撞上）。变异锚点同理：要么函数域限定，要么换唯一文本。
MUT_NS_NO_PCALL = (
    b'function DG.NsCall(name, id)\r\n'
    b'    if id == nil then return nil end\r\n'
    b'    local fn = C_Item and C_Item[name]\r\n'
    b'    if type(fn) ~= "function" then return nil end\r\n'
    b'    local ok, v = pcall(fn, id)\r\n'
    b'    if ok then return v end\r\n'
    b'    return nil\r\nend',
    b'function DG.NsCall(name, id)\r\n'
    b'    if id == nil then return nil end\r\n'
    b'    local fn = C_Item and C_Item[name]\r\n'
    b'    if type(fn) ~= "function" then return nil end\r\n'
    b'    return fn(id)\r\nend   -- MUT: no pcall guard')

# ---------------- ② 闪退 / 池化 ----------------

MUT_LIST_OLD = (b'    if not (data and data.dungeons and scroll and child and pool) then return end',
                b'    if not (data and data.dungeons and scroll and child and pool) then return end\r\n'
                b'    do\r\n'
                b'        local nc = CreateFrame("Frame", nil, scroll)\r\n'
                b'        nc:SetSize(DG.CHILD_W, 10)\r\n'
                b'        scroll:SetScrollChild(nc)\r\n'
                b'        child:SetParent(nil)\r\n'
                b'        U.dungeonListChild = nc\r\n'
                b'        child = nc\r\n'
                b'    end')

MUT_DETAIL_OLD = (
    b'        local r = rows[idx]\r\n',
    b'        local r = nil -- MUT: never reuse row\r\n')

# ---------------- ③ 提示框 ----------------

# 摘掉 pcall —— 客户端不认识的 itemID 会抛错，整个 OnEnter 被掀掉（实机症状）
MUT_TIP_PCALL = (b'pcall(GameTooltip.SetHyperlink, GameTooltip, "item:" .. tostring(id))',
                 b'GameTooltip.SetHyperlink(GameTooltip, "item:" .. tostring(id))')

# ★ 本次 bug 根因：把「无条件请客户端解析」改回「GetItemInfo 当门槛」。
# 客户端物品数据是懒加载的：没拉下来时 GetItemInfo 必然回 nil —— 拿它当门槛，
# 所有尚未预热的物品都会被误判成「客户端不认识」，于是用户在游戏里只看到站点数据。
MUT_TIP_GATE = (
    b'    local id = it[1]\r\n'
    b'    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")',
    b'    local id = it[1]\r\n'
    b'    if GetItemInfo and GetItemInfo(id) == nil then return end   -- MUT: lazy-load miss as gate\r\n'
    b'    GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")')

# 预热变成空转（不请求任何物品ID）
_PREWARM_BODY = (
    '    DG.EnsureItemListener()\r\n'
    '    for _, s in ipairs(loot) do\r\n'
    '        for _, it in ipairs(s[5]) do\r\n'
    '            -- 名字还拿不到就**强制**重请一次：客户端物品缓存会被驱逐\r\n'
    '            -- （ItemMixin:IsDataEvictable 恒 true），去过重的话驱逐之后再进这个副本\r\n'
    '            -- 就永远停在占位文案上了。\r\n'
    '            local _, hasName = DG.ItemName(it[1])\r\n'
    '            DG.RequestItem(it[1], not hasName)\r\n'
    '        end\r\n'
    '    end').encode('utf-8')
MUT_TIP_PREWARM = (
    b'function DG.PrewarmLoot(d)\r\n'
    b'    if not d then return end\r\n'
    b'    local loot = (ns.DungeonLoot or {})[d.id]\r\n'
    b'    if not loot then return end\r\n'
    b'    DG.EnsureItemListener()\r\n',
    b'function DG.PrewarmLoot(d)\r\n'
    b'    if not d then return end\r\n'
    b'    local loot = (ns.DungeonLoot or {})[d.id]\r\n'
    b'    if not loot then return end\r\n'
    b'    DG.EnsureItemListener()\r\n'
    b'    if true then return end -- MUT: prewarm does nothing\r\n')

MUT_TIP_LISTENER = (
    b'    ev:RegisterEvent("GET_ITEM_INFO_RECEIVED")\r\n',
    b'    local _evtname = "GET_ITEM_INFO_RECEIVED"\r\n')

# ---------------- ④ 滚轮 ----------------

# 滚轮①（本次 bug 根因）：详情容器不绑滚轮 —— 内容超出后完全滚不动
MUT_WHEEL_DETAIL = (b'    dscroll:EnableMouseWheel(true)\r\n',
                    b'    -- MUT: detail scroll frame has no wheel\r\n')

# 滚轮②：详情容器连处理函数也不挂（整块摘掉，写成一行的合法 Lua，避免留下悬空 end）
MUT_WHEEL_HANDLER = (
    b'    dscroll:SetScript("OnMouseWheel", function(self, delta)\r\n'
    b'        DG.WheelScroll(self, U.dungeonDetailChild, delta)\r\n'
    b'    end)\r\n',
    b'    local _wheelless = "MUT: no OnMouseWheel"\r\n')

# 滚轮③：掉落卡不转发 —— 鼠标压在卡片上时滚不动（详情页满屏都是卡片，等于整页滚不动）。
# ⚠️ 锚点必须带后续 OnMouseWheel 两行做**上下文限定**：任务行（DG.WheelScroll 同范式，
#    2026-09-22 新增）与它首行逐字相同 —— 裸锚点会命中 2 次而拒绝注入。
MUT_WHEEL_CARD = (
    b'        r:EnableMouseWheel(true)\r\n'
    b'        r:SetScript("OnMouseWheel", function(self, delta)\r\n'
    b'            DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)\r\n',
    b'        -- MUT: loot card eats the wheel\r\n'
    b'        r:SetScript("OnMouseWheel", function(self, delta)\r\n'
    b'            DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)\r\n')

# 任务页：摘掉 QUEST_LOG_UPDATE 监听 —— 接任务不触发重刷，刚接的任务要重开页面
# 才变「进行中」（2026-09-22 实机踩过）。期望：静态「QUEST_LOG_UPDATE 监听」失败。
MUT_NO_LOGUPD = (
    b'    ev:RegisterEvent("PLAYER_LOGIN")\r\n'
    b'    ev:RegisterEvent("QUEST_LOG_UPDATE")\r\n',
    b'    ev:RegisterEvent("PLAYER_LOGIN")\r\n'
    b'    -- MUT: no quest log update listener\r\n')

# 滚轮③b：任务行不转发（与掉落卡同款纪律：压在任务行上滚不动 = 任务页滚不到底）。
# 期望：静态「任务滚动容器绑了滚轮 + 行转发」失败。
MUT_WHEEL_QROW = (
    b'            r:EnableMouseWheel(true)\r\n'
    b'            r:SetScript("OnMouseWheel", function(_, delta)\r\n'
    b'                DG.WheelScroll(U.dungeonQuestScroll, U.dungeonQuestChild, delta)\r\n',
    b'            -- MUT: quest row eats the wheel\r\n'
    b'            r:SetScript("OnMouseWheel", function(_, delta)\r\n'
    b'                DG.WheelScroll(U.dungeonQuestScroll, U.dungeonQuestChild, delta)\r\n')

# 滚轮④：步进 48 -> 32（断言「下滚一步 = 48px」应失败）
MUT_WHEEL_STEP = (
    b'    scroll:SetVerticalScroll(math.max(0, math.min(maxScroll, scroll:GetVerticalScroll() - delta * 48)))\r\n',
    b'    scroll:SetVerticalScroll(math.max(0, math.min(maxScroll, scroll:GetVerticalScroll() - delta * 32)))\r\n')

# 滚轮⑤：上限算错（内容高 + 视口高）—— 到底那一条应失败（滚过头，内容被拉出可视区）
MUT_WHEEL_MAX = (b'    local maxScroll = math.max(0, child:GetHeight() - scroll:GetHeight())\r\n',
                 b'    local maxScroll = math.max(0, child:GetHeight() + scroll:GetHeight())\r\n')

# ---------------- ⑤ 卡片墙几何 ----------------

MUT_CARD_COLS = (
    b'DG.LOOT_COLS = 4\r\n',
    b'DG.LOOT_COLS = 2\r\n')
MUT_CARD_H = (b'DG.LOOT_CARD_H = 44', b'DG.LOOT_CARD_H = 30')

# 名称字号 14 -> 18 —— 3 列卡内放不下（最长名 16 字 = 288px > 可用 253px），
# 容量守门（字号 <= 15 且 字号x16 + 内边距 <= 卡宽）应失败
MUT_CARD_FONT = (b'DG.LOOT_FS_NAME = 14', b'DG.LOOT_FS_NAME = 18')

# 摘掉「每轮刷新复位常态底色」—— 池化卡会带着上一张卡的悬停态被复用。
# 运行时断言（包一层 SetBackdropColor 看最后一次 alpha）与静态计数（应为 3 处）都会失败。
MUT_CARD_BG_RESET = (
    b'r.note:Show()\r\n'
    b'                    if r.__huiCard then\r\n'
    b'                        HuiCardState(r, "norm")\r\n',
    b'r.note:Show()\r\n'
    b'                    if r.__huiCard then\r\n'
    b'                        do end -- MUT: backdrop reset skipped\r\n')

# ---------------- ⑥ 品质 ----------------

# 到货后不刷卡片色 —— 卡片会一直停在占位/旧值上
MUT_QUAL_LISTEN = (
    b'        if it and it[1] == itemID then\r\n',
    b'        if false and it and it[1] == itemID then   -- MUT: no refresh on arrival\r\n')

# 色表索引退回错位写法（QUALTAB 是 quality + 1 的 1 基表）
# —— quality 3（蓝）会取到「优秀/绿」，与真机颜色不符
MUT_QUAL_TAB = (b'    local d = DG.QUALTAB[(q or 1) + 1] or DG.QUALTAB[1]',
                b'    local d = DG.QUALTAB[q or 1] or DG.QUALTAB[1]')

# ---------------- ⑦ 物品数据加载链路 ----------------

_WARM_TIP_BLOCK = (
    '    if DG.__warmTip then\r\n'
    '        pcall(DG.__warmTip.SetOwner, DG.__warmTip, UIParent, "ANCHOR_NONE")\r\n'
    '        -- 按 ID 出提示框优先用 SetItemByID（暴雪掉落实物清单同一句）：走客户端\r\n'
    '        -- tooltip 管线去补数据；老端没有它再退 SetHyperlink。\r\n'
    '        if not pcall(DG.__warmTip.SetItemByID, DG.__warmTip, id) then\r\n'
    '            pcall(DG.__warmTip.SetHyperlink, DG.__warmTip, "item:" .. tostring(id))\r\n'
    '        end\r\n'
    '        pcall(DG.__warmTip.Hide, DG.__warmTip)\r\n'
    '    end\r\n').encode('utf-8')
# ★ 必须**整块**替换：只摘前两行会留下悬空的 end（Lua 语法错）—— 那是脏抓，不是真断言。
MUT_LOAD_TIP = (
    b'    DG.ContinueOnItemLoad(id, function() DG.RefreshItemCards(id) end)\n',
    b'    DG.ContinueOnItemLoad(id, function() end) -- MUT: arrival repaint removed\n')

MUT_LOAD_LISTENER = (
    b'    DG.__asked[id] = true\r\n'
    b'    DG.EnsureItemListener()\r\n',
    b'    DG.__asked[id] = true\r\n'
    b'    -- MUT: ensure-listener call removed\r\n')



# ---------------- ⑧ 取数口形态（本端 GetItemInfo 不在全局表里） ----------------

# 取数口①（★★ 本端形态的根因）：摘掉 C_Item 命名空间兜底 —— 本端全局 GetItemInfo 为 nil，
# 于是品质静默失效、图标回落兜底。
MUT_API_NO_NS = (
    b'function DG.ItemInfo(id)\r\n    if id == nil then return nil end\r\n'
    b'    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)\r\n',
    b'function DG.ItemInfo(id)\r\n    if id == nil then return nil end\r\n'
    b'    local fn = GetItemInfo   -- MUT: no C_Item namespace fallback\r\n')

# 取数口②：Instant 同理（图标 / 部位 / 分类）
MUT_API_NO_NS_I = (
    b'    local fn = GetItemInfoInstant or (C_Item and C_Item.GetItemInfoInstant)\r\n',
    b'    local fn = GetItemInfoInstant   -- MUT: no C_Item namespace fallback\r\n')

# 取数口③：RequestItem 第二路不再兜底命名空间
MUT_API_NO_NS_REQ = (
    b'    local fn = GetItemInfo or (C_Item and C_Item.GetItemInfo)\r\n'
    b'    if type(fn) == "function" then pcall(fn, id) end\r\n',
    b'    -- MUT: request route 2 removed\r\n')

# 取数口④：改回裸调全局（本端为 nil，静默失效）
MUT_API_BARE = (
    b'        local _, _, q = DG.ItemInfo(id)\r\n',
    b'        local _, _, q = GetItemInfo(id)   -- MUT: bare global call\r\n')

# ---------------- 地图标记（2026-09-22 第三批：点 NPC 名 → 开图放航点） ----------------

# MarkNPC 不再落航点（摘 SetUserWaypoint）：点了只开图、地图上没旗子。
# 期望：静态「DG.MarkNPC 航点链路」失败 + 动态「点起始行 → SetUserWaypoint 收到 UiMapPoint」失败。
MUT_NPC_WP_GONE = (
    b'            pcall(C_Map.SetUserWaypoint, pt)\r\n',
    b'            -- MUT: no waypoint\r\n')

# 起始行退回 Frame（Frame 不支持 OnClick，实机点了没反应、离线测不出）。
# 期望：静态「起始行可点（takeNpc Button）」失败。
MUT_NPC_BTN_GONE = (
    b'            f = CreateFrame("Button", nil, child)\r\n',
    b'            f = CreateFrame("Frame", nil, child) -- MUT: no Button\r\n')

# 起始行 __npc 不再赋值（行渲染出来但点了不干活）。
# 期望：动态「有 NPCID 时起始行走可点行」失败（__npc 断言 + 点击链路断）。
MUT_NPC_STARTNPC_GONE = (
    b'            f.__npc = q[16] or sn[1]\n',
    b'            f.__npc = nil -- MUT: start line dead\n')

# 前导链环的表外 NPCID 反查摘掉（环点不出来源）。
# 期望：静态「链节点标记入口」失败 + 动态「点链节点 → 航点指向该环起始 NPC」失败。
MUT_NPC_PRENPC_GONE = (
    b'                    if not nid and ns.QuestPreNpcID then nid = ns.QuestPreNpcID[seg] end\r\n',
    b'                    nid = nil -- MUT: pre npc gone\r\n')

# NPC 金名退回普通文本（可交互暗示丢失，玩家不知道能点）。
# 期望：静态「起始行 NPC 金名」失败。
MUT_NPC_GOLD_GONE = (
    b'        where = "|cffffd100" .. nm .. "|r" .. format(" |cff9a9a9a#%d|r", q[16])\r\n',
    b'        where = nm .. format(" |cff9a9a9a#%d|r", q[16]) -- MUT: grey name\r\n')


# ────────── 两列主从布局（2026-09-22 第二批） ──────────

# 右列详情不联动：渲染尾部摘掉 RenderQuestDetail 调用（点行右列不动 / 初选不渲染）。
# 期望：静态「点行选中 → 右列就地刷新」失败 + 动态右列整块失败。
MUT_NO_QDET = (
    b'    U.dungeonQuestScroll:SetVerticalScroll(0)\r\n'
    b'    DG.CullQuestRows()\r\n'
    b'    U:RenderQuestDetail()\r\n',
    b'    U.dungeonQuestScroll:SetVerticalScroll(0)\r\n'
    b'    DG.CullQuestRows()\r\n'
    b'    -- MUT: no quest detail linkage\r\n')

# 阵营档不自动勾当前角色阵营（永远全部）。
# 期望：静态「阵营档自动勾当前角色阵营」失败。
MUT_NO_SIDEAUTO = (
    b'        side = (ps == "A" or ps == "H") and ps or "A"\n',
    b'        side = "A" -- MUT: no auto faction side\n')

# 前导链不读第 9 字段（前置 ID 永远显示未解析）。
# 期望：静态「前导链/后续/目标/注释/奖励」失败 + 动态 5724 前导环失败。
MUT_NO_PREQ9 = (
    # 前导链追溯不读 preIDs 字段（collect 内直接置 nil）。
    b'            local pre = row[9]\r\n',
    b'            local pre = nil -- MUT: chain ignores preIds\r\n')

# 奖励芯片不读第 10 字段（任务奖励整节消失）。
# 期望：静态同上失败 + 动态 4 枚芯片失败。
MUT_NO_REW = (
    b'    local rew = q[10]\r\n',
    b'    local rew = nil -- MUT: ignore rewards\r\n')

# 点行不选中（右列详情永远停在首行）。
# 期望：静态「点行选中」失败 + 动态点行联动失败。
MUT_NO_QCLICK = (
    b'                    U.dungeonQuestSel = r.__q[1]\r\n',
    b'                    -- MUT: no click select\r\n')

# 任务行退回 Frame（实机报 script type not supported，桩的 SetScript 不校验所以离线测不出）。
# 期望：静态「任务行是 Button」失败。
# 2026-09-23：前导链节点行（NPC 地图标记）也是同形 CreateFrame 行 → 裸锚命中 2 次，
# 连上一行注释一起锚，钉死在任务列表的 takeRow() 里。
MUT_ROW_FRAME = (
    b'            r = CreateFrame("Button", nil, child, "BackdropTemplate")\r\n'
    b'            r:SetSize(DG.Q_LIST_W - DG.Q_PAD * 2, DG.Q_ROW_H)\r\n',
    b'            r = CreateFrame("Frame", nil, child, "BackdropTemplate") -- MUT: row is Frame\r\n'
    b'            r:SetSize(DG.Q_LIST_W - DG.Q_PAD * 2, DG.Q_ROW_H)\r\n')

# 前导链越过 28 副本范围就断（PreExtra 表不参与追溯）。
# 2026-09-22 起渲染分支也有一行同形 `local ex = ...`（起始信息回退），裸锚会命中 2 次
# → 连下一行 `if ex then prow = ...` 一起锚，钉在 collect() 里。
MUT_QPRE_GONE = (
    b'                        local ex = ns.DungeonQuestPreExtra[seg]\r\n'
    b'                        if ex then prow = { [1] = seg, [9] = ex } end\r\n',
    b'                        local ex = nil -- MUT: extra pre table gone\r\n'
    b'                        if ex then prow = { [1] = seg, [9] = ex } end\r\n')

# 表外链环节不显示起始 NPC（副标题退回「本表未收录起始信息」）。期望：静态+动态失败。
# 表外链环节不显示起始 NPC（src 分支接管首分支后，npc 只剩 elseif 行——锚连上下文钉域）
MUT_PRE_NO_START = (
    b'                        elseif ex.npc and ex.npc ~= "" then\r\n',
    b'                        elseif false then -- MUT: no start info\r\n')

# 起始行退回纯站点名（#NPCID 与按 ID 反查名都没了）。期望：静态失败。
# 2026-09-23：takeNpc 可点行里还有一处 `if q[16] then`（子串匹配命中 2 次）
# → 连上一行 q[6] where 拼接一起锚，钉死在名字构建分支上。
MUT_NPC_ID_GONE = (
    b'    if q[6] then where = (where ~= "" and (where .. " \xc2\xb7 " .. q[6]) or q[6]) end\r\n'
    b'    if q[16] then\r\n',
    b'    if q[6] then where = (where ~= "" and (where .. " \xc2\xb7 " .. q[6]) or q[6]) end\r\n'
    b'    if false then -- MUT: npc id branch gone\r\n')

# 表外链环节 src 来源回退没了（96391 黑铁地图 物品起始）。期望：静态失败。
MUT_SRC_GONE = (
    b'                        if ex.src and ex.src ~= "" then\r\n',
    b'                        if false then -- MUT: src branch gone\r\n')

# 详情页收获节没了（经验/金钱/声望 q[18]）。期望：静态失败。
MUT_GAINS_GONE = (
    b'        if seg and #seg > 0 then\r\n',
    b'        if false then -- MUT: gains section gone\r\n')

# 任务难度行不显示（nfu 彩色档位数字没了）。
MUT_NO_DIFF = (
    b'    if q[13] and #q[13] > 0 then\r\n',
    b'    if false then -- MUT: no difficulty line\r\n')

# 详情职业专属行不显示。
MUT_NO_CLS_LINE = (
    b'    if q[15] then\r\n',
    b'    if false then -- MUT: no class line\r\n')

# 「任务需求」节不显示（需要提供的物品被藏掉）。
MUT_NO_REQ_SECT = (
    b'        if hasChips or objTxt then\r\n',
    b'        if false then -- MUT: no required-items section\r\n')

# 奖励退回单列（右列又空一大截）。
MUT_CHIP_1COL = (
    b'        y = y - renderChips(rew, 2) * (DG.Q_DET_ICON + 8) - 2\r\n',
    b'        y = y - renderChips(rew, 1) * (DG.Q_DET_ICON + 8) - 2 -- MUT: single column\r\n')

# 左列行内职业小卡片消失。
MUT_ROW_CLS_GONE = (
    b'                local clsList = DG.QClassList(q[15])\r\n',
    b'                local clsList = nil -- MUT: row class badge gone\r\n')

# 「下一步」进度标不出现（用户看不到做到哪了）。
MUT_NO_FRONTIER = (
    b'                    if frontier and pok and pst ~= "done" then\r\n',
    b'                    if false then -- MUT: no frontier marker\r\n')

# 悬停离开后选中态被冲掉（OnLeave 不按选中复位）。
MUT_SEL_LEAVE = (
    b'                    HuiCardState(self, (self.__q and self.__q[1] == U.dungeonQuestSel) and "hover" or "norm")\r\n',
    b'                    HuiCardState(self, "norm") -- MUT: selection lost on leave\r\n')

# 卡中卡提亮被撤：任务行退回 L1 底（与外底板同档 → 层次糊掉，用户 2026-10-10 定规则）。
# 期望：静态「卡中卡必须提亮」失败。
MUT_INNER_L1_QROW = (
    b'            HuiCardFX(r, 12, 2)\r\n',
    b'            HuiCardFX(r, 12) -- MUT: inner same level\r\n')

# 卡中卡提亮被撤：NPC 节点行退回 L1 底。期望：静态「卡中卡必须提亮」失败。
MUT_INNER_L1_NODE = (
    b'            HuiCardFX(r, 10, 2)\r\n',
    b'            HuiCardFX(r, 10) -- MUT: inner same level\r\n')

# 档位路由失效：HuiCardFX 忽略 baseN=2（内卡底退回 L1 + 悬停退回 L3）。
# 注意原行是 if/elseif 链的中段（无 end），变异只能让条件为假、不能加 end（会语法崩）。
# 期望：静态「卡中卡必须提亮」失败。
MUT_INNER_ROUTE = (
    b'    if baseN == 2 then base, hov = lv.L2, lv.L4\r\n',
    b'    if false then base, hov = lv.L2, lv.L4 -- MUT: level route gone\r\n')

# 奖励芯片重新用单变量接 QColor（实机 Unpack 崩，收尾隐藏循环不跑，旧控件残留重叠）。
# 期望：静态「QColor 多变量接」失败。
MUT_QC_SINGLE = (
    b'                local qr, qg, qb = DG.QColor(DG.QualOf(iid))\r\n'
    b'                if qr then\r\n'
    b'                    r.name:SetTextColor(qr, qg, qb)\r\n',
    b'                local qc = DG.QColor(DG.QualOf(iid)) -- MUT: single var\r\n'
    b'                if qc then\r\n'
    b'                    r.name:SetTextColor(Unpack(qc))\r\n')

# 摘掉底板卡的页签显隐（板子永远出不来）。期望：静态「底板卡」失败。
MUT_NO_PLATE = (
    b'    if U.dungeonQPlateL then U.dungeonQPlateL:SetShown(isQuest) end\r\n'
    b'    if U.dungeonQPlateR then U.dungeonQPlateR:SetShown(isQuest) end\r\n',
    b'    -- MUT: plates never shown\r\n')

# 第二列又不剥坐标（地图名带 63,37）。期望：静态「只显示大地图名」失败。
MUT_ROW_GIVER = (
    b'    s = s:gsub("%s*[%d%.]+%s*,%s*[%d%.]+%s*$", "")\r\n',
    b'    -- MUT: coords not stripped\r\n')

# 节点取件不复位常态色（实机首次渲染白卡，悬停才恢复）。
# 期望：静态「节点取件复位常态色」失败。
MUT_NODE_RESET = (
    b'        if not r.__huiCard then\r\n'
    b'            r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)\r\n'
    b'            r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)\r\n'
    b'        end\r\n'
    b'        return r\r\n',
    b'        -- MUT: no node color reset\r\n'
    b'        return r\r\n')

# 阵营档退回「只看本阵营专属」（双阵营通用任务不再跟随显示）。期望：静态「阵营档含双阵营」失败。
MUT_SIDE_NO_NEUTRAL = (
    b'        if q[2] == side or not q[2] then\n'
    b'            local key = q[8] and 2 or 1\n',
    b'        if q[2] == side then -- MUT: no neutral\n'
    b'            local key = q[8] and 2 or 1\n')

# 右列详情名不再带 #任务ID。期望：静态「详情名带任务ID」失败。
MUT_NO_QID = (
    b'    if hasName then nm = nm .. format(" |cff9a9a9a#%d|r", q[1]) end\r\n'
    b'    name:SetText(nm)\r\n',
    b'    -- MUT: no quest id\r\n'
    b'    name:SetText(nm)\r\n')

# 板卡退回重叠几何（右板左缘吃掉 Q_DET_GAP ⇒ 与左板间隙 0 / 重叠）。期望：静态「板卡不重叠」失败。
# 2026-10-10 重锚：板几何改为 GUTTER 栅格（板L = GUTTER…GUTTER+Q_LIST_W，板R 左缘 = +Q_DET_GAP）。
MUT_PLATE_OVERLAP = (
    b'    plateR:SetPoint("TOPLEFT", detail, "TOPLEFT",\r\n'
    b'                    DG.Q_LIST_W + DG.Q_DET_GAP, -DG.FILTER_Y)\r\n',
    b'    plateR:SetPoint("TOPLEFT", detail, "TOPLEFT",\r\n'
    b'                    DG.Q_LIST_W, -DG.FILTER_Y) -- MUT: overlap\r\n')

# ── 跨插件命名空间（2026-09-23 实机事故） ──────────────────────────────────
# 页面构建函数脱掉 DG. 前缀退回**裸全局**：WoW 按文件夹名字母序加载，
# DungeonsForever 先、上游插件后 → 上游同名全局静默覆盖本插件，
# U:SwitchSub 里那句调用于是跑的是上游函数体（上游 U.dungeonPage 为 nil）
# → MakeFS(nil) → 实机 attempt to index local 'parent' (a nil value)。
# 期望：静态「界面层不定义裸全局函数」+「挂在 local 表 DG 上」双双失败。
# 注意：变异是 bytes，注释只能英文。
MUT_BARE_GLOBAL = (
    b'function DG.BuildDungeons()\r\n',
    b'function BuildDungeons() -- MUT: bare global (cross-addon clash)\r\n')

MUT_CAPSULE_NO_LIFT = (
    b'    host:SetPoint("TOP", U.panel, "TOP", 0, DG.CAPSULE_LIFT - ROW_SUB)\r\n',
    b'    host:SetPoint("TOP", U.panel, "TOP", 0, -ROW_SUB) -- MUT: capsule lift gone\r\n')

MUT_RAID_TAB_GONE = (
    b'        { key = "Raids",    text = L["\xe5\x9b\xa2\xe6\x9c\xac"],  width = DG.CAPSULE_W },\r\n',
    b'        -- MUT: raid tab removed\r\n')

MUT_SWITCH_IGNORES_KEY = (
    b'    local k = "Dungeons"\r\n'
    b'    if key == "Raids" then\r\n'
    b'        k = "Raids"\r\n'
    b'    elseif key == "Professions" and ns.LoadForeverPages then\r\n'
    b'        k = "Professions"\r\n'
    b'    elseif key == "Explore" and ns.LoadForeverPages then\r\n'
    b'        k = "Explore"\r\n'
    b'    elseif key == "Collections" and ns.LoadForeverPages then\r\n'
    b'        k = "Collections"\r\n'
    b'    elseif key == "Factions" and ns.LoadForeverPages then\r\n'
    b'        k = "Factions"\r\n'
    b'    elseif key == "Bis" and ns.LoadForeverPages then\r\n'
    b'        k = "Bis"\r\n'
    b'    elseif key == "Tier" and ns.LoadForeverPages then\r\n'
    b'        k = "Tier"\r\n'
    b'    elseif key == "PvP" and ns.LoadForeverPages then\r\n'
    b'        k = "PvP"\r\n'
    b'    elseif key == "Gear" and ns.LoadForeverPages then\r\n'
    b'        k = "Gear"\r\n'
    b'    end\r\n',
    b'    local k = "Dungeons" -- MUT: switch key ignored (always 5-man)\r\n')

MUT_RAID_SHOW_BOTH = (
    b'    if U.dungeonPage then U.dungeonPage:SetShown(isDun) end\r\n',
    b'    if U.dungeonPage then U.dungeonPage:SetShown(true) end -- MUT: both pages shown\r\n')

MUT_UAS_NO_SKIP = (
    b'    if self.curSub == "Raids" then return end\r\n',
    b'    -- MUT: no raid skip\r\n')

MUT_NPCLOC_EMPTY = ('Core/Data/Data_NPCLoc.lua', (
    b'ns.NPCLoc = {\n',
    b'ns.NPCLoc = { } -- MUT: npc loc emptied\nns._npc_dead = {\n'))

MUT_PRE_NPCID_EMPTY = ('Core/Data/Data_NPCLoc.lua', (
    b'ns.QuestPreNpcID = {\n',
    b'ns.QuestPreNpcID = { } -- MUT: pre-npcid map emptied\nns._qpn_dead = {\n'))

MUT_SW_COORD_STALE = ('Core/Data/Data_NPCLoc.lua', (
    b'    [5413] = { 1453, 64.6, 37.2,',
    b'    [5413] = { 1453, 57.4, 16.0,'))

MUT_CLICK_NO_SHIFT = (
    b'    if type(IsShiftKeyDown) == "function" and IsShiftKeyDown() then\r\n',
    b'    if type(IsShiftKeyDown) == "function" then -- MUT: shift check gone\r\n')

MUT_CLICK_NO_FALLBACK = (
    b'    return "item:" .. tostring(id) .. ":0:0:0:0:0:0:0"\r\n',
    b'    return nil -- MUT: no item-string fallback\r\n')

MUT_CLICK_FRAME = (
    b'        r = CreateFrame("Button", nil, child, "BackdropTemplate")\r\n'
    b'        r:SetSize(cw, DG.LOOT_CARD_H)\r\n',
    b'        r = CreateFrame("Frame", nil, child, "BackdropTemplate") -- MUT: frame cannot click\r\n'
    b'        r:SetSize(cw, DG.LOOT_CARD_H)\r\n')

MUT_CLICK_NO_OPENCHAT = (
    b'    if type(ChatFrame_OpenChat) == "function" then\r\n'
    b'        ChatFrame_OpenChat(link)\r\n'
    b'        return true\r\n'
    b'    end\r\n',
    b'    if false then -- MUT: no open-chat path\r\n'
    b'    end\r\n')

MUT_CLICK_ANY_BUTTON = (
    b'    if button ~= "LeftButton" then return false end\r\n',
    b'    if false then return false end -- MUT: any button accepted\r\n')

MUT_TIP_ITEM_SKIN = ('Core/Hui.lua', (
    b'                if on and TooltipHasItemContent(tt) then on = false end\r\n',
    b'                if on and ttItemMark[tt] then on = false end -- MUT: mark only\r\n'))

MUT_PROF_RANKS_GONE = ('Core/Data/Data_Professions.lua', (
    b'            ranks = {\n',
    b'            _ranks_dead = { -- MUT: ranks never emitted\n'))

MUT_PROF_CAPSULE_GONE = (
    b'        defs[#defs + 1] = { key = "Professions", text = L["\xe4\xb8\x93\xe4\xb8\x9a"], width = DG.CAPSULE_W }\r\n',
    b'        -- MUT: profession capsule removed\r\n')

MUT_PROF_GSUB_MULTI = ('Core/ProfessionUI.lua', (
    b'            if book then note = note:gsub("{book}", (DG.ItemName(book))) end\n',
    b'            if book then note = note:gsub("{book}", DG.ItemName(book)) end -- MUT: multi-return into gsub\n'))

MUT_PROF_ROW_FRAME = ('Core/ProfessionUI.lua', (
    b'    r = CreateFrame("Button", nil, PD.child, "BackdropTemplate")\n',
    b'    r = CreateFrame("Frame", nil, PD.child, "BackdropTemplate") -- MUT: frame cannot click\n'))

MUT_PROF_SETPARENT = ('Core/ProfessionUI.lua', (
    b'    scroll:SetScrollChild(child)\n',
    b'    scroll:SetScrollChild(child)\n    child:SetParent(scroll) -- MUT: live SetParent\n'))

MUT_PROF_RENDER_FRAME = ('Core/ProfessionUI.lua', (
    b'function PD.Render()\n',
    b'function PD.Render()\n    PD._mutFrame = CreateFrame("Frame", nil, PD.page) -- MUT: render builds frame\n'))

MUT_PROF_FISH_SPLIT = ('Core/ProfessionUI.lua', (
    b'    if PD.cur == "fishing" then\n        PD.RowsFishing(rows)\n        return\n    end\n',
    b'    -- MUT: fishing no longer split out\n'))

MUT_PROF_BIGCARD_UNPOS = ('Core/ProfessionUI.lua', (
    b'    PD.listCard:ClearAllPoints()\n    PD.listCard:SetPoint("TOPLEFT", PD.page, "TOPLEFT",\n                         PD.RIGHT_X - PD.LIST_PAD, -PD.CARD_TOP)\n    PD.listCard:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT",\n                         -PD.CARD_INSET, PD.CARD_INSET)\n',
    b'    PD.listCard:ClearAllPoints()\n    -- MUT: big card never positioned\n'))

MUT_PROF_NAVCARD_GONE = ('Core/ProfessionUI.lua', (
    b'    PD.navCard = PD.MakeCard(page)\n    PD.navCard:SetPoint("TOPLEFT", page, "TOPLEFT", PD.CARD_INSET, -PD.CARD_TOP)\n',
    b'    -- MUT: nav card gone\n'))

MUT_PROF_FACICON_BACK = ('Core/ProfessionUI.lua', (
    b'kind = "row", col = 1, nameColor = fc, icon = PD.FAC_ICON[side],\n',
    b'kind = "row", col = 1, nameColor = fc, fs = 14, icon = vd[4], -- MUT: faction icon reverted\n'))

MUT_PROF_ROW_CARD = ('Core/ProfessionUI.lua', (
    b'    r.__hlOn = false\n    PD.SetRowHover(r, false)\n',
    b'    r.__hlOn = false\n    r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG) -- MUT: row keeps its own card\n    r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE) -- MUT\n'))

MUT_PROF_TIER_NOCLR = ('Core/ProfessionUI.lua', (
    b'                           PD.TierText(r[8], r[9], r[10])) or nil,\n',
    b'                           tostring(r[8]) .. "/" .. tostring(r[9]) .. "/" .. tostring(r[10])) or nil, -- MUT: tier colour dropped\n'))

MUT_PROF_TIER_SAMECLR = ('Core/ProfessionUI.lua', (
    b'PD.TIER_HEX = { "|cffffd100", "|cff40d940", "|cff8c8c8c" }\n',
    b'PD.TIER_HEX = { "|cffffd100", "|cffffd100", "|cffffd100" } -- MUT: one colour for all three\n'))

MUT_PROF_TABS_REGROW = ('Core/ProfessionUI.lua', (
    b'    { key = "writ",     text = L["\xe5\xb7\xa5\xe5\x8c\xa0\xe6\x96\x87\xe4\xb9\xa6"] },\n}\n',
    b'    { key = "writ",     text = L["\xe5\xb7\xa5\xe5\x8c\xa0\xe6\x96\x87\xe4\xb9\xa6"] },\n'
    b'    { key = "legacy",   text = "Legacy" }, -- MUT: merged tab regrows\n}\n'))

MUT_PROF_TOOL_FIXEDW = ('Core/ProfessionUI.lua', (
    b'            bt:SetSize(w, PD.TOOL_H)\n',
    b'            bt:SetSize(PD.TOOL_W, PD.TOOL_H) -- MUT: fixed width back\n'))

MUT_PROF_NEW_TAG_GONE = ('Core/ProfessionUI.lua', (
    '    r.b:SetText((spec.is_new and L[" |cff40d940新|r"] .. " " or "") .. (spec.sub or ""))\n'.encode('utf-8'),
    '    r.b:SetText(spec.sub or "") -- MUT: NEW tag dropped\n'.encode('utf-8')))

MUT_PROF_READ_BACK = ('Core/ProfessionUI.lua', (
    b'    if s.drops and #s.drops > 0 then\n        out[#out + 1] = { text = format(L["\xe6\x8e\x89\xe8\x90\xbd %d \xe5\xa4\x84"], #s.drops) }\n    end\n',
    b'    if s.read then out[#out + 1] = { text = format(L["\xe8\xaf\xbb\xe7\x89\xa9\xef\xbc\x9a%s"], tostring(s.read)) } end -- MUT: read back\n    if s.drops and #s.drops > 0 then\n        out[#out + 1] = { text = format(L["\xe6\x8e\x89\xe8\x90\xbd %d \xe5\xa4\x84"], #s.drops) }\n    end\n'))

MUT_PROF_MERGE_GONE = ('Core/ProfessionUI.lua', (
    b'        PushHead(rows, L["\xe4\xbc\xa0\xe6\x89\xbf"], 1)\n',
    b'        -- MUT: legacy section dropped from overview\n'))

MUT_PROF_CAMP_BONUS_GONE = ('Core/ProfessionUI.lua', (
    b'            PD.campView = "bonus"\n            PD.wantBonusTable = true\n',
    b'            -- MUT: camping bonus table raise gone\n'))

MUT_PROF_ROW_NARROW = ('Core/ProfessionUI.lua', (
    b'                    x, w = PD.LIST_PAD, ROW_W\n',
    b'                    x, w = PD.LIST_PAD, PD.COL_LW -- MUT: single-col pages narrowed\n'))

MUT_PROF_STEP_SKILL = ('Core/ProfessionUI.lua', (
    b'                rng = format(L["%s \xe2\x80\x93 %s"], tostring(st[1]), tostring(st[2])),\n',
    b'                rng = format(L["\xe6\x8a\x80\xe8\x83\xbd %s \xe2\x86\x92 %s"], tostring(st[1]), tostring(st[2])), -- MUT: skill prefix back\n'))

MUT_PROF_SHOP_RIGHT_GONE = ('Core/ProfessionUI.lua', (
    b'    PushHead(rows, format(L["\xe6\x9d\x90\xe6\x96\x99\xef\xbc\x88%d \xe7\xa7\x8d\xef\xbc\x89"], #mats), 1)\n',
    b'    PushHead(rows, format(L["\xe6\x9d\x90\xe6\x96\x99\xef\xbc\x88%d \xe7\xa7\x8d\xef\xbc\x89"], #mats), 2) -- MUT: mats list back to right column\n'))

MUT_PROF_STEP_NOCNT = ('Core/ProfessionUI.lua', (
    b'        r.c:SetText(spec.cnt or "")\n',
    b'        r.c:SetText("") -- MUT: craft count dropped\n'))

MUT_PROF_DUP_CAMP = ('Core/ProfessionUI.lua', (
    b'                text = c[2] or "?",\n',
    b'                text = format(L["\xe6\x8a\x80\xe8\x83\xbd %d \xc2\xb7 %s"], c[4] or 0, c[2] or "?"), -- MUT: old camp trio row back\n'))

MUT_PROF_MATICON_GONE = ('Core/ProfessionUI.lua', (
    b'        t[#t + 1] = format("%d\xc3\x97%s%s", m[2] or 1, PD.MatIconTex(m[1]), DG.ItemName(m[1]))\n',
    b'        t[#t + 1] = format("%d\xc3\x97%s", m[2] or 1, DG.ItemName(m[1])) -- MUT: mat icon dropped\n'))

MUT_PROF_DETAIL_BACK = ('Core/ProfessionUI.lua', (
    b'    PD.secCards = {}\n',
    b'    PD.detail = CreateFrame("Frame", nil, page) -- MUT: detail back\n'
    b'    PD.secCards = {}\n'))

MUT_PROF_MATCOL_BACK = ('Core/ProfessionUI.lua', (
    b'        local sg\n        s.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)\n        s.matSegs = sg\n',
    b'            s.sub = s.sub .. "   " .. PD.MatText(s._mats, 4) -- MUT: mats back into sub\n            s.mats = ""\n            s.matSegs = nil\n'))

MUT_PROF_COL_RATIO_FLAT = ('Core/ProfessionUI.lua', (
    b'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)\n',
    b'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * 0.50) -- MUT: columns evened out\n'))

MUT_PROF_MAT_FS_WIRING = ('Core/ProfessionUI.lua', (
    b'    r.f = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")\n',
    b'    r.f = MakeFS(r, 11, C_TEXT, "LEFT") -- MUT: font size bypassed\n'))

MUT_PROF_LVSPLIT_GONE = ('Core/ProfessionUI.lua', (
    b'        PD.lvSplit = true\n',
    b'        PD.lvSplit = false -- MUT: split line not raised\n'))

# 2026-10-10 三列拆分：数据行（lvstep）次数 @LV_CNT2_R，lvhead 表头同名锚点在前 ——
#   锚文取 lvstep 独有的「d:SetPoint(UNIT_R) → c:Clear → c:SetPoint(CNT2_R)」三行序（恰好 1 次）。
MUT_PROF_CNT_AGAIN_MATS = ('Core/ProfessionUI.lua', (
    b'        r.d:SetPoint("RIGHT", r, "RIGHT", -PD.LV_UNIT_R, 0)\n'
    b'        r.c:ClearAllPoints()\n'
    b'        r.c:SetPoint("RIGHT", r, "RIGHT", -PD.LV_CNT2_R, 0)\n',
    b'        r.d:SetPoint("RIGHT", r, "RIGHT", -PD.LV_UNIT_R, 0)\n'
    b'        r.c:ClearAllPoints()\n'
    b'        r.c:SetPoint("RIGHT", r, "RIGHT", -140, 0) -- MUT: count off the column edge\n'))

MUT_PROF_DIV_FAINT = ('Core/ProfessionUI.lua', (
    b'    divider:SetColorTexture(1, 1, 1, 0.12)\n',
    b'    divider:SetColorTexture(1, 1, 1, 0.02) -- MUT: split line invisible\n'))

MUT_PROF_LV_STEP_MATS_GONE = ('Core/ProfessionUI.lua', (
    b'        PD.PaintMats(r, spec.blocks, spec.matCut, spec.passed)\n',
    b'        -- MUT: per-step mats dropped again\n'))

MUT_PROF_LVNAME_FIXED = ('Core/ProfessionUI.lua', (
    b'    PD.LV_ICON_X = 6 + math.ceil(rngW) + PD.TBL_RNG_GAP\n',
    b'    PD.LV_ICON_X = 6 + PD.TBL_RNG_GAP -- MUT: range column width fixed\n'))

MUT_PROF_HL_LEAVE_BG = ('Core/ProfessionUI.lua', (
    b'        r:SetBackdropColor(1, 1, 1, 0)\n        r:SetBackdropBorderColor(1, 1, 1, 0)\n',
    b'        r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG) -- MUT: leave writes normal colour\n        r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE) -- MUT\n'))

MUT_PROF_HL_NOSYNC = ('Core/ProfessionUI.lua', (
    b'    local hlAcc = 0\n    child:SetScript("OnUpdate", function(_, el)\n        hlAcc = hlAcc + el\n        if hlAcc < 0.1 then return end\n        hlAcc = 0\n        PD.SyncHover()\n    end)\n',
    b'    -- MUT: hover resync dropped\n'))

MUT_PROF_HL_ALWAYSOFF = ('Core/ProfessionUI.lua', (
    b'        if over ~= r.__hlOn then PD.SetRowHover(r, over) end\n',
    b'        PD.SetRowHover(r, false) -- MUT: sync only turns off\n'))

MUT_PROF_FAVOR_LABEL = ('Core/ProfessionUI.lua', (
    b'        right2 = format(L["\xe5\x95\x86\xe4\xba\xba\xe9\x9d\x92\xe7\x9d\x90 %s"], tostring(f[3])),\n',
    b'        right2 = format(L["\xe6\x81\xa9\xe6\x83\xa0 %s"], tostring(f[3])), -- MUT: old name back\n'))

MUT_PROF_LVCOL_RW_FLAT = ('Core/ProfessionUI.lua', (
    b'PD.COL_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.COL_LW\n',
    b'PD.COL_RW = PD.COL_LW -- MUT: right column keeps its width\n'))

MUT_PROF_LVNAMEW_FAT = ('Core/ProfessionUI.lua', (
    b'    PD.LV_NAME_W = math.min(PD.TBL_NAME_MAX, math.max(PD.TBL_NAME_MIN, math.ceil(nameW)))\n',
    b'    PD.LV_NAME_W = 150 -- MUT: name column fixed fat\n'))

MUT_PROF_LVMAT_CNTGAP = ('Core/ProfessionUI.lua', (
    b'    PD.LV_MAT_W = avail - PD.LV_NAME_W\n',
    b'    PD.LV_MAT_W = PD.COL_LW - PD.LV_NAME_X - PD.LV_NAME_W -- MUT: mat area eats the count column\n'))

MUT_PROF_LVMAT_NAMEGAP = ('Core/ProfessionUI.lua', (
    b'    local avail = rowW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP\n',
    b'    local avail = rowW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - 20 -- MUT: name-to-mats gap fattened\n'))

MUT_PROF_ZONENAME_RAW = ('Core/ProfessionUI.lua', (
    b'    if type(fn) == "function" then\n',
    b'    if false then -- MUT: zone name stops asking the client\n'))

MUT_PROF_NODE_TITLE_RAW = ('Core/ProfessionUI.lua', (
    b'        if not got then nm = head and format(L["\xe7\x89\xa9\xe5\x93\x81 #%d"], head) or "?" end\n',
    b'        nm = head and format(L["\xe7\x89\xa9\xe5\x93\x81 #%d"], head) or "?" -- MUT: node title never uses client\n'))

MUT_PROF_FISH_GRID_OFF = ('Core/ProfessionUI.lua', (
    b'        PD.gridSplit = (PD.cur == "fishing")\n',
    b'        PD.gridSplit = false -- MUT: fishing back to single column\n'))

MUT_PROF_GRID_ONE_COL = ('Core/ProfessionUI.lua', (
    b'                    col = (y[2] < y[1]) and 2 or 1\n',
    b'                    col = 1 -- MUT: grid stops balancing columns\n'))

MUT_PROF_LV_TBL_ICON_DIFF = ('Core/ProfessionUI.lua', (
    b'        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n',
    b'        r.icon:SetSize(20, 20) -- MUT: formula icon size differs\n'))

MUT_PROF_LV_TBL_MAT_ICON_DIFF = ('Core/ProfessionUI.lua', (
    b'    b.ic:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n',
    b'    b.ic:SetSize(24, 24) -- MUT: material icon size differs\n'))

MUT_PROF_LV_TBL_SRC_GONE = ('Core/ProfessionUI.lua', (
    # 2026-10-10：卡片宽全页统一固定，PaintCard 回到两参
    b'        PD.PaintCard(r, spec.card)\n',
    b'        PD.PaintCard(r, nil) -- MUT: source card dropped\n'))

# 十一轮（2026-10-09 用户：「这个竖线我希望显示两根」）：只画一根 / 第二根丢了。
#   锚点取 PaintSkillBar 里两行闭包（注释 + lvs 表 + 循环头），全局唯一。
#   期望：双 harness 的「两根竖线 = 本行技能区间两端」那条失败。
MUT_PROF_LV_PIN_DUAL_GONE = ('Core/ProfessionUI.lua', (
    b'    local lvs = { lvLo, lvHi }\n',
    b'    local lvs = { lvLo, nil } -- MUT: second level pin dropped\n'))

# 2026-10-09 十三轮（用户）：「106 已大于 100，第二根线要放 100 右边」→ 终点改「向上吸」。
#   若终点退回「向下吸」（写成 false / 传错参数），106 会落回 0.50 = 100 那道交界，用户报的 bug 复现。
#   期望：双 harness 的「两根竖线两头分向吸附」那条失败（起点向下 / 终点向上）。
MUT_PROF_LV_PIN_HI_NO_UP = ('Core/ProfessionUI.lua', (
    b'local xb = PD.SBValPos(lvs[2], vals[1], vals[2], vals[3], vals[4], true)',
    b'local xb = PD.SBValPos(lvs[2], vals[1], vals[2], vals[3], vals[4], false) -- MUT: hi pin snaps down again\n'))

MUT_PROF_LV_TBL_SRC_SAMEY = ('Core/ProfessionUI.lua', (
    b'        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)\n',
    b'        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.TBL_NAME_DY) -- MUT: bar onto name line\n'))

MUT_PROF_LV_TBL_NO_MARK_ROOM = ('Core/ProfessionUI.lua', (
    b'        if total + step + PD.TBL_MARK_W > budget then\n',
    b'        if total + step > budget then -- MUT: no room kept for the ellipsis\n'))

MUT_PROF_LV_TBL_GROUP_LEFT = ('Core/ProfessionUI.lua', (
    b'    local right = W - PD.TBL_MAT_RPAD\n',
    b'    local right = PD.TBL_MAT_RPAD -- MUT: material group not right-aligned\n'))

MUT_PROF_LV_TBL_CNT_ZERO = ('Core/ProfessionUI.lua', (
    b' blk.cnt))\n',
    b' 0)) -- MUT: count badge zeroed\n'))

MUT_QPRENOTE_OFF = ('Core/DungeonUI.lua', (
    b'        if pnote then\r\n',
    b'        if false then -- MUT: pre-note never renders\r\n'))

MUT_QPRENOTE_WRONGKEY = ('Core/Data/Data_DungeonQuests.lua', (
    b'    [2040] = "',
    b'    [9999] = "'))

# ── 副本入口标记（2026-09-24 用户要求）──────────────────────────────────────
# 详细说明见本文件生成器（mk_df_mut.py）的 ㉘ 步注释。
MUT_ENT_LOOKUP_DEAD = (
    b'function DG.MarkEntrance(dungeonID)\r\n',
    b'function DG.MarkEntrance(dungeonID)\r\n'
    b'    dungeonID = nil -- MUT: entrance id dropped (lookup never resolves)\r\n')

MUT_ENT_TITLE_UNBOUND = (
    b'    U.dungeonDetailTitle:SetScript("OnMouseUp", function()\r\n'
    b'        local dd = U.dungeonDetailCur\r\n'
    b'        if dd then DG.MarkEntrance(dd.id) end\r\n'
    b'    end)\r\n',
    b'    -- MUT: entrance title click unbound\r\n')

MUT_ENT_FALLBACK_COORD = (
    b'    local loc = dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID]\r\n'
    b'    if not loc then\r\n',
    b'    local loc = (dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID])\r\n'
    b'        or { 1453, 50.4, 66.4, "" } -- MUT: fallback coord when entrance unknown\r\n'
    b'    if not loc then\r\n')

MUT_PROF_LV_ZEBRA_A0 = ('Core/ProfessionUI.lua', (
    b'        r:SetBackdropColor(1, 1, 1, PD.ZEBRA_A)\n',
    b'        r:SetBackdropColor(1, 1, 1, 0) -- MUT: zebra invisible\n'))

MUT_PROF_LV_ZEBRA_ZGONE = ('Core/ProfessionUI.lua', (
    b'    r.__z = spec.z and true or false\n',
    b'    r.__z = false -- MUT: never striped\n'))

MUT_ENT_ROUTE_GONE = ('Core/DungeonUI.lua', (
    b'        local route = d and ns.DungeonEntryRoute and ns.DungeonEntryRoute[d.id]\r\n',
    b'        local route = nil -- MUT: entrance route points dropped\r\n'))

MUT_PROF_LV_CNT_NOEDGE = ('Core/ProfessionUI.lua', (
    b'    b.ct:SetShadowOffset(1, -1)\n',
    b'    b.ct:SetShadowOffset(0, 0) -- MUT: count badge edge dropped\n'))

MUT_PROF_LV_CNT_NOTHICK = ('Core/ProfessionUI.lua', (
    b'    b.ct:SetFont(ns.FONT, PD.TBL_MAT_CNT_FS, "THICKOUTLINE")\n',
    b'    b.ct:SetFont(ns.FONT, PD.TBL_MAT_CNT_FS, "") -- MUT: thick edge dropped\n'))

MUT_ENT_CHIP_IDX0 = ('Core/DungeonUI.lua', (
    b'        chip.__entIdx = i\r\n',
    b'        chip.__entIdx = 0 -- MUT: chip index zeroed\r\n'))

MUT_IX_GRID_BUILT = ('Core/ProfessionUI.lua', (
    b'    PD.BuildIndexGrid(child)\n',
    b'    -- MUT: index grid never built\n'))

MUT_IX_GRID_RAISE = ('Core/ProfessionUI.lua', (
    b'        PD.wantIndexGrid = (PD.cur == "__index")\n',
    b'        PD.wantIndexGrid = false -- MUT: never raised\n'))

MUT_IX_HOVER = ('Core/ProfessionUI.lua', (
    b'            if over ~= c.__hlOn then PD.SetCardHover(c, over) end\n',
    b'            if over ~= c.__hlOn then PD.SetCardHover(c, false) end -- MUT\n'))

MUT_IX_NOTE_GONE = ('Core/ProfessionUI.lua', (
    b'    PD.ixNote = MakeFS(root, 10, C_GREY, "CENTER")\n',
    b'    -- MUT: note gone\n'))

MUT_CAMP_MARK_GONE = ('Core/ProfessionUI.lua', (
    b'                act = function() PD.MarkCampPoint(vd[7], vd[5], vd[6]) end,\n',
    b'                act = function() end -- MUT: camp mark gone\n'))

MUT_BONTAB_OFF = ('Core/ProfessionUI.lua', (
    b'            PD.wantBonusTable = true\n',
    b'            PD.wantBonusTable = false -- MUT: bonus table off\n'))

MUT_BONTAB_NOCMP = ('Core/ProfessionUI.lua', (
    b'                r.cmp2:SetText(format("|cff7fdc7f%s|r", buffTxt))\n',
    b'                r.cmp2:SetText("") -- MUT: compare column emptied\n'))

MUT_BONTAB_NOFILL = ('Core/ProfessionUI.lua', (
    b'        local r = root.__rows[used + 1]\n',
    b'        local r = nil -- MUT: fill loop dropped\n'))

MUT_EXPLORE_TAB_GONE = (
    b'        defs[#defs + 1] = { key = "Explore", text = L["\xe6\x8e\xa2\xe7\xb4\xa2"], width = DG.CAPSULE_W }\r\n',
    b'        -- MUT: explore tab removed\r\n')

MUT_EXPLORE_KEY_DROPPED = (
    b'        k = "Explore"\r\n',
    b'    -- MUT: explore switch dropped\r\n')

MUT_EXPLORE_PAGE_GONE = (
    b'        ns.ExploreModule.Build(U.explorePage)\r\n',
    b'        -- MUT: explore page build dropped\r\n')

MUT_NAV_LEARN_GREY = ('Core/ProfessionUI.lua', (
    b'                bt:GetFontString():SetTextColor(NavAccent())\n',
    b'                bt:GetFontString():SetTextColor(Unpack(C_DIM)) -- MUT: learned green turned grey\n'))

MUT_NAV_LV_GONE = ('Core/ProfessionUI.lua', (
    b'            bt.__lv:SetText(format("%d/%d", lv.cur, lv.max))\n',
    b'            bt.__lv:SetText("") -- MUT: learned level text dropped\n'))

MUT_NAV_SLUG_FA_GONE = ('Core/ProfessionUI.lua', (
    b'[129] = "first-aid",\n',
    b'[129] = nil, -- MUT: first-aid mapping dropped\n'))

MUT_LV_PASSED_OFF = ('Core/ProfessionUI.lua', (
    b"            local passed = (greyOn and over) or nil\n",
    b"            local passed = nil -- MUT: passed grey disabled\n"))

MUT_LV_PASSED_NOICON = ('Core/ProfessionUI.lua', (
    b"        r.icon:SetDesaturated(spec.passed and true or false)\n",
    b"        r.icon:SetDesaturated(false) -- MUT: icon desaturate dropped\n"))

MUT_PROF_SET_GREY_DEF = ('Core/ProfessionUI.lua', (
    b"PD.SETTING_DEF = { greyPassed = true, hlCurrent = true }\n",
    b"PD.SETTING_DEF = { greyPassed = false, hlCurrent = true } -- MUT: default flipped\n"))

MUT_PROF_SET_CUR_GONE = ('Core/ProfessionUI.lua', (
    b"                spec.cur = true\n",
    b"                do end -- MUT: current-segment mark gone\n"))

MUT_PROF_SET_BORDER_GONE = ('Core/ProfessionUI.lua', (
    b"    r.bT:SetShown(show)\n",
    b"    r.bT:SetShown(false) -- MUT: border strip never shown\n"))

MUT_PROF_SET_PAGE_GONE = ('Core/ProfessionUI.lua', (
    b"        PD.RowsSettings(rows)\n",
    b"        -- MUT: settings page unreachable\n"))

MUT_PROF_HELP_GONE = ('Core/ProfessionUI.lua', (
    b'                hp.__tip = spec.help\n',
    b'                -- MUT: help icon tooltip unbound\n'))

MUT_PROF_SET_TOG_GONE = ('Core/ProfessionUI.lua', (
    b"            tg.__key = spec.togKey\n",
    b"            do end -- MUT: toggle unbound\n"))

MUT_GUIDE_TAB_GONE = (
    b'    local tabs = { { key = "loot", text = L["\xe6\x8e\x89\xe8\x90\xbd"] }, { key = "quest", text = L["\xe4\xbb\xbb\xe5\x8a\xa1"] }, { key = "guide", text = L["\xe6\x94\xbb\xe7\x95\xa5"] }, { key = "map", text = L["\xe5\x9c\xb0\xe5\x9b\xbe"] } }\r\n',
    b'    local tabs = { { key = "loot", text = L["\xe6\x8e\x89\xe8\x90\xbd"] }, { key = "quest", text = L["\xe4\xbb\xbb\xe5\x8a\xa1"] }, { key = "map", text = L["\xe5\x9c\xb0\xe5\x9b\xbe"] } }\r\n')

MUT_GUIDE_DISPATCH_LOOT = (
    b'        U:RenderDungeonGuide()\r\n',
    b'        U:RenderDungeonLoot() -- MUT: guide tab renders loot\r\n')

MUT_GUIDE_KEEP_SCROLL = (
    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide and not isMap) end\r\n',
    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest) end -- MUT: scroll no longer yields\r\n')

MUT_PROF_SPEEDVIEW_BACK = ('Core/ProfessionUI.lua', (
    b'    if p.racials and #p.racials > 0 then\n',
    b'    PushHead(rows, L["\xe6\x95\xb0\xe5\xad\x97\xe9\x80\x9f\xe8\xa7\x88"], 1) -- MUT: speedview revived\n    if p.racials and #p.racials > 0 then\n'))

MUT_PROF_GEAR_MISALIGN = ('Core/ProfessionUI.lua', (
    b'    gear:SetPoint("TOPRIGHT", page, "TOPLEFT",\n'
    b'                  PD.RIGHT_X + PD.RIGHT_W - PD.LIST_PAD, -PD.SUB_Y)\n',
    b'    gear:SetPoint("TOPRIGHT", page, "TOPLEFT", PD.RIGHT_X + PD.RIGHT_W, -PD.SUB_Y) -- MUT: gear hugs card border\n'))

# 2026-10-10 用户截图实锤：帧级右锚必须内缩 LIST_PAD 与行栅格一线（UI_RULES §3.1）
MUT_PROF_HUD_REDGE = ('Core/ProfessionUI.lua', (
    b'    hudBtn:SetPoint("TOPRIGHT", page, "TOPRIGHT",\n'
    b'                    -(PD.CARD_INSET + PD.LIST_PAD), -(PD.BODY_TOP + PD.LV_TILE_H + 8))\n',
    b'    hudBtn:SetPoint("TOPRIGHT", page, "TOPRIGHT",\n'
    b'                    -PD.CARD_INSET, -(PD.BODY_TOP + PD.LV_TILE_H + 8)) -- MUT: hud hugs border\n'))

MUT_PROF_SB_REDGE = ('Core/ProfessionUI.lua', (
    b'            PD.searchBox:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT",\n'
    b'                                  -(PD.CARD_INSET + PD.LIST_PAD), -(PD.BODY_TOP))\n',
    b'            PD.searchBox:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT",\n'
    b'                                  -PD.CARD_INSET, -(PD.BODY_TOP)) -- MUT: search hugs border\n'))

MUT_PROF_SNAP_REDGE = ('Core/ProfessionUI.lua', (
    b'            tf:SetWidth(usable - (n - 1) * tw)\n',
    b'            tf:SetWidth(PD.RIGHT_W) -- MUT: snap hugs border\n'))

MUT_PROF_TILE_FIXEDW = ('Core/ProfessionUI.lua', (
    b'            tf:SetWidth(tw)\n',
    b'            tf:SetWidth(200) -- MUT: fixed tile width regrown (row overflows)\n'))

MUT_PROF_IX_GREEN_GONE = ('Core/ProfessionUI.lua', (
    b'                c.__ixBorder = bord\n',
    b'                c.__ixBorder = nil -- MUT: learned-card green border gone\n'))

MUT_PROF_IX_FS_BACK = ('Core/ProfessionUI.lua', (
    b'            c.name = MakeFS(c, 16, C_TEXT, "LEFT")\n',
    b'            c.name = MakeFS(c, 12, C_TEXT, "LEFT") -- MUT: index name font regressed\n'))

MUT_PROF_MEM_GONE = ('Core/ProfessionUI.lua', (
    b'        db.lastSlug = PD.cur\n',
    b'        -- MUT: last page memory gone\n'))

# ★★ 2026-10-10（用户：不止一个商人出售时只显示一个不对、联盟商人显示给部落也不对）
MUT_PROF_VSIDE_GONE = ('Core/ProfessionUI.lua', (
    b'            if v.side == f then out[#out + 1] = v end\n',
    b'            out[#out + 1] = v -- MUT: faction filter defeated\n'))
MUT_PROF_VMULTI_GONE = ('Core/ProfessionUI.lua', (
    '            dval = format(L["商人：%s 等 %d 人"], tostring(vs[1] and vs[1].name or "?"), #vs)\n'.encode('utf-8'),
    '            dval = format(L["商人：%s"], tostring(vs[1] and vs[1].name or "?")) -- MUT: multi count gone\n'.encode('utf-8')))
MUT_PROF_VPICK_GONE = ('Core/ProfessionUI.lua', (
    b'        PD.VendorPickToggle(zone, ents)\n',
    b'        PD.MarkVendorLoc(ents[1].loc) -- MUT: picker bypassed\n'))
MUT_PROF_VPICK_STAY = ('Core/ProfessionUI.lua', (
    '    PD.HideVendorPick()\n    if slug ~= PD.cur then'.encode('utf-8'),
    '    -- MUT: popup lingers across profession switch\n    if slug ~= PD.cur then'.encode('utf-8')))

MUT_PROF_DEFSLUG_BACK = ('Core/ProfessionUI.lua', (
    b'    if slug then\n        PD.cur = slug\n        PD.toolKey = nil\n',
    b'    if slug then\n        PD.cur = "__index" -- MUT: default regressed to index page\n        PD.toolKey = nil\n'))

MUT_PROF_NAME_FIT_GONE = ('Core/ProfessionUI.lua', (
    '            s.text = PD.Fit(s.text, 13, math.max(PD.MAT_X - 8 - PD.RECIPE_PADL,\n                                                 (PD.RECIPE_NAME_W or 0) - 6))\n'.encode('utf-8'),
    '            s.text = PD.Fit(s.text, 13, nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)) -- MUT: truncate despite gap\n'.encode('utf-8')))

MUT_PROF_MATCNT_GONE = ('Core/ProfessionUI.lua', (
    b'        segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece }\n',
    b'        segs[#segs + 1] = { id = m[1], text = piece } -- MUT: count badge data gone\n'))

MUT_PROF_PAD_REGROWN = ('Core/ProfessionUI.lua', (
    'PD.RECIPE_NAME_PAD = 16'.encode('utf-8'),
    'PD.RECIPE_NAME_PAD = 44 -- MUT: column gap regrown'.encode('utf-8')))

MUT_PROF_SUBSCAN_GONE = ('Core/ProfessionUI.lua', (
    'local sw = PD.TextW(s.sub or "", 11) + (s.is_new and PD.RECIPE_BADGE_W or 0)'.encode('utf-8'),
    'local sw = PD.TextW(s.sub or "", 11) -- MUT: badge width dropped from sub scan'.encode('utf-8')))

MUT_PROF_PICKSHIELD_GONE = ('Core/ProfessionUI.lua', (
    '        shield:SetScript("OnMouseDown", function() PD.HideVendorPick() end)\n'.encode('utf-8'),
    '        shield:SetScript("OnMouseDown", nil) -- MUT: click-away close gone\n'.encode('utf-8')))

MUT_PROF_MATTAIL_GONE = ('Core/ProfessionUI.lua', (
    '                local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)\n'.encode('utf-8'),
    '                local piece2 = PD.MatIconTex(m[1], px) .. name -- MUT: tail refit gone\n'.encode('utf-8')))

# 2026-10-10 用户：配方名/材料名按物品品质着色
MUT_PROF_QNAME_GONE = ('Core/ProfessionUI.lua', (
    '    if not ncol and spec.qItem then'.encode('utf-8'),
    '    if false then -- MUT: name quality color gone'.encode('utf-8')))
MUT_PROF_QSEG_GONE = ('Core/ProfessionUI.lua', (
    '            if q then scol = { DG.QColor(q) } end'.encode('utf-8'),
    '            scol = col -- MUT: material quality color gone'.encode('utf-8')))

# 2026-10-10 自动路线方案化（默认最省钱 + 方案卡）
MUT_PROF_SCHEME_DEF_GONE = ('Core/ProfessionUI.lua', (
    'PD.SETTING_DEF.autoScheme = "cheapest"'.encode('utf-8'),
    'PD.SETTING_DEF.autoScheme = "matcost" -- MUT: scheme default regressed'.encode('utf-8')))
MUT_PROF_SCHEME_TILE_GONE = ('Core/ProfessionUI.lua', (
    '{ key = "scheme", w = 150 },'.encode('utf-8'),
    '{ }, -- MUT: scheme tile gone'.encode('utf-8')))
MUT_PROF_SCHEMEHIDE_GONE = ('Core/ProfessionUI.lua', (
    '{ "mode", "scheme", "cost", "target", "snap" }) do tiles[k]:Hide() end'.encode('utf-8'),
    '{ "mode", "cost", "target", "snap" }) do tiles[k]:Hide() end -- MUT: scheme residue'.encode('utf-8')))
MUT_PROF_SETTRAW_GONE = ('Core/ProfessionUI.lua', (
    'local cur = PD.SettingRaw("autoScheme")'.encode('utf-8'),
    'local cur = PD.Setting("autoScheme") -- MUT: boolean crunch'.encode('utf-8')))
MUT_PROF_SMELT_GONE = ('Core/ProfessionUI.lua', (
    'if PD.GatherMode(slug) == "smelt" then'.encode('utf-8'),
    'if PD.GatherMode(slug) == "smelt" and false then -- MUT: smelt branch gone'.encode('utf-8')))
MUT_PROF_SMODE_GONE = ('Core/ProfessionUI.lua', (
    'ProfDB().gatherMode = smelt and "gather" or "smelt"'.encode('utf-8'),
    'ProfDB().gatherMode = ProfDB().gatherMode -- MUT: mode toggle gone'.encode('utf-8')))
MUT_PROF_GROUTE_GONE = ('Core/ProfessionUI.lua', (
    'if PD.GATHER_SLUGS[PD.cur] then return PD.PaintGatherTiles() end'.encode('utf-8'),
    'if PD.GATHER_SLUGS[PD.cur] then else end -- MUT: gather tiles skipped'.encode('utf-8')))
MUT_PROF_GTAB_GONE = ('Core/ProfessionUI.lua', (
    'or (PD.GATHER_SLUGS and PD.GATHER_SLUGS[slug]) then out[#out + 1] = "leveling" end'.encode('utf-8'),
    'then out[#out + 1] = "leveling" end -- MUT: gather tab gone'.encode('utf-8')))
# 2026-10-11 采集路线三列行 + 相邻合并（用户可视化方案拍板：等级 | 地点 | 图标+矿名）
MUT_PROF_GR3_GONE = ('Core/ProfessionUI.lua', (
    'if spec.gr3 then'.encode('utf-8'),
    'if false then -- MUT: gr3 three-column paint gone'.encode('utf-8')))
MUT_PROF_GMERGE_GONE = ('Core/ProfessionUI.lua', (
    'and PD.ZoneText(zones) == PD.ZoneText(nx[3])) then break end'.encode('utf-8'),
    'and false) then break end -- MUT: adjacent merge disabled'.encode('utf-8')))
MUT_PROF_GR3_NAMEOFF = ('Core/ProfessionUI.lua', (
    'r.e:SetPoint("RIGHT", r, "RIGHT", -6, 0)'.encode('utf-8'),
    'r.e:SetPoint("RIGHT", r, "RIGHT", -60, 0) -- MUT: ore name offset blown'.encode('utf-8')))
MUT_PROF_SKINMAP_GONE = ('Core/ProfessionUI.lua', (
    'local rng = SKIN_SKILL[t[1][1]] or { t[1][1], t[1][2] }'.encode('utf-8'),
    'local rng = { t[1][1], t[1][2] } -- MUT: skinning skill mapping gone'.encode('utf-8')))
# 2026-10-11 三轮：快照 24h 天化 / 熔炼三列 / 采药同档合并
MUT_PROF_SNAPDAY_GONE = ('Core/ProfessionUI.lua', (
    'elseif snapSec < 24 * 3600 then'.encode('utf-8'),
    'elseif snapSec < 48 * 3600 then -- MUT: 24h day fold gone'.encode('utf-8')))
MUT_PROF_SMGR3_GONE = ('Core/ProfessionUI.lua', (
    'lv = rng,'.encode('utf-8'),
    'right = rng, -- MUT: smelt rows back to right column'.encode('utf-8')))
MUT_PROF_HMERGE_GONE = ('Core/ProfessionUI.lua', (
    'if slug == "herbalism" or slug == "mining" then'.encode('utf-8'),
    'if false then -- MUT: herb/mine group merge gone'.encode('utf-8')))
MUT_PROF_MINEGRP_GONE = ('Core/ProfessionUI.lua', (
    'lo, hi = t[5][1], t[5][2]'.encode('utf-8'),
    'hi = (g[gi + 1] and g[gi + 1][2] or 301) - 1 -- MUT: group range display gone'.encode('utf-8')))
MUT_PROF_GRICON_GONE = ('Core/ProfessionUI.lua', (
    'if spec.icons then'.encode('utf-8'),
    'if false then -- MUT: gather icon-only column gone'.encode('utf-8')))
MUT_PROF_GICWIPE_GONE = ('Core/ProfessionUI.lua', (
    'if r.gic then for _, g in ipairs(r.gic) do g:Hide() end end'.encode('utf-8'),
    'if r.gic then end -- MUT: icon pool wipe gone (stale icons across pages)'.encode('utf-8')))
# 2026-10-11 三轮：路线标题移工具行 / 感叹号居中 / 警告芯片跨页残留
MUT_PROF_ROUTEMOVE_GONE = ('Core/ProfessionUI.lua', (
    'if tool and PD.lvRouteHead then'.encode('utf-8'),
    'if false then -- MUT: route title back inside scroll list'.encode('utf-8')))
MUT_PROF_WARNWIPE_GONE = ('Core/ProfessionUI.lua', (
    'if r.__warn then r.__warn:Hide(); r.__warn.__tipLines = nil end'.encode('utf-8'),
    'if r.__warn then end -- MUT: warn chip wipe gone (stale across pages)'.encode('utf-8')))
MUT_PROF_WARNTEX_GONE = ('Core/ProfessionUI.lua', (
    'tex:SetTexture("Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\WarnTri")'.encode('utf-8'),
    'tex:SetTexture(nil) -- MUT: warn self-drawn texture gone (fontstring fallback)'.encode('utf-8')))
MUT_PROF_HEADFS_GONE = ('Core/ProfessionUI.lua', (
    'local wantFs = spec.fs or (spec.kind == "head" and 16 or 13)'.encode('utf-8'),
    'local wantFs = spec.fs or 13 -- MUT: head font default regressed to 13'.encode('utf-8')))
MUT_PROF_HOVERL4_GONE = ('Core/ProfessionUI.lua', (
    'r:SetBackdropColor(c4[1], c4[2], c4[3], c4[4] or 1)'.encode('utf-8'),
    'r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER) -- MUT: white alpha hover back'.encode('utf-8')))
MUT_PROF_OVFS14_GONE = ('Core/ProfessionUI.lua', (
    'PushText(rows, p.steps_note, 14, C_GREY, 1)'.encode('utf-8'),
    'PushText(rows, p.steps_note, 12, C_GREY, 1)'.encode('utf-8')))
MUT_PROF_SECIN_GONE = ('Core/ProfessionUI.lua', (
    'if spec.sec and spec.sec > 0 then\n                w = w - PD.SEC_IN\n            end'.encode('utf-8'),
    'if spec.sec and spec.sec > 0 then\n                w = w - 0\n            end'.encode('utf-8')))
MUT_PROF_BTCARD_GONE = ('Core/ProfessionUI.lua', (
    'PD.bonusCard:SetSize(PD.RIGHT_W - PD.SEC_PAD_X, (PD.bonusTableH or 0) + 2 * PD.SEC_PAD)'.encode('utf-8'),
    'PD.bonusCard:Hide() -- MUT: camp bonus card-in-card removed'.encode('utf-8')))
MUT_PROF_FAVCOLS_GONE = ('Core/ProfessionUI.lua', (
    'kind = "row", it = { f[1] }, qItem = f[1], _mats = mats,'.encode('utf-8'),
    'kind = "row", it = { f[1] }, _mats = nil, -- MUT: favor columns removed'.encode('utf-8')))
MUT_PROF_FAVKEY_BACK = ('Core/ProfessionUI.lua', (
    'if d and d.rows then\n        local want = f[5] or f[1]'.encode('utf-8'),
    'if d and d.rows then\n        local want = f[1] -- MUT: favor match key regressed to f[1] (mats empty)'.encode('utf-8')))
MUT_PROF_ICONCEN_GONE = ('Core/ProfessionUI.lua', (
    'r.icon:SetPoint("TOPLEFT", r, "TOPLEFT", 6, -math.floor((h - 20) / 2))'.encode('utf-8'),
    'r.icon:SetPoint("TOPLEFT", r, "TOPLEFT", 6, -5) -- MUT: icon top-anchored again'.encode('utf-8')))
MUT_PROF_PLAINOFF = ('Core/ProfessionUI.lua', (
    'w = math.ceil(PD.TextW(def.text, 12)) + 6'.encode('utf-8'),
    'w = 56 -- MUT: plain label width clamp regression'.encode('utf-8')))
MUT_PROF_SPELLICON_GONE = ('Core/ProfessionUI.lua', (
    'icon = SpellIcon(en[14]),'.encode('utf-8'),
    'icon = nil,'.encode('utf-8')))
MUT_PROF_LVSB_GONE = ('Core/ProfessionUI.lua', (
    'or (ri and (ri.yellow or ri.grey))'.encode('utf-8'),
    'or nil'.encode('utf-8')))
MUT_PROF_SETGEARGATE_GONE = ('Core/ProfessionUI.lua', (
    'local gon = (PD.tab == "leveling")'.encode('utf-8'),
    'local gon = true -- MUT: settings gear gate gone (shows on every tab)'.encode('utf-8')))
MUT_PROF_VSCROLL_GONE = ('Core/ProfessionUI.lua', (
    'if PD.setOpen then track:Hide() return end'.encode('utf-8'),
    'if false then track:Hide() return end -- MUT: recipe scrollbar gate gone'.encode('utf-8')))
MUT_PROF_VSCROLLSYNC_GONE = ('Core/ProfessionUI.lua', (
    'if PD.UpdateVScroll then PD.UpdateVScroll() end\n    PD.FlushPendingRows()'.encode('utf-8'),
    'if PD.UpdateVScroll then end -- MUT: scrollbar sync gone\n    PD.FlushPendingRows()'.encode('utf-8')))
MUT_PROF_CHEAPSKIP_GONE = ('Core/ProfRouteAuto.lua', (
    'opts.noFormula and opts.scheme ~= "cheapest"'.encode('utf-8'),
    'opts.noFormula -- MUT: cheapest honors formula exclusion'.encode('utf-8')))
MUT_PROF_FCHEAP_GONE = ('Core/ProfRouteAuto.lua', (
    'return c.cost / g + (c.fcost or 0) / span'.encode('utf-8'),
    'return (c.cost + (c.fcost or 0)) / g -- MUT: formula amortized per craft'.encode('utf-8')))
MUT_PROF_OPTIM_GAIN_GONE = ('Core/ProfRouteAuto.lua', (
    'if scheme == "optim" then return 1 end'.encode('utf-8'),
    'if false then return 1 end -- MUT: optimistic gain gone'.encode('utf-8')))

# 2026-10-10 UI_RULES 审计三连（搜索框提亮 / 页签胶囊缝 8 / 升级页切换组缝 8）
MUT_PROF_SEARCH_SAMELVL = ('Core/ProfessionUI.lua', (
    b'BuildRoundedBG(seb, 6, ns.hui.layer.L2, "both", true, 1)\n',
    b'BuildRoundedBG(seb, 6, ns.hui.layer.L1, "both", true, 1) -- MUT: search box same level as host card\n'))

MUT_PROF_SUBTAB_GAP4 = ('Core/ProfessionUI.lua', (
    b'PD.SUB_Y, PD.SUB_H, PD.SUB_W, PD.SUB_STEP = PD.CARD_TOP + 8, 22, 70, 78\n',
    b'PD.SUB_Y, PD.SUB_H, PD.SUB_W, PD.SUB_STEP = PD.CARD_TOP + 8, 22, 70, 74 -- MUT: pill gap 4\n'))

MUT_PROF_TOOL_PAIRGAP = ('Core/ProfessionUI.lua', (
    b'        { key = "page_route", text = L["\xe8\xb7\xaf\xe7\xba\xbf"],     on = PD.autoPage ~= "shop" },\n',
    b'        { key = "page_route", text = L["\xe8\xb7\xaf\xe7\xba\xbf"],     on = PD.autoPage ~= "shop", gap = 2 }, -- MUT: pair gap 2\n'))

MUT_OV_SINGLECOL = ('Core/ProfessionUI.lua', (
    b'    elseif PD.tab == "overview" then\n        PD.lvSplit = false\n',
    b'    elseif PD.tab == "overview" then\n        PD.lvSplit = true -- MUT: overview two-column regrown\n'))

MUT_GUIDE_BOSSNAME_LITERAL = (
    b'            if loot[i][1] == en then return loot[i][2] or en end\r\n',
    b'            if loot[i][1] == en then return en end -- MUT: english key leaks to UI\r\n')

MUT_GUIDE_NO_EQUAL_H = (
    b'        if b and b.h > rh then rh = b.h end\r\n',
    b'        -- MUT: row height not maxed (taller card gets squeezed)\r\n')

MUT_GUIDE_TOP_GAP = (
    b'    local top, i = 0, 1\r\n',
    b'    local top, i = -14, 1 -- MUT: cards pushed down, tagline band kept\r\n')

MUT_GUIDE_TAGLINE_GONE = (
    b'            if g.tagline then\r\n'
    b'                rows[#rows + 1] = { t = "\xc2\xb7 " .. g.tagline, c = C_TEXT, x = 0, gap = 5 }\r\n'
    b'            end\r\n',
    b'            -- MUT: tagline row dropped (not merged into tips)\r\n')

MUT_GUIDE_TOP_BACK = (
    b'    gscroll:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.GUIDE_TOP_Y)\r\n',
    b'    gscroll:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.SCROLL_Y) -- MUT: filter band gap back\r\n')

MUT_GUIDE_SIDE_GONE = (
    b'        a.frame:SetPoint("TOPLEFT", child, "TOPLEFT", DG.GUIDE_SIDE, top)\r\n',
    b'        a.frame:SetPoint("TOPLEFT", child, "TOPLEFT", 0, top) -- MUT: left margin gone\r\n')

# ㉘ 配方搜索 + 名称列现算（2026-10-09：配方页加搜索框 / 名称列按本页现算）
# ★ 2026-10-09 第二轮重锚：主路径的搜索过滤已挪进 PD.RecipeList（PD.RawHit，建 spec
#   之前），旧的 `    local list = PD.SearchFilter(PD.RecipeList())` 现在只剩「附魔 /
#   制造品 / 声望」那三条小分支 —— 锚点 0 次，这条变异原本已经**静默没人守**了。
#   新锚点必须落在**主路径的建表循环**：把命中判定短路 ⇒ 列表退回「分类前 N 条」，
#   内容级断言（留下的每一行都真的命中）立刻变红。
#   刻意**只改 RecipeList 这一处** —— ScanRecipe 那处的 PD.RawHit 留着，这样红的是
#   「行内容不对」而不是「抬头条数不对」，指向性明确。
MUT_SEARCH_FILTER_GONE = ('Core/ProfessionUI.lua', (
    b'        if (not fk) or r[4] == fk then\n'
    b'            if PD.RawHit(r, q) then\n'
    b'                out[#out + 1] = PD.RecipeSpec(r)\n',
    b'        if (not fk) or r[4] == fk then\n'
    b'            if true then -- MUT: search filter gone\n'
    b'                out[#out + 1] = PD.RecipeSpec(r)\n'))
MUT_RECIPE_COLS_STATIC = ('Core/ProfessionUI.lua', (
    '    PD.MAT_X = nameW + PD.RECIPE_NAME_PAD\n'.encode('utf-8'),
    '    PD.MAT_X = math.floor(PD.MAT_ROW_W * 0.40)\n'.encode('utf-8')))
MUT_SEARCH_HIDE = ('Core/ProfessionUI.lua', (
    b'        if PD.tab == "recipe" and not PD.setOpen then\n'
    b'            PD.searchBox:ClearAllPoints()',
    b'        if false and PD.tab == "recipe" and not PD.setOpen then\n'
    b'            PD.searchBox:ClearAllPoints()'))
MUT_SEARCH_NORENDER = ('Core/ProfessionUI.lua', (
    b'        PD.searchQ = t\n        PD.RequestRender()\n',
    b'        PD.searchQ = t\n'))
# ★★ 2026-10-09 第二轮（用户：「加了进度条也没优化好，点配方那一瞬间有卡顿」）
#    这一轮的三条断言各配一条反向变异；另加一条守卫搜索改写的性能口径。
MUT_PROF_FULL_SPEC_BUILD = ('Core/ProfessionUI.lua', (
    b'        list = PD.RecipeList(math.min(realN, PD.ROW_CAP), PD.searchQ)\n',
    b'        list = PD.RecipeList(#(d.rows or {}), PD.searchQ) -- MUT: spec for the full list\n'))
MUT_PROF_SPEC_PREBUILD = ('Core/ProfessionUI.lua', (
    b'    local vs = (r[14] and PD.VendorListOf(r[14])) or {}\n'
    b'    local hasVendor = #vs > 0\n',
    b'    local _m0 = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W) -- MUT: mats precomputed again\n'
    b'    local hasVendor = #vs > 0\n'))
MUT_PROF_NO_TW_MEMO = ('Core/ProfessionUI.lua', (
    b'    local w = m[text]\n    if w ~= nil then return w end\n',
    b'    local w = nil -- MUT: width memo gone\n'))
MUT_PROF_NO_REQ_DEDUP = ('Core/ProfessionUI.lua', (
    b'        if not id or seen[id] then return end\n',
    b'        if not id then return end -- MUT: request dedup gone\n'))

# ★★ 第十一刀（rev17）：记忆表「正负分离」被破坏 —— 清表时把**正向**那半边
#   也一起清了 ⇒ 每一帧渲染又要向引擎重问全部物品名（实机一页 428 次）。
MUT_PROF_NM_MEMO_RESET_ALL = ('Core/ProfessionUI.lua', (
    b'    _nmNeg, _nmN = {}, 0\n'
    b'    _icNeg, _icN = {}, 0\n',
    b'    _nmNeg, _nmPos, _nmN, _nmPosN = {}, {}, 0, 0  -- MUT: positive memo cleared too\n'))

# ★★ 第十一刀（rev17）：空闲预热被摘 ⇒ 「点开配方页」那一帧又得现向引擎要名字。
MUT_PROF_WARM_GONE = ('Core/ProfessionUI.lua', (
    b'    PD.RequestRows(rows)\n    PD.WarmNames()\n',
    b'    PD.RequestRows(rows)\n    -- MUT: idle prewarm gone\n'))

# ★★ 物品名记忆表（2026-10-09 第五轮）：Render 开头不清 = 把「名字还没到货」那一刻的
#   占位钉死一整局（物品到货后的重扫也刷不回来）。静默失效，必须有人守。
MUT_PROF_NO_NM_RESET = ('Core/ProfessionUI.lua', (
    b'    PD.ResetItemNameMemo()\n',
    b'    -- MUT: item-name memo never reset\n'))

# ★★ 材料图标记忆化（2026-10-09 第六轮）：摘掉 = 每行每材料又直查一次
#   DG.ItemInfo（GetItemInfo，零缓存引擎调用），一页白烧 ≈ 900 次。
MUT_PROF_NO_ICON_MEMO = ('Core/ProfessionUI.lua', (
    b'    local ic = PD.ItemIcon(id)',
    b'    local ic = DG.ItemIcon(id)  -- MUT: icon memo gone'))

# ★★ 扫描只给可见行量宽（2026-10-09 第六轮）：把闸拿掉 = 又给全量 511 行量宽。
MUT_PROF_SCAN_ALL_ROWS = ('Core/ProfessionUI.lua', (
    b'                if n <= PD.ROW_CAP then\n',
    b'                if true then  -- MUT: scan measures every row\n'))

# ★★ 皮按钮边框帧重建（2026-10-09 第七刀）：把幂等摘掉 = 每次 SetSize 都销毁重建
#   两副圆角边框帧（各 8 个新纹理）—— 专业页工具行 20 颗按钮切页时一次 ≈ 20ms。
MUT_HUI_SKIN_REBUILD = ('Core/Hui.lua', (
    b'            if borderFrame then return end\n',
    b'            -- MUT: border frames rebuilt on every SetSize\n'))

# ★★ 视口优先（2026-10-09 第七刀）：把闸拿掉 = 行帧已在池里的一律本帧同步重绑
#   （实机 300 行 37~42ms，切页那一次 111.6ms）。
MUT_PROF_ROW_SYNC_ALL = ('Core/ProfessionUI.lua', (
    b'                if r and ((not vis) or i <= syncN) then\n',
    b'                if r then  -- MUT: rebind every pooled row inline\n'))

# ★★ 工具行闸门插桩（2026-10-09 第八刀 rev14）：把计时器来源摘掉（_T0/_MK 置 nil）
#   ⇒ _MK 永远为 nil，闸-* 四项一条都记不上 ⇒ 工具行 21~26ms 又拆不开（回归到只能
#   读代码猜）。★ 锚点必须**纯 ASCII**：Python 3 的 b'...' 不许含非 ASCII 字面量。
MUT_PROF_TOOL_GATE_UNMARKED = ('Core/ProfessionUI.lua', (
    b'    local _T0, _MK = PD.__pfT0, PD.__pfMark\n',
    b'    local _T0, _MK = nil, nil  -- MUT: tool gate left uninstrumented\n'))

# ★★ 像素条复算（2026-10-09 第九刀 rev15）：把帧内索引摘掉 ⇒ 退回
#   `for tex in pairs(pixelStrips)` 全表扫 ⇒ 工具行 16 颗按钮 Hide→Show
#   每颗又 ~1.5ms（= 工具P 的 24.5ms 全回来）。
#   ★ 锚点必须**纯 ASCII**：Python 3 的 b'...' 不许含非 ASCII 字面量。
MUT_HUI_STRIP_SCAN_ALL = ('Core/Hui.lua', (
    b'            local list = frame.__huiStrips\n',
    b'            local list = nil  -- MUT: strip reapply falls back to full-table scan\n'))

# ★★ 材料串按需算（2026-10-09 第十刀 rev16）：把「首屏现算 / 其余挂待算标」
#   退回「全部行现算」⇒ FitRecipeCols 那 300 行又全在**点开那一帧**算材料串
#   （~8ms 回来），而首屏只画得下几十行。
#   ★ 锚点必须**纯 ASCII**：Python 3 的 b'...' 不许含非 ASCII 字面量。
MUT_PROF_MATS_DEFER_GONE = ('Core/ProfessionUI.lua', (
    b'            if idx <= keep then\n'
    b'                PD.FinishSpecMats(s)\n'
    b'            else\n'
    b'                s._matsPending = true\n'
    b'            end\n',
    b'            PD.FinishSpecMats(s)  -- MUT: mats computed eagerly for every row\n'))

# ㊾ 升级行提示框改版（2026-10-09 用户）：「每行有个鼠标提示框，这个提示框不要了，
#   改成当我们移动到制作物或需求材料的上方时，显示该物品的鼠标提示框。注意，这个
#   提示框不使用我们的主题」。守护点：① 行级 noTip 短路不许退回；② 制作物热区必须
#   挂产物 itemID 且盖住「图标 + 名称列」；③ 材料热区必须挂该材料 id；④ 两处热区都
#   要转发滚轮（否则压在热区上整页滚不动）；⑤ 行池跨页复用时热区必须收起。
MUT_LVTIP_ROW_TIP_BACK = ('Core/ProfessionUI.lua', (
    b'                noTip = true,\n',
    b'                -- MUT: row-level segment tooltip back\n'))
MUT_LVTIP_ICONZONE_NOIT = ('Core/ProfessionUI.lua', (
    b'        iz.__it = itemID and { itemID } or nil\n',
    b'        iz.__it = nil -- MUT: craft-product tooltip never fires\n'))
MUT_LVTIP_ICONZONE_NARROW = ('Core/ProfessionUI.lua', (
    b'        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)\n',
    b'        iz:SetSize(PD.TBL_ICON, h) -- MUT: hotspot covers the icon only\n'))
MUT_LVTIP_MATZONE_NOIT = ('Core/ProfessionUI.lua', (
    b'    b.zone.__it = { blk.id }\n',
    b'    b.zone.__it = nil -- MUT: material tooltip never fires\n'))
MUT_LVTIP_ZONE_NOWHEEL = ('Core/ProfessionUI.lua', (
    b'    z:SetScript("OnMouseWheel", function(self, delta)\n'
    b'        PD.HideVendorPick()\n'
    b'        DG.WheelScroll(PD.scroll, PD.child, delta)\n'
    b'    end)\n',
    b'    z:SetScript("OnMouseWheel", function(self, delta)\n'
    b'        do end -- MUT: wheel swallowed (page unscrollable over hotspots)\n'
    b'    end)\n'))
MUT_LVTIP_ICONZONE_KEEPSHOWN = ('Core/ProfessionUI.lua', (
    b'    if r.__iconZone then r.__iconZone:Hide() end\n',
    b'    -- MUT: hotspot not collapsed on rebind (invisible zone eats the mouse)\n'))
MUT_LVTIP_MATZONE_KEEPSHOWN = ('Core/ProfessionUI.lua', (
    b'        if b.zone then b.zone:Hide() end\n',
    b'        do end -- MUT: material hotspot not collapsed in ClearMats\n'))

# ㉚ 专业页大列表分帧 + 顶部进度条（2026-10-09 用户：「点开专业配方页面因为里面的
#   数据量特别大，需要在我们主界面增加一个进度条，这个进度条我们之前增加过，你用
#   同样的方法」= 复用 5 人本掉落页那根 DG.Gate + 分帧器）。守护点：
#   ① 渲染那一帧只算版式、不许再同步建行帧；② 间距行（kind == "gap"）也必须入队，
#   否则行池按索引取用会留空洞。
MUT_PROFGATE_SYNC_BACK = ('Core/ProfessionUI.lua', (
    b'        local h = PD.RowHeight(spec)\n'
    b'        local r = PD.rows[i]\n',
    b'        local h = PD.RowHeight(spec)\n'
    b'        local r = PD.Row(i) -- MUT: synchronous row build back\n'))
MUT_PROFGATE_GAP_NOT_QUEUED = ('Core/ProfessionUI.lua', (
    b'PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true, gen = gen }\n',
    b'-- MUT: gap rows not queued (index holes left in the row pool)\n'))

# ㊿ 升级 HUD 路线模式（2026-10-11 用户：「专业升级 hud 里面的数据需要根据路线模式进行切换」）。
#   HUD 的数据源随专业页「固定路线 / 自动计算」模式切换（routeFor），自动不可用即回落固定。
#   守护点：① 自动门禁不许失效（永远固定）；② 段标必须带模式前缀；③ 配方查找表必须并 rinfo。
MUT_HUD_ROUTEMODE_OFF = ('Core/ProfFollow.lua', (
    b'       and (scheme == "optim" or RA.Available()) then\n',
    b'       and false then -- MUT: auto gate off (HUD always fixed)\n'))
MUT_HUD_SEG_NO_MODE = ('Core/ProfFollow.lua', (
    ('    f.seg:SetText(((mode == "auto") and L["自动计算"] or L["固定路线"]) .. " · "\n'
     '                  .. format(L["段落 %d / %d"], vi, #steps))\n').encode('utf-8'),
    '    f.seg:SetText(format(L["段落 %d / %d"], vi, #steps))  -- MUT: no mode prefix\n'.encode('utf-8')))
MUT_HUD_RINFO_GONE = ('Core/ProfFollow.lua', (
    (b'        local lv = LV[slug]\n'
     b'        if lv and type(lv.rinfo) == "table" then\n'
     b'            for spell, ri in pairs(lv.rinfo) do\n'
     b'                if not c[spell] then c[spell] = ri end\n'
     b'            end\n'
     b'        end\n'),
    b'-- MUT: rinfo not merged into the recipe lookup\n'))
# ★ 实机 25 连崩的那一行（用户 2026-10-11 贴栈）：Unpack 当**非末位实参** ⇒ Lua 只展开首值
#   ⇒ g 收到 0.5、b=nil ⇒ 染色算术崩。只在「已备齐」（missing<=0）分支触发。
MUT_HUD_PILL_UNPACK_INLINE = ('Core/ProfFollow.lua', (
    (b'                local okr, okg, okb = Unpack(C_OK)\n'
     b'                paintPill(mp, L["\xe5\xb7\xb2\xe5\xa4\x87\xe9\xbd\x90"], xMiss, missW, okr, okg, okb, 0.5)\n'),
    (b'                paintPill(mp, L["\xe5\xb7\xb2\xe5\xa4\x87\xe9\xbd\x90"], xMiss, missW,'
     b' Unpack(C_OK), 0.5)  -- MUT: Unpack in non-final arg position\n')))
MUT_HUD_PILLCAP_GONE = ('Core/ProfFollow.lua', (
    b'cols = ns.hui.BuildCapsule(p, 8, ns.hui.layer.L2)'.decode('utf-8').encode('utf-8'),
    b'cols = {} -- MUT: pill capsule gone (flat rect fallback)'.decode('utf-8').encode('utf-8')))
MUT_HUD_PILLPAINT_GONE = ('Core/ProfFollow.lua', (
    b'local function paintPill(p, txt, x0, wpx, cr, cg, cb, ca)'.decode('utf-8').encode('utf-8'),
    b'local function paintPill(p, txt, x0, wpx, cr, cg, cb, ca) if true then return end -- MUT: pill paint gone'.decode('utf-8').encode('utf-8')))
# 2026-10-11 购物清单「只显示缺失」开关（用户）。守护点：
#   ① 表头必须用短键（退回旧长键 = 用户要求没落实）；② 开关必须真建且表头让位；
#   ③ 过滤必须排在算列宽之前（改到列宽之后 ⇒ 被滤掉的长名字仍撑宽名字列，右留一片白）。
MUT_HUD_HEAD_LONG_AGAIN = ('Core/ProfFollow.lua', (
    (b'        f.shop.head:SetText(L["\xe8\xb4\xad\xe7\x89\xa9\xe6\xb8\x85\xe5\x8d\x95"]'
     b' .. format(L[" \xc2\xb7 \xe5\x85\xb1%d\xe7\xa7\x8d"], #shown))\n'),
    (b'        f.shop.head:SetText(L["\xe8\xb4\xad\xe7\x89\xa9\xef\xbc\x88\xe4\xbb\x8e\xe5\xbd\x93\xe5\x89\x8d'
     b'\xe6\xae\xb5\xe7\xb4\xaf\xe8\xae\xa1\xe5\x88\xb0 300\xef\xbc\x8c\xe5\x90\xab\xe9\x93\xb6\xe8\xa1\x8c\xef\xbc\x89"]'
     b' .. format(" \xc2\xb7 \xe5\x85\xb1%d\xe7\xa7\x8d", #list))  -- MUT: long header back\n')))
MUT_HUD_SHOPTOG_GONE = ('Core/ProfFollow.lua', (
    b'    f.shop.missTog:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -6, -4)\n',
    b'    -- MUT: toggle never placed\n'))
MUT_HUD_FILTER_AFTER_COLS = ('Core/ProfFollow.lua', (
    (b'        local shown = {}\n'
     b'        for _, e in ipairs(list) do\n'
     b'            e.missing = e.need - e.have\n'
     b'            if (not onlyMissView()) or e.missing > 0 then shown[#shown + 1] = e end\n'
     b'        end\n'),
    (b'        -- MUT: filter moved out (shown == list)\n'
     b'        local shown = list\n'
     b'        for _, e in ipairs(list) do e.missing = e.need - e.have end\n')))
# 2026-10-11 用户报：「开关打开 + 材料全备齐 ⇒ 永远点不开购物清单」。
#   守护点：n == 0 时不得退回 `f.shop:Hide()`（必须 Show + 一行灰字）。
MUT_HUD_SHOPEMPTY_HIDE = ('Core/ProfFollow.lua', (
    ('            f.shop.empty:SetText(#list > 0 and L["所有物品已备齐"] or L["无材料"])\n'
     '            f.shop.empty:Show()\n'
     '            local shopH = 30 + 20 + 10\n'
     '            f.shop:ClearAllPoints()\n'
     '            f.shop:SetPoint("TOPLEFT", f, "TOPLEFT", PAD, y)\n'
     '            f.shop:SetSize(W - 2 * PAD, shopH)\n'
     '            f.shop:Show()\n'
     '            y = y - shopH - 8\n').encode('utf-8'),
    b'            f.shop:Hide() -- MUT: empty list hides the panel again\n'))
MUT_HUD_SHOPEMPTY_NOTEXT = ('Core/ProfFollow.lua', (
    b'    f.shop.empty = MakeFS(f.shop, 14, C_GREY, "LEFT")\n',
    b'    -- MUT: empty-state label never built\n'))
# 2026-10-11 用户：「hud 固定路线显示也需要 根据我设置等级 显示」。
#   守护点：固定分支不得退回直吃全量 lv.steps（HUD 一路画到 300、与专业页对不上）。
MUT_HUD_FIXED_NO_TARGET_CLIP = ('Core/ProfFollow.lua', (
    b'    return "fixed", clipFixedSteps(lv and lv.steps or nil, routeTarget(slug))\n',
    b'    return "fixed", (lv and lv.steps) or nil -- MUT: raw full route (ignores target)\n'))
MUT_HUD_TARGET_CLIP_NO_RESCALE = ('Core/ProfFollow.lua', (
    b'        if isClip then\n'
    b'            nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))\n'
    b'        end\n',
    b'        -- MUT: crossing segment keeps full craft count (no proportional rescale)\n'))
MUT_HUD_REFRESH_ROUTE_GONE = ('Core/ProfFollow.lua', (
    b'function PF.RefreshRoute(slug)\n'
    b'    local s = st()\n'
    b'    if not (s and s.slug) then return end\n',
    b'function PF.RefreshRoute(slug)\n'
    b'    -- MUT: target change not pushed\n'
    b'    local s = nil\n'
    b'    if not (s and s.slug) then return end\n'))
# 2026-10-11 用户：「只显示缺失的这个开关，左边写上文字“仅显示缺失”」。
#   守护点：① 标签得真建（挂在 f.shop 父帧、右对齐）；② 锚点必须在开关**左**缘；
#          ③ 文案走新键（不得再引用旧键「只显示缺失」）。
MUT_HUD_MISSLAB_GONE = ('Core/ProfFollow.lua', (
    b'    f.shop.missLab = MakeFS(f.shop, 14, C_TEXT, "RIGHT")\n',
    b'    -- MUT: toggle label never built\n'))
#   锚错方向：挂到开关**右**缘 ⇒ 文字跑到开关右边（用户要的是左边）。
MUT_HUD_MISSLAB_RIGHT_SIDE = ('Core/ProfFollow.lua', (
    b'    f.shop.missLab:SetPoint("RIGHT", f.shop.missTog, "LEFT", -4, 0)\n',
    b'    f.shop.missLab:SetPoint("LEFT", f.shop.missTog, "RIGHT", 4, 0) -- MUT: label on the right side\n'))
#   标签挂到开关自己身上 ⇒ ReskinToggle 的 PurgeNative 把它当「非自建子件」Hide
#   （挂载时当场隐藏，实机看不到；离线桩不复现 Hide 但静态断言能抓）。
MUT_HUD_MISSLAB_ON_TOGGLE = ('Core/ProfFollow.lua', (
    b'    f.shop.missLab = MakeFS(f.shop, 14, C_TEXT, "RIGHT")\n',
    b'    f.shop.missLab = MakeFS(f.shop.missTog, 14, C_TEXT, "RIGHT") -- MUT: label under the toggle (PurgeNative hides it)\n'))
#   让位量写死：英文 "Missing only"（≈93px）比中文「仅显示缺失」（70px）宽近一半，
#   写死常数 ⇒ enUS 的表头可用宽被吃掉一截（表头右锚是按 labW 现算的）。
MUT_HUD_HEADRESERVE_HARDCODED = ('Core/ProfFollow.lua', (
    b'    local SHOP_TOG_W = labW + 48\n',
    b'    local SHOP_TOG_W = 96 -- MUT: reserve hardcoded (ignores measured label width)\n'))

# 2026-10-09 配方页提示框改版（用户：「配方页面现在也这样修改 如果鼠标在材料上面，
#   就显示材料的鼠标提示框 如果鼠标在商人上面，就显示点击定位在地图上标记商人位置」）。
#   守护点：① 材料列必须是分段链（退回只画一整串 = 没有分段热区可挂）；
#   ② 材料热区必须挂该材料 itemID；③ 热区必须锚到字串（量宽会漂）；
#   ④ 商人半段必须拆到 r.dv；⑤ 商人热区要出提示框（含「点击：在地图上标记该 NPC」）
#   且点击落图；⑥ 行池跨页复用必须收起分段热区。
MUT_RECIPE_MATCHAIN_GONE = ('Core/ProfessionUI.lua', (
    b'        if spec.matSegs then PD.PaintMatSegs(r, spec.matSegs, spec.matColor) end\n',
    b'        do end -- MUT: material chain dropped (no per-material hotspot)\n'))
MUT_RECIPE_MATZONE_NOIT = ('Core/ProfessionUI.lua', (
    b'            z.__it = { segs[i].id }\n',
    b'            z.__it = nil -- MUT: material tooltip never fires\n'))
MUT_RECIPE_ZONE_ANCHOR_GONE = ('Core/ProfessionUI.lua', (
    b'            z:SetPoint("TOPLEFT", fs, "TOPLEFT", 0, 1)\n'
    b'            z:SetPoint("BOTTOMRIGHT", fs, "BOTTOMRIGHT", 0, -1)\n',
    b'            z:SetSize(20, 20) -- MUT: hotspot not aligned to the text run\n'))
MUT_RECIPE_VENDOR_SPLIT_GONE = ('Core/ProfessionUI.lua', (
    b'    if spec.dval and h > PD.ROW_H1 then\n',
    b'    if false then -- MUT: vendor half not split (no merchant hotspot)\n'))
MUT_RECIPE_VENDOR_NOHINT = ('Core/ProfessionUI.lua', (
    b'        vz.__tipLines = spec.vlines or PD.VendorLines(spec.src)\n',
    b'        vz.__tipLines = nil -- MUT: merchant zone shows no hint\n'))
MUT_RECIPE_VENDOR_NOACT = ('Core/ProfessionUI.lua', (
    b'        vz.__act = spec.dact or PD.VendorAct(spec.src)\n',
    b'        vz.__act = nil -- MUT: merchant zone does not mark the map\n'))
MUT_RECIPE_SEGS_NOFREE = ('Core/ProfessionUI.lua', (
    b'    PD.ClearMatSegs(r)\n',
    b'    -- MUT: stale material hotspots not collapsed across pages\n'))

MUTATIONS = [
    # 2026-10-09 配方页提示框改版（用户）
    ('配方页：材料列退回一整串（没有分段热区可挂）', MUT_RECIPE_MATCHAIN_GONE),
    ('配方页：材料热区不挂物品 id（悬停没提示框）', MUT_RECIPE_MATZONE_NOIT),
    ('配方页：材料热区不比着字串锚（量宽必漂）', MUT_RECIPE_ZONE_ANCHOR_GONE),
    ('配方页：商人半段不拆（没有商人热区）', MUT_RECIPE_VENDOR_SPLIT_GONE),
    ('配方页：商人热区不出提示框（看不到「点击定位」）', MUT_RECIPE_VENDOR_NOHINT),
    ('配方页：商人热区点击不落图', MUT_RECIPE_VENDOR_NOACT),
    ('配方页：行池复用不收起分段热区（透明热区吞鼠标）', MUT_RECIPE_SEGS_NOFREE),
    # ㊾ 升级行提示框改版（2026-10-09 用户）
    ('升级行：行级提示框又长回来（整段说明复辟）', MUT_LVTIP_ROW_TIP_BACK),
    ('升级行：制作物热区不挂产物 id（悬停没提示框）', MUT_LVTIP_ICONZONE_NOIT),
    ('升级行：制作物热区只盖图标（名称列悬停不了）', MUT_LVTIP_ICONZONE_NARROW),
    ('升级行：材料热区不挂材料 id（悬停没提示框）', MUT_LVTIP_MATZONE_NOIT),
    ('升级行：热区吞滚轮（压在热区上整页滚不动）', MUT_LVTIP_ZONE_NOWHEEL),
    ('升级行：行池复用不收起制作物热区（透明热区吞鼠标）', MUT_LVTIP_ICONZONE_KEEPSHOWN),
    ('升级行：ClearMats 不收起材料热区（切页留透明热区）', MUT_LVTIP_MATZONE_KEEPSHOWN),
    # ㉕ 副本攻略页 卡片式版面（2026-09-29 用户定「4 个卡片、两列、极简描边」）
    ('攻略：页签「攻略」被摘（入口消失）', MUT_GUIDE_TAB_GONE),
    ('攻略：点攻略渲染成掉落页（分派串线）', MUT_GUIDE_DISPATCH_LOOT),
    ('攻略：掉落滚动区不让位（两层叠着显示）', MUT_GUIDE_KEEP_SCROLL),
    ('攻略：BOSS 名不再反查（英文键漏到界面）', MUT_GUIDE_BOSSNAME_LITERAL),
    ('攻略：卡片行高不取行内较高者（高卡被压矮）', MUT_GUIDE_NO_EQUAL_H),
    ('攻略：卡片被推下（顶部又留出定位语空档）', MUT_GUIDE_TOP_GAP),
    ('攻略：定位语不再并入「副本须知」首条', MUT_GUIDE_TAGLINE_GONE),
    ('攻略：滚动区顶退回筛选行位（横幅间距又变 42）', MUT_GUIDE_TOP_BACK),
    ('攻略：左留白被清零（左右又不对称）', MUT_GUIDE_SIDE_GONE),

    # ㉔ 专业页设置 + 当前段落外框（2026-09-29 用户定）
    ('专业页：灰显开关默认值被翻成关', MUT_PROF_SET_GREY_DEF),
    ('专业页：当前段不再被标记（外框永不亮）', MUT_PROF_SET_CUR_GONE),
    ('专业页：外框上边条永不显示（框缺一条）', MUT_PROF_SET_BORDER_GONE),
    ('专业页：设置页不可达（齿轮点了没反应）', MUT_PROF_SET_PAGE_GONE),
    ('专业页：iOS 开关不再绑定设置键（点了也写不进 DB）', MUT_PROF_SET_TOG_GONE),
    # ㊶ 已过段落灰显（2026-09-29 用户定）
    ('专业页：已过段落灰显被关掉（passed 恒 nil）', MUT_LV_PASSED_OFF),
    ('专业页：已过段落图标不再去饱和', MUT_LV_PASSED_NOICON),
    # ㊵ 已学专业导航（2026-09-24 用户定）
    ('专业页：已学导航主题绿被改灰', MUT_NAV_LEARN_GREY),
    ('专业页：已学导航「当前/上限」小字被清空', MUT_NAV_LV_GONE),
    ('专业页：first-aid skillLine 映射被摘', MUT_NAV_SLUG_FA_GONE),
    # ㊴ 探索页（2026-09-24）
    ('探索：顶栏第四颗被摘（入口消失）', MUT_EXPLORE_TAB_GONE),
    ('探索：SwitchSub 把 Explore 丢掉（永远进不去探索页）', MUT_EXPLORE_KEY_DROPPED),
    ('探索：Build 不挂 ExploreModule（行池空）', MUT_EXPLORE_PAGE_GONE),
    # ㊳ 职业加成对照总表（2026-09-24）
    ('加成总表：举手被砍（对照表不出现）', MUT_BONTAB_OFF),
    ('加成总表：对照列被清空（增益绿字消失）', MUT_BONTAB_NOCMP),
    ('加成总表：填表循环被砍（0 行）', MUT_BONTAB_NOFILL),
    # ㊱ 营地/军需官 → 地图标记（2026-09-24）
    ('营地标记：军需官行落点被摘（点行不放航点）', MUT_CAMP_MARK_GONE),
    # ㉟ 全部专业总览三列宫格（2026-09-24 方案 B）
    ('总览宫格：Build 里的挂载被摘（宫格永不出现）', MUT_IX_GRID_BUILT),
    ('总览宫格：举手恒 False（wantIndexGrid 永不亮）', MUT_IX_GRID_RAISE),
    ('总览宫格：SyncHover 兜底断线（悬停失同步不自愈）', MUT_IX_HOVER),
    ('总览宫格：指路尾注丢失（ixNote 不再建）', MUT_IX_NOTE_GONE),
    # ㉝ 入口芯片（2026-09-24 用户定：标题右侧芯片，一枚 = 一个可标记的点）
    ('入口芯片：芯片序号清零（点芯片不落点）', MUT_ENT_CHIP_IDX0),
    # ㉞ 材料角标粗描边（2026-09-24 用户要求）
    ('专业页：材料角标粗描边被摘（THICKOUTLINE 回落无旗标）', MUT_PROF_LV_CNT_NOTHICK),
    # ㉜ 材料角标细描边（2026-09-24 用户要求）
    ('专业页：材料角标细描边被摘（压图标发虚）', MUT_PROF_LV_CNT_NOEDGE),
    # ㉛ 副本入口指引点（2026-09-24 用户要求：领主大厅给楼梯 + 入口两个坐标）
    ('入口指引：指引点丢失（提示框少了多段坐标行）', MUT_ENT_ROUTE_GONE),
    # ㉚ 斑马纹（2026-09-24 六轮）
    ('专业页：斑马纹底纹 alpha 归零（分支还在、看不见）', MUT_PROF_LV_ZEBRA_A0),
    ('专业页：行永远不落 __z（没有一行被画上底纹）', MUT_PROF_LV_ZEBRA_ZGONE),
    # ㉘ 副本入口标记（2026-09-24 用户要求）
    ('入口标记：入口表查不到（点标题不落点）', MUT_ENT_LOOKUP_DEAD),
    ('入口标记：标题脱掉 OnMouseUp（点不动）', MUT_ENT_TITLE_UNBOUND),
    ('入口标记：未收录也给兜底坐标（反向对照失效）', MUT_ENT_FALLBACK_COORD),
    # ⑫-b 暴风城坐标口径守护（2026-09-24 暴风城地图按新生代边界重画）
    ('同步：暴风城坐标退回经典边界口径（点图落错位置）', MUT_SW_COORD_STALE),
    # ① 站点数据弃用（用户 2026-09-22 决定：客户端没有就明说，绝不回退站点）
    ('站点弃用：物品名回退站点名（占位文案不再出）', MUT_NAME_SITE),
    ('站点弃用：名字不再走异步取数口', MUT_NAME_ORDER),
    ('站点弃用：部位在客户端无数据时回退站点部位串', MUT_META_SITE),
    ('站点弃用：图标兜底改固定站点图标名', MUT_ICON_SITE),
    ('站点弃用：提示框把站点逐行文本接回来', MUT_TIP_SITE_BACK),
    ('站点弃用：分类重新读站点「部位」字段', MUT_CAT_SITE),
    ('站点弃用：分类判定整体失效（全归 other）', MUT_CAT_OTHER),
    ('站点弃用：QualOf 重新长出 fallback 形参', MUT_QUAL_FALLBACK),
    ('站点弃用：QualOf 不再走同步口（只认异步）', MUT_QUAL_ASYNC_ONLY),
    ('站点弃用：NsCall 不再 pcall（未知 id 会抛错）', MUT_NS_NO_PCALL),

    # ② 闪退 / 池化
    ('列表：重建 scroll child + SetParent(nil)', MUT_LIST_OLD),
    ('详情：行池每次强制新建行帧', MUT_DETAIL_OLD),

    # ③ 提示框
    ('提示框：摘掉 SetHyperlink 的 pcall 保护', MUT_TIP_PCALL),
    ('提示框：GetItemInfo 当门槛（懒加载误判的根因）', MUT_TIP_GATE),
    ('提示框：预热空转（不请求任何物品）', MUT_TIP_PREWARM),
    ('提示框：不注册到货事件', MUT_TIP_LISTENER),
    ('提示框：接回「掉率」行（用户第二轮明确删掉）', MUT_TIP_DROP_RATE),
    ('提示框：缓存态原生分支被摘（退回只给占位）', MUT_TIP_NO_BYID),
    ('提示框：末行恒承诺「加载中」（判据又恒真）', MUT_TIP_PROMISE),
    ('请求：摘掉官方异步口（Item:CreateFromItemID）', MUT_REQ_ASYNC),
    ('预热：不再对名字未到货的物品强制重请', MUT_PREWARM_FORCE),
    ('名字可见：不再监听第二条件到货事件 ITEM_DATA_LOAD_RESULT', MUT_EVT_ASYNC_NAME),
    ('名字可见：打开详情不再排定时重扫', MUT_NO_SWEEP),
    ('名字可见：重扫不再跳过已到货的卡（每轮白刷）', MUT_SWEEP_NO_SKIP),
    ('名字可见：到货后不打 __named 标记（会被反复重扫）', MUT_NO_NAMED_MARK),
    ('名字可见：绑定时不记 __named（复用的卡会被漏掉）', MUT_NO_NAMED_BIND),
    ('名字可见：重扫不再尝试 tooltip 收割名字', MUT_HARVEST_GONE),

    # ④ 滚轮
    ('滚轮：详情容器不绑滚轮（根因）', MUT_WHEEL_DETAIL),
    ('滚轮：详情容器不挂 OnMouseWheel', MUT_WHEEL_HANDLER),
    ('滚轮：掉落卡片不转发（压在卡上滚不动）', MUT_WHEEL_CARD),
    ('滚轮：任务行不转发（压在任务行上滚不动）', MUT_WHEEL_QROW),
    ('任务页：不监听 QUEST_LOG_UPDATE（接任务不刷新）', MUT_NO_LOGUPD),
    ('滚轮：步进 48 -> 32', MUT_WHEEL_STEP),
    ('滚轮：滚动上限算错（内容高 + 视口高）', MUT_WHEEL_MAX),
    ('两列：右列详情不联动（渲染尾部摘 RenderQuestDetail）', MUT_NO_QDET),
    ('两列：阵营档不自动勾当前角色阵营', MUT_NO_SIDEAUTO),
    ('两列：前导链不读前置 ID 字段', MUT_NO_PREQ9),
    ('两列：奖励芯片不读奖励字段', MUT_NO_REW),
    ('两列：点行不选中', MUT_NO_QCLICK),
    ('任务行退回 Frame（实机 OnClick 报错）', MUT_ROW_FRAME),
    ('前导链跨副本就断（PreExtra 不参与）', MUT_QPRE_GONE),
    ('前导链没有「下一步」进度标', MUT_NO_FRONTIER),
    ('表外链环节不显示起始 NPC', MUT_PRE_NO_START),
    ('起始行退回纯站点名（#NPCID 没了）', MUT_NPC_ID_GONE),
    ('表外链 src 来源回退没了（96391 物品起始）', MUT_SRC_GONE),
    ('详情页收获节没了（经验/金钱/声望）', MUT_GAINS_GONE),
    ('任务难度行不显示', MUT_NO_DIFF),
    ('详情职业专属行不显示', MUT_NO_CLS_LINE),
    ('「任务需求」节不显示', MUT_NO_REQ_SECT),
    ('奖励退回单列', MUT_CHIP_1COL),
    ('左列行内职业徽记消失', MUT_ROW_CLS_GONE),
    ('悬停离开后选中态被冲掉', MUT_SEL_LEAVE),
    ('卡中卡：任务行退回 L1 同档', MUT_INNER_L1_QROW),
    ('卡中卡：节点行退回 L1 同档', MUT_INNER_L1_NODE),
    ('卡中卡：档位路由失效（baseN=2 不生效）', MUT_INNER_ROUTE),
    ('奖励色单变量接 QColor（实机 Unpack 崩）', MUT_QC_SINGLE),
    ('底板卡不随页签显隐', MUT_NO_PLATE),
    ('第二列又不剥坐标（地图名带坐标）', MUT_ROW_GIVER),
    ('节点取件不复位常态色', MUT_NODE_RESET),
    ('阵营档不再含双阵营通用任务', MUT_SIDE_NO_NEUTRAL),
    ('右列详情名去掉任务ID', MUT_NO_QID),
    ('板卡退回重叠几何', MUT_PLATE_OVERLAP),

    # ⑤ 卡片墙几何
    ('卡片墙：列数 3 -> 2', MUT_CARD_COLS),
    ('卡片墙：卡高 44 -> 30', MUT_CARD_H),
    ('卡片墙：名称字号 14 -> 18（3 列放不下）', MUT_CARD_FONT),
    ('卡片墙：摘掉每轮底色复位（悬停态会残留）', MUT_CARD_BG_RESET),

    # ⑥ 品质
    ('品质：到货不刷卡片色（一直停在占位/旧值）', MUT_QUAL_LISTEN),
    ('品质：色表索引错位（蓝变绿）', MUT_QUAL_TAB),

    # ⑦ 加载链路
    ('加载：摘掉隐藏 tooltip 兜底触发', MUT_LOAD_TIP),
    ('加载：RequestItem 不再保证监听器就位', MUT_LOAD_LISTENER),

    # ⑧ 取数口形态
    ('取数口：摘掉 C_Item 命名空间兜底（本端根因）', MUT_API_NO_NS),
    ('取数口：Instant 不兜底命名空间（图标/部位/分类）', MUT_API_NO_NS_I),
    ('取数口：RequestItem 第二路不再兜底命名空间', MUT_API_NO_NS_REQ),
    ('取数口：改回裸调全局 GetItemInfo（本端恒 nil）', MUT_API_BARE),

    # ⑨ 地图标记（2026-09-22 第三批）
    ('地图标记：MarkNPC 不落航点（摘 SetUserWaypoint）', MUT_NPC_WP_GONE),
    ('地图标记：起始行退回 Frame（OnClick 失效）', MUT_NPC_BTN_GONE),
    ('地图标记：起始行 __npc 不赋值（点了不干活）', MUT_NPC_STARTNPC_GONE),
    ('地图标记：前导链表外 NPCID 反查摘掉', MUT_NPC_PRENPC_GONE),
    ('地图标记：NPC 金名退回灰字（可点暗示丢失）', MUT_NPC_GOLD_GONE),

    # ⑩ 跨插件命名空间（2026-09-23 实机事故）
    ('命名空间：页面构建函数退回裸全局（会被后加载的同名插件覆盖）', MUT_BARE_GLOBAL),

    # ⑪ 顶栏胶囊：5人本 / 团本 + 上移 15（用户 2026-09-23）
    ('胶囊：上移量被改回 -ROW_SUB（没上移）', MUT_CAPSULE_NO_LIFT),
    ('胶囊：团本那颗入口消失（退回单页签）', MUT_RAID_TAB_GONE),
    ('胶囊：SwitchSub 又把 key 丢掉（永远只显示 5人本）', MUT_SWITCH_IGNORES_KEY),
    ('胶囊：切团本时副本页不隐藏（两页同时显示）', MUT_RAID_SHOW_BOTH),
    ('胶囊：UpdateActiveSub 在团本态也刷新（空态页误刷副本页）', MUT_UAS_NO_SKIP),

    # ⑫ 上游数据同步下限守护（2026-09-23 NPCLoc 176->237 / QuestPreNpcID 9->218）
    ('同步：NPCLoc 表被清空（数据退回旧版）', MUT_NPCLOC_EMPTY),
    ('同步：QuestPreNpcID 表被清空（表外链落旗失效）', MUT_PRE_NPCID_EMPTY),

    # ⑬ 物品卡 Shift+点击 → 聊天框（用户 2026-09-23 要求）
    ('Shift 点击：拿到 Shift 了，但不再看 Shift（随手一点就发）', MUT_CLICK_NO_SHIFT),
    ('Shift 点击：客户端未缓存时不再兜底（懒加载回 nil 就发不出去）', MUT_CLICK_NO_FALLBACK),
    ('Shift 点击：卡片退回 Frame（实机不支持 OnClick）', MUT_CLICK_FRAME),
    ('Shift 点击：聊天框没开时那一路被摘掉', MUT_CLICK_NO_OPENCHAT),
    ('Shift 点击：右键也投递（不再只认左键）', MUT_CLICK_ANY_BUTTON),

    # ⑭ 提示框换肤：装备提示框不套插件皮（用户 2026-09-23 口径）
    ('换肤：物品判据退回只看打标（装备提示框又套上插件皮）', MUT_TIP_ITEM_SKIN),

    # ⑮ 专业页（仅无限服，2026-09-23）
    ('专业页：钓鱼技能等级表 ranks 从不发射（整块静默消失）', MUT_PROF_RANKS_GONE),
    ('专业页：第三颗「专业」胶囊消失（无限服退回两颗）', MUT_PROF_CAPSULE_GONE),
    ('专业页：gsub 少套括号（多返回值直灌末参 → 整页崩）', MUT_PROF_GSUB_MULTI),
    ('专业页：行退回 Frame（实机不支持 OnClick）', MUT_PROF_ROW_FRAME),
    ('专业页：活代码里出现 SetParent（scroll child 悬空指针）', MUT_PROF_SETPARENT),
    ('专业页：渲染调度里新建帧（池化复用被破）', MUT_PROF_RENDER_FRAME),
    ('专业页：钓鱼不再先分流（对数字 ipairs → 实机必崩）', MUT_PROF_FISH_SPLIT),

    # ⑯ 专业页观感六改（2026-09-23 用户口径）
    ('专业页：大卡片没定位（等于没有大卡）', MUT_PROF_BIGCARD_UNPOS),
    ('专业页：左导航容器卡被摘', MUT_PROF_NAVCARD_GONE),
    ('专业页：军需官阵营图标回退旧物品图标', MUT_PROF_FACICON_BACK),
    ('专业页：总览退回双栏（单列口径被推翻）', MUT_OV_SINGLECOL),
    ('专业页：总览数字速览回潮', MUT_PROF_SPEEDVIEW_BACK),
    ('专业页：齿轮右缘错位回潮', MUT_PROF_GEAR_MISALIGN),
    ('专业页：HUD按钮压外卡描边回潮', MUT_PROF_HUD_REDGE),
    ('专业页：搜索框压外卡描边回潮', MUT_PROF_SB_REDGE),
    ('专业页：快照卡压外卡描边回潮', MUT_PROF_SNAP_REDGE),
    ('专业页：信息卡死宽回潮（整行溢出）', MUT_PROF_TILE_FIXEDW),
    ('专业页：总览已学卡绿描边断开', MUT_PROF_IX_GREEN_GONE),
    ('专业页：总览卡名称字号回潮 12', MUT_PROF_IX_FS_BACK),
    ('专业页：上次页面记忆断开', MUT_PROF_MEM_GONE),
    ('专业页：商人阵营过滤被击穿', MUT_PROF_VSIDE_GONE),
    ('专业页：商人多人数「等 N 人」回潮单人', MUT_PROF_VMULTI_GONE),
    ('专业页：商人选择弹窗被旁路（直落第一个）', MUT_PROF_VPICK_GONE),
    ('专业页：换专业弹窗不收（锚失主飘窗）', MUT_PROF_VPICK_STAY),
    ('专业页：默认页回潮 __index', MUT_PROF_DEFSLUG_BACK),
    ('专业页：名称按 nameW 截断回潮（右留间距左出 …）', MUT_PROF_NAME_FIT_GONE),
    ('专业页：材料数量徽标回潮（N×前缀复活）', MUT_PROF_MATCNT_GONE),
    ('专业页：材料末段整段丢弃回潮（右缘留白）', MUT_PROF_MATTAIL_GONE),
    ('专业页：配方名品质色断开', MUT_PROF_QNAME_GONE),
    ('专业页：材料段品质色断开', MUT_PROF_QSEG_GONE),
    ('专业页：路线方案默认回潮材料成本', MUT_PROF_SCHEME_DEF_GONE),
    ('专业页：路线方案卡消失', MUT_PROF_SCHEME_TILE_GONE),
    ('专业页：切页方案卡残留（Hide 列表漏 scheme）', MUT_PROF_SCHEMEHIDE_GONE),
    ('专业页：方案读取回潮布尔口径（点击不切换）', MUT_PROF_SETTRAW_GONE),
    ('自动路线：最省钱重新排除图纸（两方案恒等回潮）', MUT_PROF_CHEAPSKIP_GONE),
    ('采集页：升级页信息卡不渲染（走制造五卡）', MUT_PROF_GROUTE_GONE),
    ('采集页：熔炼分支消失（采矿只剩采集）', MUT_PROF_SMELT_GONE),
    ('采集页：路线进度卡切换失效（模式锁死）', MUT_PROF_SMODE_GONE),
    ('采集页：升级页签消失', MUT_PROF_GTAB_GONE),
    ('采集页：三列行渲染分支消失', MUT_PROF_GR3_GONE),
    ('采集页：相邻段合并失效', MUT_PROF_GMERGE_GONE),
    ('采集页：矿名偏移漂移', MUT_PROF_GR3_NAMEOFF),
    ('采集页：剥皮技能区间映射丢失', MUT_PROF_SKINMAP_GONE),
    ('升级页：快照 24h 不再天化', MUT_PROF_SNAPDAY_GONE),
    ('升级页：熔炼行退回右列等级', MUT_PROF_SMGR3_GONE),
    ('升级页：采药同档合并失效', MUT_PROF_HMERGE_GONE),
    ('升级页：矿组区间显示丢失', MUT_PROF_MINEGRP_GONE),
    ('采集页：第三列纯图标分支消失', MUT_PROF_GRICON_GONE),
    ('采集页：纯图标池跨页残留', MUT_PROF_GICWIPE_GONE),
    ('升级页：路线标题移工具行失效', MUT_PROF_ROUTEMOVE_GONE),
    ('行池：警告芯片跨页残留', MUT_PROF_WARNWIPE_GONE),
    ('升级页：警告自绘贴图丢失', MUT_PROF_WARNTEX_GONE),
    ('总览：段标题 16 回潮 13', MUT_PROF_HEADFS_GONE),
    ('总览：行悬停 L4 实色回潮白 α', MUT_PROF_HOVERL4_GONE),
    ('总览：正文字号 14 回潮 12', MUT_PROF_OVFS14_GONE),
    ('总览：卡中卡内容内缩丢失', MUT_PROF_SECIN_GONE),
    ('营地：对照表卡中卡丢失', MUT_PROF_BTCARD_GONE),
    ('商人兑换：行三列与本地化名丢失', MUT_PROF_FAVCOLS_GONE),
    ('商人兑换：材料匹配键回退 f[1]', MUT_PROF_FAVKEY_BACK),
    ('附魔：配方页法术图标丢失', MUT_PROF_SPELLICON_GONE),
    ('附魔：升级页 rinfo 色条阈值丢失', MUT_PROF_LVSB_GONE),
    ('配方页：行图标回潮顶锚不居中', MUT_PROF_ICONCEN_GONE),
    ('工具行：纯文字标签宽度钳制回归', MUT_PROF_PLAINOFF),
    ('设置页：齿轮门控失效（每页都显示）', MUT_PROF_SETGEARGATE_GONE),
    ('配方页：滚动条页签门控失效（每页都显示）', MUT_PROF_VSCROLL_GONE),
    ('配方页：滚动条内容同步失效（拖不到底）', MUT_PROF_VSCROLLSYNC_GONE),
    ('自动路线：最省钱指标丢图纸价', MUT_PROF_FCHEAP_GONE),
    ('自动路线：乐观计数收益回潮概率口径', MUT_PROF_OPTIM_GAIN_GONE),
    ('专业页：弹窗点关盾断开（点别处不收窗）', MUT_PROF_PICKSHIELD_GONE),
    ('专业页：名称列间距回潮 44', MUT_PROF_PAD_REGROWN),
    ('专业页：副行扫描丢角标宽', MUT_PROF_SUBSCAN_GONE),
    ('专业页：设置问号提示被断开', MUT_PROF_HELP_GONE),
    ('专业页：搜索框与宿主卡同级倒挂回潮', MUT_PROF_SEARCH_SAMELVL),
    ('专业页：页签胶囊间距回潮 4', MUT_PROF_SUBTAB_GAP4),
    ('专业页：升级页切换组间距回潮 2', MUT_PROF_TOOL_PAIRGAP),
    ('专业页：行又各自成卡（一张大卡的意义没了）', MUT_PROF_ROW_CARD),
    ('专业页：阈值数字不再染色（退回纯数字）', MUT_PROF_TIER_NOCLR),
    ('专业页：阈值三个数字同色（等于没染）', MUT_PROF_TIER_SAMECLR),
    ('专业页：并入总览的页签长回来（PROF_SUBTABS 回 5+ 项）', MUT_PROF_TABS_REGROW),
    ('专业页：分类按钮退回定宽 72（长名被裁）', MUT_PROF_TOOL_FIXEDW),

    # ⑰ 专业页三轮补丁（2026-09-23 傍晚，用户逐条）
    ('专业页：新配方的绿色「新」字被摘', MUT_PROF_NEW_TAG_GONE),
    ('专业页：来源行又亮出「读物：子站名」', MUT_PROF_READ_BACK),
    ('专业页：总览传承段被摘（四合一内容丢失）', MUT_PROF_MERGE_GONE),
    ('专业页：camping 对照表举手被砍（总览不出总表）', MUT_PROF_CAMP_BONUS_GONE),

    # ⑱ 升级页通栏改版 + 职业加成签名（2026-09-23 晚）
    ('专业页：单列页行宽被压窄（col=1 恒收 COL_LW）', MUT_PROF_ROW_NARROW),
    ('专业页：分段行写回「技能」前缀', MUT_PROF_STEP_SKILL),
    ('专业页：右栏备料清单跑回左栏', MUT_PROF_SHOP_RIGHT_GONE),
    ('专业页：分段行次制作被摘', MUT_PROF_STEP_NOCNT),
    ('专业页：总览长回旧「营地三档」行（D1 去重失效）', MUT_PROF_DUP_CAMP),

    # ⑲ 配方页去详情条 + 材料行内图标（2026-09-23 晚）
    ('专业页：配方材料的小图标被摘', MUT_PROF_MATICON_GONE),
    ('专业页：配方详情条长回来', MUT_PROF_DETAIL_BACK),

    # ⑳ 材料列改版（2026-09-24）
    ('专业页：材料又挤回副行（11pt 小字原状）', MUT_PROF_MATCOL_BACK),
    ('专业页：两栏比例拉平（右栏不再留窄）', MUT_PROF_COL_RATIO_FLAT),
    ('专业页：材料列字体串退回 11pt', MUT_PROF_MAT_FS_WIRING),

    # ㉑ 升级页两栏（2026-09-24 二轮）
    ('专业页：升级页不亮分栏线（两栏又读成一条横排）', MUT_PROF_LVSPLIT_GONE),
    ('专业页：次数不再贴左栏右缘（跑到栏中间）', MUT_PROF_CNT_AGAIN_MATS),
    ('专业页：分栏线淡到看不见（等于没画）', MUT_PROF_DIV_FAINT),

    # ㉒ 升级页左栏材料列 + 区间列宽（2026-09-24 三轮）
    ('专业页：分段行行内材料列又被摘掉', MUT_PROF_LV_STEP_MATS_GONE),
    ('专业页：区间列宽写死（三位数区间压名称）', MUT_PROF_LVNAME_FIXED),

    # ㉓ 悬停高亮划走不灭 + 商人兑换译名（2026-09-24 四轮）
    ('专业页：划走后行又回到常态淡框（用户报的常亮复活）', MUT_PROF_HL_LEAVE_BG),
    ('专业页：悬停状态不再定时与鼠标对齐（滚轮后那一行常亮）', MUT_PROF_HL_NOSYNC),
    ('专业页：同步只灭不亮（鼠标在行上时高亮被熄掉）', MUT_PROF_HL_ALWAYSOFF),
    ('专业页：商人兑换货币退回旧译名「恩惠」', MUT_PROF_FAVOR_LABEL),

    # ④ 升级页四列宽度全给材料（2026-09-24 布局四轮）
    ('专业页：右栏没把宽度让给左栏（两栏宽度拉平）', MUT_PROF_LVCOL_RW_FLAT),
    ('专业页：名称列写死回 150（名称与材料间又留大片白）', MUT_PROF_LVNAMEW_FAT),
    ('专业页：材料列右缘不贴次数保留区（间距吃回 12）', MUT_PROF_LVMAT_CNTGAP),
    ('专业页：名称→材料间距吃回 12（白没留给材料）', MUT_PROF_LVMAT_NAMEGAP),

    # ㉕ 采集页去英文 + 钓鱼折两栏（2026-09-24）
    ('专业页：区域名绕过客户端（恒落 区域 #ID）', MUT_PROF_ZONENAME_RAW),
    ('专业页：采集节点标题不问客户端（恒落 物品 #ID）', MUT_PROF_NODE_TITLE_RAW),
    ('专业页：钓鱼采集页退回单列（两栏没了）', MUT_PROF_FISH_GRID_OFF),
    ('专业页：网格不再自动分列（全塞第 1 栏）', MUT_PROF_GRID_ONE_COL),

    # ㉖ 升级分段行两行表格 + 两侧图标同尺寸 + 来源补齐（2026-09-24 布局五轮）
    ('专业页：配方图标尺寸与材料图标不一致', MUT_PROF_LV_TBL_ICON_DIFF),
    ('专业页：材料图标尺寸自己写死（两边又不一样）', MUT_PROF_LV_TBL_MAT_ICON_DIFF),
    ('专业页：来源卡片不显示了（来源信息又消失）', MUT_PROF_LV_TBL_SRC_GONE),
    ('专业页：色阶条塌到配方名那一行（两行叠一起）', MUT_PROF_LV_TBL_SRC_SAMEY),
    ('专业页：等级竖线只剩一根（第二根丢了）', MUT_PROF_LV_PIN_DUAL_GONE),
    ('专业页：终点竖线退回「向下吸」（106 又落回 100 那道交界）', MUT_PROF_LV_PIN_HI_NO_UP),
    ('专业页：材料块不再给省略号留那一格', MUT_PROF_LV_TBL_NO_MARK_ROOM),
    ('专业页：材料组不再右对齐（左起摆）', MUT_PROF_LV_TBL_GROUP_LEFT),
    ('专业页：材料块数量角标归零（块失去 ×N）', MUT_PROF_LV_TBL_CNT_ZERO),

    # ㉗ 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）
    ('前导链备注：备注行不再渲染', MUT_QPRENOTE_OFF),
    ('前导链备注：备注挂到了别的任务上（界面读不到）', MUT_QPRENOTE_WRONGKEY),

    # ㉘ 配方搜索 + 名称列现算（2026-10-09）
    ('搜索：列表过滤被绕过（搜索框形同虚设）', MUT_SEARCH_FILTER_GONE),
    ('搜索：名称列退回固定分割（材料列变窄）', MUT_RECIPE_COLS_STATIC),
    ('搜索：切离配方页搜索框不隐藏', MUT_SEARCH_HIDE),
    ('搜索：输入后不重渲染（要按回车才滤）', MUT_SEARCH_NORENDER),

    # ㉚ 专业页大列表分帧 + 顶部进度条（2026-10-09）
    ('专业页：渲染那一帧又同步建行帧（分帧白做、进度条不亮）', MUT_PROFGATE_SYNC_BACK),
    ('专业页：间距行不入队（行池按索引取用留空洞）', MUT_PROFGATE_GAP_NOT_QUEUED),
    # ㉚b 配方页「点开那一瞬间」的同步重计算（2026-10-09 第二轮，用户报仍卡）
    ('专业页：首屏退回复建全量 spec（点开那一帧的卡顿回来了）', MUT_PROF_FULL_SPEC_BUILD),
    ('专业页：spec 又预算材料串与行文案（FitRecipeCols 随后重算一遍 = 纯白做）',
     MUT_PROF_SPEC_PREBUILD),
    ('专业页：量宽记忆化被摘（同一材料在几百条配方里反复逐字符量宽）', MUT_PROF_NO_TW_MEMO),
    ('专业页：物品请求不再按 id 去重（一页几百条重复请求同一批物品）', MUT_PROF_NO_REQ_DEDUP),
    ('专业页：物品名记忆表不清（「名字未到货」的占位被钉死一整局）', MUT_PROF_NO_NM_RESET),
    ('专业页：材料图标查询又直调 DG.ItemIcon（一页上千次同源引擎调用）', MUT_PROF_NO_ICON_MEMO),
    ('专业页：扫描又给全量行量宽（只画 300 行却量 511 行）', MUT_PROF_SCAN_ALL_ROWS),
    ('Hui：皮按钮边框帧每次 SetSize 都重建（工具行换文案 = 20 颗各建两副）', MUT_HUI_SKIN_REBUILD),
    ('专业页：行帧已在池里也本帧全量重绑（切回配方页那一下又 100ms+）', MUT_PROF_ROW_SYNC_ALL),
    ('专业页：工具行闸门插桩被摘（21ms 又拆不开，只能读代码猜）', MUT_PROF_TOOL_GATE_UNMARKED),
    ('Hui：像素条复算退回全表扫描（工具行 Show 每颗又 ~1.5ms）', MUT_HUI_STRIP_SCAN_ALL),
    ('专业页：材料串退回「全部行现算」（点开那一帧又背 ~8ms）', MUT_PROF_MATS_DEFER_GONE),
    ('专业页：物品名记忆表连「已到货」也清（每帧渲染又重问一遍全部名字）', MUT_PROF_NM_MEMO_RESET_ALL),
    ('专业页：空闲预热被摘（点开配方页那一帧又得现向引擎要 300 个名字）', MUT_PROF_WARM_GONE),
    # ㊿ 升级 HUD 路线模式（2026-10-11 用户）
    ('升级 HUD：自动门禁失效（永远固定路线）', MUT_HUD_ROUTEMODE_OFF),
    ('升级 HUD：段标掉模式前缀（数据换了看不出）', MUT_HUD_SEG_NO_MODE),
    ('升级 HUD：配方查找表不并 rinfo（附魔段「材料未收录」）', MUT_HUD_RINFO_GONE),
    ('升级 HUD：药丸 Unpack 当非末位实参（已备齐绿丸算色崩，实机 25 连报）',
     MUT_HUD_PILL_UNPACK_INLINE),
    ('升级 HUD：药丸胶囊件消失（退回直角色块）', MUT_HUD_PILLCAP_GONE),
    ('升级 HUD：药丸染漆失效（整列透明）', MUT_HUD_PILLPAINT_GONE),
    # 2026-10-11 购物清单「只显示缺失」开关（用户）
    ('升级 HUD：表头长文案复辟（用户要求改短没落实）', MUT_HUD_HEAD_LONG_AGAIN),
    ('升级 HUD：只显示缺失开关不摆位（表头右侧看不到按钮）', MUT_HUD_SHOPTOG_GONE),
    ('升级 HUD：缺失过滤失效（已备齐的又显示出来）', MUT_HUD_FILTER_AFTER_COLS),
    ('升级 HUD：空清单又退回 Hide（开关一开就永远点不开清单）', MUT_HUD_SHOPEMPTY_HIDE),
    ('升级 HUD：空清单灰字没建（空面板无任何说明）', MUT_HUD_SHOPEMPTY_NOTEXT),
    ('升级 HUD：固定路线不按目标等级裁剪（一路画到 300）', MUT_HUD_FIXED_NO_TARGET_CLIP),
    ('升级 HUD：跨目标段不按比例折算（目标内次数算多）', MUT_HUD_TARGET_CLIP_NO_RESCALE),
    ('升级 HUD：目标等级改了不即时重推（HUD 停在旧段数）', MUT_HUD_REFRESH_ROUTE_GONE),
    # 2026-10-11 用户：「只显示缺失的这个开关，左边写上文字“仅显示缺失”」
    ('升级 HUD：开关左侧标签没建（用户要的「仅显示缺失」文字缺失）', MUT_HUD_MISSLAB_GONE),
    ('升级 HUD：标签锚到开关右边（文字跑到开关右侧）', MUT_HUD_MISSLAB_RIGHT_SIDE),
    ('升级 HUD：标签挂开关身上（被 ReskinToggle 的 PurgeNative 隐藏 = 实机看不到）', MUT_HUD_MISSLAB_ON_TOGGLE),
    ('升级 HUD：表头让位量写死（enUS 宽标签会压表头）', MUT_HUD_HEADRESERVE_HARDCODED),
]


def file_is_crlf(data):
    cr = data.count(b'\r\n')
    return cr > 0 and data.count(b'\n') == cr

def to_file_style(anchor, data):
    if file_is_crlf(data):
        return anchor.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    return anchor.replace(b'\r\n', b'\n')


def split_spec(spec):
    """变异元组：(old, new) 默认打 Core/DungeonUI.lua；('Core/Xxx.lua', (old, new)) 可指定其它文件。

    ★ 只认 2 元组：多写一段会被当成 new，注入结果是 **Lua 语法错**（harness 报
      loadfile 返回 nil）—— 那是「脏抓」：看起来变红了，其实没证明任何断言非恒真。
      踩过一次（MUT_TIP_PREWARM 被写成 3 元组）。
    """
    if len(spec) == 2 and isinstance(spec[0], str):
        return spec[0], spec[1][0], spec[1][1]
    assert len(spec) == 2, '变异必须是 2 元组 (old, new)，当前 %d 元' % len(spec)
    return 'Core/DungeonUI.lua', spec[0], spec[1]


def _harness_once():
    """跑一遍 harness，返回 (returncode, stdout+stderr)。"""
    r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def _fail_lines(out):
    """harness 输出里的失败行**去重集合**，用于取差集（基线 vs 注入后）。

    ★ 同一条失败会打两遍：详情 `  [FAIL] 名字  [附注]` 与汇总 `  ✗ 名字` —— 两者文本不等
      （详情带附注）⇒ 两个都收会把基线 22 条数成 44。**只认 `[FAIL]` 那一份**；
      万一一条 `[FAIL]` 都没有（整体崩了），退回 `✗` 行，别把「崩」当成「无失败」。
    """
    lines = [ln.strip() for ln in out.split('\n')]
    det = sorted({s[len('[FAIL]'):].strip() for s in lines if s.startswith('[FAIL]')})
    if det:
        return det
    return sorted({s[1:].strip() for s in lines if s.startswith('✗')})


def main():
    # 变异可跨文件（本插件的副本页代码全部落在 Core/DungeonUI.lua）
    files = {}
    for name, spec in MUTATIONS:
        fname, old, new = split_spec(spec)
        files.setdefault(fname, []).append((name, old, new))
    for fname in files:
        p = os.path.join(BETA, *fname.split('/'))
        orig = open(p, 'rb').read()
        print('原文件 %s：%d 字节，CRLF = %d' % (fname, len(orig), orig.count(b'\r\n')))
    # ★ 基线：先跑一遍**未变异**的 BETA。harness 里常年挂着别的工作线留下的失败断言
    #   （并发开发时尤甚）；不取差集的话「FAIL 数 > 0」恒为真 ⇒ 整批变异都会被当成
    #   「被抓住」，这条检查静默失效（同 df_check_new_muts.py 的教训）。
    _rc0, base_out = _harness_once()
    base_fails = set(_fail_lines(base_out))
    if base_fails:
        print('基线（未变异）：%d 条既有 FAIL（与本批无关，按差集判定）' % len(base_fails))
    else:
        print('基线（未变异）：无既有 FAIL')
    # ★ 2026-10-09（rev18）：① 锚点命中数**必须**按 `to_file_style` 后的形态数（变异锚点一律
    #   按 LF 书写，对 CRLF 产物直接 count(old) 恒 0 ⇒ 合法锚点被误判「不存在」）；
    #   ② 死锚只跳过该条、不再整批中止；③ 合法锚点被同文件更早的变异吃掉 ⇒ 只算「冲突」，
    #   不算死锚（那种变异单条隔离时照样能把断言打红，守卫是好的）。
    payloads, dead, conflict, injected = {}, [], [], 0
    for fname, items in files.items():
        p = os.path.join(BETA, *fname.split('/'))
        data = open(p, 'rb').read()
        pristine = data
        for name, old, new in items:
            c0 = pristine.count(to_file_style(old, pristine))
            if c0 != 1:
                dead.append((name, fname, c0))
                continue
            o, nw = to_file_style(old, data), to_file_style(new, data)
            c1 = data.count(o)
            if c1 != 1:
                conflict.append((name, fname, c1))
                continue
            data = data.replace(o, nw)
            injected += 1
            print('已注入变异：%s  [%s]' % (name, fname))
        payloads[fname] = data
    if dead:
        print('=' * 60)
        print('★ %d 条变异**死锚**（原始文件上就非 1 次）—— 锚点过期，等于没人守：' % len(dead))
        for name, fname, c in dead:
            print('    %2d 次  %-24s %s' % (c, fname, name))
        print('  → 重锚后跑 `python _temp/check_mut_anchors.py` 复检；'
              '单条守卫用 `python _temp/_mut_isolate.py <关键字>`。')
        print('=' * 60)
    if conflict:
        print('★ %d 条变异与同文件里更早的变异**改同一段**（锚点本身健康，批量注入时被吃掉）：'
              % len(conflict))
        for name, fname, c in conflict:
            print('        %-24s %s' % (fname, name))
        print('  → 守卫由 `_mut_isolate.py`（单条隔离）负责；批量注入本就不该同时生效。')
    print('本批：注入 %d 条 / 死锚 %d 条 / 冲突 %d 条（共 %d）'
          % (injected, len(dead), len(conflict), injected + len(dead) + len(conflict)))
    try:
        for fname, data in payloads.items():
            p = os.path.join(BETA, *fname.split('/'))
            open(p, 'wb').write(data)
            bare = data.count(b'\n') - data.count(b'\r\n')
            print('  %s 注入后 CRLF = %d / 裸 LF = %d' % (fname, data.count(b'\r\n'), bare))
        _rc, out = _harness_once()
        print(out[-2600:])
        crash = ('loadfile 返回 nil' in out) or ('Traceback' in out)
        newf = [l for l in _fail_lines(out) if l not in base_fails]
        print('=' * 60)
        print('变异后：新 FAIL %d 条（总 %d / 基线 %d）· 脏抓=%s'
              % (len(newf), len(_fail_lines(out)), len(base_fails), crash))
        if crash:
            print('✗ 注入后整体崩了（loadfile 返回 nil / Traceback）—— 这次注入无效，别当成功')
            return 1
        if newf:
            print('✓ 变异被抓住（harness 非恒真）')
            return 0
        print('✗ 变异未被抓住 —— 断言是白测，必须修 harness')
        return 1
    finally:
        # 用 titan 端干净文件还原 beta（二进制，保 CRLF）
        for fname in files:
            src = os.path.join(TITAN, *fname.split('/'))
            dst = os.path.join(BETA, *fname.split('/'))
            shutil.copyfile(src, dst)
            back = open(dst, 'rb').read()
            print('还原 %s：%d 字节（与 titan 一致 = %s）'
                  % (fname, len(back), back == open(src, 'rb').read()))


if __name__ == '__main__':
    sys.exit(main())

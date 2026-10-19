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


def _b(*lines):
    return ('\r\n'.join(lines) + '\r\n').encode('utf-8')

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

# 原生分支不再优先 SetItemByID（退回只认 SetHyperlink）。期望：静态「优先 SetItemByID」
# + 动态「按 ID 出提示框优先走 SetItemByID」失败。
MUT_TIP_NO_BYID = (
    b'    if id and GameTooltip.SetItemByID then\r\n',
    b'    if false and id and GameTooltip.SetItemByID then   -- MUT: no SetItemByID\r\n')

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
    # 名字收割改动后 RefreshItemCards 行缩进 12->16，且该范式出现 2 次
    # （item 池 / 任务奖励 chip 池）-> 用前一行 local c = pool[i] 钉 item 池。
    b'            local c = pool[i]\r\n            local it = c and c.__it\r\n'
    b'            if it and not c.__named then\r\n'
    b'                DG.RefreshItemCards(it[1])\r\n',
    b'            local c = pool[i]\r\n            local it = c and c.__it\r\n'
    b'            if it then -- MUT: sweep rescans named cards\r\n'
    b'                DG.RefreshItemCards(it[1])\r\n')

MUT_NO_NAMED_MARK = (
    (
        _b('                c.__named = hasName') +
        _b('            end') +
        _b('            if c.icon and c.icon.SetTexture then')
    ),
    (
        _b('                -- MUT: no __named mark') +
        _b('            end') +
        _b('            if c.icon and c.icon.SetTexture then')
    ),
)

# name harvest removed. expect: static harvest assertion fails.
MUT_HARVEST_GONE = (
    # 收割块有两处（item 池 + chip 池），钉单处杀不干净 -> 直接改函数定义名，
    # 两个调用点 guard 同时拿 nil，且 'function DG.HarvestTipName' 子串消失。
    # 注意新名不能含 'HarvestTipName' 前缀（静态断言是子串判定）。
    b'function DG.HarvestTipName(id)\r\n',
    b'function DG.TipHarvestGone_MUT(id)\r\n')

MUT_NO_NAMED_BIND = (
    b'                    -- \xe7\xbb\x91\xe5\xae\x9a\xe6\x97\xb6\xe8\xae\xb0'
    b'\xe4\xb8\x8b\xe3\x80\x8c\xe5\x90\x8d\xe5\xad\x97\xe5\x88\xb0'
    b'\xe6\xb2\xa1\xe5\x88\xb0\xe3\x80\x8d\xef\xbc\x9b\xe5\x8d\xa1'
    b'\xe7\x89\x87\xe4\xbc\x9a\xe8\xa2\xab\xe5\xa4\x8d\xe7\x94\xa8'
    b'\xef\xbc\x8c\xe6\xaf\x8f\xe6\xac\xa1\xe7\xbb\x91\xe5\xae\x9a'
    b'\xe9\x83\xbd\xe9\x87\x8d\xe8\xae\xb0\r\n'
    b'                    r.__named = hasName\r\n',
    b'                    -- MUT: no __named mark on bind\r\n')



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

MUT_DETAIL_OLD = (b'        local r = rows[nI]\r\n        if not r then',
                  b'        local r = nil\r\n        if not r then')

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
    _PREWARM_BODY,
    '    DG.EnsureItemListener()\r\n'
    '    if true then return end   -- MUT: prewarm does nothing\r\n'
    '    for _, s in ipairs(loot) do\r\n'
    '        for _, it in ipairs(s[5]) do\r\n'
    '            local _, hasName = DG.ItemName(it[1])\r\n'
    '            DG.RequestItem(it[1], not hasName)\r\n'
    '        end\r\n'
    '    end'.encode('utf-8'))

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
    b'            r:EnableMouseWheel(true)\r\n'
    b'            r:SetScript("OnMouseWheel", function(self, delta)\r\n'
    b'                DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)\r\n',
    b'            -- MUT: loot card eats the wheel\r\n'
    b'            r:SetScript("OnMouseWheel", function(self, delta)\r\n'
    b'                DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)\r\n')

# 任务页：摘掉 QUEST_LOG_UPDATE 监听 —— 接任务不触发重刷，刚接的任务要重开页面
# 才变「进行中」（2026-09-22 实机踩过）。期望：静态「QUEST_LOG_UPDATE 监听」失败。
MUT_NO_LOGUPD = (
    # 2026-09-28 收获 API 取数段新增了第二个 QUEST_LOG_UPDATE 监听（奖励晚到指纹比对），
    # 单行锚会命中 2 次 → 连下一行 OnEvent 钉死在任务状态监听那一处
    # （新监听下一行是 pcall RegisterEvent，不命中；两行间夹中文注释，字节锚禁中文不能跨行锚）。
    b'    ev:RegisterEvent("QUEST_LOG_UPDATE")\r\n    ev:SetScript("OnEvent", function(_, event, arg1)\r\n',
    b'    -- MUT: no quest log update listener\r\n    ev:SetScript("OnEvent", function(_, event, arg1)\r\n')

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

MUT_CARD_COLS = (b'DG.LOOT_COLS = 3', b'DG.LOOT_COLS = 2')
MUT_CARD_H = (b'DG.LOOT_CARD_H = 44', b'DG.LOOT_CARD_H = 30')

# 名称字号 14 -> 18 —— 3 列卡内放不下（最长名 16 字 = 288px > 可用 253px），
# 容量守门（字号 <= 15 且 字号x16 + 内边距 <= 卡宽）应失败
MUT_CARD_FONT = (b'DG.LOOT_FS_NAME = 14', b'DG.LOOT_FS_NAME = 18')

# 摘掉「每轮刷新复位常态底色」—— 池化卡会带着上一张卡的悬停态被复用。
# 运行时断言（包一层 SetBackdropColor 看最后一次 alpha）与静态计数（应为 3 处）都会失败。
_CMT = '                    -- \u6bcf\u6b21\u5237\u65b0\u90fd\u590d\u4f4d\u6210\u5e38\u6001\u5e95\u8272\uff1a\u5361\u7247\u662f\u6c60\u5316\u7684\uff0c\u4e0a\u4e00\u8f6e\u53ef\u80fd\u6b63\u88ab\u60ac\u505c\r\n'
MUT_CARD_BG_RESET = (
    (
        _b('                    r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)') +
        _b('                    r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)') +
        _b('                    r:ClearAllPoints()')
    ),
    (
        _b('                    -- MUT: backdrop reset skipped') +
        _b('                    r:ClearAllPoints()')
    ),
)

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
    _WARM_TIP_BLOCK,
    b'    -- MUT: hidden tooltip fallback removed\r\n')

MUT_LOAD_LISTENER = (
    (
        _b('    DG.EnsureItemListener()') +
        _b('    if C_Item and C_Item.RequestLoadItemDataByID then')
    ),
    (
        _b('    -- MUT: ensure-listener call removed') +
        _b('    if C_Item and C_Item.RequestLoadItemDataByID then')
    ),
)



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
    b'            f.__npc = q[16]\r\n',
    b'            f.__npc = nil -- MUT: start line dead\r\n')

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
# 2026-09-28 收获 API 取数段新增了第二个调用点（奖励晚到重渲染，8 空格缩进在 if 内，
# 子串仍会命中单行锚）→ 连上一行 SetVerticalScroll 钉死在渲染尾部这一处。
MUT_NO_QDET = (
    b'    U.dungeonQuestScroll:SetVerticalScroll(0)\r\n    U:RenderQuestDetail()\r\n',
    b'    U.dungeonQuestScroll:SetVerticalScroll(0)\r\n    -- MUT: no quest detail linkage\r\n')

# 阵营档不自动勾当前角色阵营（永远全部）。
# 期望：静态「阵营档自动勾当前角色阵营」失败。
MUT_NO_SIDEAUTO = (
    b'        side = (ps and cnt[ps] > 0) and ps or "all"\r\n',
    b'        side = "all" -- MUT: no auto faction side\r\n')

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
    (
        _b('            r = CreateFrame("Button", nil, child, "BackdropTemplate")') +
        _b('            r:SetSize(DG.Q_LIST_W, DG.Q_ROW_H)')
    ),
    (
        _b('            r = CreateFrame("Frame", nil, child, "BackdropTemplate") -- MUT: row is Frame') +
        _b('            r:SetSize(DG.Q_LIST_W, DG.Q_ROW_H)')
    ),
)

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

# 详情页收获节没了（经验/金钱/声望 q[18]，API 优先 / 表内兜底）。期望：静态失败。
# 2026-09-28 收获块重写为 DG.GainsSegs 统一取数口（API 优先、静态兜底在 GainsSegs 内），
# 旧的 `if g and (g.xp or ...)` 行没了 → 锚到新块的渲染判据行（全文件唯一）。
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

# 「任务需求」节不显示（需要提供的物品被藏掉）。2026-09-28 目标并入需求 →
# 节开关改由 hasChips 决定（目标 API 没给 + 兜底关时，hasChips=false 整节消失）。
MUT_NO_REQ_SECT = (
    b'        local hasChips = q[14] and #q[14] > 0\r\n',
    b'        local hasChips = false -- MUT: no required-items section\r\n')

# 奖励退回单列（右列又空一大截）。
MUT_CHIP_1COL = (
    b'        y = y - renderChips(rew, 2) * (DG.Q_DET_ICON + 8) - 2\r\n',
    b'        y = y - renderChips(rew, 1) * (DG.Q_DET_ICON + 8) - 2 -- MUT: single column\r\n')

# 左列行内职业徽记消失。
MUT_ROW_CLS_GONE = (
    b'                local clsChar = q[15] and DG.QClassChar(q[15]) or nil\r\n',
    b'                local clsChar = nil -- MUT: row class badge gone\r\n')

# 「下一步」进度标不出现（用户看不到做到哪了）。
MUT_NO_FRONTIER = (
    b'                    if frontier and pok and pst ~= "done" then\r\n',
    b'                    if false then -- MUT: no frontier marker\r\n')

# 悬停离开后选中态被冲掉（OnLeave 不按选中复位）。
MUT_SEL_LEAVE = (
    b'                if self.__q and self.__q[1] == U.dungeonQuestSel then\r\n',
    b'                if false then -- MUT: selection lost on leave\r\n')

# 选中行没有右缘金标条。
MUT_SELMARK_HIDE = (
    b'                    r.selMark:Show()\r\n',
    b'                    r.selMark:Hide() -- MUT: no selection mark\r\n')

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

# 左列单行重新拼上起始 NPC。期望：静态「只写接取地点」失败。
MUT_ROW_GIVER = (
    b'                local loc = q[6] or ""\r\n'
    b'                if loc == "" and q[8] then loc = L["\xe5\x89\xaf\xe6\x9c\xac\xe5\x86\x85"] end\r\n'
    b'                r.sub:SetText(loc)\r\n',
    b'                local loc = q[6] or ""\r\n'
    b'                if loc == "" and q[8] then loc = L["\xe5\x89\xaf\xe6\x9c\xac\xe5\x86\x85"] end\r\n'
    b'                if q[5] and q[5] ~= "" then loc = (loc ~= "" and (q[5] .. " \xc2\xb7 " .. loc) or q[5]) end -- MUT: giver back\r\n'
    b'                r.sub:SetText(loc)\r\n')

# 节点取件不复位常态色（实机首次渲染白卡，悬停才恢复）。
# 期望：静态「节点取件复位常态色」失败。
MUT_NODE_RESET = (
    b'        r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)\r\n'
    b'        r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)\r\n'
    b'        return r\r\n',
    b'        -- MUT: no node color reset\r\n'
    b'        return r\r\n')

# 阵营档退回「只看本阵营专属」（双阵营通用任务不再跟随显示）。期望：静态「阵营档含双阵营」失败。
MUT_SIDE_NO_NEUTRAL = (
    b'        if side == "all" or q[2] == side or not q[2] then\r\n'
    b'            local key = q[8] and 2 or 1\r\n',
    b'        if side == "all" or q[2] == side then -- MUT: no neutral\r\n'
    b'            local key = q[8] and 2 or 1\r\n')

# 右列详情名不再带 #任务ID。期望：静态「详情名带任务ID」失败。
MUT_NO_QID = (
    b'    if hasName then nm = nm .. format(" |cff9a9a9a#%d|r", q[1]) end\r\n'
    b'    name:SetText(nm)\r\n',
    b'    -- MUT: no quest id\r\n'
    b'    name:SetText(nm)\r\n')

# 板卡退回重叠几何（左板右缘 +8 与右板叠 8px）。期望：静态「板卡不重叠」失败。
MUT_PLATE_OVERLAP = (
    b'    plateR:SetPoint("TOPLEFT", detail, "TOPLEFT", DG.Q_LIST_W + DG.Q_DET_GAP - 2, -(DG.SCROLL_Y - 8))',
    b'    plateR:SetPoint("TOPLEFT", detail, "TOPLEFT", DG.Q_LIST_W + DG.Q_DET_GAP - 8, -(DG.SCROLL_Y - 8)) -- MUT: overlap')

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
    b'    elseif key == "Bis" and ns.LoadForeverPages then\r\n'
    b'        k = "Bis"\r\n'
    b'    elseif key == "Tier" and ns.LoadForeverPages then\r\n'
    b'        k = "Tier"\r\n'
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
    b'    if type(IsShiftKeyDown) ~= "function" or not IsShiftKeyDown() then return false end\r\n',
    b'    if type(IsShiftKeyDown) ~= "function" then return false end -- MUT: shift check gone\r\n')

MUT_CLICK_NO_FALLBACK = (
    b'    return "item:" .. tostring(id) .. ":0:0:0:0:0:0:0"\r\n',
    b'    return nil -- MUT: no item-string fallback\r\n')

MUT_CLICK_FRAME = (
    b'            r = CreateFrame("Button", nil, child, "BackdropTemplate")\r\n'
    b'            r:SetSize(cw, DG.LOOT_CARD_H)',
    b'            r = CreateFrame("Frame", nil, child, "BackdropTemplate") -- MUT: frame cannot click\r\n'
    b'            r:SetSize(cw, DG.LOOT_CARD_H)')

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
    b'    PD.listCard:ClearAllPoints()\n    PD.listCard:SetPoint("TOPLEFT", PD.page, "TOPLEFT",\n                         PD.RIGHT_X - PD.LIST_PAD, -(top - PD.LIST_PAD))\n    PD.listCard:SetPoint("BOTTOMRIGHT", PD.page, "BOTTOMRIGHT",\n                         -(PAGE_INSET - PD.LIST_PAD), bot - PD.LIST_PAD)\n',
    b'    PD.listCard:ClearAllPoints()\n    -- MUT: big card never positioned\n'))

MUT_PROF_ROW_CARD = ('Core/ProfessionUI.lua', (
    b'    r.__hlOn = false\n    PD.SetRowHover(r, false)\n',
    b'    r.__hlOn = false\n    r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG) -- MUT: row keeps its own card\n    r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE) -- MUT\n'))

MUT_PROF_TIER_NOCLR = ('Core/ProfessionUI.lua', (
    b'                       PD.TierText(r[8], r[9], r[10])),\n',
    b'                       tostring(r[8]) .. "/" .. tostring(r[9]) .. "/" .. tostring(r[10])), -- MUT: tier colour dropped\n'))

MUT_PROF_TIER_SAMECLR = ('Core/ProfessionUI.lua', (
    b'PD.TIER_HEX = { "|cffffd100", "|cff40d940", "|cff8c8c8c" }\n',
    b'PD.TIER_HEX = { "|cffffd100", "|cffffd100", "|cffffd100" } -- MUT: one colour for all three\n'))

MUT_PROF_LEGACY_LABEL = ('Core/ProfessionUI.lua', (
    b'    { key = "legacy",   text = L["\xe4\xbc\xa0\xe6\x89\xbf"] },\n',
    b'    { key = "legacy",   text = "Legacy" }, -- MUT: english label back\n'))

MUT_PROF_TOOL_FIXEDW = ('Core/ProfessionUI.lua', (
    b'            bt:SetSize(w, PD.TOOL_H)\n',
    b'            bt:SetSize(PD.TOOL_W, PD.TOOL_H) -- MUT: fixed width back\n'))

MUT_PROF_NEW_TAG_GONE = ('Core/ProfessionUI.lua', (
    b'    r.a:SetText((spec.text or "") .. (spec.is_new and L[" |cff40d940\xe6\x96\xb0|r"] or ""))\n',
    b'    r.a:SetText(spec.text or "") -- MUT: NEW tag dropped\n'))

MUT_PROF_READ_BACK = ('Core/ProfessionUI.lua', (
    b'    if s.drops and #s.drops > 0 then t[#t + 1] = format(L["\xe6\x8e\x89\xe8\x90\xbd %d \xe5\xa4\x84"], #s.drops) end\n',
    b'    if s.read then t[#t + 1] = format(L["\xe8\xaf\xbb\xe7\x89\xa9\xef\xbc\x9a%s"], tostring(s.read)) end -- MUT: read back\n    if s.drops and #s.drops > 0 then t[#t + 1] = format(L["\xe6\x8e\x89\xe8\x90\xbd %d \xe5\xa4\x84"], #s.drops) end\n'))

MUT_PROF_QUEST_BAREID = ('Core/ProfessionUI.lua', (
    b'                text = FitL(PD.QuestName(id)),\n',
    b'                text = tostring(id), -- MUT: bare quest id back\n'))

MUT_PROF_LEARN_BACK = ('Core/ProfessionUI.lua', (
    b'    if lv.rods and #lv.rods > 0 then\n',
    b'    if lv.learn and #lv.learn > 0 then -- MUT: spell id list back\n'))

MUT_PROF_CAMPING_CAMP_GONE = ('Core/ProfessionUI.lua', (
    b'    if slug == "camping" then out[#out + 1] = "camp" end\n',
    b'    -- MUT: camping camp tab gone\n'))

MUT_PROF_CAMPVIEW_STICKY = ('Core/ProfessionUI.lua', (
    b'        PD.campView = "a"\n',
    b'        -- MUT: camp view sticky across professions\n'))

MUT_PROF_ROW_NARROW = ('Core/ProfessionUI.lua', (
    b'                    x, w = PD.LIST_PAD, ROW_W\n',
    b'                    x, w = PD.LIST_PAD, PD.COL_LW -- MUT: single-col pages narrowed\n'))

MUT_PROF_STEP_SKILL = ('Core/ProfessionUI.lua', (
    b'                rng = format(L["%s \xe2\x80\x93 %s"], tostring(st[1]), tostring(st[2])),\n',
    b'                rng = format(L["\xe6\x8a\x80\xe8\x83\xbd %s \xe2\x86\x92 %s"], tostring(st[1]), tostring(st[2])), -- MUT: skill prefix back\n'))

MUT_PROF_SHOP_RIGHT_GONE = ('Core/ProfessionUI.lua', (
    b'        PushHead(rows, L["\xe8\xa6\x81\xe5\x87\x86\xe5\xa4\x87\xe7\x9a\x84\xe6\x9d\x90\xe6\x96\x99"], 2)\n',
    b'        PushHead(rows, L["\xe8\xa6\x81\xe5\x87\x86\xe5\xa4\x87\xe7\x9a\x84\xe6\x9d\x90\xe6\x96\x99"], 1) -- MUT: shopping list back to left\n'))

MUT_PROF_STEP_NOCNT = ('Core/ProfessionUI.lua', (
    b'        r.c:SetText(spec.cnt or "")\n',
    b'        r.c:SetText("") -- MUT: craft count dropped\n'))

MUT_PROF_BONUS_LABEL = ('Core/ProfessionUI.lua', (
    b'                bt:SetText(L["\xe8\x81\x8c\xe4\xb8\x9a\xe5\x8a\xa0\xe6\x88\x90"])\n',
    b'                bt:SetText(L["\xe5\x8a\xa0\xe6\x88\x90"]) -- MUT: label back\n'))

MUT_PROF_MATICON_GONE = ('Core/ProfessionUI.lua', (
    b'        t[#t + 1] = format("%d\xc3\x97%s%s", m[2] or 1, PD.MatIconTex(m[1]), DG.ItemName(m[1]))\n',
    b'        t[#t + 1] = format("%d\xc3\x97%s", m[2] or 1, DG.ItemName(m[1])) -- MUT: mat icon dropped\n'))

MUT_PROF_DETAIL_BACK = ('Core/ProfessionUI.lua', (
    b'    PD.BuildIndexGrid(child)\n',
    b'    PD.BuildIndexGrid(child)\n    PD.detail = CreateFrame("Frame", nil, page) -- MUT: detail back\n'))

MUT_PROF_MATCOL_BACK = ('Core/ProfessionUI.lua', (
    b'        sub = tostring(r[5] or ""),\n        mats = PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W),\n',
    b'        sub = table.concat({ tostring(r[5] or ""), PD.MatText(r[12], 4) }, "   "), -- MUT: mats back into sub\n        mats = "",\n'))

MUT_PROF_COL_RATIO_FLAT = ('Core/ProfessionUI.lua', (
    b'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)\n',
    b'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * 0.50) -- MUT: columns evened out\n'))

MUT_PROF_MAT_FS_WIRING = ('Core/ProfessionUI.lua', (
    b'    r.f = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")\n',
    b'    r.f = MakeFS(r, 11, C_TEXT, "LEFT") -- MUT: font size bypassed\n'))

MUT_PROF_LVSPLIT_GONE = ('Core/ProfessionUI.lua', (
    b'        PD.lvSplit = true\n',
    b'        PD.lvSplit = false -- MUT: split line not raised\n'))

MUT_PROF_CNT_AGAIN_MATS = ('Core/ProfessionUI.lua', (
    b'        r.c:SetPoint("RIGHT", r, "RIGHT", -PD.LV_CNT_R, 0)\n',
    b'        r.c:SetPoint("RIGHT", r, "RIGHT", -140, 0) -- MUT: count off the column edge\n'))

MUT_PROF_DIV_FAINT = ('Core/ProfessionUI.lua', (
    b'    divider:SetColorTexture(1, 1, 1, 0.12)\n',
    b'    divider:SetColorTexture(1, 1, 1, 0.02) -- MUT: split line invisible\n'))

MUT_PROF_LV_STEP_MATS_GONE = ('Core/ProfessionUI.lua', (
    b'        PD.PaintMats(r, spec.blocks, spec.matCut, spec.passed)\n',
    b'        -- MUT: per-step mats dropped again\n'))

# ㉒-新增 已过段落灰显（2026-09-29 用户定：制皮 42 → 「1 – 15」整段灰、图标也灰）
MUT_LV_PASSED_OFF = ('Core/ProfessionUI.lua', (
    b"            local passed = (greyOn and over) or nil\n",
    b"            local passed = nil -- MUT: passed grey disabled\n"))

MUT_LV_PASSED_NOICON = ('Core/ProfessionUI.lua', (
    b"        r.icon:SetDesaturated(spec.passed and true or false)\n",
    b"        r.icon:SetDesaturated(false) -- MUT: icon desaturate dropped\n"))

# ㉔ 专业页设置 + 当前段落外框（2026-09-29 用户定）
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

MUT_PROF_SET_TOG_GONE = ('Core/ProfessionUI.lua', (
    b"            tg.__key = spec.togKey\n",
    b"            do end -- MUT: toggle unbound\n"))

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
    b'    local avail = PD.COL_LW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP\n',
    b'    local avail = PD.COL_LW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - 20 -- MUT: name-to-mats gap fattened to 20\n'))

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
    b'        r.b:SetText(spec.src or "")\n',
    b'        r.b:SetText("") -- MUT: source line dropped\n'))

MUT_PROF_LV_TBL_SRC_SAMEY = ('Core/ProfessionUI.lua', (
    b'        r.b:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_SRC_DY)\n',
    b'        r.b:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY) -- MUT: two lines collapsed\n'))

MUT_PROF_LV_TBL_NO_MARK_ROOM = ('Core/ProfessionUI.lua', (
    b'        if total + step + PD.TBL_MARK_W > budget then\n',
    b'        if total + step > budget then -- MUT: no room kept for the ellipsis\n'))

MUT_PROF_LV_TBL_GROUP_LEFT = ('Core/ProfessionUI.lua', (
    b'    local right = PD.COL_LW - PD.TBL_MAT_RPAD',
    b'    local right = PD.TBL_MAT_RPAD -- MUT: material group not right-aligned'))

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
    b'        if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end\r\n',
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

MUT_GUIDE_TAB_GONE = (
    b', { key = "guide", text = L["\xe6\x94\xbb\xe7\x95\xa5"] } }',
    b' }')

MUT_GUIDE_DISPATCH_LOOT = (
    b'        U:RenderDungeonGuide()\r\n',
    b'        U:RenderDungeonLoot() -- MUT: guide tab renders loot\r\n')

MUT_GUIDE_KEEP_SCROLL = (
    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide) end\r\n',
    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest) end -- MUT\r\n')

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

MUTATIONS = [
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
    ('提示框：原生分支不再优先 SetItemByID', MUT_TIP_NO_BYID),
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
    ('选中行没有右缘金标条', MUT_SELMARK_HIDE),
    ('奖励色单变量接 QColor（实机 Unpack 崩）', MUT_QC_SINGLE),
    ('底板卡不随页签显隐', MUT_NO_PLATE),
    ('左列单行拼回起始 NPC', MUT_ROW_GIVER),
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
    ('专业页：行又各自成卡（一张大卡的意义没了）', MUT_PROF_ROW_CARD),
    ('专业页：阈值数字不再染色（退回纯数字）', MUT_PROF_TIER_NOCLR),
    ('专业页：阈值三个数字同色（等于没染）', MUT_PROF_TIER_SAMECLR),
    ('专业页：第 6 颗子页签退回英文 Legacy', MUT_PROF_LEGACY_LABEL),
    ('专业页：分类按钮退回定宽 72（长名被裁）', MUT_PROF_TOOL_FIXEDW),

    # ⑰ 专业页三轮补丁（2026-09-23 傍晚，用户逐条）
    ('专业页：新配方的绿色「新」字被摘', MUT_PROF_NEW_TAG_GONE),
    ('专业页：来源行又亮出「读物：子站名」', MUT_PROF_READ_BACK),
    ('专业页：关联任务退回裸 ID（任务名被摘）', MUT_PROF_QUEST_BAREID),
    ('专业页：要学的法术 ID 列表长回来', MUT_PROF_LEARN_BACK),
    ('专业页：营地页进不了对照（页签被摘）', MUT_PROF_CAMPING_CAMP_GONE),
    ('专业页：换专业不复位营地视图', MUT_PROF_CAMPVIEW_STICKY),

    # ⑱ 升级页通栏改版 + 职业加成签名（2026-09-23 晚）
    ('专业页：单列页行宽被压窄（col=1 恒收 COL_LW）', MUT_PROF_ROW_NARROW),
    ('专业页：分段行写回「技能」前缀', MUT_PROF_STEP_SKILL),
    ('专业页：右栏备料清单跑回左栏', MUT_PROF_SHOP_RIGHT_GONE),
    ('专业页：分段行次制作被摘', MUT_PROF_STEP_NOCNT),
    ('专业页：营地第三视图退回单字加成', MUT_PROF_BONUS_LABEL),

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
    # ㉒-新增 已过段落灰显（2026-09-29 用户定）
    ('专业页：已过段落灰显被关掉（passed 恒 nil）', MUT_LV_PASSED_OFF),
    ('专业页：已过段落图标不再去饱和', MUT_LV_PASSED_NOICON),
    ('专业页：区间列宽写死（三位数区间压名称）', MUT_PROF_LVNAME_FIXED),
    # ㉔ 专业页设置 + 当前段落外框（2026-09-29 用户定）
    ('专业页：灰显开关默认值被翻成关', MUT_PROF_SET_GREY_DEF),
    ('专业页：当前段不再被标记（外框永不亮）', MUT_PROF_SET_CUR_GONE),
    ('专业页：外框上边条永不显示（框缺一条）', MUT_PROF_SET_BORDER_GONE),
    ('专业页：设置页不可达（齿轮点了没反应）', MUT_PROF_SET_PAGE_GONE),
    ('专业页：iOS 开关不再绑定设置键（点了也写不进 DB）', MUT_PROF_SET_TOG_GONE),

    # ㉓ 悬停高亮划走不灭 + 商人兑换译名（2026-09-24 四轮）
    ('专业页：划走后行又回到常态淡框（用户报的常亮复活）', MUT_PROF_HL_LEAVE_BG),
    ('专业页：悬停状态不再定时与鼠标对齐（滚轮后那一行常亮）', MUT_PROF_HL_NOSYNC),
    ('专业页：同步只灭不亮（鼠标在行上时高亮被熄掉）', MUT_PROF_HL_ALWAYSOFF),
    ('专业页：商人兑换货币退回旧译名「恩惠」', MUT_PROF_FAVOR_LABEL),

    # ㉔ 升级页四列宽度全给材料（2026-09-24 布局四轮）
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
    ('专业页：来源那一行不写了', MUT_PROF_LV_TBL_SRC_GONE),
    ('专业页：两行塌回一行（来源与配方名同一 y）', MUT_PROF_LV_TBL_SRC_SAMEY),
    ('专业页：材料块不再给省略号留那一格', MUT_PROF_LV_TBL_NO_MARK_ROOM),
    ('专业页：材料组不再右对齐（左起摆）', MUT_PROF_LV_TBL_GROUP_LEFT),
    ('专业页：材料块数量角标归零（块失去 ×N）', MUT_PROF_LV_TBL_CNT_ZERO),

    # ㉗ 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）
    ('前导链备注：备注行不再渲染', MUT_QPRENOTE_OFF),
    ('前导链备注：备注挂到了别的任务上（界面读不到）', MUT_QPRENOTE_WRONGKEY),
]


# ---------------------------------------------------------------------------
# 注释精简配套（2026-09-29）
#   产物里的注释已统一清到「只留文件头」（见 _temp/strip_comments.py）。变异锚点里
#   那些**夹着注释**的老片段因此整段命中 0 次 —— 而锚点烂掉是静默的（变异被跳过 =
#   这条断言已经没人守）。故此处让锚点自动跟随：整行注释删掉、行尾注释剥掉。
#   对本来就不含注释的片段是恒等变换，176 条一起过。
# ---------------------------------------------------------------------------
def _strip_cmt(seg):
    """按行剥注释：整行注释丢弃，行尾注释截断（字符串里的 -- 不算）。"""
    if b'--' not in seg:
        return seg
    crlf = b'\r\n' in seg
    out = []
    for ln in seg.decode('utf-8').replace('\r\n', '\n').split('\n'):
        cut = None
        i, n = 0, len(ln)
        while i < n:
            c = ln[i]
            if c == '-' and i + 1 < n and ln[i + 1] == '-':
                cut = i
                break
            if c == '"' or c == "'":
                j = i + 1
                while j < n:
                    if ln[j] == '\\':
                        j += 2
                        continue
                    if ln[j] == c:
                        j += 1
                        break
                    j += 1
                i = j
                continue
            i += 1
        if cut is None:
            out.append(ln)
        else:
            pre = ln[:cut].rstrip()
            if pre:
                out.append(pre)
    res = '\n'.join(out)
    if crlf:
        res = res.replace('\n', '\r\n')
    return res.encode('utf-8')


def _norm_spec(sp):
    if len(sp) == 2 and isinstance(sp[0], str):
        return (sp[0], (_strip_cmt(sp[1][0]), sp[1][1]))
    return (_strip_cmt(sp[0]), sp[1])


MUTATIONS = [(nm, _norm_spec(sp)) for nm, sp in MUTATIONS]


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
    # 先在内存里把所有锚点校验/替换完，再统一落盘 ——
    # 中途报错不会留下「半边带变异」的 beta（踩过一次）
    payloads = {}
    for fname, items in files.items():
        p = os.path.join(BETA, *fname.split('/'))
        data = open(p, 'rb').read()
        for name, old, new in items:
            if data.count(old) != 1:
                print('!! 锚点不唯一/不存在（%d 次）: %s' % (data.count(old), name))
                return 2
            data = data.replace(old, new)
            print('已注入变异：%s  [%s]' % (name, fname))
        payloads[fname] = data
    for fname, data in payloads.items():
        p = os.path.join(BETA, *fname.split('/'))
        open(p, 'wb').write(data)
        bare = data.count(b'\n') - data.count(b'\r\n')
        print('  %s 注入后 CRLF = %d / 裸 LF = %d' % (fname, data.count(b'\r\n'), bare))
    try:
        r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        out = (r.stdout or '') + (r.stderr or '')
        print(out[-2600:])
        nfail = out.count('[FAIL]') + out.count('✗')
        print('=' * 60)
        print('变异后 FAIL 行数 = %d' % nfail)
        if r.returncode != 0 and nfail > 0:
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

# -*- coding: utf-8 -*-



"""从上游 mut_dungeon_check.py 派生 DungeonsForever 的变异验证。







改动面：



  ① 路径：TITAN / BETA 指向本插件



  ② 默认变异目标文件：Core/UI.lua → Core/DungeonUI.lua



  ③ 跑的是本插件的 harness：tf_dungeon_check.py → df_dungeon_check.py



  ④ 删除 2 条依赖 Core/Sim.lua 的变异（本插件没有模拟器模块）：



       MUT_COMPARE_GONE（/tf item 无参对比模式）



       MUT_QUAL_PREWARM（/tf qual 预热）



     连带删掉它们的 MUTATIONS 条目。







用法：python mk_df_mut.py → 生成 df_mut_check.py



"""



import os



import sys







HERE = os.path.dirname(os.path.abspath(__file__))



DF = os.path.dirname(HERE)



SRC = os.path.join(os.path.dirname(DF), 'TalentsForever', '_temp', 'mut_dungeon_check.py')



DST = os.path.join(HERE, 'df_mut_check.py')







text = open(SRC, encoding='utf-8').read()











def cut(start, end, label):



    """删掉 [start, end] 闭区间（含 end），返回新文本"""



    global text



    if start not in text:



        sys.exit('删除锚点(起)未命中：%s' % label)



    i = text.index(start)



    j = text.index(end, i)



    text = text[:i] + text[j + len(end):]



    print('  已删除：%s' % label)











# ── ④ 删除依赖 Core/Sim.lua 的变异定义 ───────────────────────────────────────



cut('# Sim.lua（LF）：无参 /tf item 不再走对比模式。期望：「/tf item 无参走对比模式」静态失败。\n',



    "      b'        Print(\"MUT: no compare probe\")\\n        return\\n')))",



    'MUT_COMPARE_GONE 定义')







cut('MUT_QUAL_PREWARM = (\n',



    "    b'                -- MUT: qual audit does not prewarm\\n')",



    'MUT_QUAL_PREWARM 定义')







# ── ④ 连带删除 MUTATIONS 条目 ────────────────────────────────────────────────



cut("    ('名字可见：/tf item 无参不再走对比模式', MUT_COMPARE_GONE),\n",



    "    ('名字可见：/tf item 无参不再走对比模式', MUT_COMPARE_GONE),\n",



    'MUT_COMPARE_GONE 登记')







cut("    ('加载：/tf qual 不预热（懒加载下一片 nil）',\n",



    "     ('Core/Sim.lua', MUT_QUAL_PREWARM)),\n",



    'MUT_QUAL_PREWARM 登记')







# ── ④ 连带删除文档头里的条目说明 ─────────────────────────────────────────────



cut('  · MUT_COMPARE_GONE    /tf item 无参不走对比模式\n',



    '  · MUT_COMPARE_GONE    /tf item 无参不走对比模式\n',



    '文档头 MUT_COMPARE_GONE 说明')







# ── ①②③ 路径与文件名 ────────────────────────────────────────────────────────



REPL = [



    (r"D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\TalentsForever",



     r"D:\workspace\DungeonsForever"),



    (r"D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\TalentsForever",



     r"D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever"),



    ("'Core/UI.lua'", "'Core/DungeonUI.lua'"),



    ("默认打 Core/UI.lua；('Core/Sim.lua', (old, new)) 指定文件。",



     "默认打 Core/DungeonUI.lua；('Core/Xxx.lua', (old, new)) 可指定其它文件。"),



    ("# 变异可跨文件（RequestItem 在 UI.lua，QualAudit 在 Sim.lua）",



     "# 变异可跨文件（本插件的副本页代码全部落在 Core/DungeonUI.lua）"),



    ('tf_dungeon_check.py', 'df_dungeon_check.py'),



    ('"""副本页 harness 的变异验证（证明断言非恒真）。',



     '"""副本页 harness 的变异验证（证明断言非恒真）· 无限副本手册。'),



    ('跑完自动用 titan 端（干净）覆盖 beta 还原。',



     '跑完自动用 titan 端（干净）覆盖 beta 还原；跑之前先 sync_beta.py --apply。'),



]



for old, new in REPL:



    n = text.count(old)



    if not n:



        sys.exit('替换未命中：%s' % old)



    text = text.replace(old, new)



    print('  %-40s → %d 处' % (old[:40], n))







# ── ⑤ 补一条「跨插件命名空间」变异（2026-09-23 实机事故）──────────────────────



# 事故链：副本段从上游界面层抄来了两个**裸全局函数** BuildDungeons /



#   BuildDungeonOverview，上游同名文件也定义这两个全局。WoW 按文件夹名字母序加载



#   （DungeonsForever 先、上游插件后）→ 上游静默覆盖本插件；于是本插件 U:SwitchSub



#   里的 `BuildDungeons()` 跑的是上游函数体，而上游函数用的是**上游的文件级 local U**



#   （U.dungeonPage 为 nil）→ MakeFS(nil) → 实机报错落在上游界面层。



# 为什么必须钉：离线 harness 只加载本插件，**永远测不出**「被后加载的同名插件覆盖」——



#   本次 9 轮本地回归全绿，实机点图标必崩。



# 这条变异把它退回裸全局，用来证明新加的静态断言不是恒真白测。



MUT_ANCHOR = "    ('地图标记：NPC 金名退回灰字（可点暗示丢失）', MUT_NPC_GOLD_GONE),\n]\n"



if MUT_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 尾部锚点，上游可能已改动')



text = text.replace(



    MUT_ANCHOR,



    "    ('地图标记：NPC 金名退回灰字（可点暗示丢失）', MUT_NPC_GOLD_GONE),\n"



    "\n"



    "    # ⑩ 跨插件命名空间（2026-09-23 实机事故）\n"



    "    ('命名空间：页面构建函数退回裸全局（会被后加载的同名插件覆盖）', MUT_BARE_GLOBAL),\n"



    "]\n",



    1)



print('  %-40s → %d 处' % ('MUTATIONS 尾部追加 MUT_BARE_GLOBAL', 1))







MUT_DEF_ANCHOR = "MUTATIONS = [\n"



if MUT_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处，上游可能已改动')



text = text.replace(



    MUT_DEF_ANCHOR,



    "# ── 跨插件命名空间（2026-09-23 实机事故） ──────────────────────────────────\n"



    "# 页面构建函数脱掉 DG. 前缀退回**裸全局**：WoW 按文件夹名字母序加载，\n"



    "# DungeonsForever 先、上游插件后 → 上游同名全局静默覆盖本插件，\n"



    "# U:SwitchSub 里那句调用于是跑的是上游函数体（上游 U.dungeonPage 为 nil）\n"



    "# → MakeFS(nil) → 实机 attempt to index local 'parent' (a nil value)。\n"



    "# 期望：静态「界面层不定义裸全局函数」+「挂在 local 表 DG 上」双双失败。\n"



    "# 注意：变异是 bytes，注释只能英文。\n"



    "MUT_BARE_GLOBAL = (\n"



    "    b'function DG.BuildDungeons()\\r\\n',\n"



    "    b'function BuildDungeons() -- MUT: bare global (cross-addon clash)\\r\\n')\n"



    "\n"



    "MUTATIONS = [\n",



    1)



print('  %-40s → %d 处' % ('MUT_BARE_GLOBAL 定义', 1))







# ── ⑥ 5 条「顶栏胶囊」变异（2026-09-23 用户要求：副本→5人本、右加团本、整体上移15）──



# 变异是 bytes，注释只能英文（中文字面量会被当成字节、破坏锚点匹配）。



# 每条都配了一条静态/动态断言；已逐条隔离跑过，确认不是脏抓。



_CAP_MUT_DEFS = (



    "MUT_CAPSULE_NO_LIFT = (\n"



    "    b'    host:SetPoint(\"TOP\", U.panel, \"TOP\", 0, DG.CAPSULE_LIFT - ROW_SUB)\\r\\n',\n"



    "    b'    host:SetPoint(\"TOP\", U.panel, \"TOP\", 0, -ROW_SUB) -- MUT: capsule lift gone\\r\\n')\n"



    "\n"



    "MUT_RAID_TAB_GONE = (\n"



    "    b'        { key = \"Raids\",    text = L[\"\\xe5\\x9b\\xa2\\xe6\\x9c\\xac\"],  width = DG.CAPSULE_W },\\r\\n',\n"



    "    b'        -- MUT: raid tab removed\\r\\n')\n"



    "\n"



    # ★ 2026-09-23 第二次修订：SwitchSub 从「两颗 / 二分流」长成「三颗 / 三分流」



    #   （多了专业页那一支），旧锚点 `local k = (key == \"Raids\") and ...` 已经不存在。



    #   锚点烂掉是**静默**的：`df_check_new_muts.py` 只在跑到它时才报「锚点 0 次」，



    #   不跑 --all 就永远发现不了。故新增 `check_mut_anchors.py` 做全量预检（见该脚本）。



    "MUT_SWITCH_IGNORES_KEY = (\n"



    "    b'    local k = \"Dungeons\"\\r\\n'\n"



    "    b'    if key == \"Raids\" then\\r\\n'\n"



    "    b'        k = \"Raids\"\\r\\n'\n"



    "    b'    elseif key == \"Professions\" and ns.LoadForeverPages then\\r\\n'\n"



    "    b'        k = \"Professions\"\\r\\n'\n"



    "    b'    elseif key == \"Explore\" and ns.LoadForeverPages then\\r\\n'\n"



    "    b'        k = \"Explore\"\\r\\n'\n"



    "    b'    elseif key == \"Collections\" and ns.LoadForeverPages then\\r\\n'\n"



    "    b'        k = \"Collections\"\\r\\n'\n"



    "    b'    elseif key == \"Bis\" and ns.LoadForeverPages then\\r\\n'\n"



    "    b'        k = \"Bis\"\\r\\n'\n"



    "    b'    elseif key == \"Tier\" and ns.LoadForeverPages then\\r\\n'\n"



    "    b'        k = \"Tier\"\\r\\n'\n"



    "    b'    elseif key == \"PvP\" and ns.LoadForeverPages then\\r\\n'\n"



    "    b'        k = \"PvP\"\\r\\n'\n"



    "    b'    end\\r\\n',\n"



    "    b'    local k = \"Dungeons\" -- MUT: switch key ignored (always 5-man)\\r\\n')\n"



    "\n"



    "MUT_RAID_SHOW_BOTH = (\n"



    "    b'    if U.dungeonPage then U.dungeonPage:SetShown(isDun) end\\r\\n',\n"



    "    b'    if U.dungeonPage then U.dungeonPage:SetShown(true) end -- MUT: both pages shown\\r\\n')\n"



    "\n"



    "MUT_UAS_NO_SKIP = (\n"



    "    b'    if self.curSub == \"Raids\" then return end\\r\\n',\n"



    "    b'    -- MUT: no raid skip\\r\\n')\n"



    "\n"



)



_CAP_DEF_ANCHOR = "MUTATIONS = [\n"



if _CAP_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处，上游可能已改动')



text = text.replace(_CAP_DEF_ANCHOR, _CAP_MUT_DEFS + _CAP_DEF_ANCHOR, 1)



print('  %-40s → %d 处' % ('胶囊变异定义 5 条', 1))







_CAP_REG_ANCHOR = (



    "    ('命名空间：页面构建函数退回裸全局（会被后加载的同名插件覆盖）', MUT_BARE_GLOBAL),\n"



    "]\n"



)



if _CAP_REG_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 尾部锚点，上游或第⑤步可能已改动')



text = text.replace(



    _CAP_REG_ANCHOR,



    "    ('命名空间：页面构建函数退回裸全局（会被后加载的同名插件覆盖）', MUT_BARE_GLOBAL),\n"



    "\n"



    "    # ⑪ 顶栏胶囊：5人本 / 团本 + 上移 15（用户 2026-09-23）\n"



    "    ('胶囊：上移量被改回 -ROW_SUB（没上移）', MUT_CAPSULE_NO_LIFT),\n"



    "    ('胶囊：团本那颗入口消失（退回单页签）', MUT_RAID_TAB_GONE),\n"



    "    ('胶囊：SwitchSub 又把 key 丢掉（永远只显示 5人本）', MUT_SWITCH_IGNORES_KEY),\n"



    "    ('胶囊：切团本时副本页不隐藏（两页同时显示）', MUT_RAID_SHOW_BOTH),\n"



    "    ('胶囊：UpdateActiveSub 在团本态也刷新（空态页误刷副本页）', MUT_UAS_NO_SKIP),\n"



    "]\n",



    1)



print('  %-40s → %d 处' % ('胶囊变异登记 5 条', 1))







# ── ⑦ 2 条「上游数据同步」变异（2026-09-23：NPCLoc 176->237 / QuestPreNpcID 9->218）──



# 目标文件是数据层 Core/Data/Data_NPCLoc.lua（LF），所以字节锚点用 \n 而非 \r\n。



# 清空表 = 模拟「同步回了旧数据」这一真实事故形态（本项目踩过：上游重跑生成器，



# 本插件数据静默变旧）。变异是 bytes，注释只能英文。



_SYNC_MUT_DEFS = (



    "MUT_NPCLOC_EMPTY = ('Core/Data/Data_NPCLoc.lua', (\n"



    "    b'ns.NPCLoc = {\\n',\n"



    "    b'ns.NPCLoc = { } -- MUT: npc loc emptied\\nns._npc_dead = {\\n'))\n"



    "\n"



    "MUT_PRE_NPCID_EMPTY = ('Core/Data/Data_NPCLoc.lua', (\n"



    "    b'ns.QuestPreNpcID = {\\n',\n"



    "    b'ns.QuestPreNpcID = { } -- MUT: pre-npcid map emptied\\nns._qpn_dead = {\\n'))\n"



    "\n"



)



_SYNC_DEF_ANCHOR = "MUTATIONS = [\n"



if _SYNC_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑦步），上游可能已改动')



if 'MUT_NPCLOC_EMPTY' in text:



    sys.exit('数据同步变异已存在，不再重复登记（幂等保护）')



text = text.replace(_SYNC_DEF_ANCHOR, _SYNC_MUT_DEFS + _SYNC_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('数据同步变异定义 2 条', 1))







_SYNC_REG_ANCHOR = (



    "    ('胶囊：UpdateActiveSub 在团本态也刷新（空态页误刷副本页）', MUT_UAS_NO_SKIP),\n"



    "]\n"



)



if _SYNC_REG_ANCHOR not in text:



    sys.exit('未找到胶囊变异登记尾部锚点（第⑦步），上游或第⑥步可能已改动')



text = text.replace(



    _SYNC_REG_ANCHOR,



    "    ('胶囊：UpdateActiveSub 在团本态也刷新（空态页误刷副本页）', MUT_UAS_NO_SKIP),\n"



    "\n"



    "    # ⑫ 上游数据同步下限守护（2026-09-23 NPCLoc 176->237 / QuestPreNpcID 9->218）\n"



    "    ('同步：NPCLoc 表被清空（数据退回旧版）', MUT_NPCLOC_EMPTY),\n"



    "    ('同步：QuestPreNpcID 表被清空（表外链落旗失效）', MUT_PRE_NPCID_EMPTY),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('数据同步变异登记 2 条', 1))







# ── ⑫-b 暴风城坐标口径变异（2026-09-24）──────────────────────────────────────



# 目标文件同上（LF）。形态 = 把校正后的 5413 改回经典边界口径，等价于「sync_data 漏施加



# NPCLOC_COORD_FIX / 上游数据又覆盖回来」这一真实事故。锚点收窄到不含地图名，避免



# 生成器里出现非 ASCII 的 bytes 字面量（Python 3 的 b'...' 不允许直接写中文）。



# 该变异只能被「暴风城坐标已校正」那条断言抓住：其余地图标记用例都是拿表比自己比，



# 坐标整体退回也不会红。



_SW_MUT_DEFS = (



    "MUT_SW_COORD_STALE = ('Core/Data/Data_NPCLoc.lua', (\n"



    "    b'    [5413] = { 1453, 64.6, 37.2,',\n"



    "    b'    [5413] = { 1453, 57.4, 16.0,'))\n"



    "\n"



)



if 'MUT_SW_COORD_STALE' in text:



    sys.exit('暴风城坐标变异已存在，不再重复登记（幂等保护）')



text = text.replace(_SYNC_DEF_ANCHOR, _SW_MUT_DEFS + _SYNC_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('暴风城坐标变异定义 1 条', 1))







_SW_REG_ANCHOR = "MUTATIONS = [\n"



if text.count(_SW_REG_ANCHOR) != 1:



    sys.exit('未找到 MUTATIONS 列表头锚点（⑫-b），上游可能已改动')



# ⚠️ 这条登记故意挂在 MUTATIONS 列表**头部**：本步在 ⑬ 步之前执行，若按惯例追加到



#    列表尾部会吃掉 ⑬ 步的锚点（`...MUT_PRE_NPCID_EMPTY),\n]\n`）→ ⑬ 找不到插入位置。



text = text.replace(



    _SW_REG_ANCHOR,



    _SW_REG_ANCHOR



    + "    # ⑫-b 暴风城坐标口径守护（2026-09-24 暴风城地图按新生代边界重画）\n"



    + "    ('同步：暴风城坐标退回经典边界口径（点图落错位置）', MUT_SW_COORD_STALE),\n",



    1)



print('  %-40s -> %d 处' % ('暴风城坐标变异登记 1 条', 1))







# ── ⑬ 物品卡 Shift+点击 → 聊天框（2026-09-23 用户要求）────────────────────────



# 用户原话：「物品需要支持 Shift 点击，然后能发送到聊天输入框」。



# 5 条变异，每条对应 harness 里一条静态/动态断言。变异是 bytes，注释只能英文。



# ⚠️ MUT_CLICK_FRAME 属「桩测不出」那一类：桩不区分帧类型（SetScript 一样记账），



#    所以只有静态断言抓得住 —— 而实机上 Frame 挂 OnClick 是直接



#    "script type not supported"（任务行踩过）。这正是必须留静态断言的原因。



_CLICK_MUT_DEFS = (



    "MUT_CLICK_NO_SHIFT = (\n"



    "    b'    if type(IsShiftKeyDown) ~= \"function\" or not IsShiftKeyDown() then return false end\\r\\n',\n"



    "    b'    if type(IsShiftKeyDown) ~= \"function\" then return false end -- MUT: shift check gone\\r\\n')\n"



    "\n"



    "MUT_CLICK_NO_FALLBACK = (\n"



    "    b'    return \"item:\" .. tostring(id) .. \":0:0:0:0:0:0:0\"\\r\\n',\n"



    "    b'    return nil -- MUT: no item-string fallback\\r\\n')\n"



    "\n"



    "MUT_CLICK_FRAME = (\n"



    "    b'            r = CreateFrame(\"Button\", nil, child, \"BackdropTemplate\")\\r\\n'\n"



    "    b'            r:SetSize(cw, DG.LOOT_CARD_H)',\n"



    "    b'            r = CreateFrame(\"Frame\", nil, child, \"BackdropTemplate\") -- MUT: frame cannot click\\r\\n'\n"



    "    b'            r:SetSize(cw, DG.LOOT_CARD_H)')\n"



    "\n"



    "MUT_CLICK_NO_OPENCHAT = (\n"



    "    b'    if type(ChatFrame_OpenChat) == \"function\" then\\r\\n'\n"



    "    b'        ChatFrame_OpenChat(link)\\r\\n'\n"



    "    b'        return true\\r\\n'\n"



    "    b'    end\\r\\n',\n"



    "    b'    if false then -- MUT: no open-chat path\\r\\n'\n"



    "    b'    end\\r\\n')\n"



    "\n"



    "MUT_CLICK_ANY_BUTTON = (\n"



    "    b'    if button ~= \"LeftButton\" then return false end\\r\\n',\n"



    "    b'    if false then return false end -- MUT: any button accepted\\r\\n')\n"



    "\n"



)



_CLICK_DEF_ANCHOR = "MUTATIONS = [\n"



if _CLICK_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑬步），上游可能已改动')



if 'MUT_CLICK_NO_SHIFT' in text:



    sys.exit('物品卡 Shift 点击变异已存在，不再重复登记（幂等保护）')



text = text.replace(_CLICK_DEF_ANCHOR, _CLICK_MUT_DEFS + _CLICK_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('物品卡 Shift 点击变异定义 5 条', 1))







_CLICK_REG_ANCHOR = (



    "    ('同步：QuestPreNpcID 表被清空（表外链落旗失效）', MUT_PRE_NPCID_EMPTY),\n"



    "]\n"



)



if _CLICK_REG_ANCHOR not in text:



    sys.exit('未找到数据同步变异登记尾部锚点（第⑬步），上游或第⑦步可能已改动')



text = text.replace(



    _CLICK_REG_ANCHOR,



    "    ('同步：QuestPreNpcID 表被清空（表外链落旗失效）', MUT_PRE_NPCID_EMPTY),\n"



    "\n"



    "    # ⑬ 物品卡 Shift+点击 → 聊天框（用户 2026-09-23 要求）\n"



    "    ('Shift 点击：拿到 Shift 了，但不再看 Shift（随手一点就发）', MUT_CLICK_NO_SHIFT),\n"



    "    ('Shift 点击：客户端未缓存时不再兜底（懒加载回 nil 就发不出去）', MUT_CLICK_NO_FALLBACK),\n"



    "    ('Shift 点击：卡片退回 Frame（实机不支持 OnClick）', MUT_CLICK_FRAME),\n"



    "    ('Shift 点击：聊天框没开时那一路被摘掉', MUT_CLICK_NO_OPENCHAT),\n"



    "    ('Shift 点击：右键也投递（不再只认左键）', MUT_CLICK_ANY_BUTTON),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('物品卡 Shift 点击变异登记 5 条', 1))











# ── ⑭ 提示框换肤：装备提示框不套插件皮（2026-09-23 用户口径）──────────────────



# 用户原话：「现在如果是装备的鼠标提示框，我希望不是我的UI」。



# 目标文件是本插件的**手写骨架件** Core/Hui.lua（CRLF），所以字节锚点用 \r\n。



# 变异把新增的「真·内容判据」退回「只看 ttItemMark」——正是修之前的行为：



#   DG.ShowItemTip 走 SetItemByID 分支不打标 → OnShow 按归属把皮亮回来



#   → 期望 harness 里 2 条物品提示框断言变红（方法级 SetItemByID 路径 + 掉落实物卡全链）。



# 变异是 bytes，注释只能英文。



_TIP_MUT_DEFS = (



    "MUT_TIP_ITEM_SKIN = ('Core/Hui.lua', (\n"



    "    b'                if on and TooltipHasItemContent(tt) then on = false end\\r\\n',\n"



    "    b'                if on and ttItemMark[tt] then on = false end -- MUT: mark only\\r\\n'))\n"



    "\n"



)



_TIP_DEF_ANCHOR = "MUTATIONS = [\n"



if _TIP_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑭步），上游可能已改动')



if 'MUT_TIP_ITEM_SKIN' in text:



    sys.exit('提示框换肤变异已存在，不再重复登记（幂等保护）')



text = text.replace(_TIP_DEF_ANCHOR, _TIP_MUT_DEFS + _TIP_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('提示框换肤变异定义 1 条', 1))







_TIP_REG_ANCHOR = (



    "    ('Shift 点击：右键也投递（不再只认左键）', MUT_CLICK_ANY_BUTTON),\n"



    "]\n"



)



if _TIP_REG_ANCHOR not in text:



    sys.exit('未找到 Shift 点击变异登记尾部锚点（第⑭步），上游或第⑬步可能已改动')



text = text.replace(



    _TIP_REG_ANCHOR,



    "    ('Shift 点击：右键也投递（不再只认左键）', MUT_CLICK_ANY_BUTTON),\n"



    "\n"



    "    # ⑭ 提示框换肤：装备提示框不套插件皮（用户 2026-09-23 口径）\n"



    "    ('换肤：物品判据退回只看打标（装备提示框又套上插件皮）', MUT_TIP_ITEM_SKIN),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('提示框换肤变异登记 1 条', 1))











# ── ⑮ 专业页 7 条（仅无限服，2026-09-23）─────────────────────────────────────



# 专业页是本插件独有的整页（Core/ProfessionUI.lua + 4 个 Data_Prof*.lua 生成物），



#   harness 侧刚补了 24 条静态 + 一大块动态断言。**每条断言都要有一条变异证明它不是恒真**，



#   否则就是白测（本项目铁律）。7 条覆盖三类：



#     ① 数据层：ranks 漏发射（本次真实缺口）、配方/采集元组形状；



#     ② 生成物挂钩：第三颗「专业」胶囊；



#     ③ 界面层纪律：gsub 多返回值 / 行必须是 Button / 活代码禁 SetParent / 渲染路径禁新建帧 / 钓鱼先分流。



# 目标文件三种：Core/DungeonUI.lua（CRLF）、Core/ProfessionUI.lua（LF）、



#   Core/Data/Data_Professions.lua（LF）—— 故字节锚点的行尾各不相同，写错就是「锚点 0 次」。



# 变异是 bytes，注释只能英文。



_PROF_MUT_DEFS = (



    # ⑮-1 数据层：ranks 键改名（等价于「生成器忘了发射」）→ 钓鱼页技能等级整块静默消失。



    #      这正是本次真机缺口：解析 / 翻译 / 取用清单三处都在，唯独 build 没发射。



    "MUT_PROF_RANKS_GONE = ('Core/Data/Data_Professions.lua', (\n"



    "    b'            ranks = {\\n',\n"



    "    b'            _ranks_dead = { -- MUT: ranks never emitted\\n'))\n"



    "\n"



    # ⑮-2 生成物挂钩：第三颗「专业」胶囊被摘掉 → 静态 + 动态双红。



    "MUT_PROF_CAPSULE_GONE = (\n"



    "    b'        defs[#defs + 1] = { key = \"Professions\", text = L[\"\\xe4\\xb8\\x93\\xe4\\xb8\\x9a\"], width = DG.CAPSULE_W }\\r\\n',\n"



    "    b'        -- MUT: profession capsule removed\\r\\n')\n"



    "\n"



    # ⑮-3 界面层：gsub 第 3 实参少套一层括号（DG.ItemName 返回两个值 → 收到 boolean）



    #      实机表现就是「bad argument #3 to 'gsub'」整页崩，故动态也会红。



    "MUT_PROF_GSUB_MULTI = ('Core/ProfessionUI.lua', (\n"



    "    b'            if book then note = note:gsub(\"{book}\", (DG.ItemName(book))) end\\n',\n"



    "    b'            if book then note = note:gsub(\"{book}\", DG.ItemName(book)) end -- MUT: multi-return into gsub\\n'))\n"



    "\n"



    # ⑮-4 界面层：行退回 Frame（实机 "script type not supported"）。



    #      ★ 桩不区分帧类型（SetScript 一样记账）→ **只有静态断言抓得住**，



    #        与物品卡 MUT_CLICK_FRAME 同一类，必须留着。



    "MUT_PROF_ROW_FRAME = ('Core/ProfessionUI.lua', (\n"



    "    b'    r = CreateFrame(\"Button\", nil, PD.child, \"BackdropTemplate\")\\n',\n"



    "    b'    r = CreateFrame(\"Frame\", nil, PD.child, \"BackdropTemplate\") -- MUT: frame cannot click\\n'))\n"



    "\n"



    # ⑮-5 界面层：**活代码**里出现 SetParent（桩是空实现、实机是 ACCESS_VIOLATION）。



    #      锚点是 SetScrollChild 那行（本来就有），插一行真调用在它后面。



    "MUT_PROF_SETPARENT = ('Core/ProfessionUI.lua', (\n"



    "    b'    scroll:SetScrollChild(child)\\n',\n"



    "    b'    scroll:SetScrollChild(child)\\n    child:SetParent(scroll) -- MUT: live SetParent\\n'))\n"



    "\n"



    # ⑮-6 界面层：渲染调度里新建帧 → 破「池化复用」。



    #      静态（PD.Render 段内禁 CreateFrame）与动态（第二遍全量渲染零新建帧）双红。



    "MUT_PROF_RENDER_FRAME = ('Core/ProfessionUI.lua', (\n"



    "    b'function PD.Render()\\n',\n"



    "    b'function PD.Render()\\n    PD._mutFrame = CreateFrame(\"Frame\", nil, PD.page) -- MUT: render builds frame\\n'))\n"



    "\n"



    # ⑮-7 界面层：钓鱼不再先分流 → GA.fishing 的 {区域,技能,原始值} 混进节点循环，



    #      对数字调 ipairs（实机必崩：attempt to index a number value）。静态 + 动态双红。



    "MUT_PROF_FISH_SPLIT = ('Core/ProfessionUI.lua', (\n"



    "    b'    if PD.cur == \"fishing\" then\\n        PD.RowsFishing(rows)\\n        return\\n    end\\n',\n"



    "    b'    -- MUT: fishing no longer split out\\n'))\n"



    "\n"



)



_PROF_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑮步），上游可能已改动')



if 'MUT_PROF_RANKS_GONE' in text:



    sys.exit('专业页变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF_DEF_ANCHOR, _PROF_MUT_DEFS + _PROF_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页变异定义 7 条', 1))







_PROF_REG_ANCHOR = (



    "    ('换肤：物品判据退回只看打标（装备提示框又套上插件皮）', MUT_TIP_ITEM_SKIN),\n"



    "]\n"



)



if _PROF_REG_ANCHOR not in text:



    sys.exit('未找到提示框换肤变异登记尾部锚点（第⑮步），上游或第⑭步可能已改动')



text = text.replace(



    _PROF_REG_ANCHOR,



    "    ('换肤：物品判据退回只看打标（装备提示框又套上插件皮）', MUT_TIP_ITEM_SKIN),\n"



    "\n"



    "    # ⑮ 专业页（仅无限服，2026-09-23）\n"



    "    ('专业页：钓鱼技能等级表 ranks 从不发射（整块静默消失）', MUT_PROF_RANKS_GONE),\n"



    "    ('专业页：第三颗「专业」胶囊消失（无限服退回两颗）', MUT_PROF_CAPSULE_GONE),\n"



    "    ('专业页：gsub 少套括号（多返回值直灌末参 → 整页崩）', MUT_PROF_GSUB_MULTI),\n"



    "    ('专业页：行退回 Frame（实机不支持 OnClick）', MUT_PROF_ROW_FRAME),\n"



    "    ('专业页：活代码里出现 SetParent（scroll child 悬空指针）', MUT_PROF_SETPARENT),\n"



    "    ('专业页：渲染调度里新建帧（池化复用被破）', MUT_PROF_RENDER_FRAME),\n"



    "    ('专业页：钓鱼不再先分流（对数字 ipairs → 实机必崩）', MUT_PROF_FISH_SPLIT),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页变异登记 7 条', 1))











# ── ⑯ 专业页观感六改 8 条（2026-09-23 用户口径）───────────────────────────────



# 本轮改动：①每页一张大卡片 ②升级页两列 ③阈值数字染色（不再写「黄绿灰」）



#          ④Legacy → 传承 ⑤分类按钮宽度自适应 ⑥营地对照表改真表格。



# **每条新断言都要有一条变异证明它不是恒真**（本项目铁律：断言没变异 = 白测）。



# 目标文件 Core/ProfessionUI.lua 是**手写骨架件、行尾 LF**，故锚点用 \n（不是 \r\n）。



_PROF2_MUT_DEFS = (



    # ⑯-1 大卡没定位 → 恒为零尺寸，界面上等于没有大卡



    #      ★ 锚点必须**两条 SetPoint 一起摘**：只摘一条的话「PD.listCard:SetPoint」还在，



    #        静态断言照样绿（第一次就是这么写的，实测漏抓）。



    "MUT_PROF_BIGCARD_UNPOS = ('Core/ProfessionUI.lua', (\n"



    "    b'    PD.listCard:ClearAllPoints()\\n    PD.listCard:SetPoint(\"TOPLEFT\", PD.page, \"TOPLEFT\",\\n                         PD.RIGHT_X - PD.LIST_PAD, -(top - PD.LIST_PAD))\\n    PD.listCard:SetPoint(\"BOTTOMRIGHT\", PD.page, \"BOTTOMRIGHT\",\\n                         -(PAGE_INSET - PD.LIST_PAD), bot - PD.LIST_PAD)\\n',\n"



    "    b'    PD.listCard:ClearAllPoints()\\n    -- MUT: big card never positioned\\n'))\n"



    "\n"



    # ⑯-2 行又各自成卡（常态 alpha 回去了）→ 整页一张大卡白做



    #      ★ 锚点 2026-09-24 换过：行常态改由 PD.SetRowHover 统一落值（原来那两行字面量



    #        已从 PD.Row 挪进 PD.SetRowHover），故改成摘「创建时写常态」这一句。



    "MUT_PROF_ROW_CARD = ('Core/ProfessionUI.lua', (\n"



    "    b'    r.__hlOn = false\\n    PD.SetRowHover(r, false)\\n',\n"



    "    b'    r.__hlOn = false\\n    r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG) -- MUT: row keeps its own card\\n    r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE) -- MUT\\n'))\n"



    "\n"



    # ⑯-3 配方行阈值不再染色（退回纯数字）→ 静态（TierText 调用数）+ 动态（无内联色码）双红



    "MUT_PROF_TIER_NOCLR = ('Core/ProfessionUI.lua', (\n"



    "    b'                       PD.TierText(r[8], r[9], r[10])),\\n',\n"



    "    b'                       tostring(r[8]) .. \"/\" .. tostring(r[9]) .. \"/\" .. tostring(r[10])), -- MUT: tier colour dropped\\n'))\n"



    "\n"



    # ⑯-4 三个数字用同一个颜色 = 等于没染（静态缺 40d940 + 动态「三种颜色互不相同」红）



    "MUT_PROF_TIER_SAMECLR = ('Core/ProfessionUI.lua', (\n"



    "    b'PD.TIER_HEX = { \"|cffffd100\", \"|cff40d940\", \"|cff8c8c8c\" }\\n',\n"



    "    b'PD.TIER_HEX = { \"|cffffd100\", \"|cffffd100\", \"|cffffd100\" } -- MUT: one colour for all three\\n'))\n"



    "\n"



    # ⑯-5 第 6 颗子页签退回英文 Legacy（用户明确要求叫「传承」）



    "MUT_PROF_LEGACY_LABEL = ('Core/ProfessionUI.lua', (\n"



    "    b'    { key = \"legacy\",   text = L[\"\\xe4\\xbc\\xa0\\xe6\\x89\\xbf\"] },\\n',\n"



    "    b'    { key = \"legacy\",   text = \"Legacy\" }, -- MUT: english label back\\n'))\n"



    "\n"



    # ⑯-6 分类按钮退回定宽 72（长分类名又被裁成半截）



    "MUT_PROF_TOOL_FIXEDW = ('Core/ProfessionUI.lua', (\n"



    "    b'            bt:SetSize(w, PD.TOOL_H)\\n',\n"



    "    b'            bt:SetSize(PD.TOOL_W, PD.TOOL_H) -- MUT: fixed width back\\n'))\n"



    "\n"



    # ⑯-8（已删）两列被压回一列 —— 升级页 2026-09-23 晚改通栏后不再有 col=2 的行，



    #     这条变异注入了也测不出任何变化，随两列版式一起退役。



)



_PROF2_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF2_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑯步），上游可能已改动')



if 'MUT_PROF_BIGCARD_UNPOS' in text:



    sys.exit('专业页观感变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF2_DEF_ANCHOR, _PROF2_MUT_DEFS + _PROF2_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页观感变异定义 8 条', 1))







_PROF2_REG_ANCHOR = (



    "    ('专业页：钓鱼不再先分流（对数字 ipairs → 实机必崩）', MUT_PROF_FISH_SPLIT),\n"



    "]\n"



)



if _PROF2_REG_ANCHOR not in text:



    sys.exit('未找到专业页变异登记尾部锚点（第⑯步），第⑮步可能已改动')



text = text.replace(



    _PROF2_REG_ANCHOR,



    _PROF2_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ⑯ 专业页观感六改（2026-09-23 用户口径）\n"



    "    ('专业页：大卡片没定位（等于没有大卡）', MUT_PROF_BIGCARD_UNPOS),\n"



    "    ('专业页：行又各自成卡（一张大卡的意义没了）', MUT_PROF_ROW_CARD),\n"



    "    ('专业页：阈值数字不再染色（退回纯数字）', MUT_PROF_TIER_NOCLR),\n"



    "    ('专业页：阈值三个数字同色（等于没染）', MUT_PROF_TIER_SAMECLR),\n"



    "    ('专业页：第 6 颗子页签退回英文 Legacy', MUT_PROF_LEGACY_LABEL),\n"



    "    ('专业页：分类按钮退回定宽 72（长名被裁）', MUT_PROF_TOOL_FIXEDW),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页观感变异登记 8 条', 1))











# ── ⑰ 专业页三轮补丁 6 条（2026-09-23 傍晚，用户逐条）─────────────────────────



# 本轮改动：②对照表搬「营地·加成」 ③来源行去掉「读物」



#          ④新配方加绿色「新」字 ⑤关联任务显任务名 ⑥删「要学的法术」ID 列表。



# （原 ⑰-1「左列收窄」随 2026-09-23 晚的通栏改版一起退役：没有右列可压了。）



_PROF3_MUT_DEFS = (



    # ⑰-2 新配方「新」字被摘（退回只有左缘竖条）



    # ★ 2026-09-25 本地化：串包 L 后锚点同步（L[" |cff40d940新|r"] 形态）



    "MUT_PROF_NEW_TAG_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'    r.a:SetText((spec.text or \"\") .. (spec.is_new and L[\" |cff40d940\\xe6\\x96\\xb0|r\"] or \"\"))\\n',\n"



    "    b'    r.a:SetText(spec.text or \"\") -- MUT: NEW tag dropped\\n'))\n"



    "\n"



    # ⑰-3 「读物：子站名」又亮出来（无意义还像第二处署名）



    "MUT_PROF_READ_BACK = ('Core/ProfessionUI.lua', (\n"



    "    b'    if s.drops and #s.drops > 0 then\\n        out[#out + 1] = { text = format(L[\"\\xe6\\x8e\\x89\\xe8\\x90\\xbd %d \\xe5\\xa4\\x84\"], #s.drops) }\\n    end\\n',\n"



    "    b'    if s.read then out[#out + 1] = { text = format(L[\"\\xe8\\xaf\\xbb\\xe7\\x89\\xa9\\xef\\xbc\\x9a%s\"], tostring(s.read)) } end -- MUT: read back\\n"



    "    if s.drops and #s.drops > 0 then\\n        out[#out + 1] = { text = format(L[\"\\xe6\\x8e\\x89\\xe8\\x90\\xbd %d \\xe5\\xa4\\x84\"], #s.drops) }\\n    end\\n'))\n"



    "\n"



    # ⑰-4 关联任务退回裸 ID（任务名查询被摘）



    # ★ 2026-09-24 二轮：任务行跟着升级页改版换到左栏，截断口从 Fit1 改名成 FitL（锚点同步）



    "MUT_PROF_QUEST_BAREID = ('Core/ProfessionUI.lua', (\n"



    "    b'                text = FitL(PD.QuestName(id)),\\n',\n"



    "    b'                text = tostring(id), -- MUT: bare quest id back\\n'))\n"



    "\n"



    # ⑰-5 「要学的法术」ID 列表又长回来（用户判无用）



    "MUT_PROF_LEARN_BACK = ('Core/ProfessionUI.lua', (\n"



    "    b'    if lv.rods and #lv.rods > 0 then\\n',\n"



    "    b'    if lv.learn and #lv.learn > 0 then -- MUT: spell id list back\\n'))\n"



    "\n"



    # ⑰-6 首页进不了「营地·加成」（TabsFor 提前返回退回单页签）



    "MUT_PROF_INDEX_CAMP_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'    if slug == \"__index\" then return { \"overview\", \"camp\" } end\\n',\n"



    "    b'    if slug == \"__index\" then return { \"overview\" } end -- MUT: index camp gone\\n'))\n"



    "\n"



    # ⑰-7 换专业不复位营地视图（上一专业的「加成」态粘到下一专业）



    "MUT_PROF_CAMPVIEW_STICKY = ('Core/ProfessionUI.lua', (\n"



    "    b'        PD.campView = \"a\"\\n',\n"



    "    b'        -- MUT: camp view sticky across professions\\n'))\n"



    "\n"



)



_PROF3_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF3_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑰步），上游可能已改动')



if 'MUT_PROF_LEFCOL_FULLW' in text:



    sys.exit('三轮变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF3_DEF_ANCHOR, _PROF3_MUT_DEFS + _PROF3_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页三轮变异定义 6 条', 1))







_PROF3_REG_ANCHOR = (



    "]\n"



)



if _PROF3_REG_ANCHOR not in text:



    sys.exit('未找到专业页观感变异登记尾部锚点（第⑰步），第⑯步可能已改动')



text = text.replace(



    _PROF3_REG_ANCHOR,



    _PROF3_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ⑰ 专业页三轮补丁（2026-09-23 傍晚，用户逐条）\n"



    "    ('专业页：新配方的绿色「新」字被摘', MUT_PROF_NEW_TAG_GONE),\n"



    "    ('专业页：来源行又亮出「读物：子站名」', MUT_PROF_READ_BACK),\n"



    "    ('专业页：关联任务退回裸 ID（任务名被摘）', MUT_PROF_QUEST_BAREID),\n"



    "    ('专业页：要学的法术 ID 列表长回来', MUT_PROF_LEARN_BACK),\n"



    "    ('专业页：首页进不了营地·加成（页签被摘）', MUT_PROF_INDEX_CAMP_GONE),\n"



    "    ('专业页：换专业不复位营地视图', MUT_PROF_CAMPVIEW_STICKY),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页三轮变异登记 6 条', 1))











# ── ⑱ 升级页通栏改版 + 「职业加成」签名 5 条（2026-09-23 晚，用户逐条）─────────



# 本轮改动：①升级页改通栏一行式（区间→名称→次数→材料，不写「技能」）



#          ②营地页第三视图签名改「职业加成」。



_PROF4_MUT_DEFS = (



    # ⑱-1 单列页的行宽被压窄（col == 1 是**所有**单列页共用的分支：一旦恒收 COL_LW，



    #      配方 / 总览 / 采集 / 传承…整片窄半截 —— 第六轮踩过、用户一眼看出来过）



    # ★ 2026-09-24 二轮：行宽改成「先看 PD.lvSplit 再按 col 分」，锚点跟着换到单列那一支。



    "MUT_PROF_ROW_NARROW = ('Core/ProfessionUI.lua', (\n"



    "    b'                w = PD.RIGHT_W - 2 * PD.LIST_PAD\\n',\n"



    "    b'                w = PD.COL_LW -- MUT: single-col pages narrowed\\n'))\n"



    "\n"



    # ⑱-2 分段行区间写回「技能」前缀（用户：这两个字不要）



    "MUT_PROF_STEP_SKILL = ('Core/ProfessionUI.lua', (\n"



    "    b'                rng = format(L[\"%s \\xe2\\x86\\x92 %s\"], tostring(st[1]), tostring(st[2])),\\n',\n"



    "    b'                rng = format(L[\"\\xe6\\x8a\\x80\\xe8\\x83\\xbd %s \\xe2\\x86\\x92 %s\"], tostring(st[1]), tostring(st[2])), -- MUT: skill prefix back\\n'))\n"



    "\n"



    # ⑱-3 ★★ 2026-09-24 二轮**退役**：分段行的材料列随「右栏 = 汇总备料清单」一起撤掉了



    #      （材料不再跟着每段走）→ 这条变异失去注入点。同一块版面改由下面 ⑱-3' 守。



    # ⑱-3' 右栏的备料清单跑回左栏（升级页退化成单列 —— 用户要的「两列」就没了）



    "MUT_PROF_SHOP_RIGHT_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'        PushHead(rows, L[\"\\xe8\\xa6\\x81\\xe5\\x87\\x86\\xe5\\xa4\\x87\\xe7\\x9a\\x84\\xe6\\x9d\\x90\\xe6\\x96\\x99\"], 2)\\n',\n"



    "    b'        PushHead(rows, L[\"\\xe8\\xa6\\x81\\xe5\\x87\\x86\\xe5\\xa4\\x87\\xe7\\x9a\\x84\\xe6\\x9d\\x90\\xe6\\x96\\x99\"], 1) -- MUT: shopping list back to left\\n'))\n"



    "\n"



    # ⑱-4 「~N 次制作」被摘



    "MUT_PROF_STEP_NOCNT = ('Core/ProfessionUI.lua', (\n"



    "    b'        r.c:SetText(spec.cnt or \"\")\\n',\n"



    "    b'        r.c:SetText(\"\") -- MUT: craft count dropped\\n'))\n"



    "\n"



    # ⑱-5 对照页签名退回单字「加成」（用户措辞是「职业加成」）



    # ★ 2026-09-24 三轮：「职业加成」工具钮已从各专业营地页撤掉（对照视图收归营地系统），



    #   锚点从工具钮移到 camping 页签改名行（bt:SetText，16 空格缩进）。



    "MUT_PROF_BONUS_LABEL = ('Core/ProfessionUI.lua', (\n"



    "    b'                bt:SetText(L[\"\\xe8\\x81\\x8c\\xe4\\xb8\\x9a\\xe5\\x8a\\xa0\\xe6\\x88\\x90\"])\\n',\n"



    "    b'                bt:SetText(L[\"\\xe5\\x8a\\xa0\\xe6\\x88\\x90\"]) -- MUT: label back\\n'))\n"



    "\n"



)



_PROF4_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF4_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑱步），上游可能已改动')



if 'MUT_PROF_ROW_NARROW' in text:



    sys.exit('通栏改版变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF4_DEF_ANCHOR, _PROF4_MUT_DEFS + _PROF4_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页通栏改版变异定义 5 条', 1))







_PROF4_REG_ANCHOR = (



    "    ('专业页：换专业不复位营地视图', MUT_PROF_CAMPVIEW_STICKY),\n"



    "]\n"



)



if _PROF4_REG_ANCHOR not in text:



    sys.exit('未找到三轮变异登记尾部锚点（第⑱步），第⑰步可能已改动')



text = text.replace(



    _PROF4_REG_ANCHOR,



    _PROF4_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ⑱ 升级页通栏改版 + 职业加成签名（2026-09-23 晚）\n"



    "    ('专业页：单列页行宽被压窄（col=1 恒收 COL_LW）', MUT_PROF_ROW_NARROW),\n"



    "    ('专业页：分段行写回「技能」前缀', MUT_PROF_STEP_SKILL),\n"



    "    ('专业页：右栏备料清单跑回左栏', MUT_PROF_SHOP_RIGHT_GONE),\n"



    "    ('专业页：分段行次制作被摘', MUT_PROF_STEP_NOCNT),\n"



    "    ('专业页：营地第三视图退回单字加成', MUT_PROF_BONUS_LABEL),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页通栏改版变异登记 5 条', 1))











# ── ⑲ 配方页去详情条 + 材料行内图标 2 条（2026-09-23 晚，用户逐条）─────────────



# 本轮改动：①配方页详情条整体退役（行内信息已足够）；②材料文本在数量与名字之间加小图标。



_PROF5_MUT_DEFS = (



    # ⑲-1 材料小图标被摘（退回纯「数量×名字」—— 详情条退役后图标是行内唯一记号）



    "MUT_PROF_MATICON_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'        t[#t + 1] = format(\"%d\\xc3\\x97%s%s\", m[2] or 1, PD.MatIconTex(m[1]), DG.ItemName(m[1]))\\n',\n"



    "    b'        t[#t + 1] = format(\"%d\\xc3\\x97%s\", m[2] or 1, DG.ItemName(m[1])) -- MUT: mat icon dropped\\n'))\n"



    "\n"



    # ⑲-2 详情条长回来（Build 里重建 PD.detail → 静态与动态断言双抓）



    "MUT_PROF_DETAIL_BACK = ('Core/ProfessionUI.lua', (\n"



    "    b'    PD.BuildIndexGrid(child)\\n',\n"



    "    b'    PD.BuildIndexGrid(child)\\n    PD.detail = CreateFrame(\"Frame\", nil, page) -- MUT: detail back\\n'))\n"



    "\n"



)



_PROF5_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF5_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑲步），上游可能已改动')



if 'MUT_PROF_MATICON_GONE' in text:



    sys.exit('五轮变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF5_DEF_ANCHOR, _PROF5_MUT_DEFS + _PROF5_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页五轮变异定义 2 条', 1))







_PROF5_REG_ANCHOR = (



    "    ('专业页：营地第三视图退回单字加成', MUT_PROF_BONUS_LABEL),\n"



    "]\n"



)



if _PROF5_REG_ANCHOR not in text:



    sys.exit('未找到通栏改版变异登记尾部锚点（第⑲步），第⑱步可能已改动')



text = text.replace(



    _PROF5_REG_ANCHOR,



    _PROF5_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ⑲ 配方页去详情条 + 材料行内图标（2026-09-23 晚）\n"



    "    ('专业页：配方材料的小图标被摘', MUT_PROF_MATICON_GONE),\n"



    "    ('专业页：配方详情条长回来', MUT_PROF_DETAIL_BACK),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页五轮变异登记 2 条', 1))











# ── ⑳ 材料列改版 3 条（2026-09-24：配方页材料进中间列 + 升级页左右两栏）────────────



# 本轮改动：①配方行副行只剩部位等级、材料进中间列（13pt）②升级页每行左右两栏（材料列固定左锚）。



_PROF6_MUT_DEFS = (



    # ⑳-1 材料又挤回副行（11pt 小字的原状 —— 用户点名的「特别小」）



    "MUT_PROF_MATCOL_BACK = ('Core/ProfessionUI.lua', (\n"



    "    b'            local sg\\n            s.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)\\n            s.matSegs = sg\\n',\n"



    "    b'            s.sub = s.sub .. \"   \" .. PD.MatText(s._mats, 4) -- MUT: mats back into sub\\n            s.mats = \"\"\\n            s.matSegs = nil\\n'))\n"



    "\n"



    # ⑳-2 ★★ 2026-09-24 二轮**退役**：升级页不再有「每段跟着的材料列」（右栏改放汇总清单）



    #      → 这条变异失去注入点，同上由 ⑱-3' 守右栏。这里换成守「左栏取宽 / 右栏取窄」的比例。



    # ⑳-2' 两栏比例拉平（右栏不再「很小」，用户明确要的是右栏只放名称 + 数量的窄列）



    #       ★ 四轮换锚：比例系数 0.66 → 0.72（用户要求右栏再收窄、宽度留给左栏）



    "MUT_PROF_COL_RATIO_FLAT = ('Core/ProfessionUI.lua', (\n"



    "    b'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * 0.72)\\n',\n"



    "    b'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * 0.50) -- MUT: columns evened out\\n'))\n"



    "\n"



    # ⑳-3 材料列字体串退回 11pt（不再吃 PD.MAT_FS —— 字号口径被旁路）



    "MUT_PROF_MAT_FS_WIRING = ('Core/ProfessionUI.lua', (\n"



    "    b'    r.f = MakeFS(r, PD.MAT_FS, C_TEXT, \"LEFT\")\\n',\n"



    "    b'    r.f = MakeFS(r, 11, C_TEXT, \"LEFT\") -- MUT: font size bypassed\\n'))\n"



    "\n"



)



_PROF6_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF6_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第⑳步），上游可能已改动')



if 'MUT_PROF_MATCOL_BACK' in text:



    sys.exit('六轮变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF6_DEF_ANCHOR, _PROF6_MUT_DEFS + _PROF6_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页六轮变异定义 3 条', 1))







_PROF6_REG_ANCHOR = (



    "    ('专业页：配方详情条长回来', MUT_PROF_DETAIL_BACK),\n"



    "]\n"



)



if _PROF6_REG_ANCHOR not in text:



    sys.exit('未找到五轮变异登记尾部锚点（第⑳步），第⑲步可能已改动')



text = text.replace(



    _PROF6_REG_ANCHOR,



    _PROF6_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ⑳ 材料列改版（2026-09-24）\n"



    "    ('专业页：材料又挤回副行（11pt 小字原状）', MUT_PROF_MATCOL_BACK),\n"



    "    ('专业页：两栏比例拉平（右栏不再留窄）', MUT_PROF_COL_RATIO_FLAT),\n"



    "    ('专业页：材料列字体串退回 11pt', MUT_PROF_MAT_FS_WIRING),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页六轮变异登记 3 条', 1))







# ── ㉑ 升级页两栏「看得出是两列」3 条（2026-09-24 二轮，用户逐条）─────────────



# 本轮改动：①左栏收窄到半幅、材料列加宽 ②两栏之间留空隙 + 亮一条竖向分栏线



#          ③「~N 次制作」右缘收在分栏线左侧（不再贴着材料串）。



_PROF7_MUT_DEFS = (



    # ㉑-1 升级页不举手亮分栏线（两块之间没有竖线 → 整行又读成一条横排）



    "MUT_PROF_LVSPLIT_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'        PD.lvSplit = true\\n',\n"



    "    b'        PD.lvSplit = false -- MUT: split line not raised\\n'))\n"



    "\n"



    # ㉑-2 ★ 2026-09-24 二轮换锚：「~N 次制作」不再贴**本栏**右缘（跑掉/被别的东西顶走）



    # ⚠️ 通用那一支的右锚是**同一句**（只是 x 写死 -6），所以锚点必须带上紧邻的 `return`



    #    才唯一 —— 光锚 `r.c:SetPoint("RIGHT", r, "RIGHT"…)` 会命中 2 处（锚点体检当场报出来）。



    "MUT_PROF_CNT_AGAIN_MATS = ('Core/ProfessionUI.lua', (\n"



    "    b'        r.c:SetPoint(\"RIGHT\", r, \"RIGHT\", -6, 0)\\n        return\\n',\n"



    "    b'        r.c:SetPoint(\"RIGHT\", r, \"RIGHT\", -140, 0) -- MUT: count off the column edge\\n        return\\n'))\n"



    "\n"



    # ㉑-3 分栏线调回看不见的淡度（线还在，但等于没画）



    "MUT_PROF_DIV_FAINT = ('Core/ProfessionUI.lua', (\n"



    "    b'    divider:SetColorTexture(1, 1, 1, 0.12)\\n',\n"



    "    b'    divider:SetColorTexture(1, 1, 1, 0.02) -- MUT: split line invisible\\n'))\n"



    "\n"



)



_PROF7_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF7_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉑步），上游可能已改动')



if 'MUT_PROF_LVSPLIT_GONE' in text:



    sys.exit('七轮变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF7_DEF_ANCHOR, _PROF7_MUT_DEFS + _PROF7_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页七轮变异定义 3 条', 1))







_PROF7_REG_ANCHOR = (



    "    ('专业页：材料列字体串退回 11pt', MUT_PROF_MAT_FS_WIRING),\n"



    "]\n"



)



if _PROF7_REG_ANCHOR not in text:



    sys.exit('未找到六轮变异登记尾部锚点（第㉑步），第⑳步可能已改动')



text = text.replace(



    _PROF7_REG_ANCHOR,



    _PROF7_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ㉑ 升级页两栏（2026-09-24 二轮）\n"



    "    ('专业页：升级页不亮分栏线（两栏又读成一条横排）', MUT_PROF_LVSPLIT_GONE),\n"



    "    ('专业页：次数不再贴左栏右缘（跑到栏中间）', MUT_PROF_CNT_AGAIN_MATS),\n"



    "    ('专业页：分栏线淡到看不见（等于没画）', MUT_PROF_DIV_FAINT),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页七轮变异登记 3 条', 1))











# ── ㉒ 升级页左栏「每段材料」+ 区间列宽 2 条（2026-09-24 三轮，用户逐条）─────────



# 本轮改动：①分段行行内加回材料列（用户原话：「为什么现在左侧列没有需要材料呢」）



#          ②区间列宽改按本页最宽区间现算（用户原话：「100 → 140 这些和名称有点重叠了，



#            这个名称整体需要往右边移一点」）



_PROF8_MUT_DEFS = (



    # ㉒-1 行内材料列又被摘掉（左栏只剩区间 / 名称 / 次数 —— 用户实测问「材料呢」的那一版）



    "MUT_PROF_LV_STEP_MATS_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'        r.f:SetText(spec.mats or \"\")\\n',\n"



    "    b'        r.f:SetText(\"\") -- MUT: per-step mats dropped again\\n'))\n"



    "\n"



    # ㉒-2 区间列宽写死（三位数区间回到压配方名的状态）



    "MUT_PROF_LVNAME_FIXED = ('Core/ProfessionUI.lua', (\n"



    "    b'    PD.LV_NAME_X = math.max(PD.LV_NAME_X_MIN, 6 + math.ceil(rngW) + PD.LV_COL_GAP)\\n',\n"



    "    b'    PD.LV_NAME_X = PD.LV_NAME_X_MIN -- MUT: range column width fixed\\n'))\n"



    "\n"



)



_PROF8_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF8_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉒步），上游可能已改动')



if 'MUT_PROF_LVNAME_FIXED' in text:



    sys.exit('八轮变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF8_DEF_ANCHOR, _PROF8_MUT_DEFS + _PROF8_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页八轮变异定义 2 条', 1))







_PROF8_REG_ANCHOR = (



    "    ('专业页：分栏线淡到看不见（等于没画）', MUT_PROF_DIV_FAINT),\n"



    "]\n"



)



if _PROF8_REG_ANCHOR not in text:



    sys.exit('未找到七轮变异登记尾部锚点（第㉒步），第㉑步可能已改动')



text = text.replace(



    _PROF8_REG_ANCHOR,



    _PROF8_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ㉒ 升级页左栏材料列 + 区间列宽（2026-09-24 三轮）\n"



    "    ('专业页：分段行行内材料列又被摘掉', MUT_PROF_LV_STEP_MATS_GONE),\n"



    "    ('专业页：区间列宽写死（三位数区间压名称）', MUT_PROF_LVNAME_FIXED),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页八轮变异登记 2 条', 1))











# ── ㉓ 悬停高亮「划走不灭」+ 商人兑换货币译名（2026-09-24 用户口径）──────────────



# 用户原话：①「现在专业里面每一行，我鼠标划过都会高亮，但是鼠标划走以后，这个高亮还是一直



#            显示」；②「现在配方里面 商人兑换有一个恩惠，改为 商人青睐」。



# 修法：把「亮不亮」收敛成 PD.SetRowHover 一处状态（OnEnter / OnLeave / 绑定 / 定时同步



#       四条路写同一个值），常态口径钉成「全透明」—— 原来创建写 0、离开写 0.03/0.05，



#       于是划过一次的行再也回不到出厂状态，留下那圈淡框，看上去就是「高亮没退」。



_PROF9_MUT_DEFS = (



    # ㉓-1 划走又写回「常态 0.03/0.05」→ 用户报的那圈淡框原样复活（动态：划走后描边必须为 0）



    "MUT_PROF_HL_LEAVE_BG = ('Core/ProfessionUI.lua', (\n"



    "    b'        r:SetBackdropColor(1, 1, 1, 0)\\n        r:SetBackdropBorderColor(1, 1, 1, 0)\\n',\n"



    "    b'        r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG) -- MUT: leave writes normal colour\\n        r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE) -- MUT\\n'))\n"



    "\n"



    # ㉓-2 定时同步整块摘掉 → 滚轮滚动 / 池复用后那一行的底色永久停在悬停档



    #      ★ 必须**整块**替换：只删 OnUpdate 那一行会留下悬空的 end) —— 那是语法错，属脏抓。



    "MUT_PROF_HL_NOSYNC = ('Core/ProfessionUI.lua', (\n"



    "    b'    local hlAcc = 0\\n    child:SetScript(\"OnUpdate\", function(_, el)\\n        hlAcc = hlAcc + el\\n        if hlAcc < 0.1 then return end\\n        hlAcc = 0\\n        PD.SyncHover()\\n    end)\\n',\n"



    "    b'    -- MUT: hover resync dropped\\n'))\n"



    "\n"



    # ㉓-3 同步只灭不亮（把判断写成无条件熄灭）→ 鼠标真在行上时高亮被熄掉（反向断言红）



    "MUT_PROF_HL_ALWAYSOFF = ('Core/ProfessionUI.lua', (\n"



    "    b'        if over ~= r.__hlOn then PD.SetRowHover(r, over) end\\n',\n"



    "    b'        PD.SetRowHover(r, false) -- MUT: sync only turns off\\n'))\n"



    "\n"



    # ㉓-4 商人兑换的货币退回旧译名「恩惠」（用户 2026-09-24 明确改叫「商人青睐」）



    "MUT_PROF_FAVOR_LABEL = ('Core/ProfessionUI.lua', (\n"



    "    b'        right2 = format(L[\"\\xe5\\x95\\x86\\xe4\\xba\\xba\\xe9\\x9d\\x92\\xe7\\x9d\\x90 %s\"], tostring(f[3])),\\n',\n"



    "    b'        right2 = format(L[\"\\xe6\\x81\\xa9\\xe6\\x83\\xa0 %s\"], tostring(f[3])), -- MUT: old name back\\n'))\n"



    "\n"



)



_PROF9_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF9_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉓步），上游可能已改动')



if 'MUT_PROF_HL_LEAVE_BG' in text:



    sys.exit('九轮变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF9_DEF_ANCHOR, _PROF9_MUT_DEFS + _PROF9_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页九轮变异定义 4 条', 1))







_PROF9_REG_ANCHOR = (



    "    ('专业页：区间列宽写死（三位数区间压名称）', MUT_PROF_LVNAME_FIXED),\n"



    "]\n"



)



if _PROF9_REG_ANCHOR not in text:



    sys.exit('未找到八轮变异登记尾部锚点（第㉓步），第㉒步可能已改动')



text = text.replace(



    _PROF9_REG_ANCHOR,



    _PROF9_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ㉓ 悬停高亮划走不灭 + 商人兑换译名（2026-09-24 四轮）\n"



    "    ('专业页：划走后行又回到常态淡框（用户报的常亮复活）', MUT_PROF_HL_LEAVE_BG),\n"



    "    ('专业页：悬停状态不再定时与鼠标对齐（滚轮后那一行常亮）', MUT_PROF_HL_NOSYNC),\n"



    "    ('专业页：同步只灭不亮（鼠标在行上时高亮被熄掉）', MUT_PROF_HL_ALWAYSOFF),\n"



    "    ('专业页：商人兑换货币退回旧译名「恩惠」', MUT_PROF_FAVOR_LABEL),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页九轮变异登记 4 条', 1))











# ── ④ 升级页四列宽度全给材料（2026-09-24 布局四轮，用户逐条）──────────────────────



# 用户原话：「现在左侧的材料你可以看显示的是不完全的，我需要显示完全。我觉得吧，右边这一列的



#           宽度可以缩小一点然后把宽度留给左边。然后呢，你现在材料和名称中间的宽度有点多了，



#           我觉得稍微可以再小一点，材料和制作次数的间距也可以缩小一点，最大可能都留给这个材料，



#           因为这个材料的宽度到时候会非常宽」。



# 修法：①右栏比例 0.66 → 0.72；②名称列（写死 150）与次数保留宽（写死 78）都按本页内容现算；



#       ③两处间距收到 8 / 6。省下来的全部落到材料列（炼金 157 → 317px）。



_PROF10_MUT_DEFS = (



    # ④-1 右栏没把宽度让给左栏（两栏拉平 → 左栏材料列又不够宽）



    "MUT_PROF_LVCOL_RW_FLAT = ('Core/ProfessionUI.lua', (\n"



    "    b'PD.COL_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.COL_LW\\n',\n"



    "    b'PD.COL_RW = PD.COL_LW -- MUT: right column keeps its width\\n'))\n"



    "\n"



    # ④-2 名称列写死回 150（名称实际只有 60~90px → 名称与材料之间白 122px，材料列被挤窄）



    "MUT_PROF_LVNAMEW_FAT = ('Core/ProfessionUI.lua', (\n"



    "    b'    PD.LV_NAME_W = math.min(PD.LV_NAME_W_MAX, math.max(PD.LV_NAME_W_MIN, math.ceil(nameW)))\\n',\n"



    "    b'    PD.LV_NAME_W = 150 -- MUT: name column fixed fat\\n'))\n"



    "\n"



    # ④-3 材料列右缘不再贴次数保留区（间距吃回宽的 LV_COL_GAP = 12）



    #      ⚠️ 锚点必须带**4 空格缩进**：同一句在常量区（行首无缩进）还有一份 ——



    #         短串锚点会命中 2 次（本项目踩过的坑，锚点体检当场抓到）。



    "MUT_PROF_LVMAT_CNTGAP = ('Core/ProfessionUI.lua', (\n"



    "    b'    PD.LV_MAT_W = PD.COL_LW - PD.LV_CNT_W - PD.LV_GAP_MAT_CNT - PD.LV_MAT_X\\n',\n"



    "    b'    PD.LV_MAT_W = PD.COL_LW - PD.LV_CNT_W - PD.LV_COL_GAP - PD.LV_MAT_X -- MUT: wide gap\\n'))\n"



    "\n"



    # ④-4 名称 → 材料 的间距吃回 12（白没留给材料）



    "MUT_PROF_LVMAT_NAMEGAP = ('Core/ProfessionUI.lua', (\n"



    "    b'PD.LV_GAP_NAME_MAT = 8',\n"



    "    b'PD.LV_GAP_NAME_MAT = 12 -- MUT: gap fat'))\n"



    "\n"



)



_PROF10_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF10_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第④步），上游可能已改动')



if 'MUT_PROF_LVNAMEW_FAT' in text:



    sys.exit('十轮变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF10_DEF_ANCHOR, _PROF10_MUT_DEFS + _PROF10_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页十轮变异定义 4 条', 1))







_PROF10_REG_ANCHOR = (



    "    ('专业页：商人兑换货币退回旧译名「恩惠」', MUT_PROF_FAVOR_LABEL),\n"



    "]\n"



)



if _PROF10_REG_ANCHOR not in text:



    sys.exit('未找到九轮变异登记尾部锚点（第④步），第㉓步可能已改动')



text = text.replace(



    _PROF10_REG_ANCHOR,



    _PROF10_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ④ 升级页四列宽度全给材料（2026-09-24 布局四轮）\n"



    "    ('专业页：右栏没把宽度让给左栏（两栏宽度拉平）', MUT_PROF_LVCOL_RW_FLAT),\n"



    "    ('专业页：名称列写死回 150（名称与材料间又留大片白）', MUT_PROF_LVNAMEW_FAT),\n"



    "    ('专业页：材料列右缘不贴次数保留区（间距吃回 12）', MUT_PROF_LVMAT_CNTGAP),\n"



    "    ('专业页：名称→材料间距吃回 12（白没留给材料）', MUT_PROF_LVMAT_NAMEGAP),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页十轮变异登记 4 条', 1))











# ── ㉕ 采集页去英文 + 钓鱼折两栏（2026-09-24）────────────────────────────────────



# 本轮三件事：①采集页区域名改走客户端（C_Map.GetAreaInfo，数据表只留 AreaTable ID）



#            ②采矿 / 采药节点标题改取「首个产出物」的客户端名（节点名客户端无查询口）



#            ③钓鱼采集页折两栏（PD.gridSplit，等宽网格、自动分列）



# ★ 先修正 ⑱-1 那条的锚点：单列页行宽在网格改造后换了写法



#   （`w = …` → `x, w = PD.LIST_PAD, ROW_W`）。锚点是**字节精确**的，不改就静默烂掉



#   （跑 DEFAULT_WANT 子集时永不触碰 —— 本项目实锤过一次）。



_MUT_FIX_ROW_NARROW = (



    ("    b'                w = PD.RIGHT_W - 2 * PD.LIST_PAD\\n',\n",



     "    b'                    x, w = PD.LIST_PAD, ROW_W\\n',\n"),



    ("    b'                w = PD.COL_LW -- MUT: single-col pages narrowed\\n'))\n",



     "    b'                    x, w = PD.LIST_PAD, PD.COL_LW"



     " -- MUT: single-col pages narrowed\\n'))\n"),



)



for _o, _n in _MUT_FIX_ROW_NARROW:



    if text.count(_o) != 1:



        sys.exit('㉕ 修正「单列页行宽」变异锚点失败：%r 命中 %d 次' % (_o, text.count(_o)))



    text = text.replace(_o, _n, 1)



print('  %-40s -> %d 处' % ('㉕ 修正单列页行宽变异锚点', 2))







_PROF11_MUT_DEFS = (



    # ㉕-1 区域名绕过客户端 → 恒落「区域 #ID」占位（数据表里已无英文名，界面立刻退成 ID 串）



    "MUT_PROF_ZONENAME_RAW = ('Core/ProfessionUI.lua', (\n"



    "    b'    if type(fn) == \"function\" then\\n',\n"



    "    b'    if false then -- MUT: zone name stops asking the client\\n'))\n"



    "\n"



    # ㉕-2 节点标题不问客户端 → 恒停「物品 #ID」占位（用户点名要消掉的就是这种 ID 串）



    "MUT_PROF_NODE_TITLE_RAW = ('Core/ProfessionUI.lua', (\n"



    "    b'        if not got then nm = head and format(L[\"\\xe7\\x89\\xa9\\xe5\\x93\\x81"



    " #%d\"], head) or \"?\" end\\n',\n"



    "    b'        nm = head and format(L[\"\\xe7\\x89\\xa9\\xe5\\x93\\x81 #%d\"], head)"



    " or \"?\" -- MUT: node title never uses client\\n'))\n"



    "\n"



    # ㉕-3 钓鱼采集页退回单列（用户要的「两列」就没了 —— 右半幅重新整片空着）



    "MUT_PROF_FISH_GRID_OFF = ('Core/ProfessionUI.lua', (\n"



    "    b'        PD.gridSplit = (PD.cur == \"fishing\")\\n',\n"



    "    b'        PD.gridSplit = false -- MUT: fishing back to single column\\n'))\n"



    "\n"



    # ㉕-4 网格不再自动分列（全塞第 1 栏）：两栏页退成「左栏一长条 + 右栏空白」，



    #      且 col=2 的行宽仍是半栏 → 半幅右边整片空着（正是用户要消掉的样子）。



    "MUT_PROF_GRID_ONE_COL = ('Core/ProfessionUI.lua', (\n"



    "    b'                    col = (y[2] < y[1]) and 2 or 1\\n',\n"



    "    b'                    col = 1 -- MUT: grid stops balancing columns\\n'))\n"



    "\n"



)



_PROF11_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF11_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉕步），上游可能已改动')



if 'MUT_PROF_FISH_GRID_OFF' in text:



    sys.exit('采集页去英文变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF11_DEF_ANCHOR, _PROF11_MUT_DEFS + _PROF11_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页十一轮变异定义 4 条', 1))







_PROF11_REG_ANCHOR = (



    "    ('专业页：名称→材料间距吃回 12（白没留给材料）', MUT_PROF_LVMAT_NAMEGAP),\n"



    "]\n"



)



if _PROF11_REG_ANCHOR not in text:



    sys.exit('未找到十轮变异登记尾部锚点（第㉕步），第④步可能已改动')



text = text.replace(



    _PROF11_REG_ANCHOR,



    _PROF11_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ㉕ 采集页去英文 + 钓鱼折两栏（2026-09-24）\n"



    "    ('专业页：区域名绕过客户端（恒落 区域 #ID）', MUT_PROF_ZONENAME_RAW),\n"



    "    ('专业页：采集节点标题不问客户端（恒落 物品 #ID）', MUT_PROF_NODE_TITLE_RAW),\n"



    "    ('专业页：钓鱼采集页退回单列（两栏没了）', MUT_PROF_FISH_GRID_OFF),\n"



    "    ('专业页：网格不再自动分列（全塞第 1 栏）', MUT_PROF_GRID_ONE_COL),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页十一轮变异登记 4 条', 1))











# ── ㉖ 升级分段行改「两行表格」+ 两侧图标同尺寸 + 来源补齐（2026-09-24 布局五轮）──────



# 用户原话：①「你看，这个图标大小和右边材料的图标大小明显不一样啊，我需要一致的」；



#          ②「这个配方是向训练师学习，还是通过购买图纸之类的，是没有展示出来的」。



# 修法：①分段行从「一行四样」改成**两行表格**（上行 区间 | 配方图标 | 配方名 | ~N 次制作，



#         下行 来源）；右侧材料改走**材料块**（图标 + 物品名 + ×N 落在名下方，整组右对齐，



#         放不下时最右补「…」）；②配方图标与材料图标统一吃 PD.TBL_ICON = 30；



#       ③来源由 PD.LevelSrc 现取（训练师直学 / 需图纸·商人出售）；



#       ④右栏比例 0.72 → 0.80 + 两条长标题缩短（**标题长度就是右栏宽的下限**）；



#       ⑤区间串全角「→」改半角「–」。



# ★★ 老锚点必须**受检替换**（count != 1 就 sys.exit）：几何从「四列常量 + 三处间距」



#    收敛成「avail = … / LV_NAME_W / LV_MAT_W」三行，⑱㉒④ 三步里 8 条变异的锚点全部失效。



#    **不改就是静默烂掉** —— 跑 DEFAULT_WANT 子集时永不触碰，跑 --all 又像「脚本 bug」



#    （本项目实锤过一次）。所以这一步先把它们的锚点接到新写法上，再补新条。



_MUT_REANCHOR_LV_TABLE = (



    # ⑱-2 区间串：全角箭头「→」→ 半角破折号「–」（用户早前点名「区间可以再小一点」）



    ("    b'                rng = format(L[\"%s \\xe2\\x86\\x92 %s\"], tostring(st[1]),"



     " tostring(st[2])),\\n',\n",



     "    b'                rng = format(L[\"%s \\xe2\\x80\\x93 %s\"], tostring(st[1]),"



     " tostring(st[2])),\\n',\n"),







    # ⑳-2' 两栏比例：0.72 → 0.80（分段行改两行表格后左栏要装的东西变多，再放宽一档）



    #      ★ 2026-09-25 enUS 换锚：系数改走 LV_SPLIT（enUS 0.75 / 中文 0.80，实机右栏截字修复）



    ("    b'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * 0.72)\\n',\n",



     "    b'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)\\n',\n"),







    # ㉑-2 次数右缘：写死 -6 → -PD.LV_CNT_R（现在要一次避开整片材料区）



    #      ⚠️ 旧锚点靠「紧跟 `return`」取唯一（当时那一句与通用支同形）；新写法自带



    #         `-PD.LV_CNT_R`，本身就唯一 —— 不再需要 `return`，也不能带（中间插了图标两行）。



    ("    b'        r.c:SetPoint(\"RIGHT\", r, \"RIGHT\", -6, 0)\\n        return\\n',\n",



     "    b'        r.c:SetPoint(\"RIGHT\", r, \"RIGHT\", -PD.LV_CNT_R, 0)\\n',\n"),



    ("    b'        r.c:SetPoint(\"RIGHT\", r, \"RIGHT\", -140, 0)"



     " -- MUT: count off the column edge\\n        return\\n'))\n",



     "    b'        r.c:SetPoint(\"RIGHT\", r, \"RIGHT\", -140, 0)"



     " -- MUT: count off the column edge\\n'))\n"),







    # ㉒-1 行内材料：材料**串**（r.f）→ 材料**块**（PD.PaintMats）



    ("    b'        r.f:SetText(spec.mats or \"\")\\n',\n",



     "    b'        PD.PaintMats(r, spec.blocks, spec.matCut, spec.passed)\\n',\n"),



    ("    b'        r.f:SetText(\"\") -- MUT: per-step mats dropped again\\n'))\n",



     "    b'        -- MUT: per-step mats dropped again\\n'))\n"),







    # ㉒-2 区间列宽：现在是「区间 + 配方图标」一起算进 LV_ICON_X



    ("    b'    PD.LV_NAME_X = math.max(PD.LV_NAME_X_MIN, 6 + math.ceil(rngW) + PD.LV_COL_GAP)\\n',\n",



     "    b'    PD.LV_ICON_X = 6 + math.ceil(rngW) + PD.TBL_RNG_GAP\\n',\n"),



    ("    b'    PD.LV_NAME_X = PD.LV_NAME_X_MIN -- MUT: range column width fixed\\n'))\n",



     "    b'    PD.LV_ICON_X = 6 + PD.TBL_RNG_GAP -- MUT: range column width fixed\\n'))\n"),







    # ④-2 名称列宽：写死常量 → PD.TBL_NAME_MAX / MIN



    ("    b'    PD.LV_NAME_W = math.min(PD.LV_NAME_W_MAX, math.max(PD.LV_NAME_W_MIN,"



     " math.ceil(nameW)))\\n',\n",



     "    b'    PD.LV_NAME_W = math.min(PD.TBL_NAME_MAX, math.max(PD.TBL_NAME_MIN,"



     " math.ceil(nameW)))\\n',\n"),







    # ④-3 材料区右缘：旧表达式 → avail 口径；变异体改成「吃掉次数列」（破坏 名称+材料 = avail）



    ("    b'    PD.LV_MAT_W = PD.COL_LW - PD.LV_CNT_W - PD.LV_GAP_MAT_CNT - PD.LV_MAT_X\\n',\n",



     "    b'    PD.LV_MAT_W = avail - PD.LV_NAME_W\\n',\n"),



    ("    b'    PD.LV_MAT_W = PD.COL_LW - PD.LV_CNT_W - PD.LV_COL_GAP - PD.LV_MAT_X"



     " -- MUT: wide gap\\n'))\n",



     "    b'    PD.LV_MAT_W = PD.COL_LW - PD.LV_NAME_X - PD.LV_NAME_W"



     " -- MUT: mat area eats the count column\\n'))\n"),







    # ④-4 名称→材料间距：间距常量已并入 avail 的算式 → 锚点换到 avail 那一行，



    #      变异体把 TBL_NAME_GAP 换成写死的 20（间距吃回 12px，材料区被挤到 <290）。



    ("    b'PD.LV_GAP_NAME_MAT = 8',\n",



     "    b'    local avail = PD.COL_LW - PD.TBL_MAT_RPAD - PD.LV_NAME_X"



     " - PD.TBL_NAME_GAP\\n',\n"),



    ("    b'PD.LV_GAP_NAME_MAT = 12 -- MUT: gap fat'))\n",



     "    b'    local avail = PD.COL_LW - PD.TBL_MAT_RPAD - PD.LV_NAME_X"



     " - 20 -- MUT: name-to-mats gap fattened to 20\\n'))\n"),



)



for _o, _n in _MUT_REANCHOR_LV_TABLE:



    if text.count(_o) != 1:



        sys.exit('㉖ 重接升级行变异锚点失败：%r 命中 %d 次' % (_o, text.count(_o)))



    text = text.replace(_o, _n, 1)



print('  %-40s -> %d 处' % ('㉖ 重接升级分段行变异锚点', len(_MUT_REANCHOR_LV_TABLE)))







_PROF12_MUT_DEFS = (



    # ㉖-1 配方图标尺寸不再跟材料图标一致（退回行图标默认的 20px —— 用户点名的那一版）



    "MUT_PROF_LV_TBL_ICON_DIFF = ('Core/ProfessionUI.lua', (\n"



    "    b'        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)\\n',\n"



    "    b'        r.icon:SetSize(20, 20) -- MUT: formula icon size differs\\n'))\n"



    "\n"







    # ㉖-2 材料图标自己写死一个数（两边又不一样 —— 同一条口径不许各写一个数字）



    "MUT_PROF_LV_TBL_MAT_ICON_DIFF = ('Core/ProfessionUI.lua', (\n"



    "    b'    b.ic:SetSize(PD.TBL_ICON, PD.TBL_ICON)\\n',\n"



    "    b'    b.ic:SetSize(24, 24) -- MUT: material icon size differs\\n'))\n"



    "\n"







    # ㉖-3 来源那一行不写了（用户点名「是没有展示出来的」的信息又消失）



    "MUT_PROF_LV_TBL_SRC_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'        PD.PaintCard(r, spec.card)\\n',\n"



    "    b'        PD.PaintCard(r, nil) -- MUT: source card dropped\\n'))\n"



    "\n"







    # ㉖-4 两行塌回一行（来源与配方名同一 y —— 又变成挤在一起的一行）



    "MUT_PROF_LV_TBL_SRC_SAMEY = ('Core/ProfessionUI.lua', (\n"



    "    b'        bg:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)\\n',\n"



    "    b'        bg:SetPoint(\"LEFT\", r, \"LEFT\", PD.LV_NAME_X + (k - 1) * seg, PD.TBL_NAME_DY)"



    " -- MUT: bar onto name line\\n'))\n"



    "\n"







    # ㉖-5 打包材料块时不再给「…」留那一格（块被画到预算外，右边溢出）



    "MUT_PROF_LV_TBL_NO_MARK_ROOM = ('Core/ProfessionUI.lua', (\n"



    "    b'        if total + step + PD.TBL_MARK_W > budget then\\n',\n"



    "    b'        if total + step > budget then -- MUT: no room kept for the ellipsis\\n'))\n"



    "\n"







    # ㉖-6 材料组从左边起摆（不再右对齐 —— 同页各行右缘参差不齐）



    "MUT_PROF_LV_TBL_GROUP_LEFT = ('Core/ProfessionUI.lua', (\n"



    "    b'    local right = PD.COL_LW - PD.TBL_MAT_RPAD',\n"



    "    b'    local right = PD.TBL_MAT_RPAD -- MUT: material group not right-aligned'))\n"



    "\n"







    # ㉖-7 七轮方案B改钉数量角标：块里唯一的信息就是 ×N（物品名已按方案B取消），



    #      角标归零 = 块失去内容。（锚点不含非 ASCII：只咬行尾 ` blk.cnt))`，× 在锚外。）



    "MUT_PROF_LV_TBL_CNT_ZERO = ('Core/ProfessionUI.lua', (\n"



    "    b' blk.cnt))\\n',\n"



    "    b' 0)) -- MUT: count badge zeroed\\n'))\n"



    "\n"



)



_PROF12_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROF12_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉖步），上游可能已改动')



if 'MUT_PROF_LV_TBL_ICON_DIFF' in text:



    sys.exit('升级分段行两行表格变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROF12_DEF_ANCHOR, _PROF12_MUT_DEFS + _PROF12_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('专业页十二轮变异定义 7 条', 1))







_PROF12_REG_ANCHOR = (



    "    ('专业页：网格不再自动分列（全塞第 1 栏）', MUT_PROF_GRID_ONE_COL),\n"



    "]\n"



)



if _PROF12_REG_ANCHOR not in text:



    sys.exit('未找到十一轮变异登记尾部锚点（第㉖步），第㉕步可能已改动')



text = text.replace(



    _PROF12_REG_ANCHOR,



    _PROF12_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ㉖ 升级分段行两行表格 + 两侧图标同尺寸 + 来源补齐（2026-09-24 布局五轮）\n"



    "    ('专业页：配方图标尺寸与材料图标不一致', MUT_PROF_LV_TBL_ICON_DIFF),\n"



    "    ('专业页：材料图标尺寸自己写死（两边又不一样）', MUT_PROF_LV_TBL_MAT_ICON_DIFF),\n"



    "    ('专业页：来源卡片不显示了（来源信息又消失）', MUT_PROF_LV_TBL_SRC_GONE),\n"



    "    ('专业页：色阶条塌到配方名那一行（两行叠一起）', MUT_PROF_LV_TBL_SRC_SAMEY),\n"



    "    ('专业页：材料块不再给省略号留那一格', MUT_PROF_LV_TBL_NO_MARK_ROOM),\n"



    "    ('专业页：材料组不再右对齐（左起摆）', MUT_PROF_LV_TBL_GROUP_LEFT),\n"



    "    ('专业页：材料块数量角标归零（块失去 ×N）', MUT_PROF_LV_TBL_CNT_ZERO),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('专业页十二轮变异登记 7 条', 1))











# ── ㉗ 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）──────────────────



# 用户原话：「给 2040 这个前导任务需要备注一下：不需要接 2041 就可以接」。



# 两条变异互为补充：一条断界面（渲染分支被关掉），一条断数据（备注挂到了不存在的任务上）。



# ⚠️ 数据那条落在 Data_DungeonQuests.lua（LF，锚点用 \n）；界面那条落在 Core/DungeonUI.lua



#    （CRLF，锚点用 \r\n）。锚点都收窄到不含中文的片段 —— Python 3 的 b'...' 不许写非 ASCII。



_QNOTE_MUT_DEFS = (



    "MUT_QPRENOTE_OFF = ('Core/DungeonUI.lua', (\n"



    "    b'        if pnote then\\r\\n',\n"



    "    b'        if false then -- MUT: pre-note never renders\\r\\n'))\n"



    "\n"



    "MUT_QPRENOTE_WRONGKEY = ('Core/Data/Data_DungeonQuests.lua', (\n"



    "    b'    [2040] = \"',\n"



    "    b'    [9999] = \"'))\n"



    "\n"



)



_QNOTE_DEF_ANCHOR = "MUTATIONS = [\n"



if _QNOTE_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉗步），上游可能已改动')



if 'MUT_QPRENOTE_OFF' in text:



    sys.exit('前导链备注变异已存在，不再重复登记（幂等保护）')



text = text.replace(_QNOTE_DEF_ANCHOR, _QNOTE_MUT_DEFS + _QNOTE_DEF_ANCHOR, 1)



print('  %-40s -> %d 处' % ('前导链备注变异定义 2 条', 1))







_QNOTE_REG_ANCHOR = (



    "    ('专业页：材料块数量角标归零（块失去 ×N）', MUT_PROF_LV_TBL_CNT_ZERO),\n"



    "]\n"



)



if _QNOTE_REG_ANCHOR not in text:



    sys.exit('未找到十二轮变异登记尾部锚点（第㉗步），第㉖步可能已改动')



text = text.replace(



    _QNOTE_REG_ANCHOR,



    _QNOTE_REG_ANCHOR.replace("]\n", "") +



    "\n"



    "    # ㉗ 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）\n"



    "    ('前导链备注：备注行不再渲染', MUT_QPRENOTE_OFF),\n"



    "    ('前导链备注：备注挂到了别的任务上（界面读不到）', MUT_QPRENOTE_WRONGKEY),\n"



    "]\n",



    1)



print('  %-40s -> %d 处' % ('前导链备注变异登记 2 条', 1))











# ── ㉘ 副本入口标记（2026-09-24 用户要求）──────────────────────────────────────



# 用户原话：「现在点击 NPC 名字会在地图上标记，我现在需要点击副本名字，能够标记副本的入口」。



# 三条各钉一面，合成一条链证明新断言不是白测：



#   ① 入口表查不到（dungeonID 被抹掉）→ 动态「点标题 → SetUserWaypoint 收到入口 UiMapPoint」必须失败；



#   ② 标题脱掉 OnMouseUp → 静态「详情标题可点」+ 动态「详情标题挂了 OnMouseUp」双双失败；



#   ③ 未收录时给兜底坐标 → 反向对照「未收录不落航点」必须失败 —— 少了③，



#      「未收录也照落一个点」这种骗人行为不会被任何断言发现。



#



# ⚠️ 锚点不能图省事用 `pcall(C_Map.SetUserWaypoint, pt)` 或 `local mapID = loc[1]`：



#    DG.MarkEntrance 与 DG.MarkNPC 是**镜像代码**，这两行实测各命中 2 次，注入会被直接拒



#    （见本文件其它处同样的教训）。锚点必须带上 ns.DungeonEntry / 函数头这些本功能独有的行。



# ⚠️ 锚点之间不能互相吃掉：① 若用 `local loc = ...` 那一行做锚，注入后 ③ 的两行锚就消失了



#    → 一次性批量注入时 data.count(old) != 1 → 整个跑批中止。故 ① 改锚函数头。



# 变异是 bytes，注释与兜底字面量都只能 ASCII（中文字面量会被当字节、破坏锚点匹配）。



_MUT_ENT_DEFS = (



    "MUT_ENT_LOOKUP_DEAD = (\n"



    "    b'function DG.MarkEntrance(dungeonID)\\r\\n',\n"



    "    b'function DG.MarkEntrance(dungeonID)\\r\\n'\n"



    "    b'    dungeonID = nil -- MUT: entrance id dropped (lookup never resolves)\\r\\n')\n"



    "\n"



    "MUT_ENT_TITLE_UNBOUND = (\n"



    "    b'    U.dungeonDetailTitle:SetScript(\"OnMouseUp\", function()\\r\\n'\n"



    "    b'        local dd = U.dungeonDetailCur\\r\\n'\n"



    "    b'        if dd then DG.MarkEntrance(dd.id) end\\r\\n'\n"



    "    b'    end)\\r\\n',\n"



    "    b'    -- MUT: entrance title click unbound\\r\\n')\n"



    "\n"



    "MUT_ENT_FALLBACK_COORD = (\n"



    "    b'    local loc = dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID]\\r\\n'\n"



    "    b'    if not loc then\\r\\n',\n"



    "    b'    local loc = (dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID])\\r\\n'\n"



    "    b'        or { 1453, 50.4, 66.4, \"\" } -- MUT: fallback coord when entrance unknown\\r\\n'\n"



    "    b'    if not loc then\\r\\n')\n"



    "\n"



)



_MUT_ENT_REG = (



    "    # ㉘ 副本入口标记（2026-09-24 用户要求）\n"



    "    ('入口标记：入口表查不到（点标题不落点）', MUT_ENT_LOOKUP_DEAD),\n"



    "    ('入口标记：标题脱掉 OnMouseUp（点不动）', MUT_ENT_TITLE_UNBOUND),\n"



    "    ('入口标记：未收录也给兜底坐标（反向对照失效）', MUT_ENT_FALLBACK_COORD),\n"



)



# ★ 新登记挂**列表头**：挂尾部会吃掉后续步骤锚（2026-09-24 实锤过 ⑫-b 抢 ⑬ 的锚点）。



_MUT_LIST_HEAD = "MUTATIONS = [\n"



if text.count(_MUT_LIST_HEAD) != 1:



    sys.exit('未找到 MUTATIONS 列表头（唯一性异常），上游可能已改动')



text = text.replace(



    _MUT_LIST_HEAD,



    "# ── 副本入口标记（2026-09-24 用户要求）──────────────────────────────────────\n"



    "# 详细说明见本文件生成器（mk_df_mut.py）的 ㉘ 步注释。\n"



    + _MUT_ENT_DEFS



    + "MUTATIONS = [\n"



    + _MUT_ENT_REG,



    1)



print('  %-40s -> %d 处' % ('副本入口标记变异 3 条（挂列表头）', 3))











# ── ㉙ 对照表整页搬到「营地系统 → 营地」（2026-09-24 用户要求）─────────────────



# 变异 ⑰-6 守的是「首页进不了营地·加成」；对照页现按用户口径整体挂到「营地」（camping）



# 名下、首页营地页签撤掉 —— 旧变异的锚点行已从 ProfessionUI.lua 消失，受检替换成新守护点：



# 「营地」页进不了对照页（camping 的 camp 页签被摘）。



_MUT_CAMP_OLD_DEF = (



    "MUT_PROF_INDEX_CAMP_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'    if slug == \"__index\" then return { \"overview\", \"camp\" } end\\n',\n"



    "    b'    if slug == \"__index\" then return { \"overview\" } end -- MUT: index camp gone\\n'))\n"



)



_MUT_CAMP_NEW_DEF = (



    "MUT_PROF_CAMPING_CAMP_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'    if slug == \"camping\" then out[#out + 1] = \"camp\" end\\n',\n"



    "    b'    -- MUT: camping camp tab gone\\n'))\n"



)



if 'MUT_PROF_CAMPING_CAMP_GONE' in text:



    sys.exit('㉙ 已应用过（幂等保护）')



if text.count(_MUT_CAMP_OLD_DEF) != 1:



    sys.exit('未找到（或不唯一）变异 ⑰-6 的定义块，上游可能已改动')



text = text.replace(_MUT_CAMP_OLD_DEF, _MUT_CAMP_NEW_DEF, 1)







_MUT_CAMP_OLD_REG = (



    "    ('专业页：首页进不了营地·加成（页签被摘）', MUT_PROF_INDEX_CAMP_GONE),\n")



_MUT_CAMP_NEW_REG = (



    "    ('专业页：营地页进不了对照（页签被摘）', MUT_PROF_CAMPING_CAMP_GONE),\n")



if text.count(_MUT_CAMP_OLD_REG) != 1:



    sys.exit('未找到（或不唯一）变异 ⑰-6 的登记行')



text = text.replace(_MUT_CAMP_OLD_REG, _MUT_CAMP_NEW_REG, 1)



if 'MUT_PROF_INDEX_CAMP_GONE' in text:



    sys.exit('旧变异名 MUT_PROF_INDEX_CAMP_GONE 仍有残留')



print('  %-40s -> %d 处' % ('㉙ 首页营地页签守护换到 camping', 1))











# ── ㉚ 斑马纹 2 条（2026-09-24 六轮）─────────────────────────────────────────



# 用户原话：「我想他支持斑马纹」。两条变异互为对照：



#   ①底纹 alpha 归零（静态分支还在、动态看不见 —— 证明动态断言真的在读 __bgA）；



#   ②行永远不落 __z（计数分支还在、但没有一行被画上底纹 —— 证明 _z > 0 那条守得住）。



# 目标 Core/ProfessionUI.lua 是手写骨架件、LF，锚点用 \n；片段全 ASCII。



_ZEBRA_MUT_DEFS = (



    "MUT_PROF_LV_ZEBRA_A0 = ('Core/ProfessionUI.lua', (\n"



    "    b'        r:SetBackdropColor(1, 1, 1, PD.ZEBRA_A)\\n',\n"



    "    b'        r:SetBackdropColor(1, 1, 1, 0) -- MUT: zebra invisible\\n'))\n"



    "\n"



    "MUT_PROF_LV_ZEBRA_ZGONE = ('Core/ProfessionUI.lua', (\n"



    "    b'    r.__z = spec.z and true or false\\n',\n"



    "    b'    r.__z = false -- MUT: never striped\\n'))\n"



    "\n"



)



_ZEBRA_DEF_ANCHOR = "MUTATIONS = [\n"



if _ZEBRA_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉚步），上游可能已改动')



if 'MUT_PROF_LV_ZEBRA_A0' in text:



    sys.exit('斑马纹变异已存在，不再重复登记（幂等保护）')



text = text.replace(_ZEBRA_DEF_ANCHOR, _ZEBRA_MUT_DEFS + _ZEBRA_DEF_ANCHOR, 1)



_ZEBRA_MUT_REGS = (



    "    # ㉚ 斑马纹（2026-09-24 六轮）\n"



    "    ('专业页：斑马纹底纹 alpha 归零（分支还在、看不见）', MUT_PROF_LV_ZEBRA_A0),\n"



    "    ('专业页：行永远不落 __z（没有一行被画上底纹）', MUT_PROF_LV_ZEBRA_ZGONE),\n"



)



text = text.replace(_ZEBRA_DEF_ANCHOR, _ZEBRA_DEF_ANCHOR + _ZEBRA_MUT_REGS, 1)



print('  %-40s -> %d 处' % ('㉚ 斑马纹变异定义+登记 2 条（挂列表头）', 2))











# ── ㉛ 副本入口指引点（2026-09-24 用户要求）──────────────────────────────────



# 领主大厅给两个坐标：航点落主点（副本入口 28.2,47.7），楼梯（44.2,52）是提示框里的指引行。



# 变异把 route 查找掐死 → 提示框少指引行、主点也不加「副本入口」前缀（用户要的两个坐标没了）。



# 锚点 = route 查找整行（全文件唯一），替换后语法合法（route=nil 走 or 短路，不崩提示框）。



_ENTR_ROUTE_MUT_DEFS = (



    "MUT_ENT_ROUTE_GONE = ('Core/DungeonUI.lua', (\n"



    "    b'        local route = d and ns.DungeonEntryRoute and ns.DungeonEntryRoute[d.id]\\r\\n',\n"



    "    b'        local route = nil -- MUT: entrance route points dropped\\r\\n'))\n"



    "\n"



)



_ENTR_ROUTE_DEF_ANCHOR = "MUTATIONS = [\n"



if _ENTR_ROUTE_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉛步），上游可能已改动')



if 'MUT_ENT_ROUTE_GONE' in text:



    sys.exit('入口指引点变异已存在，不再重复登记（幂等保护）')



text = text.replace(_ENTR_ROUTE_DEF_ANCHOR, _ENTR_ROUTE_MUT_DEFS + _ENTR_ROUTE_DEF_ANCHOR, 1)



_ENTR_ROUTE_REGS = (



    "    # ㉛ 副本入口指引点（2026-09-24 用户要求：领主大厅给楼梯 + 入口两个坐标）\n"



    "    ('入口指引：指引点丢失（提示框少了多段坐标行）', MUT_ENT_ROUTE_GONE),\n"



)



text = text.replace(_ENTR_ROUTE_DEF_ANCHOR, _ENTR_ROUTE_DEF_ANCHOR + _ENTR_ROUTE_REGS, 1)



print('  %-40s -> %d 处' % ('㉛ 入口指引点变异定义+登记 1 条（挂列表头）', 1))







# ── ㉜ 材料角标细描边（2026-09-24 用户要求：数量放大到 14 并加细描边）──────────



# 角标压在图标上，细描边 = 1px 阴影（hui 主题 FontFlags 恒 ""，阴影是双主题通用的描边替身）。



# 变异把阴影偏移归零 = 描边被摘（数字压在图标上又发虚）。锚带 4 空格缩进（注释里同文不命中）。



_CNT_EDGE_MUT_DEFS = (



    "MUT_PROF_LV_CNT_NOEDGE = ('Core/ProfessionUI.lua', (\n"



    "    b'    b.ct:SetShadowOffset(1, -1)\\n',\n"



    "    b'    b.ct:SetShadowOffset(0, 0) -- MUT: count badge edge dropped\\n'))\n"



    "\n"



)



_CNT_EDGE_DEF_ANCHOR = "MUTATIONS = [\n"



if _CNT_EDGE_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉜步），上游可能已改动')



if 'MUT_PROF_LV_CNT_NOEDGE' in text:



    sys.exit('材料角标细描边变异已存在，不再重复登记（幂等保护）')



text = text.replace(_CNT_EDGE_DEF_ANCHOR, _CNT_EDGE_MUT_DEFS + _CNT_EDGE_DEF_ANCHOR, 1)



_CNT_EDGE_REGS = (



    "    # ㉜ 材料角标细描边（2026-09-24 用户要求）\n"



    "    ('专业页：材料角标细描边被摘（压图标发虚）', MUT_PROF_LV_CNT_NOEDGE),\n"



)



text = text.replace(_CNT_EDGE_DEF_ANCHOR, _CNT_EDGE_DEF_ANCHOR + _CNT_EDGE_REGS, 1)



print('  %-40s -> %d 处' % ('㉜ 材料角标细描边变异定义+登记 1 条（挂列表头）', 1))







# ── ㉞ 材料角标粗描边（2026-09-24 用户要求：细描边不够明显 → 改 THICKOUTLINE）────



# 变异把旗标摘成 ""（角标只剩 1px 阴影，压图标发虚）。锚全 ASCII、LF、带 4 空格缩进



# （含 PD.TBL_MAT_CNT_FS 全文件唯一，不撞注释）。



_THICK_EDGE_MUT_DEFS = (



    "MUT_PROF_LV_CNT_NOTHICK = ('Core/ProfessionUI.lua', (\n"



    "    b'    b.ct:SetFont(ns.FONT, PD.TBL_MAT_CNT_FS, \"THICKOUTLINE\")\\n',\n"



    "    b'    b.ct:SetFont(ns.FONT, PD.TBL_MAT_CNT_FS, \"\") -- MUT: thick edge dropped\\n'))\n"



    "\n"



)



_THICK_EDGE_DEF_ANCHOR = "MUTATIONS = [\n"



if _THICK_EDGE_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉞步），上游可能已改动')



if 'MUT_PROF_LV_CNT_NOTHICK' in text:



    sys.exit('材料角标粗描边变异已存在，不再重复登记（幂等保护）')



text = text.replace(_THICK_EDGE_DEF_ANCHOR, _THICK_EDGE_MUT_DEFS + _THICK_EDGE_DEF_ANCHOR, 1)



_THICK_EDGE_REGS = (



    "    # ㉞ 材料角标粗描边（2026-09-24 用户要求）\n"



    "    ('专业页：材料角标粗描边被摘（THICKOUTLINE 回落无旗标）', MUT_PROF_LV_CNT_NOTHICK),\n"



)



text = text.replace(_THICK_EDGE_DEF_ANCHOR, _THICK_EDGE_DEF_ANCHOR + _THICK_EDGE_REGS, 1)



print('  %-40s -> %d 处' % ('㉞ 材料角标粗描边变异定义+登记 1 条（挂列表头）', 1))











# ── ㉝ 入口芯片序号（2026-09-24 用户定：标题右侧芯片按钮，一枚 = 一个可标记的点）──────



# 变异把芯片序号清零：点击芯片时 pts[0] 为 nil → 静默不落点，



# 「领主大厅点第 2 枚芯片 → 航点落楼梯 44.2,52」动态断言必须失败。



# 锚全 ASCII、CRLF、带 8 空格缩进（创建循环里唯一；OnClick 闭包读的是 self.__entIdx，不撞）。



_ENTCHIP_MUT_DEFS = (



    "MUT_ENT_CHIP_IDX0 = ('Core/DungeonUI.lua', (\n"



    "    b'        chip.__entIdx = i\\r\\n',\n"



    "    b'        chip.__entIdx = 0 -- MUT: chip index zeroed\\r\\n'))\n"



    "\n"



)



_ENTCHIP_DEF_ANCHOR = "MUTATIONS = [\n"



if _ENTCHIP_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉝步），上游可能已改动')



if 'MUT_ENT_CHIP_IDX0' in text:



    sys.exit('入口芯片变异已存在，不再重复登记（幂等保护）')



text = text.replace(_ENTCHIP_DEF_ANCHOR, _ENTCHIP_MUT_DEFS + _ENTCHIP_DEF_ANCHOR, 1)



_ENTCHIP_REGS = (



    "    # ㉝ 入口芯片（2026-09-24 用户定：标题右侧芯片，一枚 = 一个可标记的点）\n"



    "    ('入口芯片：芯片序号清零（点芯片不落点）', MUT_ENT_CHIP_IDX0),\n"



)



text = text.replace(_ENTCHIP_DEF_ANCHOR, _ENTCHIP_DEF_ANCHOR + _ENTCHIP_REGS, 1)



print('  %-40s -> %d 处' % ('㉝ 入口芯片变异定义+登记 1 条（挂列表头）', 1))











# ── ㉟ 全部专业总览三列宫格（2026-09-24 方案 B，用户拍板）──────────────────────────



# 目标文件 Core/ProfessionUI.lua 是手写骨架件、行尾 LF；锚全 ASCII（字节锚不许含中文）、



# 各带本行缩进取唯一（已逐条 grep -cF 验证恰好命中 1 次）。



# 每条对应 ⑰ 组断言：宫格没建 / 举手不亮 / 悬停兜底断线 / 指路尾注丢失。



_IX_MUT_DEFS = (



    "MUT_IX_GRID_BUILT = ('Core/ProfessionUI.lua', (\n"



    "    b'    PD.BuildIndexGrid(child)\\n',\n"



    "    b'    -- MUT: index grid never built\\n'))\n"



    "\n"



    "MUT_IX_GRID_RAISE = ('Core/ProfessionUI.lua', (\n"



    "    b'        PD.wantIndexGrid = (PD.cur == \"__index\")\\n',\n"



    "    b'        PD.wantIndexGrid = false -- MUT: never raised\\n'))\n"



    "\n"



    "MUT_IX_HOVER = ('Core/ProfessionUI.lua', (\n"



    "    b'            if over ~= c.__hlOn then PD.SetCardHover(c, over) end\\n',\n"



    "    b'            if over ~= c.__hlOn then PD.SetCardHover(c, false) end -- MUT\\n'))\n"



    "\n"



    "MUT_IX_NOTE_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'    PD.ixNote = MakeFS(root, 10, C_GREY, \"CENTER\")\\n',\n"



    "    b'    -- MUT: note gone\\n'))\n"



    "\n"



)



_IX_DEF_ANCHOR = "MUTATIONS = [\n"



if _IX_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉟步），上游可能已改动')



if 'MUT_IX_GRID_BUILT' in text:



    sys.exit('总览宫格变异已存在，不再重复登记（幂等保护）')



text = text.replace(_IX_DEF_ANCHOR, _IX_MUT_DEFS + _IX_DEF_ANCHOR, 1)



_IX_REGS = (



    "    # ㉟ 全部专业总览三列宫格（2026-09-24 方案 B）\n"



    "    ('总览宫格：Build 里的挂载被摘（宫格永不出现）', MUT_IX_GRID_BUILT),\n"



    "    ('总览宫格：举手恒 False（wantIndexGrid 永不亮）', MUT_IX_GRID_RAISE),\n"



    "    ('总览宫格：SyncHover 兜底断线（悬停失同步不自愈）', MUT_IX_HOVER),\n"



    "    ('总览宫格：指路尾注丢失（ixNote 不再建）', MUT_IX_NOTE_GONE),\n"



)



text = text.replace(_IX_DEF_ANCHOR, _IX_DEF_ANCHOR + _IX_REGS, 1)



print('  %-40s -> %d 处' % ('㉟ 总览宫格变异定义+登记 4 条（挂列表头）', 1))











# ── ㊱ 营地/军需官 → 地图标记（2026-09-24 用户：点军需官坐标标记 + 汉化）─────────────



# 锚全 ASCII、带缩进取唯一（军需官 act 只有这一处；营地 act 是另一形态）。



_CAMP_MUT_DEFS = (



    "MUT_CAMP_MARK_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'                act = function() PD.MarkCampPoint(vd[7], vd[5], vd[6]) end,\\n',\n"



    "    b'                act = function() end -- MUT: camp mark gone\\n'))\n"



    "\n"



)



_CAMP_DEF_ANCHOR = "MUTATIONS = [\n"



if _CAMP_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㊱步），上游可能已改动')



if 'MUT_CAMP_MARK_GONE' in text:



    sys.exit('营地标记变异已存在，不再重复登记（幂等保护）')



text = text.replace(_CAMP_DEF_ANCHOR, _CAMP_MUT_DEFS + _CAMP_DEF_ANCHOR, 1)



_CAMP_REGS = (



    "    # ㊱ 营地/军需官 → 地图标记（2026-09-24）\n"



    "    ('营地标记：军需官行落点被摘（点行不放航点）', MUT_CAMP_MARK_GONE),\n"



)



text = text.replace(_CAMP_DEF_ANCHOR, _CAMP_DEF_ANCHOR + _CAMP_REGS, 1)



print('  %-40s -> %d 处' % ('㊱ 营地标记变异定义+登记 1 条（挂列表头）', 1))











# ── ㊳ 职业加成对照总表 3 条（2026-09-24，方案 A 定稿：warcrafttavern 五列表）─────────



_BONTAB_MUT_DEFS = (



    # ㊳-1 举手被砍（表格永不出现 → 动态「对照总表就绪」断言抓）



    "MUT_BONTAB_OFF = ('Core/ProfessionUI.lua', (\n"



    "    b'            PD.wantBonusTable = true\\n',\n"



    "    b'            PD.wantBonusTable = false -- MUT: bonus table off\\n'))\n"



    "\n"



    # ㊳-2 对照列被清空（增益绿字消失 → 动态「绿字 >= 11」断言抓）



    "MUT_BONTAB_NOCMP = ('Core/ProfessionUI.lua', (\n"



    "    b'                r.cmp2:SetText(format(\"|cff7fdc7f%s|r\", buffTxt))\\n',\n"



    "    b'                r.cmp2:SetText(\"\") -- MUT: compare column emptied\\n'))\n"



    "\n"



    # ㊳-3 填表循环被砍（0 行 → 动态行数断言抓）



    "MUT_BONTAB_NOFILL = ('Core/ProfessionUI.lua', (\n"



    "    b'        local r = root.__rows[used + 1]\\n',\n"



    "    b'        local r = nil -- MUT: fill loop dropped\\n'))\n"



    "\n"



)



_BONTAB_DEF_ANCHOR = "MUTATIONS = [\n"



if _BONTAB_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㊳步），上游可能已改动')



if 'MUT_BONTAB_OFF' in text:



    sys.exit('对照总表变异已存在，不再重复登记（幂等保护）')



text = text.replace(_BONTAB_DEF_ANCHOR, _BONTAB_MUT_DEFS + _BONTAB_DEF_ANCHOR, 1)



_BONTAB_REGS = (



    "    # ㊳ 职业加成对照总表（2026-09-24）\n"



    "    ('加成总表：举手被砍（对照表不出现）', MUT_BONTAB_OFF),\n"



    "    ('加成总表：对照列被清空（增益绿字消失）', MUT_BONTAB_NOCMP),\n"



    "    ('加成总表：填表循环被砍（0 行）', MUT_BONTAB_NOFILL),\n"



)



text = text.replace(_BONTAB_DEF_ANCHOR, _BONTAB_DEF_ANCHOR + _BONTAB_REGS, 1)



print('  %-40s -> %d 处' % ('㊳ 加成对照总表变异定义+登记 3 条（挂列表头）', 1))







# ── ㊴ 探索页变异（2026-09-24 用户定）：顶栏第四颗「探索」接线守护 ──



# 目标文件 = 默认的 Core/DungeonUI.lua（CRLF，字节锚点）。中文「探索」按 RAID_TAB 同款



# 转义成 \xe 字节串写进生成的源码（b'' 里不直接落非 ASCII）。



#   ① 摘掉第四颗胶囊 → 动态「第四颗 key=Explore」「颗数分端 4/2」抓



#   ② SwitchSub 把 k = "Explore" 丢掉 → 动态「curSub = Explore」「探索页显示」抓



#   ③ Build 不挂 ExploreModule.Build → 动态「行池建满 40 本」抓



_EXPLORE_MUT_DEFS = (



    "MUT_EXPLORE_TAB_GONE = (\n"



    "    b'        defs[#defs + 1] = { key = \"Explore\", text = L[\"\\xe6\\x8e\\xa2\\xe7\\xb4\\xa2\"], width = DG.CAPSULE_W }\\r\\n',\n"



    "    b'        -- MUT: explore tab removed\\r\\n')\n"



    "\n"



    "MUT_EXPLORE_KEY_DROPPED = (\n"



    "    b'        k = \"Explore\"\\r\\n',\n"



    "    b'    -- MUT: explore switch dropped\\r\\n')\n"



    "\n"



    "MUT_EXPLORE_PAGE_GONE = (\n"



    "    b'        if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end\\r\\n',\n"



    "    b'        -- MUT: explore page build dropped\\r\\n')\n"



    "\n"



)



_EXPLORE_DEF_ANCHOR = "MUTATIONS = [\n"



if _EXPLORE_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㊴步），上游可能已改动')



if 'MUT_EXPLORE_TAB_GONE' in text:



    sys.exit('探索页变异已存在，不再重复登记（幂等保护）')



text = text.replace(_EXPLORE_DEF_ANCHOR, _EXPLORE_MUT_DEFS + _EXPLORE_DEF_ANCHOR, 1)



_EXPLORE_REGS = (



    "    # ㊴ 探索页（2026-09-24）\n"



    "    ('探索：顶栏第四颗被摘（入口消失）', MUT_EXPLORE_TAB_GONE),\n"



    "    ('探索：SwitchSub 把 Explore 丢掉（永远进不去探索页）', MUT_EXPLORE_KEY_DROPPED),\n"



    "    ('探索：Build 不挂 ExploreModule（行池空）', MUT_EXPLORE_PAGE_GONE),\n"



)



text = text.replace(_EXPLORE_DEF_ANCHOR, _EXPLORE_DEF_ANCHOR + _EXPLORE_REGS, 1)



print('  %-40s -> %d 处' % ('㊴ 探索页变异定义+登记 3 条（挂列表头）', 1))











# ── ㊵ 已学专业导航（2026-09-24 用户定：制皮 45/75 + 主题绿）──────────────────



# 三条各断一处：绿色被改灰（导航主题绿断言）/ 小字被清空（45/75 断言）/



# first-aid 映射被摘（急救 88/300 断言）。锚全 ASCII、LF、带原缩进防注释双命中。



_NAVLEARN_MUT_DEFS = (



    "MUT_NAV_LEARN_GREY = ('Core/ProfessionUI.lua', (\n"



    "    b'                bt:GetFontString():SetTextColor(NavAccent())\\n',\n"



    "    b'                bt:GetFontString():SetTextColor(Unpack(C_DIM)) -- MUT: learned green turned grey\\n'))\n"



    "\n"



    "MUT_NAV_LV_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'            bt.__lv:SetText(format(\"%d/%d\", lv.cur, lv.max))\\n',\n"



    "    b'            bt.__lv:SetText(\"\") -- MUT: learned level text dropped\\n'))\n"



    "\n"



    "MUT_NAV_SLUG_FA_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b'[129] = \"first-aid\",\\n',\n"



    "    b'[129] = nil, -- MUT: first-aid mapping dropped\\n'))\n"



    "\n"



)



_NAVLEARN_DEF_ANCHOR = "MUTATIONS = [\n"



if _NAVLEARN_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㊵步），上游可能已改动')



if 'MUT_NAV_LEARN_GREY' in text:



    sys.exit('已学专业导航变异已存在，不再重复登记（幂等保护）')



text = text.replace(_NAVLEARN_DEF_ANCHOR, _NAVLEARN_MUT_DEFS + _NAVLEARN_DEF_ANCHOR, 1)



_NAVLEARN_REGS = (



    "    # ㊵ 已学专业导航（2026-09-24 用户定）\n"



    "    ('专业页：已学导航主题绿被改灰', MUT_NAV_LEARN_GREY),\n"



    "    ('专业页：已学导航「当前/上限」小字被清空', MUT_NAV_LV_GONE),\n"



    "    ('专业页：first-aid skillLine 映射被摘', MUT_NAV_SLUG_FA_GONE),\n"



)



text = text.replace(_NAVLEARN_DEF_ANCHOR, _NAVLEARN_DEF_ANCHOR + _NAVLEARN_REGS, 1)



print('  %-40s -> %d 处' % ('㊵ 已学专业导航变异定义+登记 3 条（挂列表头）', 1))











# ── ㊶ 已过段落灰显（2026-09-29 用户定：制皮 42 → 「1 – 15」整段灰、图标也灰）────



# 两条各断一处：passed 判定被关（灰显断言 + spec 断言全哑）/ 图标去饱和被摘（静态钉）。



# 锚全 ASCII、LF、带原缩进防注释双命中。



_LVPASSED_MUT_DEFS = (



    "MUT_LV_PASSED_OFF = ('Core/ProfessionUI.lua', (\n"



    "    b\"            local passed = (greyOn and over) or nil\\n\",\n"



    "    b\"            local passed = nil -- MUT: passed grey disabled\\n\"))\n"



    "\n"



    "MUT_LV_PASSED_NOICON = ('Core/ProfessionUI.lua', (\n"



    "    b\"        r.icon:SetDesaturated(spec.passed and true or false)\\n\",\n"



    "    b\"        r.icon:SetDesaturated(false) -- MUT: icon desaturate dropped\\n\"))\n"



    "\n"



)



_LVPASSED_DEF_ANCHOR = "MUTATIONS = [\n"



if _LVPASSED_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㊶步），上游可能已改动')



if 'MUT_LV_PASSED_OFF' in text:



    sys.exit('已过段落灰显变异已存在，不再重复登记（幂等保护）')



text = text.replace(_LVPASSED_DEF_ANCHOR, _LVPASSED_MUT_DEFS + _LVPASSED_DEF_ANCHOR, 1)



_LVPASSED_REGS = (



    "    # ㊶ 已过段落灰显（2026-09-29 用户定）\n"



    "    ('专业页：已过段落灰显被关掉（passed 恒 nil）', MUT_LV_PASSED_OFF),\n"



    "    ('专业页：已过段落图标不再去饱和', MUT_LV_PASSED_NOICON),\n"



)



text = text.replace(_LVPASSED_DEF_ANCHOR, _LVPASSED_DEF_ANCHOR + _LVPASSED_REGS, 1)



print('  %-40s -> %d 处' % ('㊶ 已过段落灰显变异定义+登记 2 条（挂列表头）', 1))











# ── ㉔ 专业页设置 + 当前段落外框（2026-09-29 用户定）────



# 四条各断一处：默认值被翻 / cur 举手被摘 / 上边条永隐 / 设置页不可达。



# 锚全 ASCII、LF、带原缩进防注释双命中。



_PROFSET_MUT_DEFS = (



    "MUT_PROF_SET_GREY_DEF = ('Core/ProfessionUI.lua', (\n"



    "    b\"PD.SETTING_DEF = { greyPassed = true, hlCurrent = true }\\n\",\n"



    "    b\"PD.SETTING_DEF = { greyPassed = false, hlCurrent = true } -- MUT: default flipped\\n\"))\n"



    "\n"



    "MUT_PROF_SET_CUR_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b\"                spec.cur = true\\n\",\n"



    "    b\"                do end -- MUT: current-segment mark gone\\n\"))\n"



    "\n"



    "MUT_PROF_SET_BORDER_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b\"    r.bT:SetShown(show)\\n\",\n"



    "    b\"    r.bT:SetShown(false) -- MUT: border strip never shown\\n\"))\n"



    "\n"



    "MUT_PROF_SET_PAGE_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b\"        PD.RowsSettings(rows)\\n\",\n"



    "    b\"        -- MUT: settings page unreachable\\n\"))\n"



    "\n"



    "MUT_PROF_SET_TOG_GONE = ('Core/ProfessionUI.lua', (\n"



    "    b\"            tg.__key = spec.togKey\\n\",\n"



    "    b\"            do end -- MUT: toggle unbound\\n\"))\n"



    "\n"



)



_PROFSET_DEF_ANCHOR = "MUTATIONS = [\n"



if _PROFSET_DEF_ANCHOR not in text:



    sys.exit('未找到 MUTATIONS 定义处（第㉔步），上游可能已改动')



if 'MUT_PROF_SET_GREY_DEF' in text:



    sys.exit('专业页设置变异已存在，不再重复登记（幂等保护）')



text = text.replace(_PROFSET_DEF_ANCHOR, _PROFSET_MUT_DEFS + _PROFSET_DEF_ANCHOR, 1)



_PROFSET_REGS = (



    "    # ㉔ 专业页设置 + 当前段落外框（2026-09-29 用户定）\n"



    "    ('专业页：灰显开关默认值被翻成关', MUT_PROF_SET_GREY_DEF),\n"



    "    ('专业页：当前段不再被标记（外框永不亮）', MUT_PROF_SET_CUR_GONE),\n"



    "    ('专业页：外框上边条永不显示（框缺一条）', MUT_PROF_SET_BORDER_GONE),\n"



    "    ('专业页：设置页不可达（齿轮点了没反应）', MUT_PROF_SET_PAGE_GONE),\n"



    "    ('专业页：iOS 开关不再绑定设置键（点了也写不进 DB）', MUT_PROF_SET_TOG_GONE),\n"



)



text = text.replace(_PROFSET_DEF_ANCHOR, _PROFSET_DEF_ANCHOR + _PROFSET_REGS, 1)



print('  %-40s -> %d 处' % ('㉔ 专业页设置变异定义+登记 4 条（挂列表头）', 1))











# ===========================================================================
# ㉕ 副本攻略页 · 卡片式版面（2026-09-29 用户定「4 个卡片、两列、极简描边」）
# ===========================================================================

_GUIDE_MUT_DEFS = (
    "MUT_GUIDE_TAB_GONE = (\n"
    "    b', { key = \"guide\", text = L[\"\\xe6\\x94\\xbb\\xe7\\x95\\xa5\"] } }',\n"
    "    b' }')\n"
    "\n"
    "MUT_GUIDE_DISPATCH_LOOT = (\n"
    "    b'        U:RenderDungeonGuide()\\r\\n',\n"
    "    b'        U:RenderDungeonLoot() -- MUT: guide tab renders loot\\r\\n')\n"
    "\n"
    "MUT_GUIDE_KEEP_SCROLL = (\n"
    "    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest and not isGuide) end\\r\\n',\n"
    "    b'    if U.dungeonDetailScroll then U.dungeonDetailScroll:SetShown(not isQuest) end -- MUT\\r\\n')\n"
    "\n"
    "MUT_GUIDE_BOSSNAME_LITERAL = (\n"
    "    b'            if loot[i][1] == en then return loot[i][2] or en end\\r\\n',\n"
    "    b'            if loot[i][1] == en then return en end -- MUT: english key leaks to UI\\r\\n')\n"
    "\n"
    "MUT_GUIDE_NO_EQUAL_H = (\n"
    "    b'        if b and b.h > rh then rh = b.h end\\r\\n',\n"
    "    b'        -- MUT: row height not maxed (taller card gets squeezed)\\r\\n')\n"
    "\n"
    "MUT_GUIDE_TOP_GAP = (\n"
    "    b'    local top, i = 0, 1\\r\\n',\n"
    "    b'    local top, i = -14, 1 -- MUT: cards pushed down, tagline band kept\\r\\n')\n"
    "\n"
    "MUT_GUIDE_TAGLINE_GONE = (\n"
    "    b'            if g.tagline then\\r\\n'\n"
    "    b'                rows[#rows + 1] = { t = \"\\xc2\\xb7 \" .. g.tagline, c = C_TEXT, x = 0, gap = 5 }\\r\\n'\n"
    "    b'            end\\r\\n',\n"
    "    b'            -- MUT: tagline row dropped (not merged into tips)\\r\\n')\n"
    "\n"
    "MUT_GUIDE_TOP_BACK = (\n"
    "    b'    gscroll:SetPoint(\"TOPLEFT\", detail, \"TOPLEFT\", 0, -DG.GUIDE_TOP_Y)\\r\\n',\n"
    "    b'    gscroll:SetPoint(\"TOPLEFT\", detail, \"TOPLEFT\", 0, -DG.SCROLL_Y) -- MUT: filter band gap back\\r\\n')\n"
    "\n"
    "MUT_GUIDE_SIDE_GONE = (\n"
    "    b'        a.frame:SetPoint(\"TOPLEFT\", child, \"TOPLEFT\", DG.GUIDE_SIDE, top)\\r\\n',\n"
    "    b'        a.frame:SetPoint(\"TOPLEFT\", child, \"TOPLEFT\", 0, top) -- MUT: left margin gone\\r\\n')\n"
    "\n"
)

_GUIDE_DEF_ANCHOR = "MUTATIONS = [\n"

if _GUIDE_DEF_ANCHOR not in text:
    sys.exit('未找到 MUTATIONS 定义处（第㉕步），上游可能已改动')

text = text.replace(_GUIDE_DEF_ANCHOR, _GUIDE_MUT_DEFS + _GUIDE_DEF_ANCHOR, 1)

_GUIDE_REGS = (
    "    # ㉕ 副本攻略页 卡片式版面（2026-09-29 用户定「4 个卡片、两列、极简描边」）\n"
    "    ('攻略：页签「攻略」被摘（入口消失）', MUT_GUIDE_TAB_GONE),\n"
    "    ('攻略：点攻略渲染成掉落页（分派串线）', MUT_GUIDE_DISPATCH_LOOT),\n"
    "    ('攻略：掉落滚动区不让位（两层叠着显示）', MUT_GUIDE_KEEP_SCROLL),\n"
    "    ('攻略：BOSS 名不再反查（英文键漏到界面）', MUT_GUIDE_BOSSNAME_LITERAL),\n"
    "    ('攻略：卡片行高不取行内较高者（高卡被压矮）', MUT_GUIDE_NO_EQUAL_H),\n"
    "    ('攻略：卡片被推下（顶部又留出定位语空档）', MUT_GUIDE_TOP_GAP),\n"
    "    ('攻略：定位语不再并入「副本须知」首条', MUT_GUIDE_TAGLINE_GONE),\n"
    "    ('攻略：滚动区顶退回筛选行位（横幅间距又变 42）', MUT_GUIDE_TOP_BACK),\n"
    "    ('攻略：左留白被清零（左右又不对称）', MUT_GUIDE_SIDE_GONE),\n"
    "\n"
)

text = text.replace(_GUIDE_DEF_ANCHOR, _GUIDE_DEF_ANCHOR + _GUIDE_REGS, 1)

print('  %-40s -> %d 处' % ('㉕ 攻略页卡片变异定义+登记 5 条（挂列表头）', 1))

# ㊚ 行内锚点风格 helpers（2026-10-07 固化进生成物）
#   旧生成物里这两个函数是手补的，重跑 mk_df_mut.py 会丢 → check_mut_anchors /
#   _mut_isolate 直接 AttributeError。现固化为生成链的一步，幂等（有了就不再插）。
_MUT_HELPERS = (
    "def file_is_crlf(data):\n"
    "    cr = data.count(b'\\r\\n')\n"
    "    return cr > 0 and data.count(b'\\n') == cr\n"
    "\n"
    "def to_file_style(anchor, data):\n"
    "    if file_is_crlf(data):\n"
    "        return anchor.replace(b'\\r\\n', b'\\n').replace(b'\\n', b'\\r\\n')\n"
    "    return anchor.replace(b'\\r\\n', b'\\n')\n"
    "\n"
    "\n"
)

# ── ㊾ 升级行提示框改版（2026-10-09 用户）────────────────────────────
_LVTIP_MUT_DEFS = (
    "# ㊾ 升级行提示框改版（2026-10-09 用户）：「每行有个鼠标提示框，这个提示框不要了，\n"
    "#   改成当我们移动到制作物或需求材料的上方时，显示该物品的鼠标提示框。注意，这个\n"
    "#   提示框不使用我们的主题」。守护点：① 行级 noTip 短路不许退回；② 制作物热区必须\n"
    "#   挂产物 itemID 且盖住「图标 + 名称列」；③ 材料热区必须挂该材料 id；④ 两处热区都\n"
    "#   要转发滚轮（否则压在热区上整页滚不动）；⑤ 行池跨页复用时热区必须收起。\n"
    "MUT_LVTIP_ROW_TIP_BACK = ('Core/ProfessionUI.lua', (\n"
    "    b'                noTip = true,\\n',\n"
    "    b'                -- MUT: row-level segment tooltip back\\n'))\n"
    "MUT_LVTIP_ICONZONE_NOIT = ('Core/ProfessionUI.lua', (\n"
    "    b'        iz.__it = itemID and { itemID } or nil\\n',\n"
    "    b'        iz.__it = nil -- MUT: craft-product tooltip never fires\\n'))\n"
    "MUT_LVTIP_ICONZONE_NARROW = ('Core/ProfessionUI.lua', (\n"
    "    b'        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)\\n',\n"
    "    b'        iz:SetSize(PD.TBL_ICON, h) -- MUT: hotspot covers the icon only\\n'))\n"
    "MUT_LVTIP_MATZONE_NOIT = ('Core/ProfessionUI.lua', (\n"
    "    b'    b.zone.__it = { blk.id }\\n',\n"
    "    b'    b.zone.__it = nil -- MUT: material tooltip never fires\\n'))\n"
    "MUT_LVTIP_ZONE_NOWHEEL = ('Core/ProfessionUI.lua', (\n"
    "    b'    z:SetScript(\"OnMouseWheel\", function(self, delta)\\n'\n"
    "    b'        DG.WheelScroll(PD.scroll, PD.child, delta)\\n'\n"
    "    b'    end)\\n',\n"
    "    b'    z:SetScript(\"OnMouseWheel\", function(self, delta)\\n'\n"
    "    b'        do end -- MUT: wheel swallowed (page unscrollable over hotspots)\\n'\n"
    "    b'    end)\\n'))\n"
    "MUT_LVTIP_ICONZONE_KEEPSHOWN = ('Core/ProfessionUI.lua', (\n"
    "    b'    if r.__iconZone then r.__iconZone:Hide() end\\n',\n"
    "    b'    -- MUT: hotspot not collapsed on rebind (invisible zone eats the mouse)\\n'))\n"
    "MUT_LVTIP_MATZONE_KEEPSHOWN = ('Core/ProfessionUI.lua', (\n"
    "    b'        if b.zone then b.zone:Hide() end\\n',\n"
    "    b'        do end -- MUT: material hotspot not collapsed in ClearMats\\n'))\n"
    "\n"
)


_LVTIP_REGS = (
    "    # ㊾ 升级行提示框改版（2026-10-09 用户）\n"
    "    ('升级行：行级提示框又长回来（整段说明复辟）', MUT_LVTIP_ROW_TIP_BACK),\n"
    "    ('升级行：制作物热区不挂产物 id（悬停没提示框）', MUT_LVTIP_ICONZONE_NOIT),\n"
    "    ('升级行：制作物热区只盖图标（名称列悬停不了）', MUT_LVTIP_ICONZONE_NARROW),\n"
    "    ('升级行：材料热区不挂材料 id（悬停没提示框）', MUT_LVTIP_MATZONE_NOIT),\n"
    "    ('升级行：热区吞滚轮（压在热区上整页滚不动）', MUT_LVTIP_ZONE_NOWHEEL),\n"
    "    ('升级行：行池复用不收起制作物热区（透明热区吞鼠标）', MUT_LVTIP_ICONZONE_KEEPSHOWN),\n"
    "    ('升级行：ClearMats 不收起材料热区（切页留透明热区）', MUT_LVTIP_MATZONE_KEEPSHOWN),\n"
)


_LVTIP_DEF_ANCHOR = "MUTATIONS = [\n"
if _LVTIP_DEF_ANCHOR not in text:
    sys.exit('未找到 MUTATIONS 列表头，上游可能已改动')
if 'MUT_LVTIP_ROW_TIP_BACK' in text:
    print('  %-40s -> 已存在，跳过' % ('㊾ 升级行提示框改版'))
else:
    text = text.replace(_LVTIP_DEF_ANCHOR, _LVTIP_MUT_DEFS + _LVTIP_DEF_ANCHOR, 1)
    text = text.replace(_LVTIP_DEF_ANCHOR, _LVTIP_DEF_ANCHOR + _LVTIP_REGS, 1)
    print('  %-40s -> 定义 + 登记各 %d 处' % ('㊾ 升级行提示框改版', 1))
_HELPER_ANCHOR = "def split_spec(spec):"
if 'def to_file_style' not in text:
    if _HELPER_ANCHOR not in text:
        sys.exit('未找到 split_spec 定义处，上游可能已改动')
    text = text.replace(_HELPER_ANCHOR, _MUT_HELPERS + _HELPER_ANCHOR, 1)
    print('  %-40s -> %d 处' % ('㊚ 锚点风格 helpers（file_is_crlf/to_file_style）', 1))
else:
    print('  %-40s -> 已存在，跳过' % '㊚ 锚点风格 helpers')


# 残留自检



for kw in ('TalentsForever', 'Sim.lua', 'MUT_COMPARE_GONE', 'MUT_QUAL_PREWARM'):



    if kw in text:



        bad = [l for l in text.split('\n') if kw in l][:3]



        sys.exit('残留 %s：\n  %s' % (kw, '\n  '.join(bad)))







if 'Core/DungeonUI.lua' not in text:



    sys.exit('默认变异目标未改到 DungeonUI.lua')







# ── 安全闸（2026-10-09）──────────────────────────────────────────────────
# ⚠️ 本生成器**已经落后于产物**：df_mut_check.py 里有一批手加的变异（㉘ 配方搜索、
#    ㉚ 专业页大列表分帧…）在生成器里**没有对应步骤** —— 直接重跑会把它们连同它们的
#    断言一起**静默删掉**（实测：会丢 MUT_SEARCH_FILTER_GONE 等 ㉘ 整块）。
#    所以默认拒绝覆盖：确要重跑，先把生成器补平，再设 DF_MUT_ALLOW_REGEN=1。
#
# ⚠️ 2026-10-09 追加：上游 mut_dungeon_check.py 的 `main()` 里那段「注入 + 判据」是**旧口径**，
#    本生成器只把 `to_file_style` 注进了产物、**没让那段循环用它**，于是产物里
#    `data.count(old) != 1` 对 CRLF 产物恒 0 → 明明合法的锚点被误判「不存在」，
#    main() 每次在图里第一条这种变异上 `return 2`（这条路径一直是死的）。
#    ⇒ **重跑本生成器后，必须紧接着跑一次 `python _temp/patch_mut_main_fix.py`**
#      （幂等；把锚点口径 / 烂锚只跳过 / 基线差集 / 脏抓判据一起补回来），
#      再跑 `python _temp/check_mut_anchors.py` 复检。
import os as _os
import re as _re

if _os.environ.get('DF_MUT_ALLOW_REGEN') != '1':
    _cur = open(DST, encoding='utf-8').read() if _os.path.exists(DST) else ''
    _lost = sorted(set(_re.findall(r'^(MUT_[A-Z0-9_]+)\s*=', _cur, _re.M))
                   - set(_re.findall(r'^(MUT_[A-Z0-9_]+)\s*=', text, _re.M)))
    if _lost:
        sys.exit('拒绝覆盖 %s：产物里有 %d 条生成器不认识的变异会被删掉：\n  %s\n'
                 '（先把它们补进本生成器；确要强行覆盖：DF_MUT_ALLOW_REGEN=1）'
                 % (DST, len(_lost), '\n  '.join(_lost)))

open(DST, 'w', encoding='utf-8', newline='\n').write(text)



print('已生成 %s（%d 行）' % (DST, text.count('\n') + 1))

# -*- coding: utf-8 -*-
"""从上游 TalentsForever 的 tf_dungeon_check.py 派生 DungeonsForever 的副本页回归检查。

改动面（有意压到最小，其余 1901 行断言逐字不动）：
  ① 路径：beta 目标目录 / TOC 名 / Core/UI.lua → Core/DungeonUI.lua
  ② 导出名：TF_NS.TalentSimUI → TF_NS.DungeonUI（页面控制器）；
            TF_NS.DungeonUI  → TF_NS.DungeonModule（副本模块工具表，原名让位给控制器）
  ③ 删掉「/tf qual、/tf item」整段（那是天赋模拟器 Core/Sim.lua 的命令族，
     本插件没有 Sim.lua）；simall 随之置空 —— 剩余的同名断言由 uiall 覆盖。
  ④ 标题文案。

用法：python mk_df_check.py  → 生成 df_dungeon_check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(os.path.dirname(DF), 'TalentsForever', '_temp', 'tf_dungeon_check.py')
DST = os.path.join(HERE, 'df_dungeon_check.py')

text = open(SRC, encoding='utf-8').read()

# ── ③ 删除上游 Sim.lua 命令族断言段 ──────────────────────────────────────────
START = '    # ---- /tf qual 必须主动预热 ----'
END = "       '已到货 %d / %d 件' in sim)\n"
if START not in text:
    sys.exit('未找到 Sim 断言段的起点，上游可能已改动')
i = text.index(START)
j = text.index(END, i) + len(END)
text = text[:i] + (
    '    # （上游此处有「/tf qual、/tf item 命令族」的一组断言，依赖 Core/Sim.lua。\n'
    '    #   本插件没有模拟器模块，故整段不搬；物品取数路径的不变量仍由\n'
    '    #   上面的 DG.RequestItem / DG.EnsureItemListener 断言与动态段覆盖。）\n'
    '\n'
) + text[j:]

# ── simall 置空：Sim.lua 不存在，全文件级检查只剩 uiall（= DungeonUI.lua）──────
OLD_SIMALL = "simall = '\\n'.join(l.split('--')[0] for l in sim.split('\\n'))"
if OLD_SIMALL not in text:
    sys.exit('未找到 simall 赋值，上游可能已改动')
text = text.replace(OLD_SIMALL, "simall = ''  # 本插件无 Core/Sim.lua；全文件级检查由 uiall 承担")

# ── ② 导出名 ────────────────────────────────────────────────────────────────
# ⚠️ 顺序是坑：不能先「TalentSimUI → DungeonUI」再「DungeonUI → DungeonModule」——
#    第二步会连刚改出来的那个也一起改掉（TF_NS.DungeonUI 全部 → DungeonModule），
#    结果 U 取到的是 DG 表（没有 Build 方法），动态段首句就 "attempt to call method
#    'Build' (a nil value)"。必须先把**原有**的 DungeonUI 换成占位符。
PLACEHOLDER = '@@DG_TABLE@@'
n0 = text.count('TF_NS.DungeonUI')
if not n0:
    sys.exit('替换未命中：TF_NS.DungeonUI')
text = text.replace('TF_NS.DungeonUI', PLACEHOLDER)
print('  %-28s → %-28s %d 处（占位保护）' % ('TF_NS.DungeonUI', PLACEHOLDER, n0))

REPL = [
    ('TF_NS.TalentSimUI', 'TF_NS.DungeonUI'),
    ('ns.TalentSimUI 不存在', 'ns.DungeonUI 不存在'),
    (PLACEHOLDER, 'TF_NS.DungeonModule'),
]
for old, new in REPL:
    n = text.count(old)
    if not n:
        sys.exit('替换未命中：%s' % old)
    text = text.replace(old, new)
    print('  %-28s → %-28s %d 处' % (old, new, n))

# ── ⑤ 分段标记换新（上游 Core 有「---- 构建 ----」分隔注释，DF 的 DungeonUI 在
#   懒构建重构后已无此注释；按 DF 现存函数边界替换，语义不变）：
#   · static_guard 的「DG 整段无 SetParent(nil)」→ 段尾改 U:ShowDungeonDetail 定义处；
#   · 掉落卡片墙段 → 段尾改 U:RenderDungeonLootCards 定义处。
OLD_SEG_GUARD = ("src[src.index('local DG = {}'):"
                 "src.index('-------------------- 构建 --------------------')]")
NEW_SEG_GUARD = "src[src.index('local DG = {}'):src.index('function U:ShowDungeonDetail(d)')]"
OLD_SEG_CARDS = ("src[src.index('function U:RenderDungeonLoot'):"
                 "src.index('-------------------- 构建 --------------------')]")
NEW_SEG_CARDS = ("src[src.index('function U:RenderDungeonLoot'):"
                 "src.index('function U:RenderDungeonLootCards')]")
# 取数口自适应段：上游以「-- 品质取值：」注记收尾，DF 无 → 改到 NsCall 定义处
# （DF 的 ItemInfo + ItemInfoInstant 两取数口正好落在 DG.ItemInfo → DG.NsCall 之间）
OLD_SEG_API = "src[src.index('function DG.ItemInfo'):src.index('-- 品质取值：')]"
NEW_SEG_API = "src[src.index('function DG.ItemInfo'):src.index('function DG.NsCall')]"
# NsCall 函数体段：上游以「-- 物品名：」注记收尾，DF 无 → 改到 ContinueOnItemLoad 定义处
OLD_SEG_NSC = "src[src.index('function DG.NsCall'):src.index('-- 物品名：')]"
NEW_SEG_NSC = "src[src.index('function DG.NsCall'):src.index('function DG.ContinueOnItemLoad')]"
# 任务取数段：上游以「副本任务：客户端取数口」横幅开头，DF 无 → 改从 QLCall 定义处起
# （QLCall → U:Build() 之间含任务快照/事件/渲染全部锚点，且无 SetParent/SetScrollChild）
OLD_SEG_QUEST = "src.index('-------------------- 副本任务：客户端取数口 --------------------')"
NEW_SEG_QUEST = "src.index('function DG.QLCall(name, id)')"
for _o, _n in ((OLD_SEG_GUARD, NEW_SEG_GUARD), (OLD_SEG_CARDS, NEW_SEG_CARDS),
               (OLD_SEG_API, NEW_SEG_API), (OLD_SEG_NSC, NEW_SEG_NSC),
               (OLD_SEG_QUEST, NEW_SEG_QUEST)):
    if _o not in text:
        sys.exit('未找到待换的分段标记（上游可能已改动）：%s' % _o[:60])
    text = text.replace(_o, _n)
    print('  分段标记 → %s' % _n[-46:])

# ── ⑥ TOC 行内注记剥离：DF 的 TOC 有「Locales\zhTW.lua [AllowLoadTextLocale zhTW]」
#   这类行尾方括号注记（真客户端按注记限定加载），上游解析器不认 → 注记会被并进
#   rel 使 loadfile 恒 nil。剥离行尾 [ ... ] 再入 files。
OLD_FILES = ("    files = [l.strip().replace('\\\\', '/') for l in toc.splitlines()\n"
             "             if l.strip() and not l.strip().startswith('##')]")
NEW_FILES = ("    import re as _re\n"
             "    files = [_re.sub(r'\\s*\\[[^\\]]*\\]\\s*$', '', l.strip()).replace('\\\\', '/')\n"
             "            for l in toc.splitlines()\n"
             "            if l.strip() and not l.strip().startswith('##')]")
if OLD_FILES not in text:
    sys.exit('未找到 TOC files 解析段（上游可能已改动）')
text = text.replace(OLD_FILES, NEW_FILES)
print('  TOC 行内注记剥离 → 已接入')

# ── ④ 地图标记断言分端化 ─────────────────────────────────────────────────────
# 地图标记（用户航点）只有无限客户端（1.60.x）支持：泰坦端 DG.MarkNPC 走
# 「地图标记仅无限客户端支持」分支、**不**落航点。上游 harness 无条件断言落航点，
# 于是泰坦端恒 3 项失败（既有失败，设计使然）。派生版按端号分开断言：
# 无限端要求落航点 + 开图；泰坦端要求「不落航点」。两端都成为真断言。
IS_FOREVER_OLD = (
    "    local U = TF_NS.DungeonUI\n"
    "    if U == nil then ck(\"ns.DungeonUI 不存在\", false) return end\n"
)
if IS_FOREVER_OLD not in text:
    sys.exit('未找到 LUA_SCRIPT 的 U 取用处，上游可能已改动')
text = text.replace(
    IS_FOREVER_OLD,
    "    local U = TF_NS.DungeonUI\n"
    "    -- ㉒ iOS 开关桩：真 ReskinToggle 在桩 CheckButton 上会炸（万能壳把缺失键 Text 现造成\n"
    "    -- function，真件预期 nil）。开关视觉全由 hui 托管、harness 不断言皮，覆盖为 no-op。\n"
    "    if TF_NS and TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end\n"
    "    local IS_FOREVER = TF_NS.IsForever == true   -- 地图标记分端断言的开关\n"
    "    if U == nil then ck(\"ns.DungeonUI 不存在\", false) return end\n",
    1)

MARK_OLD = '''      if npcRow and npcRow.__scripts and npcRow.__scripts.OnClick then
        npcRow.__scripts.OnClick(npcRow)
        ck("★ 点起始行 → SetUserWaypoint 收到 UiMapPoint（x/y 已 /100）",
           C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == TF_NS.NPCLoc[markQ[16]][1]
           and C_MAP_MARK.wp.x == TF_NS.NPCLoc[markQ[16]][2] / 100
           and C_MAP_MARK.wp.y == TF_NS.NPCLoc[markQ[16]][3] / 100,
           tostring(C_MAP_MARK.wp and C_MAP_MARK.wp.uiMapID))
        ck("★ 点起始行 → OpenWorldMap 打开 NPC 所在地图",
           C_MAP_MARK.opened == TF_NS.NPCLoc[markQ[16]][1], tostring(C_MAP_MARK.opened))
      else'''
MARK_NEW = '''      if npcRow and npcRow.__scripts and npcRow.__scripts.OnClick then
        npcRow.__scripts.OnClick(npcRow)
        -- ★ 分端断言（派生版新增）：地图标记只有无限端支持，泰坦端不该落航点
        if IS_FOREVER then
          ck("★ 点起始行 → SetUserWaypoint 收到 UiMapPoint（x/y 已 /100）",
             C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == TF_NS.NPCLoc[markQ[16]][1]
             and C_MAP_MARK.wp.x == TF_NS.NPCLoc[markQ[16]][2] / 100
             and C_MAP_MARK.wp.y == TF_NS.NPCLoc[markQ[16]][3] / 100,
             tostring(C_MAP_MARK.wp and C_MAP_MARK.wp.uiMapID))
          ck("★ 点起始行 → OpenWorldMap 打开 NPC 所在地图",
             C_MAP_MARK.opened == TF_NS.NPCLoc[markQ[16]][1], tostring(C_MAP_MARK.opened))
        else
          ck("★ 泰坦端点起始行不落航点（地图标记仅无限客户端支持）",
             C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil)
        end
      else'''
if MARK_OLD not in text:
    sys.exit('未找到起始行航点断言，上游可能已改动')
text = text.replace(MARK_OLD, MARK_NEW, 1)

NODE_OLD = '''        C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
        hitNode.__scripts.OnClick(hitNode)
        ck("★ 点链节点 → 航点指向该环起始 NPC 的地图",
           C_MAP_MARK.opened == TF_NS.NPCLoc[hitNode.__npc][1], tostring(C_MAP_MARK.opened))'''
NODE_NEW = '''        C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
        hitNode.__scripts.OnClick(hitNode)
        if IS_FOREVER then
          ck("★ 点链节点 → 航点指向该环起始 NPC 的地图",
             C_MAP_MARK.opened == TF_NS.NPCLoc[hitNode.__npc][1], tostring(C_MAP_MARK.opened))
        else
          ck("★ 泰坦端点链节点不落航点", C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil)
        end'''
if NODE_OLD not in text:
    sys.exit('未找到链节点航点断言，上游可能已改动')
text = text.replace(NODE_OLD, NODE_NEW, 1)

# ── ⑤ 补一条静态断言：门禁必须写在代码里 ──────────────────────────────────────
# 上一条动态断言在泰坦端只证明「没落航点」，不证明「为什么不落」。
# 这条把正当性钉在代码上：DG.MarkNPC 里必须有端号门禁 + 明确提示文案。
STATIC_ANCHOR = (
    "    ck('★★ 提示框活代码不出现「站点」/「掉率」字样',\n"
    "       '站点' not in tipcode and '掉率' not in tipcode)\n"
)
if STATIC_ANCHOR not in text:
    sys.exit('未找到静态断言插入锚点，上游可能已改动')
text = text.replace(
    STATIC_ANCHOR,
    STATIC_ANCHOR
    + "    marca = src[src.index('function DG.MarkNPC'):src.index('function DG.ShowNpcTip')]\n"
    + "    marcacode = '\\n'.join(l.split('--')[0] for l in marca.split('\\n'))\n"
    + "    ck('★ 地图标记有端号门禁（非无限端不静默失败，明确提示）',\n"
    + "       'GetBuildInfo()' in marcacode and '16999' in marcacode\n"
    + "       and '地图标记仅无限客户端支持' in marcacode)\n",
    1)

# ── ⑦ 补「跨插件命名空间」不变式（2026-09-23 实机事故）─────────────────────────
# 事故链：副本段从 upstream UI.lua 抄来了两个**裸全局函数**
#   BuildDungeons / BuildDungeonOverview；上游同名文件也定义这两个全局。
#   WoW 按文件夹名字母序加载 → DungeonsForever 先、TalentsForever 后 → 上游覆盖本插件。
#   于是本插件 U:SwitchSub 里的 `BuildDungeons()` 静默跑的是上游函数：
#   上游函数用的是**上游的文件级 local U**（U.dungeonPage 为 nil）→ MakeFS(nil)
#   → 报错落在 TalentsForever/Core/UI.lua:113（用户看到的正是这条）。
# 关键教训：离线 harness 只加载本插件，这种「被覆盖」永远测不出（9 次全绿 / 实机必崩），
#   只能用静态断言钉死：界面层不得有裸全局函数定义。
NS_ANCHOR = "       and '地图标记仅无限客户端支持' in marcacode)\n"
NS_EXTRA = r"""
    # ★★ 跨插件命名空间不变式（2026-09-23 实机事故）：界面层不得定义裸全局函数。
    #   上游插件界面层也定义 BuildDungeons / BuildDungeonOverview，
    #   WoW 按文件夹名字母序加载（DungeonsForever < TalentsForever）→ 上游覆盖本插件，
    #   U:SwitchSub 会静默调到上游函数（上游 U.dungeonPage 为 nil）→ MakeFS(nil)。
    #   离线 harness 只加载本插件，这种覆盖测不出，只能静态钉死。
    _bare = re.findall(r'(?m)^function\s+[A-Za-z_]\w*\s*\(', src)
    ck('★★ 界面层不定义裸全局函数（否则会被后加载的同名插件静默覆盖）',
       _bare == [], _bare)
    ck('★ BuildDungeons / BuildDungeonOverview 挂在 local 表 DG 上',
       'function DG.BuildDungeons()' in src
       and 'function DG.BuildDungeonOverview()' in src)
    _sw = src[src.index('function U:SwitchSub'):src.index('function U:UpdateActiveSub')]
    ck('★ U:SwitchSub 调的是 DG.BuildDungeons()（不是裸全局）',
       'DG.BuildDungeons()' in _sw)

    # ── 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 10（2026-09-23 用户指定）──
    # 「上移量」是纯几何量：桩的 SetPoint 只校验首参类型、不记偏移（CHECKED.SetPoint）
    # → 离线拿不到几何值，只能静态钉。
    # 静态断言一律**收窄到目标函数体**：同名串在别处会被「替命中」（白测）。
    ck('★★ 胶囊行上移量 DG.CAPSULE_LIFT = 10（先 +15 后 -5）',
       re.search(r'DG\.CAPSULE_LIFT\s*=\s*10\b', src) is not None)
    ck('★ 胶囊 host 的 y 偏移 = DG.CAPSULE_LIFT - ROW_SUB（上移没被改回 -ROW_SUB）',
       'host:SetPoint("TOP", U.panel, "TOP", 0, DG.CAPSULE_LIFT - ROW_SUB)' in src)
    # ★ 2026-09-25 起是**五颗**（无限服：5人本/团本/专业/探索/BIS配装）/ 两颗（泰坦），
    #   各颗一律取同一个 DG.CAPSULE_W —— 分段控件的滑块宽度按按钮宽取，
    #   只要有一颗用了别的宽就会跳形。
    ck('★ 各颗胶囊等宽（分段控件滑块宽度按按钮宽取，不等宽会跳形）',
       'DG.CAPSULE_W = 82' in src and src.count('width = DG.CAPSULE_W') == 8)
    ck('★ 胶囊 = 5人本(Dungeons) / 团本(Raids)',
       '{ key = "Dungeons", text = L["5人本"], width = DG.CAPSULE_W }' in src
       and '{ key = "Raids",    text = L["团本"],  width = DG.CAPSULE_W }' in src)
    ck('★★ 第三颗「专业」在无限服/正式服出现（泰坦端没有对应物品与专业）',
       'if ns.LoadForeverPages then' in src
       and 'defs[#defs + 1] = { key = "Professions", text = L["专业"], width = DG.CAPSULE_W }' in src)
    ck('★ 旧的单页签「副本」文案已下线', 'L["副本"]' not in src)
    ck('★★ SwitchSub 按 key 三分流（不是把参数丢掉、永远只显示副本页）',
       'if key == "Raids" then' in _sw
       and 'elseif key == "Professions" and ns.LoadForeverPages then' in _sw
       and 'if U.dungeonPage then U.dungeonPage:SetShown(isDun) end' in _sw
       and 'if U.raidPage then U.raidPage:SetShown(isRaid) end' in _sw
       and 'if U.profPage then U.profPage:SetShown(isProf) end' in _sw
       and 'if isDun then' in _sw)
    _bld = src[src.index('function U:Build()'):src.index('function U:Refresh()')]
    ck('★ 团本页在 Build 里一次建好（不在切页时懒建 → 保住「渲染路径零新建帧」不变量）',
       'U.raidPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'if ns.RaidModule then ns.RaidModule.Build(U.raidPage) end' in _bld)
    _uas = src[src.index('function U:UpdateActiveSub'):src.index('function U:Build()')]
    ck('★ UpdateActiveSub 在团本态跳过刷新（空态没有可刷新的内容）',
       'if self.curSub == "Raids" then return end' in _uas)
    ck('★ UpdateActiveSub 在专业态刷专业页自己那一套（不去碰副本页）',
       'if self.curSub == "Professions" then' in _uas
       and 'ns.ProfModule.Refresh()' in _uas)

    # ── 团本页（Core/RaidUI.lua，2026-09-29 新增：时间线 / 列表 两个二级子页）──
    _ra = open(os.path.join(ADDON, 'Core', 'RaidUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
    _toc2 = open(TOC, encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    _raf = re.findall(r'MakeFS\([^,]+,\s*(\d+),', _ra)
    # 原意图 = 「RaidUI 在 TOC 里排在 DungeonUI **之后**」，不是「紧邻」。
    # 掉落过滤把 Core\LootFilterUI.lua 插在两者之间（架构设计要求）→ 改比索引，忠实原意图。
    _toc_seq = [l.strip() for l in _toc2.splitlines()
                if l.strip() and not l.strip().startswith('##')]
    ck('★ RaidUI 按 toc 顺序挂在 DungeonUI 之后',
       'Core\\DungeonUI.lua' in _toc_seq and 'Core\\RaidUI.lua' in _toc_seq
       and _toc_seq.index('Core\\DungeonUI.lua') < _toc_seq.index('Core\\RaidUI.lua'))
    ck('★★ RaidUI 全端可见（不挂 LoadForeverPages 闸）',
       'if not ns.LoadForeverPages then return end' not in _ra)
    ck('★★ RaidUI 字号只许 11/14/16（全插件字号标准同款）',
       _raf and all(v in ('11', '14', '16') for v in _raf), sorted(set(_raf)))
    ck('★★ RaidUI 二级页签 = 时间线 / 列表',
       '{ key = "timeline", text = L["时间线"] }' in _ra
       and '{ key = "list", text = L["列表"] }' in _ra)
    ck('★★ RaidUI 倒计时到「分」（纯函数 RU.CountdownText，默认 RU.NowSec()）',
       'function RU.CountdownText(nowSec, shift)' in _ra
       and 'local now = nowSec or RU.NowSec()' in _ra
       and '距首批开放还有 %d 天 %d 小时 %d 分' in _ra)

    # ★★ 时钟不许直用 os.*（2026-09-29 实机事故）：WoW 的 Lua 没有 os 库（只有全局
    #    time() / date() / difftime()），而 lupa 的离线 harness 标准库齐全 ——
    #    「写了 os.* 的代码」离线恒绿、实机必崩。故这里正面钉住时钟链 + 反向全仓扫。
    def _os_direct_hits(src_text):
        hits = []
        for i, line in enumerate(src_text.replace('\r\n', '\n').split('\n'), 1):
            if line.lstrip().startswith('--'):          # 注释里提 os.time 不算违规
                continue
            if re.search(r'(?<![\w.])os\.(time|date|clock|difftime|getenv)\s*\(', line):
                hits.append(i)
        return hits

    ck('★★ RaidUI 时钟链：time() → GetServerTime() → 离线桩 os.time（os 必须 type 守卫）',
       'function RU.PickClock(env)' in _ra
       and 'function RU.NowSec()' in _ra
       and 'time = _G.time' in _ra
       and 'if type(env.time) == "function" then return env.time end' in _ra
       and 'type(env.os) == "table" and type(env.os.time) == "function"' in _ra)
    _os_hit = []
    for _base, _dirs, _fs in os.walk(ADDON):
        _dirs[:] = [d for d in _dirs if d not in ('Libs', '.git', '.workbuddy', 'Media')]
        for _f in sorted(_fs):
            if not _f.endswith('.lua'):
                continue
            _p = os.path.join(_base, _f)
            with open(_p, encoding='utf-8', errors='replace') as _fh:
                for _ln in _os_direct_hits(_fh.read()):
                    _os_hit.append('%s:%d' % (os.path.relpath(_p, ADDON).replace(os.sep, '/'), _ln))
    ck('★★ 全仓（除 Libs 第三方）不许直用 os.*（WoW 无 os 库，用全局 time()/date()）',
       not _os_hit, ', '.join(_os_hit))
    ck('★★ 国服比外服晚 1 天（RU.CN_SHIFT + RU.DayShift，zhCN 自动判 / 可显式覆盖）',
       'RU.CN_SHIFT = 1' in _ra
       and 'function RU.DayShift(cn)' in _ra
       and 'if cn == nil then cn = IsCnClient() end' in _ra
       and 'GetLocale() == "zhCN"' in _ra)
    ck('★★ 首批开放日不写死（表里只留 firstOpen 基准，日期按地区算）',
       'firstOpen = { y = 2026, m = 12, d = 9 }' in _ra
       and '2026 年 12 月 9 日' not in _ra
       and 'function RU.FirstOpenText(shift)' in _ra
       and 'format(L["%d 年 %d 月 %d 日"], f.y, f.m, f.d + RU.DayShift(shift))' in _ra)
    ck('★★ 时间线节点标签与卡墙卡片日期共用 RecDateText（两页不许各显示一个日期）',
       'local function RecDateText(rec)' in _ra
       and 'local label = RecDateText(rec)' in _ra
       and 'c.date:SetText(RecDateText(rec))' in _ra
       and 'note = RU.FirstOpenText() .. " · " .. L["同日开启"]' in _ra)
    ck('★★ RaidUI 倒计时不给秒（格式串只有 天/小时/分）',
       '距首批开放还有 %d 天 %d 小时 %d 分' in _ra and '%d 秒' not in _ra)
    ck('★★ RaidUI 时间轴轴线两端都锚页面 TOPLEFT（BOTTOMLEFT+负偏移会戳出窗口）',
       'RU.axis:SetPoint("BOTTOMLEFT", RU.page, "TOPLEFT"' in _ra
       and 'RU.axis:SetPoint("BOTTOMLEFT", RU.page, "BOTTOMLEFT"' not in _ra)
    ck('★★ 「国服待确定」注记挂 禁止 GDKP 行描述右侧',
       'L["国服待确定"]' in _ra
       and 'RU.cnNote:SetPoint("LEFT", gdkpDesc, "RIGHT", 14, 0)' in _ra)
    ck('★★ RaidUI 界面层不定义裸全局函数（函数一律挂 local 表 RU）',
       not re.search(r'^function\s+[A-Za-z_][A-Za-z0-9_]*\s*\(', _ra, re.M))

    # ★★ 卡墙几何（2026-09-29 修）：RenderList 原先在**逐卡循环体内**推进 y，
    #    首档 3 张大卡就被排成斜梯（x 增、y 也增），第 3 张已落到规则块上；
    #    桩的 SetPoint 不记偏移 -> 离线全绿也漏。现改成一次性算好落点（纯几何），
    #    这里钉住「落点来自 RU.LayoutCards，且逐卡循环里不再动 y」。
    ck('★★ RaidUI 卡墙落点走纯几何函数 RU.LayoutCards',
       'function RU.LayoutCards(list, w, h, y0)' in _ra
       and 'c:SetPoint("TOPLEFT", RU.page, "TOPLEFT", pos[i].x, pos[i].y)' in _ra)
    ck('★★ RaidUI 逐卡循环里不得再推进 y（否则卡排成斜梯）',
       re.search(r'RU\.PaintCard\(c, rec\)\s*\n\s*y = y \+', _ra) is None
       and 'y = pos.bottom + RU.LS_LABEL_H' in _ra)

    # ── 探索页：顶栏第四颗「探索」（2026-09-24 用户定）──
    ck('★ 顶栏第四颗「探索」在无限服/正式服出现（与专业同一道门）',
       'defs[#defs + 1] = { key = "Explore", text = L["探索"], width = DG.CAPSULE_W }' in src)
    ck('★ SwitchSub 有 Explore 分支且走 LoadForeverPages 闸',
       'elseif key == "Explore" and ns.LoadForeverPages then' in _sw
       and 'if U.explorePage then U.explorePage:SetShown(isExpl) end' in _sw
       and 'elseif isExpl and ns.ExploreModule then' in _sw)
    ck('★ UpdateActiveSub 在探索态刷探索页自己那一套',
       'if self.curSub == "Explore" then' in _uas
       and 'ns.ExploreModule.Refresh()' in _uas)
    ck('★ 探索页在 Build 里一次建好（不在切页时懒建）',
       'U.explorePage = CreateFrame("Frame", nil, panel)' in _bld
       and 'if ns.ExploreModule then ns.ExploreModule.Build(U.explorePage) end' in _bld)

    # ── 物品卡 Shift+点击 → 聊天框（2026-09-23 用户要求）──
    # 用户原话：「物品需要支持 Shift 点击，然后能发送到聊天输入框」。
    # ① 掉落卡与奖励芯片的帧类型都必须是 **Button**：Frame 不支持 OnClick
    #    （实测 "script type not supported"，任务行踩过这个坑才改的 Button）；
    # ② 只认 Shift + 左键；③ 客户端尚未缓存这件时自造 item:<id> 兜底
    #    （懒加载回 nil ≠ 客户端不认识，不许静默失败）；
    # ④ 聊天框两路投递：已开 → ChatEdit_InsertLink；未开 → ChatFrame_OpenChat。
    clickseg = src[src.index('function DG.ItemLink'):src.index('function U:SetDungeonFilter')]
    clickcode = '\n'.join(l.split('--')[0] for l in clickseg.split('\n'))
    ck('★★ 掉落卡与奖励芯片都是 Button（Frame 不支持 OnClick，实机踩过）',
       'r = CreateFrame("Button", nil, child, "BackdropTemplate")' in src
       and 'r = CreateFrame("Button", nil, child)' in src
       and 'r = CreateFrame("Frame", nil, child, "BackdropTemplate")' not in src
       and 'r = CreateFrame("Frame", nil, child)\n' not in src)
    ck('★ 两个物品控件挂的是同一个 Shift 点击入口',
       src.count('r:SetScript("OnClick", function(self, button)'
                 ' DG.ItemShiftClick(self, button) end)') == 2)
    ck('★★ Shift+点击只认左键 + Shift（别的点击一律放过）',
       'button ~= "LeftButton"' in clickcode and 'IsShiftKeyDown()' in clickcode)
    ck('★★ 客户端未缓存时链接有 item:<id> 兜底（不静默失败）',
       '"item:" .. tostring(id)' in clickcode)
    ck('★★ 聊天框两路投递：已开走 ChatEdit_InsertLink / 未开走 ChatFrame_OpenChat',
       'ChatEdit_InsertLink' in clickcode and 'ChatFrame_OpenChat' in clickcode)

    # ── 专业页：仅无限服的一张独立页（2026-09-23）──
    # 结构上刻意**不放进** DungeonUI.lua：那个文件是从源文件按**硬编码行号**抽出来的
    # （SEG_* 就是行号区间，增删一行整段错位），业务代码写进去会让每次迭代都去动生成链。
    # 故新页单独一个文件 Core/ProfessionUI.lua（手写骨架件），生成物里只留 4 处挂钩。
    profui = open(os.path.join(ADDON, 'Core', 'ProfessionUI.lua'), encoding='utf-8',
                  errors='replace').read().replace('\r\n', '\n')
    hui = open(os.path.join(ADDON, 'Core', 'Hui.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
    exui = open(os.path.join(ADDON, 'Core', 'ExploreUI.lua'), encoding='utf-8',
                errors='replace').read().replace('\r\n', '\n')
    exmap = open(os.path.join(ADDON, 'Core', 'ExploreMap.lua'), encoding='utf-8',
                 errors='replace').read().replace('\r\n', '\n')
    expdata = open(os.path.join(ADDON, 'Core', 'Data', 'Data_Explore.lua'),
                   encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    profdata = open(os.path.join(ADDON, 'Core', 'Data', 'Data_Professions.lua'),
                    encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    ptoc = open(TOC, encoding='utf-8', errors='replace').read()
    plines = [l.strip().replace('\\', '/') for l in ptoc.splitlines()
              if l.strip() and not l.strip().startswith('##')]
    ck('★★ 专业页在 TOC 里、且排在 DungeonUI 之后（ns.ProfHost 在其文件末尾才赋值）',
       'Core/ProfessionUI.lua' in plines and 'Core/DungeonUI.lua' in plines
       and plines.index('Core/ProfessionUI.lua') > plines.index('Core/DungeonUI.lua'))
    _profdata = ['Core/Data/Data_Professions.lua', 'Core/Data/Data_ProfRecipes.lua',
                 'Core/Data/Data_ProfLeveling.lua', 'Core/Data/Data_ProfGathering.lua']
    ck('★ 四个专业数据文件都在 TOC 里、且排在 ProfessionUI 之前（它在加载期就取 ns.ProfData）',
       all(f in plines for f in _profdata)
       and max(plines.index(f) for f in _profdata) < plines.index('Core/ProfessionUI.lua'),
       [f for f in _profdata if f not in plines])
    # ── 专业升级 HUD：数据随「固定路线 / 自动计算」模式切换（2026-10-11）──
    #   HUD 与专业页共用同一套自动路线（routeFor 的 opts 逐项对齐 RowsLeveling），
    #   自动不可用（未开 / 没装 Auctionator / 无价快照）一律回落固定路线。
    #   ⚠️ 注释里不许写出被负向断言盯的标识符形态（段表取法的旧写法）。
    pfhud = open(os.path.join(ADDON, 'Core', 'ProfFollow.lua'), encoding='utf-8',
                 errors='replace').read().replace('\r\n', '\n')
    pf_live = '\n'.join(l.split('--')[0] for l in pfhud.split('\n'))
    ck('★★ 升级 HUD 路线模式：routeFor（自动门禁 = 设置开 + Auctionator 可用 + 有价，否则回落固定）',
       'local function routeFor(slug, skill)' in pfhud
       and 'PD.Setting("autoRoute") and RA and RA.Available()' in pfhud
       and 'if res and res.priced then return "auto", res.steps end' in pfhud
       # 2026-10-11：固定分支按「目标等级」裁剪（用户：「hud 固定路线显示也需要 根据我设置等级 显示」）
       and 'return "fixed", clipFixedSteps(lv and lv.steps or nil, routeTarget(slug))' in pfhud)
    # 2026-10-11：HUD 固定路线裁剪口径必须与专业页 ClipFixedSteps 逐字一致（同一套折算公式）。
    ck('★★ 升级 HUD 固定路线按目标等级裁剪（口径与专业页 ClipFixedSteps 一致）',
       'local function clipFixedSteps(steps, target)' in pfhud
       and 'if not target or target >= 300 then return steps end' in pfhud
       and 'nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))' in pfhud
       and 'out[#out + 1] = { a, nb, st[3], nq, _clip = isClip or nil }' in pfhud
       # 目标 >= 300 = 全程 ⇒ 原样返回（不与旧行为回归）
       and 'if a > target then break end' in pfhud)
    ck('★ 升级 HUD 目标等级变更 → 即时重推指针（PF.RefreshRoute，不必等 1 秒轮询）',
       'function PF.RefreshRoute(slug)' in pfhud
       and 'PF.Sync()' in pfhud
       and 'if PF.f and PF.f:IsShown() then pcall(PF.Paint) end' in pfhud)
    ck('★★ 升级 HUD 路线模式：自动 opts 与专业页逐项一致（起点 / 三个过滤 / 目标按 slug 取）',
       'PD.Setting("autoFromCurrent")' in pfhud and 'PD.Setting("autoOnlyAH")' in pfhud
       and 'PD.Setting("autoNoFormula")' in pfhud and 'PD.Setting("autoLearnedOnly")' in pfhud
       and 'target = routeTarget(slug)' in pfhud)
    ck('★★ 升级 HUD 路线模式：段落 / 购物 / 浏览全走 routeFor（不许再直读固定路线段表）',
       '#lv.steps' not in pf_live and 'LV[s.slug]' not in pf_live
       and pf_live.count('routeFor(s.slug, s.skill)') == 4)
    ck('★★ 升级 HUD 路线模式：段标带模式前缀（自动计算 / 固定路线，复用既有 L 键）',
       '((mode == "auto") and L["自动计算"] or L["固定路线"])' in pf_live
       and 'format(L["段落 %d / %d"], vi, #steps)' in pf_live)
    ck('★★ 升级 HUD 路线模式：配方查找表并入 rinfo（附魔路线全靠它取材料）',
       'if lv and type(lv.rinfo) == "table" then' in pf_live
       and 'local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end' in pf_live
       and 'local function recItem(rec) return rec and (rec[2] or rec.makes) or nil end' in pf_live
       and 'if mats and #mats > 0 then' in pf_live)
    _bad_unpack = [l.strip() for l in pf_live.split('\n')
                   if re.search(r'\b[Uu]npack\([^()]*\)\s*,', l)]
    ck('★★ 升级 HUD：Unpack / unpack 不许出现在非末位实参（多返回值只展末位 → b 收到 nil 崩染色）',
       not _bad_unpack, ' | '.join(_bad_unpack))
    ck('★★ 升级 HUD 购物清单：表头改短（换 L["购物清单"]，旧长键不再用于渲染）',
       'f.shop.head:SetText(L["购物清单"] .. format(L[" · 共%d种"], #shown))' in pf_live
       and '购物（从当前段累计到 300，含银行）"] .. format' not in pf_live)
    ck('★★ 升级 HUD 购物清单：「仅显示缺失」开关已建 + 表头右侧让位（长文案不压开关）',
       'f.shop.missTog = CreateFrame("CheckButton", nil, f.shop)' in pf_live
       and 'f.shop.head:SetPoint("RIGHT", f.shop, "RIGHT", -(SHOP_TOG_W + 10), 0)' in pf_live
       and 'f.shop.missTog:SetPoint("TOPRIGHT", f.shop, "TOPRIGHT", -6, -4)' in pf_live
       and 'ReskinToggle(f.shop.missTog)' in pf_live)
    # ★★ 开关左侧的文字标签（2026-10-11 用户：「只显示缺失的这个开关，左边写上文字“仅显示缺失”」）。
    #   三条硬约束：① 挂 f.shop 父帧（挂开关上会被 ReskinToggle 的 PurgeNative 当
    #   「非自建子件」Hide 掉 = 实机看不到）；② 右对齐（面板随购物列加宽时贴着开关走）；
    #   ③ 锚在开关**左**缘（锚成 RIGHT 就跑到开关右边了）。文案必须走新键「仅显示缺失」。
    ck('★★ 升级 HUD 购物清单：开关左侧有文字标签「仅显示缺失」（挂父帧 + 右对齐 + 锚开关左缘）',
       'f.shop.missLab = MakeFS(f.shop, 14, C_TEXT, "RIGHT")' in pf_live
       and 'f.shop.missLab:SetPoint("RIGHT", f.shop.missTog, "LEFT", -4, 0)' in pf_live
       and 'f.shop.missLab:SetWordWrap(false)' in pf_live
       and 'f.shop.missLab:SetText(L["仅显示缺失"])' in pf_live)
    ck('★★ 升级 HUD 购物清单：表头让位量按标签实测宽现算 + 旧键「只显示缺失」已退役',
       'local SHOP_TOG_W = labW + 48' in pf_live
       and 'pcall(PDw.TextW, L["仅显示缺失"], 14)' in pf_live
       and 'L["只显示缺失"]' not in pfhud)
    #   ⚠️ 用 find 取下标并判 -1：改前基线里没有这些子串，.index() 会把整段断言崩掉。
    _i_shown = pf_live.find('local shown = {}')
    _i_cols = pf_live.find('local nameW, numW, missW, tagW, anySold')
    ck('★★ 升级 HUD 购物清单：过滤排在算列宽之前（先行滤出 shown，再扫列宽）',
       _i_shown >= 0 and _i_cols >= 0 and _i_shown < _i_cols
       and 'if (not onlyMissView()) or e.missing > 0 then shown[#shown + 1] = e end' in pf_live
       and 'for _, e in ipairs(shown) do' in pf_live
       and 'for _, e in ipairs(list) do\n            local nm, got = DG.ItemName(e.id)' not in pf_live)
    ck('★ 升级 HUD 购物清单：一键导入口径不受过滤影响（DoImport 仍走 shopList 全量）',
       'local list = shopList(tmp)' in pf_live)
    # ★★ 空清单也必须打开面板（2026-10-11 用户：「开关一开就永远点不开购物清单」）。
    #   原先 n == 0 走 else f.shop:Hide() ⇒ 开关开 + 全备齐（#shown == 0）面板永不出现。
    #   用 find 判 -1：改前基线里没有这些子串（.index() 会崩掉整段，见 PROF_PITFALLS）。
    _i_empty = pf_live.find('f.shop.empty = MakeFS(f.shop, 14, C_GREY, "LEFT")')
    _i_hide = pf_live.find('        else\n            f.shop:Hide()\n        end')
    ck('★★ 升级 HUD 购物清单：空清单必须把面板打开（不得退回「n==0 就 Hide」；用户报的「永远点不开」）',
       'f.shop.empty = MakeFS(f.shop, 14, C_GREY, "LEFT")' in pf_live
       and 'f.shop.empty:SetText(#list > 0 and L["所有物品已备齐"] or L["无材料"])' in pf_live
       and 'f.shop.empty:Show()' in pf_live
       and _i_hide < 0
       # 有行分支要收起灰字（否则有数据时残影）
       and 'f.shop.empty:Hide()' in pf_live
       # 空清单分支必须显式 Show + 摆位（否则零尺寸帧 ⇒ 实机照样看不到）
       and 'f.shop.empty:Show()\n            local shopH = 30 + 20 + 10' in pf_live)
    ck('★ 升级 HUD 购物清单：空清单提示文案 + 只保留一处 Hidden 分支（showShop 关时才 Hide）',
       "L[\"所有物品已备齐\"]" in pf_live
       and pf_live.count('f.shop:Hide()') == 1)
    ck('★ 探索页两件都在 TOC 里（数据在 DungeonUI 前、骨架在 ProfessionUI 后）',
       'Core/Data/Data_Explore.lua' in plines
       and 'Core/ExploreUI.lua' in plines
       and plines.index('Core/Data/Data_Explore.lua') < plines.index('Core/DungeonUI.lua')
       and plines.index('Core/ExploreUI.lua') > plines.index('Core/ProfessionUI.lua'))
    # ★★ 实机空表教训（2026-09-24 探索页实机踩实）：ScrollFrame / 大卡只建不摆 = 零尺寸帧，
    #    行全被裁掉、连空态文案都看不见 —— 离线桩全绿照样漏。骨架件必须显式 SetPoint 成真实矩形。
    ck('★★ 探索页滚动区必须显式摆位（零尺寸 ScrollFrame = 实机空白页，离线桩看不出）',
       'EG.scroll:SetPoint("TOPLEFT"' in exui and 'EG.scroll:SetPoint("BOTTOMRIGHT"' in exui)
    ck('★★ 探索页正文大卡必须显式摆位（同上）',
       'EG.listCard:SetPoint("TOPLEFT"' in exui and 'EG.listCard:SetPoint("BOTTOMRIGHT"' in exui)
    # ★★ 路线书坐标链（2026-09-29）：PaintCoords 画「区名 入口 → 末步」，两段点击钮走
    #    EG.MarkPoint；桩环境 GetStringWidth 缺失时 pin 走估宽兜底，钮必须照样亮出。
    ck('★★ 探索页路线链 PaintCoords 在、PaintRow 真的调了（只写函数不接线 = 经典假绿）',
       'local function PaintCoords(r, rec)' in exui
       and 'PaintCoords(r, rec)' in exui
       and exui.count('PaintCoords(r, rec)') == 2)
    ck('★★ 路线链两段点击钮：s1/s2 挂 OnClick → EG.MarkPoint(loc[1], loc[2], loc[3])',
       'r.s1 = CreateFrame("Button", nil, r)' in exui
       and 'r.s2 = CreateFrame("Button", nil, r)' in exui
       and 'EG.MarkPoint(loc[1], loc[2], loc[3])' in exui
       and 'pin(r.s1, r.c2)' in exui and 'pin(r.s2, r.c)' in exui)
    # ★★ 2026-09-24 用户定（方案 A）：对称双卡底板 —— 右列大底卡（进度条上方包到页底、
    #    常驻不随子页切换）+ 左列导航等高底卡；筛选钮全部 MakeOutline 常显描边。
    ck('★★ 探索页对称双卡底板（navCard 骨架 + listCard 顶边抬到进度文本上方 + Render 不再藏底卡）',
       'EG.navCard' in exui
       and 'EG.listCard:SetPoint("TOPLEFT", EG.page, "TOPLEFT",\n                         EG.X0 - 6, -(EG.NAV_TOP - 16))' in exui
       and 'EG.listCard:SetShown(not isRw)' not in exui)
    ck('★★ 探索页筛选钮常显描边（MakeOutline 建框 + PaintFilter 选中金/常态灰 + hui 双通道重染）',
       'MakeOutline(bt, 1, 0.82, 0)\n        bt:SetScript("OnEnter", function(self)' in exui
       and 'SetOutline(bt, true, r, g, b)' in exui
       and 'tex.__huiBorderStrip' in exui
       and 'tex:SetColorTexture(r, g, b, 1)' in exui
       and 'tex:SetVertexColor(r, g, b)' in exui)
    # ★ 2026-09-24 用户定：筛选钮/奖励钮悬停高亮（未激活悬停字提亮 + 描边提亮，OnLeave 复位）
    ck('★★ 探索页筛选钮/奖励钮悬停高亮（OnEnter 提亮 / OnLeave 走 PaintFilter/PaintRwBtn 复位）',
       'PaintFilter(self, self.__key == EG.view)' in exui
       and 'TintOutline(self, 0.75, 0.75, 0.78)' in exui
       and exui.count('PaintRwBtn() end)') >= 1)
    # ★ 2026-09-24 用户定：卡片倒圆角 —— hui 皮 SkinPopup(卡, 6, nil, {1,1,1,0.03})，
    #   非 hui 保留方形细边回退（与专业页大卡同款）
    ck('★★ 探索页双卡倒圆角（hui SkinPopup 自定义淡白底色，非 hui 方形回退）',
       'ns.hui.SkinPopup(listCard, 6, nil, { 1, 1, 1, 0.03 })' in exui
       and 'ns.hui.SkinPopup(navCard, 6, nil, { 1, 1, 1, 0.03 })' in exui)
    ck('★ 探索页几何摆位走 LayoutBody 且在 Build 期被调用',
       'function EG.LayoutBody()' in exui and exui.count('EG.LayoutBody()') >= 1)
    # ★★ 无限服没有 C_Map.GetMapInfoFromAreaID（专业页十八轮踩实）—— 探索页标记主路径
    #    必须是静态映射（wago UiMapAssignment 全 55 行户外图），API 只许作后备。
    _am = re.search(r'local AREA_MAP = \{(.*?)\}', exui, re.S)
    _am_n = len(re.findall(r'\[\d+\]\s*=\s*\d+', _am.group(1))) if _am else 0
    ck('★★ 探索页标记主路径 = 静态 AREA_MAP（>=30 区域，含 17→1413 wowhead 互证值）',
       _am_n >= 30 and '[17] = 1413' in exui, _am_n)
    ck('★★ 探索页 AREA_MAP 必须挂在 MarkPoint 取 mapID 的第一跳',
       re.search(r'function EG\.MarkPoint\([\s\S]{0,120}AREA_MAP\[areaID\]', exui) is not None)
    # ★ 自动识别已找到：背包计数 + 上交任务完成，都必须带守卫（pcall / API 存在性）；
    #   两态标记：auto 表存 "quest"/"bag" 字符串（金格=已上交，绿格=背包有书）。
    ck('★ 探索页自动识别已找到（ScanAuto：GetItemCount + IsQuestFlaggedCompleted 双守卫）',
       'function EG.ScanAuto()' in exui and 'pcall(GetItemCount' in exui
       and 'pcall(C_QuestLog.IsQuestFlaggedCompleted' in exui)
    ck('★ 探索页两态标记（quest=金格终态 / bag=绿格进行中，PaintRow 三态着色）',
       't[rec[1]] = "quest"' in exui and 't[rec[1]] = "bag"' in exui
       and 'autoSt == "quest"' in exui and 'autoSt == "bag"' in exui)
    # ★ 背包计数多路径（定制客户端 API 形态不确定）：GetItemCount → C_Item → 逐格链接解析；
    #   实时刷新：BAG_UPDATE_DELAYED / QUEST_LOG_UPDATE 事件钩子（页面可见才收）。
    ck('★★ 探索页背包计数走 CountInBags 多路径（三层回退）',
       'function EG.CountInBags(id)' in exui and 'GetItemCount' in exui
       and 'C_Item.GetItemCount' in exui and 'item%:(%d+)' in exui)
    ck('★ 探索页事件实时刷新（BAG_UPDATE_DELAYED + QUEST_LOG_UPDATE，可见才重绘）',
       'BAG_UPDATE_DELAYED' in exui and 'QUEST_LOG_UPDATE' in exui
       and 'IsShown' in exui)
    # ★ 双计数：已找到（含背包/手动）+ 已提交（只算 quest 完成态）
    ck('★ 探索页进度文本双计数（已找到 + 已提交）',
       '已找到 %d / %d · 已提交 %d / %d' in exui
       and 'EG._auto[rec[1]] == "quest"' in exui)
    ck('★ 探索页进度条（方案 C：右列整宽无边框细条 + 出头门槛刻度，宽度静态算不走 GetWidth）',
       'EG.barFill' in exui and 'EG.BAR_W, EG.BAR_H = EG.RIGHT_W, 4' in exui
       and 'math.floor(EG.BAR_W * n / total' in exui
       and 'EG.BAR_H + 6' in exui)
    # ★ 2026-09-24 用户定：门槛文案挂刻度线上（EG.tickLabs 线正上方居中，达标转金），
    #   右上角旧「10本 → 项链 / 20本 → 戒指」徽章删除（badge1/badge2 不得再现）
    ck('★★ 探索页门槛文案挂刻度线 + 旧徽章删除（2026-10-03 加 25 本三选一刻度）',
       'EG.tickLabs' in exui and 'L["10本 项链"]' in exui and 'L["20本 戒指"]' in exui
       and 'L["25本 三选一"]' in exui and 'EG.CHOICE_AT' in exui
       and 'badge1' not in exui and 'badge2' not in exui)
    # ★ 2026-10-03 用户定：奖励页重构 = 三卡同排（rwCards 网格）+ 状态章挂卡（card.state），
    #   行内 state 列删除；说明卡通栏 3 步横排（howSteps 仍落步骤标题文本）
    ck('★★ 奖励页三卡同排重构（rwCards 网格 + card.state 状态章 + 行内 state 列删除）',
       'EG.rwCards' in exui and 'card.state' in exui
       and 'row.state' not in exui
       and 'dl:GetStringWidth()' in exui)
    # ★ 2026-10-04 实机反馈：三卡 TOPRIGHT 曾错锚 rw 右缘 -ox ⇒ ①卡通栏压②③、③卡宽负
    #   （25本名称不显示 / tooltip 锚塌 / ③状态章飘到②标题区）。钉死正确锚法（显式宽 CW）。
    ck('★★ 奖励三卡摆位 = TOPRIGHT 锚 rw 左缘 ox+CW（显式宽，禁锚右缘 -ox）',
       'card:SetPoint("TOPRIGHT", rw, "TOPLEFT", ox + CW, -y)' in exui
       and '"TOPRIGHT", rw, "TOPRIGHT", -ox' not in exui)
    # ★ 2026-10-04 用户定：卡右上角显示接任务的等级要求（数据 req 字段 + card.lv 标签）
    # ★ 2026-10-04 实机反馈：state 锚 lv（FontString）文本变化后锚点不重解析 → 叠字；
    #   且 state 曾被双写锚点（最后一条 TOPRIGHT card -12 生效 = 与 lv 完全同位）。
    #   钉死：state 固定贴右缘，lv 让位偏移在 PaintRewards 按 state 实测宽算（-（12+sw+6））。
    ck('★★ 奖励卡右上角等级标签（card.lv + L["要求等级 %d"]；lv 让位 = 实测偏移，禁锚 FontString）',
       'card.lv' in exui and 'L["要求等级 %d"]' in exui
       and 'card.lv:SetPoint("TOPRIGHT", card, "TOPRIGHT", -(12 + sw + 6), -12)' in exui
       and '"TOPRIGHT", lv, "TOPLEFT"' not in exui)
    # ★ 2026-10-04 用户定：探索页阵营口径 = 联盟领地/部落领地（书行胶囊 + 睡袋页切换钮；
    #   其它页 BisUI/ProfessionUI 等共用键 L["联盟"]/L["部落"] 不动）。
    #   2026-10-13 用户定：睡袋钮改 PVP 式（阵营图标 + 文字胶囊），88 宽防 4 字截断。
    ck('★★ 探索页阵营 = 领地口径（书行胶囊 + 睡袋钮 PVP 式图标钮 88 宽，禁回退裸「联盟/部落」）',
       'L["联盟领地"]' in exui and 'L["部落领地"]' in exui
       and 'NewButton(fc, f == "A" and L["联盟领地"] or L["部落领地"], 88, 18, 14)' in exui
       and 'BAG_FAC_ICON[f]' in exui
       and 'rec[6] == "A" and L["联盟"]' not in exui
       and 'f == "A" and L["联盟"]' not in exui
       and 'local terr = BookTerr(rec)' in exui and 'FAC_PILL[terr]' in exui)
    # ★ 2026-10-04 用户定：奖励 tooltip 任务名真源 = 客户端（questID 查本地化名），
    #   数据表 quest 英文串只是兜底（2026-10-04 实机反馈：tooltip 直出英文名未汉化）。
    ck('★★ 奖励 tooltip 任务名 = 客户端按 questID 取（GetTitleForQuestID/GetQuestInfo 双路 + 兜底）',
       'C_QuestLog.GetTitleForQuestID' in exui and 'C_QuestLog.GetQuestInfo' in exui
       and 'local qname = tier.quest' in exui)
    # ★ 2026-10-04 新增：探索页地图钉 + 收集路线层（Core/ExploreMap.lua，只取机制自研）。
    #   钉线池化 + 客户端 API 全 pcall + Shift 打卡 + OnUpdate 节流 + 朝向箭头；
    #   入口钮挂 EG.routeBtn，Render 尾挂 ns.ExploreMapRefresh 钩；toc 必须注册。
    ck('★★ 探索地图层：钉/线池化 + 投影/缩放/朝向全 pcall 守卫 + Shift 打卡',
       'local function releasePins' in exmap and 'local function releaseLines' in exmap
       and 'pcall(C_Map.GetMapRectOnMap' in exmap and 'pcall(sc.GetCanvasScale, sc)' in exmap
       and 'IsShiftKeyDown() and self.rec' in exmap
       and 'UPDATE_TICK = 0.1' in exmap and 'math.atan2(dy, dx) - facing' in exmap
       and 'Media\\\\textures\\\\route_dial' in exmap and 'Media\\\\textures\\\\route_arrow' in exmap
       and 'ns.ExploreUnverIDs or {}' in exmap and 'UNVER[id] and not includeUnver' in exmap
       and 'ns.ExploreMapSettingsToggle' in exmap and 'cfg().autoRoute and not routeOn and not manualOff' in exmap
       and 'C_Timer.After(2.5' in exmap and 'ns.CloseExploreMapSettings' in exmap
       and 'ns.MainFrame or UIParent' in exmap and 'ns.hui.SkinPopup' in exmap
       and 'host, "TOPRIGHT", 8, 0' in exmap and 'ns.hui.ReskinToggle' in exmap
       and 'bookMode or "manual"' in exmap and 'ns.ExploreMapTrackBook' in exmap
       and 'showPins = false' in exmap and 'showLines = false' in exmap
       and 'cfg().showPins == true' in exmap and 'cfg().showLines == true' in exmap
       and 'local function recalcAll' in exmap
       and 'InputBoxTemplate' not in exmap and 'BuildRoundedBG(eb, 8' in exmap
       and 'BuildRoundBorder(eb, 8' in exmap and 'SetTextInsets' in exmap
       and 'label:SetPoint("TOPLEFT", content, "TOPLEFT", 2, y + 7)' in exmap
       and 'SetScrollChild' in exmap
       and 'function ns.ExploreMapConfigPopup' in exmap and 'local function qbReanchor' in exmap
       and 'local ADDON_NAME, ns = ...' in exmap and 'if not EG then return end' in exmap)
    ck('★★ 探索地图层接入：EG.routeBtn 入口钮 + Render 尾 Refresh 钩 + IsBookFound/ToggleBookFound 导出 + toc 注册',
       'EG.routeBtn' in exui and 'ns.ExploreMapRefresh then pcall(ns.ExploreMapRefresh)' in exui
       and 'function EG.IsBookFound' in exui and 'function EG.ToggleBookFound' in exui
       and 'rf:SetText(L["找书HUD"])' in exui and 'Core\\ExploreMap.lua' in ptoc
       and 'ns.ExploreMapToggle' in exui and 'ns.ExploreMapOn' in exui)
    ck('★★ 探索地图设置入口：齿轮见方贴内容右缘（EG.mapSetBtn）+ 显隐随 booksVis',
       'EG.mapSetBtn' in exui and 'EG.mapSetBtn:SetShown(booksVis)' in exui
       and 'Media\\\\textures\\\\DF_Settings' in exui and 'ns.ExploreMapSettingsToggle then pcall(ns.ExploreMapSettingsToggle)' in exui)
    ck('★★ 手动选书联动：书籍列表行 __rec + 点行调 ExploreMapTrackBook + 空态清 __rec',
       'r.__rec = rec' in exui and 'ns.ExploreMapTrackBook, self.__rec' in exui
       and 'r.__it, r.__mark, r.__rec = nil, nil, nil' in exui
       and 'manualTrack = self.rec' in exmap)
    ck('★★ 探索路线规划：NN+2-opt / set 分组接力 / 跨大陆罚 20000 / 二选一按书记账',
       'CONTINENT_PENALTY = 20000' in exmap and 'SET_ORDER = { 1, 35, 45, 60 }' in exmap
       and 'used[best.rec] = true' in exmap and 'not used[c.rec]' in exmap
       and 'ns.ExploreMapPlanRoute = BuildRoute' in exmap)
    # ★ 2026-10-05 用户定：图钉编号开关（默认开）+ 图钉大小默认 14 + 连接方式/书籍显示改下拉行
    ck('★★ 探索地图设置：图钉编号开关 showNum 默认开（钉角标 SetShown 跟随）+ 图钉大小默认 14',
       'showNum = true' in exmap
       and 'p.badge:SetShown(c.showNum ~= false)' in exmap
       and 'pinSize = 14' in exmap and 'cfg().pinSize or 14' in exmap)
    ck('★★ 探索地图设置：连接方式/书籍显示改 LibBG EasyMenu 下拉行（每下拉独立宿主防互吞）'
       ' + 分组标题改「找书HUD」+ 触发按钮登记 ns.ExploreMapMenuGuard',
       'local function mkDropdownRow' in exmap
       and 'ns.LibBG:EasyMenu(menu, host, "cursor", 0, 0, "MENU")' in exmap
       and 'function ns.ExploreMapMenuGuard' in exmap
       and 'hdr(L["找书HUD"])' in exmap)
    _ddui = open(os.path.join(ADDON, 'Core', 'DungeonUI.lua'), encoding='utf-8',
                 errors='replace').read().replace('\r\n', '\n')
    ck('★★ DungeonUI 点外关闭白名单放行探索地图下拉触发按钮（不放行 = 先收后开永远关不掉）',
       'ns.ExploreMapMenuGuard and ns.ExploreMapMenuGuard()' in _ddui)
    _twl = open(os.path.join(ADDON, 'Locales', 'zhTW.lua'), encoding='utf-8').read()
    _enl = open(os.path.join(ADDON, 'Locales', 'enUS.lua'), encoding='utf-8').read()
    ck('★★ 探索地图设置三语 L 键：图钉编号（EN 缺键会拒绝生成，这里再钉一次）',
       '图钉编号' in _twl and '图钉编号' in _enl)
    ck('★★ 下一站坐标框超宽观察口径：未聚焦看最左（SetText 后光标归 0）/ 点进去看最右（光标移末端）',
       's:SetCursorPosition(#s:GetText())' in exmap and 'eb:SetCursorPosition(0)' in exmap
       and 'OnEditFocusLost' in exmap)
    ck('★★ 到目标连线：金色 C_ME_LINE（与路线蓝线区分）+ showMeLine 默认开 + 0.2s OnUpdate 只挪线',
       'showMeLine = true' in exmap and 'local C_ME_LINE' in exmap
       and 'meLineLn = drawLine(' in exmap and 'local function meLineMove' in exmap
       and 'tickAcc < 0.2' in exmap and 'cfg().showMeLine ~= false' in exmap
       and 'local function meLineTarget' in exmap
       # ★ 反模式守卫：`and pcall(...)` 链会截断多值 ⇒ mm 恒 nil 线永不显示（2026-10-05 实机踩坑）
       and "s2 = manualTrack and not EG.IsBookFound(manualTrack[1]) and stepOfRec(manualTrack) or nil" in exmap
       and 'and pcall(C_Map.GetBestMapForUnit' not in exmap
       and 'okm, mm = pcall(C_Map.GetBestMapForUnit, "player")' in exmap)
    ck('★★ 显示连线依赖图钉：无钉不画线（c.showPins 守卫）+ 行禁用置灰联动（mkToggleRow enabledFn）'
       ' + 界面缩放步进实时 applySettings',
       'c.showLines == true and c.showPins == true' in exmap
       and 'if enabledFn and not enabledFn() then return end' in exmap
       and 'mkToggleRow(content, y, L["显示连线"],' in exmap
       and 'syncShowLineRow' in exmap
       and "cfg().hudScale = v / 100 applySettings() end" in exmap)
    ck('★★ 打卡清除地图标记 → 连线目标同步清：meLineTarget 拒已找到书 + updateTracker 清 manualTrack',
       'not EG.IsBookFound(manualTrack[1]) and stepOfRec(manualTrack)' in exmap
       and 'manualTrack = nil' in exmap)
    ck('★★ 到目标连线跟航点走：航点（地图标记）被移除**或换位置** ⇒ 连线清除（waypointMatches 同图+坐标比对）',
       'local function waypointMatches' in exmap
       and 'C_Map.GetUserWaypoint' in exmap
       and 'wmid ~= uiMapOf(s2.area)' in exmap
       and 'math.abs(wx - s2.x) < 0.0005' in exmap
       and 'if not waypointMatches(s2) then return nil end' in exmap)
    # ★ 2026-09-24 用户定：进度文本/徽章抬到进度条上方一行 + 贴住页右缘（原与条同排被刻度穿字）
    ck('★ 探索页进度文本贴右缘（-PAGE_INSET）且抬到进度条上方（-(EG.PROG_Y - 10)）',
       'EG.prog:SetPoint("TOPRIGHT", page, "TOPRIGHT", -PAGE_INSET, -(EG.PROG_Y - 10))' in exui)
    # ★ 交互重排（方案 A 落地）：打卡 = 行上独立方框按钮 r.chk；
    #   2026-09-24 用户定：Shift/Alt 修饰键点击废除（打卡只走方框），行点击只剩标图；
    #   行悬停 tooltip 整块移除（信息行内已全展示），两态口径常驻注释摆页面上。
    #   GameTooltip 仅允许出现在奖励子页的 EG.RewardTip 内（奖励详情无行内载体，必须悬停）。
    _gti = exui.find('GameTooltip')
    ck('★★ 探索页行交互：只剩标图 + 方框打卡，修饰键与行 tooltip 不得再现',
       'r.chk' in exui and 'r.strike' in exui
       and 'IsShiftKeyDown' not in exui and 'IsAltKeyDown' not in exui
       and 'IsControlKeyDown' not in exui
       and '__tip' not in exui
       and (_gti < 0 or _gti > exui.find('function EG.RewardTip')))
    ck('★ 探索页两态口径常驻注释（独立一行，筛选行下方左对齐；奖励钮占位后从筛选行让开）',
       'EG.note' in exui and '自动识别：金格 = 已上交；绿格 = 背包有书未上交' in exui
       and 'EG.note:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0, -EG.NOTE_Y)' in exui)
    # ★ 全插件字号标准（2026-09-24 用户定）：标题 16 / 正文文本 14；分组小标 11 与专业页导航同款
    _fs = re.findall(r'MakeFS\([^,]+,\s*(\d+),', exui)
    ck('★★ 探索页字号标准：标题 16 / 正文 14 / 分组小标 11（MakeFS 出现的字号只许 11/14/16）',
       _fs and all(v in ('11', '14', '16') for v in _fs),
       sorted(set(_fs)))
    # ★ 筛选五颗：全部 / 联盟领地(ally=terr=="A") / 部落领地(hode=terr=="H") / 争夺中的领地(contested=terr=="C") / 只看没找到
    ck('★★ 探索页筛选含「联盟领地/部落领地/争夺中的领地」三态领地口径（terr==A/H/C）',
       'key = "ally"' in exui and 'key = "horde"' in exui and 'key = "contested"' in exui
       and 'EG.view == "ally" and terr == "A"' in exui
       and 'EG.view == "horde" and terr == "H"' in exui
       and 'EG.view == "contested" and terr == "C"' in exui
       and exui.count('key = "') >= 5)
    ck('★★ 专业页只在无限服/正式服加载（泰坦端整体 return）',
       'if not ns.LoadForeverPages then return end' in profui)
    # ★ 左列导航 + 奖励钮（2026-09-24 用户定，mockup 修订版）：左列 = 专业页 NAV 规格
    #   （148 宽 / 行高 26 / MakeOutline 金描边）；奖励从子页签收归 40本书页，
    #   筛选行末尾独立史诗紫钮；rwFrame 骨架 + PaintRewards/RewardTip + Render 分支
    ck('★★ 探索页左列导航 + 奖励钮骨架（navBtns/rwBtn/rwFrame/PaintRewards/RewardTip/Render 分支）',
       'EG.navBtns' in exui and 'EG.rwBtn' in exui and 'EG.rwFrame' in exui
       and 'function PaintRewards' in exui.replace('local function PaintRewards', 'function PaintRewards')
       and 'function EG.RewardTip' in exui
       and 'local sub = CurSub()' in exui
       and 'local isRw = sub == "rewards"' in exui
       and 'tier.items and tier.items[side]' in exui
       and 'DG.ItemName(id)' in exui
       and 'MakeOutline(bt, 1, 0.82, 0)' in exui
       and 'EG.NAV_X, EG.NAV_W, EG.NAV_TOP = PAGE_INSET, 148, Host.ROW_CLASS' in exui
       and 'EG.X0 = EG.NAV_X + EG.NAV_W + 18' in exui
       and 'EG.rwMageHead' in exui and 'EG.rwMageLines' in exui
       and 'ns.ExploreMageBonus' in exui
       and 'mh:Hide()' in exui and 'ln:Hide()' in exui)  # ★ 用户定：法师块先隐藏只留代码
    # ★ 2026-09-25 用户定：说明卡 + 等级/推荐后缀 + 右上角地图坐标合并
    ck('★★ 探索页奖励页「如何获得奖励」说明卡（SkinPopup 圆角 + 文案走 ns.ExploreHowTo）',
       'EG.howCard' in exui and 'ns.ExploreHowTo' in exui
       and 'ns.hui.SkinPopup(card, 6, nil, { 1, 1, 1, 0.03 })' in exui
       and 'EG.howSteps' in exui
       and 'ns.ExploreMageBonus' in exui
       and 'mh:Hide()' in exui)
    ck('★★ 探索页行内胶囊徽章（2026-09-25 用户定方案 A：阵营/等级/推荐/待确认四胶囊，'
       '极细 1px 描边、推荐无星、阵营去「仅」字；等级 = ns.ExploreZoneLv；'
       '推荐 = ns.ExploreRecIDs；待确认 = ns.ExploreUnverIDs）',
       'MakeTagPill' in exui and 'PaintPill' in exui and 'FAC_PILL' in exui
       and 'ns.ExploreZoneLv and ns.ExploreZoneLv[rec[2]]' in exui
       and 'ns.ExploreRecIDs and ns.ExploreRecIDs[id]' in exui
       and 'ns.ExploreUnverIDs and ns.ExploreUnverIDs[id]' in exui
       and 'edgeSize = 1' in exui
       and '__prev' in exui
       and '★推荐)|r' not in exui and '(待确认)|r' not in exui
       and 'L["仅联盟"]' not in exui and 'L["仅部落"]' not in exui
       and 'rec.lv' not in exui and '(1级)' not in exui and '(35级' not in exui)
    ck('★★ 待确认书名删除线（2026-09-26 用户定：r.unStrike 1px 灰细线压书名正中，'
       '渲染期锚 FontString LEFT/RIGHT 显隐，与推荐互斥；完成态金线是 r.strike，两线独立）',
       'r.unStrike' in exui
       and 'r.unStrike:SetPoint("LEFT", r.a, "LEFT", 0, 0)' in exui
       and 'r.unStrike:SetPoint("RIGHT", r.a, "RIGHT", 0, 0)' in exui
       and 'r.unStrike:Show()' in exui and 'r.unStrike:Hide()' in exui)
    ck('★★ 探索页行宽 = 右列宽（EG.RIGHT_W——修 ScrollFrame 裁掉右上角坐标/区域名的 bug）',
       'r:SetWidth(EG.RIGHT_W - 2 * EG.LIST_PAD)' in exui
       and 'r:SetWidth(EG.W - 2 * EG.LIST_PAD)' not in exui)
    ck('★ 探索页行右上角合并区域名 + 坐标（r.d 挪到 r.c 左侧，右下角锚废弃）',
       'r.d:SetPoint("RIGHT", r.c, "LEFT", -6, 0)' in exui
       and 'r.d:SetPoint("BOTTOMRIGHT"' not in exui)
    ck('★ 说明卡/数据层不得出现英文人名（交书 NPC 无中文名 → 只给区域 + 坐标，2026-09-25 用户定）',
       'Garion' not in expdata and 'Owen' not in expdata
       and 'Garion' not in exui and 'Owen' not in exui
       and 'ns.ExploreZoneLv = {' in expdata and 'ns.ExploreRecIDs = {' in expdata
       and 'ns.ExploreUnverIDs = {' in expdata
       and 'lv = 35' not in expdata and 'lv = 1' not in expdata)
    # ★ 睡袋子页（2026-09-24 两列式改版）：左列任务链 + 右列详情/总奖励双态 + 阵营胶囊；
    #   状态字走 C_QuestLog（打卡框废）；红框空区收掉（bagFrame 顶到 NAV_TOP-6）。
    ck('★★ 探索页睡袋子页两列式（BAG_CHAIN + 阵营胶囊 + 芯片池 + 双卡 + NAV_TOP 收顶）',
       'EG.navBtns["bag"]' in exui
       and 'SetSub("bag")' in exui
       and 'db.explore.subPage == "bag"' in exui
       and 'EG.bagFrame:SetShown(isBag)' in exui
       and 'local BAG_CHAIN = {' in exui
       and 'EG.bagScroll, EG.bagChild = rs, rc' in exui
       and 'EG.bagFacBtns[f] = bt' in exui
       and 'EG.bagChips[i] = c' in exui
       and 'C_QuestLog.IsQuestFlaggedCompleted, qid' in exui
       and 'PaintBag()' in exui
       and 'L["任务线奖励总览"]' in exui
       and 'EG.bagLC = lc' in exui
       and 'BagLayoutRows()' in exui
       and 'EG.bagDRH2 = dRwH2' in exui
       and 'L["你可以选择一件："]' in exui and 'L["你还会获得："]' in exui
       and 'EG.bagNote = nc' in exui
       and 'L["作者备注"]' in exui and 'L["收获"]' in exui
       and 'BAG_REQ_LVL, BAG_QUEST_LVL = 14, 40' in exui
       and 'xp = 3150' in exui and 'xp = 2350' in exui and 'xp = 315,' in exui
       and 'ns.hui.SkinPopup(lc, 8, nil, { 1, 1, 1, 0.03 })' in exui
       and 'ns.hui.SkinPopup(det, 8, nil, { 1, 1, 1, 0.03 })' in exui
       and 'ns.hui.SkinPopup(nc, 8, nil, { 1, 1, 1, 0.03 })' in exui
       and 'ns.hui.SkinPopup(eb, 6, nil, { 1, 1, 1, 0.045 })' in exui
       and 'EG.bagViewH' in exui
       and 'EG.bagFrame:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -(EG.NAV_TOP - 6))' in exui)
    # ★ 2026-09-24 第七轮（用户截图反馈）：芯片去边框+图标 24；石爪三步 area 8→406
    #   （此前定位飞悲伤沼泽）；作者备注支持内联可点坐标段（③ 岔口 50.9,52.3 / ⑥ 推车 87.4,49.7
    #   + 信使行囊阿拉希侧 22.4,24.2，第 16 轮对齐 foreverchanges.pro 攻略精修）；
    #   注释卡行首物品钮可悬停（混调干果 216619 / 睡袋 211527）；总奖励二选一拆②③两组。
    ck('★★ 睡袋第七轮（芯片无边框24 + area406 + 备注内联坐标 + 注释物品钮 + 二选一两组）',
       'ns.hui.SkinPopup(c, 8, nil, { 1, 1, 1, 0.045 }, 1, true)' in exui
       and 'c.icon:SetSize(24, 24)' in exui
       and 'area = 406' in exui and 'area = 8,' not in exui
       and 'EG.bagNSegs' in exui and '{ 406, 50.9, 52.3 }' in exui and '{ 267, 87.4, 49.7 }' in exui
       and '{ 45, 22.4, 24.2 }' in exui
       and 'area = 28,' not in exui   # ★ 28 是西瘟疫之地；希尔斯布莱德丘陵 = 267（第 16 轮用户实测纠错）
       and 'EG.bagNoteItems' in exui
       and '"二选一 · 第②步"' in exui and '"三选一 · 第③步"' in exui
       and '"二选一 · 第③步"' not in exui
       and 'L["状态来自你自己的任务日志，交完任务这里会自动变。"]' not in exui
       and '步步经验 · wowhead 口径' not in exui)
    # ★ 2026-09-24 第十轮（用户实测反馈）：① 混排备注段池在纯文本分支残留（③→④ 切换
    #   段落还挂着）→ 纯文本分支整组隐藏段池；② ③ 实为三选一（rw note + 总奖励组头），
    #   选一判定用「选一」通配；③ 提示框不显示「×选一」注记；④ 左列序号/任务名 16 号。
    # ★ 2026-09-25 本地化：睡袋备注串已包 L（zhCN 下 L 返回键名原文，语义不变），
    #   断言同步到 find(L["选一"]) / note = L["…"] 形态。
    ck('★★ 睡袋第十轮（备注段池清隐 + 三选一 + 提示框免选一 + 左列 16 号）',
       'for _, pi in ipairs(EG.bagNSegs or {}) do' in exui
       and 'find(L["选一"], 1, true)' in exui
       and 'not tostring(c.__note):find(L["选一"], 1, true)' in exui
       and 'note = L["三选一"]' in exui and 'note = L["二选一"]' in exui
       and 'MakeFS(r, 16, C_GOLD, "LEFT")' in exui
       and 'MakeFS(r, 16, C_TEXT, "LEFT")' in exui)
    # ★ 2026-09-24 第八轮（用户实测反馈）：PaintBagDetail 是文件级函数、**不可见 Build 局部
    #   RWd**——混排备注渲染 `RWd - 20` 引到全局 nil，实机进 ③⑥ 直接算术报错、备注整段空。
    #   修复后段宽走 EG.bagRWd；卡间距统一 8（列间 12→8、总奖励组间 10→8）。
    ck('★★ 睡袋第八轮（备注段宽走 EG.bagRWd 防全局 nil + 卡间距统一 8）',
       'local avail = (EG.bagRWd or 700) - 20' in exui
       and 'CW - LW - 8' in exui
       and 'LW + 12' not in exui and 'RWd + 12' not in exui)
    # ★ 2026-09-24 第十一轮（用户实测反馈）：① CW 旧值 RIGHT_W - 2*LIST_PAD 比 bag 帧
    #   实际宽（= RIGHT_W）窄 10px → 左卡右缘（锚 bag 右缘 -RWd-8）右移越过右列起点
    #   288，两卡重叠 2px（「紧贴」根因）。CW 必须等于实际帧宽。
    #   ② 备注坐标钮 20 高 + 顶部下压 2px → 金色坐标明显低于同行文字；改 18 高顶对齐。
    ck('★★ 睡袋第十一轮（CW=RIGHT_W 防两卡重叠 + 备注坐标钮 18 高顶对齐）',
       'local CW = EG.RIGHT_W' in exui
       and 'sb:SetHeight(18)' in exui
       and '"TOPLEFT", det, "TOPLEFT", 10 + nx, -y)' in exui
       and '10 + nx, -y - 2' not in exui)
    # ★ 2026-09-24 第八轮补丁（用户实测截图：混排备注文字重叠）：换行分支必须**先收掉
    #   当前行再起排**（旧码先摆在当前 y 再推进 → 尾段叠在当前行文字/坐标钮上），
    #   行高走实机 GetStringHeight（type 守卫，桩回落宽度估算）。
    ck('★★ 睡袋备注换行先收行再起排 + GetStringHeight 真实行高（type 守卫）',
       'if nx > 0 then nx, y = 0, y + 22 end' in exui
       and 'GetStringHeight' in exui
       and 'y = y + lines * 22' not in exui)
    # ★ 2026-09-24 用户定：奖励不分阵营 —— 奖励行**不得**再带「仅联盟/仅部落」标签。
    #   2026-09-25 用户定：清单页阵营括注升格为胶囊（去「仅」字）。
    #   2026-10-04 用户定：胶囊文案改「联盟领地/部落领地」（裸 L["联盟"]/L["部落"] 仅剩其它页共用件）。
    ck('★★ 奖励行无阵营标签（row.tag 整块删除）+ 书行阵营改胶囊（L["仅…"] 全绝迹）',
       'row.tag' not in exui
       and exui.count('L["仅联盟"]') == 0 and exui.count('L["仅部落"]') == 0
       and 'L["联盟领地"]' in exui and 'L["部落领地"]' in exui)
    # ⚠️ L 在本插件是**局部表**（Locales/zhCN.lua 的 `local L` 只导出成 ns.L）：
    #    裸用 L["…"] 会在加载期直接 nil 崩、整页废掉（首版就是这么写的）。
    ck('★★ ProfessionUI 先取 ns.L（裸用全局 L 会加载期崩）',
       'local L = ns.L' in profui)
    # 跨插件撞名（本文件头记录过的实机事故）在专业页同样适用：界面层不得定义裸全局函数。
    _pbare = re.findall(r'(?m)^function\s+[A-Za-z_]\w*\s*\(', profui)
    ck('★★ ProfessionUI 不定义裸全局函数（否则会被后加载的同名插件静默覆盖）',
       _pbare == [], _pbare)
    ck('★ ProfessionUI 的按钮显式建描边（SetOutline 只翻已建好的描边件，漏建则选中态永不亮）',
       'MakeOutline(bt, 1, 0.82, 0)' in profui)
    ck('★ 专业页的行 / 详情条与副本页同一套卡片参数（两页并排看是同一个插件）',
       profui.count('DG.LOOT_CARD_BG') >= 3 and 'DG.LOOT_CARD_EDGE_HOVER' in profui)
    ck('★★ 专业页的行是 Button（Frame 不支持 OnClick，实机踩过 "script type not supported"）',
       'r = CreateFrame("Button", nil, PD.child, "BackdropTemplate")' in profui)
    # ⚠️ 打在**活代码**上：文件头的纪律说明里就写着「绝不 SetParent(nil)」，
    #    不剥注释的话「删掉代码、留下注释」照样全绿 —— 断言等于白测（本项目的老坑）。
    _proflive = '\n'.join(l.split('--')[0] for l in profui.split('\n'))
    ck('★★ 专业页活代码不调 SetParent（scroll child 被换掉会让 ScrollFrame 留悬空指针 → 实机 ACCESS_VIOLATION）',
       'SetParent(' not in _proflive)
    ck('★★ 专业页只建一次 scroll child（不重建滚动子帧）',
       _proflive.count('SetScrollChild(') == 1)
    # ★ DG.ItemName 返回 (名字, 是否拿到) 两个值：放在调用**末参**位置时两个都会被传进去。
    #   gsub 的第 3 个实参要求是替换串/number/table，收到 boolean 会当场报
    #   「bad argument #3 to 'gsub' (number expected, got boolean)」（钓鱼页实机整页崩）。
    #   format 那边多传一个会被忽略、无害，故只钉 gsub。
    ck('★★ 用 DG.ItemName 做 gsub 替换时必须套括号（它返回两个值，末参会被一并传入）',
       'note:gsub("{book}", (DG.ItemName(book)))' in profui)
    _prender = profui[profui.index('function PD.Render()'):profui.index('function PD.RequestRows')]
    ck('★★ PD.Render（渲染调度）本身不新建帧、不重建 scroll child（骨架已在 PD.Build 一次建好）',
       'CreateFrame' not in _prender and 'SetScrollChild' not in _prender)
    _pbuild = profui[profui.index('function PD.Build(page)'):
                     profui.index('local NAV_SKILL_SLUG = {')]
    ck('★ 页面骨架在 PD.Build 里一次建全（导航 / 子页签 / 工具条 / 滚动容器 / 详情条）',
       _pbuild.count('CreateFrame') >= 3 and 'SetScrollChild(child)' in _pbuild
       and 'PD.toolBtns' in _pbuild and 'PD.subBtns' in _pbuild)
    # ★ hero 条已删（2026-09-24 用户定）：不许再回来 —— 回来就是又一条没内容的空白淡底条。
    ck('★ 专业页 hero 条保持删除状态（不再建 hero 帧 / hero 常量）',
       'PD.hero' not in profui and 'HERO_TOP' not in profui and 'PD.heroIcon' not in profui)
    # ★★ 总览段落卡（2026-09-24 实机二轮）：每个内容块一张卡。卡池在 Build 一次建全，
    #    Render 期只摆位置 —— 行池「零新建帧」纪律的段落卡版。
    ck('★ 总览段落卡池在 PD.Build 一次建全（Render 不建帧）',
       'PD.secCards' in profui and 'PD.SEC_CARD_MAX' in profui
       and profui.index('PD.secCards[i] = c') < profui.index('function PD.Render()'))
    ck('★ 总览分栏 0.62 举手（splitLW 按 OV_GUT 沟距算、优先于 COL_LW；升级页不举手仍 0.80）',
       'PD.OV_SPLIT = 0.62' in profui
       and 'PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.OV_SPLIT)' in profui
       and 'PD.splitLW or PD.COL_LW' in profui)
    # ★★ 卡片净距标准（2026-09-24 用户定稿 8px，已写入 AGENTS.md）：段落卡上下、左右
    #    看得见的空隙 = SEC_GAP，由 OV_GUT = SEC_GAP + 2*SEC_PAD 换算落地 —— 段间空档行、
    #    右栏 x 落点、分栏线落点三处都必须认 OV_GUT，不许别处另写死间距数。
    ck('★★ 卡片净距标准 8px（SEC_GAP 单源，OV_GUT 换算；段间空档 ≥3 处 + 右栏落点 + 分栏线）',
       'PD.SEC_GAP = 8' in profui
       and 'PD.OV_GUT = PD.SEC_GAP + 2 * PD.SEC_PAD' in profui
       and profui.count('PushGap(rows, PD.OV_GUT, 1)') >= 3
       and 'PushGap(rows, PD.OV_GUT, 2)' in profui
       and '(PD.LIST_PAD + lw + PD.OV_GUT)' in profui
       and 'local gut = PD.lvSplit and PD.OV_GUT or PD.COL_GAP' in profui)
    # ★★ 三轮（2026-09-24 实机）：① 折行宽度必须跟实际渲染栏宽走（ColTextW 认 splitLW/splitRW，
    #    否则左栏文字按 0.80 旧宽折行 → 整段冲进右栏「简介超出卡片」）；② 段落卡走
    #    ns.hui.BuildRoundedBG 圆角原语（可视化方案里卡片四角是圆的，SetBackdrop 是直角）。
    ck('★★ ColTextW 折行宽度跟随本页举手分栏（lvSplit→splitLW/RW，gridSplit→GRID_LW/RW）',
       'if PD.lvSplit then return PD.splitRW or PD.COL_RW end' in profui
       and 'if PD.lvSplit then return PD.splitLW or PD.COL_LW end' in profui
       and 'if PD.gridSplit then return PD.GRID_RW end' in profui)
    ck('★★ 段落卡是圆角（ns.hui.BuildRoundedBG 原语，弧盘 + 1px 描边；不许退回 SetBackdrop 直角）',
       'ns.hui.BuildRoundedBG(c, 6, { 1, 1, 1, DG.LOOT_CARD_BG }, "both", true, 1)' in profui
       and profui.count('secCards') > 0
       and 'c:SetBackdrop(' not in profui.split('PD.secCards = {}', 1)[-1].split('-- ── 底部左侧', 1)[0])
    # ★★ 段内末行免分割线（2026-09-24 用户实机报）：PaintRows 前瞻标记 + BindRow 认标记，
    #    两处都在才成立 —— 缺前瞻则标记恒 nil、缺消费则白算。
    ck('★★ 段落卡末行不画分割线（PaintRows 前瞻 _lastInSec + BindRow 据此 Hide sep）',
       'spec._lastInSec = not (nxt and nxt.sec == spec.sec)' in profui
       and 'if spec._lastInSec then r.sep:Hide() else r.sep:Show() end' in profui)
    # 钓鱼页曾经把 GA.fishing 的 {区域, 技能, 原始值} 丢进「节点表」通用循环 → 对数字调 ipairs
    # （实机必崩：attempt to index a number value）。形状不同就得先分流。
    _pgath = profui[profui.index('function PD.RowsGather(rows)'):]
    ck('★★ 钓鱼页先分流再渲染（GA.fishing 是 {区域,技能,原始值}，混进节点循环会对数字 ipairs）',
       'PD.RowsFishing(rows)' in _pgath
       and _pgath.index('PD.RowsFishing(rows)') < _pgath.index('for _, n in ipairs(g) do'))
    # ── 采集页去英文 + 钓鱼页折两栏（2026-09-24 用户：采集页很多是英文的）──────────
    # 口径：**区域名与节点名都客户端化** —— 数据表里只留 AreaTable 区域 ID 与产出物品 ID，
    #   名字运行期问客户端；客户端拿不到就给中文占位，**绝不回落英文**（站点 JSON 给的
    #   正是英文区域名 / GameObject 节点名，那两样就是要消掉的东西）。
    ck('★★ 区域名走客户端（C_Map.GetAreaInfo），拿不到落「区域 #ID」中文占位、绝不回落英文',
       'DG.ZoneName = function(id)' in profui
       and 'local fn = m and m.GetAreaInfo' in profui
       and 'return format(L["区域 #%d"], id)' in profui)
    ck('★★ 采集节点标题 = 首个产出物的客户端名（节点名客户端无查询口，数据表不再落）',
       'local nm, got = DG.ItemName(head)' in profui
       and 'if not got then nm = head and format(L["物品 #%d"], head) or "?" end' in profui
       # ★ 该物品必须挂进 it：否则 PD.RequestRows 不催它、PD.SweepNames 不来重扫，
       #   标题就永远停在「物品 #ID」占位上（懒加载路径的静默失效）。
       and 'kind = "row", it = head and { head } or nil, text = nm,' in profui)
    ck('★★ 钓鱼采集页折两栏（gridSplit 只认 fishing，其余采集页仍单列）',
       'PD.GRID_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) / 2)' in profui
       and 'PD.gridSplit = (PD.cur == "fishing")' in profui
       and 'PD.gridSplit = false\n' in profui)
    ck('★★ 网格自动分列（放进**较矮**的一栏，不靠「上一行取反」；通栏元素先拉平游标）',
       'col = (y[2] < y[1]) and 2 or 1' in profui
       # span 表达式 2026-09-24 扩过一次：grid 页按 kind 通栏之外，总览页（lvSplit）
       # 还支持行定义**显式举手**（spec.span == true）通栏 —— 两个来源缺一不可。
       and ('local span = (grid and spec.kind ~= "row") or spec.span == true' in profui
            or 'local span = grid and (spec.kind ~= "row")' in profui)
       and 'y[1], y[2] = top + h + 2, top + h + 2' in profui)
    # ★★ 数据层零英文文案：只扫字符串字面量（键名 mining / herbalism 是结构不是文案）。
    #   ⚠️ 不剥注释就会恒红/恒绿 —— 文件头那两块注释里本来就有英文工具名。
    _pgathdata = open(os.path.join(ADDON, 'Core', 'Data', 'Data_ProfGathering.lua'),
                      encoding='utf-8', errors='replace').read()
    _pgathlive = re.sub(r'(?m)--\[\[.*?\]\]--', '', _pgathdata, flags=re.S)
    _pgathlive = '\n'.join(l.split('--')[0] for l in _pgathlive.split('\n'))
    _pen = sorted(set(re.findall(r'"([^"]*[A-Za-z]{3,}[^"]*)"', _pgathlive)))
    ck('★★ 采集数据表零英文文案（英文区域名 / 节点名不得进库，只剩 mining / herbalism 键名）',
       _pen == ['herbalism', 'mining'], _pen)
    # 生成物侧的挂钩：ns.ProfHost 交接 + Build 里建页
    ck('★ 生成物导出 ns.ProfHost 基建（专业页靠它拿到同款皮与配色）',
       'ns.ProfHost = {' in src and "MakeOutline = MakeOutline," in src
       and 'CONTENT_W = CONTENT_W, CONTENT_H = CONTENT_H,' in src)
    ck('★ 专业页在 Build 里一次建好（改成切页懒建就破「渲染路径零新建帧」）',
       'U.profPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'ns.ProfModule.Build(U.profPage)' in _bld
       and 'if ns.LoadForeverPages then' in _bld)

    # ── 观感六改（2026-09-23 用户口径）──────────────────────────────────────
    # ① 每页一张大卡片（行不再各自成小卡）
    ck('★★ 专业页正文是一张**大卡片**（用户：现在是每一行一个小卡片 → 要整页一张）',
       'PD.listCard = listCard' in _pbuild
       and 'listCard:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)' in _pbuild)
    # ★ 顺序断言：同为 page 的子帧按创建序绘制 —— 大卡必须先于滚动帧建，否则盖住整页列表
    ck('★★ 大卡建在滚动帧**之前**（子帧按创建序绘制，反了就盖住列表）',
       _pbuild.index('PD.listCard = listCard') < _pbuild.index('SetScrollChild(child)'))
    _prow = profui[profui.index('function PD.Row(i)'):profui.index('function PD.RowHeight')]
    _phover = profui[profui.index('function PD.SetRowHover(r, on)'):
                     profui.index('function PD.Row(i)')]
    ck('★★ 行常态透明（一张大卡之后再画几百个行方框 = 白改）',
       'r:SetBackdropColor(1, 1, 1, 0)' in _phover
       and 'r:SetBackdropBorderColor(1, 1, 1, 0)' in _phover)
    ck('★ 行 / 大卡的悬停高亮仍走副本页那两档参数（两页并排看是同一个插件）',
       'DG.LOOT_CARD_BG_HOVER' in profui and 'DG.LOOT_CARD_EDGE_HOVER' in profui)
    # ★★ 悬停高亮（用户 2026-09-24 报「鼠标划走以后高亮一直显示」）：
    #   ①创建时写「全透明 0」、OnLeave 却写「常态 0.03/0.05」→ 划过一次的行回不到出厂状态，
    #     留下那圈淡框；②帧在悬停中被平移或复用（滚轮滚动移动整个 scroll child、切页签把行
    #     Hide 后复用）时 WoW 不补发 OnLeave → 底色停在悬停值。
    #   修法：把「亮不亮」收敛成一处状态，四条路写同一个值，并与真实鼠标位置定时对齐。
    ck('★★ 行创建时就写成常态（不再「创建写全透明、离开写常态」——那样划过的行永久常亮）',
       'PD.SetRowHover(r, false)' in _prow)
    ck('★★ 悬停是一处状态：OnEnter / OnLeave 都写同一个值（不再各写一套颜色）',
       'PD.SetRowHover(self, true)' in _prow and 'PD.SetRowHover(self, false)' in _prow)
    ck('★★ 悬停失同步会自愈：行池按真实鼠标位置定时对齐（滚轮滚动不补发 OnLeave）',
       'function PD.SyncHover()' in profui
       and 'child:SetScript("OnUpdate"' in _pbuild
       and 'PD.SyncHover()' in _pbuild)
    ck('★ 绑定行时按真实鼠标状态落值（池里复用来的行不带上一轮悬停残留）',
       'PD.SetRowHover(r, r.IsMouseOver and r:IsMouseOver())' in profui)
    # ★★ 六轮：斑马纹（用户原话「我想他支持斑马纹」）—— 隔行真行一层极淡底。
    #   数值不钉死（同 TBL_ICON 的教训，用户还会微调）：只钉「常量有定义 + SetRowHover
    #   有 __z 分支（悬停仍优先、描边不跟底色）+ BindRow 先落 __z 再落色 +
    #   PaintRows 按真行（kind == "row"）分列交替计数」。
    ck('★★ 斑马纹：SetRowHover 有 __z 分支（底纹走 ZEBRA_A、描边保持透明、悬停仍优先）',
       re.search(r'PD\.ZEBRA_A = [0-9.]+', profui) is not None
       and 'elseif r.__z then' in _phover
       and 'r:SetBackdropColor(1, 1, 1, PD.ZEBRA_A)' in _phover
       and _phover.index('elseif r.__z then') < _phover.index('else\n'))
    ck('★★ 斑马纹：BindRow 先落 __z 再落色（行复用不残留条纹）',
       'r.__z = spec.z and true or false' in profui
       and profui.index('r.__z = spec.z and true or false')
           < profui.index('PD.SetRowHover(r, r.IsMouseOver and r:IsMouseOver())'))
    ck('★★ 斑马纹：PaintRows 按真行分列交替计数（标题/说明/空档不吃底纹）',
       'local zc = { 0, 0 }' in profui
       and 'zc[col] = zc[col] + 1' in profui
       and 'spec.z = (zc[col] % 2 == 0)' in profui
       and 'spec.z = nil' in profui)
    # ★★ ⑳ 已学专业导航（用户 2026-09-24 原话「制皮 45/75…颜色就不要是灰色的了，是主题绿」）。
    #   钉链路五件套：skillLineID→slug 映射（含易错的 first-aid 短横）、读取函数的桩安全护栏、
    #   右侧「当前/上限」小字（14pt 正文口径）、绿色走 ns.hui.ACCENT（主题热切换即跟随）+
    #   主题监听重染、图标已学显真彩。锚全带缩进，防注释双命中。
    _nmap = profui[profui.index('local NAV_SKILL_SLUG'):profui.index('function PD.ProfLearned')]
    ck('★★ ⑳ skillLineID→slug 映射覆盖 12 个可学专业（first-aid 短横 slug 不写错）',
       _nmap.count('= "') == 12
       and '[165] = "leatherworking"' in _nmap and '[129] = "first-aid"' in _nmap
       and '[185] = "cooking"' in _nmap and '[356] = "fishing"' in _nmap
       and '[393] = "skinning"' in _nmap)
    _pl = profui[profui.index('function PD.ProfLearned'):profui.index('local function NavAccent')]
    ck('★★ ⑳ ProfLearned 读 GetProfessions 六槽 + skillLine（第 7 返回值），桩环境安全降级',
       'if type(GetProfessions) ~= "function" then return out end' in _pl
       and 'local ok, a, b, c, d, e, f = pcall(GetProfessions)' in _pl
       and 'pcall(GetProfessionInfo, idx)' in _pl
       and 'tonumber(cur) or 0' in _pl)
    ck('★★ ⑳ 导航「当前/上限」小字：14pt 正文口径、右对齐贴边、未学隐藏',
       'PD.NAV_LV_FS = 14' in profui
       and 'bt.__lv = MakeFS(bt, PD.NAV_LV_FS, C_GREY, "RIGHT")' in profui
       and 'bt.__lv:SetPoint("RIGHT", bt, "RIGHT", -6, 0)' in profui
       and 'bt.__lv:Hide()' in profui)
    _pn = profui[profui.index('function PD.PickNav'):profui.index('function PD.TabsFor')]
    ck('★★ ⑳ 已学导航项：名字走主题绿（选中态仍金色）、未学维持灰、右侧补 45/75、图标显真彩',
       'local learned = PD.ProfLearned()' in _pn
       and 'bt:GetFontString():SetTextColor(NavAccent())' in _pn
       and 'Unpack(sel and C_GOLD or C_DIM)' in _pn
       and 'format("%d/%d", lv.cur, lv.max)' in _pn
       and 'bt.__icon:SetDesaturated(not sel and not lv)' in _pn)
    ck('★★ ⑳ 绿色取 ns.hui.ACCENT（主题热切换即跟随），hui 缺位回落默认强调绿',
       'ns.hui.OnThemeChange(function() if PD.built then pcall(PD.PickNav) end end)' in profui
       and 'if a then return a[1], a[2], a[3] end' in profui
       and '0x46 / 255, 0xbf / 255, 0x72 / 255' in profui)
    # ★ 商人兑换的货币译名（用户 2026-09-24）：界面上叫「商人青睐」。
    ck('★★ 商人兑换的货币写「商人青睐」（用户口径：不再写「恩惠」）',
       'L["商人青睐 %s"]' in profui and '恩惠' not in profui)
    ck('★★ 大卡随滚动区定位（四周外扩 LIST_PAD，行再内缩回同一矩形）',
       profui.count('PD.listCard:SetPoint') >= 2
       and 'PD.listCard:SetPoint("BOTTOMRIGHT"' in profui
       and 'PD.listCard:Show()' in profui)
    # ② 升级页左右两栏（2026-09-24 二轮：每段一行，左步骤 / 右材料，中间亮一条竖线）
    ck('★★ 升级页举手开两栏（PD.lvSplit = true；旧的 PD.twoCol 已退役）',
       'L["1 → 300 分段路线"]' in profui and 'lvstep = true' in profui
       and 'PD.lvSplit = true' in profui and 'PD.twoCol' not in profui)
    ck('★★ 两栏靠行定义里的 col 分列、共用同一套行池（分列不许新建帧）',
       'local col = (spec.col == 2) and 2 or 1' in profui
       and 'PD.COL_LW' in profui and 'PD.COL_RW' in profui
       and 'PD.COL_GAP' in profui)
    # ③ 技能阈值：数字染色，不再写「黄绿灰」
    # ⚠️ 查的是**活代码**（剥注释）：文件头与字段序说明里仍写着「黄绿灰」三个字解释数据字段，
    #    不剥注释的话「删掉代码、留下注释」照样全绿（本项目的老坑）。
    ck('★★ 技能阈值直接标颜色（用户：50 黄 / 70 绿 / 90 灰，不要「黄绿灰」这几个字）',
       'PD.TierText' in profui and profui.count('PD.TierText(') >= 4
       and '黄绿灰' not in _proflive and '黄 %s' not in profui)
    ck('★★ 染色走内联色彩码（一个字体串搞定，不给行池翻三倍字体串）',
       '|cffffd100' in profui and '|cff40d940' in profui and '|cff8c8c8c' in profui)
    # ④ 第 6 颗子页签：Legacy → 传承
    ck('★★ 子页签第 6 颗与相关标题都改叫「传承」（界面上不留英文 Legacy）',
       'text = L["传承"]' in profui and 'Legacy 里程碑' not in profui
       and 'Legacy 点数' not in profui and 'L["Legacy 特权' not in profui)
    # ⑤ 配方页分类按钮宽度按文字自适应
    ck('★★ 分类按钮宽度按文字自适应（原定宽 72：长分类名被裁成半截，用户报）',
       'function PD.ToolSize' in profui and 'bt:SetSize(w, PD.TOOL_H)' in profui
       and 'PD.TOOL_MIN_W, PD.TOOL_MAX_W' in profui)
    ck('★ 量宽 / 折行 / 截断共用同一套字符宽度口径（三处各算一套必然对不上）',
       profui.count('CharStep(') >= 4)
    # ⑥ 营地页「职业加成」→ 五列对照总表（2026-09-24 方案 A 定稿：warcrafttavern 口径）
    ck('★★ 职业加成 = 五列对照总表（BuildBonusTable 帧一次建全，渲染期只摆位显隐）',
       'function PD.BuildBonusTable(parent)' in profui
       and 'PD.BuildBonusTable(child)' in profui
       and 'PD.wantBonusTable = true' in profui and 'PD.wantBonusTable = false' in profui
       and 'PD.placeBonusTable(h1)' in profui
       and 'function PD.RowsCampBonus' not in profui and 'BuildCampTable' not in profui)
    # ★ 表格只属于营地页的加成视图：RowsOverview 里不再举手要表
    _ovslice = profui[profui.index('function PD.RowsOverview'):
                      profui.index('function PD.RowsCamp')]
    ck('★ 总览首页不再挂对照表（对照页挂「营地系统 → 职业加成」，总览只留指路一句）',
       'wantTable' not in _ovslice and '营地系统 → 职业加成' in profui)
    ck('★ 对照页挂在「营地」（camping）名下、首页不放行营地页签（2026-09-24 用户定）',
       'if slug == "__index" then return { "overview" } end' in profui
       and 'if slug == "camping" then out[#out + 1] = "camp" end' in profui)
    # ⑰ 全部专业总览：三列导航宫格（2026-09-24 方案 B，用户拍板）
    ck('★★ 全部专业总览挂三列导航宫格（帧在 Build 一次建全，渲染期只摆位）',
       'PD.BuildIndexGrid(child)' in profui
       and 'PD.wantIndexGrid = (PD.cur == "__index")' in profui
       and 'PD.wantIndexGrid = false' in profui
       and 'PD.placeIndexGrid(h1)' in profui)
    ck('★★ 宫格卡走行池同款悬停（状态驱动 + SyncHover 兜底），不另定配色',
       'function PD.SetCardHover(c, on)' in profui
       and 'PD.SetCardHover(c, over)' in profui
       and 'PD.ixRoot:IsVisible()' in profui)
    # ⑱ 营地页卡片化（2026-09-24 用户定稿「三档合一卡」）：复用段落卡机制
    #    特权段已删（传承内容归 Legacy 页）→ RowsCamp 里只剩 1 处裸 OV_GUT（坐标段前）。
    ck('★★ 营地联盟/部落视图套段落卡（RowsCamp 打 sec 编号 + Render 举手 hasSecs；段间空档 = OV_GUT）',
       '    PushGap(rows, 6)\n    PushHead(rows, L["三档营地物件' in profui
       and 'PD.hasSecs = true\n            PD.RowsCamp(rows, PD.campView)' in profui
       and profui.count('PushGap(rows, PD.OV_GUT)') >= 1
       and '对营地系统的贡献' not in profui)
    # ⑲ 国服术语（2026-09-24 用户定）：商人恩惠 → 商人青睐（数据由 fc_gen.py 生成，改词走 zh.json）
    ck('★★ 国服术语「商人青睐」（Data_Professions.lua 不残留「恩惠」）',
       '商人恩惠' not in profdata and '商人青睐' in profdata)
    ck('★ 旧指路文案从 RowsOverview 挪进宫格尾注（__index 分支不再 PushText 那句）',
       '各专业营地物件的档位对照表在左列' not in profui
       and 'L["营地档位对照表 →「营地系统 → 职业加成」"]' in profui)
    ck('★ 对照页签名是「职业加成」（用户 2026-09-23 晚措辞，不叫单字「加成」）',
       'bt:SetText(L["职业加成"])' in profui and 'L["加成"]' not in profui)
    # ★★ 十七轮（用户 2026-09-24）：左列导航项「字体大小都是 16」，图标随字号稍微放大
    #   （16 → 20，行高 22 → 26）。数值不钉死（同 TBL_ICON 教训）——钉「吃常量」：
    #   NewButton 字号 / 图标 SetSize / 文字落点都得跟着 PD.NAV_FS / PD.NAV_ICON 走。
    ck('★★ 左列导航项字号/图标吃 NAV_FS/NAV_ICON 常量（文字落点随图标联动）',
       'NewButton(page, text, PD.NAV_W, PD.NAV_ITEM_H, PD.NAV_FS)' in profui
       and 'bt.__icon:SetSize(PD.NAV_ICON, PD.NAV_ICON)' in profui
       and 'fs:SetPoint("LEFT", bt, "LEFT", 5 + PD.NAV_ICON + 5, 0)' in profui
       and 'PD.NAV_FS, PD.NAV_ICON = 16, 20' in profui
       and 'PD.NAV_ITEM_H, PD.NAV_GROUP_H, PD.NAV_GAP = 26, 22, 3' in profui)
    # ★★ 2026-09-24 三轮：对照视图收归营地系统 —— 各专业营地页只留 联盟/部落 两颗钮，
    #    「职业加成」钮（key="bonus"）全文件不允许再出现。
    ck('★★ 「职业加成」对照视图只在营地系统名下（各专业营地页不放这颗钮，2026-09-24 用户定）',
       'key = "bonus"' not in profui)
    # ⑲ 营地/军需官 → 地图标记（2026-09-24 用户：点军需官坐标在地图上标记；这一段要汉化）
    # ★★ 二轮补（用户实机报「未收录该位置的地图」）：无限服源码 1.60.1 全库没有
    #    C_Map.GetMapInfoFromAreaID → AreaID→uiMapID 必须有静态映射兜底，API 只作后备。
    ck('★★ 军需官/营地行挂 act 落航点（走 PD.MarkCampPoint 统一链路，静态映射 + API 后备解析 AreaID → uiMapID）',
       'function PD.MarkCampPoint(areaID, x, y)' in profui
       and 'CAMP_AREA_MAP[areaID]' in profui
       and 'C_Map.GetMapInfoFromAreaID' in profui
       and 'PD.MarkCampPoint(vd[7], vd[5], vd[6])' in profui
       and 'PD.MarkCampPoint(camp[6], camp[4], camp[5])' in profui)
    # ★★ 2026-09-24 六轮（方案 A 定稿）：五列总表 —— 对照列 + 烹饪折档 + 悬停完整详情
    _ctslice = profui[profui.index('function PD.BuildBonusTable'):
                      profui.index('local function ixCardSub(slug, p)')]
    ck('★★ 对照列取互斥字段（c[9] 职业版名）+ 增益 c[6] 绿字（7fdc7f）',
       'c[9]' in _ctslice and 'c[6]' in _ctslice and '7fdc7f' in _ctslice
       and 'Unpack(C_GREY)' in _ctslice)
    ck('★★ 烹饪特有档位折进相邻列并标注实际技能数；悬停行出完整详情（材料/图纸）',
       'format("(%d)", lv)' in _ctslice
       and 'PD.MatText(c[11])' in _ctslice and 'DG.ItemName(c[12][1])' in _ctslice)
    ck('★★ 静态映射两区齐备（wowhead g_mapperData 互证：44 赤脊山→1433 / 17 贫瘠之地→1413）',
       'local CAMP_AREA_MAP = { [44] = 1433, [17] = 1413 }' in profui)
    ck('★★ 区域名客户端优先：PD.CampZoneName 现取（GetMapInfoFromAreaID → GetAreaInfo 两级，失败回落数据原文）',
       'function PD.CampZoneName(areaID, fallback)' in profui
       and 'C_Map.GetAreaInfo' in profui
       and 'PD.CampZoneName(camp[6], tostring(camp[2] or ""))' in profui)
    ck('★ 两行都带悬停提示（点击：在地图上标记）',
       'L["点击：在地图上标记该 NPC"]' in profui
       and 'L["点击：在地图上标记此位置"]' in profui)
    # ★★ 2026-09-24 二轮：camping 不再多套一层工具钮 —— 页签直接改名「职业加成」，
    #    三视图切换钮只属于「有自己的营地物件」的专业（bonus 钮收到 hasCamp 分支里，12 空格缩进）。
    ck('★★ camping 页签改名「职业加成」、对照页不再套工具条一层（2026-09-24 用户定）',
       'bt:SetText(L["职业加成"])' in profui and 'bt:SetText(def.text)' in profui)
    # ⑦ 三轮版式补丁（2026-09-23 傍晚，用户逐条）
    # ★★ 行宽**不能**只由 col 决定：单列页的行也落在 col == 1，必须先看本屏有没有开两栏。
    #   （早先 col=1 恒给整幅 → 两栏页的第 1 栏反而铺满；col=1 恒给 COL_LW → 单列页全被压窄。
    #    两个方向都栽过，所以这条按「先 lvSplit 分流」来钉。）
    # ⚠️ 单列那一支要连**缩进**一起查：`w = PD.RIGHT_W - 2 * PD.LIST_PAD` 这个短串在
    #    PD.RowWidth 之类的别处也有一份（第 553 行），短串断言会恒真白测（实测漏抓过一条变异）。
    ck('★★ 行宽先看两栏举手（lvSplit / gridSplit）再按 col 分：两栏页 col1=半栏 / col2=半栏，单列页整幅',
       # ⚠️ 只查 `if PD.lvSplit then` 会恒真：PD.Layout 的分栏线里也有一句同形
       #   （实测 2 处），必须连缩进一起查才唯一。
       '                if PD.lvSplit then\n' in profui
       # 2026-09-24 总览 0.62 举手：lvSplit 支取宽走「splitLW 优先」的局部 lw/rw（见下方专条），
       #   这里查 gridSplit 支 + 单列支不动。
       and 'w = (col == 2) and rw or lw' in profui
       and 'w = (col == 2) and PD.GRID_RW or PD.GRID_LW' in profui
       # 单列那一支写成 `x, w = PD.LIST_PAD, ROW_W`，整幅宽来自 PD.PaintRows 顶部的 ROW_W。
       and '    local ROW_W = PD.RIGHT_W - 2 * PD.LIST_PAD\n' in profui
       and '                    x, w = PD.LIST_PAD, ROW_W\n' in profui)
    # ★★ 2026-10-09：专业页大列表「分帧 + 主界面顶部进度条」（与副本掉落页同一套家伙）。
    #   配方页「全部」最多 300 条 —— 原来在渲染那一帧里同步建出全部行帧，弱机器上主线程
    #   一次堵上百毫秒。现在渲染只算版式：行帧记进待建表，按每帧预算逐批建；
    #   进度条 / 分帧器 / 每帧预算整个复用副本掉落页那边那一套（同一根条）。
    _paint = profui[profui.index('function PD.PaintRows'):
                    profui.index('function PD.RowBorder')]
    _paintlive = '\n'.join(l.split('--')[0] for l in _paint.split('\n'))
    ck('★★ 专业页大列表分帧：待建表 / 每帧预算 / 进度条三件齐备（与掉落页同一套）',
       'PD.ROW_SYNC_MAX = 20' in profui
       and 'function PD.RealizePendingRow(e)' in profui
       and 'function PD.BuildPendRows()' in profui
       and 'function PD.FlushPendingRows()' in profui
       and 'DG.Gate.Begin(n)' in profui
       and 'DG.Gate.Advance(1)' in profui
       and 'DG.PushStep(PD.BuildPendRows)' in profui
       and 'DG.RunSteps()' in profui
       and 'DG.LOOT_ROW_FRAME_CAP' in profui
       and 'DG.Loader.budgetMs' in profui)
    ck('★★ 渲染那一帧不再同步建行帧（PaintRows 里没有裸建帧 / 没有直取新行，收尾交分帧器）',
       'CreateFrame' not in _paintlive
       and 'PD.Row(i)' not in _paintlive
       and 'PD.rows[i]' in _paintlive
       and 'PD.FlushPendingRows()' in _paintlive)
    ck('★ 量小走快速通道（不闪进度条），量大才交分帧器',
       '    if n < PD.ROW_SYNC_MAX then\n' in profui
       and 'DG.Gate.Begin(n)\n' in profui)
    ck('★ 间距行（kind == "gap"）也进待建表（跳号会在行池里留空洞）',
       'PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true }' in profui)
    # ★★ 2026-10-09 第七刀：实机 /dfprofperf rep 的「工具P」在**签名变化**的帧上恒为
    #   ~21ms、签名不变的帧 0.1ms ⇒ 那 21ms 是「建/换皮」的一次性成本。数量级 20 颗按钮
    #   × ~1ms 恰好对上 `ns.hui.SkinButton` 的 TryBuild：它挂在 SetSize/SetWidth/
    #   SetHeight/OnSizeChanged 四样上，而函数体是**无条件**销毁重建两副圆角边框帧。
    #   ★ 重建是纯浪费：两副边框帧都是 SetAllPoints()，所有角/边纹理都锚在帧上
    #     （DrawRoundBorder 里 `t:SetPoint(point, f, point, ox, oy)`）⇒ 尺寸自己跟。
    ck('★★ 皮按钮圆角边框帧不许在 SetSize 时重建（SetAllPoints，会自己跟尺寸走）',
       'if borderFrame then return end' in hui
       and 'ns.hui.__skinBuilds' in hui)
    # ★★ 2026-10-09 第七刀：行帧**已在池里**的那些原来一律在本帧同步重绑（实机 300 行
    #   上数据 37~42ms；从别的页签切回来那一次铺行 111.6ms）。现在只同步绑首屏。
    #   ★ 判据必须**同时**吃「行帧已存在」——光看 i 会把还没建的首屏行拖回来建帧。
    ck('★★ 行帧已在池里也只同步绑首屏，其余交分帧器（单帧不再重绑 300 行）',
       'function PD.SyncRows()' in profui
       and 'PD.SYNC_ROWS_BUF' in profui
       and 'local syncN = PD.SyncRows()' in _paintlive
       and 'if r and i <= syncN then' in _paintlive)
    # ★★ 2026-10-09 第八刀（rev14）：第七刀把「皮按钮帧」那行写成「sk>0 才打」⇒
    #   实机看不到它时无法区分「本版没加载」与「加载了但没建帧」。现在恒打 + rev。
    #   并把工具行闸门内部切四刀（16 颗按钮切页时吃 21~26ms，闸门里每样都便宜 ⇒
    #   必须实测拆开）。★ 计时器要**运行期动态取**（加载期抓局部会让替换失效）。
    _pt = profui[profui.index('function PD.PaintTool'):
                 profui.index('function PD.PaintLvTiles')]
    _ptlive = '\n'.join(l.split('--')[0] for l in _pt.split('\n'))
    ck('★★ 工具行闸门内部切四刀（尺寸/锚点/文本/显示），且「皮按钮帧」行恒打并带 rev',
       'PD.__pfT0, PD.__pfMark' in _ptlive
       and '_MK("闸-尺寸", _m0)' in _ptlive
       and '_MK("闸-锚点", _m0)' in _ptlive
       and '_MK("闸-文本", _m0)' in _ptlive
       and '_MK("闸-显示", _m0)' in _ptlive
       and 'function PD.__pfMark(' in profui
       and 'if sk > 0 then' not in profui
       and '（rev14' in profui)
    # ★★ 2026-10-09 第九刀（rev15）：实机把「工具P 25.0ms」逼到一句 `bt:Show()`
    #   上（闸门 16 开 = 尺寸 0.1 + 锚点 0.2 + 文本 0.1 + **显示 24.5**）。引擎
    #   Show 沿「Show 链」把 OnShow 打到子帧，而按钮的圆角边框帧挂的正是
    #   ReapplyStripPixels —— 它原来是 `for tex in pairs(pixelStrips)` **全表扫**
    #   （全插件一张弱表）⇒ 16 次 ≈ 24.5ms。必须改成帧内索引（O(本帧 4 条)），
    #   并留计数器把这条链钉死（否则下一轮又只能读代码猜）。
    ck('★★ 像素条复算走帧内索引（不许全表扫）+ 有计数器（rev15）',
       'ns.hui.__stripStat' in hui
       and 'local list = frame.__huiStrips' in hui
       and 'p.__huiStrips = list' in hui
       and 'PD.__pfAdd' in profui
       and '皮条纹复算：%d 次' in profui
       and '（rev15' in profui)
    # ★★ 2026-10-09 第十刀（rev16）：实机把「数据 20.8ms」一元分解成
    #   扫描 7.6 + 建spec 3.3 + 列宽材料 9.8（三项和 20.7），其中
    #   「材料串 9.1ms」整个包在「列宽材料」里 ⇒ FitRecipeCols 那 300 行
    #   里 93% 掉在**本帧画不到**的行上（列表封顶 300，本帧只同步绑首屏
    #   几十行，其余交分帧器）。材料串必须改成**按需算**：首屏现算、其余
    #   挂标，由 PD.BindRow 在**真绑上前**用同一个 PD.MAT_W 补算。
    #   ★ 缺了补算那一句，延后的行会空着材料列 —— 断言必须同时钉住两头。
    ck('★★ 配方页材料串按需算（首屏现算 / 其余挂标，绑前用同一个 PD.MAT_W 补算）',
       'function PD.FinishSpecMats(s)' in profui
       and 'local keep = PD.SyncRows()' in profui
       and 's._matsPending = true' in profui
       and 'if spec._matsPending then PD.FinishSpecMats(spec) end' in profui)
    # ★★ 第十一刀（rev17）：物品名 / 图标记忆表**正负分离 + 正向跨渲染持久**。
    #   原来每次 Render 开头把两表整个清空 ⇒ 到货重扫（0.5/1.5/4/9s）与任何一次
    #   重渲都要**重新向引擎要一遍全部物品名**（实机一页 428 次 GetItemInfo / 4.7ms，
    #   而那一页 `发包 0 次` ⇒ 名字本来就在客户端缓存里，全是白问）。名字一旦到货
    #   就不会再变 ⇒ 正向（_nmPos/_icPos）必须跨渲染留着，Render 只清负向。
    ck('★★ 物品名/图标记忆表正负分离：正向跨渲染持久，Render 只清「未到货」那半边',
       'local _nmPos, _nmPosN = {}, 0' in profui
       and 'local _nmNeg, _nmN = {}, 0' in profui
       and 'local _icPos, _icPosN = {}, 0' in profui
       and '_nmPos[id], _nmPosN = nm, _nmPosN + 1' in profui
       and '_nmNeg[id], _nmN = true, _nmN + 1' in profui
       and ('function PD.ResetItemNameMemo(hard)\n'
            '    _nmNeg, _nmN = {}, 0\n'
            '    _icNeg, _icN = {}, 0\n' in profui))
    # ★★ 第十一刀（rev17）：空闲预热 —— Render 收尾必须在空闲帧把当前专业的
    #   物品名先喂进持久记忆表（用户切到其它页签的那几百毫秒就是预热窗口）。
    ck('★★ 空闲预热：Render 收尾在空闲帧把当前专业的物品名喂进持久记忆表',
       'function PD.WarmNames()' in profui
       and 'function PD.WarmId(id)' in profui
       and '    PD.RequestRows(rows)\n    PD.WarmNames()' in profui
       and 'if DG.stepping then C_Timer.After(0, feed) return end' in profui)
    _pr = profui[profui.index('function PD.Render()'):
                 profui.index('function PD.RequestRows')]
    ck('★ 每轮渲染开头丢掉上一轮排下、还没建的行（否则它们会在新页面上冒出来）',
       'PD.__pendRows = {}' in _pr)
    ck('★ 设置页开关不对还没建出来的行取层级（nil 索引 = 整页炸）',
       'if PD.setOpen and spec.togKey and rr then' in profui)
    ck('★ 进度条自检入口（/dfprofgate，与 /dfgate 同款）',
       'function PD.StartGateDemo()' in profui
       and 'function PD.EndGateDemo()' in profui
       and 'SLASH_DUNGEONSFOREVERPROFGATE1 = "/dfprofgate"' in profui)
    ck('★★ 升级分段行不写「技能」二字（用户：左边就 1➡11）',
       '技能 %s → %s' not in profui and 'L["做 %s 个' not in profui
       and 'spec.rng' in profui and 'spec.cnt' in profui)
    # ★★★ 五轮（用户 2026-09-24）：「这个配方是向训练师学习，还是通过购买图纸之类的，
    #   是没有展示出来的」→ 分段行从「一行四样」改成**两行表格**。
    #   ★★★ 十轮（用户 2026-10-09）：「专业升级路线页面，我现在每行还是要显示这个配方的
    #   几级变绿、几级变黄」→ 名字下一行（原来源行）改放**四档技能色阶条**
    #   （学 / 黄 / 绿 / 灰 + 当前档落点竖线），来源压成名字右侧的小卡片。
    #   ★ 统一左缘不变：配方名行与色阶条都锚 PD.LV_NAME_X。
    ck('★★ 升级分段行：名字下一行是四档技能色阶条，来源压成名字右侧卡片（左缘仍 PD.LV_NAME_X）',
       '~%s 次制作' in profui
       and 'r.a:SetText(spec.rng or "")' in profui
       and 'r.e:SetText(spec.text or "")' in profui
       and 'r.c:SetText(spec.cnt or "")' in profui
       # 来源不再写进 r.b：新写法在位、旧写法必须彻底消失（两套并存 = 改了一半）
       and '        r.b:SetText("")\n' in profui
       and 'r.b:SetText(spec.src or "")' not in profui
       and 'function PD.LvTier(skill, learn, yellow, green, grey)' in profui
       and 'function PD.PaintSkillBar(r, vals, lvLo, lvHi, dim)' in profui
       and 'function PD.HideSkillBar(r)' in profui
       and 'function PD.PaintCard(r, card)' in profui
       and 'function PD.CardOf(rec, ri)' in profui
       # 两条新通道真的接上了 + 卡片宽度确实进了材料区预算
       and '            PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)\n' in profui
       and '        PD.PaintCard(r, spec.card)\n' in profui
       and '    PD.LV_CARD_W = math.ceil(cardNeed)\n' in profui
       # ⚠️ 这两句要连 8 空格缩进查：通用那一支也有 SetPoint("LEFT"...) 同形句，短串会恒真白测。
       and '        r.e:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY)\n' in profui
       and '        bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)\n' in profui)
    # ★★ 十轮：四档**等分**而不是按等级跨度 —— 数据里 learn == yellow 极常见
    #   （如 150/150/162/175），按真实跨度画「必升」那档宽度就是 0，会缺一块。
    ck('★★ 色阶条四档等分（learn == yellow 时「必升」档不许消失）+ 落点竖线',
       'PD.SB_COL = {' in profui
       and 'PD.SB_DY = -8' in profui
       and '    local seg = PD.LV_NAME_W / 4\n' in profui
       and 'if grey and skill >= grey then return 4 end' in profui
       and 'if yellow and skill >= yellow then return 2 end' in profui
       and 'function PD.SBValPos(skill, learn, yellow, green, grey, up)' in profui
       and 'PD.SB_EDGE = 4' in profui
       and '    return (t - 1) / 4\n' in profui
       and 'PD.SB_VAL' not in profui)
    # ★★ 十一轮：两根竖线 = 本行技能区间两端（左 = st[1] / 右 = st[2]）。
    # ★★ 十二轮（用户）：「竖线落在交界处」→ 吸到交界。
    # ★★ 十三轮（用户）：「106 已经大于 100 了，第二根竖线就要放在 100 的右边」→
    #   两头分向吸附：起点 lvLo 向下吸、终点 lvHi 向上吸（仍只停 0 / 0.25 / 0.50 / 0.75）。
    ck('★★ 两根竖线 = 本行技能区间两端（起点向下吸 / 终点向上吸）',
       '    r.__sbPin = {}\n' in profui
       and '                sbLo = segLo, sbHi = segHi,\n' in profui
       and '    local lvs = { lvLo, lvHi }\n' in profui
       and 'local xa = PD.SBValPos(lvs[1], vals[1], vals[2], vals[3], vals[4], false)' in profui
       and 'local xb = PD.SBValPos(lvs[2], vals[1], vals[2], vals[3], vals[4], true)' in profui
       and 'PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)' in profui
       and 'p:SetPoint("CENTER", r, "LEFT", PD.LV_NAME_X + x * PD.LV_NAME_W, PD.SB_DY)' in profui
       and 'r.__sbPin:SetPoint' not in profui
       and 'spec.sbTier' not in profui)
    # ★★ 十轮：来源卡片三分色 + 悬停 / 点击两条通道。
    ck('★★ 来源卡片三分色（训练师 / 图纸·掉落 / 图纸·商人）+ 悬停 __tipLines / 点击 __act',
       'PD.CARD_COL = {' in profui
       and 'trainer = { 0.29, 0.33, 0.40 }' in profui
       and 'kind = hasDrop and "drop" or (hasVendor and "vendor" or "drop")' in profui
       and '    z.__tipLines = card.lines\n' in profui
       and '    z.__act = card.act\n' in profui
       and '    z.__it = card.fid and { card.fid } or nil\n' in profui)
    # ★★ 五轮：材料不再走 r.f 那条 13pt 材料**串**（配方页仍在用），改走行子件**材料块**。
    #   七轮方案B（用户拍板）：块里**不写物品名**（4 材料的名字版一块 ~93px 放不下），
    #   块 = 图标 + ×N 角标（角标落在图标下方）；名字走悬停（悬停里始终有全量清单）。
    #   ⚠️ 必须连 8 空格缩进 + **紧随的下一句**一起查 `r.f:SetText("")`：配方页那一支是同一句的
    #      4 空格缩进版，短串断言会恒真白测（本项目踩过的坑）。
    #      （注释精简后尾注没了，靠下一句 `r.a:ClearAllPoints()` 消歧，强度不变。）
    ck('★★ 升级分段行的材料改走材料块（r.f 收干净；配方页的材料串口径不受影响）',
       '        r.f:SetText("")\n        r.a:ClearAllPoints()' in profui
       and '        PD.PaintMats(r, spec.blocks, spec.matCut, spec.passed)\n' in profui
       and '    local blocks, _, cut = PD.PackMats(mats, PD.LV_MAT_W)\n' in profui
       and 'blocks = blocks, matCut = cut,' in profui)
    # ★★ ㉑ 已过段落灰显（2026-09-29 用户定：制皮 42 → 「1 – 15」整段灰、图标也灰）——
    #   钉链路四件套：段落上限 < 当前技能判定（当前技能与左导航同一条 ProfLearned 链，
    #   未学不灰）、BindRow 灰分支 + 显式复位（行池复用不残留灰）、配方图标去饱和、
    #   材料块灰参贯通（图标去饱和 + 角标/「…」换灰）。
    _rl = profui[profui.index('function PD.RowsLeveling'):profui.index('function PD.RowsLegacy')]
    ck('★★ ㉑ 已过段落灰显：段落上限 < 当前技能（ProfLearned 同链），未学不灰',
       'local _learned = PD.ProfLearned()' in _rl
       and 'local curLv = _learned and _learned[PD.cur] and _learned[PD.cur].cur or nil' in _rl
       and 'local passed = (greyOn and over) or nil' in _rl
       and 'passed = passed,' in _rl)
    _bl = profui[profui.index('if spec.lvstep then'):profui.index('local padL = showIcon')]
    ck('★★ ㉑ 已过段落灰显：BindRow 灰分支 + 显式复位 + 配方图标去饱和',
       'if spec.passed then' in _bl
       and 'r.e:SetTextColor(Unpack(C_DIM))' in _bl
       and 'r.e:SetTextColor(Unpack(C_GOLD))' in _bl
       and 'r.icon:SetDesaturated(spec.passed and true or false)' in _bl)
    ck('★★ ㉑ 已过段落灰显：材料块灰参贯通（图标去饱和 + 角标/「…」换灰、显式复位）',
       'function PD.PaintMats(r, blocks, cut, grey)' in profui
       and 'b.ic:SetDesaturated(grey and true or false)' in profui
       and 'b.ct:SetTextColor(Unpack(grey and C_DIM or C_GOLD))' in profui
       and 'b.nm:SetTextColor(Unpack(grey and C_DIM or C_TEXT))' in profui
       and 'PD.PaintMats(r, spec.blocks, spec.matCut, spec.passed)' in profui)
    # ★★ ③ 专业页设置 + 当前段落外框（2026-09-29 用户定：齿轮在子页签行右端，点开是设置页；
    #   当前段 = 第一个未过分段，亮一圈主题绿外框；两个开关默认开，存 DungeonsForeverDB.prof）。
    ck('★★ ③ 设置页：齿轮入口 + DB 开关 + 点行切换 + 切页收起',
       'PD.SETTING_DEF = { greyPassed = true, hlCurrent = true }' in profui
       and 'function PD.Setting(k)' in profui
       and 'function PD.RowsSettings' in profui
       and '        PD.setOpen = not PD.setOpen\n' in profui
       and 'PD.setGear = gear' in profui
       and 'function PD.SetTab(key)\n    PD.setOpen = false' in profui
       and '        PD.tab = "overview"\n        PD.setOpen = false' in profui)
    ck('★★ ③ 当前段落外框：四条 1px 色条（行禁 edgeFile 的合规做法）+ cur 举手链',
       'r.bT = r:CreateTexture(nil, "BORDER")' in profui
       and 'function PD.RowBorder(r, on)' in profui
       and '    PD.RowBorder(r, spec.cur)' in profui
       and '                spec.cur = true' in profui
       and 'if PD.Setting("hlCurrent") and curLv ~= nil then' in profui)
    ck('★★ ㉒ iOS 开关：无限工具箱同款 ns.hui.ReskinToggle，摆位/绑定/翻转链齐全',
       'PD.SETTING_TOG_MAX = 4' in profui
       and '        ns.hui.ReskinToggle(tg)\n' in profui
       and 'function PD.PlaceSettingsToggles' in profui
       and '    PD.PlaceSettingsToggles(rows)\n    PD.scroll:SetVerticalScroll(0)' in profui
       and '            togKey = d.k,' in profui
       and '            tg.__key = spec.togKey' in profui
       and 'ProfDB()[self.__key] = not PD.Setting(self.__key)' in profui)
    # ★★ 七轮方案B：材料块**不写物品名**（PD.PackMats 不再量名、PD.PaintMats 不再 SetText(blk.name)），
    #   块宽 = max(图标, N 角标宽)；角标右对齐到块右缘（动作条堆叠数的读法）。
    #   八轮（用户）：「乘号删了」→ 角标只剩裸数字 format("%d", ...)，块宽随之再省一点。
    ck('★★ 方案B：材料块只画「图标 + N 角标」（不写物品名、无乘号；块宽 = max(图标, 角标宽)）',
       'local w = math.max(PD.TBL_ICON, PD.TextW(format("%d", cnt), PD.TBL_MAT_CNT_FS))' in profui
       and '        b.nm:Hide()\n' in profui
       and '        b.ct:SetPoint("RIGHT", r, "RIGHT", -(PD.COL_LW - right), PD.TBL_MAT_CNT_DY)\n' in profui
       and 'b.ct:SetText(format("%d", blk.cnt))' in profui
       # 旧的名字版/乘号版必须清干净（防两套并存）
       and 'PD.TextW(name, PD.TBL_MAT_FS)' not in profui
       and 'b.nm:SetText(blk.name)' not in profui
       and 'b.ct:SetText(format("×%d"' not in profui)
    # ★★ 七轮追补（用户）：角标压在图标上，「这个数字我需要你放大一下，放到 14，然后加上细描边」。
    #   hui 主题 FontFlags 恒 ""（无描边）→ 细描边 = 1px 阴影（详情页副行同款，双主题通用）。
    #   ⚠️ 字号数值不钉死（用户可调，同 TBL_ICON 教训）——只钉「字体串吃常量 + 阴影两行在」。
    #   ★ 八轮（用户）：角标「改成金色」→ 吃 C_GOLD（金色在双主题都是本插件强调色，
    #     与区间旁配方名/次数列同族）；数值不钉死颜色的 RGBA，钉常量名 C_GOLD。
    #   ★ 八轮追补（用户）：「描边不够明显」→ 细阴影升级为真·粗描边 THICKOUTLINE
    #     （数量类文字的描边豁免口径，双主题生效；1px 阴影保留叠加）。
    ck('★★ 数量角标金色（C_GOLD）+ THICKOUTLINE 粗描边 + 1px 阴影（压图标可读）',
       '    b.ct = MakeFS(r, PD.TBL_MAT_CNT_FS, C_GOLD, "LEFT")\n' in profui
       and '    b.ct:SetFont(ns.FONT, PD.TBL_MAT_CNT_FS, "THICKOUTLINE")\n' in profui
       and '    b.ct:SetShadowColor(0, 0, 0, 1)\n' in profui
       and '    b.ct:SetShadowOffset(1, -1)\n' in profui)
    # ★★ 五轮：材料块是**行的子件**（纹理 + 字体串），不是帧 —— 不进 FRAMES 计数、
    #   「切页零新建帧」纪律不变；而且**惰性建**（首次用到才建）。有对应变异钉住。
    ck('★★ 材料块是行子件、惰性建（不是帧；只看配方页时一个块都不建）',
       'function PD.RowBlk(r, j)' in profui
       and '    local b = r.blk[j]\n' in profui
       and '    if b then return b end\n' in profui
       and '    b.ic = r:CreateTexture(nil, "ARTWORK")\n' in profui
       and 'function PD.ClearMats(r)' in profui
       and '    PD.ClearMats(r)\n' in profui)
    # ★★ 五轮：来源补齐（数据里一直有、界面此前没取：训练师直学 / 需图纸·商人出售）。
    ck('★★ 分段行补上「来源」（向训练师学习 / 需图纸 · 商人出售；图纸名与掉落留给悬停）',
       'function PD.LevelSrc(rec)' in profui
       and 'L["向训练师学习"]' in profui and 'L["需图纸 · 商人出售"]' in profui
       and '            local src = PD.LevelSrc(rec)\n' in profui
       and '    local fid = rec[13] and rec[13][1]\n' in profui
       and '                src = src,\n' in profui)
    # ★★ 六轮（2026-10-09）：行级悬停提示框**退役**，改由「制作物 / 需求材料」各自出
    #   物品提示框。用户原话：「每行有个鼠标提示框，这个提示框不要了，改成当我们移动到
    #   制作物或需求材料的上方时，显示该物品的鼠标提示框。注意，这个提示框不使用我们的主题」。
    #   ① 分段行打 noTip（PD.Row 的 OnEnter 首行短路）⇒ 整行悬停不再出自拼段落提示框；
    #   ② 制作物热区 PD.IconZone 盖住「图标 + 名称列」、挂产物 itemID；
    #   ③ 材料块自带热区 b.zone，挂该材料 id、与图标同尺寸；
    #   ④ 两处共用 PD.WireTipZone（悬停高亮 / ShowItemTip / 滚轮转发 / Shift 发链接）。
    #   ★ 一律走 DG.ShowItemTip（= SetItemByID，带物品内容 ⇒ Hui 的 TooltipHasItemContent
    #     命中 ⇒ 强制暴雪原皮），这正是用户要的「不使用我们的主题」；热区里不得出现自绘皮肤。
    ck('★★ 升级行行级提示框退役、改出物品提示框（制作物 / 需求材料各自悬停；暴雪原皮）',
       '        if self.__noTip then return end\n' in profui
       and '    r.__noTip = spec.noTip\n' in profui
       and '                noTip = true,\n' in profui
       and 'function PD.IconZone(r)' in profui
       and '    r.__iconZone = z\n' in profui
       and '        iz.__it = itemID and { itemID } or nil\n' in profui
       and '        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)\n' in profui
       and 'function PD.WireTipZone(z, r)' in profui
       and '        elseif self.__it and DG.ShowItemTip then\n' in profui
       and '            DG.ShowItemTip(self, self.__it)\n' in profui
       # 滚轮转发钉**整块**（只钉函数头的话，把 DG.WheelScroll 掏空也抓不到）
       and '    z:SetScript("OnMouseWheel", function(self, delta)\n        DG.WheelScroll(PD.scroll, PD.child, delta)\n    end)\n' in profui
       # 行池跨页复用必须收起热区：不收起就留一个透明热区在旧位置吞鼠标（实机踩过）
       and '    if r.__iconZone then r.__iconZone:Hide() end\n' in profui
       and '        if b.zone then b.zone:Hide() end\n' in profui
       and '    b.zone.__it = { blk.id }\n' in profui
       and '    b.zone:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n' in profui
       and '    PD.WireTipZone(b.zone, r)\n' in profui
       # 行级提示框的自拼路径必须与升级行脱钩（noTip 已短路；不留下的写法）
       and '                lines = tip,\n' not in profui)
    # ★★ 七轮（2026-10-09）：配方页的「材料列 / 右下角商人」也做成热区。用户原话：
    #   「配方页面现在也这样修改 如果鼠标在材料上面，就显示材料的鼠标提示框
    #     如果鼠标在商人上面，就显示点击定位在地图上标记商人位置」。
    #   ① 材料列改**锚点分段链**（第 1 段沿用 r.f、第 2 段起 r.mn[i]）：位置交给引擎算 ——
    #      ns.hui.TextW 是**估算器**（图标按 fs + 2、空格走步进表），拿它摆热区必然漂；
    #      段间那两格空格跟着后一段走 ⇒ 与旧的 table.concat(out, "  ") 逐像素一致。
    #   ② 每段配一格热区 r.mz[i]（PD.MatZone → PD.WireTipZone）挂 { 该材料 itemID }；
    #      热区尺寸靠「锚到字串的 TOPLEFT / BOTTOMRIGHT」取得，全程零量宽。
    #   ③ 右下角那格用 PD.SourceParts 把**恒居末位**的「商人：X」拆到 r.dv（r.d 只留前缀，
    #      两半锚点链相接），热区只盖 r.dv；悬停出 PD.VendorLines（商人明细 +
    #      「点击：在地图上标记该 NPC」），点击落图。
    #   ④ PD.WireTipZone 扩两个通道：__tipLines（文字提示框）/ __act（自定义点击）。
    #   ⑤ 行池跨页复用：ClearMatSegs 必须把分段字串与热区一起收干净（透明热区吞鼠标）。
    ck('★★ 配方页：材料分段热区（悬停出该材料的物品提示框）+ 商人半段热区（点击定位落图）',
       'function PD.MatCol' in profui
       and 'return table.concat(out, "  "), w, n, segs\n' in profui
       and 'function PD.SourceParts(s)' in profui
       and 'out[#out + 1] = { text = format(L["商人：%s"], (v and v.name) or "?"), vendor = true }\n' in profui
       and 'function PD.MatSeg(r, i)' in profui
       and 'function PD.MatZone(r, i)' in profui
       and 'function PD.PaintMatSegs(r, segs, color)' in profui
       and 'function PD.ClearMatSegs(r)' in profui
       # 热区尺寸靠区域互锚（不让估算器参与摆热区）
       and '            z:SetPoint("TOPLEFT", fs, "TOPLEFT", 0, 1)\n' in profui
       and '            z:SetPoint("BOTTOMRIGHT", fs, "BOTTOMRIGHT", 0, -1)\n' in profui
       and '        if spec.matSegs then PD.PaintMatSegs(r, spec.matSegs, spec.matColor) end\n' in profui
       and '    r.mz = {}\n' in profui
       and '    r.dv = MakeFS(r, 11, C_GREY, "RIGHT")\n' in profui
       and '    if spec.dval and h > PD.ROW_H1 then\n' in profui
       and '        r.d:SetPoint("RIGHT", r.dv, "LEFT", 0, 0)\n' in profui
       and '        vz.__tipLines = PD.VendorLines(spec.src)\n' in profui
       and '        vz.__act = PD.VendorAct(spec.src)\n' in profui
       and '    PD.ClearMatSegs(r)\n' in profui
       # 反例：材料列不许退回「只画一整串」（那样就没有分段热区可挂）
       and '    if not spec.matSegs then r.f:SetText(spec.mats or "") end\n' in profui)
    # ★★ 五轮：配方图标与材料图标**同尺寸**（用户原话「这个图标大小和右边材料的图标大小
    #   明显不一样啊，我需要一致的」）—— 两处都吃 PD.TBL_ICON 一个常量。
    #   ⚠️ 数值本身**不钉死**（用户后来把 30 调成 24，写死数字让每次微调必红）——
    #   只钉「常量有定义 + 两侧 SetSize 都吃它 + 分段行不再走默认 20px」。
    ck('★★ 配方图标与材料图标同尺寸（都吃 PD.TBL_ICON；用户点名「两边大小不一样」）',
       re.search(r'PD\.TBL_ICON = \d+', profui) is not None
       and '        r.icon:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n' in profui
       and '    b.ic:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n' in profui
       # 分段行图标不再走默认 20px（通用那一支的 SetSize(20, 20) 仍在，故要连缩进查）
       and '        r.icon:SetSize(20, 20)\n' in profui)
    #   ②区间/图标/名称/次数**四列几何全部按本页数据现算**（写死时三位数区间「295 → 300」
    #     会压到名称上；名称列写死 150 又会在名称与材料之间留 122px 白）。
    #   ★ 五轮：区间改用**半角破折号**「–」（全角「→」太占宽，用户早前点名「区间可以再小一点」）。
    ck('★★ 升级行四列几何全按本页数据现算（区间/名称/次数/材料，无一写死）',
       # 区间串走半角破折号；全角「→」的写法必须一处不剩
       'local w = PD.TextW(format(L["%s – %s"], tostring(st[1]), tostring(st[2])), PD.LV_FS)'
           in profui
       and 'L["%s → %s"]' not in profui
       and 'PD.LV_ICON_X = 6 + math.ceil(rngW) + PD.TBL_RNG_GAP' in profui
       and 'PD.LV_NAME_X = PD.LV_ICON_X + PD.TBL_ICON + PD.TBL_NAME_GAP' in profui
       and 'PD.LV_CNT_W = math.max(40, math.ceil(cntW))' in profui
       and 'local nw = PD.TextW(SpellName(st[3]), PD.LV_FS)' in profui
       and 'local cw = PD.TextW(format(L["~%s 次制作"], tostring(st[4])), PD.LV_FS)' in profui)
    # ★★ 五轮：分配优先级 = **材料优先** —— 名称列只在「装得下本页最长名、且材料块仍放得下」
    #   的余量里长，余量不够就退回 PD.TBL_NAME_MIN。用户反复点名的「材料要显示完全」压过一切。
    ck('★★ 材料优先分配：名称列先按本页最长名取，余量不够就退回下限（材料块压过名称列）',
       'PD.LV_NAME_W = math.min(PD.TBL_NAME_MAX, math.max(PD.TBL_NAME_MIN, math.ceil(nameW)))'
           in profui
       and '    if avail - PD.LV_NAME_W < matNeed then\n' in profui
       and '        PD.LV_NAME_W = math.max(PD.TBL_NAME_MIN, avail - matNeed)\n' in profui
       and 'PD.LV_MAT_W = avail - PD.LV_NAME_W' in profui)
    ck('★★ 材料块预算里始终预留省略号那一格（PD.TBL_MARK_W —— 不预留就会画出半个块）',
       '        if total + step + PD.TBL_MARK_W > budget then\n' in profui
       and '        if mw + PD.TBL_MARK_W > matNeed then matNeed = mw + PD.TBL_MARK_W end\n'
           in profui)
    #   ③单行行（魔棒）不再拿「名称列宽」去截（关联任务区块已退役） —— 名称列现在可能只有 56px
    ck('★★ 单行行（魔棒）的截断宽与名称列解耦（名称列变窄不许跟着切任务名）',
       'local function FitL(s)\n        return PD.Fit(s, PD.LV_FS, PD.COL_LW - 120)\n    end' in profui
       and 'text = FitName(nm),' in profui
       and 'text = FitL(DG.ItemName(rd[2]))' in profui)
    # ★★ 二轮澄清（用户原话）：「右边这一列是显示需要准备的材料，这一列宽度可以很小，
    #    因为准备的材料只有一个物品名称和数量」—— 右栏是**汇总备料清单**（col = 2）。
    ck('★★ 升级页两栏分工：左栏「怎么练」(col 1) / 右栏「要准备的材料」(col 2)',
       'PushHead(rows, L["1 → 300 分段路线"], 1)' in profui
       and 'PushHead(rows, L["要准备的材料"], 2)' in profui
       # ★ 五轮：右栏两条标题缩短 —— **标题长度就是右栏宽的下限**（右栏能收到 152 的前提）。
       and 'PushHead(rows, L["商人直卖（无需自采）"], 2)' in profui
       and 'PushHead(rows, format(L["半成品（%d 种）"], #lv.parts), 2)' in profui
       # ⚠️ 负向检查要查**活代码**（剥注释）：文件头与 RowsLeveling 的注释里为了说明「改前/改后」
       #   仍写着旧标题原文，不剥注释的话「代码改了、注释留着」照样恒真（本项目的老坑）。
       and '商人直接卖的（不用自己攒）' not in _proflive
       and '半成品 / 中间产物' not in _proflive)
    ck('★★ 左栏取宽、右栏取窄（0.80：五轮分段行改两行表格后左栏要装的东西变多，再放宽一档）',
       'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)' in profui)
    ck('★★ 两栏页之间亮一条竖向分栏线（lvSplit→splitLW或COL_LW / gridSplit→GRID_LW，落点 = 两栏间隙中线；总览举手隐藏）',
       'PD.divider:SetPoint("TOPLEFT", PD.page, "TOPLEFT", mx, -top)' in profui
       # 沟距分源（2026-09-24 净距标准）：总览 lvSplit 用 OV_GUT（卡片净距换算），其余 COL_GAP。
       and 'local gut = PD.lvSplit and PD.OV_GUT or PD.COL_GAP\n' in profui
       and 'local mx = PD.RIGHT_X + PD.LIST_PAD + splitW + gut / 2\n' in profui
       and 'if PD.lvSplit then splitW = PD.splitLW or PD.COL_LW\n' in profui
       and 'elseif PD.gridSplit then splitW = PD.GRID_LW end\n' in profui
       # 总览竖线隐藏（2026-09-24 用户定）：两栏各有段落卡，竖线冗余。Layout 显隐认举手。
       and 'if splitW and not PD.hideDivider then' in profui
       and 'PD.hideDivider = true' in profui
       and 'PD.hideDivider = false' in profui)
    ck('★★ 分栏线抬到 BORDER 层、alpha 0.12（BACKGROUND 层会被大卡底色压灰，太淡等于没画）',
       'local divider = page:CreateTexture(nil, "BORDER")' in profui
       and 'divider:SetColorTexture(1, 1, 1, 0.12)' in profui)
    ck('★★ 新配方在名称右边补绿色「新」字（左缘竖条之外再加字）',
       '|cff40d940新|r' in profui and 'spec.is_new and L[" |cff40d940新|r"]' in profui)
    ck('★ 配方来源行不再显示「读物：xxx」（那是抓取子站名，不是游戏内读物）',
       '读物：' not in profui)
    #   （2026-10-09 v3：升级页底部「关联任务」区块已退役，断言随块删除）
    # ⑧ 五轮补丁（2026-09-23 晚，用户逐条）
    ck('★★ 配方页详情条整体退役（行内信息已足够，点击展开是重复信息）',
       'PD.detail' not in profui and 'PaintDetail' not in profui
       and 'PD.Chip' not in profui and 'PD.Select' not in profui
       and 'detailOn' not in profui and 'PD.sel' not in profui)
    ck('★★ 材料文本带小图标：数量与名字之间（6×|T图标|t中皮）',
       'function PD.MatIconTex' in profui
       and "format(\"%d×%s%s\", m[2] or 1, PD.MatIconTex(m[1]), DG.ItemName(m[1]))" in profui)
    # ⑨ 六轮补丁（2026-09-24：配方页材料进中间列 + 升级页左右两栏）
    ck('★★ 材料列文本按**分块宽度预算**生成（|T 转义串不能用 PD.TextW 直接量，量出来 300px 会把首料砍掉）',
       'function PD.MatCol' in profui and 'PD.TextW(cnt, fs) + px + PD.TextW(name, fs)' in profui
       and 'PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui)
    ck('★★ 配方行副行只剩部位等级（材料已搬进材料列）',
       'sub = tostring(r[5] or "")' in profui
       and 'PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' not in profui
       and 'PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui)
    # ★★ 2026-10-09 第二轮（用户：「加了进度条也没优化好，点配方那一瞬间有卡顿」）：
    #   点开配方页那一帧**不许再对全量建 spec** —— 列表封顶只画 PD.ROW_CAP 条，
    #   「过滤后多少条 + 名称列最宽多少」交给 PD.ScanRecipe 的轻量扫描
    #   （不建 spec / 不拼文案 / 不量材料串）。实测（_temp/_prof_render_prof.py，
    #   leatherworking 511 条）：整帧 28.5ms → 4.7ms，RecipeSpec 511 → 300 次，
    #   TextW 7391 → 300 次（PD.TextW 记忆化），DG.RequestItem 1349 → 392 次（去重）。
    ck('★★ 配方页首屏只为画得出来的行建 spec（不许对全量建 —— 点开那一帧的卡顿就出在这）',
       'function PD.ScanRecipe' in profui
       and 'PD.RecipeList(math.min(realN, PD.ROW_CAP), PD.searchQ)' in profui
       and 'PD.FitRecipeCols(list, maxW)' in profui)
    ck('★★ spec 不再预算材料串与行 tooltip 文案（FitRecipeCols 会用定稿列宽重算一遍，那里是纯白做）',
       'PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' not in profui
       and 'mkLines = function()' in profui
       and 'if self.__lines == nil and self.__mkLines then' in profui
       and 'r.__mkLines = spec.mkLines' in profui)
    ck('★ 量宽记忆化 + 物品请求按 id 去重（同一材料在几百条配方里重复量宽 / 重复请求）',
       'local _twMemo, _twN = {}, 0' in profui
       and 'if w ~= nil then return w end' in profui
       and 'if not id or seen[id] then return end' in profui)
    # ★★ 2026-10-09 第五轮：实机 79.8ms 剩下的部分全在「引擎调用次数」上 ——
    #   DG.ItemName → GetItemInfo 是**零缓存**引擎调用，一页配方 2228 次里大半是
    #   同一种材料反复查 ⇒ 改成事务内记忆化（Render 开头清空）。
    #   ★ 守护点必须是「**每次渲染清空**」：不清就会把「名字还没到货」那一刻的
    #     占位钉死一整局，物品到货后的重扫也刷不回来（页面永远停在「暂时没有客户端数据」）。
    # ★ 第十一刀（rev17）：机制改成「正负分离」—— 这条断言跟着换字面（守护点不变：
    #   「还没到货」那半边必须每次渲染清，否则到货重扫永远刷不回来）。
    ck('★★ 物品名记忆表每次渲染清空（不清就会把「名字还没到货」的占位钉死一整局）',
       'local _nmNeg, _nmN = {}, 0' in profui
       and ('function PD.ResetItemNameMemo(hard)\n'
            '    _nmNeg, _nmN = {}, 0\n'
            '    _icNeg, _icN = {}, 0\n' in profui)
       and 'function PD.ItemName(id)' in profui
       and 'PD.ResetItemNameMemo()' in _prender)
    # ★★ 2026-10-09 第六轮：实机「列宽材料 17.9ms（其中 材料串 17.2）」那一笔 ——
    #   材料图标查询原来**没记忆化**：PD.MatCol 每行每个材料都走
    #   PD.MatIconTex → DG.ItemIcon → DG.ItemInfo(id)（= GetItemInfo，零缓存引擎调用），
    #   一页 300 行 × 平均 3 材料 ≈ 900 次，且与物品名**同源**。离线实测
    #   取名(引擎) 1198 → 467（−61%）、真量宽 288 → 186。
    #   ★ 守护点：MatIconTex **不许**再直调 DG.ItemIcon（绕过记忆表 = 白做）；
    #     记忆表还必须**跟着 PD.ResetItemNameMemo 一起清**（否则「图标未到货」的
    #     占位会钉死一整局）。
    ck('★★ 材料图标查询走记忆化（一页上千次同源引擎调用；MatIconTex 不许绕过记忆表）',
       'function PD.ItemIcon(id)' in profui
       and 'local _icNeg, _icN = {}, 0' in profui
       and '    _icNeg, _icN = {}, 0' in profui
       and 'local ic = PD.ItemIcon(id)' in profui
       and 'local ic = DG.ItemIcon(id)' not in profui)
    # ★★ 2026-10-09 第六轮：轻量扫描**只给画得出来的行量宽**。
    #   列宽 maxW → PD.RECIPE_NAME_W 只要放得下**真正画出来的**那些行；第
    #   ROW_CAP+1 条往后根本不进列表 ⇒ 给它们量宽是纯白做（每次点开白量
    #   211 次取名 + 422 次量宽）。
    #   ★ 判据是「量宽被 n <= ROW_CAP 圈住」，**不是**「少扫了行」—— 计数 n 必须
    #     仍然精确（抬头要显示真实总数）。
    ck('★★ 配方页只给画得出来的行量宽（计数 n 仍精确；不许给 ROW_CAP 之后的行白量宽度）',
       'if n <= PD.ROW_CAP then' in profui
       and 'if w > maxW then maxW = w end' in profui)
    # ★★ 2026-10-09 第二轮收尾：上一轮的性能改写一度把**主路径的搜索过滤**整个绕过
    #   （主路径不再套 PD.SearchFilter），实机表现就是「搜索框形同虚设」。修法是
    #   把过滤挪进 PD.RecipeList 且**发生在建 spec 之前**（PD.RawHit 与 ScanRecipe
    #   共用同一口径，不许两边各写一套 —— 口径一漂，条数与行就对不上）。
    ck('★★ 搜索过滤在建 spec 之前（PD.RawHit 扫描/建表两处共用，不许绕过）',
       'function PD.RawHit' in profui
       and profui.count('PD.RawHit(r, q)') >= 2
       and profui.count('PD.EffKeyFilter(d)') >= 2)
    ck('★★ 配方页与升级页各自独立排版（配方页单列居中列 / 升级页整页两栏）',
       'PD.MAT_X = math.floor(PD.MAT_ROW_W * 0.40)' in profui
       and 'PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * LV_SPLIT)' in profui)

    # ⑩ 配方搜索 + 名称列现算（2026-10-09：第一列名称太宽 / 材料列截断太多 + 工具行右端加搜索框）
    ck('★★ 配方搜索框 Build 一次建好（帧数纪律）',
       'PD.searchBox = sb' in profui
       and 'CreateFrame("EditBox", nil, sb, "BackdropTemplate")' in profui)
    _otc = None
    if 'seb:SetScript("OnTextChanged"' in profui and 'seb:SetScript("OnEscapePressed"' in profui:
        _otc = profui[profui.index('seb:SetScript("OnTextChanged"'):
                                 profui.index('seb:SetScript("OnEscapePressed"')]
    ck('★★ 搜索框输入即滤：OnTextChanged 里更新搜索词并重渲染（不等回车）',
       _otc is not None and 'PD.searchQ = t' in _otc and 'PD.Render()' in _otc)
    ck('★★ 搜索按纯文本匹配（用户输入当字面量，不吃 Lua 模式字符；名称/副行/材料三路都查）',
       'function PD.SearchHit' in profui and 'function PD.SearchFilter' in profui
       and profui.count(', q, 1, true)') >= 3)
    ck('★★ 工具行给搜索框让位（首行右端留白，分类芯片不压搜索框）',
       'function PD.SearchReserve' in profui
       and 'PD.RIGHT_W - ((row == 0) and PD.SearchReserve() or 0)' in profui)
    ck('★★ 名称列按本页现算（量本页最宽名称/副行，剩余全给材料列；固定分割只在加载期兜底）',
       'function PD.FitRecipeCols' in profui
       and 'PD.MAT_X = nameW + PD.RECIPE_NAME_PAD' in profui
       and 's.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui
       and 'PD.SearchFilter(PD.RecipeList())' in profui)
    ck('★ 搜不到给中文空态提示（不许白屏）',
       'L["没有名称或材料匹配「%s」的配方 —— 换个关键词再试试。"]' in profui)
    ck('★ 材料列字体串吃 PD.MAT_FS（字号口径不许被旁路写死）',
       'r.f = MakeFS(r, PD.MAT_FS, C_TEXT, "LEFT")' in profui)
    ck('★ 升级页不再罗列「要学的法术」裸 ID（与分段路线重复，用户判无用）',
       'lv.learn' not in profui)
    ck('★ 对照总表只在 Build 里建帧、渲染期只改位置与显隐（池化纪律同款）',
       'function PD.BuildBonusTable' in profui and 'CreateFrame' not in _prender
       and 'PD.placeBonusTable(h1)' in profui and 'CampLevels' not in profui)
    # 名字可见系列此前只有动态断言；「不打 __named 标记」变异注入后动态块会在断言前抛异常
    # （脏抓）。这里补一条静态断言，让它在静态阶段就干净变红。
    _dui = open(os.path.join(ADDON, 'Core', 'DungeonUI.lua'), encoding='utf-8',
                errors='replace').read().replace('\r\n', '\n')
    ck('★ 名字到货打 __named 标记（重扫只扫没标记的卡，否则每轮白刷）',
       _dui.count('c.__named = hasName') == 4)

    # ---- ★★ 2026-10-09 变异重锚收尾：孤儿变异的配对静态断言 ----
    # 这些变异此前没有配对断言（或配对断言随重构过时），注入后零新增红 = 没人守。
    # 口径：钉住变异锚点行的存在性/计数 —— 基线全绿、注入变异必红（非恒真）。
    ck('★ 攻略页签在二级页签表里（key = "guide" 入口不被摘除）',
       _dui.count('key = "guide"') == 1)
    ck('★ 攻略页签激活时掉落滚动区让位（not isGuide 参与显隐判断）',
       _dui.count('SetShown(not isQuest and not isGuide and not isMap)') == 1)
    ck('★ 探索模块挂载点：ns.ExploreModule.Build(U.explorePage) 调用在（行池有主人）',
       _dui.count('ns.ExploreModule.Build(U.explorePage)') == 1)
    ck('★ 提示框预热不得提前短路（PrewarmLoot 必须真的发请求）',
       'if true then return end' not in _dui)
    ck('★ 掉落卡/任务行等 r:EnableMouseWheel(true) 共 4 处（压在卡上滚轮收得到）',
       _dui.count('r:EnableMouseWheel(true)') == 4)
    ck('★ 专业页：材料组右对齐（right = W - TBL_MAT_RPAD，不从左起摆）',
       profui.count('local right = W - PD.TBL_MAT_RPAD') == 1)
    ck('★ 专业页：名称→材料间距走 TBL_NAME_GAP（白留给材料列）',
       profui.count('local avail = rowW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP') == 1)
    ck('★ 专业页：备料清单标题行高走单倍行距（PushHead(..., 1)）',
       profui.count('PushHead(rows, format(L["材料（%d 种）"], #mats), 1)') == 1)
    ck('★ 卡片墙列数定版 4（DG.LOOT_COLS = 4；动态断言在 Lua 死区，静态兜底）',
       'DG.LOOT_COLS = 4' in _dui)

"""
if NS_ANCHOR not in text:
    sys.exit('未找到⑦步的 harness 插入锚点，上游可能已改动')
text = text.replace(NS_ANCHOR, NS_ANCHOR + NS_EXTRA, 1)

# ── ⑧ 顶栏胶囊：两颗（5人本 / 团本）+ 整体上移 10（2026-09-23 用户指定）────────
# 本插件侧由 port_dungeonsforever.py 的 CAPSULE_PATCHES 落地；这里往 harness 里插动态断言。
# 上移量只能静态钉（桩的 SetPoint 不记偏移，见上面 static_guard 里的断言）。
# 动态这半边要证明的是：**两颗真的能互斥切换**，且切到空态团本页时不去碰副本页的构建/刷新。
DYN_ANCHOR = (
    '    U:SwitchSub("Dungeons")\n'
    '    if U.dungeonPage == nil then ck("dungeonPage 页面帧未创建", false) return end\n'
    '    ck("★ SwitchSub 后副本页显示（漏 SetShown → 整页空白）", U.dungeonPage.__shown == true)\n'
    '    ck("副本页已构建", U.dungeonBuilt == true)\n'
)
DYN_EXTRA = r"""
    -- ---------- 顶栏胶囊：5人本 / 团本（2026-09-23 用户指定）----------
    -- 整块包 do...end：Lua 5.1 单函数 local 上限 200，本脚本很长，
    -- 块内临时变量出块即释放，不计入峰值。
    do
      -- ★ 分端：无限服（1.60.x）五颗，泰坦（3.8.x）两颗 —— 后三颗由 ns.IsForever 门控。
      ck("★ 胶囊行颗数分端（无限服 8 / 泰坦 2）",
         #(U.subTabs or {}) == (IS_FOREVER and 8 or 2), #(U.subTabs or {}))
      local _t1, _t2 = (U.subTabs or {})[1], (U.subTabs or {})[2]
      ck("★ 两颗胶囊 key = Dungeons / Raids",
         _t1 ~= nil and _t1.key == "Dungeons" and _t2 ~= nil and _t2.key == "Raids",
         tostring(_t1 and _t1.key) .. " / " .. tostring(_t2 and _t2.key))
      ck("★ 两颗胶囊文案 = 5人本 / 团本（用户 2026-09-23 改名）",
         _t1 ~= nil and _t1.text == "5人本" and _t2 ~= nil and _t2.text == "团本",
         tostring(_t1 and _t1.text) .. " / " .. tostring(_t2 and _t2.text))
      if IS_FOREVER then
        local _t3 = (U.subTabs or {})[3]
        ck("★ 无限服第三颗胶囊 key = Professions / 文案 = 专业",
           _t3 ~= nil and _t3.key == "Professions" and _t3.text == "专业",
           tostring(_t3 and _t3.key) .. " / " .. tostring(_t3 and _t3.text))
        local _t4 = (U.subTabs or {})[4]
        ck("★ 无限服第四颗胶囊 key = Explore / 文案 = 探索",
           _t4 ~= nil and _t4.key == "Explore" and _t4.text == "探索",
           tostring(_t4 and _t4.key) .. " / " .. tostring(_t4 and _t4.text))
        local _t5 = (U.subTabs or {})[5]
        ck("★ 无限服第五颗胶囊 key = Bis / 文案 = BIS配装",
           _t5 ~= nil and _t5.key == "Bis" and _t5.text == "BIS配装",
           tostring(_t5 and _t5.key) .. " / " .. tostring(_t5 and _t5.text))
      end
      local RM = TF_NS.RaidModule
      ck("★★ 团本页是常驻帧（已接 RaidModule 建页）", U.raidPage ~= nil and RM ~= nil)
      ck("★★ 团本页二级页签 = 时间线 / 列表",
         RM ~= nil and RM.tabs ~= nil and RM.tabs.timeline ~= nil and RM.tabs.list ~= nil)
      ck("★★ 时间轴节点 = 3 段（12/9 · 2027 春 · 2027 夏）",
         RM ~= nil and RM.nodes ~= nil and #RM.nodes == 3,
         RM and RM.nodes and tostring(#RM.nodes))
      ck("★★ 行池 7 / 卡片池 7（与数据条数对齐，渲染期不新建帧）",
         RM ~= nil and RM.rows ~= nil and #RM.rows == 7
         and RM.cards ~= nil and #RM.cards == 7,
         RM and RM.rows and (tostring(#RM.rows) .. " / " .. tostring(#(RM.cards or {}))))
      ck("★★ 首批三座中文名 = 深穴 / 海加尔峰 / 奥妮克希亚的巢穴",
         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].name == "深穴"
         and RM.DATA.raids[2].name == "海加尔峰"
         and RM.DATA.raids[3].name == "奥妮克希亚的巢穴")
      ck("★★ 首批同日开启（三座共用同一个开放窗口，日期由地区算出）",
         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].date == nil
         and RM.DATA.raids[1].first == true and RM.DATA.raids[3].first == true)
      ck("★★ 时间线首节点标签 = 地区算出的开放日（桩 GetLocale=zhCN ⇒ 国服口径）",
         RM ~= nil and RM.nodes ~= nil and RM.nodes[1].date == RM.FirstOpenText()
         and RM.nodes[1].date == "2026 年 12 月 10 日",
         tostring(RM and RM.nodes and RM.nodes[1] and RM.nodes[1].date))

      -- ★★ 卡墙几何（纯函数直调）：同档共线单行 / 不越右缘 / 不压规则块
      --    （2026-09-29 修：原先逐卡推进 y 会把卡排成斜梯，首档就压到规则块上）
      do
        local _big, _small = {}, {}
        for _, _rc in ipairs(RM.DATA.raids) do
          if _rc.first then _big[#_big + 1] = _rc else _small[#_small + 1] = _rc end
        end
        local _pb = RM.LayoutCards(_big, RM.LS_BIG_W, RM.LS_BIG_H, RM.BODY_Y + RM.LS_LABEL_H)
        local _ps = RM.LayoutCards(_small, RM.LS_SMALL_W, RM.LS_SMALL_H,
                                   _pb.bottom + RM.LS_LABEL_H)
        local _sameB, _sameS, _rb, _rs = true, true, 0, 0
        for i = 1, #_big do
          if _pb[i].y ~= _pb[1].y then _sameB = false end
          if _pb[i].x + RM.LS_BIG_W > _rb then _rb = _pb[i].x + RM.LS_BIG_W end
        end
        for i = 1, #_small do
          if _ps[i].y ~= _ps[1].y then _sameS = false end
          if _ps[i].x + RM.LS_SMALL_W > _rs then _rs = _ps[i].x + RM.LS_SMALL_W end
        end
        ck("★★ 卡墙·首批 3 大卡共线单行且不越右缘",
           #_big == 3 and _sameB and _pb.rows == 1 and _rb <= RM.X + RM.W,
           tostring(#_big) .. " 张 / " .. tostring(_pb.rows) .. " 行 / 右缘 " .. tostring(_rb))
        ck("★★ 卡墙·后续 4 小卡共线单行且不越右缘",
           #_small == 4 and _sameS and _ps.rows == 1 and _rs <= RM.X + RM.W,
           tostring(#_small) .. " 张 / " .. tostring(_ps.rows) .. " 行 / 右缘 " .. tostring(_rs))
        ck("★★ 卡墙整体不压到底部「团本规则」块", _ps.bottom < RM.RULES_RULE_Y,
           tostring(_ps.bottom) .. " < " .. tostring(RM.RULES_RULE_Y))
      end

      -- ★★ 倒计时（纯函数：喂定点 nowSec 即可复现）/ 国服待确定注记（2026-09-29 补）
      do
        local _tgt = RM.DATA.unlockAt
        ck("★★ 倒计时锚点 = 首批开放时刻 2026-12-09 13:00 PST",
           _tgt == 1796850000, _tgt)
        ck("★★ 地区移位：外服 0 天 / 国服 1 天（显式覆盖两档）",
           RM.DayShift(false) == 0 and RM.DayShift(true) == 1
           and RM.UnlockAt(false) == _tgt and RM.UnlockAt(true) == _tgt + 86400,
           tostring(RM.DayShift(false)) .. " / " .. tostring(RM.DayShift(true)))
        ck("★★ 自动判定（桩 GetLocale = zhCN ⇒ 国服口径，锚点 +1 天）",
           RM.DayShift() == 1 and RM.UnlockAt() == _tgt + 86400,
           tostring(RM.UnlockAt()))
        ck("★★ 开放日文案：外服 2026 年 12 月 9 日 / 国服 2026 年 12 月 10 日",
           RM.FirstOpenText(false) == "2026 年 12 月 9 日"
           and RM.FirstOpenText(true) == "2026 年 12 月 10 日",
           RM.FirstOpenText(false) .. " / " .. RM.FirstOpenText(true))
        ck("★★ 倒计时到「分」：各按自己的锚点算 ⇒ 都是 1 天 1 小时 1 分",
           RM.CountdownText(_tgt - (86400 + 3600 + 60), false)
               == "距首批开放还有 1 天 1 小时 1 分"
           and RM.CountdownText(_tgt + 86400 - (86400 + 3600 + 60), true)
               == "距首批开放还有 1 天 1 小时 1 分",
           RM.CountdownText(_tgt - (86400 + 3600 + 60), false))
        ck("★★ 国服在外服开放时刻尚未开启（锚点确实后移了一天）",
           RM.CountdownText(_tgt + 10, true) ~= "已开启"
           and RM.CountdownText(_tgt + 86400 + 10, true) == "已开启",
           RM.CountdownText(_tgt + 10, true))
        ck("★★ 倒计时跨过开放时刻即显示「已开启」（两档各自跨点）",
           RM.CountdownText(_tgt + 10, false) == "已开启",
           RM.CountdownText(_tgt + 10, false))
        -- ★★ 时钟解析链（2026-09-29 实机事故：os.time() 在客户端不存在）
        local _cT = RM.PickClock({ time = function() return 11 end })
        local _cS = RM.PickClock({ serverTime = function() return 22 end })
        ck("★★ 时钟解析链：优先全局 time()，次 GetServerTime()，最后离线桩 os.time",
           _cT ~= nil and _cT() == 11
           and _cS ~= nil and _cS() == 22
           and RM.PickClock({ os = { time = function() return 33 end } })() == 33
           and RM.PickClock({}) == nil and RM.PickClock(nil) == nil)
        ck("★★ 拿不到时钟时倒计时返回空串（不报错、不阻断 Build）",
           RM.CountdownText("no-clock") == "", tostring(RM.CountdownText("no-clock")))
        ck("★★ 无参调用走与游戏同款全局 time()（桩 time 固定 -> 现算得出文案）",
           RM.NowSec() == 1796850000 - 3660
           and RM.CountdownText() == "距首批开放还有 1 天 1 小时 1 分",
           tostring(RM.NowSec()) .. " / " .. tostring(RM.CountdownText()))
        ck("★★ 「国服待确定」注记已建且文案正确",
           RM.cnNote ~= nil and tostring(RM.cnNote.__text) == "国服待确定",
           RM.cnNote and tostring(RM.cnNote.__text))
        -- 卡墙分档说明只在列表子页渲染 -> 先切过去再取实际文案（否则这条永远是 nil 白测）
        RM.SetTab("list")
        ck("★★ 卡墙首档说明也走地区日期（列表子页实际渲染文案）",
           RM.wallLabels[2] ~= nil
           and tostring(RM.wallLabels[2].__text) == "2026 年 12 月 10 日 · 同日开启",
           RM.wallLabels[2] and tostring(RM.wallLabels[2].__text))
        RM.SetTab("timeline")
      end

      -- ---------- BIS配装页数据（2026-09-25 抓取；数据两端都加载，UI 由 LoadForeverPages 门控）----------
      do
        local B = TF_NS.BIS
        ck("★ BiS 数据已加载（Core/Data/Data_BIS.lua）",
           B ~= nil and type(B.classes) == "table")
        if B then
          ck("★ BiS 9 职业", #(B.classes or {}) == 9, tostring(#(B.classes or {})))
          local nSpec, nBadID, nThin, nRows0 = 0, 0, 0, 0
          for _, c in ipairs(B.classes) do
            for _, sp in ipairs(c.specs or {}) do
              nSpec = nSpec + 1
              local nSlot = 0
              for _, sides in pairs(sp.slots or {}) do
                nSlot = nSlot + 1
                for si = 1, 2 do
                  local s = sides[si]
                  if type(s) == "table" and type(s[1]) ~= "number" then
                    nBadID = nBadID + 1
                  end
                end
              end
              if nSlot < 13 then nThin = nThin + 1 end
              local nRows = 0
              for _ in pairs(sp.rows or {}) do nRows = nRows + 1 end
              if nRows < 13 then nRows0 = nRows0 + 1 end
            end
          end
          ck("★ BiS 专精共 17（2026-09-25 站点口径）", nSpec == 17, tostring(nSpec))
          ck("★ BiS 推荐件 itemID 均为纯数字", nBadID == 0, tostring(nBadID))
          ck("★ BiS 每专精推荐部位 ≥ 13", nThin == 0, tostring(nThin))
          ck("★ BiS 每专精备选部位 ≥ 13", nRows0 == 0, tostring(nRows0))
          if IS_FOREVER then
            ck("★ BiS 界面模块已挂（仅无限服）",
               TF_NS.BisModule ~= nil and type(TF_NS.BisModule.Build) == "function")
          end
        end
      end

      -- 切到团本：副本页隐、团本页显
      local _f0 = FRAMES
      U:SwitchSub("Raids")
      ck("★ 切团本 → 团本页显示", U.raidPage.__shown == true)
      ck("★ 切团本 → 副本页隐藏（两页互斥）", U.dungeonPage.__shown == false)
      ck("★ 切团本 → curSub = Raids", U.curSub == "Raids", tostring(U.curSub))
      ck("★ 切团本零新建帧（空态骨架不做构建）", FRAMES == _f0, FRAMES - _f0)
      ck("★ 选中态写进存档 subTab（开窗沿用上次那一颗）",
         DungeonsForeverDB ~= nil and DungeonsForeverDB.dungeon ~= nil
         and DungeonsForeverDB.dungeon.subTab == "Raids",
         DungeonsForeverDB and DungeonsForeverDB.dungeon
         and tostring(DungeonsForeverDB.dungeon.subTab))
      -- 开窗刷新路径：团本态下不得去刷按钮都没显示的副本页
      local _okU = pcall(U.UpdateActiveSub, U)
      ck("★ 团本态下 UpdateActiveSub 不报错", _okU == true)
      ck("★ 团本态下 UpdateActiveSub 不会把副本页刷出来", U.dungeonPage.__shown == false)

      -- 切回 5人本：副本页复原、内容仍在
      U:SwitchSub("Dungeons")
      ck("★ 切回 5人本 → 副本页显示", U.dungeonPage.__shown == true)
      ck("★ 切回 5人本 → 团本页隐藏", U.raidPage.__shown == false)
      ck("★ 切回 5人本 → curSub = Dungeons", U.curSub == "Dungeons", tostring(U.curSub))
      ck("★ 切回后副本页仍处于已构建态", U.dungeonBuilt == true)

      -- ---------- 探索页：顶栏第四颗（2026-09-24 用户定）----------
      if IS_FOREVER then
        ck("★★ 探索模块已挂载且行池建满 40 本",
           TF_NS.ExploreModule ~= nil and #(TF_NS.ExploreModule.rows or {}) == 40,
           TF_NS.ExploreModule and #(TF_NS.ExploreModule.rows or {}))
        local _qn = 0
        for _ in pairs(TF_NS.ExploreBookQuests or {}) do _qn = _qn + 1 end
        ck("★ 探索页上交任务 ID 表齐 40 条（自动识别已找到的依据）", _qn == 40, _qn)
        -- ★ 2026-10-04：任务组表（路线分组接力依据，游戏内事实分组 1/35/45/60）
        local _sn, _sbad = 0, 0
        local _sc = { [1] = 0, [35] = 0, [45] = 0, [60] = 0 }
        for _, rec in ipairs(TF_NS.ExploreBooks or {}) do
            local v = TF_NS.ExploreBookSet and TF_NS.ExploreBookSet[rec[1]]
            if v and _sc[v] then
                _sn = _sn + 1
                _sc[v] = _sc[v] + 1
            else
                _sbad = _sbad + 1
            end
        end
        ck("★ 探索页任务组表齐 40 本且组值合法（1/35/45/60 = 16/8/8/8）",
           _sn == 40 and _sbad == 0 and _sc[1] == 16 and _sc[35] == 8
           and _sc[45] == 8 and _sc[60] == 8,
           _sn .. "/" .. _sc[1] .. "," .. _sc[35] .. "," .. _sc[45] .. "," .. _sc[60])
        local _rn = 0
        for _ in pairs(TF_NS.ExploreBookRewards or {}) do _rn = _rn + 1 end
        ck("★ 探索奖励表齐 3 档（10本项链 / 20本戒指 / 25本三选一）", _rn == 3, _rn)
        if TF_NS.ExploreBookRewards and TF_NS.ExploreBookRewards[1] and TF_NS.ExploreBookRewards[2] then
          ck("★ 奖励档1 = 10本项链（questID 78150 + A/H 只存物品 ID：277203/277204）",
             TF_NS.ExploreBookRewards[1].at == 10
             and TF_NS.ExploreBookRewards[1].questID == 78150
             and TF_NS.ExploreBookRewards[1].items.A == 277203
             and TF_NS.ExploreBookRewards[1].items.H == 277204)
          ck("★ 奖励档2 = 20本戒指（questID 79536 修正 + A/H 只存物品 ID：281634/281635）",
             TF_NS.ExploreBookRewards[2].at == 20
             and TF_NS.ExploreBookRewards[2].questID == 79536
             and TF_NS.ExploreBookRewards[2].items.A == 281634
             and TF_NS.ExploreBookRewards[2].items.H == 281635)
        end
        if TF_NS.ExploreBookRewards and TF_NS.ExploreBookRewards[3] then
          local _t3 = TF_NS.ExploreBookRewards[3]
          local _c = _t3.choices or {}
          ck("★ 奖励档3 = 25本三选一（questID 82208 + choices 弓/徽记/小夜灯 277254/277258/277260）",
             _t3.at == 25 and _t3.questID == 82208
             and _t3.items == nil and #_c == 3
             and _c[1] == 277254 and _c[2] == 277258 and _c[3] == 277260)
        end
        if TF_NS.ExploreMageBonus then
          ck("★ 法师专属块数据（Research/Study + 轻羽毛 17056 + 4 行文案）",
             TF_NS.ExploreMageBonus.prof == "Research"
             and TF_NS.ExploreMageBonus.ability == "Study"
             and TF_NS.ExploreMageBonus.reagent == 17056
             and type(TF_NS.ExploreMageBonus.desc) == "table"
             and #TF_NS.ExploreMageBonus.desc == 4)
        end
        if TF_NS.ExploreBooks and TF_NS.ExploreRecIDs and TF_NS.ExploreZoneLv then
          local _nRec, _has = 0, {}
          for _ in pairs(TF_NS.ExploreRecIDs) do
            _nRec = _nRec + 1
            _has[_] = true
          end
          ck("★ 推荐清单恰 19 种且 ID 对位（2026-09-26 双站核实：阿拉塔瑞克移出→待确认）",
             _nRec == 19 and _has[203755] and _has[203754] and _has[207972]
             and _has[213165] and _has[215683] and _has[215815] and _has[215822]
             and not _has[210177],
             "推荐=" .. tostring(_nRec))
          local _nUnv, _both = 0, false
          if TF_NS.ExploreUnverIDs then
            for _iid in pairs(TF_NS.ExploreUnverIDs) do
              _nUnv = _nUnv + 1
              if _has[_iid] then _both = true end
            end
          end
          ck("★ 待确认清单恰 1 种（2026-10-13：阿拉塔瑞克已确认可拾取，仅剩 220347 菲拉斯移位书）、与推荐无交集",
             TF_NS.ExploreUnverIDs ~= nil and _nUnv == 1 and not _both
             and TF_NS.ExploreUnverIDs[220347] and not TF_NS.ExploreUnverIDs[210177],
             "待确认=" .. tostring(_nUnv))
          ck("★ 地图等级区间（艾尔文 5~10 / 荆棘谷 30~44 / 主城标「主城」）",
             TF_NS.ExploreZoneLv[12] == "5~10" and TF_NS.ExploreZoneLv[33] == "30~44"
             and TF_NS.ExploreZoneLv[1537] == "主城" and TF_NS.ExploreZoneLv[1637] == "主城")
          local _crimes
          for _, rec in pairs(TF_NS.ExploreBooks) do
            if rec[1] == 209849 then _crimes = rec end
          end
          ck("★ 坐标修正：侵犯人体的罪行 = 暗色河滩 16.6,28.5（站点玩家确认口径）",
             _crimes ~= nil and math.abs(_crimes[3] - 16.6) < 0.05
             and math.abs(_crimes[4] - 28.5) < 0.05,
             _crimes and (_crimes[3] .. "," .. _crimes[4]))
          local _r13d, _r17d, _r22d, _r8d
          for _, rec in pairs(TF_NS.ExploreBooks) do
            if rec[1] == 209846 then _r13d = rec
            elseif rec[1] == 215683 then _r17d = rec
            elseif rec[1] == 215820 then _r22d = rec
            elseif rec[1] == 208860 then _r8d = rec end
          end
          ck("★★ 路线书 3 本带 route 步骤链（第 8 字段、2 步、末步 = 主坐标；13 梦中人 / 17 几何学 / 22 木乃伊）",
             _r13d and #_r13d == 8 and type(_r13d[8]) == "table" and #_r13d[8] == 2
             and math.abs(_r13d[8][1][2] - 46.0) < 0.05 and math.abs(_r13d[8][1][3] - 36.5) < 0.05
             and math.abs(_r13d[8][2][2] - 52.8) < 0.05 and math.abs(_r13d[8][2][3] - 54.7) < 0.05
             and _r17d and #_r17d == 8 and type(_r17d[8]) == "table" and #_r17d[8] == 2
             and math.abs(_r17d[8][1][2] - 31.0) < 0.05
             and _r22d and #_r22d == 8 and type(_r22d[8]) == "table" and #_r22d[8] == 2
             and math.abs(_r22d[8][1][2] - 56.0) < 0.05,
             _r13d and type(_r13d[8]) == "table" and tostring(#_r13d[8]))
          ck("★ 二选一书（8 侏儒鲁米）不带 route（仍走第 7 字段 alt，暂不做右上双坐标）",
             _r8d and #_r8d == 7 and type(_r8d[7]) == "table" and _r8d[7][1] ~= nil
             and _r8d[7][1][1] == 40 and _r8d[8] == nil,
             _r8d and tostring(#_r8d))
        end
        if TF_NS.ExploreHowTo then
          ck("★ 「如何获得奖励」说明卡数据（标题 + intro/detail + 3 步）",
             TF_NS.ExploreHowTo.title == "如何获得奖励"
             and type(TF_NS.ExploreHowTo.intro) == "string" and TF_NS.ExploreHowTo.intro ~= ""
             and type(TF_NS.ExploreHowTo.detail) == "string" and TF_NS.ExploreHowTo.detail ~= ""
             and type(TF_NS.ExploreHowTo.steps) == "table" and #TF_NS.ExploreHowTo.steps == 3
             and TF_NS.ExploreHowTo.steps[2].t == "交给你的图书馆员")
        end
        local _mn = 0
        if TF_NS.ExploreModule then
          -- ScanAuto 在桩环境跑一遍：桩没有 GetItemCount/C_QuestLog 应静默跳过、不报错
          local _ok = pcall(TF_NS.ExploreModule.ScanAuto)
          ck("★ ScanAuto 桩环境静默降级（无 API 不炸）且产出空表",
             _ok and type(TF_NS.ExploreModule._auto) == "table", _ok)
        end
        local _fe0 = FRAMES
        U:SwitchSub("Explore")
        ck("★ 切探索 → 探索页显示", U.explorePage ~= nil and U.explorePage.__shown == true)
        ck("★ 切探索 → 专业页隐藏（页面互斥）", U.profPage ~= nil and U.profPage.__shown == false)
        ck("★ 切探索 → curSub = Explore", U.curSub == "Explore", tostring(U.curSub))
        ck("★ 切探索零新建帧（骨架首屏一次建全）", FRAMES == _fe0, FRAMES - _fe0)
        ck("★ 切探索把选中态写进存档（与团本/专业同口径）",
           DungeonsForeverDB ~= nil and DungeonsForeverDB.dungeon ~= nil
           and DungeonsForeverDB.dungeon.subTab == "Explore",
           DungeonsForeverDB and DungeonsForeverDB.dungeon
           and tostring(DungeonsForeverDB.dungeon.subTab))
        -- 左列导航（2026-09-24 用户定）：条目右侧实时进度小字 = n/40 口径
        do
          local _nb = TF_NS.ExploreModule and TF_NS.ExploreModule.navBooks
          ck("★★ 左列导航「40本书」条目在（含实时进度小字 n/40）",
             _nb ~= nil and _nb.__pv ~= nil
             and tostring(_nb.__pv.__text):match("^%d+/40$") ~= nil,
             _nb and _nb.__pv and tostring(_nb.__pv.__text))
          -- ★ 进页即刷（2026-09-26 用户定）：停在睡袋/战斗法师子页也要刷导航进度 ——
          --   刷点挪进 PaintNav（Render 必走），不再等点开「40本书」清单。
          --   硬断言 = 计数随存档打卡变化：睡袋态 Render 后 __pv 必须 +1（而非仅格式匹配）。
          local _EM2 = TF_NS.ExploreModule
          local _dbN = TF_NS.DB()
          _dbN.explore = _dbN.explore or {}
          _dbN.explore.found = _dbN.explore.found or {}
          local _bid = TF_NS.ExploreBooks and TF_NS.ExploreBooks[1] and TF_NS.ExploreBooks[1][1]
          local _had = _bid and _dbN.explore.found[_bid] and true or false
          _dbN.explore.subPage = "books"
          pcall(_EM2.Render)
          local _n0 = tonumber(tostring(_nb.__pv.__text):match("^(%d+)/"))
          _dbN.explore.subPage = "bag"
          _dbN.explore.found[_bid] = true
          local _okBag = pcall(_EM2.Render)
          local _n1 = tonumber(tostring(_nb.__pv.__text):match("^(%d+)/"))
          _dbN.explore.found[_bid] = nil
          local _okBm = pcall(_EM2.Render)
          _dbN.explore.subPage = "books"
          ck("★ 导航进度进页即刷：睡袋态 Render 后 __pv 计数随打卡 +1（PaintNav 必走，不等点开清单）",
             _okBag and _okBm and _bid ~= nil and _n0 ~= nil
             and _n1 == _n0 + (_had and 0 or 1),
             string.format("n0=%s n1=%s first=%s", tostring(_n0), tostring(_n1), tostring(_bid)))
        end
        local _okE = pcall(U.UpdateActiveSub, U)
        ck("★ 探索态下 UpdateActiveSub 不报错", _okE == true)
        -- 奖励子页：切过去 rwFrame 显示、清单件隐藏；切回 40本书 复原
        local EM = TF_NS.ExploreModule
        if EM and EM.rwFrame then
          local _db = TF_NS.DB()
          _db.explore = _db.explore or {}
          -- ★ 行名后缀（2026-09-25 用户定）：等级 = 所在地图等级区间；站点核实书 = 金色 ★推荐
          _db.explore.subPage = "books"
          local _okB = pcall(EM.Render)
          -- ★ 行内胶囊徽章（2026-09-25 用户定方案 A）：阵营/等级/推荐/待确认
          local _r1, _r5, _r21, _r19 = EM.rows and EM.rows[1], EM.rows and EM.rows[5],
                                        EM.rows and EM.rows[21], EM.rows and EM.rows[19]
          ck("★ 行1（艾尔文 5~10·推荐）：领地胶囊=联盟领地 + 等级胶囊 + 推荐金胶囊、无待确认",
             _okB and _r1 ~= nil and _r1.fTag ~= nil and _r1.lvTag ~= nil
             and _r1.lvTag.t ~= nil and _r1.recTag ~= nil and _r1.unTag ~= nil
             and _r1.fTag.__shown == true
             and tostring(_r1.fTag.t.__text) == "联盟领地"
             and tostring(_r1.lvTag.t.__text) == "5~10级"
             and tostring(_r1.recTag.t.__text) == "推荐"
             and tostring(_r1.a.__text):find("★推荐", 1, true) == nil
             and _r1.unTag.__shown == false
             and _r1.unStrike ~= nil and _r1.unStrike.__shown == false
             and _r1.a.__textColor ~= nil and math.abs(_r1.a.__textColor[1] - 0.88) < 1e-6,
             _r1 and _r1.lvTag.t and tostring(_r1.lvTag.t.__text))
          ck("★ 行5（阿拉塔瑞克·银松 10~20）：领地胶囊=部落领地、2026-10-13 已确认可拾取 → 无待确认标、无书名删除线",
             _r5 ~= nil and _r5.fTag ~= nil and _r5.lvTag ~= nil
             and _r5.fTag.__shown == true
             and tostring(_r5.fTag.t.__text) == "部落领地"
             and tostring(_r5.lvTag.t.__text) == "10~20级"
             and _r5.unTag.__shown ~= true
             and _r5.unStrike ~= nil and _r5.unStrike.__shown ~= true,
             _r5 and _r5.lvTag.t and tostring(_r5.lvTag.t.__text))
          ck("★ 行21（荆棘谷 30~44·推荐）：等级胶囊 + 推荐金胶囊、无阵营胶囊",
             _r21 ~= nil and _r21.lvTag ~= nil
             and tostring(_r21.lvTag.t.__text) == "30~44级"
             and tostring(_r21.recTag.t.__text) == "推荐"
             and _r21.fTag.__shown == false,
             _r21 and _r21.lvTag.t and tostring(_r21.lvTag.t.__text))
          -- 2026-09-29 三方核对：网罗谎言（行19）已被双站确认 → 待确认/删除线全撤、书名回白
          ck("★ 行19（阿拉希 30~40·已确认）：等级胶囊在、待确认/删除线全撤、书名回白",
             _r19 ~= nil and _r19.lvTag ~= nil
             and tostring(_r19.lvTag.t.__text) == "30~40级"
             and _r19.unTag.__shown == false
             and _r19.recTag.__shown == false
             and _r19.unStrike ~= nil and _r19.unStrike.__shown == false
             and _r19.a.__textColor ~= nil and math.abs(_r19.a.__textColor[1] - 0.88) < 1e-6,
             _r19 and _r19.lvTag.t and tostring(_r19.lvTag.t.__text))
          local _r26 = EM.rows and EM.rows[26]
          ck("★ 行26（The Liminal and the Arcane·菲拉斯·移位失踪）：待确认灰胶囊 + 删除线 + 书名灰",
             _r26 ~= nil and _r26.unTag ~= nil
             and tostring(_r26.unTag.t.__text) == "待确认"
             and _r26.recTag.__shown == false
             and _r26.unStrike ~= nil and _r26.unStrike.__shown == true
             and _r26.a.__textColor ~= nil and math.abs(_r26.a.__textColor[1] - 0.55) < 1e-6,
             _r26 and _r26.unTag.t and tostring(_r26.unTag.t.__text))
          -- ★★ 路线书坐标链（2026-09-29 用户定）：右上「区名 入口x,y → 末步x,y」，每段可点
          local _rc13 = EM.rows and EM.rows[13]
          ck("★ 行13（梦中人的秘密）路线链：r.c2=入口 46.0, 36.5、r.arr=→、r.c=末步 52.8, 54.7、同区不重复区名",
             _rc13 ~= nil and _rc13.c2 ~= nil and _rc13.arr ~= nil
             and tostring(_rc13.c2.__text) == "46.0, 36.5"
             and tostring(_rc13.arr.__text) == "→"
             and tostring(_rc13.c.__text) == "52.8, 54.7"
             and tostring(_rc13.d2.__text) == "",
             _rc13 and _rc13.c2 and tostring(_rc13.c2.__text))
          ck("★ 行13 两段点击钮都亮出（pin 依赖文本非空，桩 GetStringWidth 缺失走估宽兜底）",
             _rc13 ~= nil and _rc13.s1 ~= nil and _rc13.s2 ~= nil
             and _rc13.s1.__shown == true and _rc13.s2.__shown == true
             and _rc13.s1.__loc ~= nil and math.abs(_rc13.s1.__loc[2] - 46.0) < 0.05
             and math.abs(_rc13.s2.__loc[2] - 52.8) < 0.05,
             _rc13 and _rc13.s1 and tostring(_rc13.s1.__shown))
          do
            local _cap = nil
            local _mp = EM.MarkPoint
            EM.MarkPoint = function(a, x, y) _cap = { a, x, y } end
            local _b1 = _rc13 and _rc13.s1
            if _b1 and _b1.__scripts and _b1.__scripts.OnClick then
              _b1.__scripts.OnClick(_b1)
              ck("★★ 点行13 第一段 → 只落入口点（贫瘠之地 46.0,36.5，不落末步）",
                 _cap ~= nil and _cap[1] == 17
                 and math.abs(_cap[2] - 46.0) < 0.05 and math.abs(_cap[3] - 36.5) < 0.05,
                 _cap and (_cap[1] .. "," .. tostring(_cap[2])))
            end
            local _b2 = _rc13 and _rc13.s2
            if _b2 and _b2.__scripts and _b2.__scripts.OnClick then
              _cap = nil
              _b2.__scripts.OnClick(_b2)
              ck("★★ 点行13 第二段 → 落书的位置（52.8,54.7）",
                 _cap ~= nil and _cap[1] == 17
                 and math.abs(_cap[2] - 52.8) < 0.05 and math.abs(_cap[3] - 54.7) < 0.05,
                 _cap and (_cap[1] .. "," .. tostring(_cap[2])))
            end
            EM.MarkPoint = _mp
          end
          local _rc1 = EM.rows and EM.rows[1]
          ck("★ 行1（非路线书）无链：c2/arr 空、点击钮不亮（单坐标书外观不变）",
             _rc1 ~= nil and _rc1.c2 ~= nil and _rc1.s1 ~= nil
             and tostring(_rc1.c2.__text) == ""
             and tostring(_rc1.arr.__text) == ""
             and _rc1.s1.__shown == false and _rc1.s2.__shown == false,
             _rc1 and _rc1.s1 and tostring(_rc1.s1.__shown))
          local _rn2 = 0
          for _ in pairs(EM.rwRows or {}) do _rn2 = _rn2 + 1 end
          ck("★ 奖励行池 = 7 条（2 档 × 联盟/部落 + 25 本档三选一 3 行）", _rn2 == 7, _rn2)
          _db.explore.subPage = "rewards"
          local _okR = pcall(EM.Render)
          ck("★ 切奖励子页 → rwFrame 显示、listCard 大底卡常驻（方案 A：底板不随子页切换）",
             _okR and EM.rwFrame.__shown == true and EM.listCard.__shown == true
             and EM.navCard ~= nil and EM.navCard.__shown == true)
          ck("★ 奖励态：奖励钮保持可见（入口不随筛选件一起隐藏）",
             _okR and EM.rwBtn ~= nil and EM.rwBtn.__shown ~= false)
          ck("★ 奖励态：筛选行/进度条/进度文本/徽章常显（2026-09-24 用户定：奖励态要留返回按钮）",
             _okR and EM.filterBtns and EM.filterBtns.all and EM.filterBtns.all.__shown ~= false
             and EM.bar ~= nil and EM.bar.__shown ~= false
             and EM.prog ~= nil and EM.prog.__shown ~= false)
          ck("★ 奖励态：档位标题落了文本（建骨架时一直空着的 rwHead 补上门槛文案）",
             _okR and EM.rwHead1 ~= nil and EM.rwHead1.__text ~= nil
             and tostring(EM.rwHead1.__text) ~= "",
             EM.rwHead1 and tostring(EM.rwHead1.__text))
          ck("★★ 奖励页三卡同排：rwCards 齐 3 张、rwHead3/state 落文本（2026-10-03 重构）",
             _okR and type(EM.rwCards) == "table" and #EM.rwCards == 3
             and EM.rwHead3 ~= nil and tostring(EM.rwHead3.__text) ~= ""
             and EM.rwCards[3].state ~= nil and tostring(EM.rwCards[3].state.__text) ~= "",
             EM.rwCards and #EM.rwCards)
          -- ★ 2026-10-04 用户定：卡右上角显示接任务的等级要求（req = 1/20/30，wowhead 任务页口径）
          ck("★★ 奖励卡右上角等级：三卡 lv 落文本 = 要求等级 1 / 20 / 30",
             _okR and EM.rwCards[1].lv ~= nil and tostring(EM.rwCards[1].lv.__text) == "要求等级 1"
             and tostring(EM.rwCards[2].lv.__text) == "要求等级 20"
             and tostring(EM.rwCards[3].lv.__text) == "要求等级 30",
             EM.rwCards[1].lv and tostring(EM.rwCards[1].lv.__text))
          ck("★ 说明卡建骨架（howCard + 3 步文案落位）",
             _okR and EM.howCard ~= nil and type(EM.howSteps) == "table" and #EM.howSteps == 3
             and EM.howSteps[1].__text ~= nil and tostring(EM.howSteps[1].__text):find("搜索书籍", 1, true) ~= nil,
             EM.howSteps and tostring(EM.howSteps[1].__text))
          -- ★★ 奖励名客户端取：items 只存物品 ID，名称 = 运行时按 ID 问客户端。
          --   给 GetItemInfo 桩后重渲染，四行行名必须全变成桩名「测物<ID>」——
          --   防止再退回「英文名写死进数据表」的旧口径。
          GetItemInfo = function(id)
            return "测物" .. tostring(id), "|Hitem:" .. tostring(id) .. "|h[x]|h", 3
          end
          local _okR2 = pcall(EM.Render)
          local _n1 = _okR2 and EM.rwRows[1] and EM.rwRows[1].name
             and tostring(EM.rwRows[1].name.__text) or ""
          local _okN = _n1 == "测物277203"
             and EM.rwRows[2] and EM.rwRows[2].name ~= nil
             and tostring(EM.rwRows[2].name.__text) == "测物277204"
             and EM.rwRows[3] and EM.rwRows[3].name ~= nil
             and tostring(EM.rwRows[3].name.__text) == "测物281634"
             and EM.rwRows[4] and EM.rwRows[4].name ~= nil
             and tostring(EM.rwRows[4].name.__text) == "测物281635"
             and EM.rwRows[5] and EM.rwRows[5].name ~= nil
             and tostring(EM.rwRows[5].name.__text) == "测物277254"
             and EM.rwRows[6] and EM.rwRows[6].name ~= nil
             and tostring(EM.rwRows[6].name.__text) == "测物277258"
             and EM.rwRows[7] and EM.rwRows[7].name ~= nil
             and tostring(EM.rwRows[7].name.__text) == "测物277260"
          ck("★★ 奖励行名 = 客户端按物品 ID 解析（桩给「测物<ID>」→ 七行全命中）",
             _okN == true, _n1)
          GetItemInfo = nil
          _db.explore.subPage = "books"
          local _okB = pcall(EM.Render)
          ck("★ 切回 40本书 → listCard 显示、rwFrame 隐藏",
             _okB and EM.listCard.__shown == true and EM.rwFrame.__shown == false)
          -- ---------- 探索地图层（2026-10-04）：模块导出 + 规划器粗排行为 ----------
          ck("★ 探索地图层三口齐（On 状态口 / Toggle 开关 / PlanRoute 规划器）",
             type(TF_NS.ExploreMapOn) == "function"
             and type(TF_NS.ExploreMapToggle) == "function"
             and type(TF_NS.ExploreMapPlanRoute) == "function"
             and TF_NS.ExploreMapOn() == false)
          do
            local _okP, _route = pcall(TF_NS.ExploreMapPlanRoute)
            local _steps = type(_route) == "table" and #_route or 0
            local _uniq, _seen, _first, _ids = true, {}, nil, {}
            for _, s in ipairs(type(_route) == "table" and _route or {}) do
                if s.rec == nil or _seen[s.rec] then _uniq = false end
                _seen[s.rec] = true
                _ids[s.rec[1]] = true
                if _first == nil then _first = s.rec[1] end
            end
            local _noUnver = not _ids[220347]
            ck("★★ 探索路线规划器（桩环境粗排）：39 本全入路径（存疑 1 本默认排除）、每本恰一站、首站属组1",
               _okP and _steps == 39 and _uniq and _noUnver
               and _first ~= nil and TF_NS.ExploreBookSet[_first] == 1,
               _steps)
            TF_NS.DB().explore = TF_NS.DB().explore or {}
            TF_NS.DB().explore.mapCfg = { showUnver = true }
            local _okP2, _route2 = pcall(TF_NS.ExploreMapPlanRoute)
            local _steps2 = type(_route2) == "table" and #_route2 or 0
            ck("★★ 设置勾选「包含存疑书籍」→ 规划器恢复 40 本",
               _okP2 and _steps2 == 40, _steps2)
            TF_NS.DB().explore.mapCfg = nil
          end
          -- ---------- 睡袋子页（2026-09-24 两列式）：左列任务链 + 右列详情/总奖励 ----------
          do
            local _bb = EM.navBtns and EM.navBtns["bag"]
            ck("★ 睡袋导航钮在（navBtns.bag 挂 OnClick）",
               _bb ~= nil and _bb.__scripts ~= nil and _bb.__scripts.OnClick ~= nil)
            if _bb and _bb.__scripts and _bb.__scripts.OnClick then
              _bb.__scripts.OnClick(_bb)
              ck("★★ 点睡袋 → bagFrame 显示、滚动区隐藏、subPage=bag 落存档",
                 EM.bagFrame ~= nil and EM.bagFrame.__shown == true
                 and EM.scroll ~= nil and EM.scroll.__shown == false
                 and TF_NS.DB().explore.subPage == "bag")
              ck("★ 睡袋态：书本专属件整组让位（筛选行/进度条/奖励钮/注释隐藏）",
                 EM.filterBtns and EM.filterBtns.all and EM.filterBtns.all.__shown == false
                 and EM.bar ~= nil and EM.bar.__shown == false
                 and EM.rwBtn ~= nil and EM.rwBtn.__shown == false
                 and EM.note ~= nil and EM.note.__shown == false)
              ck("★★ 睡袋两列骨架：左列 7 行行池 + 右列详情/总奖励双卡 + 芯片池 20 + 阵营胶囊",
                 EM.bagRows and #EM.bagRows == 7
                 and EM.bagDetail ~= nil and EM.bagTotal ~= nil
                 and EM.bagChips and #EM.bagChips == 20
                 and EM.bagFacBtns ~= nil and EM.bagFacBtns.A ~= nil and EM.bagFacBtns.H ~= nil
                 and EM.bagProg ~= nil)
              local _rwb = EM.bagRwBtn
              if _rwb and _rwb.__scripts and _rwb.__scripts.OnClick then
                _rwb.__scripts.OnClick(_rwb)
                ck("★ 点任务线奖励 → 总奖励态（bagTotal 显示、详情隐藏）",
                   EM.bagTotal.__shown == true and EM.bagDetail.__shown == false)
                _rwb.__scripts.OnClick(_rwb)
                ck("★ 再点回详情态（bagDetail 显示、bagTotal 隐藏）",
                   EM.bagDetail.__shown == true and EM.bagTotal.__shown == false)
              end
              local _bk2 = EM.navBtns and EM.navBtns["books"]
              if _bk2 and _bk2.__scripts and _bk2.__scripts.OnClick then
                _bk2.__scripts.OnClick(_bk2)
                ck("★ 点回 40本书 → bagFrame 隐藏、滚动区/筛选行复原",
                   EM.bagFrame.__shown == false and EM.scroll.__shown == true
                   and EM.filterBtns.all.__shown ~= false)
              end
            end
          end
        end
        U:SwitchSub("Professions")
        ck("★ 切回专业 → 探索页隐藏", U.explorePage ~= nil and U.explorePage.__shown == false)
        U:SwitchSub("Dungeons")
      end
    end
"""
if DYN_ANCHOR not in text:
    sys.exit('未找到⑧步动态插入锚点（上游 harness 可能已改动）')
text = text.replace(DYN_ANCHOR, DYN_ANCHOR + DYN_EXTRA, 1)
print('  %-28s → %d 处' % ('⑧动态断言块', 1))

# 旧断言名里的「副本」随胶囊改名 → 「5人本」（只改文案，判定逻辑不变）
_LBL_OLD = '    ck("标签行里有「副本」入口", found)\n'
_LBL_NEW = '    ck("标签行里有「5人本」入口（key = Dungeons；文案随用户要求已改名）", found)\n'
if _LBL_OLD not in text:
    sys.exit('未找到⑧步标签断言名锚点（上游 harness 可能已改动）')
text = text.replace(_LBL_OLD, _LBL_NEW, 1)
print('  %-28s → %d 处' % ('⑧标签断言改名', 1))

# ── ⑥ 修两条「恒真白测」断言（上游既有缺陷，逐条变异实测未抓住）────────────────
# 上游 harness 有两条断言过宽，导致对应变异注入后仍全绿 —— 断言等于白测：
#   ① 「任务滚动容器绑了滚轮 + 行转发」查的是大切片里的 `r:EnableMouseWheel(true)`，
#      而全文件该串共 4 处（掉落行 / 任务行 / 右列节点 ×2），删掉任务行那一处照样满足。
#   ② 「起始行 NPC 以 ID 为参考键」查全文件的 `if q[16] then`，而左列行构建处也有一处，
#      把详情里的分支改成 `if false then` 后断言仍满足。
# 修法：把这两条收窄到各自函数体切片。修好后对应变异才能被抓住。

WHEEL_OLD = """    ck('★ 任务滚动容器绑了滚轮 + 行转发（压在任务行上也能滚）',
       'qscroll:EnableMouseWheel(true)' in src
       and 'qscroll:SetScript("OnMouseWheel"' in src
       and 'r:EnableMouseWheel(true)' in qcode
       and 'DG.WheelScroll(U.dungeonQuestScroll, U.dungeonQuestChild, delta)' in qcode)
"""
WHEEL_NEW = """    # ★ 收窄到「任务行构建」函数体：`r:EnableMouseWheel(true)` 全文件有 4 处
    #   （掉落行 / 任务行 / 右列节点 ×2）—— 只在大切片里查「存在」的话，
    #   删掉任务行那一处也照样满足，对应变异就成了恒真白测（上游实测未抓住）。
    seg_qrow = src[src.index('function U:RenderDungeonQuests'):src.index('function U:RefreshQuestRows')]
    qrowcode = '\\n'.join(l.split('--')[0] for l in seg_qrow.split('\\n'))
    ck('★ 任务滚动容器绑了滚轮 + 行转发（压在任务行上也能滚）',
       'qscroll:EnableMouseWheel(true)' in src
       and 'qscroll:SetScript("OnMouseWheel"' in src
       and 'r:EnableMouseWheel(true)' in qrowcode
       and 'DG.WheelScroll(U.dungeonQuestScroll, U.dungeonQuestChild, delta)' in qrowcode)
"""
if WHEEL_OLD not in text:
    sys.exit('未找到任务行滚轮断言，上游可能已改动')
text = text.replace(WHEEL_OLD, WHEEL_NEW, 1)

NPCID_OLD = """    ck('★ 起始行 NPC 以 ID 为参考键：q[16] 有值时显示 金名 + #NPCID 灰尾缀（2026-09-22，金名=可点开图标记）',
       'if q[16] then' in src
       and 'local nm = (q[17] and q[17] ~= "" and q[17]) or q[5] or ""' in src
       and 'where = "|cffffd100" .. nm .. "|r" .. format(" |cff9a9a9a#%d|r", q[16])' in src)
"""
NPCID_NEW = """    # ★ 同上：`if q[16] then` 在详情函数体里就有两处（4 空格缩进=拼 where；
    #   8 空格缩进=选可点行容器）。只查「存在」的话，把前一处改成 `if false then`
    #   照样满足（后一处还在）→ 恒真白测（上游实测未抓住）。
    #   故按行首缩进精确锚定前一处。
    seg_qdet = src[src.index('function U:RenderQuestDetail'):src.index('function U:SetDungeonTab')]
    qdetcode = '\\n'.join(l.split('--')[0] for l in seg_qdet.split('\\n'))
    ck('★ 起始行 NPC 以 ID 为参考键：q[16] 有值时显示 金名 + #NPCID 灰尾缀（2026-09-22，金名=可点开图标记）',
       re.search(r'^    if q\\[16\\] then$', qdetcode, re.M) is not None
       and 'local nm = (q[17] and q[17] ~= "" and q[17]) or q[5] or ""' in qdetcode
       and 'where = "|cffffd100" .. nm .. "|r" .. format(" |cff9a9a9a#%d|r", q[16])' in qdetcode)
"""
if NPCID_OLD not in text:
    sys.exit('未找到起始行 NPCID 断言，上游可能已改动')
text = text.replace(NPCID_OLD, NPCID_NEW, 1)

# ── ① 路径 ─────────────────────────────────────────────────────────────────
PATH_REPL = [
    (r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\TalentsForever',
     r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'),
    ("'TalentsForever.toc'", "'DungeonsForever.toc'"),
    ("os.path.join(ADDON, 'Core', 'UI.lua')", "os.path.join(ADDON, 'Core', 'DungeonUI.lua')"),
    ("'Core/UI.lua'", "'Core/DungeonUI.lua'"),
    # 隔离树：允许探针把 harness 指到「变异注入用的副本树」（_prof_*_probe.py）。
    # 不设 DF_ADDON_ROOT 时行为与原来完全一致（默认仍是 beta）。
    ("ADDON = r'D:\\Game\\World of Warcraft\\_classic_beta_\\Interface\\AddOns\\DungeonsForever'",
     "(os.environ.get('DF_ADDON_ROOT')\n"
     "         or r'D:\\Game\\World of Warcraft\\_classic_beta_\\Interface\\AddOns\\DungeonsForever')"),
    ('chunk("TalentsForever", TF_NS)', 'chunk("DungeonsForever", TF_NS)'),
    ("section('副本页回归检查（TF_BUILD=%d）' % CLIENT_BUILD)",
     "section('无限副本手册 · 副本页回归检查（TF_BUILD=%d，加载自 beta 副本）' % CLIENT_BUILD)"),
    # 上游 docstring 里点名了 TalentsForever 专有文件名，改成本插件的对应物
    ('现有 tf_chain_check / tf_load_check 都**不覆盖**副本页',
     '上游 TalentsForever 的 tf_chain_check / tf_load_check 都**不覆盖**副本页'),
]
for old, new in PATH_REPL:
    n = text.count(old)
    if not n:
        sys.exit('替换未命中：%s' % old)
    text = text.replace(old, new)
    print('  %-28s →  %d 处' % (old[:28], n))

# ── ⑨ 上游数据同步「下限守护」（2026-09-23：NPCLoc 176→237 / QuestPreNpcID 9→218）──
# 上游 Data_NPCLoc.lua 由 _temp/gen_nploc.py 产出，本插件靠 _temp/sync_data.py 逐字节同步。
# 踩过的坑：上游重跑生成器后本插件数据静默变旧（旧数据只有 NPCLoc 176 / QuestPreNpcID 9）。
SYNC_ANCHOR = '    local U = TF_NS.DungeonUI\n'
SYNC_EXTRA = r"""
    -- ---------- 上游数据同步下限守护（2026-09-23）----------
    -- 上游 Core/Data/Data_NPCLoc.lua 由 _temp/gen_nploc.py 产出；本插件靠 _temp/sync_data.py
    -- 逐字节同步。踩过的坑：上游一重跑，本插件数据静默变旧（曾残留 176 / 9）。
    -- 这里钉「不得回退」的下限 + 「表外链兜底真被数据支撑」，防止将来又同步到旧数据。
    do
      local _npc, _pre = TF_NS.NPCLoc, TF_NS.QuestPreNpcID
      local _nNpc, _nPre = 0, 0
      for _ in pairs(_npc or {}) do _nNpc = _nNpc + 1 end
      for _ in pairs(_pre or {}) do _nPre = _nPre + 1 end
      ck("★★ NPCLoc 条目数不得回退（2026-09-23 实测 237）", _nNpc >= 230, _nNpc)
      ck("★★ QuestPreNpcID 条目数不得回退（2026-09-23 实测 218）", _nPre >= 210, _nPre)
      -- 表外链兜底：统计「q[9] 数字段、行内拿不到 NPCID、只能靠 QuestPreNpcID、
      -- 且该 NPC 在 NPCLoc 里有坐标」的用例数 —— 少了就说明同步回了旧数据。
      local _hit = 0
      for _, _dg in ipairs(TF_NS.DungeonData.dungeons) do
        for _, _qq in ipairs(TF_NS.DungeonModule.QuestList(_dg)) do
          if _qq[9] then
            for _, _seg in ipairs(_qq[9]) do
              if type(_seg) == "number" then
                local _pr = TF_NS.DungeonModule.QuestRowByID(_seg)
                if _pr == nil or _pr[16] == nil then
                  local _nid = _pre and _pre[_seg]
                  if _nid and _npc and _npc[_nid] then _hit = _hit + 1 end
                end
              end
            end
          end
        end
      end
      ck("★★ 表外链靠 QuestPreNpcID 兜底且能落旗的用例 >= 80", _hit >= 80, _hit)
    end

    -- ---------- 暴风城坐标口径守护（2026-09-24）----------
    -- 无限服客户端的暴风城地图按**新生代边界**重画过，而站点记的是经典边界口径 →
    -- 该图整张百分比坐标系统性偏移（实测 5413 旧 57.4,16.0 实机在 64.6,37.2）。
    -- 校正表在 _temp/sync_data.py 的 NPCLOC_COORD_FIX，此处把结果**独立抄一遍**钉死：
    -- 少了这道，上游重跑生成器 / 同步脚本漏施加校正都不会红 —— 数据静默回到旧口径，
    -- 只有实机点图才看得出来（离线断言拿表比自己比永远相等）。
    -- ★ 本块的值不是从 sync_data.py 生成的，改校正表必须同时改这里，否则等于没守。
    do
      local _sw = {
        [332] = { 78.3, 70.7 }, [656] = { 70.3, 40.8 }, [928] = { 48.4, 50.2 },
        [1284] = { 50.3, 45.5 }, [1416] = { 59.7, 33.8 }, [1646] = { 57.7, 47.9 },
        [1719] = { 51.5, 69.4 }, [1721] = { 73.3, 55.5 }, [1748] = { 79.6, 38.3 },
        [2198] = { 56.4, 74.1 }, [2285] = { 76.9, 47.8 }, [4984] = { 36.2, 67.6 },
        [5384] = { 69.5, 40.4 }, [5413] = { 64.6, 37.2 }, [6171] = { 50.5, 47.5 },
        [6579] = { 62.6, 34.1 }, [7917] = { 51.0, 48.4 }, [12336] = { 52.6, 43.2 },
        [14450] = { 56.3, 54.0 }, [11026] = { 62.0, 30.4 }, [1325] = { 78.2, 58.4 },
      }
      local _npc = TF_NS.NPCLoc or {}
      local _n, _bad = 0, 0
      for _nid, _xy in pairs(_sw) do
        local _l = _npc[_nid]
        _n = _n + 1
        if not (_l and _l[1] == 1453
                and math.abs(_l[2] - _xy[1]) < 0.05 and math.abs(_l[3] - _xy[2]) < 0.05) then
          _bad = _bad + 1
        end
      end
      ck("★★ 暴风城 21 条坐标已是新生代边界口径", _n == 21 and _bad == 0,
         "校正表 " .. _n .. " 条 / 不匹配 " .. _bad)
      -- 反向：全表里地图名为「暴风城」的条目数必须与校正表一致 —— 上游给该图新增 NPC 时
      -- 必须同时补进 NPCLOC_COORD_FIX，否则新条目会带着旧边界口径静默混进产物。
      local _swAll = 0
      for _, _l in pairs(_npc) do
        if _l[4] == "暴风城" then _swAll = _swAll + 1 end
      end
      ck("★★ 暴风城条目数与校正表一致（新增须同时补校正表）", _swAll == 21, _swAll)
    end
"""
if SYNC_ANCHOR not in text:
    sys.exit('未找到⑨步数据守护插入锚点（上游 harness 可能已改动）')
text = text.replace(SYNC_ANCHOR, SYNC_ANCHOR + SYNC_EXTRA, 1)
print('  %-30s → %d 处' % ('⑨数据同步守护块', 1))

# ── ⑩ 物品卡 Shift+点击 → 聊天框（2026-09-23 用户要求）────────────────────────
# 用户原话：「物品需要支持 Shift 点击，然后能发送到聊天输入框」。
# 静态那半边（NS_EXTRA 里）钉控件类型 + 判定 + 兜底 + 两路投递；
# 动态这半边真按一次，看链接到底走到哪 —— 两半互为证伪，缺一不可
# （静态能过而动态不动的典型：OnClick 挂了但 __it 没绑、或桩里 ChatEdit_* 根本不存在）。
# ⚠️ 插在 LUA_SCRIPT 尾部：此处掉落卡池与任务奖励 chip 池都已渲染过，
#    两类物品控件同时可取，不用再造一遍渲染流程（避免扰动前面的状态断言）。
CLICK_ANCHOR = (
    '    -- 页面重建（UI:Build 复位路径）：池与子帧必须整体丢弃，不能跨页复用\n'
    '    ck("页面复位时池引用已清空准备重建",\n'
    '       U.dungeonDetailChild == dc0 and U.dungeonListChild == child0)\n'
)
CLICK_EXTRA = r"""
    -- ---------- 物品卡 Shift+点击 → 把链接送进聊天输入框（2026-09-23 用户要求）----
    -- 用户原话：「物品需要支持 Shift 点击，然后能发送到聊天输入框」。
    -- 五种情形都要覆盖：非 Shift 不碰 / 没开框自己开 / 已开框插光标处 /
    -- 客户端未缓存这件时自造 item:<id> 兜底 / 右键不触发。
    -- 桩里本来没有聊天框 API（也没有把 Shift 置真的办法）→ 现装现拆，跑完复位。
    do
      local _ins, _open, _act, _shift = nil, nil, nil, false
      ChatEdit_GetActiveWindow = function() return _act end
      ChatEdit_InsertLink = function(link) _ins = link end
      ChatFrame_OpenChat = function(text) _open = text end
      IsShiftKeyDown = function() return _shift end   -- 桩里原本恒 false，这里改成开关

      local _card
      for _, _r in ipairs(U.dungeonDetailPool and U.dungeonDetailPool.item or {}) do
        if not _card and _r.__it then _card = _r end
      end
      ck("掉落卡池里仍有绑 __it 的卡（Shift 点击的取值来源）", _card ~= nil)
      ck("掉落卡挂了 OnClick（Frame 不支持 OnClick，故必须是 Button）",
         _card ~= nil and _card.__scripts ~= nil and _card.__scripts.OnClick ~= nil)
      if _card and _card.__scripts and _card.__scripts.OnClick then
        local _id = _card.__it[1]
        local _link = "|cffa335ee|Hitem:" .. tostring(_id) .. ":0:0:0:0:0:0:0|h[测试装备]|h|r"

        -- ① 不按 Shift：点卡片不该碰聊天框（否则平时随手一点就污染输入框）
        GetItemInfo, C_Item = function() return "测试装备", _link, 4 end, nil
        _ins, _open, _act, _shift = nil, nil, nil, false
        _card.__scripts.OnClick(_card, "LeftButton")
        ck("★ 不按 Shift 点物品卡不碰聊天框", _ins == nil and _open == nil,
           tostring(_ins) .. " / " .. tostring(_open))

        -- ② Shift+左键、聊天框没开 → 自己开框并把链接塞进去（等价游戏内 Shift+点击物品）
        _ins, _open, _act, _shift = nil, nil, nil, true
        _card.__scripts.OnClick(_card, "LeftButton")
        ck("★★ Shift+左键点物品卡 → 链接进聊天框（没开框时自己开）",
           _open == _link, tostring(_open))
        ck("★ 投递的是客户端给的 hyperlink（不是自造 item string）",
           _open ~= nil and tostring(_open):find("|Hitem:", 1, true) ~= nil)

        -- ③ Shift+左键、聊天框已开 → 插到光标处（不覆盖已输入的草稿）
        _ins, _open, _act, _shift = nil, nil, { tag = "eb" }, true
        _card.__scripts.OnClick(_card, "LeftButton")
        ck("★★ 聊天框已开时 Shift+点击 → 插进当前输入框（ChatEdit_InsertLink）",
           _ins == _link and _open == nil, tostring(_ins) .. " / " .. tostring(_open))

        -- ④ 客户端还没缓存这件（懒加载未到货，GetItemInfo 回 nil）→ 自造 item:<id> 兜底。
        --    ★ 这条不能省：拿「GetItemInfo 回 nil」当门槛是踩过的坑（未预热 ≠ 不认识）。
        GetItemInfo = nil
        C_Item = { GetItemInfo = function() return nil end }
        _ins, _open, _act, _shift = nil, nil, nil, true
        _card.__scripts.OnClick(_card, "LeftButton")
        ck("★★ 客户端未缓存时 Shift+点击仍发得出链接（item:<id> 兜底，不静默失败）",
           _open ~= nil and tostring(_open):find("item:" .. tostring(_id), 1, true) ~= nil,
           tostring(_open))

        -- ⑤ Shift+右键不投递（只认左键）
        GetItemInfo = function() return "测试装备", _link, 4 end
        C_Item = nil
        _ins, _open, _act, _shift = nil, nil, nil, true
        _card.__scripts.OnClick(_card, "RightButton")
        ck("★ Shift+右键不投递链接（只认左键）", _ins == nil and _open == nil)

        -- ⑥ 奖励芯片是同款入口（任务详情右列的奖励物品行）
        local _chip
        for _, _c in ipairs(U.dungeonQDetPool and U.dungeonQDetPool.chip or {}) do
          if not _chip and _c.__it then _chip = _c end
        end
        ck("任务奖励芯片存在且绑了 __it", _chip ~= nil)
        ck("奖励芯片挂了 OnClick（同款入口）",
           _chip ~= nil and _chip.__scripts ~= nil and _chip.__scripts.OnClick ~= nil)
        if _chip and _chip.__scripts and _chip.__scripts.OnClick then
          _ins, _open, _act, _shift = nil, nil, nil, true
          _chip.__scripts.OnClick(_chip, "LeftButton")
          ck("★★ 奖励芯片同样支持 Shift+点击发链接（与掉落卡同一入口）",
             _open ~= nil, tostring(_open))
        end
      end

      -- 收尾：聊天框 API 复位成「本端没有」的形态（桩纪律：无此方法写 = false，
      -- 写 nil 会被 __index 泛型复活成 truthy），Shift 关回去
      ChatEdit_GetActiveWindow, ChatEdit_InsertLink, ChatFrame_OpenChat = false, false, false
      IsShiftKeyDown = function() return false end
      GetItemInfo, C_Item = nil, nil
    end
"""
if CLICK_ANCHOR not in text:
    sys.exit('未找到⑩步动态插入锚点（harness 尾部可能已改动）')
text = text.replace(CLICK_ANCHOR, CLICK_EXTRA + CLICK_ANCHOR, 1)
print('  %-30s → %d 处' % ('⑩物品卡 Shift 点击块', 1))


# ── ⑬ 专业页（仅无限服，2026-09-23）─────────────────────────────────────────
# 静态那半边（NS_EXTRA 里）钉结构：加载顺序 / 只对无限服 / 无裸全局 / 帧数纪律 /
# 钓鱼先分流 / 描边显式建。动态这半边证明它**真的画得出来**，而且三件事：
#   ① 分端：无限服三颗胶囊 + 有页帧，泰坦两颗 + 切「专业」落回 5人本；
#   ② 三页互斥且切页零新建帧；
#   ③ 全部专业 × 全部子页签两遍跑通，第二遍**零新建帧**（池化复用，不是每切一次建一套）。
# ③ 是最要紧的：字段位置（那套紧凑元组）对不上时取到的是 nil，只会画空、不报错 ——
# 只有把每一页都真渲染一遍才能把它变成红灯。
PROF_ANCHOR = CLICK_ANCHOR
PROF_EXTRA = r"""
    -- ---------- 专业页（仅无限服，2026-09-23）----------
    -- 用户口径：整页只对无限服（1.60.x）开放 —— 营地系统 / Legacy 特权 / 1→300 路线
    -- 都是无限服自己的规则，泰坦 3.80.2 端没有对应物品与专业。
    do
      if not IS_FOREVER then
        -- 泰坦端：模块整体 return，第二颗之外没有第三颗胶囊
        ck("★★ 泰坦端没有专业模块（Core/ProfessionUI.lua 整体 return）",
           TF_NS.ProfModule == nil)
        ck("★ 泰坦端不建专业页帧（U.profPage 为 nil）", U.profPage == nil)
        local _f0 = FRAMES
        local _okT = pcall(U.SwitchSub, U, "Professions")
        ck("★ 泰坦端切「专业」不报错", _okT == true)
        ck("★★ 泰坦端切「专业」落回 5人本（该颗胶囊本就不存在，不许切出一张空白页）",
           U.curSub == "Dungeons" and U.dungeonPage.__shown == true, tostring(U.curSub))
        ck("★ 泰坦端切「专业」零新建帧", FRAMES == _f0, FRAMES - _f0)
      else
        local PD = TF_NS.ProfModule
        ck("★ 无限服专业模块已加载（ns.ProfModule）", PD ~= nil)
        ck("★ 无限服专业页帧已建（U.profPage）", U.profPage ~= nil)
        if PD == nil then
          ck("★★ 专业页模块缺失 —— 后续断言无法进行", false)
        else
          ck("★ 页面骨架由 ProfModule.Build 建好（PD.built）", PD.built == true)
          ck("★ 行池 / 滚动容器就位（详情条 2026-09-23 晚已退役）",
             PD.child ~= nil and PD.scroll ~= nil and PD.detail == nil)

          -- 切到专业页：三页互斥 + 存档。
          -- ★ 首次切过去会**按需长行池**（与副本页同一套：池子按需生长，骨架才在 Build 里建全），
          --   所以「零新建帧」这条要量在**第二次**切过去上：那时池已长齐，不该再建任何帧。
          local _f0 = FRAMES
          U:SwitchSub("Professions")
          ck("★★ 切专业 → 专业页显示", U.profPage.__shown == true)
          ck("★★ 切专业 → 副本页与团本页都隐藏（三页互斥）",
             U.dungeonPage.__shown == false and U.raidPage.__shown == false)
          ck("★ 切专业 → curSub = Professions", U.curSub == "Professions", tostring(U.curSub))
          ck("★ 切专业 → 存档 subTab = Professions（开窗沿用上次那一颗）",
             DungeonsForeverDB ~= nil and DungeonsForeverDB.dungeon ~= nil
             and DungeonsForeverDB.dungeon.subTab == "Professions")
          ck("★ 首次进专业页只长行池、不重复建骨架（新建帧 < 64）", FRAMES - _f0 < 64, FRAMES - _f0)
          U:SwitchSub("Dungeons")
          local _f0b = FRAMES
          U:SwitchSub("Professions")
          ck("★★ 再切回专业页零新建帧（骨架与池都已就位）", FRAMES == _f0b, FRAMES - _f0b)

          -- 开窗刷新路径：专业态下刷的是 PD.Refresh，不许把副本页刷出来
          local _okU = pcall(U.UpdateActiveSub, U)
          ck("★ 专业态下 UpdateActiveSub 不报错", _okU == true)
          ck("★ 专业态下 UpdateActiveSub 不会把副本页刷出来", U.dungeonPage.__shown == false)

          -- ---------- 全专业 × 全子页签渲染 ----------
          -- 第一遍让行池 / 芯片池长到需要的大小；第二遍必须零新建帧。
          -- 两遍各自报出「是哪个专业哪一页」炸的，便于定位字段位置错位。
          local PDM = TF_NS.DungeonModule
          local slugs = { "__index" }
          for _, s in ipairs(TF_NS.ProfData.order or {}) do slugs[#slugs + 1] = s end
          local allTabs = {}
          for _, d in ipairs(PDM.PROF_SUBTABS or {}) do allTabs[#allTabs + 1] = d.key end
          ck("★ 专业页子页签 = 7 个固定槽位（总览/营地/配方/采集/升级/Legacy/说明）",
             #allTabs == 7, #allTabs)

          local function sweep()
            local done, bad, why = 0, nil, nil
            for _, slug in ipairs(slugs) do
              local has = {}
              for _, k in ipairs(PD.TabsFor(slug) or {}) do has[k] = true end
              for _, k in ipairs(allTabs) do
                if has[k] then
                  local ok1, e1 = pcall(function() PD.Show(slug); PD.SetTab(k) end)
                  if not ok1 then
                    return done, tostring(slug) .. " / " .. tostring(k),
                           tostring(e1):gsub("[\r\n]+", " "):sub(1, 160)
                  end
                  done = done + 1
                end
              end
            end
            return done, bad, why
          end

          local n1, bad1, why1 = sweep()
          ck("★★ 全部专业 × 全部子页签都渲染得出来（紧凑元组位置对不上会在这里炸）",
             bad1 == nil, bad1 and (bad1 .. " → " .. tostring(why1)))
          ck("★ 渲染覆盖面够（专业×子页签 组合 >= 40）", n1 >= 40, n1)

          local _f1 = FRAMES
          local n2, bad2, why2 = sweep()
          ck("★ 第二遍全量渲染同样不报错（渲染可重入）",
             bad2 == nil, bad2 and (bad2 .. " → " .. tostring(why2)))
          ck("★★ 第二遍全量重渲染零新建帧（池化复用，不是每切一次建一套）",
             FRAMES == _f1, FRAMES - _f1)
          ck("★ 两遍覆盖的组合数一致（第二遍没有偷偷少渲染）", n2 == n1, n1 .. " / " .. n2)

          -- ---------- 数据下限（防「又同步回旧数据 / 生成器漏发射」）----------
          local D, RC, LV, GA = TF_NS.ProfData, TF_NS.ProfRecipes,
                                TF_NS.ProfLeveling, TF_NS.ProfGathering
          ck("★★ 13 个专业都在（order 表）", #(D.order or {}) == 13, #(D.order or {}))
          do
            local _all = true
            for _, s in ipairs(D.order or {}) do
              if D.pro[s] == nil then _all = false end
            end
            ck("★ order 里每一条都有对应的 pro 元信息", _all)
          end
          -- ★ 这一条钉的是一个真实缺口：ranks 在解析 / 翻译 / 取用清单三处都在，
          --   唯独生成器忘了发射 → 数据里恒无此键、UI 静默读 nil（整块不显示、不报错）。
          ck("★★ 钓鱼技能等级表 ranks 已产出且 >= 4 条（曾漏发射，静默读 nil）",
             D.pro.fishing ~= nil and D.pro.fishing.ranks ~= nil
             and #D.pro.fishing.ranks >= 4,
             D.pro.fishing and D.pro.fishing.ranks and #D.pro.fishing.ranks)
          ck("★★ 钓鱼区域表 >= 50 处（GA.fishing）",
             GA ~= nil and #(GA.fishing or {}) >= 50, GA and #(GA.fishing or {}))
          ck("★ 采矿 / 采药 / 剥皮节点表都在",
             GA ~= nil and #(GA.mining or {}) >= 8 and #(GA.herbalism or {}) >= 20
             and #(GA.skinning or {}) >= 5)
          do
            local _rc, _lv = 0, 0
            for _ in pairs(RC or {}) do _rc = _rc + 1 end
            for _ in pairs(LV or {}) do _lv = _lv + 1 end
            ck("★ 配方 / 附魔覆盖 8 个专业", _rc >= 8, _rc)
            ck("★ 升级路线与营地坐标覆盖 8 个专业", _lv >= 8, _lv)
          end

          -- ---------- 踩过的坑：钓鱼页（形状不同的数据不能混进通用循环）----------
          local _f2 = FRAMES
          local okFish = pcall(function() PD.Show("fishing"); PD.SetTab("gather") end)
          ck("★★ 钓鱼 · 采集页渲染不报错（GA.fishing 是 {区域,技能,原始值}，"
             .. "曾对数字调 ipairs → 实机必崩）", okFish == true)
          ck("★ 钓鱼页零新建帧", FRAMES == _f2, FRAMES - _f2)
          ck("★ 钓鱼页真的画出了行（不是空页）",
             #(PD.specs or {}) > 0 and #(PD.rows or {}) > 0,
             #(PD.specs or {}) .. " spec / " .. #(PD.rows or {}) .. " row")

          -- ---------- 采集页去英文 + 钓鱼页折两栏（2026-09-24）----------
          -- ★★ 桩保真度 = 断言有效性：C_Map / GetItemInfo 必须**显式给上**。
          --   泛型桩会把 C_Map.GetAreaInfo 复活成一个回 nil 的函数 → DG.ZoneName 恒落
          --   「区域 #ID」占位，于是「区域名客户端化」这条实际零覆盖（hooksecurefunc
          --   空实现那次的翻版：离线全绿、实机才发现没接上）。
          C_Map = { GetAreaInfo = function(id) return "测区" .. tostring(id) end }
          GetItemInfo = function(id)
            return "测物" .. tostring(id), "|Hitem:" .. tostring(id) .. "|h[x]|h", 3
          end
          local _f3 = FRAMES
          PD.Show("fishing")
          PD.SetTab("gather")
          ck("★★ 钓鱼采集页举手折两栏（PD.gridSplit = true）", PD.gridSplit == true)
          ck("★★ 网格页的竖向分栏线真的显示出来了（PD.divider 不隐藏）",
             PD.divider ~= nil and PD.divider.__shown == true)
          ck("★★ 分栏线落在「第 1 栏宽 + 栏间距中点」（与行位同源，不是拍脑袋的常数）",
             PD.divider ~= nil and PD.divider.__pts ~= nil
             and PD.divider.__pts[4] == PD.RIGHT_X + PD.LIST_PAD + PD.GRID_LW + PD.COL_GAP / 2,
             PD.divider and PD.divider.__pts and PD.divider.__pts[4])
          ck("★ 网格页零新建帧", FRAMES == _f3, FRAMES - _f3)
          do
            -- ⚠️ 判据顺序必须是 **先看宽度、再看 x**：
            --   ①网格两栏是**等宽**的（GRID_RW = 总宽 - GRID_LW，取整后往往与 GRID_LW 相等）
            --     —— 按「宽度 == GRID_LW / == GRID_RW」分栏会把两栏都算进第 1 栏，写出
            --     「第二栏一行都没有」的假红；
            --   ②通栏的标题 / 说明也落在 x = LIST_PAD 上 —— 先判 x 会把它们算成第 1 栏的行，
            --     于是又写出「栏宽不等」的假红。
            local _x2 = PD.LIST_PAD + PD.GRID_LW + PD.COL_GAP
            local _c1, _c2, _span, _stray = 0, 0, 0, 0
            local _full = PD.RIGHT_W - 2 * PD.LIST_PAD
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__w and r.__w > 0 then
                local px = r.__pts and r.__pts[4]
                if r.__w == _full then
                  _span = _span + 1
                elseif r.__w == PD.GRID_LW or r.__w == PD.GRID_RW then
                  if px == PD.LIST_PAD then _c1 = _c1 + 1
                  elseif px == _x2 then _c2 = _c2 + 1
                  else _stray = _stray + 1 end
                else
                  _stray = _stray + 1
                end
              end
            end
            -- ★ 两栏都真有行：只断「举手了」不够 —— 全塞一栏照样能举手。
            ck("★★ 钓鱼页的行真的分到两栏（左栏 x = LIST_PAD、右栏 x = LIST_PAD + GRID_LW + COL_GAP）",
               _c1 > 0 and _c2 > 0, tostring(_c1) .. " / " .. tostring(_c2))
            ck("★★ 两栏等宽（同一列表折栏：栏宽差 <= 1px，不是升级页的 0.80 配比）",
               PD.GRID_LW > 0 and PD.GRID_RW >= PD.GRID_LW
               and PD.GRID_RW - PD.GRID_LW <= 1,
               tostring(PD.GRID_LW) .. " / " .. tostring(PD.GRID_RW))
            ck("★★ 网格页的行只落在两栏之一（没有第三种落点）", _stray == 0, _stray)
            ck("★★ 网格页的标题 / 说明通栏（先把两个游标拉平再占整幅，不吃半栏）",
               _span > 0, _span)
          end
          -- 区域名走客户端：界面上不许再出现「区域 #ID」占位（桩给的「测区N」才是对的）
          do
            local _ph, _cli = 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              local s = tostring(sp.text or "") .. " " .. tostring(sp.right2 or "")
              if s:find("区域 #", 1, true) then _ph = _ph + 1 end
              if s:find("测区", 1, true) then _cli = _cli + 1 end
            end
            ck("★★ 钓鱼页区域名走客户端 C_Map.GetAreaInfo（不是「区域 #ID」占位）",
               _cli > 0 and _ph == 0, tostring(_cli) .. " / 占位 " .. tostring(_ph))
          end
          -- 采矿页：节点标题 = 首个产出物的客户端中文名；且**不**折栏（其余采集页仍单列）
          PD.Show("mining")
          PD.SetTab("gather")
          ck("★ 采矿页不走网格（折栏只给钓鱼，其它采集页仍单列）", PD.gridSplit == false)
          ck("★ 采矿页不挂分栏线", PD.divider ~= nil and PD.divider.__shown == false)
          do
            local _ph, _named, _en = 0, 0, 0
            local _full = PD.RIGHT_W - 2 * PD.LIST_PAD
            local _wide, _narrow = 0, 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__w and r.__w > 0 then
                if r.__w == _full then _wide = _wide + 1 else _narrow = _narrow + 1 end
              end
            end
            for _, sp in ipairs(PD.specs or {}) do
              if sp.kind == "row" then
                local s = tostring(sp.text or "")
                if s:find("物品 #", 1, true) then _ph = _ph + 1
                else _named = _named + 1 end
                -- 界面上不该有英文（站点给的 Copper Vein / Peacebloom 不许露头）
                if s:find("%a%a%a") then _en = _en + 1 end
              end
            end
            ck("★★ 采集节点标题 = 客户端给的产出物名（不再停在「物品 #ID」占位）",
               _named > 0 and _ph == 0, tostring(_named) .. " / 占位 " .. tostring(_ph))
            ck("★★ 采集页界面上没有任何英文节点名（站点给的英文名不进界面）", _en == 0, _en)
            ck("★★ 单列采集页所有行满幅（不跟着网格被压成半栏）",
               _wide > 0 and _narrow == 0, tostring(_wide) .. " 宽 / " .. tostring(_narrow) .. " 窄")
          end
          -- 收尾：把客户端取数口撤掉（桩纪律：无此方法写 = false）→ 验降级路径
          C_Map, GetItemInfo = false, nil
          local _f4 = FRAMES
          local _okNoMap = pcall(function() PD.Show("fishing"); PD.SetTab("gather") end)
          ck("★★ 客户端没有 C_Map 时钓鱼页仍渲染不报错（老端 / API 未就绪也不许崩）",
             _okNoMap == true)
          ck("★ 撤掉 C_Map 后零新建帧（降级走同一条渲染路径，不重建骨架）",
             FRAMES == _f4, FRAMES - _f4)
          do
            local _ph, _cli = 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              local s = tostring(sp.text or "") .. " " .. tostring(sp.right2 or "")
              if s:find("区域 #", 1, true) then _ph = _ph + 1 end
              if s:find("测区", 1, true) then _cli = _cli + 1 end
            end
            ck("★★ 拿不到客户端区域名 → 落中文占位「区域 #ID」（不是英文、也不是空白）",
               _ph > 0 and _cli == 0,
               tostring(_ph) .. " 占位 / " .. tostring(_cli) .. " 客户端名")
          end
          C_Map = false

          -- ---------- 配方页：详情条退役 + 行内材料小图标（2026-09-23 晚）----------
          PD.Show("alchemy")
          PD.SetTab("recipe")
          ck("★★ 配方页不再建详情条（PD.detail 恒空）", PD.detail == nil)
          local _row
          for _, sp in ipairs(PD.specs or {}) do
            if sp.kind == "row" and sp._mats and #sp._mats > 0 then
              _row = sp; break
            end
          end
          ck("★ 配方页有带材料的行", _row ~= nil)
          if _row then
            ck("★★ 行不再带 act（点击展开详情已撤，行内信息已足够）", _row.act == nil)
            -- ★ 2026-09-24：材料从副行搬到行中间的**材料列**（13pt），副行只剩部位等级
            ck("★★ 配方行带独立材料列（spec.mats，含 |T 装备图标）",
               type(_row.mats) == "string" and _row.mats:find("|T") ~= nil)
            ck("★★ 材料不再挤在副行里（副行只有部位等级，不含「N×材料」）",
               type(_row.sub) == "string" and _row.sub:find("%d×") == nil)
            -- ① 材料列位置：固定左锚在 PD.MAT_X，且不压到右栏（学 / 技能）地盘
            local _mf, _mok, _mover = nil, 0, 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.f and r.f.__text and r.f.__text ~= "" then
                _mf = _mf or r.f
                local px = r.f.__pts and r.f.__pts[4]
                if px == PD.MAT_X then _mok = _mok + 1 else _mover = _mover + 1 end
              end
            end
            ck("★★ 配方页材料列是中间列（左锚 x = PD.MAT_X，不是副行也不是右栏）",
               _mf ~= nil and _mok > 0 and _mover == 0,
               tostring(_mok) .. "/" .. tostring(_mover))
            ck("★★ 材料列可用宽 = 行宽 - 右栏保留宽 - 列起点（不压右栏）",
               PD.MAT_X + PD.MAT_W <= PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE,
               tostring(PD.MAT_X + PD.MAT_W) .. "<=" .. tostring(PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE))
            -- ② 材料列字号比原来的副行大一档（用户：放在下面那一行字体特别小）
            ck("★★ 材料列字号 13pt（原副行 11pt 是用户点名的小）",
               PD.MAT_FS == 13 and PD.MAT_FS > 11, PD.MAT_FS)
            -- ③ 首材料再宽也不劈字：预算为 0 时不许切出半个汉字
            local _t0 = PD.MatCol({ { 1, 1 } }, PD.MAT_FS, 0)
            ck("★ 材料列预算不足时不劈字（截到放得下 + …）", type(_t0) == "string")
          end

          -- ---------- 配方搜索 + 名称列现算（2026-10-09）----------
          do
            ck("★★ 名称列按本页现算（在 [MIN,MAX] 内、材料列 = 行宽-右保留-起点-8）",
               PD.RECIPE_NAME_W ~= nil
               and PD.RECIPE_NAME_W >= PD.RECIPE_NAME_MIN
               and PD.RECIPE_NAME_W <= PD.RECIPE_NAME_MAX
               and PD.MAT_X == PD.RECIPE_NAME_W + PD.RECIPE_NAME_PAD
               and PD.MAT_W == PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - PD.MAT_X - 8)
            ck("★★ 现算的名称列比旧的固定分割窄（省下的全给了材料列）",
               PD.MAT_X < math.floor(PD.MAT_ROW_W * 0.40),
               tostring(PD.MAT_X))
            ck("★★ 搜索框只在配方页显示（当前就在配方页）",
               PD.searchBox ~= nil and PD.searchBox.__shown == true)
            PD.SetTab("overview")
            ck("★ 切离配方页搜索框隐藏", PD.searchBox.__shown == false)
            PD.SetTab("recipe")
            do
              local _DG = TF_NS.ProfHost.DG
              local _oIN = _DG.ItemName
              _DG.ItemName = function(id)
                if (tonumber(id) or 0) % 2 == 0 then return "轻皮甲片", true end
                return "铁扣环", true
              end
              -- ★ 判据必须落到**行内容**上（2026-10-09 第二轮实锤）：只比条数不够 ——
              --   上一轮的性能改写让主路径「条数按命中数截断、行却是分类前 N 条」，
              --   纯条数断言照样全绿（实测 300 -> 31 全绿），搜索框其实形同虚设。
              --   PD.specs 里还混着抬头/间距/截断提示 ⇒ 只认真正的配方行（有 it）。
              local function _isRecipe(s)
                return s ~= nil and s.it ~= nil
                   and (s.kind == "row" or s.kind == nil)
              end
              local function _nRecipes(list)
                local n = 0
                for _, s in ipairs(list or {}) do
                  if _isRecipe(s) then n = n + 1 end
                end
                return n
              end
              local function _hitAndMiss(list, q)
                local n, bad = 0, 0
                for _, s in ipairs(list or {}) do
                  if _isRecipe(s) then
                    local cands = { tostring(_DG.ItemName(s.it[1]) or ""), s.sub or "" }
                    for _, m in ipairs(s._mats or {}) do
                      cands[#cands + 1] = tostring(_DG.ItemName(m[1]) or "")
                    end
                    local hit = false
                    for _, t in ipairs(cands) do
                      if t ~= "" and string.find(string.lower(t), q, 1, true) then
                        hit = true
                        break
                      end
                    end
                    if hit then n = n + 1 else bad = bad + 1 end
                  end
                end
                return n, bad
              end
              local _n0 = _nRecipes(PD.specs)
              PD.searchQ = "轻皮"
              PD.Render()
              local _n1, _bad = _hitAndMiss(PD.specs, "轻皮")
              _DG.ItemName = _oIN
              PD.searchQ = nil
              PD.Render()
              local _n2 = _nRecipes(PD.specs)
              ck("★★ 搜索词过滤列表（命中子集）且清空后全量还原",
                 _n0 > 0 and _n1 > 0 and _n1 < _n0 and _n2 == _n0,
                 tostring(_n0) .. " -> " .. tostring(_n1) .. " -> " .. tostring(_n2))
              ck("★★ 搜索后留下的每一行都真的命中（条数对不算数，行内容也得对）",
                 _n1 > 0 and _bad == 0,
                 tostring(_n1) .. " 行命中 / " .. tostring(_bad) .. " 行未命中")
            end
          end

          -- ---------- 专业页的行同样支持 Shift+点击发链接 ----------
          do
            local _ins, _open, _act, _shift = nil, nil, nil, false
            local _oCAG, _oCIL, _oCFO, _oISK =
              ChatEdit_GetActiveWindow, ChatEdit_InsertLink, ChatFrame_OpenChat, IsShiftKeyDown
            ChatEdit_GetActiveWindow = function() return _act end
            ChatEdit_InsertLink = function(l) _ins = l end
            ChatFrame_OpenChat = function(t) _open = t end
            IsShiftKeyDown = function() return _shift end
            local _ir
            for _, r in ipairs(PD.rows or {}) do
              if r.__it and r.__scripts and r.__scripts.OnClick then _ir = r; break end
            end
            ck("★ 专业页行池里有绑物品的行（Shift 点击的取值来源）", _ir ~= nil)
            if _ir then
              _shift, _open = false, nil
              _ir.__scripts.OnClick(_ir, "LeftButton")
              ck("★ 专业页不按 Shift 点行不碰聊天框", _open == nil)
              _shift, _open = true, nil
              _ir.__scripts.OnClick(_ir, "LeftButton")
              ck("★★ 专业页 Shift+左键点行 → 物品链接进聊天框（与副本页同一入口）",
                 _open ~= nil, tostring(_open))
            end
            ChatEdit_GetActiveWindow, ChatEdit_InsertLink, ChatFrame_OpenChat, IsShiftKeyDown =
              _oCAG, _oCIL, _oCFO, _oISK
          end

          -- ---------- 观感改（2026-09-23）：通栏 / 大卡 / 表格 / 染色 / 传承 / 按钮宽度 ----------
          -- 这些断言都要有对应变异钉住，否则「写了但没人守」（本项目老坑）。
          do
            -- ① 升级页**整页两栏**（2026-09-24 二轮澄清）：左「怎么练」/ 右「要准备的材料」
            -- ★ 斑马纹前置（六轮）：桩不记录 SetBackdropColor（走万能壳，上游 ⑬ 同款结论），
            --   渲染前给行池**临时包一层**把 alpha 记进 __bgA。行池惰性建 → 包**两轮**：
            --   第一轮重画可能补建新行（未包），再包一轮、重画一次，行池齐全 __bgA 才可信。
            do
              local function _wrapBd()
                for _, r in ipairs(PD.rows or {}) do
                  -- ⚠️ 不能用 rawget(r, "SetBackdropColor") == nil 判重：桩的 __index 尾部
                  --   rawset(t, k, f) 把方法**缓存进原始表**，被读过一次的行永远非 nil。
                  --   用自己的标记字段（布尔，非 function，不犯「自定义字段现造 function」的忌）。
                  if not rawget(r, "__bdWrap") then
                    local orig = r.SetBackdropColor
                    rawset(r, "__bdWrap", true)
                    r.SetBackdropColor = function(self, rr, gg, bb, aa)
                      self.__bgA = aa
                      return orig(self, rr, gg, bb, aa)
                    end
                  end
                end
              end
              _wrapBd()
              PD.Show("alchemy")
              PD.SetTab("leveling")
              _wrapBd()
              -- ⚠️ 对同一页签连调 SetTab 是空操作（不重画）→ 必须切走再切回，强制整页重画，
              --   第一轮补建的新行才会带着包裹被落色。
              PD.Show("alchemy")
              PD.SetTab("recipe")
              PD.Show("alchemy")
              PD.SetTab("leveling")
            end
            ck("★★ 升级页举手开两栏（PD.lvSplit = true）", PD.lvSplit == true)
            ck("★★ 升级页的竖向分栏线真的显示出来了（PD.divider 不隐藏）",
               PD.divider ~= nil and PD.divider.__shown == true)
            -- 两栏各有行着落：左栏行 = COL_LW、右栏行 = COL_RW
            local _c1w, _c2w = 0, 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__w and r.__w > 0 then
                if r.__w == PD.COL_LW then _c1w = _c1w + 1
                elseif r.__w == PD.COL_RW then _c2w = _c2w + 1 end
              end
            end
            ck("★★ 两栏各有行着落：左栏行宽 = COL_LW、右栏行宽 = COL_RW",
               _c1w > 0 and _c2w > 0, tostring(_c1w) .. " / " .. tostring(_c2w))
            -- ⚠️ 这一段整体套进 `do ... end`：Lua 5.1 每个函数**最多 200 个活跃局部变量**，
            --   动态块已经贴着上限（实测加 4 个新局部就报 "more than 200 local variables"）。
            --   新加的计数器一律缩进在 do 里，出块即释放，别再加到外层的头上。
            do
            local _st, _badfmt, _nomats, _nocnt, _notleft, _ovl, _nosrc = 0, 0, 0, 0, 0, 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.lvstep then
                _st = _st + 1
                if sp.col ~= 1 then _notleft = _notleft + 1 end
                -- ★ 五轮：区间串三项一起查（不写「技能」二字 / 走半角破折号「–」/ 不留全角「→」）
                local rg = tostring(sp.rng or "")
                if rg:find("技能", 1, true) or rg:find("→", 1, true)
                   or not rg:find("–", 1, true) then
                  _badfmt = _badfmt + 1
                end
                -- ★ 五轮：该段有材料 → 必须至少画出一块（块是行子件，spec.blocks 落行帧 r.blk）
                if sp._mats and #sp._mats > 0 and (not sp.blocks or #sp.blocks == 0) then
                  _nomats = _nomats + 1
                end
                -- ★ 五轮：来源补齐后**每段**都要有（向训练师学习 / 需图纸 · 商人出售），不许空
                if not sp.src or sp.src == "" then _nosrc = _nosrc + 1 end
                -- ★ 五轮：区间列与配方图标列**不许重叠** —— 图标左缘必须容得下本页最宽的区间
                if PD.TextW(sp.rng or "", PD.LV_FS) + 6 > PD.LV_ICON_X then _ovl = _ovl + 1 end
                if not sp.cnt or not tostring(sp.cnt):find("次制作", 1, true) then
                  _nocnt = _nocnt + 1
                end
              end
            end
            ck("★★ 分段行存在（alchemy 应为 17 段）且全部落在左栏", _st == 17 and _notleft == 0,
               tostring(_st) .. " / 不在左栏 " .. tostring(_notleft))
            ck("★★ 分段行区间不写「技能」二字、走半角破折号「–」、不留全角「→」"
               .. "（用户早前点名「区间可以再小一点」）", _badfmt == 0, _badfmt)
            ck("★★ 每段有材料就至少画出一块（材料块，不是「只有右栏汇总才有」）",
               _nomats == 0, _nomats)
            ck("★★ 每段都补上了来源（向训练师学习 / 需图纸 · 商人出售）", _nosrc == 0, _nosrc)
            ck("★★ 区间与配方图标不重叠（图标左缘 >= 区间宽 + 左边距；三位数区间也容得下）",
               _ovl == 0, _ovl)
            ck("★ 每段都有 ~N 次制作", _nocnt == 0, _nocnt)
            end
            -- 渲染后：左栏三样真的画上（配方名 + 次数）
            local _painted, _cntbad = 0, 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.e and r.e.__text and r.e.__text ~= ""
                 and r.c and r.c.__text and tostring(r.c.__text):find("次制作", 1, true) then
                _painted = _painted + 1
                -- 次数右缘贴**本栏**右缘（pts[2] 是锚对象、pts[4] 是 x —— 桩的记录格式）。
                -- ★ 这条是「右栏是独立一栏」的守门人：一旦次数锚回材料列/整幅右侧，就会红。
                local cp = r.c.__pts
                if not (cp and cp[2] == r and cp[4] == -PD.LV_CNT_R) then _cntbad = _cntbad + 1 end
              end
            end
            ck("★★ 渲染后分段行的「配方名 + ~N 次制作」真的画上了（17 段全中）",
               _painted == 17, _painted)
            ck("★★ 左栏「~N 次制作」右缘落在 PD.LV_CNT_R（材料区左边，不许压到材料块上）",
               _cntbad == 0, _cntbad)
            -- ★★ 五轮：**两行表格**、**图标同尺寸**、**材料块右对齐**这三条都是用户逐条点名过的，
            --   动态必须亲眼见到。整段套 `do ... end`（局部变量出块即释放，见上面的 200 局部上限说明）。
            do
            --   ①配方名（r.e）与来源（r.b）同左缘 PD.LV_NAME_X、上下不同 y；
            --   ②配方图标（r.icon）与材料图标（r.blk[1].ic）**同尺寸** = PD.TBL_ICON。
            local _twobad, _iconbad = 0, 0
            for i, sp in ipairs(PD.specs or {}) do
              if sp.lvstep then
                local r = PD.rows and PD.rows[i]
                if r and r.__shown ~= false then
                  if not (r.icon.__w == PD.TBL_ICON and r.icon.__h == PD.TBL_ICON) then
                    _iconbad = _iconbad + 1
                  end
                  local b1 = r.blk and r.blk[1]
                  if b1 and b1.ic.__w ~= PD.TBL_ICON then _iconbad = _iconbad + 1 end
                  local ep, bp = r.e.__pts, r.b.__pts
                  if not (ep and bp and ep[2] == r and bp[2] == r
                          and ep[4] == PD.LV_NAME_X and bp[4] == PD.LV_NAME_X
                          and ep[5] ~= bp[5]) then
                    _twobad = _twobad + 1
                  end
                end
              end
            end
            ck("★★ 配方名与来源真的排成**两行**（同左缘 PD.LV_NAME_X、上下不同 y）",
               _twobad == 0, _twobad)
            ck("★★ 配方图标与材料图标**同尺寸**（都 = PD.TBL_ICON；用户「两边大小不一样」）",
               _iconbad == 0, _iconbad)
            -- ★★ 五轮：材料块真的画上了 —— spec.blocks 逐条落到**对应行帧**的 r.blk。
            --   七轮方案B：块 = 图标 + ×N 角标（**没有物品名**），图标与角标都右对齐到块右缘，
            --   整组**右缘贴本栏右缘**（= COL_LW - TBL_MAT_RPAD）→ 同页各行材料组右缘一条直线。
            --   （行帧与行定义同序：PaintRows 拿 specs[i] 绑 rows[i]，故可按 i 对表。）
            --   ⚠️ 方案B 的块宽不再量物品名（不依赖 DG.ItemName）→ 离线桩下**不再截断**，
            --      matCut 恒 false；「…」分支仍按存在截断的通用形态断（cut 行 = nm 显示的省略块）。
            local _blkneed, _blkbad = 0, 0
            for i, sp in ipairs(PD.specs or {}) do
              if sp.lvstep and sp.blocks and #sp.blocks > 0 then
                _blkneed = _blkneed + 1
                local r = PD.rows and PD.rows[i]
                local ok = false
                if r and r.__shown ~= false and r.blk and #r.blk >= #sp.blocks then
                  ok = true
                  for k = 1, #sp.blocks do
                    local b = r.blk[k]
                    if not (b and b.ic.__shown ~= false and b.ic.__w == PD.TBL_ICON
                            and b.ct.__shown ~= false
                            and b.ct.__text == tostring(sp.blocks[k].cnt)
                            and b.nm.__shown == false) then
                      ok = false; break
                    end
                  end
                  -- 整组右对齐：不截断 = 最后一块的角标右缘；截断 = 「…」那颗字（占组最右端）
                  local ri = #sp.blocks + (sp.matCut and 1 or 0)
                  local lb = r.blk[ri]
                  local rfs = sp.matCut and lb and lb.nm or lb and lb.ct
                  if ok and not (rfs and rfs.__pts and rfs.__pts[2] == r
                                 and rfs.__pts[4] == -PD.TBL_MAT_RPAD) then
                    ok = false
                  end
                end
                if not ok then _blkbad = _blkbad + 1 end
              end
            end
            ck("★★ 材料块真的画上了且整组右对齐（spec.blocks → 行帧 r.blk：图标 + N 角标、"
               .. "无物品名无乘号；组右缘贴 COL_LW - TBL_MAT_RPAD）",
               _blkneed > 0 and _blkbad == 0,
               tostring(_blkneed - _blkbad) .. " / " .. tostring(_blkneed))
            end
            -- ★★ 五轮（用户 2026-09-24）：「右边这一列的宽度可以缩小一点，然后把宽度留给左边」
            --   +「最大可能都留给这个材料」。分段行改两行表格后左栏要装的东西更多 → 系数 0.80，
            --   右栏那两条长标题一起缩短（**标题长度就是右栏宽的下限**）。三条数值钉：
            --     ① 左栏明显宽于右栏（0.66 那版 498/258 / 0.72 那版 545/211 也要被挡回去）
            --     ② 材料区预算（炼金实测 297）
            --     ③ 名称列按本页最长名现算（写死 150 时名称与材料之间白 122px）
            ck("★★ 左栏明显宽于右栏（右栏收窄，宽度留给左栏）",
               PD.COL_LW >= PD.COL_RW * 2.4,
               "COL_LW=" .. PD.COL_LW .. " / COL_RW=" .. PD.COL_RW)
            ck("★★ 材料区预算足够宽（炼金 ≥290 —— 改前只有 157，材料串被截成「…」）",
               PD.LV_MAT_W >= 290,
               "LV_MAT_W=" .. PD.LV_MAT_W .. "（LV_NAME_X=" .. PD.LV_NAME_X
               .. " LV_CNT_W=" .. PD.LV_CNT_W .. "）")
            local _maxnm = 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.e and r.e.__text and r.e.__text ~= ""
                 and r.c and r.c.__text and tostring(r.c.__text):find("次制作", 1, true) then
                local w = PD.TextW(r.e.__text, PD.LV_FS)
                if w > _maxnm then _maxnm = w end
              end
            end
            ck("★★ 名称列宽 = 本页最长配方名（不再写死 150 → 名称与材料之间不留大片白）",
               _maxnm > 0 and PD.LV_NAME_W <= math.max(PD.TBL_NAME_MIN, math.ceil(_maxnm) + 4),
               "LV_NAME_W=" .. PD.LV_NAME_W .. " / 最长名=" .. string.format("%.1f", _maxnm))
            -- ★★ 五轮：名称列 + 材料区**正好吃满**可用宽 —— 多留一像素白就是材料块被少画一块
            --   （用户反复点名的「材料要显示完全」在几何上就是这个等式）。
            do
            local _avail = PD.COL_LW - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP
                           - PD.LV_CNT_W - PD.TBL_CNT_GAP
            ck("★★ 名称列 + 材料区正好吃满可用宽（不留白 —— 余量全给材料块）",
               PD.LV_NAME_W + PD.LV_MAT_W == _avail,
               "LV_NAME_W=" .. PD.LV_NAME_W .. " + LV_MAT_W=" .. PD.LV_MAT_W
               .. " = " .. (PD.LV_NAME_W + PD.LV_MAT_W) .. " / avail=" .. _avail)
            end
            ck("★ 材料优先分配：至少保住了名称列下限（材料区拿的是余量，不是被名称列挤掉）",
               PD.LV_NAME_W >= PD.TBL_NAME_MIN and PD.LV_MAT_W > 0,
               "LV_NAME_W=" .. PD.LV_NAME_W .. " / LV_MAT_W=" .. PD.LV_MAT_W)
            -- 右栏确实排了备料清单（col = 2 的行）
            local _r2 = 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.col == 2 and sp.kind == "row" then _r2 = _r2 + 1 end
            end
            ck("★★ 右栏排了备料清单（col = 2 的行）", _r2 > 0, _r2)
            -- 悬停带「配方名 + 来源 + 材料全量」：行内只放得下几块，放不下的靠这里不丢
            local _tip = 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.lvstep and sp.lines and #sp.lines >= 3 then _tip = _tip + 1 end
            end
            ck("★★ 升级分段行悬停带「配方名 + 来源 + 材料全量」（行内放不下的信息不丢）",
               _tip == 17, _tip)
            -- ★★ 六轮：斑马纹真的画上了 —— 真行隔行 __z = true、底 alpha = ZEBRA_A、
            --   描边 alpha = 0；非真行（标题/说明/空档）__z = false → 底描边全透明。
            --   底色 alpha 靠上面「临时包一层」记的 __bgA 亲眼看见，否则这条断言恒真。
            --   整段套 do ... end（局部变量出块即释放，见前面 200 局部上限说明）。
            do
              local _z, _bad, _nil, _hover = 0, 0, 0, 0
              for _, r in ipairs(PD.rows or {}) do
                if r.__shown ~= false and r.__w and r.__w > 0 then
                  if r.__bgA == nil then _nil = _nil + 1 end
                  if r.__hlOn then _hover = _hover + 1 end
                  if r.__bgA ~= (r.__z and PD.ZEBRA_A or 0) then _bad = _bad + 1 end
                  if r.__z then
                    _z = _z + 1
                    local bd = r.__border
                    if not (bd and bd[4] == 0) then _bad = _bad + 1 end
                  end
                end
              end
              ck("★★ 斑马纹：隔行真行底纹 = ZEBRA_A、描边 = 0；其余行全透明",
                 _z > 0 and _bad == 0,
                 "striped=" .. _z .. " bad=" .. _bad .. " nilA=" .. _nil
                 .. " hover=" .. _hover)
            end
            PD.Show("alchemy")
            PD.SetTab("recipe")
            ck("★ 配方页不挂分栏线（PD.lvSplit 复位 → divider 隐藏；配方页是单列）",
               PD.lvSplit == false and PD.divider.__shown == false)
            -- ★★ 单列页的行必须是**整幅**：lvSplit 复位后 col == 1 不能再收 COL_LW
            --   （col == 1 是所有单列页共用的分支 —— 这里压窄，配方/总览/采集/传承全跟着窄）
            local _fullw = PD.RIGHT_W - 2 * PD.LIST_PAD
            local _wide2, _narrow2 = 0, 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__w and r.__w > 0 then
                if r.__w == _fullw then _wide2 = _wide2 + 1
                else _narrow2 = _narrow2 + 1 end
              end
            end
            ck("★★ 单列页（配方页）所有行满幅 —— col=1 不许被压窄成 COL_LW",
               _wide2 > 0 and _narrow2 == 0,
               tostring(_wide2) .. " 宽 / " .. tostring(_narrow2) .. " 窄")
            PD.Show("alchemy")
            PD.SetTab("overview")
            -- ★ 总览重设计（2026-09-24 方案 B + 实机二轮）：左右双栏 + 每个内容块一张段落卡。
            --   营地三档从 span 通栏挪回左栏收尾（通栏在左栏下留整片空白，实机被否）。
            ck("★ 总览页走左右双栏（lvSplit 亮、竖向分栏线举手隐藏、0.62 分栏举手）",
               PD.lvSplit == true and PD.divider.__shown == false
               and PD.hideDivider == true
               and PD.splitLW ~= nil and PD.splitRW ~= nil
               and PD.splitRW > PD.COL_RW)
            local _ovL, _ovR = 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.col == 2 then _ovR = _ovR + 1 else _ovL = _ovL + 1 end
            end
            ck("★★ 总览双栏：左右两栏都有行", _ovL > 0 and _ovR > 0,
               tostring(_ovL) .. "L / " .. tostring(_ovR) .. "R")
            local _ovSecs, _ovSecRows = 0, 0
            for _, c in ipairs(PD.secCards or {}) do
              if c.__shown ~= false then _ovSecs = _ovSecs + 1 end
            end
            for _, sp in ipairs(PD.specs or {}) do
              if sp.sec then _ovSecRows = _ovSecRows + 1 end
            end
            ck("★★ 总览每个内容块一张段落卡（炼金术 5 段：简介/认证/速览/里程碑/营地）",
               _ovSecs >= 5 and _ovSecs <= 6 and _ovSecRows >= 10,
               tostring(_ovSecs) .. " 卡 / " .. tostring(_ovSecRows) .. " 行入段")
            local _ovZ = 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__z then _ovZ = _ovZ + 1 end
            end
            ck("★★ 段落卡页不出斑马纹（卡给块状结构，条纹叠卡里是噪声）", _ovZ == 0, _ovZ)
            local _ovW = PD.RIGHT_W - 2 * PD.LIST_PAD
            local _ovBadW = 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__w and r.__w > _ovW then _ovBadW = _ovBadW + 1 end
            end
            ck("★★ 总览行不超出行区宽（两栏行 = 各自栏宽）", _ovBadW == 0, tostring(_ovBadW))
            PD.Show("__index")
            PD.SetTab("overview")
            ck("★ 全部专业首页仍是单列（lvSplit 复位、分栏线隐藏）",
               PD.lvSplit == false and PD.divider.__shown == false)
            -- ⑰ 全部专业总览：三列导航宫格（2026-09-24 方案 B）。
            --   整段套 do ... end：新加的局部出块即释放（200 局部上限纪律）。
            do
              ck("★★ 全部专业总览举手挂宫格（wantIndexGrid 亮、整块 root 显示）",
                 PD.wantIndexGrid == true and PD.ixRoot ~= nil and PD.ixRoot.__shown == true,
                 tostring(PD.wantIndexGrid) .. "/" .. tostring(PD.ixRoot and PD.ixRoot.__shown))
              local _ixn = #(PD.ixCards or {})
              ck("★★ 宫格 13 张卡都建出来了（13 专业 × 四段分组）", _ixn == 13, _ixn)
              local _ixNamed = 0
              for _, c in ipairs(PD.ixCards or {}) do
                if c.name and c.name.__text and c.name.__text ~= "" then _ixNamed = _ixNamed + 1 end
              end
              ck("★★ 每张卡都有名字（数据静态填定，不依赖客户端懒加载）",
                 _ixNamed == _ixn, tostring(_ixNamed) .. " / " .. tostring(_ixn))
              local _ixAlc
              for _, c in ipairs(PD.ixCards or {}) do
                if c.name and c.name.__text == "炼金术" then _ixAlc = c end
              end
              if _ixAlc and _ixAlc.__scripts and _ixAlc.__scripts.OnClick then
                _ixAlc.__scripts.OnClick(_ixAlc)
                ck("★★ 点炼金术卡 → 直达该专业总览（与左列导航同一条路）",
                   PD.cur == "alchemy" and PD.tab == "overview",
                   tostring(PD.cur) .. "/" .. tostring(PD.tab))
              end
              PD.Show("__index")
              PD.SetTab("overview")
              local _ixCamp
              for _, c in ipairs(PD.ixCards or {}) do
                if c.name and c.name.__text == "营地" then _ixCamp = c end
              end
              if _ixCamp and _ixCamp.__scripts and _ixCamp.__scripts.OnClick then
                _ixCamp.__scripts.OnClick(_ixCamp)
                ck("★★ 点营地卡 → 直达「职业加成」对照表（camping + bonus 视图）",
                   PD.cur == "camping" and PD.tab == "camp" and PD.campView == "bonus"
                   and PD.wantBonusTable == true and PD.bonusTable.__shown == true,
                   tostring(PD.cur) .. "/" .. tostring(PD.tab) .. "/" .. tostring(PD.campView))
              end
              PD.Show("alchemy")
              PD.SetTab("overview")
              ck("★ 离开全部专业 → 宫格整块隐藏、举手复位",
                 PD.ixRoot.__shown == false and PD.wantIndexGrid == false,
                 tostring(PD.ixRoot.__shown) .. "/" .. tostring(PD.wantIndexGrid))
            end
            PD.Show("alchemy")
            PD.SetTab("leveling")
            ck("★ 升级页仍用 0.80 默认分栏（总览的 0.62 举手不外溢）",
               PD.lvSplit == true and PD.splitLW == nil and PD.splitRW == nil)
            PD.Show("alchemy")
            PD.SetTab("overview")

            -- ② 营地页「加成」：对照表只在这里（2026-09-24 从首页搬到「营地」名下；
            --    二轮：页签直接改名「职业加成」，不再多套一层工具钮）
            PD.Show("camping")
            PD.SetTab("camp")
            ck("★★ 营地页只有「加成」一支、自动落在它上面（对照总表就绪）",
               PD.campView == "bonus" and PD.wantBonusTable == true
               and PD.bonusTable ~= nil and PD.bonusTable.__shown == true,
               tostring(PD.campView) .. "/" .. tostring(PD.wantBonusTable))
            ck("★ camping 的营地页签已改名「职业加成」（点页签直达对照表）",
               PD.subBtns.camp ~= nil and PD.subBtns.camp:GetText() == "职业加成",
               tostring(PD.subBtns.camp and PD.subBtns.camp:GetText()))
            local _anyTool = false
            for _ti = 1, (PD.TOOL_MAX or 0) do
              local _tb = PD.toolBtns and PD.toolBtns[_ti]
              if _tb and _tb.__shown ~= false then _anyTool = true end
            end
            ck("★ camping 对照页不再套工具条一层（联盟/部落/职业加成钮全不亮）",
               not _anyTool)
            -- ★★ 2026-09-24 六轮（方案 A 定稿）：五列对照总表 —— 整块 do…end
            --   防 main chunk 200 局部上限（与 ⑰ 宫格块同口径）
            do
              local _n, _named, _green, _cellsv = 0, 0, 0, 0
              for _, br in ipairs(PD.bonusTable.__rows or {}) do
                if br.__shown ~= false then
                  _n = _n + 1
                  if br.name and br.name.__text and br.name.__text ~= "" then
                    _named = _named + 1
                  end
                  if br.cmp2 and br.cmp2.__text
                     and tostring(br.cmp2.__text):find("|cff7fdc7f", 1, true) then
                    _green = _green + 1
                  end
                  for _, cf in ipairs(br.cells or {}) do
                    if cf.__text and cf.__text ~= "" then _cellsv = _cellsv + 1 end
                  end
                end
              end
              ck("★★ 有营地的专业都进了总表（>= 12 行、行行有名字）",
                 _n >= 12 and _named == _n, tostring(_n) .. " / " .. tostring(_named))
              ck("★★ 对照列写出增益/功能：绿字 >= 11 行（11 增益 + 烹饪容量）",
                 _green >= 11, _green)
              ck("★★ 三档物件列真的填了内容（>= 34 格）", _cellsv >= 34, _cellsv)
            end
            PD.Show("alchemy")
            PD.SetTab("camp")
            ck("★ 有营地数据的专业默认联盟视图（2 段、对照总表收起）",
               PD.campView == "a" and PD.hasSecs == true and PD.secCount == 2
               and PD.bonusTable.__shown == false)
            -- ②b 营地页卡片化（2026-09-24 用户定稿「三档合一卡」）：联盟/部落视图两段两卡
            --    （特权段已删：传承内容归 Legacy 页，与营地无关——用户 2026-09-24 定）
            ck("★★ 营地联盟视图套段落卡（物件/坐标 = 2 段，特权段不再出现在营地页）",
               PD.hasSecs == true and PD.secCount == 2, tostring(PD.secCount))
            local _sec1Rows, _campCards = 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.sec == 1 and sp.kind == "row" then _sec1Rows = _sec1Rows + 1 end
            end
            for _, c in ipairs(PD.secCards or {}) do
              if c.__shown ~= false then _campCards = _campCards + 1 end
            end
            ck("★★ 三档合一卡：第 1 段 3 档行、可见卡数 = 段数",
               _sec1Rows == 3 and _campCards == PD.secCount,
               tostring(_sec1Rows) .. " 行 / " .. tostring(_campCards) .. " 卡")
            local _campZ = 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__z then _campZ = _campZ + 1 end
            end
            ck("★★ 段落卡页不出斑马纹（与总览同口径）", _campZ == 0, _campZ)
            PD.onTool("h")
            ck("★ 切部落 → 物件视图切换（仍是 2 段段落卡）",
               PD.campView == "h" and PD.hasSecs == true and PD.secCount == 2,
               tostring(PD.campView))
            local _bonusBtn = false
            for _ti = 1, (PD.TOOL_MAX or 0) do
              local _tb = PD.toolBtns and PD.toolBtns[_ti]
              if _tb and _tb.__shown ~= false and _tb:GetText() == "职业加成" then
                _bonusBtn = true
              end
            end
            ck("★★ 「职业加成」钮只在营地系统名下（有物件专业的营地页不放它，2026-09-24 用户定）",
               _bonusBtn == false)
            PD.onTool("a")
            ck("★ 切回联盟 → 段落卡恢复", PD.hasSecs == true and PD.secCount == 2)
            PD.SetTab("overview")
            ck("★ 有营地数据的专业总览不落加成视图（对照页只在「营地」名下）",
               PD.campView ~= "bonus")
            PD.Show("camping")
            PD.SetTab("camp")
            ck("★ 切走再切回来 → 职业加成对照总表还在",
               PD.campView == "bonus" and PD.wantBonusTable == true
               and PD.bonusTable.__shown == true)
            PD.Show("alchemy")

            -- ⑲ 营地/军需官 → 地图标记（2026-09-24 用户：点军需官坐标在地图上标记 + 这一段汉化）
            -- ★★ 二轮（用户实机报「未收录该位置的地图」）：无限服源码 1.60.1 全库没有
            --    C_Map.GetMapInfoFromAreaID → 主路径改静态映射（CAMP_AREA_MAP），
            --    本块**不**挂该 API 桩模拟真机；区域名走 GetAreaInfo（无限服有）。
            do
              PD.Show("alchemy")
              PD.SetTab("camp")
              -- 上游钓鱼页断言块收尾会把**全局** C_Map = false（坑档案 #8 口径），
              -- 本块在它之后跑 → 先恢复 C_Map 桩表（与 env 桩同一套四件）。
              if type(C_Map) ~= "table" then
                C_Map = {
                  CanSetUserWaypointOnMap = function() return true end,
                  SetUserWaypoint = function(pt) C_MAP_MARK.wp = pt end,
                  OpenWorldMap = function(mapID) C_MAP_MARK.opened = mapID end,
                }
              end
              C_Map.GetAreaInfo = function(id)
                if id == 44 then return "赤脊山" end
                if id == 17 then return "贫瘠之地" end
                return nil
              end
              local _vspec, _cspec
              for _, sp in ipairs(PD.specs or {}) do
                if type(sp.text) == "string" and sp.text:find("军需官 · ", 1, true) then _vspec = sp end
                if type(sp.text) == "string" and sp.text:find("营地 · ", 1, true) then _cspec = sp end
              end
              ck("★ 军需官行已汉化（zh.json 套用：名/职责中文）",
                 _vspec ~= nil and _vspec.text == "军需官 · 妮娜·神火" and _vspec.sub == "军需官",
                 _vspec and (_vspec.text .. " | " .. tostring(_vspec.sub)) or "nil")
              ck("★ 营地行区域名走客户端（GetAreaInfo 解析 AreaID 44 → 赤脊山）",
                 _cspec ~= nil and _cspec.sub == "赤脊山 · 艾泽拉斯商会",
                 _cspec and tostring(_cspec.sub) or "nil")
              ck("★★ 两行都可点且带悬停提示（act + lines）",
                 _vspec ~= nil and type(_vspec.act) == "function" and _vspec.lines ~= nil
                 and _cspec ~= nil and type(_cspec.act) == "function" and _cspec.lines ~= nil)
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              _vspec.act()
              ck("★★ 点军需官行 → 航点落赤脊山(1433) 10.8,72.4 并开图（静态映射主路径）",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1433
                 and C_MAP_MARK.wp.x == 10.8 / 100 and C_MAP_MARK.wp.y == 72.4 / 100
                 and C_MAP_MARK.opened == 1433,
                 C_MAP_MARK.wp and tostring(C_MAP_MARK.wp.uiMapID) or "nil")
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              _cspec.act()
              ck("★★ 点营地行 → 航点落赤脊山(1433) 10.3,72.5",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1433
                 and C_MAP_MARK.wp.x == 10.3 / 100 and C_MAP_MARK.wp.y == 72.5 / 100)
              -- API 后备路径：静态表没有的区域（99）→ 真有 GetMapInfoFromAreaID 的客户端走 API
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              C_Map.GetMapInfoFromAreaID = function(id)
                if id == 99 then return { name = "测试区", mapID = 4242 } end
                return nil
              end
              PD.MarkCampPoint(99, 50.0, 60.0)
              ck("★ 静态表未收录 → API 后备兜住（99 → 4242）",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 4242
                 and C_MAP_MARK.opened == 4242)
              C_Map.GetMapInfoFromAreaID = false
              -- 区域名回退路径：GetAreaInfo 桩摘掉 → 回落数据原文（zh.json 兜底仍中文）
              C_Map.GetAreaInfo = false
              PD.SetTab("recipe")
              PD.SetTab("camp")
              local _cspec2
              for _, sp in ipairs(PD.specs or {}) do
                if type(sp.text) == "string" and sp.text:find("营地 · ", 1, true) then _cspec2 = sp end
              end
              ck("★ 区域名回落数据原文（zh.json 兜底仍是中文）",
                 _cspec2 ~= nil and _cspec2.sub == "赤脊山 · 艾泽拉斯商会",
                 _cspec2 and tostring(_cspec2.sub) or "nil")
              -- 未知区域：静态表和 API 都没有 → 明说不假装（不放航点、不开图）
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              PD.MarkCampPoint(9999, 10.0, 20.0)
              ck("★★ 未知区域明说不假装：不放航点、不开图",
                 C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil)
              PD.Show("alchemy")
            end

            -- ③ 阈值染色：三个数字三种颜色，且界面上不再有「黄绿灰」
            PD.Show("alchemy")
            PD.SetTab("recipe")
            local _hit, _bad, _colors = 0, 0, {}
            for _, sp in ipairs(PD.specs or {}) do
              local t = sp.right
              if type(t) == "string" then
                if t:find("|cff", 1, true) then _hit = _hit + 1 end
                if t:find("黄绿灰", 1, true) then _bad = _bad + 1 end
                for code in t:gmatch("|cff%x%x%x%x%x%x") do _colors[code] = true end
              end
            end
            ck("★★ 配方行的技能阈值带内联色彩码（数字被染色）", _hit > 0, _hit)
            ck("★★ 配方行不再出现「黄绿灰」三个字", _bad == 0, _bad)
            local _nc = 0
            for _ in pairs(_colors) do _nc = _nc + 1 end
            ck("★★ 黄 / 绿 / 灰 三种颜色确实互不相同（同一个色 = 等于没染）",
               _nc >= 3, _nc)

            -- ④ 传承（原 Legacy）
            ck("★★ 子页签第 6 颗文案是「传承」",
               PDM.PROF_SUBTABS[6] ~= nil and PDM.PROF_SUBTABS[6].text == "传承",
               PDM.PROF_SUBTABS[6] and PDM.PROF_SUBTABS[6].text)

            -- ⑤ 分类按钮宽度按文字自适应
            PD.Show("blacksmithing")
            PD.SetTab("recipe")
            local _mn, _mx, _n = nil, nil, 0
            for _, bt in ipairs(PD.toolBtns or {}) do
              if bt.__shown then
                _n = _n + 1
                _mn = (not _mn or bt.__w < _mn) and bt.__w or _mn
                _mx = (not _mx or bt.__w > _mx) and bt.__w or _mx
              end
            end
            ck("★ 配方页分类按钮都显示出来了（>= 4 个）", _n >= 4, _n)
            ck("★★ 按钮宽度不再定死 72（长分类名「磨刀石、平衡石与砂轮」要更宽）",
               _mx ~= nil and _mn ~= nil and _mx >= 140 and _mx > _mn,
               tostring(_mn) .. " ~ " .. tostring(_mx))
            ck("★ 宽度落在下限/上限之间（过窄裁字、过宽挤掉一整行）",
               _mn ~= nil and _mn >= PD.TOOL_MIN_W - 1 and _mx <= PD.TOOL_MAX_W,
               tostring(_mn) .. " / " .. tostring(_mx))
          end

          -- ---------- 悬停高亮：划走必须灭（用户 2026-09-24 报「高亮一直显示」）----------
          -- 桩把 SetBackdropBorderColor 的实参记在 __border、IsMouseOver 读 __mouseOver，
          -- 于是「亮/灭」与「鼠标在不在这一行」都能直接量。
          do
            PD.Show("blacksmithing")
            PD.SetTab("recipe")
            local _hr
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__scripts and r.__scripts.OnEnter then
                _hr = r; break
              end
            end
            ck("★ 行池里有可测悬停的行", _hr ~= nil)
            if _hr then
              _hr.__mouseOver = false
              _hr.__scripts.OnEnter(_hr)
              local _hi = _hr.__border and _hr.__border[4]
              _hr.__scripts.OnLeave(_hr)
              local _lo = _hr.__border and _hr.__border[4]
              ck("★★ 划过 → 描边亮起；划走 → 回到 0（不是常态 0.05 —— 那圈淡框正是用户看到的「高亮没退」）",
                 type(_hi) == "number" and _hi > 0 and _lo == 0,
                 tostring(_hi) .. " -> " .. tostring(_lo))
              ck("★★ 划走之后行不再处于「亮着」状态（__hlOn 归 false）", _hr.__hlOn == false)
              -- 失同步：状态停在悬停档、鼠标却已经不在这行上（滚轮滚动 / 池复用后的真实情形）
              _hr.__mouseOver = false
              _hr.__scripts.OnEnter(_hr)
              ck("★ 造出失同步：鼠标不在行上、底色却停在悬停档",
                 _hr.__border[4] > 0 and _hr.__hlOn == true)
              PD.SyncHover()
              ck("★★ 同步一次即归位（滚轮滚动不补发 OnLeave 也能自愈）",
                 _hr.__border[4] == 0 and _hr.__hlOn == false, tostring(_hr.__border[4]))
              -- 反向：鼠标真在这一行上时，同步不许把高亮熄掉（只灭一个方向 = 同步逻辑写反）
              _hr.__mouseOver = true
              PD.SyncHover()
              ck("★★ 反向：鼠标真在行上时同步不许熄灭它",
                 _hr.__border[4] > 0 and _hr.__hlOn == true, tostring(_hr.__border[4]))
              _hr.__mouseOver = false
              PD.SyncHover()
              ck("★ 鼠标移开后同步把它灭掉", _hr.__border[4] == 0, tostring(_hr.__border[4]))
            end
          end

          -- ---------- 切回副本页：三页互斥不破、副本页照旧可用 ----------
          U:SwitchSub("Dungeons")
          ck("★ 切回 5人本 → 专业页隐藏", U.profPage.__shown == false)
          ck("★ 切回 5人本 → 副本页显示且仍是已构建态",
             U.dungeonPage.__shown == true and U.dungeonBuilt == true)
        end
      end
    end
"""
if PROF_ANCHOR not in text:
    sys.exit('未找到⑬步动态插入锚点（harness 尾部可能已改动）')
text = text.replace(PROF_ANCHOR, PROF_EXTRA + PROF_ANCHOR, 1)
print('  %-30s → %d 处' % ('⑬专业页动态断言块', 1))


# ── ⑫ 提示框换肤：装备提示框不套插件皮（2026-09-23 用户口径）────────────────────
# 用户原话：「现在如果是装备的鼠标提示框，我希望不是我的UI」。
# 为什么必须补桩：Hui.lua 的「这个提示框要不要套插件皮」全部发生在 GameTooltip 的 OnShow 里，
#   而桩原先只把 OnShow 记进 __scripts、Show 只置 __shown —— **从不触发**，于是这段逻辑
#   离线零覆盖（改坏了也全绿：这正是本次实机症状能在离线全绿的前提下存活的原因）。
# 补桩只动 GameTooltip / ItemRefTooltip 两个暴雪帧，不碰 CreateFrame、不碰 TOOLTIP_LINES。
TIP_STUB_ANCHOR = "    loadfile = lua.eval(\n"
TIP_STUB_EXTRA = r"""    # ★ 提示框换肤的桩（2026-09-23，见 mk_df_check.py 第⑫步）：
    #   ① Show 按客户端语义在「隐藏→显示」时触发 OnShow（真帧的 widget 脚本就是这个时序），
    #      否则 Hui.lua 的换肤判定（全在 OnShow 里）在离线 harness 中永不执行；
    #   ② SetOwner / GetOwner 记真 owner —— TooltipOwnerIsMine 靠 owner 父链判归属；
    #   ③ GetItem 回真内容（物品提示框的内容判据）、NineSlice alpha 记成数字（皮生效 = 0）；
    #   ④ ClearLines 顺带清内容（真帧 ClearLines 之后 GetItem 回 nil，防上一轮物品内容残留）。
    #   AddLine / ClearLines 的记账仍走原桩（断言依赖 TOOLTIP_LINES），这里只包一层。
    lua.execute(r'''
do
  local function tipPatch(tt)
    local oldShow, oldHide, oldClear = tt.Show, tt.Hide, tt.ClearLines
    tt.Show = function(self)
      local was = rawget(self, "__shown")
      oldShow(self)
      if was ~= true then
        local s = rawget(self, "__scripts")
        local fn = s and s.OnShow
        if fn then fn() end
      end
      return self
    end
    tt.Hide = function(self) oldHide(self) return self end
    -- ⚠️ 真客户端里 hooksecurefunc(GameTooltip, "SetOwner") 会在每次 SetOwner 之后清掉
    --    「物品内容标记」；桩的 hooksecurefunc 是**空实现**（function hooksecurefunc() end）
    --    → 不补这一步的话，物品标一旦打上就永久残留（跨用例污染：后面的文字提示框会被
    --    误判成物品提示框）。这里按真实语义等价补一次（清标走插件自己的公开口）。
    tt.SetOwner = function(self, owner)
      rawset(self, "__owner", owner)
      local hui = TF_NS and TF_NS.hui
      if hui and hui.MarkTipItem then hui.MarkTipItem(self, nil) end
      return self
    end
    tt.GetOwner = function(self) return rawget(self, "__owner") end
    tt.GetItem = function(self) return rawget(self, "__itemName"), rawget(self, "__itemLink") end
    tt.ClearLines = function(self)
      rawset(self, "__itemName", nil)
      rawset(self, "__itemLink", nil)
      return oldClear(self)
    end
    local ns9 = rawget(tt, "NineSlice")
    if ns9 then
      ns9.GetAlpha = function(self) return rawget(self, "__alpha") or 1 end
      ns9.SetAlpha = function(self, a) rawset(self, "__alpha", a) return self end
    end
  end
  tipPatch(GameTooltip)
  tipPatch(ItemRefTooltip)
end
''')
"""
if TIP_STUB_ANCHOR not in text:
    sys.exit('未找到⑫步桩补丁锚点（harness 可能已改动）')
text = text.replace(TIP_STUB_ANCHOR, TIP_STUB_EXTRA + TIP_STUB_ANCHOR, 1)
print('  %-30s → %d 处' % ('⑫提示框换肤桩', 1))

# 动态断言：同一 owner、同一 Show 链路，只把内容从「文字」换成「物品」
#   · 文字（AddLine 拼装）→ 皮必须生效（NineSlice 压 0 + 皮件亮起）
#   · 物品（SetItemByID 路径，正是 DG.ShowItemTip 的首选分支且**不打标**）→ 皮必须退场
#   两者互为对照：只断「物品不套皮」会恒真（桩里本来就不开皮），必须有「文字套皮」的正例。
#   末条走真·用户场景（掉落实物卡 OnEnter → DG.ShowItemTip 全链）。
TIP_DYN_ANCHOR = "      -- ---------- 按需加载：预热 + 数据到货自动重刷 ----------\n"
TIP_DYN_EXTRA = r"""      -- ---------- 提示框换肤：装备提示框不套插件皮（2026-09-23 用户口径）----------
      -- 用户原话：「现在如果是装备的鼠标提示框，我希望不是我的UI」。
      -- 成因：DG.ShowItemTip 的首选分支 GameTooltip:SetItemByID **不打 ttItemMark**，
      --   而「物品内容撤皮」那条发生在 **Show 之前**（内容先于显示赋值）→ 紧随其后的
      --   OnShow 又按归属把皮亮回来 → 实机表现「悬停装备仍是插件皮」。
      -- 判据用两个独立信号一起钉（避免只钉一个桩细节）：
      --   · NineSlice alpha：皮生效 = 0（暴雪皮被压掉），退场 = 恢复原 alpha；
      --   · 可见皮件数：相对另一个状态必然变化。
      -- owner 用 ns.hui.RegisterTooltipRoot 登记成「本插件归属」（Hui.lua 的兜底口）。
      do
        local function _pieces()
          local n, list = 0, rawget(GameTooltip, "__children")
          for i = 1, (list and #list or 0) do
            if rawget(list[i], "__shown") then n = n + 1 end
          end
          return n
        end
        local function _tipAlpha()
          local ns9 = rawget(GameTooltip, "NineSlice")
          return ns9 and (rawget(ns9, "__alpha") or 1) or -1
        end
        local _oldByID, _oldLink, _oldNL =
          GameTooltip.SetItemByID, GameTooltip.SetHyperlink, GameTooltip.NumLines
        TF_NS.hui.RegisterTooltipRoot(row)
        -- 零点：此刻皮是关的（加载期 RefreshGameTooltipSkin 已把皮件全隐），四条断言都以它为参照，
        -- 不互相耦合 —— 这样变异「物品判据退回只看打标」只会打红两条**物品**断言，
        -- 归因干净（若这里不是 0，说明桩基线变了，会立刻暴露成四条一起红）。
        local _baseP = _pieces()
        ck("★ 桩基线：未套皮时皮件数 = 0（下面四条断言共同的零点）", _baseP == 0, _baseP)

        -- ① 本插件自己的文字提示框（AddLine 拼装 + owner 归属本插件）→ 皮必须生效
        GameTooltip:Hide()
        GameTooltip:SetOwner(row, "ANCHOR_TOP")
        GameTooltip:ClearLines()
        GameTooltip:AddLine("文字提示", 1, 1, 1, true)
        GameTooltip:Show()
        local _t1a, _t1p = _tipAlpha(), _pieces()

        -- ② 同一 owner、同一 Show 链路，只把内容换成物品（SetItemByID 路径）→ 皮必须退场
        GameTooltip:Hide()
        GameTooltip.SetItemByID = function(self, i)
          rawset(self, "__itemLink", "item:" .. tostring(i))
          rawset(self, "__itemName", "装备")
          self.__n = 12
        end
        GameTooltip.SetHyperlink = function(self, link)
          rawset(self, "__itemLink", tostring(link))
          self.__n = 12
        end
        GameTooltip.NumLines = function(self) return self.__n or 0 end
        GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
        GameTooltip:ClearLines()
        GameTooltip:SetItemByID(GameTooltip, 12345)
        GameTooltip:Show()
        local _t2a, _t2p = _tipAlpha(), _pieces()

        -- ③ 再换回文字内容 → 皮必须还能开回来（防「见过一次物品就永久关皮」）
        GameTooltip:Hide()
        GameTooltip:SetOwner(row, "ANCHOR_TOP")
        GameTooltip:ClearLines()
        GameTooltip:AddLine("文字提示二", 1, 1, 1, true)
        GameTooltip:Show()
        local _t3a, _t3p = _tipAlpha(), _pieces()

        -- ④ 真·用户场景：掉落实物卡 OnEnter（走 DG.ShowItemTip 全链，含打标分支）→ 皮退场
        GameTooltip:Hide()
        row.__scripts.OnEnter(row)
        local _t4a, _t4p = _tipAlpha(), _pieces()

        ck("★ 文字提示框（归属本插件）套插件皮：NineSlice 压到 0 + 皮件亮起",
           _t1a == 0 and _t1p > _baseP, _t1a .. " / " .. _t1p .. " vs " .. _baseP)
        ck("★★ 装备提示框（SetItemByID 路径，不打标）不套插件皮：皮退场回暴雪默认",
           _t2a ~= 0 and _t2p == _baseP, _t2a .. " / " .. _t2p .. " vs " .. _baseP)
        ck("★ 换回文字提示框皮能开回来（物品判据不是一票封死）",
           _t3a == 0 and _t3p > _baseP, _t3a .. " / " .. _t3p .. " vs " .. _baseP)
        ck("★★ 悬停掉落实物卡（DG.ShowItemTip 全链）→ 不套插件皮",
           _t4a ~= 0 and _t4p == _baseP, _t4a .. " / " .. _t4p .. " vs " .. _baseP)

        GameTooltip:Hide()
        GameTooltip.SetItemByID, GameTooltip.SetHyperlink, GameTooltip.NumLines =
          _oldByID, _oldLink, _oldNL
      end

"""
if TIP_DYN_ANCHOR not in text:
    sys.exit('未找到⑫步动态断言锚点（harness 可能已改动）')
text = text.replace(TIP_DYN_ANCHOR, TIP_DYN_EXTRA + TIP_DYN_ANCHOR, 1)
print('  %-30s → %d 处' % ('⑫提示框换肤动态断言', 1))


# ── ⑭ 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）─────────────────
# 用户原话：「给 2040 这个前导任务需要备注一下：不需要接 2041 就可以接」。
# 2040 的直连前置写的是 2041（诺恩给的引导任务），界面会在「前导任务」区把它渲染成
# 一个链节点 + 「下一步」标 → 很容易被读成「必须先接 2041」。备注落在数据层的
# ns.DungeonQuestPreNote[questID]（由 _temp/sync_data.py 注入）+ 界面层链节点下方渲染。
#
# ★ 为什么静态锚点选在「链节点标记入口」那条**之后**：那一行之前 seg_qdet / qdetcode
#   （函数体切片、剥注释）还没算出来，插在前面会 NameError。
# ★ 静态断言查的是 qdetcode（已剥注释的切片）而不是全文 src —— 注释里的同名串会让
#   「存在性」断言恒真（本项目踩过这类白测）。
QNOTE_STATIC_ANCHOR = (
    "    ck('★ 链节点标记入口（node 池 Button 化 + 前导/后续 __npc，2026-09-22）',\n"
    "       'r = CreateFrame(\"Button\", nil, child, \"BackdropTemplate\")' in src\n"
    "       and 'if not nid and ns.QuestPreNpcID then nid = ns.QuestPreNpcID[seg] end' in src\n"
    "       and 'r.__npc = fq[16]' in src\n"
    "       and 'for i = pool.nNpc + 1, #pool.npc do pool.npc[i]:Hide() end' in src)\n"
)
QNOTE_STATIC_EXTRA = r"""
    # ★ 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）。
    #   静态这半边钉两件事：渲染代码真的在详情函数体里 + 数据表真的发射了 2040 那条。
    #   动态那半边（本文件 LUA_SCRIPT 里）真渲染一遍，看这行到底有没有出来；两半互为证伪
    #   （典型脱节：数据发射了但界面没渲染、或渲染挂了但数据表是空的）。
    ck('★ 前导链备注渲染（数据层 DungeonQuestPreNote：链上某些环其实非必需）',
       'local pnote = ns.DungeonQuestPreNote and ns.DungeonQuestPreNote[q[1]]' in qdetcode
       and 't:SetText(pnote)' in qdetcode
       and 'ns.DungeonQuestPreNote = {' in qdat
       and '[2040] = "' in qdat)
    ck('★ 前导链备注取的是**本任务**那一条（键 = questID，不是前置环 ID）',
       qdetcode.count('ns.DungeonQuestPreNote[q[1]]') == 1)
"""
if text.count(QNOTE_STATIC_ANCHOR) != 1:
    sys.exit('未找到⑭步静态断言锚点（链节点标记入口），上游 harness 可能已改动')
text = text.replace(QNOTE_STATIC_ANCHOR, QNOTE_STATIC_ANCHOR + QNOTE_STATIC_EXTRA, 1)
print('  %-30s → %d 处' % ('⑭前导链备注静态断言', 2))

QNOTE_DYN_ANCHOR = (
    '    ck("★ 源头环节副标题 = 起始NPC（65 → 格里安·斯托曼）",\n'
    '       sub65 and sub65:find("格里安·斯托曼", 1, true) ~= nil, sub65)\n'
)
QNOTE_DYN_EXTRA = r"""
    -- ---------- 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）------------
    -- 用户原话：「给 2040 这个前导任务需要备注一下：不需要接 2041 就可以接」。
    -- 两条一起测：① 有备注的（2040）真渲染出来；② 没备注的（同副本 214，同样有前置）
    -- 不许长出这一行 —— 少了②，把备注写成「无备注也渲染」照样绿（等于给全表加了一行）。
    do
      U:ShowDungeonDetail(dm)
      U.dungeonQSide = "all"
      U.dungeonQFilter = "all"
      U:SetDungeonTab("quest")
      local q2040, q214
      for _, r in ipairs(qpool0.row) do
        if r.__q and r.__q[1] == 2040 then q2040 = r end
        if r.__q and r.__q[1] == 214 then q214 = r end
      end
      ck("★ 死亡矿井任务页能定位 2040（沉默的舒尼）与反向对照 214",
         q2040 ~= nil and q214 ~= nil)
      if q2040 then
        q2040.__scripts.OnClick()
        local got
        for _, t in ipairs(U.dungeonQDetPool.txt) do
          if t.__shown and tostring(t.__text):find("2041 不是必须", 1, true) then
            got = tostring(t.__text)
          end
        end
        ck("★★ 前导链备注渲染出来了（2040：2041 非必需，不接也能接）", got ~= nil, tostring(got))
        if q214 then
          q214.__scripts.OnClick()
          local leak = false
          for _, t in ipairs(U.dungeonQDetPool.txt) do
            if t.__shown and tostring(t.__text):find("2041 不是必须", 1, true) then leak = true end
          end
          ck("★ 无备注的任务不长这一行（214 前导链无备注）", not leak)
        end
      end
    end

"""
if text.count(QNOTE_DYN_ANCHOR) != 1:
    sys.exit('未找到⑭步动态断言锚点（源头环节副标题），上游 harness 可能已改动')
text = text.replace(QNOTE_DYN_ANCHOR, QNOTE_DYN_ANCHOR + QNOTE_DYN_EXTRA, 1)
print('  %-30s → %d 处' % ('⑭前导链备注动态断言', 1))


# ── ⑮ 副本入口标记：点副本名 → 在地图上标入口（2026-09-24 用户要求）────────────
# 用户原话：「现在点击 NPC 名字会在地图上标记，我现在需要点击副本名字，能够标记副本的入口」。
# 落点有三层，各配一条断言，缺一层都可能「看着绿、实机点不动」：
#   ① 数据层 ns.DungeonEntry（新表，与 NPCLoc 同形）—— 没有它 MarkEntrance 只会提示未收录；
#   ② 界面层绑定 —— 标题没挂 OnMouseUp 的话，函数写得再对也点不动（本项目踩过：
#      断言只查「函数存在」，结果调用点根本没接上）；
#   ③ 动态真点一次 —— 验证航点真落到该副本入口那张图，而不是「函数存在」就完事。
# 反向对照（必配）：未收录入口的副本（黑石山三兄弟 / 自制新副本）点了**不许**落航点，
# 否则「未收录也照落一个点」会静默骗人。少了这条，全表都长出口也不会被发现。
ENT_DATA_ANCHOR = (
    '      ck("★★ 表外链靠 QuestPreNpcID 兜底且能落旗的用例 >= 80", _hit >= 80, _hit)\n'
    '    end\n'
)
ENT_DATA_EXTRA = r"""
    -- ★ 副本入口坐标表（2026-09-24）：与 NPCLoc 同形（uiMapID + x/y%），走同一条航点链路。
    --   下限守护 23 条（实测：35 个副本里 23 个有公开入口坐标，其余 12 个是本服自制新副本
    --   与黑石山共享大门，等实测值）；坐标必须落在 (0,100)，且 uiMapID 必须能在 NPCLoc 的
    --   地图名表里对上 —— 图号写错会静默标到别的地图上去，这一条专门拦它。
    do
      local _ent, _nEnt, _bad = TF_NS.DungeonEntry, 0, 0
      local _mapName = {}
      for _, _v in pairs(TF_NS.NPCLoc or {}) do _mapName[_v[1]] = _v[4] end
      local _all, _miss = 0, 0
      for _, _dg in ipairs(TF_NS.DungeonData.dungeons) do
        _all = _all + 1
        local _e = _ent and _ent[_dg.id]
        if _e then
          _nEnt = _nEnt + 1
          if not (_e[1] and _e[2] > 0 and _e[2] < 100 and _e[3] > 0 and _e[3] < 100) then
            _bad = _bad + 1
          end
          if not _mapName[_e[1]] then _bad = _bad + 1 end
        else
          _miss = _miss + 1
        end
      end
      ck("★★ 副本入口坐标表落键 >= 23（2026-09-24 实测）", _nEnt >= 23, _nEnt)
      ck("★ 入口坐标全部合法（0<x,y<100）且 uiMapID 能与地图名表对上", _bad == 0, _bad)
      ck("★ 未收录入口的副本 <= 12（自制新副本 + 黑石山共享大门，界面明说不假装）",
         _miss > 0 and _miss <= 12, _miss)
    end
"""
if text.count(ENT_DATA_ANCHOR) != 1:
    sys.exit('未找到⑮步数据守护锚点（QuestPreNpcID 兜底下限），上游 harness 可能已改动')
text = text.replace(ENT_DATA_ANCHOR, ENT_DATA_ANCHOR + ENT_DATA_EXTRA, 1)
print('  %-30s → %d 处' % ('⑮副本入口数据守护', 3))

ENT_STATIC_ANCHOR = QNOTE_STATIC_EXTRA
ENT_STATIC_EXTRA = r"""
    # ★ 副本入口标记（2026-09-24 用户要求）：点副本详情页标题 → 开图放入口航点。
    #   静态这半边钉「链路完整」四件套：端号门禁 → 查入口表 → 放航点 → 开图；
    #   再钉标题真的挂了鼠标事件（只写函数不接调用点是本项目的经典假绿）。
    #   查的是剥注释后的 entcode 切片，避免注释里的同名串把存在性断言顶成恒真。
    entcode = src[src.index('function DG.MarkEntrance'):src.index('function DG.ShowEntranceTip')]
    ck('★★ 副本入口标记航点链路（DG.MarkEntrance：端号门禁 + 查入口表 + UiMapPoint + SetUserWaypoint + OpenWorldMap）',
       entcode != ''
       and 'if ver < 16000 or ver > 16999 then' in entcode
       and 'local loc = dungeonID and ns.DungeonEntry and ns.DungeonEntry[dungeonID]' in entcode
       and 'UiMapPoint.CreateFromCoordinates, mapID, loc[2] / 100, loc[3] / 100' in entcode
       and 'pcall(C_Map.SetUserWaypoint, pt)' in entcode
       and 'pcall(C_Map.OpenWorldMap, mapID)' in entcode)
    ck('★★ 详情标题可点 → DG.MarkEntrance（点副本名标记入口）',
       'U.dungeonDetailTitle:EnableMouse(true)' in src
       and 'U.dungeonDetailTitle:SetScript("OnMouseUp"' in src
       and 'if dd then DG.MarkEntrance(dd.id) end' in src
       and 'U.dungeonDetailTitle:SetScript("OnEnter"' in src
       and 'U.dungeonDetailTitle:SetScript("OnLeave"' in src)
    ck('★ 未收录入口的副本明说不假装（loc 为 nil 时不落航点、只提示）',
       entcode.count('if not loc then') == 1
       and 'L["未收录该副本的入口位置"]' in entcode)
    # ★ 入口指引点（2026-09-24 用户要求）：自制副本可给多段坐标——航点仍落主点（副本入口），
    #   悬停提示框逐行列出指引点（领主大厅：先到铁炉堡楼梯 44.2,52，再下到入口 28.2,47.7）。
    #   有指引行时主点行加「副本入口」前缀，与指引行区分。本条钉提示框真的会渲染 route 行。
    tipcode = src[src.index('function DG.ShowEntranceTip'):src.index('function U:RenderQuestDetail')]
    ck('★★ 入口提示框渲染多段指引点（DungeonEntryRoute 逐行 + 主点加「副本入口」前缀）',
       'local route = d and ns.DungeonEntryRoute and ns.DungeonEntryRoute[d.id]' in tipcode
       and 'L["副本入口"]' in tipcode
       and 'format("%.1f, %.1f", p[2], p[3])' in tipcode)
"""
if text.count(ENT_STATIC_ANCHOR) != 1:
    sys.exit('未找到⑮步静态断言锚点（⑭静态补丁段），上游 harness 可能已改动')
text = text.replace(ENT_STATIC_ANCHOR, ENT_STATIC_ANCHOR + ENT_STATIC_EXTRA, 1)
print('  %-30s → %d 处' % ('⑮副本入口静态断言', 4))

# ── ⑯ 入口芯片静态断言（2026-09-24 用户定：标题右侧按钮，一枚 = 一个可标记的坐标点）──
CHIP_STATIC_EXTRA = r"""
    # ★ 入口芯片（2026-09-24 用户定）：标题右侧一排按钮，一枚 = 一个可标记的坐标点。
    #   静态钉三件：点清单 / 按序号落点 / 芯片建池与排布，链路三口都在活代码里。
    ck('★★ 入口芯片链路（DG.EntrancePoints 点清单 + DG.MarkEntranceAt 按序号落点 + 悬停提示）',
       'function DG.EntrancePoints(dungeonID)' in src
       and 'function DG.MarkEntranceAt(dungeonID, idx)' in src
       and 'function DG.ShowEntrancePointTip(owner, idx)' in src
       and 'local p = pts and pts[idx or 1]' in src)
    ck('★★ 入口芯片建池（Build 一次建好 3 枚 Button、显式抬层、点击走 MarkEntranceAt）',
       'U.dungeonEntChips = {}' in src
       and 'chip.__entIdx = i' in src
       and 'if dd then DG.MarkEntranceAt(dd.id, self.__entIdx) end' in src
       and 'chip:SetFrameLevel(hero:GetFrameLevel() + 1)' in src)
    ck('★★ 入口芯片排布在 ShowDungeonDetail（主点「入口」/ 指引点用数据标签，锚标题右侧）',
       'chip:SetText(p.label or L["入口"])' in src
       and 'chip:SetPoint("LEFT", U.dungeonDetailTitle, "RIGHT", 10, 0)' in src
       and 'chip:SetPoint("LEFT", chips[ci - 1], "RIGHT", 6, 0)' in src)
"""
CHIP_STATIC_ANCHOR = ENT_STATIC_EXTRA      # ⑮ 静态段插完后的整段即锚（必唯一）
if text.count(CHIP_STATIC_ANCHOR) != 1:
    sys.exit('未找到⑯步静态断言锚点（⑮入口静态段），上游 harness 可能已改动')
text = text.replace(CHIP_STATIC_ANCHOR, CHIP_STATIC_ANCHOR + CHIP_STATIC_EXTRA, 1)
print('  %-30s → %d 处' % ('⑯入口芯片静态断言', 3))

ENT_DYN_ANCHOR = QNOTE_DYN_EXTRA
ENT_DYN_EXTRA = r"""
    -- ---------- 副本入口标记：点副本名 → 在地图上标入口（2026-09-24 用户要求）----------
    -- 三个用例：① 有入口坐标的副本 → 航点落到入口那张图；② 未收录的 → 只提示不落点；
    -- ③ 端号门禁（泰坦端不落航点）。用例 ① 的副本与 ② 的副本都从表里现挑，不硬编码
    -- （将来补了黑石山三兄弟的实测值，② 仍能拿到别的未收录副本，不会因数据补全而空跑）。
    do
      local entD, missD, nEnt, nMiss = nil, nil, 0, 0
      for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
        if TF_NS.DungeonEntry and TF_NS.DungeonEntry[dg.id] then
          nEnt = nEnt + 1
          if not entD then entD = dg end
        else
          nMiss = nMiss + 1
          if not missD then missD = dg end
        end
      end
      ck("★ 入口数据正反两个用例都在（有坐标的 + 未收录的）", entD ~= nil and missD ~= nil,
         nEnt .. " 有 / " .. nMiss .. " 无")

      if entD then
        U:ShowDungeonDetail(entD)
        local tt = U.dungeonDetailTitle
        ck("★ 详情标题挂了 OnMouseUp / OnEnter / OnLeave（可点 + 悬停提示）",
           tt.__scripts ~= nil and tt.__scripts.OnMouseUp ~= nil
           and tt.__scripts.OnEnter ~= nil and tt.__scripts.OnLeave ~= nil)
        C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
        if tt.__scripts and tt.__scripts.OnMouseUp then tt.__scripts.OnMouseUp(tt) end
        local e = TF_NS.DungeonEntry[entD.id]
        if IS_FOREVER then
          ck("★★ 点副本标题 → SetUserWaypoint 收到入口 UiMapPoint（x/y 已 /100）",
             C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == e[1]
             and C_MAP_MARK.wp.x == e[2] / 100 and C_MAP_MARK.wp.y == e[3] / 100,
             tostring(C_MAP_MARK.wp and C_MAP_MARK.wp.uiMapID) .. " / " .. tostring(e[1]))
          ck("★ 点副本标题 → OpenWorldMap 打开入口那张图",
             C_MAP_MARK.opened == e[1], tostring(C_MAP_MARK.opened))
        else
          ck("★ 泰坦端点副本标题不落航点（地图标记仅无限客户端支持）",
             C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil)
        end
      end

      if missD then
        U:ShowDungeonDetail(missD)
        C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
        local tt2 = U.dungeonDetailTitle
        if tt2.__scripts and tt2.__scripts.OnMouseUp then tt2.__scripts.OnMouseUp(tt2) end
        ck("★★ 未收录入口的副本：点了不落航点、不开图（明说不假装成功）",
           C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil, missD.id)
      end
      U:ShowDungeonDetail(dm)   -- 还原现场：后续断言依赖死亡矿井
    end

    -- ---------- ⑯ 入口指引点（2026-09-24 用户要求）----------
    -- 自制副本没有公开库可对照，主点 / 指引点的具体值都要有人守（图号写错会静默标到
    -- 别的地图上去——铁炉堡 1455，奥格瑞玛才是 1454）。洛丹伦废墟 = 幽暗城正门口径。
    do
      local r = TF_NS.DungeonEntryRoute and TF_NS.DungeonEntryRoute["hall_of_thanes"]
      ck("★ 入口指引点：领主大厅带 1 段楼梯指引（铁炉堡 44.2,52）",
         r ~= nil and #r == 1 and r[1][1] == 1455 and r[1][2] == 44.2 and r[1][3] == 52
         and r[1][4] ~= nil and r[1][5] ~= nil,
         r and ("#r=" .. #r) or "nil")
      local e = TF_NS.DungeonEntry and TF_NS.DungeonEntry["hall_of_thanes"]
      ck("★ 领主大厅入口主点 = 铁炉堡(1455) 28.2,47.7（航点落这里）",
         e ~= nil and e[1] == 1455 and e[2] == 28.2 and e[3] == 47.7,
         e and (tostring(e[1]) .. " " .. tostring(e[2]) .. "," .. tostring(e[3])) or "nil")
      local e2 = TF_NS.DungeonEntry and TF_NS.DungeonEntry["ruins_of_lordaeron"]
      ck("★ 洛丹伦废墟入口 = 幽暗城正门（提瑞斯法林地 61.9,65.0）",
         e2 ~= nil and e2[1] == 1420 and e2[2] == 61.9 and e2[3] == 65.0,
         e2 and (tostring(e2[1]) .. " " .. tostring(e2[2]) .. "," .. tostring(e2[3])) or "nil")
    end

"""
if text.count(ENT_DYN_ANCHOR) != 1:
    sys.exit('未找到⑮步动态断言锚点（⑭动态补丁段），上游 harness 可能已改动')
text = text.replace(ENT_DYN_ANCHOR, ENT_DYN_ANCHOR + ENT_DYN_EXTRA, 1)
print('  %-30s → %d 处' % ('⑮副本入口动态断言', 6))

# ── ⑯b 入口芯片动态断言（2026-09-24 用户定）─────────────────────────────────
CHIP_DYN_EXTRA = r"""
    -- ---------- ⑯b 入口芯片（2026-09-24 用户定：标题右侧按钮，一枚 = 一个可标记的点）----------
    -- 领主大厅应点亮 2 枚（入口 + 楼梯入口）：点第 2 枚航点落楼梯（44.2,52），
    -- 点第 1 枚落主点（28.2,47.7）；未收录入口的副本整排隐藏。
    do
      local chips = U.dungeonEntChips
      local hallD
      for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
        if dg.id == "hall_of_thanes" then hallD = dg end
      end
      ck("★ 入口芯片池已建（3 枚 Button）", chips ~= nil and #chips == 3, chips and #chips or "nil")
      if hallD and chips then
        U:ShowDungeonDetail(hallD)
        ck("★ 领主大厅点亮 2 枚芯片、第 3 枚隐藏",
           chips[1].__shown == true and chips[2].__shown == true and chips[3].__shown ~= true,
           tostring(chips[1].__shown) .. "/" .. tostring(chips[2].__shown) .. "/" .. tostring(chips[3].__shown))
        ck("★ 芯片文案：主点=「入口」，指引点用数据标签「楼梯入口」",
           chips[1].__text == "入口" and chips[2].__text == "楼梯入口",
           tostring(chips[1].__text) .. " / " .. tostring(chips[2].__text))
        local rt = TF_NS.DungeonEntryRoute and TF_NS.DungeonEntryRoute["hall_of_thanes"]
        local r = rt and rt[1]
        local e = TF_NS.DungeonEntry and TF_NS.DungeonEntry["hall_of_thanes"]
        C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
        chips[2].__scripts.OnClick(chips[2])
        if IS_FOREVER then
          ck("★★ 点第 2 枚芯片 → 航点落楼梯指引点（44.2,52）",
             r ~= nil and C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == r[1]
             and C_MAP_MARK.wp.x == r[2] / 100 and C_MAP_MARK.wp.y == r[3] / 100,
             C_MAP_MARK.wp and tostring(C_MAP_MARK.wp.uiMapID) or "nil")
          C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
          chips[1].__scripts.OnClick(chips[1])
          ck("★★ 点第 1 枚芯片 → 航点落主点（副本入口 28.2,47.7）",
             e ~= nil and C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.x == e[2] / 100
             and C_MAP_MARK.wp.y == e[3] / 100)
        else
          ck("★ 泰坦端点入口芯片不落航点（地图标记仅无限客户端支持）",
             C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil)
        end
      end
      local missD3
      for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
        if not (TF_NS.DungeonEntry and TF_NS.DungeonEntry[dg.id]) then missD3 = dg end
      end
      if missD3 and chips then
        U:ShowDungeonDetail(missD3)
        local nShown = 0
        for i = 1, #chips do if chips[i].__shown then nShown = nShown + 1 end end
        ck("★★ 未收录入口的副本：入口芯片整排隐藏", nShown == 0, nShown)
      end
      U:ShowDungeonDetail(dm)   -- 还原现场：后续断言依赖死亡矿井
    end

"""
CHIP_DYN_ANCHOR = ENT_DYN_EXTRA            # ⑮ 动态段插完后的整段即锚（必唯一）
if text.count(CHIP_DYN_ANCHOR) != 1:
    sys.exit('未找到⑯b步动态断言锚点（⑮入口动态段），上游 harness 可能已改动')
text = text.replace(CHIP_DYN_ANCHOR, CHIP_DYN_ANCHOR + CHIP_DYN_EXTRA, 1)
print('  %-30s → %d 处' % ('⑯入口芯片动态断言', 4))


# ── ⑳ 已学专业导航（2026-09-24 用户定：制皮 45/75 + 主题绿）──────────────────
# 桩补丁： ProfessionUI.Build 现在会注册主题监听（ns.hui.OnThemeChange），
# 桩里的 BG.hui 没这个键 → Build 期 nil call。桩只吞不记（注册行为由静态断言守）。
HUISTUB_ANCHOR = '    lua.execute(T.STUB)\n'
if text.count(HUISTUB_ANCHOR) != 1:
    sys.exit('未找到 hui 主题监听桩锚点（lua.execute(T.STUB)），上游 harness 可能已改动')
text = text.replace(
    HUISTUB_ANCHOR,
    HUISTUB_ANCHOR
    + '    lua.execute("BG.hui.OnThemeChange = function(fn) end")  # ⑳ 主题监听桩\n',
    1)
print('  %-30s → %d 处' % ('⑳ BG.hui.OnThemeChange 桩', 1))


# ── ㉒ 环境与客户端同形（2026-09-29 实机事故：WoW 的 Lua 没有 os 库）──────────────
# 桩跑的是 lupa 真 Lua：标准库齐全（有 os.time）、反而没有全局 time()，与客户端**相反**。
# 于是「写了 os.* 的代码」在离线恒绿、实机必崩 —— 团本页倒计时就栽在这：
# os.time() 抛 attempt to index a nil value，整段 Build 被 xpcall 打断、页面开不出来。
# 这里抹掉 os、补上客户端提供的全局 time()（固定时刻，便于断言「无参调用」那条路径）。
# 锚点仍在 `lua.execute(T.STUB)` 上：⑳ 已把它的桩行插在其后，这里再插就落在两行之间。
CLOCKENV_EXTRA = (
    '    # ★★ 环境与客户端同形（2026-09-29 实机事故）：WoW 的 Lua **没有 os 库**\n'
    '    #    （暴雪用全局 time() / date() / difftime() 顶替），而 lupa 自带完整标准库\n'
    '    #    → 「写了 os.* 的代码」在离线 harness 恒绿、实机必崩（团本页倒计时就栽在这）。\n'
    '    #    这里把 os 抹掉、补上全局 time()（固定时刻，便于断言「无参调用」那条路径）。\n'
    '    #    注意：桩自身不用 os，所以抹掉是安全的；哪天桩要用，得先在这里补等价实现。\n'
    "    lua.execute('os = nil')\n"
    "    lua.execute('time = function() return 1796850000 - 3660 end')\n")
if text.count(HUISTUB_ANCHOR) != 1:
    sys.exit('未找到㉒步锚点（lua.execute(T.STUB)），上游 harness 可能已改动')
text = text.replace(HUISTUB_ANCHOR, HUISTUB_ANCHOR + CLOCKENV_EXTRA, 1)
print('  %-30s → %d 处' % ('㉒ 抹 os / 补全局 time', 1))

# 动态断言：插在「切回副本页」之前（仍在 IS_FOREVER 专业分支内，PD = TF_NS.ProfModule）。
# 桩注入 GetProfessions / GetProfessionInfo（skillLine 走第 7 返回值）：
# 制皮(165)=45/75、急救(129)=88/300 两路对照 + 烹饪未学灰显；
# 注入前先验「桩环境空表不炸」，收尾还原全局桩并验灰显复位（导航不残留绿字）。
NAVSUB_DYN_ANCHOR = ('          -- ---------- 切回副本页：三页互斥不破、副本页照旧可用 ----------\n'
                     '          U:SwitchSub("Dungeons")\n')
if text.count(NAVSUB_DYN_ANCHOR) != 1:
    sys.exit('未找到⑳步动态插入锚点（切回副本页段），上游 harness 可能已改动')
NAVSUB_DYN_EXTRA = r"""
          -- ---------- ⑳ 已学专业导航（2026-09-24 用户定：制皮 45/75 + 主题绿）----------
          do
            local _lv0 = PD.ProfLearned()
            local _empty = true
            for _ in pairs(_lv0) do _empty = false end
            ck("★★ ⑳ 桩环境无 GetProfessions → ProfLearned 空表（不炸、全按未学）", _empty)

            local _savedGP, _savedGPI = GetProfessions, GetProfessionInfo
            GetProfessionInfo = function(id)
              if id == 20250 then return "制皮", 134400, 45, 75, 0, 0, 165 end
              if id == 20251 then return "急救", 136243, 88, 300, 0, 0, 129 end
              return nil
            end
            GetProfessions = function() return nil, nil, nil, nil, 20250, 20251 end

            local _lv = PD.ProfLearned()
            ck("★★ ⑳ ProfLearned 读到 制皮 45/75（skillLine 第 7 返回值 → slug）",
               _lv.leatherworking ~= nil and _lv.leatherworking.cur == 45
               and _lv.leatherworking.max == 75,
               _lv.leatherworking
               and (_lv.leatherworking.cur .. "/" .. _lv.leatherworking.max) or "nil")
            ck("★ ⑳ 急救 88/300 也在（first-aid 短横 slug 不写错）",
               _lv["first-aid"] ~= nil and _lv["first-aid"].cur == 88
               and _lv["first-aid"].max == 300)

            PD.Show("alchemy")
            PD.SetTab("overview")
            local _lw = PD.navKey and PD.navKey.leatherworking
            local _fa = PD.navKey and PD.navKey["first-aid"]
            local _ck = PD.navKey and PD.navKey.cooking
            ck("★ ⑳ 导航按钮经 navKey 可取（制皮/急救/烹饪）",
               _lw ~= nil and _fa ~= nil and _ck ~= nil)
            if _lw and _fa and _ck then
              local a = ns.hui and ns.hui.ACCENT
              local er = a and a[1] or 0x46 / 255
              local eb = a and a[3] or 0x72 / 255
              local ntc = _lw:GetFontString() and _lw:GetFontString().__textColor
              ck("★★ ⑳ 已学（制皮）右侧出现「45/75」小字",
                 _lw.__lv ~= nil and _lw.__lv.__shown == true and _lw.__lv.__text == "45/75",
                 _lw.__lv and tostring(_lw.__lv.__text) or "nil")
              ck("★★ ⑳ 已学（制皮）名字走主题绿（= ns.hui.ACCENT，切主题即跟随）",
                 ntc ~= nil and math.abs(ntc[1] - er) < 1e-6 and math.abs(ntc[3] - eb) < 1e-6,
                 ntc and tostring(ntc[1]) or "nil")
              ck("★ ⑳ 已学（急救）小字 = 88/300（各读各的，不串位）",
                 _fa.__lv ~= nil and _fa.__lv.__shown == true and _fa.__lv.__text == "88/300",
                 _fa.__lv and tostring(_fa.__lv.__text) or "nil")
              local ctc = _ck:GetFontString() and _ck:GetFontString().__textColor
              ck("★★ ⑳ 未学（烹饪）维持灰显、不出小字（颜色 != 主题绿，相对断言）",
                 (_ck.__lv == nil or _ck.__lv.__shown ~= true)
                 and ctc ~= nil
                 and (math.abs(ctc[1] - er) > 1e-3 or math.abs(ctc[3] - eb) > 1e-3),
                 ctc and tostring(ctc[1]) or "nil")
            end

            -- 收尾：摘桩重画 → 灰显复位（导航不残留绿字 / 旧小字）
            GetProfessions, GetProfessionInfo = _savedGP, _savedGPI
            PD.PickNav()
            local _lw2 = PD.navKey and PD.navKey.leatherworking
            ck("★★ ⑳ 摘桩重画 → 已学小字隐藏、导航复位（不残留绿）",
               _lw2 ~= nil and _lw2.__lv ~= nil and _lw2.__lv.__shown ~= true,
               _lw2 and _lw2.__lv and tostring(_lw2.__lv.__shown) or "nil")
          end

          -- ---------- ㉑ 已过段落灰显（2026-09-29 用户定：制皮 42 → 「1 – 15」整段灰）----------
          -- 桩掉 ProfLearned（当前技能 42）重渲升级页：passed 落 spec 的段落数与上限、
          -- 帧级区间字真灰（r.a.__textColor 明度 < 0.5）、未过段不灰（复位分支生效）。
          do
            local _savedPL = PD.ProfLearned
            PD.ProfLearned = function()
              return { leatherworking = { cur = 42, max = 75 } }
            end
            PD.Show("leatherworking")
            PD.SetTab("leveling")
            local _np, _okN, _badHi = 0, true, nil
            for _, sp in ipairs(PD.specs or {}) do
              if sp.lvstep and sp.passed then
                _np = _np + 1
                local hi = tonumber(sp.rng and sp.rng:match("–%s*(%d+)"))
                if not hi then _okN = false
                elseif hi >= 42 then _badHi = hi end
              end
            end
            ck("★★ ㉑ 制皮 42：已过段落 >= 1 段（passed 落 spec）", _np >= 1, _np)
            ck("★ ㉑ passed 段落上限全部 < 42（判定没写反）", _okN and _badHi == nil,
               tostring(_badHi))
            local _dimRng, _litRng = 0, 0
            for _, fr in ipairs(PD.rows or {}) do
              if fr.__shown ~= false and fr.a and fr.a.__text
                 and fr.a.__text:find("–", 1, true) then
                local c = fr.a.__textColor
                local hi = c and tonumber(fr.a.__text:match("–%s*(%d+)"))
                if hi and hi < 42 then
                  if c[1] < 0.75 then _dimRng = _dimRng + 1 end   -- C_DIM 0.63 < 0.75 < C_TEXT 0.88
                elseif hi then
                  if c[1] > 0.75 then _litRng = _litRng + 1 end
                end
              end
            end
            ck("★★ ㉑ 已过段的区间字真的灰了（帧级颜色）", _dimRng >= 1, _dimRng)
            ck("★ ㉑ 未过段的区间字不灰（复位分支生效）", _litRng >= 1, _litRng)
            -- 收尾：摘桩重渲，灰显全部退掉（行池复用不残留灰）
            PD.ProfLearned = _savedPL
            PD.Show("leatherworking")
            PD.SetTab("leveling")
            local _np2 = 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.lvstep and sp.passed then _np2 = _np2 + 1 end
            end
            ck("★★ ㉑ 摘桩重渲 → passed 清零（桩环境无 GetProfessions = 全未学）", _np2 == 0, _np2)
          end

          -- ---------- ㉒ 专业页设置 + 当前段落外框（2026-09-29 用户定）----------
          -- 齿轮开设置页（两行开关、点行切换落 DungeonsForeverDB.prof）；当前段 =
          -- 第一个未过分段（over 判定，与灰显开关解耦），行框四条 1px 色条亮出。
          do
            local _savedPL3 = PD.ProfLearned
            PD.ProfLearned = function()
              return { leatherworking = { cur = 42, max = 75 } }
            end
            -- ㉒A 齿轮开设置页
            PD.setOpen = true
            PD.Render()
            local _nrow = 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.kind == "row" then _nrow = _nrow + 1 end
            end
            ck("★★ ㉒ 设置页恰好两行开关", _nrow == 2, _nrow)
            ck("★ ㉒ 齿轮入口已建", PD.setGear ~= nil)
            -- ㉒A' iOS 开关池：greyPassed 的开关已摆到行右缘、绑对键、随设置值勾选
            local _tg1
            for _, tg in ipairs(PD.setToggles or {}) do
              if tg.__key == "greyPassed" then _tg1 = tg break end
            end
            ck("★★ ㉒ iOS 开关摆位且绑定 greyPassed（行右缘、可见）",
               _tg1 ~= nil and _tg1.__shown == true)
            if _tg1 then
              local _before = PD.Setting("greyPassed")
              _tg1.__scripts.OnClick(_tg1)
              ck("★★ ㉒ 点开关 greyPassed 翻转并落 DungeonsForeverDB.prof",
                 PD.Setting("greyPassed") ~= _before
                 and DungeonsForeverDB ~= nil and DungeonsForeverDB.prof ~= nil
                 and DungeonsForeverDB.prof.greyPassed ~= nil,
                 tostring(PD.Setting("greyPassed")))
              -- ㉒B 灰显关掉：passed 全清；当前段（hlCurrent 默认开）照常落在 15–58
              PD.Show("leatherworking")
              PD.SetTab("leveling")
              local _np3, _ncur, _curHi = 0, 0, nil
              for _, sp in ipairs(PD.specs or {}) do
                if sp.lvstep then
                  if sp.passed then _np3 = _np3 + 1 end
                  if sp.cur then
                    _ncur = _ncur + 1
                    _curHi = tonumber(sp.rng and sp.rng:match("–%s*(%d+)"))
                  end
                end
              end
              ck("★★ ㉒ 灰显关掉 → passed 全清", _np3 == 0, _np3)
              ck("★★ ㉒ 当前段唯一且上限 58（= 42 的下一格 15–58）",
                 _ncur == 1 and _curHi == 58, tostring(_curHi))
              local _frB = 0
              for _, fr in ipairs(PD.rows or {}) do
                if fr.__shown ~= false and fr.bT and fr.bT.__shown then _frB = _frB + 1 end
              end
              ck("★★ ㉒ 当前段行框亮出（bT 可见且只此一行）", _frB == 1, _frB)
              -- ㉒C 关掉 hlCurrent → cur 清零、行框全收
              DungeonsForeverDB.prof.hlCurrent = false
              PD.Render()
              local _ncur2, _frB2 = 0, 0
              for _, sp in ipairs(PD.specs or {}) do
                if sp.lvstep and sp.cur then _ncur2 = _ncur2 + 1 end
              end
              for _, fr in ipairs(PD.rows or {}) do
                if fr.__shown ~= false and fr.bT and fr.bT.__shown then _frB2 = _frB2 + 1 end
              end
              ck("★★ ㉒ 高亮关掉 → cur 清零、行框全收（不残留）",
                 _ncur2 == 0 and _frB2 == 0, _ncur2 .. "/" .. _frB2)
              -- 收尾：恢复默认（删键回落 SETTING_DEF）、摘桩、离开设置页
              DungeonsForeverDB.prof.greyPassed = nil
              DungeonsForeverDB.prof.hlCurrent = nil
              PD.ProfLearned = _savedPL3
              PD.Show("leatherworking")
              PD.SetTab("overview")
              local _tgShown = 0
              for _, tg in ipairs(PD.setToggles or {}) do
                if tg.__shown then _tgShown = _tgShown + 1 end
              end
              ck("★★ ㉒ 离开设置页 → iOS 开关全收（不残留）", _tgShown == 0, _tgShown)
              ck("★ ㉒ 收尾：开关键删净回落默认（全开）",
                 DungeonsForeverDB.prof.greyPassed == nil
                 and DungeonsForeverDB.prof.hlCurrent == nil
                 and PD.Setting("greyPassed") == true and PD.Setting("hlCurrent") == true)
            end
          end

"""
text = text.replace(NAVSUB_DYN_ANCHOR, NAVSUB_DYN_EXTRA + NAVSUB_DYN_ANCHOR, 1)
print('  %-30s → %d 处' % ('⑳ 已学专业导航动态断言', 6))


# ── ㉑ 关于页静态断言（2026-09-24 用户定：标题栏「?」→ 主窗口内切换，非弹窗）──────
#    关于页在 Core/MainFrame.lua（手写件），不在 DungeonUI 生成物里 → 模块级独立读文件。
#    ⚠️ 必须插在 __main__ 守卫**之前**（模块级执行；append 到文件尾会落在 main() 调用后，
#    脚本方式运行时整块被跳过且不报错 —— 2026-09-24 实测踩过）。
ABOUT_STATIC_EXTRA = r'''
# ---- ㉑ 关于页（Core/MainFrame.lua，手写件）----
_about_src = open(os.path.join(ADDON, 'Core', 'MainFrame.lua'), encoding='utf-8',
                  errors='replace').read().replace('\r\n', '\n')
ck('★★ ㉑ 关于页入口「?」（关闭钮左侧同规格：-40 偏移 / 层级 510 / 点击切换）',
   'aboutBtn:SetPoint("TOPRIGHT", f, "TOPRIGHT", -40, -4)' in _about_src
   and 'aboutBtn:SetFrameLevel(510)' in _about_src
   and 'about:SetShown(not about:IsShown())' in _about_src)
ck('★★ ㉑ 关于页 = 主窗口内覆盖层（SetAllPoints 盖全窗 / 层级 505 内容上按钮下 / 点击任意处关闭）',
   'about:SetAllPoints(f)' in _about_src
   and 'about:SetFrameLevel(505)' in _about_src
   and 'about:EnableMouse(true)' in _about_src
   and 'about:SetScript("OnMouseUp"' in _about_src)
ck('★★ ㉑ 关于页文案钉死（作者圆圆 / 鸣谢黑科研·胡里胡涂 / 黑科研研究所 / 版本号走 GetAddOnMetadata 不写死）',
   '"圆圆"' in _about_src
   and '"黑科研 · 胡里胡涂"' in _about_src
   and '"黑科研研究所"' in _about_src
   and 'GetAddOnMetadata("DungeonsForever", "Version")' in _about_src)
ck('★★ ㉑ 关于页署名口径（仅「数据来源：wowhead」一条）+ 重开窗口自动退回手册页',
   '"数据来源：wowhead"' in _about_src
   and 'f:HookScript("OnShow"' in _about_src)
'''
ABOUT_MAIN_GUARD = "if __name__ == '__main__':"
if text.count(ABOUT_MAIN_GUARD) != 1:
    sys.exit('未找到 __main__ 守卫锚点（㉑关于页静态断言无法定位插入点）')
text = text.replace(ABOUT_MAIN_GUARD, ABOUT_STATIC_EXTRA + '\n\n' + ABOUT_MAIN_GUARD, 1)
print('  %-30s → %d 处' % ('㉑关于页静态断言', 4))


# 残留自检：活代码里不得再出现上游身份
for kw in ('TalentsForever/', 'TalentsForever.toc', 'Core/UI.lua',
           PLACEHOLDER, 'TF_NS.TalentSimUI'):
    if kw in text:
        bad = [l for l in text.split('\n') if kw in l][:3]
        sys.exit('残留 %s：\n  %s' % (kw, '\n  '.join(bad)))

# ★★ 覆盖防护（2026-10-11 实锤）：本生成器从**上游 TalentsForever** 派生，而产品
#   `df_dungeon_check.py` 已经被本仓多轮增量手改（断言数远超上游）。直接重跑会
#   **静默把那些断言整片抹掉**，还会因上游结构漂移产出跑不起来的文件
#   （实测：生成物里 ADDON 变量定义被吃掉 → `NameError: name 'ADDON' is not defined`）。
#   故：产物已存在时拒绝覆盖，必须显式设 DF_CHECK_ALLOW_REGEN=1。
#   ★ 例行做法不是重跑生成器，而是**直接手改 df_dungeon_check.py**（并在 mk 侧同步一份，
#     仅作留档），改完 `python df_dungeon_check.py` 验证。
if os.path.exists(DST) and os.environ.get('DF_CHECK_ALLOW_REGEN') != '1':
    sys.exit(
        '拒绝覆盖已存在的 %s。\n'
        '  本生成器源自上游 TalentsForever，滞后于本仓手改后的产物；直接重跑会静默\n'
        '  抹掉本仓新增断言（甚至产出跑不起来的文件 —— 2026-10-11 实测 ADDON 定义被吃）。\n'
        '  · 要改断言 → 直接编辑 df_dungeon_check.py，勿重跑本脚本；\n'
        '  · 确实要重跑 → 先备份，再设 DF_CHECK_ALLOW_REGEN=1 并事后 diff 找回手改。' % DST)
open(DST, 'w', encoding='utf-8', newline='\n').write(text)
print('已生成 %s（%d 行）' % (DST, text.count('\n') + 1))

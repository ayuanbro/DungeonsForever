# -*- coding: utf-8 -*-
"""副本页回归检查（上游 TalentsForever 的 tf_chain_check / tf_load_check 都**不覆盖**副本页）。

为什么必须单独立一个 harness：
  2026-09-22 实机点副本卡即 **硬闪退**（ERROR #132 / ACCESS_VIOLATION，RCX=0 读 [rcx+0x128]），
  根因是滚动容器 ScrollFrame 的 **scroll child 被整块换掉**：旧 child 先 `SetParent(nil)` 解挂、
  再 CreateFrame 一个新的 `SetScrollChild` 回去 —— ScrollFrame 内部一直持有旧 child 指针，
  指向一个「没有父帧的帧」，客户端下一次布局/渲染就摔。离线桩**永远复现不出**这个崩溃
  （桩的 SetParent / SetScrollChild 都是空实现），所以只能把「不变量」钉成断言来守：

    ① 反复刷新（升级 / 反复切等级）后，`U.dungeonListChild` 必须是**同一个 Lua 对象**；
    ② 反复开详情后，`U.dungeonDetailChild` 必须是同一个对象；
    ③ 上述路径全部 **零新建帧**（池化复用，CreateFrame 计数 == 0）；
    ④ 静态扫描：副本模块的**活代码**里不得出现 `SetParent(nil)`。

用法：`python tf_dungeon_check.py`（用 BGLite 的 venv，含 lupa）
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

# 与其它 harness 保持一致：断的是已同步的 beta/forever 副本
ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')
CLIENT_BUILD = int(os.environ.get('TF_BUILD', '16001'))

FAILED = []
PASSED = []


def ck(name, ok, extra=None):
    (PASSED if ok else FAILED).append(name)
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           '' if extra is None else '  [%s]' % extra))
    return ok


def section(t):
    print('=' * 72)
    print(t)
    print('=' * 72)


# ---------------------------------------------------------------------------
# 静态守卫：活代码里不得有 SetParent(nil)
# ---------------------------------------------------------------------------
def static_guard():
    section('静态守卫：副本模块活代码中的 SetParent 调用')
    src = open(os.path.join(ADDON, 'Core', 'DungeonUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
    live = []
    for i, line in enumerate(src.split('\n'), 1):
        code = line.split('--')[0]                     # 粗暴去行注释（本文件无 `--` 字符串）
        if 'SetParent(' in code:
            live.append((i, code.strip()))
    for i, code in live:
        print('    %s:%d  %s' % ('Core/DungeonUI.lua', i, code))
    # 命中只可能是 HUD 类辅助帧；对 scroll child 调 SetParent(nil) 才是致命的
    bad = [x for x in live if 'nil' in x[1]]
    ck('活代码无 SetParent(nil)', not bad, bad if bad else 'clean')
    # 更进一步：副本模块所在的整段（DG 表 → ShowDungeonDetail 结束）不得有任何 SetParent
    seg = src[src.index('local DG = {}'):src.index('function U:ShowDungeonDetail(d)')]
    seg_live = [l for l in seg.split('\n') if 'SetParent(' in l.split('--')[0]]
    ck('副本模块整段无任何 SetParent 调用', not seg_live, seg_live[:3])

    # ---- 掉落物品鼠标提示的活代码不变量 ----
    # 用户诉求：悬停某件装备要能直接看到「这件装备是干什么的 / 有什么数值」。
    # 桩记不到 EnableMouse（桩的 __index 不登记它），所以这一条只能静态守。
    ck('物品行开了鼠标（r:EnableMouse(true)）', 'r:EnableMouse(true)' in src)
    ck('物品行挂了 OnEnter 与 OnLeave',
       'r:SetScript("OnEnter"' in src and 'r:SetScript("OnLeave"' in src)
    # ★ SetHyperlink 必须包在 pcall 里：客户端不认识的 itemID 在部分端上会直接抛错，
    #   不包的话整个 OnEnter 被掀掉 → 用户看到的就是「完全没有鼠标提示」（实测症状）。
    # 起点从 `function DG.NsCall` 起：站点兜底函数 DG.TipOf 已删除（站点物品资料整体弃用）
    tipseg = src[src.index('function DG.NsCall'):src.index('function U:SetDungeonFilter')]
    # ★ 断言必须打在**代码**上：注释里也写了这些 API 名（解释为什么不能这么做），
    #   不剥注释的话「删掉代码、留下注释」照样全绿 —— 断言等于白测。
    tipcode = '\n'.join(l.split('--')[0] for l in tipseg.split('\n'))
    ck('★ SetHyperlink 用 pcall 包住（否则不认识的 itemID 会掀掉整个 OnEnter）',
       'pcall(GameTooltip.SetHyperlink' in tipcode)
    # ★★ 核心不变量：客户端物品数据是**懒加载**的，GetItemInfo 首次回 nil 只表示
    #    「还没拉下来」，不代表客户端没有这件物品。拿它当原生分支的门槛 → 所有未预热的
    #    物品一律被误判成「客户端不认识」→ 用户明明在游戏里却只看到站点数据（实测症状）。
    # 收紧到「整条路都不许碰」：懒加载未命中 ≠ 客户端不认识，任何以其结果为门控的
    # 写法都会把未预热的物品误判成「客户端没有」。GetItemInfo 只允许出现在取图标那条路
    # （DG.ItemIcon，在 tipseg 之外，那边命中不了才回退站点图标名）。
    # 只禁「拿它的结果当门控」的写法。老端兼容分支里允许调一次 GetItemInfo 去触发
    # 按需拉取（那正是它唯一的正当用途：调用即请求），但绝不能由它决定走不走原生。
    ck('★★ 原生分支不被 GetItemInfo 的结果门控（懒加载未命中 ≠ 客户端不认识）',
       'local known' not in tipcode
       and 'known = GetItemInfo' not in tipcode
       and 'GetItemInfo(id) == nil' not in tipcode
       and 'GetItemInfo(id) then' not in tipcode)
    ck('★ 客户端拿不出内容时主动催它加载（C_Item.RequestLoadItemDataByID）',
       'C_Item.RequestLoadItemDataByID' in tipcode)
    # ★ 只查「代码里提到过这个事件名」太弱：把 RegisterEvent 摘掉、只留一个同名字符串
    #   照样能骗过断言（变异验证实测抓到过）。必须钉住「真的注册了」+「帧存进 DG.__itemEvt」
    #   （那是到货重刷唯一的入口，丢了它事件到了也没人接）。
    ck('★ 物品数据到货后自动重刷提示框（RegisterEvent + OnEvent + __itemEvt 齐备）',
       'RegisterEvent("GET_ITEM_INFO_RECEIVED")' in tipcode
       and 'DG.EnsureItemListener' in tipcode
       and 'DG.__itemEvt = ev' in tipcode
       and '"OnEvent"' in tipcode,
       'reg=%s evt=%s' % ('RegisterEvent("GET_ITEM_INFO_RECEIVED")' in tipcode,
                          'DG.__itemEvt = ev' in tipcode))
    # ★★ 2026-09-22 用户决定：站点物品资料整体弃用（口径不准）→ 兜底也只给
    #    「客户端拿得到的名字 + 一句实话」，不再有站点逐行文本。
    ck('★★ 提示框不再引用站点提示数据（无 ns.DungeonTips / DG.TipOf）',
       'DungeonTips' not in tipcode and 'DG.TipOf' not in tipcode)
    ck('★ 原生链接拿不到内容时的判据仍是 NumLines（只 1 行 = 数据未到货）',
       'NumLines' in tipcode)
    seg_detail = src[src.index('function U:ShowDungeonDetail'):src.index('function U:RenderDungeonLoot')]
    ck('★ 打开详情预热本副本全部掉落（悬停时直接出原生属性）',
       'DG.PrewarmLoot(d)' in '\n'.join(l.split('--')[0] for l in seg_detail.split('\n')))
    ck('★ 到货时把已渲染的卡片文字改成客户端口径',
       'c.name:SetTextColor(DG.QColor(DG.QualOf(itemID)))' in tipcode)
    # 名字 / 品质 / 图标 / 部位都是客户端物品数据，到货就一起刷 —— 别只刷颜色
    ck('★ 到货重刷名字 / 图标 / 部位（同源同刷）',
       'c.name:SetText(nm)' in tipcode
       and 'c.icon:SetTexture(DG.ItemIcon(itemID))' in tipcode
       and 'c.tp:SetText(DG.ItemMeta(itemID))' in tipcode)
    ck('★★ 到货重刷抽成 DG.RefreshItemCards（事件与官方异步回调共用一个入口）',
       'function DG.RefreshItemCards(itemID)' in tipcode
       and 'DG.RefreshItemCards(itemID)' in tipcode)
    # ★★ 2026-09-22 第二轮（用户原话）：标出站点出处「搞得好像我这些数据都是从网站上
    #    拷下来的」→ 提示框上连「站点」二字都不许有；掉率只在卡片上给纯数字（DG.Pct）。
    ck('★★ 提示框活代码不出现「站点」/「掉率」字样',
       '站点' not in tipcode and '掉率' not in tipcode)
    marca = src[src.index('function DG.MarkNPC'):src.index('function DG.ShowNpcTip')]
    marcacode = '\n'.join(l.split('--')[0] for l in marca.split('\n'))
    ck('★ 地图标记有端号门禁（非无限端不静默失败，明确提示）',
       'GetBuildInfo()' in marcacode and '16999' in marcacode
       and '地图标记仅无限客户端支持' in marcacode)

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
    ck('★★ 胶囊行上移量 DG.CAPSULE_LIFT = 20（轨道底=面板顶，卡顶↔轨道底缝 8）',
       re.search(r'DG\.CAPSULE_LIFT\s*=\s*20\b', src) is not None)
    ck('★ 胶囊 host 的 y 偏移 = DG.CAPSULE_LIFT - ROW_SUB（上移没被改回 -ROW_SUB）',
       'host:SetPoint("TOP", U.panel, "TOP", 0, DG.CAPSULE_LIFT - ROW_SUB)' in src)
    # ★ 2026-09-25 起是**五颗**（无限服：5人本/团本/专业/探索/BIS配装）/ 两颗（泰坦），
    #   各颗一律取同一个 DG.CAPSULE_W —— 分段控件的滑块宽度按按钮宽取，
    #   只要有一颗用了别的宽就会跳形。
    ck('★ 各颗胶囊等宽（分段控件滑块宽度按按钮宽取，不等宽会跳形）',
       'DG.CAPSULE_W = 82' in src and src.count('width = DG.CAPSULE_W') == 10)
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
    # ★ 2026-10-09 起页面架构 = **EnsureBuilt 懒构建**（壳帧在 Build 建、内容首切才建，
    #   U.subBuilt[k] 幂等闸；首屏不再整包建帧）。断言随架构改写：
    #   壳帧仍须在 Build；内容构建必须走 EnsureBuilt（三查：闸 + Build 调用 + 幂等标记）。
    _ebi = src.index('function U:EnsureBuilt')
    _eb = src[_ebi:src.index('function U:', _ebi + 10)]
    ck('★ 团本页壳帧在 Build 建、内容走 EnsureBuilt 懒构建（U.subBuilt 幂等闸）',
       'U.raidPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'if k == "Raids" and ns.RaidModule and U.raidPage then' in _eb
       and 'ns.RaidModule.Build(U.raidPage)' in _eb
       and 'U.subBuilt[k] = true' in _eb)
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
    ck('★★ RaidUI 单列表页（时间线退役、页签行整个退役）',
       'L["时间线"]' not in _ra
       and 'RU.SetTab' not in _ra
       and 'function RU.Render()' in _ra
       and 'RU.RenderList()' in _ra)
    ck('★★ RaidUI 套装页整体休眠（代码留存、不构建不渲染，入口后期再接）',
       'function RU.BuildSets(page)' in _ra
       and '    RU.BuildSets(page)\n' not in _ra
       and 'function RU.RenderSets()' in _ra)
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
    ck('★★ 卡片日期与分组注记共用地区日期口径（RecDateText / FirstOpenText）',
       'local function RecDateText(rec)' in _ra
       and 'c.date:SetText(RecDateText(rec))' in _ra
       and 'note = RU.FirstOpenText() .. " · " .. L["同日开启"]' in _ra)
    ck('★★ RaidUI 倒计时不给秒（格式串只有 天/小时/分）',
       '距首批开放还有 %d 天 %d 小时 %d 分' in _ra and '%d 秒' not in _ra)
    ck('★★ 「国服待确定」注记挂 禁止 GDKP 行描述右侧',
       'L["国服待确定"]' in _ra
       and 'RU.cnNote:SetPoint("LEFT", gdkpDesc, "RIGHT", 14, 0)' in _ra)
    ck('★★ RaidUI 界面层不定义裸全局函数（函数一律挂 local 表 RU）',
       not re.search(r'^function\s+[A-Za-z_][A-Za-z0-9_]*\s*\(', _ra, re.M))

    # ★★ 卡墙几何（2026-09-29 修）：RenderList 原先在**逐卡循环体内**推进 y，
    #    首档 3 张大卡就被排成斜梯（x 增、y 也增），第 3 张已落到规则块上；
    #    桩的 SetPoint 不记偏移 -> 离线全绿也漏。现改成一次性算好落点（纯几何），
    #    这里钉住「落点来自 RU.LayoutCards，且逐卡循环里不再动 y」。
    ck('★★ RaidUI 卡宽按可用宽反算（左右内衬对称，余数摊进列宽；高 145 = 五人本卡 2.5 倍）一行 2 张',
       'RU.LS_COLS = 2' in _ra
       and 'RU.LS_COL_W = math.floor((RU.W - 2 * RU.GRID_PAD - (RU.LS_COLS - 1) * RU.LS_GAP) / RU.LS_COLS)' in _ra
       and 'c:SetPoint("TOPLEFT", child, "TOPLEFT", pos[i].x, pos[i].y)' in _ra)
    ck('★★ RaidUI 逐卡循环里不得再推进 y（否则卡排成斜梯）',
       re.search(r'RU\.PaintCard\(c, rec\)\s*\n\s*y = y \+', _ra) is None
       and 'y = pos.bottom + RU.LS_LABEL_H' in _ra)

    # ── 团本详情入口（2026-10-11 二稿：详情复用五人本整套，点卡跳转）──
    ck('★★ 团本列表页：头部四件套全删 + 几何对齐五人本定案（2026-10-12 用户）',
       'RU.TITLE_Y = ' not in _ra
       and 'RU.NOTE_Y = ' not in _ra
       and 'RU.BODY_Y = ' not in _ra
       and 'RU.SyncHeader' not in _ra
       and 'local function UpdateCD' not in _ra
       and 'RU.CARD_TOP = 8' in _ra
       and 'RU.LIST_Y = 16' in _ra
       and 'RU.CARD_BOTTOM = PAGE_INSET' in _ra
       and 'card:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -RU.X, RU.CARD_BOTTOM)' in _ra
       and ', -12)' not in _ra
       and 'scroll:SetPoint("TOPLEFT", page, "TOPLEFT", RU.X + RU.GRID_PAD, -RU.LIST_Y)' in _ra
       and 'scroll:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -(RU.X + RU.GRID_PAD), RU.CARD_BOTTOM)' in _ra
       and 'RU.listFades = { mask }' in _ra)
    ck('★★ RaidUI 详情 = 跳转复用五人本（SwitchSub Dungeons + ShowDungeonDetail）',
       'RU.DETAILS[self.rec.name]' in _ra
       and 'c.rec = rec' in _ra
       and 'function RU.DungeonRec(name)' in _ra
       and 'MJ:SwitchSub("Dungeons")' in _ra
       and 'MJ:SetDungeonView("list")' in _ra
       and 'MJ:ShowDungeonDetail(rec)' in _ra)
    ck('★★ 跳转后胶囊归位团本 + 返回键按来源分流（2026-10-12 用户：详情里胶囊不能停在 5 人本）',
       'if MJ.SetSubCapsule then MJ:SetSubCapsule("Raids") end' in _ra
       and 'function U:SetSubCapsule(key)' in src
       and 'if U.subCtrl and selected then U.subCtrl:SetSelected(tab.button, true) end' in src
       and 'SetSelected(tab.button, selected)' not in src
       and 'U.dungeonDetailCur and U.dungeonDetailCur.raid and U.SwitchSub' in src
       and 'U.dungeonBack:SetText(d.raid and L["‹ 团本"] or L["‹ 副本"])' in src
       and 'and U.dungeonDetail:IsShown() then' in src)
    ck('★★ RaidUI 列表卡带原画（奥巢=客户端加载图 TGA，art L2 + 压暗 L3）',
       'c.art = c:CreateTexture(nil, "BACKGROUND", nil, 2)' in _ra
       and 'c.dim:SetColorTexture(0, 0, 0, 0.38)' in _ra
       and 'ns.DungeonUI.CardArtFor({ id = det.id })' in _ra
       and 'c.bg:SetAlpha(0)' in _ra)
    ck('★★ RaidUI 列表卡 UI 规则合规（强调条全删 + 满幅原画卡圆角描边 + 悬停描边换白 + 分组语义边）',
       'c.bar' not in _ra
       and 'c.hint' not in _ra
       and 'c.edge' not in _ra
       and 'SetHover' not in _ra
       and 'ns.hui.BuildRoundedBG(c, 6, layer.L2, "both", false)' in _ra
       and 'ns.hui.BuildRoundBorder(c, 6, ns.hui.CARD_BORDER, c, "OVERLAY", "both", 1)' in _ra
       and 'ns.hui.RoundIcon(c.art)' in _ra
       and 'CardEdge(self, 1, 1, 1, 0.9)' in _ra
       and 'c:IsMouseOver()' in _ra
       and 'RU.PaintCard(RU.cards[ci], rec, g.edge, g.ea)' in _ra
       and 'edge = C_GOLD, ea = 0.70' in _ra
       and 'edge = { 0.60, 0.63, 0.68 }, ea = 0.30' in _ra)
    ck('★★ 团本掉落卡片视图 = 整宽 boss 卡 + 卡内物品 4 列（2026-10-11 用户：单 boss 掉落多，不许单列）',
       'raid = true,' in _ra
       and 'local raidWide = (d.raid == true) and not bossMode and U.dungeonLootBoss ~= DG.LOOT_TRASH' in src
       and 'if raidWide and n > 0 then visRows = math.ceil(n / wideCols) end' in src
       and 'rx = rx + (cc - 1) * (rowW + DG.LOOT_GAP_X)' in src
       and 'ry = cy - DG.LOOT_CARD_HDR_H - rr * wideStepY' in src
       and 'cols = 1' in src)
    _mu = open(os.path.join(ADDON, 'Core', 'MapUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
    ck('★★ 奥巢地图 = 客户端 OnyxiasLair 单层 12 块（区域图目录名不得混入）',
       'onyxias_lair          = { "OnyxiasLair", { "OnyxiasLair1_" } }' in _mu
       and 'OnyxiasLair' in _mu)
    ck('★★ 地图页顶部工具栏卡：卡高 + 间距 + 地图高 == 可用高（尺寸解耦）',
       'M.MAP_H = M.FRAME_H - M.HDR_CARD_H - M.HDR_GAP' in _mu
       and 'M.MAP_W = math.floor(M.MAP_H * M.ART_W / M.ART_H)' in _mu)
    ck('★★ 奥巢 hero/卡面美术 = 插件自带 TGA（ArtOf 先查 MEDIA 表再走客户端 FDID）',
       'local MEDIA_HERO = {' in src
       and 'local MEDIA_WIDE = {' in src
       and 'mpath = wide and MEDIA_WIDE[d.id] or MEDIA_HERO[d.id]' in src
       and 'function DG.CardArtFor(d)' in src
       and 'U.CardArtFor = DG.CardArtFor' in src)
    ck('★★ RaidUI 滚动列表行级剔除（无裁剪引擎：子元素全部登记 cullables）',
       'function RU.CullCards()' in _ra
       and 'local function CullAdd(f, yTop, yBot, card)' in _ra
       and 'RU.cullables = {}, {}, {}, {}' in _ra
       and 'e.f:SetShown(ok and e.card.__shown)' in _ra)

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
    ck('★ 探索页壳帧在 Build 建、内容走 EnsureBuilt 懒构建（2026-10-09 架构）',
       'U.explorePage = CreateFrame("Frame", nil, panel)' in _bld
       and 'ns.ExploreModule.Build(U.explorePage)' in _eb)

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
    ck('★★ Ctrl+点击（Shift 未按）→ 试衣间试穿（DressUpItemLink）',
       'IsControlKeyDown()' in clickcode and 'DG.TryOn(' in clickcode)
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
    am_src = open(os.path.join(ADDON, 'Core', 'Data', 'Data_AreaMap.lua'), encoding='utf-8',
                  errors='replace').read().replace('\r\n', '\n')
    gearui = open(os.path.join(ADDON, 'Core', 'GearUI.lua'), encoding='utf-8',
                  errors='replace').read().replace('\r\n', '\n')
    geardata = open(os.path.join(ADDON, 'Core', 'Data', 'Data_Gear.lua'), encoding='utf-8',
                  errors='replace').read().replace('\r\n', '\n')
    bisui = open(os.path.join(ADDON, 'Core', 'BisUI.lua'), encoding='utf-8',
                 errors='replace').read().replace('\r\n', '\n')
    ck('★★ BIS 附魔列表全显但灰显超档（2026-10-15 用户：根据装备过滤器等级显示）',
       'local function EnchCap(lvOverride)' in bisui
       and 'if BG.onlyUsable then return tonumber(BG.filterLv) or 60 end' in bisui
       and 'local function EnchRowsFor(sp, dk)' in bisui
       and 'local cap = EnchCap(nil)' in bisui
       and 'local over = cap and e.req and e.req > cap' in bisui
       and 'r.note:SetTextColor(Unpack(over and C_DIM or C_TEXT))' in bisui
       and 'r.name:SetTextColor(Unpack(over and not sel and C_DIM or (sel and C_GOLD or C_TEXT)))' in bisui
       and 'local cap = EnchCap(lvOverride)' in bisui
       and 'if not (cap and e.req and e.req > cap)' in bisui)
    ck('★★ BIS 目标等级空 ⇒ 面板按 60 级显示；「当前」按钮填入玩家当前等级',
       'local lv = BG.onlyUsable and (BG.filterLv or 60) or nil' in bisui
       and 'local lv = BG.filterLv or 60' not in bisui
       and 'local lv = AutoLevel()' in bisui
       and 'local lv = PlayerLevel() or 60' in bisui
       and 'ApplyLvText(tostring(lv))' in bisui
       and 'if BG.onlyUsable then return tonumber(BG.filterLv) or 60 end' in bisui)
    ck('★★ BIS 备选装备池上限 = 过滤目标等级（与预设方案卷等级解耦）',
       'local function CatRowsFor(rkey)' in bisui
       and 'local cap = (BG.onlyUsable and tonumber(BG.filterLv)) or 60' in bisui
       and 'and (r.req or 0) <= cap then' in bisui
       and 'local lv = CurVol().lv' not in bisui)
    ck('★★ BIS 进页优先玩家职业；会话内选过则保持；重登/reload 复位',
       'local function PlayerClassSlug()' in bisui
       and 'local ok, _, file = pcall(UnitClass, "player")' in bisui
       and 'BG.cls = PlayerClassSlug() or "warrior"' in bisui
       and 'BG.__clsPicked = true' in bisui
       and 'if not BG.__clsPicked then' in bisui
       and 'if slug and slug ~= BG.cls then' in bisui)
    ck('★★ BIS 预设方案：类型只有一份配装（三系共用）⇒ 只写类型名、对所有天赋可见',
       'local cnt = {}' in bisui
       and 'cnt[sp.id] = (cnt[sp.id] or 0) + 1' in bisui
       and 'if (cnt[sp.id] or 0) <= 1 or sp.tspec == nil or sp.tspec == tsp then' in bisui
       and 'local solo = (cnt[sp.id] or 0) <= 1' in bisui
       and 'if solo then lab, ts = nil, nil end' in bisui
       and 'talent = lab, side = sd }' in bisui
       and 'solo and nil or sp.label' not in bisui)
    ck('★★ BIS 来源过滤器新增「商人」：从「其他」拆出，老存档迁移默认开',
       '{ id = "vendor", label = L["商人"] }' in bisui
       and 'if kind == "商人" then return "vendor" end' in bisui
       and 'if s.fSrcVer ~= 2 then' in bisui
       and 'if s.fSrcSet and s.fSrcSet.vendor == nil then s.fSrcSet.vendor = true end' in bisui
       and 'pop:SetSize(170, 334)' in bisui
       and 'gb:SetPoint("TOPLEFT", pop, "TOPLEFT", 8, -296)' in bisui)
    ck('★★ BIS 两套自动方案：当前等级已知内容（排除其他）/ 当前等级含位置来源（全收），置顶且进页默认预览前者',
       'local AUTO_SRC_KNOWN = { craft = true, quest = true, boss = true, rare = true, vendor = true }' in bisui
       and 'local function ComputeAutoPlan(mode, cap)' in bisui
       and '{ auto = "known", lv = AutoLevel(), type = L["已知内容"] }' in bisui
       and '{ auto = "all", lv = AutoLevel(), type = L["包含位置来源"] }' in bisui
       and 'function BG.UseAutoPlan(mode)' in bisui
       and 'elseif self.__auto then' in bisui
       and 'BG.usingPlan == nil and BG.autoPlan == nil and BG.vol == pe.vol' in bisui
       and 'N_PRESET = maxPages * 2 + 2' in bisui
       and 'BG.__wantDefault = true' in bisui
       and 'if not BG.usingPlan then BG.UseAutoPlan("known") end' in bisui)
    ck('★★ 护甲片行等级列 = 要求等级（可交易物品，不显示「附魔 N」技能口径）',
       'if e.item then' in bisui
       and 'r.lvl:SetText(e.req and format(L["%d 级可用"], e.req) or "")' in bisui
       and 'r.lvl:SetText(e.lvl and format(L["附魔 %d"], e.lvl) or "")' in bisui
       and '（%d 级可用）' not in bisui)
    ck('★ BIS 附魔候选不再按 req 剔除（EnchRowsFor 收集循环无 req 过滤）',
       'if not (cap and e.req and e.req > cap) then' not in bisui)
    ck('★★ BIS 装备卡差值徽章只显百分比（基准分无效时回退最高分，禁显裸分）',
       'BG.baseScore = mx' in bisui
       and 'local pct = (rsc / BG.baseScore - 1) * 100' in bisui
       and 'ChipSet(r.chip2, tostring(math.floor(rsc + 0.5)), CHIP_DOWN_BG, nil)' not in bisui)
    ck('★★ 装备库来源补丁：1401 条新来源 + 世界掉落等级段 + 任务 ID 表落库',
       geardata.count('首领掉落|') >= 300
       and '[23057]="首领掉落|纳克萨玛斯' in geardata
       and re.search(r'ns\.GearWDLv = \{ \[647\]=\{54,59\}', geardata) is not None
       and re.search(r'ns\.GearSrcQ = \{', geardata) is not None)
    ck('★★ 装备库来源补丁：GearUI 运行时任务标题 + 等级段渲染接线',
       'GetTitleForQuestID' in gearui
       and 'GD_SRC_Q and GD_SRC_Q[e.id]' in gearui
       and 'GD_WDLV and GD_WDLV[e.id]' in gearui
       and '%s级怪物' in gearui)
    # 自动路线（拍卖行价格 / 卖店价 / 快照时间戳）也纳入静态检查（2026-10-10）
    profra = open(os.path.join(ADDON, 'Core', 'ProfRouteAuto.lua'), encoding='utf-8',
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
    ck('★★ 升级 HUD 路线模式：routeFor（自动门禁 = 设置开 +（optim 免价格插件 | Auctionator 可用）+ 有价/optim，否则回落固定）',
       'local function routeFor(slug, skill)' in pfhud
       and 'PD.Setting("autoRoute") and RA' in pfhud
       and '(scheme == "optim" or RA.Available())' in pfhud
       and 'if res and (res.priced or scheme == "optim") then return "auto", res.steps end' in pfhud
       # 2026-10-11：固定分支按「目标等级」裁剪（用户：「hud 固定路线显示也需要 根据我设置等级 显示」）
       and 'return "fixed", clipFixedSteps(lv and lv.steps or nil, routeTarget(slug))' in pfhud)
    # 2026-10-11：HUD 固定路线裁剪口径必须与专业页 ClipFixedSteps 逐字一致（同一套折算公式）。
    #   ⚠️ RefreshRoute 要**切出函数体**再断（只断字符串存在 ⇒ 空壳函数照样绿，踩过一次）。
    _rf = pfhud.find('function PF.RefreshRoute(slug)')
    _rfseg = pfhud[_rf:_rf + 400] if _rf >= 0 else ''
    ck('★★ 升级 HUD 固定路线按目标等级裁剪（口径与专业页 ClipFixedSteps 一致）',
       'local function clipFixedSteps(steps, target)' in pfhud
       and 'if not target or target >= 300 then return steps end' in pfhud
       and 'nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))' in pfhud
       and 'out[#out + 1] = { a, nb, st[3], nq, _clip = isClip or nil }' in pfhud
       # 目标 >= 300 = 全程 ⇒ 原样返回（不与旧行为回归）
       and 'if a > target then break end' in pfhud)
    ck('★ 升级 HUD 目标等级变更 → 即时重推指针（PF.RefreshRoute，不必等 1 秒轮询）',
       # ⚠️ 不能只断「字符串存在」：把函数体改成 `local s = nil` 的**空壳**照样通过。
       #    必须切出函数体那一段，确认里面真有 Sync + Paint（不是被提前 return 掐掉）。
       _rf >= 0 and 'local s = st()' in _rfseg and 'PF.Sync()' in _rfseg
       and 'pcall(PF.Paint)' in _rfseg
       and 'local s = nil' not in _rfseg)
    ck('★★ 升级 HUD 路线模式：自动 opts 与专业页逐项一致（起点 / 三个过滤 / 目标按 slug 取）',
       'PD.Setting("autoFromCurrent")' in pfhud and 'PD.Setting("autoOnlyAH")' in pfhud
       and 'PD.Setting("autoNoFormula")' in pfhud and 'PD.Setting("autoLearnedOnly")' in pfhud
       and 'target = routeTarget(slug)' in pfhud)
    ck('★★ 升级 HUD 路线模式：段落 / 购物 / 浏览全走 routeFor（不许再直读固定路线段表）',
       '#lv.steps' not in pf_live and 'LV[s.slug]' not in pf_live
       and pf_live.count('routeFor(s.slug, s.skill)') == 5)
    ck('★★ 升级 HUD 路线模式：段标带模式前缀（自动计算 / 固定路线，复用既有 L 键）',
       '((mode == "auto") and L["自动计算"] or L["固定路线"])' in pf_live
       and 'format(L["段落 %d / %d"], vi, #steps)' in pf_live)
    ck('★★ 升级 HUD 路线模式：配方查找表并入 rinfo（附魔路线全靠它取材料）',
       'if lv and type(lv.rinfo) == "table" then' in pf_live
       and 'local function recMats(rec) return rec and (rec[12] or rec.mats) or nil end' in pf_live
       and 'local function recItem(rec) return rec and (rec[2] or rec.makes) or nil end' in pf_live
       and 'if mats and #mats > 0 then' in pf_live)
    # ── ★ 药丸染色不许把 Unpack 放在**非末位实参**（Lua 多返回值只在末位展开）──
    #   历史 bug（用户实机 25 连报）：`pill(..., Unpack(C_OK), 0.5)` 里 Unpack 是倒数第二个，
    #   Lua 只取首值 ⇒ g 收到 0.5、b 为 nil ⇒ PillBaseCol 预混时 b*0.5 直接「算术运算 nil」崩，
    #   且**只在「已备齐」分支**（row.missing<=0）触发，缺料时不崩 —— 离线桩没有 GetItemCount
    #   ⇒ Have() 恒 0 ⇒ missing 恒 >0 ⇒ 该分支零覆盖，所以历次全绿也照崩。
    #   这里做源码级扫描：任何 `Unpack(...)` / `unpack(...)` 后面紧跟逗号都判红。
    _bad_unpack = [l.strip() for l in pf_live.split('\n')
                   if re.search(r'\b[Uu]npack\([^()]*\)\s*,', l)]
    ck('★★ 升级 HUD：Unpack / unpack 不许出现在非末位实参（多返回值只展末位 → b 收到 nil 崩染色）',
       not _bad_unpack, ' | '.join(_bad_unpack))
    # ── 购物清单「只显示缺失」开关（2026-10-11 用户）──
    #   ① 表头必须换短键（旧的「从当前段累计到 300，含银行」不许再出现在渲染里）；
    #   ② 开关必须真建（CheckButton）并且**表头给它让位**（否则长文案压住开关）；
    #   ③ 过滤必须排在「算各列宽」之前（否则被滤掉的长名字仍撑宽名字列，右留一片白）；
    #   ④ 一键导入口径不许被过滤波及（DoImport 仍走 shopList 全量）。
    ck('★★ 升级 HUD 购物清单：表头改短（换 L["购物清单"]，旧长键不再用于渲染）',
       'f.shop.head:SetText(L["购物清单"] .. format(L[" · 共%d种"], #shown))' in pf_live
       and '购物（从当前段累计到 300，含银行）"] .. format' not in pf_live)
    ck('★★ 升级 HUD 购物清单：「仅显示缺失」开关已建 + 表头右侧让位（长文案不压开关）',
       'f.shop.missTog = CreateFrame("CheckButton", nil, f.shop)' in pf_live
       # 2026-10-10：表头右界还要再让出「一键导入」按钮位（66 + 6 间隔 + 4 余量）
       and 'f.shop.head:SetPoint("RIGHT", f.shop, "RIGHT", -(SHOP_TOG_W + 66 + 12), 0)' in pf_live
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
    # 让位量必须按标签**实测宽**现算：英文 "Missing only"（≈93px）比中文「仅显示缺失」（70px）
    # 宽近一半，写死 96 会让 enUS 的表头可用宽被吃掉一截。
    ck('★★ 升级 HUD 购物清单：表头让位量按标签实测宽现算 + 旧键「只显示缺失」已退役',
       'local SHOP_TOG_W = labW + 48' in pf_live
       and 'pcall(PDw.TextW, L["仅显示缺失"], 14)' in pf_live
       and 'L["只显示缺失"]' not in pfhud)
    #   ⚠️ 用 find 取下标并判 -1：改前基线里没有这些子串，.index() 会把整段断言崩掉
    #      （=「能红就绝不许崩」，见 PROF_PITFALLS 的两条工程坑）。
    _i_shown = pf_live.find('local shown = {}')
    _i_cols = pf_live.find('local nameW, numW, missW, tagW, anySold')
    ck('★★ 升级 HUD 购物清单：过滤排在算列宽之前（先行滤出 shown，再扫列宽）',
       _i_shown >= 0 and _i_cols >= 0 and _i_shown < _i_cols
       and 'if (not onlyMissView()) or e.missing > 0 then shown[#shown + 1] = e end' in pf_live
       and 'for _, e in ipairs(shown) do' in pf_live
       and 'for _, e in ipairs(list) do\n            local nm, got = DG.ItemName(e.id)' not in pf_live)
    ck('★ 升级 HUD 购物清单：一键导入口径不受过滤影响（DoImport 仍走 shopList 全量）',
       'local list = shopList(tmp)' in pf_live)
    # ── 购物清单药丸重做（2026-10-11 用户：按 UI_RULES §4 BuildCapsule 胶囊，方案 D 三段贴图退役）──
    ck('★★ 升级 HUD 购物清单：药丸走 BuildCapsule 胶囊宿主帧（旧三段贴图方案 D 退役）',
       'local rowsShopMissPill, rowsShopSoldPill, rowsShopTagPill = {}, {}, {}' in pf_live
       and 'cols = ns.hui.BuildCapsule(p, 8, ns.hui.layer.L2)' in pf_live
       and 'p.__cols = cols' in pf_live
       and 'p.fs = MakeFS(p, 14, color, "CENTER")' in pf_live
       and 'local function paintPill(p, txt, x0, wpx, cr, cg, cb, ca)\n                p:ClearAllPoints()' in pf_live
       and 'paintPill(mp, format(L["缺%d"], row.missing), xMiss, missW, Unpack(C_BAD))' in pf_live
       and 'paintPill(sp, L["直售"], xSold, soldW, Unpack(C_OK))' in pf_live
       and 'rowsShopTagPill[i]:Hide()' in pf_live
       and 'pill(miss' not in pf_live
       and 'hidePillBG' not in pf_live
       and 'PillBaseCol' not in pf_live)
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
    # ★★ 探索页两件都在 TOC 里（数据在 DungeonUI 前、骨架在 ProfessionUI 后）
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
       and 'EG.listCard:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -EG.TOP_EDGE)' in exui
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
    ck('★★ 探索页双卡倒圆角（hui SkinPopup 走主题 L1 底，非 hui 方形回退）',
       'ns.hui.SkinPopup(listCard, 6)' in exui
       and 'ns.hui.SkinPopup(navCard, 6)' in exui)
    # ★ 2026-10-10 规整守门：SkinPopup 白 α fill 清零 + 内卡显式 L2 + 窗沿/间距公式
    #   （LIST_PAD=8、行距 ROW_GAP=4、轨道竖链 TICK_Y/BAR_Y、BODY_BOT 退役改 EG.EDGE）。
    ck('★★ 探索页 2026-10-10 规整守门（SkinPopup 白 α fill=0 处 + 内卡 L2 + EDGE=PAGE_INSET（§3.3 外缘 12） + LIST_PAD=8 + ROW_GAP=4 + 轨道竖链公式）',
       re.search(r'SkinPopup\([^)]*\{ 1, 1, 1, 0\.0', exui) is None
       and 'ns.hui.layer.L2' in exui
       and 'EG.EDGE = PAGE_INSET' in exui
       and 'EG.RIGHT_W = CONTENT_W - EG.X0 - EG.EDGE' in exui
       and 'EG.LIST_PAD = 8' in exui
       and 'EG.ROW_H, EG.ROW_GAP = 46, 4' in exui
       and 'EG.BAR_Y + EG.BAR_H + 8, 20, 8, 96' in exui
       and 'rw:SetSize(EG.TOOL_W, EG.TOOL_H)' in exui
       and 'rb:SetSize(EG.TOOL_W, EG.TOOL_H)' in exui
       and 'gb:SetPoint("TOPRIGHT", page, "TOPRIGHT", -EG.EDGE, -EG.TOOL_Y)' in exui
       and 'BODY_BOT' not in exui)
    ck('★ 探索页几何摆位走 LayoutBody 且在 Build 期被调用',
       'function EG.LayoutBody()' in exui and exui.count('EG.LayoutBody()') >= 1)
    # ★★ 无限服没有 C_Map.GetMapInfoFromAreaID（专业页十八轮踩实）—— 探索页标记主路径
    #    必须是静态映射（2026-10-09 起整表挪 Data_AreaMap / ns.AreaMap，UI 只留委托）。
    _am_n = len(re.findall(r'\[\d+\]\s*=\s*\d+', am_src))
    ck('★★ 探索页标记主路径 = 静态 AREA_MAP（Data_AreaMap >=30 区域，含 17→1413 wowhead 互证值；UI 取 ns.AreaMap）',
       _am_n >= 30 and '[17] = 1413' in am_src
       and 'local AREA_MAP = ns.AreaMap or {}' in exui, _am_n)
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
       'EG.barFill' in exui and 'EG.BAR_W = EG.RIGHT_W - 2 * EG.LIST_PAD' in exui
       and 'EG.BAR_H = 4' in exui
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
       and 'f:SetPoint("TOPLEFT", host, "TOPRIGHT", 4, 0)' in exmap and 'ns.hui.ReskinToggle' in exmap
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
    ck('★★ 探索地图设置：连接方式/书籍显示改 Hui ShowMenu 下拉行（光标锚定 + 外点关闭）'
       ' + 分组标题改「找书HUD」',
       'local function mkDropdownRow' in exmap
       and 'ns.hui.ShowMenu(menu, { owner = b })' in exmap
       and 'hdr(L["找书HUD"])' in exmap)
    _ddui = open(os.path.join(ADDON, 'Core', 'DungeonUI.lua'), encoding='utf-8',
                 errors='replace').read().replace('\r\n', '\n')
    ck('★★ DungeonUI 类型/BOSS 下拉统一走 Hui ShowMenu（owner 传入保 toggle 语义）',
       'ns.hui.ShowMenu(items, { owner = owner })' in _ddui)
    _twl = open(os.path.join(ADDON, 'Locales', 'zhTW.lua'), encoding='utf-8').read()
    _enl = open(os.path.join(ADDON, 'Locales', 'enUS.lua'), encoding='utf-8').read()
    ck('★★ 探索地图设置三语 L 键：图钉编号（EN 缺键会拒绝生成，这里再钉一次）',
       '图钉编号' in _twl and '图钉编号' in _enl)
    ck('★★ BIS 自动方案三语键齐全（enUS 缺键会拒绝生成）',
       'L["已知内容"]' in _twl and 'L["包含位置来源"]' in _twl
       and 'L["已知内容"]' in _enl and 'L["包含位置来源"]' in _enl)
    ck('★★ 达拉然城等定制副本任务奖励补 GearSrcQLv（req0/1 不再漏进低级池，gen_qlv_from_quests.py 产出）',
       '[279837]=24' in geardata and '[251962]=24' in geardata
       and '[279845]=24' in geardata and '[279847]=24' in geardata
       and '[279837]=92457' in geardata
       and 'local qlv = ns.GearSrcQLv and ns.GearSrcQLv[id]' in bisui
       and 'UsableAt(r.id, cap, r.req or 0)' in bisui)
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
    #   2026-10-10 规整：TOP 锚改 TICK_Y（= 卡顶+8），进度条锚改 BAR_Y。
    ck('★ 探索页进度文本贴右缘（窗沿+内衬）且抬到进度条上方（-EG.TICK_Y）',
       'EG.prog:SetPoint("TOPRIGHT", page, "TOPRIGHT", -(EG.EDGE + EG.LIST_PAD), -EG.TICK_Y)' in exui
       and 'bar:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0 + EG.LIST_PAD, -EG.BAR_Y)' in exui)
    # ★ 交互重排（方案 A 落地）：打卡 = 行上独立圆环打卡标 r.chk（2026-10-10 方框改三态圆形贴图）；
    #   2026-09-24 用户定：Shift/Alt 修饰键点击废除（打卡只走打卡标），行点击只剩标图；
    #   行悬停 tooltip 整块移除（信息行内已全展示），两态口径常驻注释摆页面上。
    #   GameTooltip 仅允许出现在奖励子页的 EG.RewardTip 内（奖励详情无行内载体，必须悬停）。
    _gti = exui.find('GameTooltip')
    ck('★★ 探索页行交互：只剩标图 + 圆环打卡，修饰键与行 tooltip 不得再现',
       'r.chk' in exui and 'r.strike' in exui
       and 'IsShiftKeyDown' not in exui and 'IsAltKeyDown' not in exui
       and 'IsControlKeyDown' not in exui
       and '__tip' not in exui
       and (_gti < 0 or _gti > exui.find('function EG.RewardTip')))
    ck('★ 探索页两态口径常驻注释（独立一行，筛选行下方左对齐；奖励钮占位后从筛选行让开）',
       'EG.note' in exui and '自动识别：金格 = 已上交；绿格 = 背包有书未上交' in exui
       and 'EG.note:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0 + EG.LIST_PAD, -EG.NOTE_Y)' in exui)
    # ★ 全插件字号标准（2026-09-24 用户定）：标题 16 / 正文文本 14；分组小标 11 与专业页导航同款
    _fs = re.findall(r'MakeFS\([^,]+,\s*(\d+),', exui)
    ck('★★ 探索页字号标准：标题 16 / 正文 14 / 分组小标 11（MakeFS 出现的字号只许 11/14/16）',
       _fs and all(v in ('11', '14', '16') for v in _fs),
       sorted(set(_fs)))
    # ★ 筛选五颗：全部 / 联盟领地(ally=terr=="A") / 部落领地(horde=terr=="H") / 争夺中的领地(contested=terr=="C") / 只看没找到
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
       and 'EG.NAV_TOP, EG.NAV_PAD = EG.TOP_EDGE + 8, 8' in exui
       and 'EG.X0 = EG.NAV_X + EG.NAV_PAD + EG.NAV_W + EG.NAV_PAD + 8' in exui
       and 'EG.rwMageHead' in exui and 'EG.rwMageLines' in exui
       and 'ns.ExploreMageBonus' in exui
       and 'mh:Hide()' in exui and 'ln:Hide()' in exui)  # ★ 用户定：法师块先隐藏只留代码
    # ★ 2026-09-25 用户定：说明卡 + 等级/推荐后缀 + 右上角地图坐标合并
    ck('★★ 探索页奖励页「如何获得奖励」说明卡（SkinPopup 圆角 + 文案走 ns.ExploreHowTo）',
       'EG.howCard' in exui and 'ns.ExploreHowTo' in exui
       and 'ns.hui.SkinPopup(card, 6, nil, ns.hui.layer.L2)' in exui
       and 'EG.howSteps' in exui
       and 'ns.ExploreMageBonus' in exui
       and 'mh:Hide()' in exui)
    # ★ 2026-10-10 用户定：小动物页卡片高度自适应（yy 链统一，固定 176 退役）+
    #   网格按实高顺序重锚 + 滚动子帧高 = 头部 + 实高累计（奖励卡两行制同日落地）
    ck('★★ 探索页宠物卡流自适应（yy 链统一 / 实高网格 / 子帧实高 / 奖励行两行制）',
       'local flowY = 0' in exui
       and 'local hCard = -yy + EG.TOY_CARD_PAD' in exui
       and 'flowY = flowY + hCard + EG.PET_GAP' in exui
       and 'flowY - EG.PET_GAP' in exui
       and 'local yy = -76' in exui
       and 'card:SetHeight(toy and' not in exui
       and 'row.meta' in exui and 'L["装等%d"]' in exui and 'L["需要等级 %d"]' in exui
       and 'row.icon:SetSize(36, 36)' in exui
       and 'reqLvl > plv' in exui)
    ck('★★ 探索页行内胶囊徽章（2026-09-25 用户定方案 A：阵营/等级/推荐/待确认四胶囊，'
       '极细 1px 描边、推荐无星、阵营去「仅」字；等级 = ns.ExploreZoneLv；'
       '推荐 = ns.ExploreRecIDs；待确认 = ns.ExploreUnverIDs）',
       'MakeTagPill' in exui and 'PaintPill' in exui and 'FAC_PILL' in exui
       and 'ns.ExploreZoneLv and ns.ExploreZoneLv[rec[2]]' in exui
       and 'ns.ExploreRecIDs and ns.ExploreRecIDs[id]' in exui
       and 'ns.ExploreUnverIDs and ns.ExploreUnverIDs[id]' in exui
       and 'edgeSize = 1' in exui
       and 'PILL_PREV' in exui
       and 'local function MakeTagPill(r, key)' in exui
       and 'PaintPill(r, key, txt, show' in exui
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
       # 2026-10-10 用户定：lc 外层卡皮删除（任务行已是独立卡），lc 只当布局容器
       and 'ns.hui.SkinPopup(lc, 8)' not in exui
       and 'BagLayoutRows()' in exui
       and 'EG.bagDRH2 = dRwH2' in exui
       and 'L["你可以选择一件："]' in exui and 'L["你还会获得："]' in exui
       and 'EG.bagNote = nc' in exui
       and 'L["作者备注"]' in exui and 'L["收获"]' in exui
       and 'BAG_REQ_LVL, BAG_QUEST_LVL = 14, 40' in exui
       and 'xp = 3150' in exui and 'xp = 2350' in exui and 'xp = 315,' in exui
       and 'ns.hui.SkinPopup(det, 8, nil, ns.hui.layer.L2)' in exui
       and 'ns.hui.SkinPopup(nc, 8, nil, ns.hui.layer.L2)' in exui
       and 'ns.hui.SkinPopup(eb, 6, nil, ns.hui.layer.L2)' in exui
       and 'EG.bagViewH' in exui
       and 'EG.bagFrame:SetPoint("TOPLEFT", EG.page, "TOPLEFT", EG.X0, -EG.TOP_EDGE)' in exui)
    # ★ 2026-09-24 第七轮（用户截图反馈）：芯片去边框+图标 24；石爪三步 area 8→406
    #   （此前定位飞悲伤沼泽）；作者备注支持内联可点坐标段（③ 岔口 50.9,52.3 / ⑥ 推车 87.4,49.7
    #   + 信使行囊阿拉希侧 22.4,24.2，第 16 轮对齐 foreverchanges.pro 攻略精修）；
    #   注释卡行首物品钮可悬停（混调干果 216619 / 睡袋 211527）；总奖励二选一拆②③两组。
    ck('★★ 睡袋第七轮（芯片无边框24 + area406 + 备注内联坐标 + 注释物品钮 + 二选一两组）',
       'ns.hui.SkinPopup(c, 8, nil, ns.hui.layer.L3, 1, true)' in exui
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
    ck('★★ 睡袋第八轮（备注段宽走 EG.bagRWd 防全局 nil + 卡间距统一 8；2026-10-10 右列两侧内衬 8 → RWd=CW-LW-16）',
       'local avail = (EG.bagRWd or 700) - 20' in exui
       and 'CW - LW - 16' in exui
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
    # ★★ 秒卡池（普通卡 secCards / 金卡 secGoldCards）清场不许用「共用计数器」（2026-10-09）。
    #   两个池子用得不一样多时（总览/营地用普通卡池、购物清单只用金卡池），共用 ci 会让
    #   两个池都「从 ci+1 起裁」⇒ 上一页那几张卡留在新页上（实测：营地/总览 → 升级/购物清单
    #   多留 1 张卡盖在材料表上）。正解：每轮先全收，再各用各的计数器按需开。
    #   行为级回归：_temp/_prof_rowsig_probe.py（跨页签穷举 + PD.child 孤儿帧扫描）。
    ck('★★ 秒卡池每轮先全收再按需开（不许共用计数器 ci 裁后段）',
       'local ciP, ciG = 0, 0' in profui
       and 'local c = (bgold[s] and PD.secGoldCards or PD.secCards)[ci]' not in profui
       and 'for i = ci + 1, #PD.secCards do PD.secCards[i]:Hide() end' not in profui)
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
    ck('★ 总览单列（2026-10-10 用户定：简介/开发备注/数字速览删除后不再分栏，OV_SPLIT 退役）',
       'PD.OV_SPLIT' not in profui
       and '        PD.lvSplit = false\n' in profui
       and 'PushHead(rows, L["数字速览"], 1)' not in profui
       and 'local function stat(label, value)' not in profui)
    # ★★ 卡片净距标准（2026-09-24 用户定稿 8px，已写入 AGENTS.md）：段落卡上下、左右
    #    看得见的空隙 = SEC_GAP，由 OV_GUT = SEC_GAP + 2*SEC_PAD 换算落地 —— 段间空档行、
    #    右栏 x 落点、分栏线落点三处都必须认 OV_GUT，不许别处另写死间距数。
    ck('★★ 卡片净距标准 8px（SEC_GAP 单源，OV_GUT 换算；段间空档 ≥3 处 + 右栏落点 + 分栏线）',
       'PD.SEC_GAP = 8' in profui
       and 'PD.OV_GUT = PD.SEC_GAP + 2 * PD.SEC_PAD' in profui
       and profui.count('PushGap(rows, PD.OV_GUT, 1)') >= 3
       and 'PushGap(rows, PD.OV_GUT, 2)' not in profui
       and '(PD.LIST_PAD + lw + PD.OV_GUT)' in profui
       and 'local gut = PD.lvSplit and PD.OV_GUT or PD.COL_GAP' in profui)
    # ★★ 卡中卡左右几何（2026-10-11 用户截图实锤二次修正；2026-10-13 三改 padL 化）：
    #    子区坐标系在外卡内左缩 8、右齐平 ⇒ 内卡水平包裹默认 SEC_PAD_X=8（左 padL 可被
    #    每页覆写：工匠文书页 secPadL=0 与上方双卡左缘对齐）、右包恒 SEC_PAD_X；
    #    sec>0 行内容仅右侧收 SEC_IN=8。垂直包裹仍走 SEC_PAD（OV_GUT 换算数学不破）。
    ck('★★ 卡中卡左右几何（padL 可覆写默认 SEC_PAD_X 包裹 + SEC_IN 右侧单边内缩 + sec>0 守卫）',
       'PD.SEC_PAD_X = 8' in profui
       and 'PD.SEC_IN = 8' in profui
       and 'local padL = PD.secPadL or PD.SEC_PAD_X' in profui
       and 'b.x0 - padL' in profui
       and '(b.x1 - b.x0) + padL + PD.SEC_PAD_X,' in profui
       and 'if spec.sec and spec.sec > 0 then\n                w = w - PD.SEC_IN' in profui
       and 'x = x + PD.SEC_IN' not in profui)
    # ★★ 营地对照表卡中卡（2026-10-11 用户定）：bonusTable 根挂 bonusCard（父子层级可靠），
    #    卡 = L2 同 sec 卡轨（子区 [0, RIGHT_W−8]），表宽右收 SEC_IN=8、卡上下包 SEC_PAD；
    #    卡顶 = 行流光标（防压表头行帧底 2px）；悬停随底座 L2 升 L4（+2 档规则）。
    ck('★★ 营地对照表卡中卡（bonusCard L2 包裹 + BT_W 右收 + 悬停 L4）',
       'PD.bonusCard = card' in profui
       and 'local root = CreateFrame("Frame", nil, card)' in profui
       and 'PD.bonusCard:SetSize(PD.RIGHT_W - PD.SEC_PAD_X, (PD.bonusTableH or 0) + 2 * PD.SEC_PAD)' in profui
       and 'PD.bonusTable:SetPoint("TOPLEFT", PD.bonusCard, "TOPLEFT", PD.LIST_PAD, -PD.SEC_PAD)' in profui
       and 'PD.BT_W = W' in profui
       and 'local W = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.SEC_IN' in profui
       and 'r:SetSize(PD.BT_W, rowH)' in profui
       and 'local c4 = ns.hui.layer.L4' in profui)
    # ★★ 三轮（2026-09-24 实机）：① 折行宽度必须跟实际渲染栏宽走（ColTextW 认 splitLW/splitRW，
    #    否则左栏文字按 0.80 旧宽折行 → 整段冲进右栏「简介超出卡片」）；② 段落卡走
    #    ns.hui.BuildRoundedBG 圆角原语（可视化方案里卡片四角是圆的，SetBackdrop 是直角）。
    ck('★★ ColTextW 折行宽度跟随本页举手分栏（lvSplit→splitLW/RW，gridSplit→GRID_LW/RW）',
       'if PD.lvSplit then return PD.splitRW or PD.COL_RW end' in profui
       and 'if PD.lvSplit then return PD.splitLW or PD.COL_LW end' in profui
       and 'if PD.gridSplit then return PD.GRID_RW end' in profui)
    ck('★★ 段落卡是圆角（ns.hui.BuildRoundedBG 原语，弧盘 + 1px 描边；不许退回 SetBackdrop 直角）',
       'ns.hui.BuildRoundedBG(c, 6, ns.hui.layer.L2, "both", true, 1)' in profui
       and profui.count('secCards') > 0
       and 'c:SetBackdrop(' not in profui.split('PD.secCards = {}', 1)[-1].split('-- ── 底部左侧', 1)[0])
    # ★★ 段内末行免分割线 → 2026-10-10 分割线整体退役（用户：斑马纹已承担行分隔）：
    #    前瞻标记保留（数据层无害），消费位删除、r.sep 恒 Hide —— 旧写法回来了就是回退。
    ck('★★ 段落卡分割线退役（2026-10-10：斑马纹承担行分隔，r.sep 恒 Hide、消费位删除）',
       'spec._lastInSec = not (nxt and nxt.sec == spec.sec)' in profui
       and 'r.sep:Hide()' in profui
       and 'if spec._lastInSec then r.sep:Hide() else r.sep:Show() end' not in profui)
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
    ck('★ 专业页壳帧在 Build 建、内容走 EnsureBuilt 懒构建（2026-10-09 架构）',
       'U.profPage = CreateFrame("Frame", nil, panel)' in _bld
       and 'ns.ProfModule.Build(U.profPage)' in _eb
       and 'if ns.LoadForeverPages then' in _bld)

    # ── 观感六改（2026-09-23 用户口径）──────────────────────────────────────
    # ① 每页一张大卡片（行不再各自成小卡）
    ck('★★ 专业页正文是一张**大卡片**（用户：现在是每一行一个小卡片 → 要整页一张）',
       'PD.listCard = PD.MakeCard(page)' in _pbuild
       and 'function PD.MakeCard(f)' in profui
       and 'c:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)' in profui)
    # ★ 顺序断言：同为 page 的子帧按创建序绘制 —— 大卡必须先于滚动帧建，否则盖住整页列表
    ck('★★ 大卡建在滚动帧**之前**（子帧按创建序绘制，反了就盖住列表）',
       _pbuild.index('PD.listCard = PD.MakeCard(page)') < _pbuild.index('SetScrollChild(child)'))
    # ★★ 容器卡版式（用户定）：左导航 + 右正文两张 L1 卡，顶/底对齐等高；子页签收进右卡
    ck('★★ 专业页双容器卡：navCard/listCard 先建垫底 + 等高锚定（三外缘 = PAGE_INSET 12（§3.3），卡间 = GUTTER）',
       'PD.CARD_INSET = PAGE_INSET' in profui
       and 'PD.CARD_TOP = 8' in profui
       and 'PD.navCard:SetPoint("TOPLEFT", page, "TOPLEFT", PD.CARD_INSET, -PD.CARD_TOP)' in profui
       and 'PD.navCard = PD.MakeCard(page)' in _pbuild
       and 'PD.navCard:SetPoint("BOTTOMRIGHT", page, "BOTTOMLEFT",' in profui
       and 'PD.RIGHT_X - PD.LIST_PAD, -PD.CARD_TOP)' in profui
       and '-PD.CARD_INSET, PD.CARD_INSET)' in profui
       and _pbuild.index('PD.navCard = PD.MakeCard(page)')
           < _pbuild.index('PD.navOrder = {}')
       and _pbuild.index('PD.navCard = PD.MakeCard(page)')
           < _pbuild.index("for _, def in ipairs(DG.PROF_SUBTABS)"))
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
       and _phover.index('if on then') < _phover.index('elseif r.__z then')
       and _phover.index('elseif r.__z then') < _phover.index('r:SetBackdropColor(1, 1, 1, 0)'))
    ck('★★ 斑马纹：BindRow 先落 __z 再落色（行复用不残留条纹）',
       'r.__z = spec.z and true or false' in profui
       and profui.index('r.__z = spec.z and true or false')
           < profui.index('PD.SetRowHover(r, r.IsMouseOver and r:IsMouseOver())'))
    ck('★★ 斑马纹：PaintRows 按真行分列交替计数（标题/说明/空档不吃底纹）',
       'local zc = { 0, 0 }' in profui
       and 'zc[col] = zc[col] + 1' in profui
       and 'spec.z = (zc[col] % 2 == 0)' in profui
       and 'spec.z = nil' in profui)
    # ★★ UI 规则收编（2026-10-11 用户「全做」）：总览字号体系 + 行悬停 L 实色 + 对照表金线退役
    # ★★ 2026-10-11 用户回退：行高恢复 34（双行 fs=14 在 34px 会叠字 → 双行行一律不带 fs，
    #    恢复 13/11/12）；fs=14 只保留在单行行（h=ROW_H1）与 PushText（TEXT_H 24）。
    ck('★★ 总览字号收编：段标题默认 16（单行行 14 走 spec.fs，副行/右列随 auxFs 联动；双行不带 fs）',
       'local wantFs = spec.fs or (spec.kind == "head" and 16 or 13)' in profui
       and 'local auxFs = (spec.fs == 14) and 14 or nil' in profui
       and 'local wb = auxFs or 11' in profui
       and 'local wc = auxFs or 12' in profui
       and 'local dfsW = (spec.fs == 14) and 14 or 12' in profui
       and 'kind = "row", h = PD.ROW_H1, col = 1, fs = 14,' in profui
       and 'kind = "row", col = 1, fs = 14,' not in profui
       and 'nameColor = fc, fs = 14,' not in profui
       and 'PD.ROW_H, PD.ROW_H1, PD.TEXT_H = 34, 24, 24' in profui
       and 'PushText(rows, p.steps_note, 14, C_GREY, 1)' in profui
       and '"· " .. (rc[3] or ""), 14, nil, 1' in profui)
    ck('★★ 行悬停 hui 走 L4 实色（白 α 近似退役，非 hui 回落保留）',
       'local c4 = ns.hui.layer.L4' in profui
       and 'r:SetBackdropColor(c4[1], c4[2], c4[3], c4[4] or 1)' in profui
       and 'r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)' in profui)
    ck('★★ 营地对照表：表头金线改 DIV 色、悬停块随 L2 卡座升 L4、口径注释升 14',
       'local dv = ns.hui.layer.DIV' in profui
       and 'local c4 = ns.hui.layer.L4' in profui
       and 'PD.bonusTitleNote = MakeFS(child, 14, C_GREY, "RIGHT")' in profui)
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
    # ★★ 商人兑换行三列 + 中文名（2026-10-11 用户）：favor 行补 材料(配方真实材料)/拍卖/制作成本。
    #    ★ 匹配键=f[5]（商人兑换图样 ID 与 d.rows 图样 ID 是两个物品，f[1] 在 rows 里查不到=材料全空；
    #      f[5] 才是 d.rows r[2] 同款图样，实锤 favor{252770,...,252433} ↔ rows r[2]=252433）。
    #    拍卖列同口径优先 f[5]（有 AH 快照，f[1] 恒 —）。
    ck('★★ 商人兑换行三列齐 + 换得名本地化优先（用户 2026-10-11）',
       'PD.FavorSpec(f, d)' in profui
       and 'qItem = f[1], _mats = mats,' in profui
       and '(out and out ~= "" and out) or f[4] or ""' in profui
       and 'local want = f[5] or f[1]' in profui
       and 'if r[2] == want then' in profui
       and 'RA.AHPriceOf(f[5] or f[1])' in profui
       and 'tipExtra = function() return PD.PriceTipLines(f[1], mats) end' in profui
       and 'sub = (reward ~= "" and format(L["换得：%s"], reward)) or ""' not in profui)
    # ★★ 附魔 spellID 第四源（2026-10-12）：Skillwright [333] join 回填 en[14] 法术ID，
    #    配方页附魔行图标走 SpellIcon(en[14])（GetSpellInfo 两代 API 兜底）；
    #    升级页 rinfo 兜底行三补：色条吃 ri.learn/yellow/green/grey、法术图标、悬停价格段。
    ck('★★ 附魔 spellID 消费链（Skillwright 第四源 + SpellIcon + rinfo 三补）',
       'icon = SpellIcon(en[14]),' in profui
       and 'local function SpellIcon(id)' in profui
       and 'if C_Spell and C_Spell.GetSpellInfo then' in profui
       and 'return select(3, GetSpellInfo(id))' in profui
       and 'icon = ((not rec) and ri and not ri.makes) and SpellIcon(st[3]) or nil' in profui
       and 'or (ri and (ri.yellow or ri.grey))' in profui
       and 'and { ri.learn, ri.yellow, ri.green, ri.grey } or nil,' in profui
       and 'or ((ri and ri.makes and ri.mats)' in profui
       and 'and function() return PD.PriceTipLines(ri.makes, ri.mats) end' in profui)
    # ★★ 行图标垂直居中（2026-10-11 用户）：TOPLEFT -5 写死只对两行行合适，24px 行溢出。
    ck('★★ 行图标随行高垂直居中（h−20)/2）',
       'r.icon:SetPoint("TOPLEFT", r, "TOPLEFT", 6, -math.floor((h - 20) / 2))' in profui)
    ck('★★ 大卡随滚动区定位（四周外扩 LIST_PAD，行再内缩回同一矩形）',
       profui.count('PD.listCard:SetPoint') >= 2
       and 'PD.listCard:SetPoint("BOTTOMRIGHT"' in profui
       and 'PD.listCard:Show()' in profui)
    # ② 升级页布局（2026-10-09 v2 重构：右栏退役，路线与购物清单统一单栏，
    #    材料/图纸全部收进「购物清单」子页，固定/自动共用；固定路线加需要金币）
    ck('★★ 升级页单栏化（PD.lvSplit = false；旧右栏「要准备的材料」退役进购物清单子页）',
       'L["1 → %d 分段路线"]' in profui and 'lvstep = true' in profui
       and 'PD.lvSplit = false' in profui and 'PD.twoCol' not in profui)
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
    # ④ 四合一（2026-10-10 用户定）：页签 7 → 4，营地/传承/说明并入总览
    #    2026-10-11 加板条箱/工匠文书两枚（仅 crates 导航可用，旧专业不受影响）
    #    2026-10-11 14:12 遭劫货物页签按钮暂撤（数据/生成器/分发代码全保留）
    _sts = profui[profui.index('DG.PROF_SUBTABS = {'):]
    _sts = _sts[:_sts.index('\n}') + 1]
    ck('★★ 子页签 7 项（总览/训练师/配方/采集/升级 + 板条箱/工匠文书），遭劫货物暂撤，营地/传承/说明退出页签',
       _sts.count('key = "') == 7
       and 'L["遭劫货物"]' not in _sts
       and 'L["营地"]' not in _sts and 'L["传承"]' not in _sts and 'L["说明"]' not in _sts
       and 'PushHead(rows, L["传承"], 1)' in profui
       and 'PushHead(rows, L["开发备注"]' not in profui
       and 'PushHead(rows, L["简介"]' not in profui)
    # ★★ 训练师页四件套（2026-10-12 新增）：页签键 / Render 分支 / 右上阵营按钮 / 板卡建帧
    ck('★★ 训练师页四件套齐全（PROF_SUBTABS 键 + Render 分发 + 阵营按钮 + BuildTrainerBoard）',
       '{ key = "trainer",  text = L["训练师"] }' in profui
       and 'PD.tab == "trainer"' in profui
       and 'PD.trFacBtns' in profui
       and 'PD.trFac = k' in profui
       and 'function PD.BuildTrainerBoard(parent)' in profui
       and 'PD.BuildTrainerBoard(child)' in profui
       and 'PD.wantTrainerBoard = true' in profui)
    ck('★★ 训练师页工具行阵营三钮已退役（2026-10-12 用户定案：删全部/联盟/部落工具行，改右上角）',
       'PD.TrainerTool' not in profui)
    ck('★★ 训练师板卡列宽反算禁写死（UI_RULES §3.2 恒等式）',
       'local COL_W = math.floor((W - (COLS - 1) * GAP) / COLS)' in profui
       and 'PD.trainerBoardH' in profui)
    # ★★ 页签 → Render 总分发齐全（2026-10-11 遭劫货物页空白真凶：分发漏 plunder）
    import re as _re_tab
    _tabkeys = _re_tab.findall(r'key = "([a-z]+)"', _sts)
    ck('★★ 每个 PROF_SUBTABS 页签 key 都被 Render 总分发覆盖',
       all(('PD.tab == "%s"' % k) in profui for k in _tabkeys),
       [k for k in _tabkeys if ('PD.tab == "%s"' % k) not in profui])
    # ★★ 工匠文书详情三张卡中卡（2026-10-12 用户）：材料明细 / 成本汇总 / 总结各包一张 L2
    #   段落卡（复用总览页 sec 机制），标题 16、正文 14；结论金额独立右对齐不贴字
    _writ = profui[profui.index('function PD.WritRows'):profui.index('function PD.PlunderRows')]
    ck('★★ 工匠文书详情四张卡中卡（头部/材料/汇总/总结）：MarkSec 四段 + hasSecs/secCount 举手',
       _writ.count('MarkSec(rows, sec') == 4
       and 'MarkSec(rows, secH, #rows, 1)' in _writ
       and 'MarkSec(rows, secA, #rows, 2)' in _writ
       and 'MarkSec(rows, secB, #rows, 3)' in _writ
       and 'MarkSec(rows, secC, #rows, 4)' in _writ
       and 'PD.hasSecs = true' in _writ and 'PD.secCount = 4' in _writ)
    _crate = profui[profui.index('function PD.CrateRows'):profui.index('function PD.WritRows')]
    ck('★★ 板条箱详情三张卡中卡（头部/凑法/总结）+ 青睐文案 + 最省标签 + 购买最省行',
       _crate.count('MarkSec(rows, sec') == 3
       and 'MarkSec(rows, secH, #rows, 1)' in _crate
       and 'MarkSec(rows, secO, #rows, 2)' in _crate
       and 'MarkSec(rows, secS, #rows, 3)' in _crate
       and 'PD.secPadL = 0' in _crate and 'PD.secCount = 3' in _crate
       and 'L["青睐 +%d"]' in _crate and 'L["青睐未验证"]' in _crate
       and 'L["声望 +%d"]' not in _crate
       and 'tag = isBest and { text = L["最省"], color = CRATE_GREEN } or nil' in _crate
       and 'format(L["购买 %s"],\n                 PD.MatIconTex(cheapestOpt[1], 14) .. " " .. PD.ItemName(cheapestOpt[1])\n                 .. " ×" .. (cheapestOpt[2] or 1))' in _crate
       and _crate.count('h = PD.ROW_H1, fs = 14,') >= 2)
    ck('★★ 板条箱头部卡含物品图标（与工匠文书头部卡一致，it = { sc.id } 走 head 图标渲染）',
       'it = { sc.id },' in _crate)
    ck('★★ 右列卡中卡整体下移（PaintRows col2 顶衬 SEC_PAD，修头部卡上缘裁剪）+ 每点青睐最低成本',
       'local y = { 0, PD.hasSecs and PD.SEC_PAD or 0 }' in profui
       and 'L["每点青睐的最低成本"]' in _crate
       and 'total / sc.favor' in _crate
       and '(sc.favor or 0) > 0' in _crate)
    ck('★★ 卡中卡字号：标题 16（head 不带 fs）+ 正文 14（ROW_H1 单行 fs=14；旧 fs=13 退役）',
       'kind = "head", col = 2,\n' in _writ
       and _writ.count('h = PD.ROW_H1, fs = 14,') >= 5
       and 'fs = 13,' not in _writ)
    ck('★★ 制造单件成本改名「制造上交所需物的成本」+ 总结标题 + 结论金额独立右对齐',
       'L["制造上交所需物的成本"]' in _writ and 'L["制造单件成本"]' not in _writ
       and 'PushHead(rows, L["总结"], 2)' in _writ
       and 'text = L["自己造省"],' in _writ and 'text = L["直接买便宜"],' in _writ
       and 'format(L["自己造省 %s"]' not in _writ and 'format(L["直接买便宜 %s"]' not in _writ)
    ck('★★ 「最省」徽标两轮上移（-4 → +1 → +9，TOP 锚 y=+9）',
       'bd:SetPoint("TOPRIGHT", host, "TOPRIGHT", -4, 9)' in profui
       and '"TOPRIGHT", host, "TOPRIGHT", -4, 1)' not in profui)
    ck('★★ 上交成本 = 整批上取整凑齐上交数量（ceil(qty/产出)×单次成本；括号后缀删除）',
       'local batches = math.ceil((sw.qty or 1) / (craft[3] or 1))' in _writ
       and 'math.floor(craftSum * batches + 0.5)' in _writ
       and '一次制作' not in _writ
       and 'craftSum / (craft[3] or 1)' not in _writ)
    ck('★★ craftCost 同口径整批上取整（vs 卡自己制造价 = ceil 口径）',
       'craftSum * math.ceil((sw.qty or 1) / (craft[3] or 1))' in _writ)
    ck('★★ 工匠文书卡中卡左缘与上方双卡对齐（secPadL=0 每页左衬；其他页默认 SEC_PAD_X）',
       'local padL = PD.secPadL or PD.SEC_PAD_X' in profui
       and 'b.x0 - padL' in profui
       and '(b.x1 - b.x0) + padL + PD.SEC_PAD_X,' in profui
       and 'PD.secPadL = 0' in _writ
       and 'PD.secPadL = nil' in profui)
    ck('★★ 总结结论金额双分支均为绿色（直接买便宜/自己造省，旧 TIP_RED 退役）',
       'text = L["直接买便宜"],' in _writ
       and _writ.count('rightColor = { 0.42, 0.94, 0.62 },') == 2
       and 'rightColor = TIP_RED,' not in _writ)
    ck('★★ 自身价格列偏移走 OwnR()（表头/数据行/排序热区同源；裸 CRATE_OWN_R 锚点退役）',
       'PD.OWN_SHIFT = 0.08' in profui and 'function PD.OwnR()' in profui
       and profui.count('-PD.OwnR(), -4') == 2 and profui.count('-PD.OwnR(), 0') == 3
       and '-PD.CRATE_OWN_R' not in profui)
    ck('★★ 配方页排序接线：三态(升/降/取消) + 四排序热区 + 四排序字段 + 差价标签',
       'PD.recipeSort = nil' in profui and 'PD.recipeSortDesc = false' in profui
       and 'ahVal = ah,' in profui and 'costVal = total,' in profui
       and 'diffVal = tonumber(' in profui
       and 'gapVal = (ah and total) and (ah - total) or nil,' in profui
       and 'r.icon4' in profui and 'r.hsGap' in profui and 'r.h6' in profui
       and 'L["差价"]' in profui
       and profui.count('_act("ah")') >= 1
       and profui.count('_act("gap")') >= 1
       and profui.count('_act("cost")') >= 1
       and profui.count('_act("diff")') >= 1)
    ck('★★ 双卡胜方标签白字（最省那张的「直接买齐/自己制造」不再灰；败方仍 C_GREY）',
       'c.lab:SetTextColor(Unpack(d.win and C_WHITE or C_GREY))' in profui)
    ck('★★ 卡中卡间距 = 净距 8 标准（行推进 2 + gap − 2×SEC_PAD；卡间 gap 14 / 卡前 gap 10）',
       _writ.count('PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)') == 2
       and 'PushGap(rows, PD.SEC_GAP + 2, 2)' in _writ
       and 'PushGap(rows, 14, 2)' not in _writ and 'PushGap(rows, 10, 2)' not in _writ)
    ck('★★ CrateMetaRow 支持 fs 透传（正文 14 走单行行口径，双行仍不带 fs）',
       'local function CrateMetaRow(rows, label, val, valOk, fs)' in profui
       and 'kind = "row", col = 2, h = PD.ROW_H1, fs = fs,' in profui)
    ck('★★ 工匠文书卡中卡新文案三语齐全（制造上交所需物的成本 / 总结 / 自己造省 / 直接买便宜）',
       'L["制造上交所需物的成本"] = "製造上交所需物的成本"' in _twl
       and 'L["总结"] = "總結"' in _twl and 'L["直接买便宜"] = "直接買便宜"' in _twl
       and 'L["制造上交所需物的成本"] = "Cost per turn-in"' in _enl
       and 'L["总结"] = "Summary"' in _enl
       and 'L["自己造省"] = "Crafting saves"' in _enl
       and 'L["直接买便宜"] = "Buying is cheaper"' in _enl)
    # ⑤ 配方页分类按钮宽度按文字自适应
    ck('★★ 分类按钮宽度按文字自适应（原定宽 72：长分类名被裁成半截，用户报）',
       'function PD.ToolSize' in profui and 'bt:SetSize(w, PD.TOOL_H)' in profui
       and 'PD.TOOL_MIN_W, PD.TOOL_MAX_W' in profui)
    ck('★ 量宽 / 折行 / 截断共用同一套字符宽度口径（2026-10-09 起 = ns.hui 单实现：专业页 CharStep 别名委托 + TextW 记忆化包装；DungeonUI FitText 走 ns.hui.Fit）',
       'local CharStep = ns.hui.CharStep' in profui
       and 'ns.hui.TextW' in profui and 'hui.TextW(' in hui
       and 'ns.hui.CharStep = HCharStep' in hui
       and 'if H and H.Fit and type(maxw) == "number" and maxw > 0 then' in src)
    # ⑥ 营地页「职业加成」→ 五列对照总表（2026-09-24 方案 A 定稿：warcrafttavern 口径）
    ck('★★ 职业加成 = 五列对照总表（BuildBonusTable 帧一次建全，渲染期只摆位显隐）',
       'function PD.BuildBonusTable(parent)' in profui
       and 'PD.BuildBonusTable(child)' in profui
       and 'PD.wantBonusTable = true' in profui and 'PD.wantBonusTable = false' in profui
       and 'PD.placeBonusTable(h1)' in profui
       and 'function PD.RowsCampBonus' not in profui and 'BuildCampTable' not in profui)
    # ★★ 四合一：对照表改挂总览页（camping + bonus 视图），「营地」页签退役
    _ovslice = profui[profui.index('function PD.RowsOverview'):
                      profui.index('local CAMP_AREA_MAP')]
    ck('★★ 四合一：camping 在总览页直出对照表（Render 举手 wantBonusTable），营地页签退出',
       'wantTable' not in _ovslice
       and 'PD.cur == "camping" then' in profui
       and 'PD.campView = "bonus"' in profui
       and '"camp"' not in profui
       and '营地系统 → 职业加成' not in profui)
    # ⑰ 全部专业总览：三列导航宫格（2026-09-24 方案 B，用户拍板）
    ck('★★ 全部专业总览挂三列导航宫格（帧在 Build 一次建全，渲染期只摆位）',
       'PD.BuildIndexGrid(child)' in profui
       and 'PD.wantIndexGrid = (PD.cur == "__index")' in profui
       and 'PD.wantIndexGrid = false' in profui
       and 'PD.placeIndexGrid(h1)' in profui)
    ck('★★ 总览已学专业卡：绿名 + 右上角等级 + 绿描边（与左列按钮同 NavAccent / 同 ProfLearned 数据源）',
       'function PD.PaintIndexCards' in profui
       and 'PD.PaintIndexCards()' in profui
       and 'c.__ixBorder = bord' in profui
       and 'local IX_EDGE_NORM_A = 0.10' in profui
       and 'c.__slug = slug' in profui)
    ck('★ 总览卡字号 名称16/副行14（旧 12/10；38 高卡装不下 → 卡高 46）',
       'c.name = MakeFS(c, 16, C_TEXT, "LEFT")' in profui
       and 'c.sub = MakeFS(c, 14, C_GREY, "LEFT")' in profui
       and 'PD.IX_CARD_H = 46' in profui
       and 'c.lv:SetPoint("TOPRIGHT", c, "TOPRIGHT", -7, -5)' in profui)
    ck('★★ 「全部专业」页 + 左列按钮退役（2026-10-10 用户）：按钮不再注册，宫格仅存休眠代码路径',
       'navEntry("__index"' not in profui
       and 'PD.wantIndexGrid = (PD.cur == "__index")' in profui
       and 'PD.navKey["__index"]' not in profui)
    ck('★★ 进专业页默认=已学主要专业 + 跨重载记忆上次（slug,tab → DungeonsForeverDB.prof）',
       'function PD.DefaultSlug' in profui
       and 'function PD.EnsureCur' in profui
       and 'db.lastSlug = PD.cur' in profui
       and 'db.lastTab = PD.tab' in profui
       and 'RememberLast()' in profui
       and 'PD.EnsureCur()' in profui)
    ck('★★ 宫格卡走行池同款悬停（状态驱动 + SyncHover 兜底），不另定配色',
       'function PD.SetCardHover(c, on)' in profui
       and 'PD.SetCardHover(c, over)' in profui
       and 'PD.ixRoot:IsVisible()' in profui)
    # ⑱ 四合一：营地段并入 RowsOverview（col=1），联盟/部落坐标同列直出（联盟蓝/部落红）
    ck('★★ 营地段并入总览（物件带悬停明细 + 联盟/部落坐标同列、阵营字体色）',
       '    PushHead(rows, L["营地"], 1)' in profui
       and 'for _, side in ipairs({ "a", "h" })' in profui
       and 'local C_ALLIANCE' in profui and 'local C_HORDE' in profui
       and 'nameColor = fc' in profui
       and 'function PD.RowsCamp' not in profui
       and '对营地系统的贡献' not in profui)
    # ⑳ 总览内容删改（用户）：简介状态行/状态标签说明退役；军需官行换阵营图标并入营地位置
    ck('★★ 总览删简介状态行与状态标签说明（p.status 不再上界面）',
       'text = p.status or L["未标注"]' not in profui
       and 'PushHead(rows, L["状态标签说明"])' not in profui)
    ck('★★ 军需官行：阵营图标 + 组织·区域·地点副行（营地行只在无军需官侧兜底）',
       'PD.FAC_ICON = {' in profui
       and 'icon = PD.FAC_ICON[side]' in profui
       and 'icon = vd[4]' not in profui
       and 'loc = format("%s · %s · %s", tostring(camp[1] or ""),' in profui
       and 'elseif camp then' in profui
       and 'L["营地位置 %.1f, %.1f"]' in profui)
    # ⑲ 国服术语（2026-09-24 用户定）：商人恩惠 → 商人青睐（数据由 fc_gen.py 生成，改词走 zh.json）
    ck('★★ 国服术语「商人青睐」（Data_Professions.lua 不残留「恩惠」）',
       '商人恩惠' not in profdata and '商人青睐' in profdata)
    ck('★ 宫格尾注指路文案随四合一改写（营地页签退役 → 直指「营地系统」）',
       '各专业营地物件的档位对照表在左列' not in profui
       and 'L["营地档位对照表 →「营地系统」"]' in profui)
    ck('★ 页签签名统一 def.text（「职业加成」改名逻辑退役；宫格卡副题仍用该词）',
       'bt:SetText(def.text)' in profui and 'bt:SetText(L["职业加成"])' not in profui
       and '物件 %d · 职业加成' in profui)
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
    ck('★★ 静态映射两区齐备（2026-10-09 起整表挪 Data_AreaMap、UI 取 ns.AreaMap；44 赤脊山→1433 / 17 贫瘠之地→1413 互证值仍在）',
       'local CAMP_AREA_MAP = ns.AreaMap or {}' in profui
       and 'ns.AreaMap = {' in am_src
       and '[44] = 1433' in am_src and '[17] = 1413' in am_src)
    ck('★★ 区域名客户端优先：PD.CampZoneName 现取（GetMapInfoFromAreaID → GetAreaInfo 两级，失败回落数据原文）',
       'function PD.CampZoneName(areaID, fallback)' in profui
       and 'C_Map.GetAreaInfo' in profui
       and 'PD.CampZoneName(camp[6], tostring(camp[2] or ""))' in profui)
    ck('★ 两行都带悬停提示（点击：在地图上标记）',
       'L["点击：在地图上标记该 NPC"]' in profui
       and 'L["点击：在地图上标记此位置"]' in profui)
    # ★★ 2026-09-24 二轮：camping 不再多套一层工具钮 —— 页签直接改名「职业加成」，
    #    三视图切换钮只属于「有自己的营地物件」的专业（bonus 钮收到 hasCamp 分支里，12 空格缩进）。
    ck('★★ 营地页联盟/部落视图切换钮不回潮（训练师页的阵营筛选 chips 属新功能不在此列）',
       'PD.campView = k' not in profui)
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
    ck('★ 间距行（kind == "gap"）也进待建表（非视口路径；视口模式跳过、池空洞安全）',
       'PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true, gen = gen }' in profui)
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
       and 'if r and ((not vis) or i <= syncN) then' in _paintlive)
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
    # ★★ 2026-10-13 用户拍板：圆角超采样体系扩展到 BuildCapsule（胶囊家族）——
    #   四角一律 GLASS_FILL 超采样象限取样（与 BuildRoundedBG 同一体系），
    #   角块尺寸 = 原半径（显示半径不变），贴图档位由 SnapCornerR 就近选。
    ck('★★ HUI 圆角体系统一：BuildCapsule 四角走 GLASS_FILL 超采样象限贴图（旧 4 张角贴图退役）',
       'local GLASS_FILL_TEX = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIGlassFill"' in hui
       and 'local function SnapCornerR(r)' in hui
       and 'local function CornerQuadUV(point, snap)' in hui
       and 'local cornerTex = GLASS_FILL_TEX .. snapR' in hui
       and 'tl:SetTexCoord(CornerQuadUV("TOPLEFT", snapR))' in hui
       and 'tr:SetTexCoord(CornerQuadUV("TOPRIGHT", snapR))' in hui
       and 'bl:SetTexCoord(CornerQuadUV("BOTTOMLEFT", snapR))' in hui
       and 'br:SetTexCoord(CornerQuadUV("BOTTOMRIGHT", snapR))' in hui
       and 'HUI_CORNER_TL' not in hui.split('local function BuildCapsule')[1].split('local pieces')[0])
    ck('★ 控件边框色单一真源：开关边框 = 按钮皮边框（2026-10-13 用户拍板：开关压暗统一）',
       'local C_CTRL_BORDER = {0x4A / 255, 0x52 / 255, 0x63 / 255}' in hui
       and 'local C_TOGGLE_BORDER = C_CTRL_BORDER' in hui
       and 'local C_BORDER = C_CTRL_BORDER' in hui
       and '0.42, 0.42, 0.46' not in hui)
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
    # ★★ 清空必须落在 PD.Render **顶部**、页面派发（if PD.setOpen）**之前**（2026-10-09）。
    #   分帧窗口：购物清单行数多 ⇒ 只排队不建；这期间玩家切到「路线」子页，
    #   PD.PaintRows 末尾那句 `for i=n+1,#PD.rows ... Hide()` 是在**建行之前**跑的，
    #   池子那一刻还是空的 ⇒ 藏不掉还没建的行。若清空挪到派发之后（或删掉），
    #   上一页排下的行就会按上一页的规格被逐批建出来，落在新页上
    #   （实锤：8 专业「购物清单→路线」残留 7~16 行材料）。行为级回归见 _prof_residual_probe.py。
    ck('★ 每轮渲染开头丢掉上一轮排下、还没建的行（否则它们会在新页面上冒出来；须在派发之前）',
       'PD.__pendRows = {}' in _pr
       and _pr.index('PD.secCount = 0') < _pr.index('PD.__pendRows = {}')
       < _pr.index('if PD.setOpen then'))
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
    #   是没有展示出来的」→ 分段行从「一行四样」改成**两行表格**：
    #   上行 区间 | [配方图标] 配方名 | ~N 次制作；下行 来源；右侧材料块（图标 + 名 + ×N）。
    #   ★ 配方名与来源**共用同一个左缘**（PD.LV_NAME_X）—— 两行文字不在一个左缘上整行就散了。
    # ★★★ 五轮（2026-09-24）→ 十轮（2026-10-09 用户）：「我现在每行还是要显示这个
    #   配方的几级变绿、几级变黄」→ 名字下一行（原来源行）改放**四档技能色阶条**
    #   （学 / 黄 / 绿 / 灰），来源压成名字右侧的小卡片。
    #   ★★★ 十一轮（2026-10-09 用户）：「这个竖线，我希望显示两根，显示的位置是
    #   左边这个等级的位置。例如：第一根显示在 36 的位置；第二根显示在 45 的位置。」
    #   → 一根「当前档位」线 → **两根本行技能区间线**（左 = st[1] / 右 = st[2]）。
    #   ★ 统一左缘不变：配方名行与色阶条都锚 PD.LV_NAME_X。
    ck('★★ 升级分段行：名字下一行是四档技能色阶条，来源压成名字右侧卡片（左缘仍 PD.LV_NAME_X）',
       '~%s 次制作' in profui
       and 'r.a:SetText(spec.rng or "")' in profui
       and 'r.e:SetText(spec.text or "")' in profui
       and 'r.c:SetText(spec.cnt or "")' in profui
       # 来源不再写进 r.b：新写法在位、旧写法必须彻底消失（两套并存 = 改了一半）
       and '        r.b:SetText("")' in profui
       and 'r.b:SetText(spec.src or "")' not in profui
       and 'function PD.LvTier(skill, learn, yellow, green, grey)' in profui
       and 'function PD.SBValPos(skill, learn, yellow, green, grey, up)' in profui
       and 'function PD.PaintSkillBar(r, vals, lvLo, lvHi, dim)' in profui
       and 'function PD.HideSkillBar(r)' in profui
       # 2026-10-10：卡片宽全页统一固定（LV_CARD_FIXW），PaintCard 不再收 nameW
       and 'function PD.PaintCard(r, card)' in profui
       and 'function PD.CardOf(rec, ri)' in profui
       # 两条新通道真的接上了
       and 'PD.PaintSkillBar(r, spec.sbVals, spec.sbLo, spec.sbHi, spec.passed)' in profui
       # 2026-10-10：卡片挪到第一列等级（区间）正下方（不跟名字走）
       and 'PD.PaintCard(r, spec.card)' in profui
       and 'PD.LV_CARD_FIXW = math.ceil(cardNeed)' in profui
       and '        r.e:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X, PD.TBL_NAME_DY)' in profui
       and 'bg:SetPoint("LEFT", r, "LEFT", PD.LV_NAME_X + (k - 1) * seg, PD.SB_DY)' in profui)
    # ★★ 十三轮（2026-10-09 用户，贴 85–106 / 阈值 55·85·100·115 的截图）：
    #   「第二根竖线因为 106 已经大于 100 了，那么第二根竖线就要放在 100 的右边」
    #   + 「落在 100 和 115 的交界处，a 大于 85 且小于 100 则落在 55 和 85 交界处」
    #   → 落位口径由「一律吸到所在色块左交界」改成**两头分向吸附**：
    #     · a（起点 lvLo）**向下吸** = 已跨过的交界（最大的 ≤a 的阈值）⇒ 36→0.25、85→0.25
    #     · b（终点 lvHi）**向上吸** = 将要到达的交界（最小的 ≥b 的阈值）⇒ 45→0.50、106→0.75
    #   ⇒ 仍只停 0 / 0.25 / 0.50 / 0.75 四点。PD.SBValPos 增可选参 up（true = 向上吸）。
    #   ★ 向下吸那一支保留原句 `return (t - 1) / 4`（旧锚点不破）；段内插值 PD.SB_VAL 早已退役。
    ck('★★ 色阶条四档等分 + 两根竖线两头分向吸附（起点向下 / 终点向上；36→0.25 / 106→0.75）',
       'PD.SB_COL = {' in profui
       and 'PD.SB_DY = -8' in profui
       and 'PD.SB_EDGE = 4' in profui
       and 'PD.SB_VAL' not in profui
       and '    local seg = PD.LV_NAME_W / 4' in profui
       and 'if grey and skill >= grey then return 4 end' in profui
       and 'if yellow and skill >= yellow then return 2 end' in profui
       and '    return (t - 1) / 4\n' in profui
       and 'local span = (type(hi)' not in profui
       and 'function PD.SBValPos(skill, learn, yellow, green, grey, up)' in profui
       and 'if type(thr[j]) == "number" and skill <= thr[j] then k = j break end' in profui
       and '    local lvs = { lvLo, lvHi }' in profui
       and 'local xa = PD.SBValPos(lvs[1], vals[1], vals[2], vals[3], vals[4], false)' in profui
       and 'local xb = PD.SBValPos(lvs[2], vals[1], vals[2], vals[3], vals[4], true)' in profui
       and 'if xa and xb and xb < xa then xb = xa end' in profui
       and 'p:SetPoint("CENTER", r, "LEFT", PD.LV_NAME_X + x * PD.LV_NAME_W, PD.SB_DY)' in profui
       and 'for k = 1, 2 do r.__sbPin[k]:Hide() end' in profui)
    # ★★ 旧口径必须**彻底退役**（两套并存 = 改了一半，实机看不出哪根生效）。
    #   一根线 / 按档心摆 / spec.sbTier 三样都不许再出现在产品源码里。
    ck('★★ 旧「一根当前档位竖线」彻底退役（不许与两根新线并存）',
       'r.__sbPin:SetPoint' not in profui
       and 'r.__sbPin:Hide()' not in profui
       and 'r.__sbPin = r:CreateTexture' not in profui
       and 'spec.sbTier' not in profui
       and 'PaintSkillBar(r, vals, tier, dim)' not in profui)
    # ★★ 来源卡片三分色 + 悬停 / 点击两条通道。
    ck('★★ 来源卡片三分色（训练师 / 图纸·掉落 / 图纸·商人）+ 悬停 __tipLines / 点击 __act',
       'PD.CARD_COL = {' in profui
       and 'trainer = { 0.29, 0.33, 0.40 }' in profui
       and 'kind = hasDrop and "drop" or (hasVendor and "vendor" or "drop")' in profui
       and 'z.__tipLines = card.lines' in profui
       and 'z.__act = card.act' in profui
       and 'z.__it = card.fid and { card.fid } or nil' in profui)
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
    _rl = profui[profui.index('function PD.RowsLeveling'):profui.index('function PD.RowsSettings')]
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
       and '        PD.tab = "overview"\n        PD.setOpen = false' in profui
       # 设置按钮只属于升级页（2026-10-11 用户）：其它页签整颗收起
       and 'local gon = (PD.tab == "leveling")' in profui
       and 'if PD.setGear.__shown ~= gon then' in profui
       and 'PD.setGear:SetShown(gon)' in profui
       and 'if gon then\n            SetOutline(PD.setGear,' in profui)
    ck('★★ 配方页右缘滚动条（2026-10-11 用户：样式对齐藏品页；L4 只给滑块、轨道 L2，1.5 倍宽）',
       'ns.hui.BuildCapsule(track, 3, ns.hui.layer.L2)' in profui
       and 'ns.hui.BuildCapsule(thumb, 2, ns.hui.layer.L4)' in profui
       and 'track:SetWidth(9)' in profui
       and 'thumb:SetWidth(6)' in profui
       and 'thumb:SetPoint("TOP", track, "TOP", 0, -1)' in profui
       and 'function PD.UpdateVScroll()' in profui
       and 'if PD.setOpen then track:Hide() return end' in profui
       and 'track:SetPoint("TOPLEFT", PD.divider, "TOPLEFT", -4, -2)' in profui
       and 'track:SetPoint("BOTTOMLEFT", PD.divider, "BOTTOMLEFT", -4, 2)' in profui
       and '''scroll:SetScript("OnVerticalScroll", function()
        PD.UpdateVScroll()
        if PD.CullRows then PD.CullRows() end
    end)''' in profui
       and profui.count('if PD.UpdateVScroll then PD.UpdateVScroll() end') >= 2
       and 'PD.scroll:SetVerticalScroll(math.min(maxScroll, math.max(0, sc0 + (cy0 - cy) / span * maxScroll)))' in profui)
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
       and 'PD.truncated = PD.PaintRows(rows)\n    ns.OpenPerf.Mark("首屏")\n    PD.PlaceSettingsToggles(rows)' in profui
       and '            togKey = d.k,' in profui
       and '            tg.__key = spec.togKey' in profui
       and '    PD.setHelps = {}' in profui
       and 'hp:SetPoint("LEFT", rr.a, "RIGHT", 6, -1)' in profui
       and '                hp.__tip = spec.help' in profui
       and '            sub = d.desc,' not in profui
       and 'if d.d1 then PushText(rows, d.d1, 11, C_GREY) end' not in profui
       and 'ProfDB()[self.__key] = not PD.Setting(self.__key)' in profui)
    # ★★ 七轮方案B：材料块**不写物品名**（PD.PackMats 不再量名、PD.PaintMats 不再 SetText(blk.name)），
    #   块宽 = max(图标, N 角标宽)；角标右对齐到块右缘（动作条堆叠数的读法）。
    #   八轮（用户）：「乘号删了」→ 角标只剩裸数字 format("%d", ...)，块宽随之再省一点。
    ck('★★ 方案B：材料块只画「图标 + N 角标」（不写物品名、无乘号；块宽 = max(图标, 角标宽)）',
       'local w = math.max(PD.TBL_ICON, PD.TextW(format("%d", cnt), PD.TBL_MAT_CNT_FS))' in profui
       and '        b.nm:Hide()\n' in profui
       and '        b.ct:SetPoint("RIGHT", r, "RIGHT", -(W - right), PD.TBL_MAT_CNT_DY)\n' in profui
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
       # 2026-10-10：物品通道带惰性价格段 extra（self.__tipExtra，函数先求值）
       and '            DG.ShowItemTip(self, self.__it, extra)\n' in profui
       # 滚轮转发钉**整块**（只钉函数头的话，把 DG.WheelScroll 掏空也抓不到）；
       #   2026-10-10 滚轮先收商人弹窗（弹窗锚着滚动内容，不收就飘）
       and '    z:SetScript("OnMouseWheel", function(self, delta)\n        PD.HideVendorPick()\n        DG.WheelScroll(PD.scroll, PD.child, delta)\n    end)\n' in profui
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
       and 'return table.concat(out, ""), w, n, segs\n' in profui
       and 'function PD.SourceParts(s)' in profui
       and 'out[#out + 1] = { text = format(L["商人：%s"], (v and v.name) or "?"), vendor = true }\n' in profui
       # ★★ 商人阵营过滤（2026-10-10 用户：不止一个商人只显示一个不对、联盟商人显示给部落也不对）
       and 'function PD.VendorListOf(src)' in profui
       and 'local vs = PD.VendorListOf(s)' in profui
       and 'local vs = (r[14] and PD.VendorListOf(r[14])) or {}' in profui
       and 'L["商人：%s 等 %d 人"]' in profui
       and '        if v.side then\n            known = true\n' in profui
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
       and '        vz.__tipLines = spec.vlines or PD.VendorLines(spec.src)\n' in profui
       and '        vz.__act = spec.dact or PD.VendorAct(spec.src)\n' in profui
       # ★★ 商人选择弹窗（2026-10-10 用户：多商人点击弹窗选人再落图，点谁标谁）
       and 'function PD.VendorEntries(s)' in profui
       and '        PD.VendorPickToggle(zone, ents)\n' in profui
       and 'function PD.HideVendorPick()' in profui
       and '    page:HookScript("OnHide", function() PD.HideVendorPick() end)\n' in profui
       and '            PD.HideVendorPick()\n            PD.MarkVendorLoc(e.loc)\n' in profui
       and '    PD.HideVendorPick()\n    if slug ~= PD.cur then' in profui
       and '        PD.HideVendorPick()\n        DG.WheelScroll(PD.scroll, PD.child, delta)' in profui
       and '    PD.ClearMatSegs(r)\n' in profui
       # 反例：材料列不许退回「只画一整串」（那样就没有分段热区可挂）
       and '    if not spec.matSegs then r.f:SetText(spec.mats or "") end\n' in profui)
    ck('★★ 商人弹窗点关盾：点别处收窗 + 滚轮收窗照常滚页（2026-10-10 用户）',
       'pick.__shield = shield' in profui
       and 'shield:SetScript("OnMouseDown", function() PD.HideVendorPick() end)' in profui
       and 'shield:EnableMouseWheel(true)' in profui
       and 'pick.__shield:Hide()' in profui
       and 'pick.__shield:SetFrameLevel(pick:GetFrameLevel() - 1)' in profui)
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
       # 2026-10-10 三列拆分：次数串先按档位拼好（≈/~/·按目标折算），再统一量宽
       and 'local cw = PD.TextW(cntStr, PD.LV_FS)' in profui)
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
    #   ③单行行（魔棒）段已退役（2026-10-12 用户拍板删除）—— 名称列截断只剩 FitName 口径
    ck('★★ 单行行（魔棒）的截断宽与名称列解耦（名称列变窄不许跟着切任务名）',
       'local function FitName(s)\n        return PD.Fit(s, PD.LV_FS, PD.LV_NAME_W)\n    end' in profui
       and 'text = FitName(nm),' in profui
       and 'local function FitL' not in profui)
    # ★★ v3（用户 2026-10-10 B1 改版）：固定路线「需要金币」上移顶部信息卡（cost 卡），
    #    工具行只剩 视图切换 + 重算；lvSummary 由路线 / 购物清单两分支各写一份。
    ck('★★ 升级页 B1 v3：目标裁剪 + 购物清单双模式子页 + lvSummary 两分支齐写',
       'local function ClipFixedSteps(steps, target)' in profui
       and 'local function FixedShopData(target)' in profui
       and 'local data = auto and res or FixedShopData(target)' in profui
       and 'PD.RowsAutoShop(rows, data)' in profui
       and profui.count('PD.lvSummary = {') == 2
       and 'L["图纸（一次性）（%d 个）"]' in profui
       and 'local hd = { kind = "head", text = format(L["1 → %d 分段路线"], target) }' in profui
       and 'if #warn > 0 then hd.warn = warn end' in profui
       # ⚠️ 负向检查查活代码：旧右栏标题不得再出现在活代码里
       and 'PushHead(rows, L["要准备的材料"], 2)' not in profui
       and '商人直接卖的（不用自己攒）' not in _proflive
       and '半成品 / 中间产物' not in _proflive)
    ck('★★ 升级页路线表头六列齐 + 警告改 WarnChip 图标提示框（2026-10-11 用户）',
       'r.a:SetText(L["段落"])' in profui
       and 'r.e:SetText(L["配方"])' in profui
       and 'r.b:SetText(L["材料"])' in profui
       and 'function PD.WarnChip(r, plainTip)' in profui
       and 'wz.__tipLines = spec.warn' in profui
       and 'tex:SetTexture("Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\WarnTri")' in profui
       and 'PushText(rows, format(L["含无价材料 %d 种：花费为估算下限"], np), 12,' not in profui)
    ck('★★ 升级页路线标题移工具行 + 感叹号居中 + 警告芯片跨页残留清零（2026-10-11 用户三轮）',
       # 标题改暂存：自动路线分支不再推 head 行，改写 PD.lvRouteHead
       'PD.lvRouteHead = {\n                text = format(L["1 → %d 自动路线（按拍卖行价格）"], target),' in profui
       and 'if tool and PD.lvRouteHead then' in profui
       and 'tool[#tool + 1] = { key = "route_head", plain = true,' in profui
       and '    PD.lvRouteHead = nil\n\n    local _learned = PD.ProfLearned()' in profui
       and '    PD.ResetItemNameMemo()\n    PD.lvRouteHead = nil' in profui
       # PaintTool plain 分支：宽不钳制 / 无描边白字 / 禁点 / 芯片右挂
       and 'w = math.ceil(PD.TextW(def.text, 12)) + 6' in profui
       and 'bt:EnableMouse(false)' in profui
       and 'local wz = PD.WarnChip(bt, true)' in profui
       and 'wz:SetPoint("LEFT", bt, "RIGHT", 2, 0)' in profui
       # WarnChip：警告图标改自绘贴图 WarnTri（2026-10-11 用户拍板方案 C）+ 工具行独立提示框（Button 宿主禁 SetRowHover）
       and 'tex:SetSize(18, 18)' in profui
       and 'tex:SetPoint("CENTER", z, "CENTER", 0, 0)' in profui
       and 'z:SetScript("OnLeave", function() GameTooltip:Hide() end)' in profui
       # 行池回收警告芯片（跨页残留）
       and 'if r.__warn then r.__warn:Hide(); r.__warn.__tipLines = nil end' in profui)
    ck('★★ 升级页 B1：四张信息卡 Build 一次建好 + PaintLvTiles 刷新（tgtBox 退役）',
       'PD.LV_TILE_H, PD.LV_TILE_GAP = 38, 8' in profui
       and 'PD.lvTiles[td.key] = tf' in profui
       and 'ns.hui.BuildRoundedBG(tf, 6' in profui
       and 'tf.__hov = ns.hui.BuildCapsule(tf, 8, ns.hui.layer.L4, 1, 2)' in profui
       and 'PD.RIGHT_X + PD.RIGHT_W - PD.LIST_PAD, -PD.SUB_Y)' in profui
       and 'PD.RIGHT_X + PD.RIGHT_W, -PD.SUB_Y)' not in profui
       # 帧级右锚统一内缩 LIST_PAD（2026-10-10 用户截图：搜索框/HUD/快照卡压外卡描边）
       and '-(PD.CARD_INSET + PD.LIST_PAD), -(PD.BODY_TOP + PD.LV_TILE_H + 8))' in profui
       and '-(PD.CARD_INSET + PD.LIST_PAD), -(PD.BODY_TOP))' in profui
       # 信息卡五卡均分（2026-10-10 用户：加路线方案卡，第二位）；余数给快照卡
       # 毒药页四卡变体（2026-10-11 用户）：固定路线专用，方案卡隐藏，n 张等分
       and 'local usable = PD.RIGHT_W - PD.LIST_PAD - (n - 1) * PD.LV_TILE_GAP' in profui
       and 'local tw = math.floor(usable / n)' in profui
       and 'tf:SetWidth(usable - (n - 1) * tw)' in profui
       and 'layout = { "mode", "cost", "target", "snap" }' in profui
       and 'TileFit(' not in profui
       and 'function PD.PaintTileBorder' in profui
       and profui.count('PD.secGoldCards[i]:Hide()') == 2
       and 'function PD.PaintLvTiles' in profui
       and 'PD.PaintLvTiles() + PD.PaintTool(tool, handler, PD.LV_TILE_H + 8)' in profui
       and 'PD.tgtBox' not in profui
       and 'key = "fixed"' not in profui and 'key = "auto"' not in profui
       and 'PD.impBtn:SetShown(wantImp and true or false)' in profui
       and 'L["需要金币 %s"]' not in profui)
    # ★★ 快照时间用「真实扫描时间戳(秒)」而不是被误读成分钟的「天」级 API（2026-10-10）
    ck('★★ 快照年龄取真实扫描时间戳（Auctionator.SavedState.TimeOfLast*Scan，秒级）',
       'local function SnapshotSec()' in profra
       and 'Auctionator' in profra
       and 'TimeOfLastGetAllScan' in profra
       and 'TimeOfLastReplicateScan' in profra
       and 'TimeOfLastBrowseScan' in profra
       and 'snapshotAge = SnapshotSec()' in profra
       and 'snapshotDays = priceCache.__minAge' in profra
       # 旧的「天 × 1440 当分钟用」必须彻底消失（快照把人坑过一轮，钉死）
       and '1440' not in profra
       and '1440' not in profui)
    ck('★★ 卖店价只缓存成功值（未加载不再钉死 0，产物到货后重算）',
       'if p then sellCache[id] = p end' in profra
       and 'sellCache[id] = p or false' not in profra
       and 'local function RequestProduct(id)' in profra
       and 'RequestProduct(prod)' in profra
       and 'if RA then RA.Invalidate() end' in profui)
    # ★★ 购物清单「产物收益」金卡与上方「总共需要」金卡之间的净距 = 8（PD.SEC_GAP 标准）。
    #   相邻两张 sec 金卡：净距 = gap + 2 − 2*SEC_PAD ⇒ gap = SEC_GAP + 2*SEC_PAD − 2 = 14。
    #   不得写成硬编码间距数；也不得改用 PD.OV_GUT（那是跨列/组间外槽，净距会变成 10）。
    ck('★★ 购物清单两张金卡净距 = 8 标准（gap = SEC_GAP + 2*SEC_PAD − 2，无硬编码数）',
       'PushGap(rows, PD.SEC_GAP + 2 * PD.SEC_PAD - 2, 2)\n        PushHead(rows, L["产物收益"], 2)' in profui
       and 'PushGap(rows, 10,' not in profui
       and 'PushGap(rows, PD.OV_GUT, 2)\n        PushHead(rows, L["产物收益"], 2)' not in profui
       and 'PD.SEC_GAP = 8' in profui
       and 'PD.OV_GUT = PD.SEC_GAP + 2 * PD.SEC_PAD' in profui)
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
    ck('★★ 新配方副行「类型」左边带绿色「新」字（2026-10-10 用户：从名称行尾移来）',
       '|cff40d940新|r' in profui
       and 'spec.is_new and L[" |cff40d940新|r"] .. " "' in profui
       and '(spec.text or "") .. (spec.is_new and L[" |cff40d940新|r"] or "")' not in profui)
    ck('★★ 名称↔材料列间距压缩：PAD 44→16 + 角标迁副行（名称/副行扫描各归各）',
       'PD.RECIPE_NAME_PAD = 16' in profui
       and 'local sw = PD.TextW(s.sub or "", 11) + (s.is_new and PD.RECIPE_BADGE_W or 0)' in profui
       and 'local sw = PD.TextW(PD.KitSub(tostring(r[5] or ""), r[6]), 11) + (r[11] and PD.RECIPE_BADGE_W or 0)' in profui
       and 'if s.is_new then w = w + PD.RECIPE_BADGE_W end' not in profui
       and 'if r[11] then w = w + PD.RECIPE_BADGE_W end' not in profui)
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
    #   2026-10-10 用户：数量不再写「N×」前缀 → 压图标右下角徽标（MatCnt），列宽少量一次数字
    ck('★★ 材料列宽公式不再含数量前缀（数量改压图标徽标）',
       'function PD.MatCol' in profui and 'local cw = px + PD.TextW(name, fs)' in profui
       and 'PD.TextW(cnt, fs)' not in profui and 'format("%d×", m[2] or 1)' not in profui
       and 'PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui)
    ck('★★ 材料数量徽标：压图标右下角 + 白字黑描边黑阴影（2026-10-10 用户）',
       'function PD.MatCnt(r, i)' in profui
       and 'r.mcnt = r.mcnt or {}' in profui
       and 'r.mc and' not in profui and 'r.mc =' not in profui and 'r.mc[' not in profui
       and 'c:SetPoint("BOTTOMRIGHT", fs, "BOTTOMLEFT", PD.MAT_ICON_PX - 1, 1)' in profui
       and 'c:SetShadowColor(0, 0, 0, 1)' in profui
       and 'c:SetShadowOffset(1, -1)' in profui
       and "c:SetFont(f, s, \"OUTLINE\")" in profui
       and 'segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece }' in profui
       and 'PD.MatCnt(r, i)' in profui)
    ck('★★ 材料段链零间距 + 徽标锚定（段文本不带前导空格，徽标才钉得住图标左缘）',
       'fs:SetPoint("LEFT", prev, "RIGHT", 0, 0)' in profui
       and 'local gap, px = 0, PD.MAT_ICON_PX' in profui
       and '{ text = "  …" }' not in profui and '{ text = "…" }' in profui
       and 'c:SetText("")' in profui)
    ck('★★ 材料末段「图标+截断名」不整段丢弃（2026-10-10 截图红框：右缘留白）',
       'local avail = budget - w - gap - px' in profui
       and 'local piece2 = PD.MatIconTex(m[1], px) .. PD.Fit(name, fs, avail)' in profui
       and 'segs[#segs + 1] = { id = m[1], cnt = m[2] or 1, text = piece2 }' in profui
       and 'PD.MAT_TAIL_MIN' in profui)
    ck('★★ 配方行副行只剩部位等级（材料已搬进材料列）',
       'sub = PD.KitSub(tostring(r[5] or ""), r[6])' in profui
       and 'PD.MatCol(r[12], PD.MAT_FS, PD.MAT_W)' not in profui
       and 'PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui)
    ck('★★ 护甲片副行改写 KitSub（2026-10-15 用户：要求30级 耐力+4 护甲+32）',
       'function PD.KitSub(sub, desc)' in profui
       and '"^永久附着"' in profui
       and '，(%d+)%s*[级級]' in profui
       and 'PD.KIT_STAT_PATS' in profui
       and 'format(L["要求%d级"], tonumber(lv))' in profui)
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
       _otc is not None and 'PD.searchQ = t' in _otc
       and ('PD.RequestRender()' in _otc or 'PD.Render()' in _otc))
    ck('★★ 搜索按纯文本匹配（用户输入当字面量，不吃 Lua 模式字符；名称/副行/材料三路都查）',
       'function PD.SearchHit' in profui and 'function PD.SearchFilter' in profui
       and profui.count(', q, 1, true)') >= 3)
    ck('★★ 工具行给搜索框让位（首行右端留白，分类芯片不压搜索框）',
       'function PD.SearchReserve' in profui
       and 'PD.RIGHT_W - ((row == 0) and PD.SearchReserve() or 0)' in profui)
    # ★★ 2026-10-10 UI_RULES 审计（配方页 + 升级页，用户定规则回查）：
    #   ① 搜索框坐在 L1 大卡（listCard）里 → 内卡必须提亮 L2（与信息卡/分区卡同口径）；
    #   ② 页签胶囊按钮↔按钮 = 8（SUB_STEP = SUB_W + 8 = 78，旧 74 = 缝 4 违标）；
    #   ③ 升级页「路线|购物清单」切换组间距走默认 TOOL_GAP=8，不许写死 2/14
    #     （对齐掉落页 LOOT_VIEW_GAP「4 → 8」同款先例）。
    ck('★★ 专业页卡中卡提亮 + 按钮间距 8（搜索框 L2 / 页签胶囊 78 / 切换组不写死 2·14）',
       'BuildRoundedBG(seb, 6, ns.hui.layer.L2' in profui
       and 'BuildRoundedBG(seb, 6, ns.hui.layer.L1' not in profui
       and '22, 70, 78' in profui
       and 'on = PD.autoPage ~= "shop" }' in profui
       and 'gap = 2 },' not in profui
       and 'gap = 14 },' not in profui)
    ck('★★ 名称列按本页现算（量本页最宽名称/副行，剩余全给材料列；固定分割只在加载期兜底）',
       'function PD.FitRecipeCols' in profui
       and 'PD.MAT_X = nameW + PD.RECIPE_NAME_PAD' in profui
       and 's.mats, _, _, sg = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W)' in profui
       and 'PD.SearchFilter(PD.RecipeList())' in profui)
    ck('★ 名称截断预算双口径（随列宽 MAT_X-8-32；列宽被钳住的短名页退回 nameW-6 防新增截断）',
       'PD.RECIPE_PADL = 32' in profui
       and 'PD.Fit(s.text, 13, math.max(PD.MAT_X - 8 - PD.RECIPE_PADL,' in profui
       and '(PD.RECIPE_NAME_W or 0) - 6))' in profui
       and 'nameW - (s.is_new and PD.RECIPE_BADGE_W or 0)' not in profui)
    ck('★★ 配方/可制造名称按产物物品品质着色（qItem + 会话缓存 QualCached；无品质退默认色）',
       'function PD.QualCached' in profui
       and 'qItem = r[2],' in profui and 'qItem = c[2],' in profui
       and 'if not ncol and spec.qItem then' in profui
       and 'if q then ncol = { DG.QColor(q) } end' in profui)
    ck('★★ 材料段名按材料品质着色（附魔/可制造也挂 matSegs；…纯段无 id 保持默认）',
       'if q then scol = { DG.QColor(q) } end' in profui
       and 'fs:SetTextColor(Unpack(scol))' in profui
       and profui.count('matSegs = matSg,') == 2)
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
    # ---- ★★ 2026-10-10 自动路线方案化（用户：默认最省钱；方案卡第二位）----
    ck('★★ 自动路线方案化：四方案/标签/Compute 兜底最省钱/缓存键含 scheme/结果带 scheme',
       '"cheapest", "matcost", "crafts", "optim"' in profra
       and 'function RA.SchemeOrder' in profra
       and 'if scheme == nil or not SCHEME_LABEL[scheme] then scheme = "cheapest" end' in profra
       and 'tostring(opts.scheme)' in profra
       and profra.count('        scheme = scheme,\n') >= 1)
    ck('★★ 最省钱指标计入图纸价（已学免费/取不到按 0）；乐观计数提前学习线+收益恒 1+排冷却/未公开',
       'fcost = MatPrice(f[1], soldSet) or 0' in profra
       and 'if scheme == "cheapest" then' in profra
       and 'return c.cost / g + (c.fcost or 0) / span' in profra
       and 'local span = math.max(1, (c.grey or 0) - (c.learn or 0))' in profra
       and 'if scheme == "optim" then return 1 end' in profra
       and 'math.max(1, math.min(learn, cY - 25))' in profra
       # 最省钱忽略排除开关（否则两方案恒等）；其余方案维持语义
       and 'opts.noFormula and opts.scheme ~= "cheapest"' in profra
       and profra.count('c.cd or c.unknown') >= 2
       and profra.count('(c.learnO or c.learn)') >= 3
       and 'if c then st.cost = (c.base or 0) * (st[4] or 0) end' in profra)
    ck('★★ 升级页方案卡第二位 + 五卡均分 + 点击循环切换',
       profui.count('{ key = "scheme", w = 150 },') == 1
       and '"mode", "scheme", "cost", "target", "snap"' in profui
       and '(n - 1) * PD.LV_TILE_GAP' in profui
       and 'math.floor(usable / n)' in profui
       and 'ProfDB().autoScheme = order[ni]' in profui)
    ck('★ 方案默认最省钱 + 乐观计数不依赖价格插件（页面与 HUD 门槛都放宽）',
       'PD.SETTING_DEF.autoScheme = "cheapest"' in profui
       and 'scheme ~= "optim"' in profui
       and '(scheme == "optim" or RA.Available())' in profui
       and pfhud.count('scheme == "optim"') >= 2
       and 'PD.SettingRaw("autoScheme")' in pfhud)
    ck('★★ 采集升级路线页（2026-10-11）：四采集 slug 开页签 + 静态路线 + 三卡 + 绿色定位',
       'PD.GATHER_SLUGS = { mining = true, herbalism = true, skinning = true, fishing = true }' in profui
       and 'function PD.RowsGatherRoute' in profui
       and 'function PD.PaintGatherTiles' in profui
       and 'if PD.GATHER_SLUGS[PD.cur] then return PD.PaintGatherTiles() end' in profui
       and 'or (PD.GATHER_SLUGS and PD.GATHER_SLUGS[slug]) then out[#out + 1] = "leveling" end' in profui
       and 'local TipOn = PD.TipTile' in profui
       and 'function PD.TipTile' in profui
       and profui.count('if hi < lo then hi = lo end') >= 2
       and '按技能门槛分档推进：下竿必涨，到下一档门槛就换区域。' in profui
       and '当前技能 %d，绿色为推荐段：采到区间上缘再换下一段。' in profui
       # 采矿双模式（2026-10-11 用户）：采集/熔炼切换 + 熔炼表 + 上游样式副行
       and 'local SMELT_TBL = {' in profui
       and '{ 2840, 1 }, { 3576, 65 }, { 2841, 75 }, { 2842, 75 }, { 3575, 125 },' in profui
       and 'function PD.GatherMode(slug)' in profui
       and 'if PD.GatherMode(slug) == "smelt" then' in profui
       and 'ProfDB().gatherMode = smelt and "gather" or "smelt"' in profui
       and 'loc = format(L["大多在 %s"], PD.ZoneText(zones)),' in profui
       and 'L["点击切换：采集 ⇄ 熔炼"]' in profui)
    ck('★★ 采集路线三列行 + 相邻合并（2026-10-11 用户可视化方案拍板：等级 | 地点 | 图标+矿名）',
       # 三列行渲染分支（BindRow gr3）：等级左、地点中、图标定列 + 矿名跟图标右侧
       'if spec.gr3 then' in profui
       and 'r.a:SetPoint("LEFT", r, "LEFT", PD.GR_LV_X, 0)' in profui
       and 'r.b:SetText(spec.loc or "")' in profui
       and 'r.b:SetPoint("LEFT", r, "LEFT", PD.GR_LOC_X, 0)' in profui
       and 'r.c:SetText(""); r.c2:SetText(""); r.d:SetText(""); r.f:SetText("")' in profui
       and 'r.e:SetPoint("RIGHT", r, "RIGHT", -6, 0)' in profui
       and 'r.icon:SetPoint("RIGHT", r.e, "LEFT", -6, 0)' in profui
       # 第三列纯图标（2026-10-11 用户：采药/采矿只放图标，名字退役；剥皮仍图标+名）
       and 'r.gic = {}' in profui
       and 'if r.gic then for _, g in ipairs(r.gic) do g:Hide() end end' in profui
       and 'if spec.icons then' in profui
       and 'for k = 1, #r.gic do' in profui
       and 'g:SetPoint("RIGHT", r.gic[k - 1], "LEFT", -4, 0)' in profui
       and 'icons = (slug == "herbalism" or slug == "mining") and ids or nil,' in profui
       and 'PD.GR_LOC_X = 88' in profui
       and 'PD.GR_ICON_W = 20' in profui
       # 行构造：三列字段（lv/loc），等级区间进第一列
       and 'kind = "row", h = PD.ROW_H1, gr3 = true,' in profui
       and 'lv = (hi > lo) and format(L["%d - %d"], lo, hi) or tostring(lo),' in profui
       # 相邻合并：产物与分布一致 → 并一行区间贯通（用户拍板「合并」）
       and 'local function GrSameSeg(a, b)' in profui
       and 'and PD.ZoneText(zones) == PD.ZoneText(nx[3])) then break end' in profui
       and 'if nx[1][1] ~= t[1][2] + 1 then break end' in profui
       # 剥皮等级列按上游映射为技能区间（1；10-100；105-150；155-200；205-250；255-300）
       and 'local SKIN_SKILL = { [1] = { 1, 1 }, [11] = { 10, 100 }, [21] = { 105, 150 }, [31] = { 155, 200 }, [41] = { 205, 250 }, [51] = { 255, 300 } }' in profui
       and 'local rng = SKIN_SKILL[t[1][1]] or { t[1][1], t[1][2] }' in profui
       and 'lo, hi, ids, zones = rng[1], rng[2], t[2], t[3]' in profui
       and 'hi = (SKIN_SKILL[nx[1][1]] or { nil, nx[1][2] })[2]' in profui)
    ck('★★ 快照紧贴文案+24h 天化 / 熔炼三列 / 采药同档合并（2026-10-11 用户三轮）',
       # 快照：时间与插件名紧贴（·退役），超 24 小时直接 X 天前
       'L["%d 小时前Auctionator"]' in profui
       and 'elseif snapSec < 24 * 3600 then' in profui
       and ' · Auctionator' not in profui
       # 熔炼行同款三列（左等级 / 右图标+名称，中列留空）——smelt 与 gather 两处 gr3
       and 'lv = rng,' in profui
       and profui.count('gr3 = true,') >= 2
       # 采药/采矿区间合并（2026-10-11 用户拍板，取代旧同档合并）：HERB_GRP/MINE_GRP 分组 + t[5] 区间
       and 'if slug == "herbalism" or slug == "mining" then' in profui
       and 'local HERB_GRP = { { 1, 50 }, { 50, 100 }, { 100, 150 }, { 150, 205 }, { 205, 230 }, { 230, 270 }, { 270, 300 } }' in profui
       and 'local MINE_GRP = { { 1, 65 }, { 65, 125 }, { 125, 175 }, { 175, 245 }, { 245, 300 } }' in profui
       and 'if last and last[5] == GrpOf(t[2]) then' in profui
       and 'merged[#merged + 1] = { t[1], t[2], t[3], nil, GrpOf(t[2]) }' in profui
       and 'lo, hi = t[5][1], t[5][2]' in profui
       and 'while not t[5] and g[gi + 1] do' in profui
       and 'last[4] = true' in profui
       and 'nm = table.concat(nms, "、")' in profui)
    ck('★ 方案卡收显 + 字符串读取（2026-10-11 截图两 bug 防回潮）',
       # 残留：其它签/设置面板的 Hide 列表必须含 scheme（曾漏 → 切页残留）
       '{ "mode", "scheme", "cost", "target", "snap" }) do tiles[k]:Hide() end' in profui
       # 点击不切换：autoScheme 是字符串，必须走 SettingRaw（PD.Setting 布尔口径会吃掉 "optim"）
       and 'function PD.SettingRaw(k)' in profui
       and profui.count('PD.SettingRaw("autoScheme")') == 2
       and 'local cur = PD.SettingRaw("autoScheme")' in profui
       # PD.Setting 本体保持布尔口径（老布尔开关调用方零波及）
       and 'return v and true or false' in profui
       # HUD 读取也走 SettingRaw
       and 'PD.SettingRaw and PD.SettingRaw("autoScheme")' in pfhud)

    # ---- ★★ 2026-10-09 变异重锚收尾：孤儿变异的配对静态断言 ----
    # 这些变异此前没有配对断言（或配对断言随重构过时），注入后零新增红 = 没人守。
    # 口径：钉住变异锚点行的存在性/计数 —— 基线全绿、注入变异必红（非恒真）。
    ck('★ 攻略页签在二级页签表里（key = "guide" 入口不被摘除）',
       _dui.count('key = "guide"') == 1)
    ck('★ 攻略页签激活时掉落滚动区让位（not isGuide 参与显隐判断）',
       _dui.count('SetShown(not isQuest and not isGuide and not isMap)') == 2)
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

    ck('★ locale 里也删掉了「站点掉率」文案',
       '站点掉率' not in open(os.path.join(ADDON, 'Locales', 'zhCN.lua'),
                             encoding='utf-8').read())
    ck('★ 缓存态提示框走 GameTooltip:SetHyperlink（掉落清单同源取值；SetItemByID 未缓存会同步装载已弃用）',
       'pcall(GameTooltip.SetHyperlink, GameTooltip, "item:" .. tostring(id))' in tipcode
       and 'pcall(GameTooltip.SetItemByID, GameTooltip, id)' not in tipcode)
    ck('★★ 末行判据可证伪：Instant 有值才承诺「加载中」，否则直言未收录',
       'if id and DG.ItemInfoInstant(id) then' in tipcode
       and 'L["客户端详细数据加载中，稍后自动刷新"]' in tipcode
       and 'L["客户端未收录此物品"]' in tipcode)

    # ---- 物品数据「请求得出去」的活代码不变量 ----
    # ★★ 2026-09-22 实机事故：请求发不出去 → `/tf qual` 实测 1807 件、到货 0 件 →
    #    卡片永远停在站点口径（用户看到「插件绿色 / 游戏蓝色」）。三路齐发就是修复本身。
    # 断言收窄到 RequestItem 自己的函数体：PrewarmLoot 里也有 EnsureItemListener，
    # 不收窄的话「删掉 RequestItem 里那行」会被 PrewarmLoot 的同名调用掩盖。
    reqseg = tipcode[tipcode.index('function DG.RequestItem'):
                     tipcode.index('function DG.EnsureItemListener')]
    ck('★★ 请求三路①：C_Item.RequestLoadItemDataByID（现代端官方入口）',
       'C_Item.RequestLoadItemDataByID' in reqseg)
    ck('★★ 请求三路②：裸调取数口（全局优先、C_Item.GetItemInfo 兜底）',
       'GetItemInfo or (C_Item and C_Item.GetItemInfo)' in reqseg
       and 'pcall(fn, id)' in reqseg)
    ck('★★ 请求三路③：到货统一重刷（官方异步回调 → RefreshItemCards 经 C_Timer 去抖）',
       'DG.ContinueOnItemLoad(id, function() DG.RefreshItemCards(id) end)' in reqseg
       and 'DG.__rcT = C_Timer.NewTimer(0.1' in tipcode)
    ck('★ 请求路径自己保证到货监听器就位（谁先发起请求都能重刷）',
       'DG.EnsureItemListener()' in reqseg)
    ck('★ 隐藏 tooltip 兜底已退役（不建任何隐藏提示框；取名统一走缓存 + 事件重刷）',
       'DG.__warmTip' not in tipcode
       and 'CreateFrame("GameTooltip"' not in tipcode)
    ck('★ 到货重刷去抖（__rcT 未清空前不重复排程）',
       'if DG.__rcT then return end' in tipcode
       and 'DG.__rcT = nil' in tipcode)
    # ★★ 第④路：官方异步口。暴雪整个 Lua 侧从不调用 C_Item.RequestLoadItemDataByID
    #    （全源码零命中）—— 加载请求是 C 端在 tooltip / 异步回调（ItemEventListener
    #    → ASYNC_ITEM）管线里自己发的。所以这一路才是「一定会发」的那条。
    ck('★★ 请求第④路：官方异步口 Item:CreateFromItemID + ContinueOnItemLoad',
       'DG.ContinueOnItemLoad(id, function() DG.RefreshItemCards(id) end)' in reqseg
       and '_G.Item.CreateFromItemID' in tipcode
       and 'item.ContinueOnItemLoad, item, cb' in tipcode)
    ck('★ 预热对「名字还没到货」的物品强制重请（客户端缓存会被驱逐）',
       'DG.RequestItem(it[1], not hasName)' in tipcode)

    # ---- ★★ 名字「到不了货」时怎么补救（用户诉求：不能只有图标没有名字） ----
    # 实机症状：整页卡片都是「图标 + 部位 · 子类 + 掉率」，名字全是占位。图标/部位走的是
    # GetItemInfoInstant（静态数据、随叫随有），名字走 GetItemInfo（要等详细数据到货）——
    # 所以「图标有、名字没有」= 到货那一步没接住，不是取数口错。两手补救：双事件 + 定时重扫。
    ck('★★ 同时监听官方异步到货事件 ITEM_DATA_LOAD_RESULT（载荷同 GET_ITEM_INFO_RECEIVED）',
       'pcall(ev.RegisterEvent, ev, "ITEM_DATA_LOAD_RESULT")' in tipcode,
       '有 ITEM_DATA_LOAD_RESULT' if 'ITEM_DATA_LOAD_RESULT' in tipcode else '缺 ITEM_DATA_LOAD_RESULT')
    ck('★★ 打开详情后按时间点重扫（数据慢到几秒也不至于永远停在占位）',
       'DG.ScheduleNameSweep()' in tipcode
       and 'DG.SWEEP_AT = { 0.5, 1.5, 4, 9 }' in tipcode
       and 'C_Timer.After(t, function() DG.SweepMissingNames() end)' in tipcode)
    ck('★ 重扫用 C_Timer（不新增常驻帧，也不打乱「首屏新建帧数」那类断言）',
       'type(C_Timer) ~= "table"' in tipcode)
    ck('★ 重扫只碰「名字还没到货」的卡（带 __named 的跳过，别每轮白刷）',
       tipcode.count('if it and not c.__named then') == 2
       and 'DG.PaintItemRow(c, it[1])' in tipcode)
    ck('★★ 名字收割走 __tipName 缓存（同步口命中即落缓存，未命中补请求）',
       'function DG.HarvestTipName' in tipcode
       and 'if not c.__named and DG.HarvestTipName then' in tipcode
       and 'local nm = DG.HarvestTipName(it[1])' in tipcode
       and 'cache[id] = { nm, r, g, b }' in tipcode)
    ck('★ 取名自愈：失败拉黑 __tipDead 防自激 + 用户可 dfNoTipWarm 关掉整条管线',
       'DG.__tipDead' in tipcode
       and 'DungeonsForeverDB.dfNoTipWarm' in tipcode)
    ck('★ 卡上记 __named 标记（到货后就不再重扫这张）',
       'c.__named = hasName' in tipcode)
    allcode = '\n'.join(l.split('--')[0] for l in src.split('\n'))
    ck('★ 绑定卡片时也记 __named（卡片会被复用，每次绑定都要重记）',
       'r.__named = hasName' in allcode)

    # （上游此处有「/tf qual、/tf item 命令族」的一组断言，依赖 Core/Sim.lua。
    #   本插件没有模拟器模块，故整段不搬；物品取数路径的不变量仍由
    #   上面的 DG.RequestItem / DG.EnsureItemListener 断言与动态段覆盖。）


    # ---------- 静态：掉落卡片墙（3 列 · 双行卡） ----------
    # 用户诉求：原来「名字靠左、部位靠右」中间空一大截 → 每件一张卡、一行排 3 张。
    seg_render = src[src.index('function U:RenderDungeonLoot'):src.index('function U:RenderDungeonLootCards')]
    rcode = '\n'.join(l.split('--')[0] for l in seg_render.split('\n'))
    ck('卡片底色 + 1px 描边走 Backdrop（引擎自带、不占 region）',
       'r:SetBackdrop({' in rcode and 'edgeSize = 1' in rcode)
    ck('★ 卡片悬停提亮（改色不改结构）',
       'SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG_HOVER)' in rcode
       and 'SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE_HOVER)' in rcode)
    # 常态色复位应出现 3 处：OnLeave 还原 + 「暂无掉落数据」占位卡 + 物品卡每轮刷新
    ck('★ 常态底色复位 3 处（OnLeave / 占位卡 / 每轮刷新）',
       rcode.count('SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)') == 3,
       rcode.count('SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)'))
    ck('卡片仍走常驻池（takeRow 从 rows 池取行，不每轮新建）',
       'takeRow' in rcode and 'local r = rows[idx]' in rcode)
    ck('★ 卡片行不重建 scroll child、不用 SetParent',
       'SetScrollChild' not in rcode and 'SetParent' not in rcode)
    # 品质色：站点 dungeons.json 的 q 是第三方口径、实测不准（6465「水蛇法袍」站点 2 绿 /
    # 游戏内 3 蓝，全库 1807 件里 444 件不一致）→ 2026-09-22 起**整体弃用**，只认客户端。
    ck('★★ 卡片文字全走客户端口径（名字 / 品质 / 部位）',
       'DG.ItemName(it[1])' in rcode and 'DG.ItemMeta(it[1])' in rcode
       and 'DG.QColor(DG.QualOf(it[1]))' in rcode)
    ck('★★ 名字取不到时用占位文案（不回退站点名）',
       'return L["暂时没有客户端数据"], false' in src)
    ck('★★ 卡片分类走客户端 classID（不再看站点部位中文串）',
       'DG.CatOf(it[1])' in rcode and 'it[4]' not in rcode)
    qseg = src[src.index('function DG.QualOf'):src.index('function DG.NsCall')]
    qcode = '\n'.join(l.split('--')[0] for l in qseg.split('\n'))
    ck('★ 品质只认客户端：异步取数口 → 同步口，都不行回 nil',
       'local _, _, q = DG.ItemInfo(id)' in qcode
       and 'DG.NsCall("GetItemQualityByID", id)' in qcode
       and 'return nil' in qcode)
    ck('★★ 站点品质彻底弃用（QualOf 不再有 fallback 形参）',
       'function DG.QualOf(id, fallback)' not in src
       and 'return fallback' not in src
       and 'DG.QualOf(it[1], it[3])' not in src)

    # ---------- 客户端物品数据取数口（本端 GetItemInfo 不在全局表里） ----------
    # 实机 `/tf qual` 体检（2026-09-22）：GetItemInfo 无 / GetItemInfoInstant 无，
    # 而 C_Item.RequestLoadItemDataByID 有 / C_Item.IsItemDataCachedByID 有
    # → 这两个取数函数只挂在 C_Item 命名空间下。裸调全局恒回 nil **且不报错**，
    #   品质、图标、到货判据因此全部静默失效 —— 同一个根因同时造成
    #   「卡片颜色永远停在站点口径」与「/tf qual 说客户端已知 0 件」。
    apiseg = src[src.index('function DG.ItemInfo'):src.index('function DG.NsCall')]
    apicode = '\n'.join(l.split('--')[0] for l in apiseg.split('\n'))
    ck('★★ 取数口自适应①：全局 GetItemInfo 优先、C_Item.GetItemInfo 兜底',
       'GetItemInfo or (C_Item and C_Item.GetItemInfo)' in apicode)
    ck('★★ 取数口自适应②：Instant 同理（图标靠它同步取）',
       'GetItemInfoInstant or (C_Item and C_Item.GetItemInfoInstant)' in apicode)
    ck('取数口对「非函数」也安全（桩环境常把它塞成非函数）',
       apicode.count('if type(fn) ~= "function" then return nil end') == 2,
       apicode.count('if type(fn) ~= "function" then return nil end'))
    ck('★ 体检/探针能报出「实际生效的取数口」',
       'function DG.ItemApiName()' in apicode)
    # ★★ 全文件不变量：任何地方都不许再裸调全局取数口 —— 本端它们是 nil。
    #    只按「调用形态」（带括号）判，免得误伤 `GetItemInfo or (...)` 这种取函数引用的写法。
    uiall = '\n'.join(l.split('--')[0] for l in src.split('\n'))
    simall = ''  # 本插件无 Core/Sim.lua；全文件级检查由 uiall 承担
    ck('★★ 全文件没有裸调全局 GetItemInfo(...) / GetItemInfoInstant(...)',
       'GetItemInfo(id)' not in uiall and 'GetItemInfoInstant(id)' not in uiall
       and 'GetItemInfo(id)' not in simall and 'GetItemInfoInstant(id)' not in simall)

    # ---------- 物品数据来源不变量（站点物品属性整体弃用） ----------
    # 2026-09-22 用户决定：站点口径不准，物品的一切属性只从客户端取。这几条守住
    # 「别哪天又悄悄把站点物品字段接回来」——注释里提到这些名字不算（已剥注释）。
    ck('★★ 全文件不再引用站点物品资料（无 ns.DungeonTips / DG.TipOf / SiteQualOf）',
       'DungeonTips' not in uiall and 'DG.TipOf' not in uiall
       and 'DungeonTips' not in simall and 'SiteQualOf' not in simall)
    # 收窄到 NsCall 自己的函数体：RequestItem 里也有一句 pcall(fn, id)，
    # 不收窄的话「删掉 NsCall 里的 pcall」会被那一句掩盖（变异验证实测踩过）。
    nseg = src[src.index('function DG.NsCall'):src.index('function DG.ContinueOnItemLoad')]
    ncode = '\n'.join(l.split('--')[0] for l in nseg.split('\n'))
    ck('★ 同步取数口统一走 DG.NsCall（内部 pcall，未知 id 不抛错）',
       'function DG.NsCall(name, id)' in ncode and 'pcall(fn, id)' in ncode,
       'NsCall 段 pcall = %s' % ('pcall(fn, id)' in ncode))
    ck('★ 提示框兜底明说「暂时没有客户端数据」',
       'L["暂时没有客户端数据"]' in src)
    toc_txt = open(TOC, encoding='utf-8', errors='replace').read()
    ck('★ TOC 不再加载站点提示数据（Data_DungeonTips.lua 已卸下）',
       'Data_DungeonTips' not in toc_txt)
    # 掉落数据层结构：每件物品只能有 3 个字段（itemID / 掉率 / 无限版新增），
    # 且不得出现任何字符串字段（名字 / 品质 / 部位 / 图标都已删净）。
    lut = open(os.path.join(ADDON, 'Core', 'Data', 'Data_DungeonLoot.lua'),
               encoding='utf-8').read()
    rows = re.findall(r'\n            \{ ([^}]*?) \},', lut)
    fields = {}
    for r in rows:
        n = r.count(',') + 1
        fields[n] = fields.get(n, 0) + 1
    ck('★★ 掉落数据层每件物品只有 3 个字段（itemID / 掉率 / 无限版新增；行数随 fc 回铺增长，≥1900 且只增不减）',
       len(rows) >= 1900 and set(fields) == {3},
       '%d 行，字段数分布 %s' % (len(rows), fields))
    ck('★★ 数据层物品行里没有任何字符串字段（站点名字 / 品质 / 部位 / 图标已删净）',
       all('"' not in r for r in rows), next((r for r in rows if '"' in r), 'clean'))

    # ---------- 滚轮：内容超出一屏时必须能往下滚 ----------
    # 症状（2026-09-22 用户实测）：「这个页面不支持往下滑，很多内容一页放不下，看不到下面的内容」。
    # 根因不是高度算错（child:SetHeight 一直是对的），而是详情 ScrollFrame **只建了容器、
    # 没绑 OnMouseWheel** —— 列表 / 总览都绑了，唯独详情漏了，于是内容再长也滚不动。
    # 第二层坑：卡片是 EnableMouse 的（要收悬停），鼠标压在卡片上时滚轮不保证继续向上冒泡，
    # 所以卡片自己也必须显式转发给所属滚动容器（否则「鼠标停在内容上就滚不动」）。
    ck('★ 详情滚动容器绑了滚轮（本次「滚不动」的根因）',
       'dscroll:EnableMouseWheel(true)' in src
       and 'dscroll:SetScript("OnMouseWheel"' in src)
    ck('三个滚动容器（列表 / 详情 / 总览）都绑了滚轮',
       'listScroll:EnableMouseWheel(true)' in src
       and 'dscroll:EnableMouseWheel(true)' in src
       and 'oscroll:EnableMouseWheel(true)' in src)
    # ⚠️ 掉落卡的 EnableMouseWheel 必须**按上下文**钉（掉落卡转发行前 160 字内）：
    #    任务行（2026-09-22 新增）也有 `r:EnableMouseWheel(true)`，裸查子串会让
    #    「删掉掉落卡滚轮绑定」这条变异照样全绿（逐条隔离跑抓出来的白测）。
    _lootWheel = src.find('DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)')
    ck('★ 卡片（列表卡 + 掉落卡/卡头热区）压住滚轮时显式转发给所属滚动容器',
       'card:EnableMouseWheel(true)' in src
       and _lootWheel > 0
       and ('r:EnableMouseWheel(true)' in src[max(0, _lootWheel - 160):_lootWheel]
            or 'c.hit:EnableMouseWheel(true)' in src[max(0, _lootWheel - 160):_lootWheel])
       and 'DG.WheelScroll(U.dungeonListScroll, U.dungeonListChild, delta)' in src
       and 'DG.WheelScroll(U.dungeonDetailScroll, U.dungeonDetailChild, delta)' in src)
    whseg = src[src.index('function DG.WheelScroll'):src.index('function DG.NewCard(')]
    whcode = '\n'.join(l.split('--')[0] for l in whseg.split('\n'))
    ck('★ 滚轮统一走 DG.WheelScroll（步进 48px，夹在 [0, 内容高 - 视口高]）',
       'delta * 48' in whcode
       and 'child:GetHeight() - scroll:GetHeight()' in whcode
       and 'math.max(0, math.min(maxScroll' in whcode)

    # ---- 副本底图来源不变量（2026-09-22：三处统一走客户端加载图） ----
    # 详情 hero / 列表卡片墙 / 总览条形都必须经 DG.ArtOf 取图。任何一处写死站点 Media 路径，
    # 客户端明明有 1024×512 的加载图却仍显示 256×64 的站点缩略图，而且**零报错**。
    # 桩的 Texture 不记 SetTexCoord（未知方法返回假对象），故裁切数值只能静态锁。
    ck('★ 三处底图都不再写死站点路径（无 SetTexture(DG.ART …)）',
       'SetTexture(DG.ART' not in src and 'DG.ART' not in src)
    ck('★ 三处底图统一走 DG.PaintArt（hero / 卡片墙 / 总览 各 1 处）',
       src.count('DG.PaintArt(card.art, d, "wide")') == 1
       and src.count('DG.PaintArt(art, d, "wide")') == 1
       and src.count('DG.PaintArt(hero.art, d, "hero")') == 1)
    ck('★ 宽版裁切两套齐备（官方 / camelot）',
       all(k in src for k in ('DG.WIDE_TEX_OFFICIAL = { 0.115, 0.885, 0.295, 0.805 }',
                              'DG.WIDE_TEX_CAMELOT  = { 0.000, 1.000, 0.169, 0.831 }')))
    ck('★ 兜底链完整（camelot → 官方 FileDataID → 纯色，不再回站点 Media）',
       'DG.HERO_CAMELOT[d.id]' in src and 'DG.HERO_FDID[d.id]' in src
       and 'SetColorTexture(DG.NOART_COLOR[1]' in src)

    # ---------- 副本任务页（2026-09-22 新增） ----------
    # 用户诉求：每个副本下面要有「这个副本的任务」，且任务状态要能索引到游戏客户端
    # （「我做没做过这条任务」必须走 API 拿到，不能是站点文本）。
    # 段边界 = 「副本任务：客户端取数口」注记 → `function U:Build()`：
    # 本块在文件里的落点是「构建」横幅**之后**，所以右端点不能再用那条横幅。
    qseg = src[src.index('function DG.QLCall(name, id)'):
               src.index('function U:Build()')]
    qcode = '\n'.join(l.split('--')[0] for l in qseg.split('\n'))
    # ★★ 与物品侧同款铁律：任务取数口**统一从这里走**，活代码不得裸调。
    #    本端（1.60 / 3.80）这些函数都挂在 C_QuestLog 命名空间下，裸调全局恒 nil 且零报错。
    qall = '\n'.join(l.split('--')[0] for l in src.split('\n'))
    ck('★★ 全文件不裸调任务取数口（统一走 DG.QLCall）',
       'C_QuestLog.IsQuestFlaggedCompleted(' not in qall
       and 'C_QuestLog.IsOnQuest(' not in qall
       and 'C_QuestLog.GetTitleForQuestID(' not in qall
       and 'C_QuestLog.GetQuestDifficultyLevel(' not in qall)
    ck('★ 任务取数口引用了全部 5 个 C_QuestLog 口 + 原生链接',
       all(k in qcode for k in ('IsQuestFlaggedCompleted', 'IsOnQuest', 'GetTitleForQuestID',
                                'GetQuestDifficultyLevel', 'GetAllCompletedQuestIDs',
                                'GetQuestLink')))
    ck('★ 任务取数口统一 pcall（未知 questID 不抛错）',
       'function DG.QLCall(name, id)' in qcode and 'pcall(fn, id)' in qcode)
    # 完成状态：1.60 有批量口 → 建集合；3.80 没有 → 逐条查并缓存（绝不每帧调 API）
    ck('★★ 完成状态有批量快照 + 逐条兜底两条路（1.60 有 GetAllCompletedQuestIDs、3.80 没有）',
       'DG.questDoneSet' in qcode and 'DG.questDoneCache[id]' in qcode
       and 'GetAllCompletedQuestIDs' in qcode)
    ck('★ 换角色 / 交任务会作废快照（否则状态会停在旧值）',
       'function DG.QuestSnapReset()' in qcode
       and 'RegisterEvent("QUEST_TURNED_IN")' in qcode
       and 'RegisterEvent("PLAYER_ENTERING_WORLD")' in qcode)
    ck('★ 状态监听注册形态钉死（RegisterEvent + OnEvent + __questEvt 三件齐备）',
       '"OnEvent"' in qcode and 'DG.__questEvt = ev' in qcode)
    ck('★ 接任务 / 放弃任务也要当场刷（QUEST_LOG_UPDATE 监听 + 独立分支不动完成态快照）',
       qcode.count('RegisterEvent("QUEST_LOG_UPDATE")') == 2
       and 'elseif event == "QUEST_LOG_UPDATE" then' in qcode)
    # ★★ 名字只认客户端：拿不到就给占位名 + hasName=false，由 UI 明说，绝不回退本表文本
    ck('★★ 任务名只认客户端：拿不到给占位文案 + hasName=false',
       'return format(L["任务 #%d"], id), false' in qcode)
    ck('★★ 客户端拿不到名字时行上明说「暂时没有客户端数据」（不回退本表文本）',
       'L["暂时没有客户端数据"]' in qcode)
    ck('★ 悬停走原生任务链接 + pcall 保护 + NumLines 判据',
       'pcall(GameTooltip.SetHyperlink, GameTooltip, link)' in qcode
       and 'NumLines' in qcode)
    # 滚轮：任务页是新加的滚动容器，三条纪律一个都不能漏
    # ★ 收窄到「任务行构建」函数体：`r:EnableMouseWheel(true)` 全文件有 4 处
    #   （掉落行 / 任务行 / 右列节点 ×2）—— 只在大切片里查「存在」的话，
    #   删掉任务行那一处也照样满足，对应变异就成了恒真白测（上游实测未抓住）。
    seg_qrow = src[src.index('function U:RenderDungeonQuests'):src.index('function U:RefreshQuestRows')]
    qrowcode = '\n'.join(l.split('--')[0] for l in seg_qrow.split('\n'))
    ck('★ 任务滚动容器绑了滚轮 + 行转发（压在任务行上也能滚）',
       'qscroll:EnableMouseWheel(true)' in src
       and 'qscroll:SetScript("OnMouseWheel"' in src
       and 'r:EnableMouseWheel(true)' in qrowcode
       and 'DG.WheelScroll(U.dungeonQuestScroll, U.dungeonQuestChild, delta)' in qrowcode)
    ck('★★ 任务行不重建 scroll child、不调 SetParent（实机闪退的根因）',
       'SetScrollChild' not in qcode and 'SetParent' not in qcode)
    # 两个页签共用一条筛选行：按钮必须按 __mode 分派，否则任务页点「已完成」会跑到掉落去
    # 分派点（if bt.__mode == "quest"）落在 BuildDungeons 的共用筛选行里，不在本切片窗口内
    # —— 所以分派点按全文件钉、档位表按切片钉，两段合起来才等价于「共用一条行」。
    ck('★ 两个页签共用一条筛选行（按 __mode 分派；任务只用前 3 格）',
       'if bt.__mode == "quest" then' in src and 'U.dungeonFilterBtns[i] = bt' in src
       and 'DG.QFILTERS = { "all", "todo", "done" }' in qcode
       and 'bt.__mode, bt.__key = "quest", key' in qcode
       and 'U:RenderDungeonTab()' in qcode)
    ck('★ 阵营过滤有兜底（筛空退回全部，绝不整页空白）',
       'if m == 0 then return all, n, (other and "fallback" or nil) end' in qcode)
    # 页签按钮必须显式抬帧级：hero 与它同为 detail 的子帧，泰坦端同层绘制顺序随机
    ck('★ 页签按钮显式抬帧级（压不住 hero 会被底图盖住）',
       'bt:SetFrameLevel(hero:GetFrameLevel() + 1)' in src)

    # 数据层结构：每行恰好 18 个字段（…15 字段 + 16=NPCID 17=NPC名 18=收获）
    # ——**没有名字字段**（名字一律运行时问客户端）。
    qdat = open(os.path.join(ADDON, 'Core', 'Data', 'Data_DungeonQuests.lua'),
                encoding='utf-8').read()
    qend = open(os.path.join(ADDON, 'Core', 'Data', 'Data_QuestEndNpc.lua'),
                encoding='utf-8').read()
    qsloc = open(os.path.join(ADDON, 'Core', 'Data', 'Data_QuestStartLoc.lua'),
                 encoding='utf-8').read()
    qrows = re.findall(r'^        \{ (.*?) \},\s*(?:--.*)?$', qdat, re.M)
    qbad = [r for r in qrows
            if not re.match(r'^\d+, (?:nil|"[AH]"), (?:nil|\d+), (?:nil|\d+),'
                            r' (?:nil|"[^"]*"), (?:nil|"[^"]*"), (?:nil|"[^"]*"),'
                            r' (?:true|false),'
                            r' (?:nil|\{[^}]*\}), (?:nil|\{[\d, ]*\}),'
                            r' (?:nil|"[^"]*"), (?:nil|"[^"]*"),'
                            r' (?:nil|\{(?:\{\d+,\d\}(?:, )?)*\}),'
                            r' (?:nil|\{[\d, ]*\}),'
                            r' (?:nil|"[^"]*"),'
                            r' (?:nil|\d+), (?:nil|"[^"]*"),'
                            r' (?:nil|\{.*\})$', r)]
    ck('★★ 任务数据层每行恰好 18 个字段、无任务名字段（名字只走客户端；'
       '13=难度 14=需要提供 15=职业 16=NPCID 17=NPC名 18=收获）',
       len(qrows) > 300 and not qbad,
       '%d 行，异常 %d 行 %s' % (len(qrows), len(qbad), qbad[:1]))
    ck('★ 前置 ID / 奖励 / 目标注注口径沿用（数字=已解析 questID；2026-10-09 数据结构扩列后抽查 5724→5722 前置引用与 5722 起始 NPC 仍在）',
       re.search(r'\{ 5724, [^\n]*\{5722\}, \{[\d, ]+\}', qdat) is not None
       and re.search(r'\{ 5722, [^\n]*nil, nil, "[^"]*", "[^"]*"', qdat) is not None)
    ck('★ 前置关系以 nfuwow 核对（PreExtra 表 + 迪菲亚链 132←65…155←142）',
       'ns.DungeonQuestPreExtra = {' in qdat
       and        '[132] = { 65, npc = "黑衣威利", lv = 14 }' in qdat
       and '[155] = { 142, npc = "迪菲亚叛徒", lv = 14 }' in qdat
       and '[65] = { npc = "格里安·斯托曼", lv = 14 }' in qdat)
    ck('★ 任务数据文件在 TOC 里加载（Data_DungeonQuests.lua）',
       'Data_DungeonQuests.lua' in toc_txt)
    ck('★ 任务页两列主从：左列宽常量 + 左列锚定（右列详情固定不随左列滚）',
       'DG.Q_LIST_W = 520' in src
       and 'qscroll:SetPoint("BOTTOMRIGHT", detail, "BOTTOMLEFT", DG.Q_LIST_W, 8)' in src
       and 'U.dungeonQDet = qdet' in src
       and 'U.dungeonQListCard = ilc' in src)
    ck('★ 右列详情随任务页签显隐 + 独立滚轮（总览保持显示）',
       'if U.dungeonQDet then U.dungeonQDet:SetShown(isQuest) end' in src
       and 'DG.WheelScroll(self, U.dungeonQDetChild, delta)' in src)
    ck('★ 点行选中 → 右列就地刷新（渲染尾部联动 RenderQuestDetail，1 定义 + 4 调用）',
       'U.dungeonQuestSel = r.__q[1]' in src and 'U:RenderQuestDetail()' in src
       and src.count('U:RenderQuestDetail()') == 5)
    ck('★ 总览自动适配缩放（canvasW 变化时 zoom=min(1, availW/canvasW)，低限 0.5）',
       'U.dungeonQOVZoom = math.max(0.5, math.min(1, availW / canvasW))' in src
       and 'if U.__ovFitW ~= math.floor(canvasW) then' in src)
    ck('★ 任务行是 Button（Frame 不支持 OnClick，实机 script type not supported）',
       # 不能只查 'r = CreateFrame("Button"...'：drawBar 的 'bar = CreateFrame("Button"...)'
       # 包含该子串，行变异后会被它替命中（实测踩过）。用多行上下文钉。
       'CreateFrame("Button", nil, child, "BackdropTemplate")\n            r:SetSize(DG.Q_LIST_W' in src)
    ck('★ QColor 三连返回必须多变量接（local qc = 只接第一个数，Unpack 实机崩）',
       'local qc = DG.QColor(' not in src and 'local qc = DG.QualOf(' not in src)
    ck('★ 左列单行只写接取地点（不拼起始 NPC，用户 2026-09-22）',
       'local loc = q[6] or ""' in src
       and 'q[5] .. " · " .. loc' not in src)
    ck('★ 阵营档含双阵营通用任务（选联盟也显示无阵营任务，用户 2026-09-22）',
       'if s == "A" or not s then cnt.A = cnt.A + 1 end' in src
       and 'or not q[2] then\n            local key' in src)
    ck('★ 右列详情名带 #任务ID（前导/后续环节点名同样带）',
       'format(" |cff9a9a9a#%d|r", q[1])' in src
       and 'format(" |cff9a9a9a#%d|r", seg)' in src
       and 'format(" |cff9a9a9a#%d|r", fq[1])' in src)
    ck('★ 两块底板卡不重叠且收进栅格（板L 贴左缘 0…+Q_LIST_W，板R 左缘 +Q_DET_GAP，间隙 8）',
       'DG.Q_LIST_W, 0)' in src
       and 'DG.Q_LIST_W + DG.Q_DET_GAP,' in src)
    ck('★ 任务页重排（2026-10-13 · 10-18 列表卡中卡）：两卡顶上移贴 hero + 筛选按钮入左卡顶部 + 进度行不再显示',
       'plateL:SetPoint("TOPLEFT", detail, "TOPLEFT", 0, -DG.FILTER_Y)' in src
       and 'DG.Q_HEAD_H = DG.Q_PAD + 24 + DG.Q_PAD' in src
       and 'local nH, nR, y = 0, 0, -4' in src
       and 'ilc:SetPoint("TOPLEFT", detail, "TOPLEFT", 8, -(DG.FILTER_Y + DG.Q_HEAD_H))' in src
       and 'U.dungeonQuestSum:Hide()' in src
       and 'for k = 1, i - 1 do bx = bx + ((k <= 2) and 92 or 50) end' in src
       and 'bt:SetWidth((i <= 2) and 84 or 42)' in src)
    ck('★★ 任务行小卡片（2026-10-13 用户定：前置改小卡片 + 新增可共享 + 职业色小卡片，紧贴任务名右侧链条）',
       'function DG.MakeBadge(parent, bg)' in src and 'function DG.PlaceBadge(b, x, text, maxX)' in src
       and 'r.preB = DG.MakeBadge(r, DG.Q_BADGE_PRE_BG)' in src
       and 'r.shareB = DG.MakeBadge(r, DG.Q_BADGE_SHARE_BG)' in src
       and 'DG.Q_BADGE_PRE_BG = { 0.78, 0.60, 0.10, 1 }' in src
       and 'DG.Q_BADGE_SHARE_BG = { 0.16, 0.52, 0.26, 1 }' in src
       and 'DG.Q_BADGE_CLS_BG = { 0.30, 0.30, 0.34, 1 }' in src
       and 'function DG.BadgeTint(b, col)' in src and 'function DG.ClsBadgeAt(r, i)' in src
       and 'MakeFS(b, DG.Q_BADGE_FS, C_WHITE, "CENTER")' in src
       and 'if maxX and x + w > maxX then' in src and 'local bmax = DG.Q_X_LOC - 4' in src
       and 'DG.PlaceBadge(r.preB, bx, L["前置"], bmax)' in src
       and 'DG.PlaceBadge(r.shareB, bx, L["可共享"], bmax)' in src
       and 'r.raceB = DG.MakeBadge(r, DG.Q_BADGE_RACE_BG)' in src
       and 'DG.Q_BADGE_RACE_BG = { 0.78, 0.14, 0.12, 1 }' in src
       and 'DG.Q_RACE_TAG = { [1049] = { ok = { 2, 6, 8 }, label = "非亡灵" } }' in src
       and 'function DG.QuestRaceTag(qid)' in src
       and 'DG.PlaceBadge(r.raceB, bx, rtag, bmax)' in src
       and 'DG.Q_BADGE_H = 14' in src and 'DG.Q_BADGE_FS = 12' in src
       and 'DG.Q_BADGE_GAP = 4' in src and 'DG.Q_BADGE_PAD = 3' in src
       and 'DG.Q_BADGE_DY = 2' in src
       and '-(DG.Q_ROW_H - DG.Q_BADGE_H) / 2 - DG.Q_BADGE_DY)' in src)
    ck('★★ 可共享判定走客户端「共享」数据（C_QuestLog.IsPushableQuest，与详情卡同一口径；数据表为离线回退）',
       'function DG.QuestShare(id)' in src
       and 'DG.QLCall("IsPushableQuest", id)' in src
       and 'ns.DungeonQuestShare and ns.DungeonQuestShare[id]' in src
       and 'ns.DungeonQuestShare = {' in qdat)
    ck('★ 详情卡「前置任务」标题（2026-10-13 由「前导任务」改名）',
       'f:SetText(L["前置任务"])' in src and 'L["前导任务"]' not in src)
    ck('★ 详情节点行不再有左强调条（r.bar 删净，内衬 10→8）',
       'r.bar' not in src
       and 'r.name:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -3)' in src
       and 'r.sub:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -21)' in src)
    ck('★ 第二列只显示大地图名（去坐标 + 去子区域）',
       'function DG.QuestMapName(s)' in src
       and 'r.sub:SetText(DG.QuestMapName(loc))' in src
       and '    s = s:gsub("%s*[%d%.]+%s*,%s*[%d%.]+%s*$", "")' in src
       and '    s = s:gsub("%s*%-%s*[^%-]*$", "")' in src)
    ck('★★ 任务页「显示已完成」iOS 开关（ReskinToggle + 默认开 + 5 号钮起退役）',
       'U.dungeonQDoneTg' in src and 'ns.hui.ReskinToggle(tg)' in src
       and 'function U:SetQuestShowDone(on)' in src
       and 'if bt and i > 4 then' in src
       and 'tg:SetPoint("TOPRIGHT", plateL, "TOPRIGHT", -DG.Q_PAD, -DG.Q_PAD - 2)' in src
       and 'tg.label:SetPoint("RIGHT", tg, "LEFT", -6, 0)' in src)
    ck('★★ 任务页两维切换（2026-10-18 用户定：联盟/部落/总览/列表 钮序 + 会话记忆，RL 重置为当前阵营列表）',
       'U.dungeonQView = "overview"' in src and 'U.dungeonQView = "list"' in src
       and 'local view = U.dungeonQView\n    if view ~= "overview" then view = "list" end' in src
       and 'if view == "overview" then' in src
       and '(i == 1 and side == "A") or (i == 2 and side == "H")' in src
       and 'DB().dungeonQView' not in src and 'DB().dungeonQSide' not in src
       and 'qall' not in src
       and 'U.dungeonQOverview = false' not in src)
    ck('★ 全局间距标准（2026-10-10 方案二：窗沿 20 = 12+GUTTER，卡间/组间/按钮间隙全 8）',
       'DG.GUTTER = 8' in src
       and 'DG.LOOT_GAP_Y = 8' in src and 'DG.LOOT_GRP_GAP = 8' in src
       and 'DG.Q_GRP_GAP = 8' in src and 'DG.SCROLL_Y = DG.FILTER_Y + 32' in src
       and 'DG.LOOT_VIEW_X = DG.LOOT_BOSS_X + DG.LOOT_BOSS_W + DG.GUTTER' in src
       and 'DG.LOOT_BOSS_X = DG.LOOT_BOSS_W + DG.GUTTER' in src)
    ck('★ 前导/后续节点取件复位常态色（SetBackdrop 默认白，首渲全白卡；hui=圆角底托管）',
       ('r:SetBackdropColor(1, 1, 1, DG.LOOT_CARD_BG)\n        r:SetBackdropBorderColor(1, 1, 1, DG.LOOT_CARD_EDGE)\n        return r' in src)
       or ('HuiCardFX(r, 10, 2)' in src and 'if not r.__huiCard then' in src))
    ck('★ 卡中卡必须提亮（任务行/节点行在 L1 底板里 → 内卡 L2 底 + L4 悬停，用户 2026-10-10 定规则）',
       'HuiCardFX(r, 12, 2)' in src and 'HuiCardFX(r, 10, 2)' in src
       and 'local base, hov = lv.L1, lv.L3' in src and 'if baseN == 2 then base, hov = lv.L2, lv.L4' in src)
    ck('★ 两列底板卡（左列列表/右列详情各一块，随任务页签显隐）',
       'U.dungeonQPlateL = plateL' in src and 'U.dungeonQPlateR = plateR' in src
       and 'U.dungeonQPlateL:SetShown(isQuest)' in src and 'U.dungeonQPlateR:SetShown(isQuest)' in src)
    ck('★ 阵营档自动勾当前角色阵营（2026-10-17 两维切换：all 退役，恒勾玩家阵营）',
       'function U:SetQuestSide(key)' in src
       and 'side = (ps == "A" or ps == "H") and ps or "A"' in src)
    ck('★★ 四子页滚动定式（2026-10-13 审计⑤⑥⑧）：上缘遮罩 DetailTopMask ×3 + RaiseDetailChrome + __vgen 区间剔除',
       'function DG.DetailTopMask(topY)' in src
       and 'function DG.RaiseDetailChrome()' in src
       and 'U.dungeonDetailHero:SetFrameLevel(base + 3)' in src
       and 'U.dungeonDetailTipZone:SetFrameLevel(base + 3)' in src
       and 'local lv = base + 4' in src
       and 'U.dungeonQDoneTg:SetFrameLevel(lv)' in src
       and 'function DG.CullQuestRows()' in src
       and 'function DG.CullGuideCards()' in src
       and 'function DG.CullLootCards()' in src
       and 'U.dungeonQMask = DG.DetailTopMask(DG.FILTER_Y)' in src
       and 'U.dungeonGMask = DG.DetailTopMask(DG.GUIDE_TOP_Y)' in src
       and 'U.dungeonLMask = DG.DetailTopMask(DG.SCROLL_Y)' in src
       and 'U.dungeonDetailBase = hero:GetFrameLevel()' in src
       and 'el.__vgen == DG.__vgen' in src
       and 'if type(items) ~= "table" then return end' in src
       and 'ns.hui.BuildCapsule(f, 6, hov, 1, 2)' in src
       and 'U.dungeonQMask:SetShown(isQuest)' in src
       and 'U.dungeonGMask:SetShown(isGuide)' in src
       and 'U.dungeonLMask:SetShown(not isQuest and not isGuide and not isMap)' in src)
    ck('★ 掉落页工具行对齐卡墙（2026-10-13 审计⑦ + 二次修订）：BOSS_X 收 0 链 + 位置权威收归 ApplyDetailChrome',
       'DG.LOOT_BOSS_X = DG.LOOT_BOSS_W + DG.GUTTER' in src
       and 'local bx = (cur == "loot" and i == 1) and 0 or DG.GUTTER + (i - 1) * 100' in src
       and 'bt1:ClearAllPoints()' not in src
       and src.count('SetPoint("TOPLEFT", U.dungeonDetail, "TOPLEFT", DG.GUTTER, -DG.FILTER_Y)') == 0)
    ck('★★ 地图页五项整改（2026-10-13 审计①②③④⑨）：底色 L2 / 字号 14 / 返回钮 96×24·14 / SIDE_GAP 8 / 死常量删除',
       'BuildRoundedBG(hdrCard, M.BLK_RADIUS, ns.hui.layer.L2, "both", true, 1)' in _mu
       and 'BuildRoundedBG(side, M.BLK_RADIUS, ns.hui.layer.L2, "both", true, 1)' in _mu
       and '{ 1, 1, 1, 0.03 }' not in _mu
       and 'M.SIDE_GAP = 8' in _mu
       and 'M.CUSTOM_W' not in _mu and 'M.CUSTOM_H' not in _mu
       and 'Host.NewButton(detChild, L["‹ 全部首领"], 96, 24, 14)' in _mu
       and 'MakeFS(blkLoot, 14, C_GREY, "RIGHT")' in _mu
       and 'MakeFS(blkLoot, 14, C_GREY, "LEFT")' in _mu
       and 'r.ds = MakeFS(r, 14, C_TEXT, "LEFT")' in _mu
       and 'MakeFS(listChild, 14, C_GREY, "LEFT")' in _mu)
    ck('★★ 任务行左侧阵营标识走自制品图标（A/H 双档，与筛选按钮同源；暴雪 PVP-Capture 探测与单字兜底退役）',
       'DG.Q_FAC_ICON = {' in src and 'FactionIcon_Alliance' in src and 'FactionIcon_Horde' in src
       and 'local ftex = q[2] and DG.Q_FAC_ICON[q[2]] or nil' in src
       and 'DG.FactionTex' not in src and 'DG.FactionLetter' not in src
       and 'r.emL' not in src
       and 'DG.Q_FAC_ICON_SZ = 18' in src
       and 'r.em:SetSize(DG.Q_FAC_ICON_SZ, DG.Q_FAC_ICON_SZ)' in src
       and '-(DG.Q_ROW_H - DG.Q_FAC_ICON_SZ) / 2)' in src)
    ck('★★ 任务页「地图图钉」开关（默认开 + DB.mapQuestPins 显式 false 才关 + 联动 MapUI.SyncPins）',
       'U.dungeonQuestPinTg' in src and 'tg.label:SetText(L["地图图钉"])' in src
       and 's.mapQuestPins = self:GetChecked() and true or false' in src
       and 'tg:SetChecked(DB().mapQuestPins ~= false)' in src
       and 'return s.mapQuestPins ~= false' in _mu
       and 'ns.MapModule and ns.MapModule.SyncPins' in src
       and 'tg:SetPoint("RIGHT", U.dungeonQDoneTg.label, "LEFT", -8, 0)' in src
       and 'if not (cur == "loot" and i == 1) then bt:SetWidth(92) end' in src)
    ck('★★ 地图任务钉三态（2026-10-14：开关关全隐 + 状态过滤 + 前置链 B/C 双态 + 三枚自制品贴图）',
       'M.PIN_QUEST_READY_TEX' in _mu and 'M.PIN_QUEST_LOCKED_TEX' in _mu and 'M.PIN_QUEST_PRE_TEX' in _mu
       and 'Interface\\\\GossipFrame\\\\AvailableQuestIcon' not in _mu
       and 'function M.QuestPinsOn()' in _mu
       and 'if kind == "quest" and not qp then' in _mu
       and 'local lockedPre, preBlock = {}, {}' in _mu
       and 'local function segOk(seg)' in _mu
       and 'if qlv and lv < qlv then return false end' in _mu
       and 'if type(ps) == "number" and (DG.QuestState and DG.QuestState(ps)) ~= "done" then' in _mu
       and 'for i = 1, #ex do' in _mu
       and 'if DG.QuestState(seg) ~= "done" then' in _mu
       and 'elseif preBlock[p.id] then' in _mu
       and 'elseif lockedPre[p.id] then' in _mu
       and 'bt.dot:SetTexture(M.PIN_QUEST_READY_TEX)' in _mu
       and 'bt.dot:SetTexture(M.PIN_QUEST_LOCKED_TEX)' in _mu
       and 'bt.dot:SetTexture(M.PIN_QUEST_PRE_TEX)' in _mu
       and 'L["需先完成：%s"]' in _mu and 'L["完成后解锁：%s"]' in _mu
       and 'L["副本任务"]' in _mu
       and 'L["点击进入[无限副本手册]任务详情"]' in _mu
       and 'local function wpDName(dk)' in _mu
       and 'f:SetFont(bf, bs, bfl)' in _mu
       and 'for i = 2, nl do' in _mu)
    ck('★★ 地图页图钉开关合并（「图钉显示」下拉 + 首领/任务图钉两项 + 独立 DB 开关）',
       'M.PIN_BTN_W, M.PIN_BTN_MIN, M.PIN_BTN_GAP = 72, 64, 8' in _mu
       and 'local bossPinBtn = Host.NewButton(frame, "", M.PIN_BTN_W, M.BAR_H, 14)' in _mu
       and 'local questPinBtn = Host.NewButton' not in _mu
       and 'bossPinBtn:SetScript("OnClick", function() M.ShowPinMenu(bossPinBtn) end)' in _mu
       and 'function M.ShowPinMenu(owner)' in _mu
       and 'function M.ToggleBossPins()' in _mu and 'function M.ToggleQuestPins()' in _mu
       and 's.mapBossHidden = M.hideBossPins or nil' in _mu
       and 's.mapQuestHidden = M.hideQuestPins or nil' in _mu
       and 'function M.HasKindPins(id, want)' in _mu
       and 'local hide = (M.hideBossPins and (k == "boss" or k == "rare"))' in _mu
       and 'frame.routePinBtn:SetPoint("LEFT", frame.bossPinBtn, "RIGHT", M.PIN_BTN_GAP, 0)' in _mu
       and 'bt:SetWidth(math.max(M.PIN_BTN_MIN, math.ceil(w + 22)))' in _mu)
    ck('★★ 大地图任务图钉（2026-10-14 用户改向：钉上 WorldMapFrame，机制照探索找书钉）',
       'function M.SyncWorldQuestPins()' in _mu
       and 'hooksecurefunc, WorldMapFrame, "OnMapChanged", M.SyncWorldQuestPins' in _mu
       and 'hooksecurefunc, WorldMapFrame, "OnCanvasScaleChanged", M.SyncWorldQuestPins' in _mu
       and 'WorldMapFrame.HookScript, WorldMapFrame, "OnShow", M.SyncWorldQuestPins' in _mu
       and 'pcall(wpEv.RegisterEvent, wpEv, "QUEST_LOG_UPDATE")' in _mu
       and 'C_Map.GetMapRectOnMap' in _mu
       and 'ns.NPCLoc' in _mu and 'ns.QuestPreNpcID' in _mu
       and 'if not M.QuestPinsOn() then' in _mu
       and 'if ns.MapModule and ns.MapModule.SyncWorldQuestPins then ns.MapModule.SyncWorldQuestPins() end' in src)
    ck('★★ 图钉设置面板（2026-10-14：齿轮入口 + 右侧侧挂面板 + 大小步进 + 多选范围 + 阵营自动过滤）',
       'function M.ToggleQuestPinPanel()' in _mu
       and 'function M.QuestPinPanel()' in _mu
       and 'function ns.CloseQuestPinSettings()' in _mu
       and 'db.dungeon.mapQuestPinsCfg = nil' in _mu
       and 'local WP_DEF = { size = 32, world = false, scope = { lv = true, reco = true, enter = true, all = false, grey = true } }' in _mu
       and 'if ns.MapModule and ns.MapModule.QuestPinPanel then hook(ns.MapModule.QuestPinPanel()) end' in open(os.path.join(ADDON, 'Core', 'QuickBar.lua'), encoding='utf-8').read()
       and 'U.dungeonQuestPinCfg = bt' in src
       and 'bt:SetPoint("RIGHT", U.dungeonQuestPinTg.label, "LEFT", -6, 0)' in src
       and 'ns.SET_ICON or "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\textures\\\\DF_Settings"' in src
       and 'bt.SyncIconState = function(self)' in src
       and 'self.tex:SetVertexColor(0.62, 0.62, 0.62)' in src
       and 'local open = (ns.MapModule and ns.MapModule.QuestPinPanel and ns.MapModule.QuestPinPanel()) and true or false' in src
       and 'if ns.SyncQuestPinIcon then pcall(ns.SyncQuestPinIcon) end' in open(os.path.join(ADDON, 'Core', 'MapUI.lua'), encoding='utf-8').read()
       and 'PopShown(ns.MapModule.QuestPinPanel())' in open(os.path.join(ADDON, 'Core', 'QuickBar.lua'), encoding='utf-8').read()
       and 'local useLv, useReco, useEnter' in _mu
       and 'local function wpGrey(qlv)' in _mu
       and 'if d[2] == 5 and type(d[1]) == "number" then gt = d[1] break end' in _mu
       and 'local glv = DG.QuestLevel and DG.QuestLevel(q[1]) or nil' in _mu
       and 'if glv == nil then glv = q[4] end' in _mu
       and 'if glv and wpGrey(glv) then return false end' in _mu
       and '{ k = "grey",  t = L["任务难度灰色不显示"] }' in _mu
       and 'if side and q[2] and q[2] ~= side then return false end' in _mu
       and 'local pcls = (UnitClass and UnitClass("player")) or nil' in _mu
       and 'if pcls and q[15] and q[15] ~= pcls then return false end' in _mu
       and 'if qlv == nil and r then qlv = r[1] end' in _mu
       and 'w * x / k, -h * y / k' in _mu
       and 'local BP_MASK_TEX = "Interface\\\\CharacterFrame\\\\TempPortraitAlphaMask"' in _mu
       and 'local function bpMask(tex)' in _mu
       and 'pcall(tex.AddMaskTexture, tex, m) then tex.__bpMask = m end' in _mu
       and 'return (pcall(SetPortraitTextureFromCreatureDisplayID, tex, disp))' in _mu
       and 'local function bpPaint(host, disp, cr, cg, cb, size)' in _mu
       and 'bpPaint(bt.__av, bpDisp(M.curId, p.en), rr, rg, rb, isSel and M.PIN_SIZE or M.PIN_MIN)' in _mu
       and 'bpPaint(r.__av, bpDisp(id, bosses[i].en), cr, cg, cb, 32)' in _mu
       and 'BP_AVATAR_ORANGE = { 1, 0.60, 0.15 }' in _mu
       and 'r.__av = CreateFrame("Frame", nil, r)' in _mu
       and 'PIN_FRAME_LEVEL_DUNGEON_ENTRANCE' in _mu
       and 'WorldMapFrame:AddDataProvider(provider)' in _mu
       and 'p:SetScale(k)' in _mu
       and 'p:RegisterForClicks("LeftButtonUp")' in _mu
       and 'if ns.ShowDungeonDetail then ns.ShowDungeonDetail(dk) end' in _mu
       and 'if U.SetDungeonTab then U:SetDungeonTab("quest") end' in _mu
       and 'U.dungeonQuestSel = qid' in _mu
       and 'if it.blocking then' in _mu
       and 'qid, dk = it.blocking, dk2' in _mu
       and 'local WP_DEF = { size = 32, world = false,' in _mu
       and 'if cfg.world == true or e.loc[1] == disp then' in _mu
       and 'L["世界地图显示"]' in _mu
       and 'local provider' in _mu)
    ck('★ 前导链/后续/目标/注释/奖励五类信息进右列渲染（2026-10-09 起收获/注释段走 DG.GainsSegs）',
       'local pre = row[9]' in src and 'DG.QuestFollowers' in src
       and 'DG.GainsSegs(q)' in src and 'local rew = q[10]' in src)
    ck('★ 前导链追溯到源头（collect 递归 + 表外 PreExtra 继续爬 + 「下一步」进度标）',
       'collect(q, 1)' in src and 'ns.DungeonQuestPreExtra[seg]' in src
       and 'L["下一步"]' in src)
    ck('★ 表外链环节副标题补起始信息（PreExtra npc/lv 回退，2026-09-22）',
       'elseif ns.DungeonQuestPreExtra and ns.DungeonQuestPreExtra[seg] then' in src
       and 'if ex.npc and ex.npc ~= "" then' in src
       and 'if ex.lv then sub = sub .. " · " .. format(L["%d 级可接"], ex.lv) end' in src)
    ck('★ 表外链环节 src 来源回退（物品起始任务 96391 黑铁地图，2026-09-22）',
       'if ex.src and ex.src ~= "" then' in src
       and 'sub = ex.src' in src
       and 'src = "黑铁地图(黑铁间谍掉落，丹莫罗 77,60)"' in qdat)
    ck('★ 详情页收获节：经验/金钱/声望（DG.GainsSegs 统一拼装，2026-10-09 对齐现口径）',
       'local seg = DG.GainsSegs(q)' in src
       and 'if seg and #seg > 0 then' in src
       and 'L["收获"]' in src)
    ck('★ 「下一步」金标在状态词前，状态词跟随环节状态色不落灰（2026-09-22）',
       'stag = "|cffffd100" .. L["下一步"] .. "|r" .. (stag ~= "" and (" · |cff" .. shex .. stag .. "|r") or "")' in src
       and 'local shex = format("%02x%02x%02x", pcol[1] * 255 + 0.5' in src)
    ck('★ 任务难度行：nfu 档位彩色数字（Q_DIFF_COLOR r1红…r5灰）',
       'if q[13] and #q[13] > 0 then' in src
       and 'DG.Q_DIFF_COLOR[d[2]] or C_GREY' in src
       and 'L["任务难度"] .. "：|r"' in src)
    ck('★★ 职业专属：详情行职业色文字 + 任务行职业色小卡片（白字、去「圣」全名，紧贴任务名右侧）',
       'function DG.QClassColor(' in src and 'function DG.QClassLabel(' in src and 'function DG.QClassList(' in src
       and 'DG.QCLASS_DIM = 0.78' in src and 'DG.QCLASS_LUM = 0.62' in src and 'DG.QCLASS_TOKEN' in src
       and 'format(L["%s专属"], q[15])' in src
       and 'local clsList = DG.QClassList(q[15])' in src
       and 'DG.PlaceBadge(cb, bx, cnm, bmax)' in src
       and 'DG.QCLASS_CHAR' not in src and 'DG.QClassChar' not in src)
    ck('★ 奖励/需求两列网格 + 「任务需求」单列（需要提供 ≠ 奖励，2026-09-22）',
       'local function renderChips(items, ncol, questID)' in src
       and 'renderChips(q[14], 2, q[1])' in src and 'renderChips(rew, 2)' in src
       and 'if hasChips or objTxt then' in src
       and 'L["任务需求"]' in src)
    # ★ 同上：`if q[16] then` 在详情函数体里就有两处（4 空格缩进=拼 where；
    #   8 空格缩进=选可点行容器）。只查「存在」的话，把前一处改成 `if false then`
    #   照样满足（后一处还在）→ 恒真白测（上游实测未抓住）。
    #   故按行首缩进精确锚定前一处。
    seg_qdet = src[src.index('function U:RenderQuestDetail'):src.index('function U:SetDungeonTab')]
    qdetcode = '\n'.join(l.split('--')[0] for l in seg_qdet.split('\n'))
    ck('★ 起始行 NPC 以 ID 为参考键：q[16] 有值时显示 金名 + #NPCID 灰尾缀（2026-09-22，金名=可点开图标记）',
       re.search(r'^    if q\[16\] then$', qdetcode, re.M) is not None
       and 'local nm = (q[17] and q[17] ~= "" and q[17]) or q[5] or ""' in qdetcode
       and 'where = "|cffffd100" .. nm .. "|r" .. format(" |cff9a9a9a#%d|r", q[16])' in qdetcode)
    ck('★ 起始行地图按钮（takeNpc 行内 mark 子按钮 → DG.MarkNPC，2026-10-18 掉落类起始 + 按钮化）',
       'local function takeNpc()' in src
       and 'f = CreateFrame("Button", nil, child)' in src
       and 'f.__npc = q[16] or sn[1]' in src
       and 'f.__loc = (smap and { smap, sx, sy }) or (sn and sn[3] and { sn[3], sn[4], sn[5] }) or nil' in src
       and 'local mb = NewButton(f, L["地图"], 62, 20, 14)' in src
       and 'AddBtnIcon(mb, "EntryPin", 12, 4)' in src
       and 'mb:SetPoint("RIGHT", f.fs, "RIGHT", 74, 0)' in src
       and 'DG.MarkNPC(p.__npc, p.__loc)' in src)
    ck('★ 详情页结束行（DungeonQuestEndNpc 数据源 + 与起始同款 地图 子按钮，2026-10-18）',
       'function DG.QuestEndNpc(qid)' in src
       and 'local en = DG.QuestEndNpc(q[1])' in src
       and 'f.fs:SetText(DG.Hex(C_GREY) .. L["结束："] .. "|r" .. txt)' in src
       and 'f.__loc = { emap, ex, ey }' in src
       and 'if emap and ex and ey and MapUsable(emap) then' in src
       and 'local zl = DG.LocText(emap, ex, ey, ezone)' in src
       and 'ns.DungeonQuestEndNpc = {' in qend)
    ck('★ 地点口径统一（ZoneShort 截子区域 + StartLoc 精确坐标，2026-10-18 B+ 定稿）',
       'function DG.ZoneShort(s)' in src
       and 'local head, rest = s:match("^(.-)%s*%-%s*(.+)$")' in src
       and 'function DG.LocText(mapID, x, y, fb)' in src
       and 'function DG.StartLoc(qid, npcID)' in src
       and 'local smap, sx, sy, szone = DG.StartLoc(q[1], startNpcID)' in src
       and '(smap and DG.LocText(smap, sx, sy, szone)) or DG.ZoneShort(q[6])' in src
       and 'local smap, sx, sy, szone = DG.StartLoc(q[1], q[16])' in src
       and 'Core\\Data\\Data_QuestStartLoc.lua' in open(os.path.join(ADDON, 'DungeonsForever.toc'), encoding='utf-8').read()
       and 'ns.DungeonQuestStartLoc = {' in qsloc)
    ck('★ 总览徽标按客户端类型显示地下城（GetQuestType==81，2026-10-18）',
       'n.posB.lab:SetText(chainText or ((DG.QLCall("GetQuestType", q[1]) == 81) and L["地下城"] or L["副本内"]))' in src
       and 'chainLab[chains[r][k][1]] = (k < anchor) and L["前置"] or L["后续"]' in src
       and 'n.posB.__wantCol = chainText and DG.Q_BADGE_PRE_BG or DG.Q_BADGE_IN_BG' in src)
    ck('★ DG.MarkNPC 航点链路（UiMapPoint + SetUserWaypoint + OpenWorldMap，2026-09-22）',
       'function DG.MarkNPC(npcID, locOverride)' in src
       and 'local loc = locOverride or (ns.NPCLoc and ns.NPCLoc[npcID])' in src
       and 'UiMapPoint.CreateFromCoordinates' in src
       and 'pcall(C_Map.SetUserWaypoint, pt)' in src
       and 'pcall(C_Map.OpenWorldMap, mapID)' in src
       and 'ns.NPCLoc and ns.NPCLoc[npcID]' in src)
    ck('★ 链节点标记入口（node 池 Button 化 + 前导/后续 __npc，2026-09-22；2026-10-18 掉落类前置 __loc 扩展）',
       'r = CreateFrame("Button", nil, child, "BackdropTemplate")' in src
       and 'if not nid and ns.QuestPreNpcID then nid = ns.QuestPreNpcID[seg] end' in src
       and 'local sn = (not nid) and DG.QuestStartNpc(seg) or nil' in src
       and 'r.__loc = (sn and sn[3] and { sn[3], sn[4], sn[5] }) or nil' in src
       and 'r.__npc = fq[16] or (fsn and fsn[1]) or nil' in src
       and 'for i = pool.nNpc + 1, #pool.npc do pool.npc[i]:Hide() end' in src)

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
    ck('★ 任务行选中态：无强调条（右缘金标条 selMark 已删）+ OnLeave/paint 按选中态复位（悬停不冲掉选中）',
       'r.selMark' not in src
       and 'HuiCardState(r, isSel and "hover" or "norm")' in src
       and '(self.__q and self.__q[1] == U.dungeonQuestSel) and "hover" or "norm"' in src)


# ---------------------------------------------------------------------------
# 动态守卫
# ---------------------------------------------------------------------------
LUA_SCRIPT = r'''
(function()
  local R = {}
  local function ck(name, cond, extra)
    R[#R + 1] = (cond and "OK" or "FAIL") .. "\t" .. name
      .. (extra ~= nil and ("\t[" .. tostring(extra) .. "]") or "")
  end
  local ok, err = pcall(function()
    local U = TF_NS.DungeonUI

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
    -- ㉒ iOS 开关桩：真 ReskinToggle 在桩 CheckButton 上会炸（万能壳把缺失键 Text 现造成
    -- function，真件预期 nil）。开关视觉全由 hui 托管、harness 不断言皮，覆盖为 no-op。
    if TF_NS and TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
    local IS_FOREVER = TF_NS.IsForever == true   -- 地图标记分端断言的开关
    if U == nil then ck("ns.DungeonUI 不存在", false) return end

    -- ★ 桩里没有 UnitLevel（现有 harness 从未走到调用它的路径），本页第一个吃它的页面。
    --   不补的话 BuildDungeons 第一步就 "attempt to call a nil value"。
    PLAYER_LEVEL = 16
    UnitLevel = function() return PLAYER_LEVEL end

    -- 计帧器：必须在 U:Build() 之前挂上，之后**所有**新建帧都计进来（池化后应为 0）
    FRAMES = 0
    local _cf = CreateFrame
    CreateFrame = function(...) FRAMES = FRAMES + 1; return _cf(...) end

    if not U.built then U:Build() end
    -- ★★ 2026-10-09 起页面架构 = EnsureBuilt 懒构建（首屏不整包建帧）。本 harness 数千条
    --   断言隐式依赖「容器/池已建」的旧时序，统一在此把全部懒建池显式建齐（幂等），
    --   等价于旧「Build 一次建全」时序；懒构建不变量改由静态断言（壳帧在 Build、
    --   内容走 EnsureBuilt）+ 幂等断言（二建零新建帧）守护。顺序照游戏渲染入口。
    U:EnsureBuilt("Raids")
    U:EnsureBuilt("Explore")
    if ns.LoadForeverPages then
        U:EnsureBuilt("Professions")
        U:EnsureBuilt("Collections")
        U:EnsureBuilt("Bis")
        U:EnsureBuilt("Tier")
        U:EnsureBuilt("PvP")
    end
    DG = TF_NS.DungeonModule
    DG.EnsureCardPool()
    DG.EnsureOverviewBuilt()
    DG.EnsureDetailBuilt()
    DG.EnsureGuideLane()
    DG.EnsureMapPage()
    DG.EnsureQuestLane()
    DG.EnsureItemListener()
    DG.BuildDetailChips()

    -- 标签入口 & SwitchSub
    local found = false
    for _, t in ipairs(U.subTabs or {}) do if t.key == "Dungeons" then found = true end end
    ck("标签行里有「5人本」入口（key = Dungeons；文案随用户要求已改名）", found)

    U:SwitchSub("Dungeons")
    if U.dungeonPage == nil then ck("dungeonPage 页面帧未创建", false) return end
    ck("★ SwitchSub 后副本页显示（漏 SetShown → 整页空白）", U.dungeonPage.__shown == true)
    ck("副本页已构建", U.dungeonBuilt == true)

    -- ---------- 顶栏胶囊：5人本 / 团本（2026-09-23 用户指定）----------
    -- 整块包 do...end：Lua 5.1 单函数 local 上限 200，本脚本很长，
    -- 块内临时变量出块即释放，不计入峰值。
    do
      -- ★ 分端：无限服（1.60.x）五颗，泰坦（3.8.x）两颗 —— 后三颗由 ns.IsForever 门控。
      ck("★ 胶囊行颗数分端（无限服 10 / 泰坦 2）",
         #(U.subTabs or {}) == (IS_FOREVER and 10 or 2), #(U.subTabs or {}))
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
        ck("★ 无限服第五颗胶囊 key = Collections / 文案 = 藏品（2026-10-08 藏品页加入）",
           _t5 ~= nil and _t5.key == "Collections" and _t5.text == "藏品",
           tostring(_t5 and _t5.key) .. " / " .. tostring(_t5 and _t5.text))
        local _t6 = (U.subTabs or {})[6]
        ck("★ 无限服第六颗胶囊 key = Factions / 文案 = 声望（2026-10-11 声望页加入）",
           _t6 ~= nil and _t6.key == "Factions" and _t6.text == "声望",
           tostring(_t6 and _t6.key) .. " / " .. tostring(_t6 and _t6.text))
        local _t7 = (U.subTabs or {})[7]
        ck("★ 无限服第七颗胶囊 key = Bis / 文案 = BIS配装",
           _t7 ~= nil and _t7.key == "Bis" and _t7.text == "BIS配装",
           tostring(_t7 and _t7.key) .. " / " .. tostring(_t7 and _t7.text))
      end
      local RM = TF_NS.RaidModule
      -- ★ 2026-10-09 懒构建架构：团本内容首切才建 → 断言前显式 EnsureBuilt（幂等）
      U:EnsureBuilt("Raids")
      ck("★★ 团本页是常驻帧（已接 RaidModule 建页）", U.raidPage ~= nil and RM ~= nil)
      ck("★★ 单列表页：卡片池 7 / 分组 2 / 剔除清单齐全",
         RM ~= nil and RM.cards ~= nil and #RM.cards == 7
         and RM.groups ~= nil and #RM.groups == 2
         and RM.cullables ~= nil and #RM.cullables >= 7 + 4 + 12,
         RM and RM.cullables and tostring(#RM.cullables))
      ck("★★ 卡宽填满滚动区（456×2+8=920，左右内衬各 8 对称）×145",
         RM ~= nil and RM.LS_COL_W == 456 and RM.LS_COL_H == 145
         and RM.LS_COLS == 2
         and RM.LS_COLS * RM.LS_COL_W + (RM.LS_COLS - 1) * RM.LS_GAP == RM.W - 2 * RM.GRID_PAD)
      ck("★★ 首批三座中文名 = 深穴 / 海加尔峰 / 奥妮克希亚的巢穴",
         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].name == "深穴"
         and RM.DATA.raids[2].name == "海加尔峰"
         and RM.DATA.raids[3].name == "奥妮克希亚的巢穴")
      ck("★★ 首批同日开启（三座共用同一个开放窗口，日期由地区算出）",
         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].date == nil
         and RM.DATA.raids[1].first == true and RM.DATA.raids[3].first == true)

      -- ★★ 卡墙几何（纯函数直调）：一行 2 张 / 不越右缘
      do
        local _big, _small = {}, {}
        for _, _rc in ipairs(RM.DATA.raids) do
          if _rc.first then _big[#_big + 1] = _rc else _small[#_small + 1] = _rc end
        end
        local _pb = RM.LayoutCards(_big, RM.LS_COL_W, RM.LS_COL_H, 34)
        local _ps = RM.LayoutCards(_small, RM.LS_COL_W, RM.LS_COL_H,
                                   _pb.bottom + RM.LS_LABEL_H)
        local _rb, _rs = 0, 0
        for i = 1, #_big do
          if _pb[i].x + RM.LS_COL_W > _rb then _rb = _pb[i].x + RM.LS_COL_W end
        end
        for i = 1, #_small do
          if _ps[i].x + RM.LS_COL_W > _rs then _rs = _ps[i].x + RM.LS_COL_W end
        end
        local _cw = RM.W - 2 * RM.GRID_PAD
        ck("★★ 卡墙·首批 3 大卡 = 2 行且不越右缘",
           #_big == 3 and _pb.rows == 2 and _rb <= _cw,
           tostring(#_big) .. " 张 / " .. tostring(_pb.rows) .. " 行 / 右缘 " .. tostring(_rb))
        ck("★★ 卡墙·后续 4 小卡 = 2 行且不越右缘",
           #_small == 4 and _ps.rows == 2 and _rs <= _cw,
           tostring(#_small) .. " 张 / " .. tostring(_ps.rows) .. " 行 / 右缘 " .. tostring(_rs))
      end

      -- ★★ 顶栏切换序列（两页互斥 / 团本态刷新安全）
      do
        local _f0 = FRAMES
        local _ok1 = pcall(function() U:SwitchSub("Raids") end)
        ck("★ 切团本 → 团本页显示", _ok1 and U.raidPage.__shown == true)
        ck("★ 切团本 → 副本页隐藏（两页互斥）", U.dungeonPage.__shown == false)
        ck("★ 切团本 → curSub = Raids", U.curSub == "Raids", tostring(U.curSub))
        ck("★ 切团本零新建帧（列表页 Build 期全建）", FRAMES == _f0, FRAMES - _f0)
        local _okU = pcall(function() U:UpdateActiveSub() end)
        ck("★ 团本态下 UpdateActiveSub 不报错", _okU == true)
        ck("★ 团本态下 UpdateActiveSub 不会把副本页刷出来", U.dungeonPage.__shown == false)
        pcall(function() U:SwitchSub("Dungeons") end)
        ck("★ 切回 5人本 → 团本页隐藏", U.raidPage.__shown == false)
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
        ck("★★ 分组注记 = 地区日期（Build 后即渲染，无需切页签）",
           RM.wallLabels[2] ~= nil
           and tostring(RM.wallLabels[2].__text) == "2026 年 12 月 10 日 · 同日开启",
           RM.wallLabels[2] and tostring(RM.wallLabels[2].__text))
      end


      -- ---------- BIS配装页数据（2026-09-25 抓取；数据两端都加载，UI 由 LoadForeverPages 门控）----------
      do
        local B = TF_NS.EnsureBISData and TF_NS.EnsureBISData() or nil
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
          -- 2026-10-16：收录口径由「职业口径 17」扩到「方案页全量」（默认 30 级卷 38 页）
          local nTS, nKey, nLabel = 0, 0, 0
          for _, c in ipairs(B.classes) do
            for _, sp in ipairs(c.specs or {}) do
              if type(sp.tspec) == "string" then nTS = nTS + 1 end
              if type(sp.key) == "string" then nKey = nKey + 1 end
              if type(sp.label) == "string" then nLabel = nLabel + 1 end
            end
          end
          local nBadMain, nBadCfg, nAsym, nPg20, nPg30 = 0, 0, 0, 0, 0
          do
            local WK = { "two-hand", "main-hand", "off-hand", "held", "shield" }
            -- ★ 两卷都守（数据层 levels[20]/levels[30] 各自独立收录；默认卷只是别名）。
            for lv, v in pairs(B.levels or {}) do
              for _, c in ipairs(v.classes or {}) do
                for _, sp in ipairs(c.specs or {}) do
                  if lv == 20 then nPg20 = nPg20 + 1 else nPg30 = nPg30 + 1 end
                  local S = sp.slots or {}
                  local has = {}
                  for si = 1, 2 do
                    local o = {}
                    for _, wk in ipairs(WK) do
                      local sd = S[wk]
                      o[wk] = type(sd) == "table" and type(sd[si]) == "table" and sd[si][1] ~= nil
                    end
                    has[si] = o
                  end
                  for si = 1, 2 do
                    local o = has[si]
                    local anyMain = o["two-hand"] or o["main-hand"]
                    local anyOff = o["off-hand"] or o["held"] or o["shield"]
                    if not anyMain then nBadMain = nBadMain + 1 end
                    -- 单侧配置合法性：双手独占（禁与主手/副手类并存）；或 主手+可选副手类。
                    local bad = (o["two-hand"] and (o["main-hand"] or anyOff))
                        or (not o["two-hand"] and not o["main-hand"])
                    if bad then nBadCfg = nBadCfg + 1 end
                  end
                  if has[1]["two-hand"] ~= has[2]["two-hand"] then nAsym = nAsym + 1 end
                  if has[1]["main-hand"] ~= has[2]["main-hand"] then nAsym = nAsym + 1 end
                end
              end
            end
          end
          ck("★ BiS 专精共 38（2026-10-16 方案页全量口径）", nSpec == 38, tostring(nSpec))
          ck("★ BiS 方案页均带 tspec 天赋轴", nTS == nSpec, tostring(nTS) .. "/" .. tostring(nSpec))
          ck("★ BiS 方案页均带 key（同天赋多页的唯一标识）", nKey == nSpec,
             tostring(nKey) .. "/" .. tostring(nSpec))
          ck("★ BiS 方案页均带 label（预设行天赋段文案）", nLabel == nSpec,
             tostring(nLabel) .. "/" .. tostring(nSpec))
          -- 武器槽判据（2026-10-16 修正口径）：源站允许**两阵营用不同武器类型**
          --   （例：30级术士痛苦 联盟双手法杖 / 部落主手匕首+副手宝珠；20级牧师暗牧、
          --   20级德鲁伊鸟德 联盟双手 / 部落主手；20级德鲁伊熊德 反过来）。
          --   故不能再要求「某槽两侧都有值」——那是站点设计，不是抓取缺失。
          --   改为三条真不变量：① 每侧至少有一个主手类槽有值（UI MainKey 才不落空）；
          --   ② 单侧武器配置自洽（双手独占／主手+可选副手类）；
          --   ③ 两阵营确有不同的武器配置组（记录口径，防「别人都一致」被误当回归）。
          ck("★ BiS 每侧主手类槽均有值（UI MainKey 不落空）", nBadMain == 0, tostring(nBadMain))
          ck("★ BiS 单侧武器配置自洽（双手独占／主手+可选副手类）", nBadCfg == 0, tostring(nBadCfg))
          -- 差异计数只作口径记录（本卷 = 30级术士痛苦 1 页的 two-hand/main-hand 各 1 处）。
          --   若归零，说明「两阵营武器双配置」样本消失，需复核抓取是否又吞了某一侧。
          ck("★ BiS 两阵营武器配置差异样本仍在（双配置未被抓塌）", nAsym >= 1, tostring(nAsym))
          -- 两卷独立收录（2026-10-16 全量口径）：30级 38 页 / 20级 32 页。
          ck("★ BiS 卷页数 20级=32 / 30级=38（两卷独立收录）", nPg20 == 32 and nPg30 == 38,
             tostring(nPg20) .. "/" .. tostring(nPg30))
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
        -- ★ 2026-10-09 懒构建：探索池在 harness 开头统一 Ensure 建齐 →
        --   这里验「EnsureBuilt 幂等（二建零新建帧）」。
        local _ef0 = FRAMES
        U:EnsureBuilt("Explore")
        ck("★★ 探索 EnsureBuilt 幂等（二建零新建帧）", FRAMES - _ef0 == 0, FRAMES - _ef0)
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
          -- ★ 行内胶囊徽章（2026-09-25 用户定方案 A；2026-10-15 懒创建拍板：按需建、走 PILL_STORE 弱键表，
          --   断言统一走 EM.PillOf 访问器；「未显示」语义 = 未创建（nil），懒创建是省内存的断言目标本身
          local _r1, _r5, _r21, _r19 = EM.rows and EM.rows[1], EM.rows and EM.rows[5],
                                        EM.rows and EM.rows[21], EM.rows and EM.rows[19]
          ck("★ 行1（艾尔文 5~10·推荐）：领地胶囊=联盟领地 + 等级胶囊 + 推荐金胶囊、待确认胶囊未创建",
             _okB and _r1 ~= nil
             and EM.PillOf(_r1, "fTag") ~= nil and EM.PillOf(_r1, "fTag").__shown == true
             and tostring(EM.PillOf(_r1, "fTag").t.__text) == "联盟领地"
             and EM.PillOf(_r1, "lvTag") ~= nil
             and tostring(EM.PillOf(_r1, "lvTag").t.__text) == "5~10级"
             and EM.PillOf(_r1, "recTag") ~= nil
             and tostring(EM.PillOf(_r1, "recTag").t.__text) == "推荐"
             and tostring(_r1.a.__text):find("★推荐", 1, true) == nil
             and EM.PillOf(_r1, "unTag") == nil
             and _r1.unStrike ~= nil and _r1.unStrike.__shown == false
             and _r1.a.__textColor ~= nil and math.abs(_r1.a.__textColor[1] - 0.88) < 1e-6,
             _r1 and EM.PillOf(_r1, "lvTag") and tostring(EM.PillOf(_r1, "lvTag").t.__text))
          ck("★ 行5（阿拉塔瑞克·银松 10~20）：领地胶囊=部落领地、2026-10-13 已确认可拾取 → 待确认胶囊未创建、无书名删除线",
             _r5 ~= nil and EM.PillOf(_r5, "fTag") ~= nil and EM.PillOf(_r5, "fTag").__shown == true
             and tostring(EM.PillOf(_r5, "fTag").t.__text) == "部落领地"
             and EM.PillOf(_r5, "lvTag") ~= nil
             and tostring(EM.PillOf(_r5, "lvTag").t.__text) == "10~20级"
             and EM.PillOf(_r5, "unTag") == nil
             and _r5.unStrike ~= nil and _r5.unStrike.__shown ~= true,
             _r5 and EM.PillOf(_r5, "lvTag") and tostring(EM.PillOf(_r5, "lvTag").t.__text))
          ck("★ 行21（荆棘谷 30~44·推荐）：等级胶囊 + 推荐金胶囊、领地胶囊未创建",
             _r21 ~= nil and EM.PillOf(_r21, "lvTag") ~= nil
             and tostring(EM.PillOf(_r21, "lvTag").t.__text) == "30~44级"
             and EM.PillOf(_r21, "recTag") ~= nil
             and tostring(EM.PillOf(_r21, "recTag").t.__text) == "推荐"
             and EM.PillOf(_r21, "fTag") == nil,
             _r21 and EM.PillOf(_r21, "lvTag") and tostring(EM.PillOf(_r21, "lvTag").t.__text))
          -- 2026-09-29 三方核对：网罗谎言（行19）已被双站确认 → 待确认/删除线全撤、书名回白
          ck("★ 行19（阿拉希 30~40·已确认）：等级胶囊在、待确认/推荐胶囊未创建、删除线撤、书名回白",
             _r19 ~= nil and EM.PillOf(_r19, "lvTag") ~= nil
             and tostring(EM.PillOf(_r19, "lvTag").t.__text) == "30~40级"
             and EM.PillOf(_r19, "unTag") == nil
             and EM.PillOf(_r19, "recTag") == nil
             and _r19.unStrike ~= nil and _r19.unStrike.__shown == false
             and _r19.a.__textColor ~= nil and math.abs(_r19.a.__textColor[1] - 0.88) < 1e-6,
             _r19 and EM.PillOf(_r19, "lvTag") and tostring(EM.PillOf(_r19, "lvTag").t.__text))
          local _r26 = EM.rows and EM.rows[26]
          ck("★ 行26（The Liminal and the Arcane·菲拉斯·移位失踪）：待确认灰胶囊 + 删除线 + 书名灰、推荐胶囊未创建",
             _r26 ~= nil and EM.PillOf(_r26, "unTag") ~= nil
             and tostring(EM.PillOf(_r26, "unTag").t.__text) == "待确认"
             and EM.PillOf(_r26, "recTag") == nil
             and _r26.unStrike ~= nil and _r26.unStrike.__shown == true
             and _r26.a.__textColor ~= nil and math.abs(_r26.a.__textColor[1] - 0.55) < 1e-6,
             _r26 and EM.PillOf(_r26, "unTag") and tostring(EM.PillOf(_r26, "unTag").t.__text))
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

    local data = TF_NS.DungeonData
    ck("副本数据 35 条", data and data.dungeons and #data.dungeons == 35,
       data and data.dungeons and #data.dungeons)

    -- ---------- 列表视图 ----------
    U:SetDungeonView("list")
    ck("列表视图已选中", U.dungeonView == "list")
    local child0 = U.dungeonListChild
    local pool0  = U.dungeonListPool
    ck("列表滚动容器 + 子帧都在", U.dungeonListScroll ~= nil and child0 ~= nil)
    ck("★ 子帧父级 = 滚动容器（未被解挂）", child0.__parent == U.dungeonListScroll)

    local nCard, nShown = #pool0.card, 0
    for _, c in ipairs(pool0.card) do if c.__shown then nShown = nShown + 1 end end
    ck("卡片池尺寸 = 副本总数", nCard == 35, nCard)
    ck("35 张卡全部显示", nShown == 35, nShown)
    ck("三组标题建出（现在可以进入/推荐/还需升级）", #pool0.hdr == 3, #pool0.hdr)

    -- 等级 16：三组各自的数量对不对（分组口径 = DG.GroupOf）
    local nNow, nRec, nUp = 0, 0, 0
    for _, d in ipairs(data.dungeons) do
      if d.levelMin > 16 then nUp = nUp + 1
      elseif d.levelMax and 16 <= d.levelMax then nRec = nRec + 1
      else nNow = nNow + 1 end
    end
    ck("lv16 三组合计 = 35", nNow + nRec + nUp == 35,
       ("now=%d rec=%d up=%d"):format(nNow, nRec, nUp))
    local shownTip = 0
    for _, c in ipairs(pool0.card) do if c.__shown and c.__tip then shownTip = shownTip + 1 end end
    ck("每张显示的卡都写了 __tip（tooltip 不悬空）", shownTip == 35, shownTip)
    local withD = 0
    for _, c in ipairs(pool0.card) do if c.__shown and c.__d then withD = withD + 1 end end
    ck("每张显示的卡都绑了 __d（点击能进详情）", withD == 35, withD)

    -- ---------- 底图来源：客户端加载图优先，取不到落纯色（2026-09-22 三处统一） ----------
    -- 桩的 Texture 记 __tex（SetTexture 入参）与 __ct（SetColorTexture 入参），但**不清旧字段**；
    -- 池化卡片会被不同来源的副本复用 → 直接读会拿到上一轮的残留。故先手动把两者都置成
    -- 哨兵值 "CLEARED"，再触发一次刷新，记录必然来自本轮。
    -- camelot160 那 4 张只有 1.60 端有 → 泰坦端(ns.IsForever=false)那 4 个副本也落纯色，
    -- 故两端的「客户端图 / 纯色」张数不同。
    do
      local solidOnly = {
        the_drowned_city = true, kroldok_stronghold = true, alcaz_prison = true,
        blackmaw_hold = true, shapers_terrace = true,
      }
      for _, c in ipairs(pool0.card) do
        if c.art then c.art.__tex, c.art.__ct = "CLEARED", nil end
      end
      -- UpdateDungeons 只在「等级变了」时才重建卡片墙（U.dungeonListLevel 缓存）。
      -- 这里把缓存置 -1 强制走一次 DG.BuildList，而不改 PLAYER_LEVEL（免影响后续分组断言）。
      U.dungeonListLevel = -1
      U:UpdateDungeons()
      local nClient, nSolid, nBad, nMissSolid = 0, 0, 0, 0
      for _, c in ipairs(pool0.card) do
        if c.__shown and c.art then
          local needSolid = solidOnly[c.__d and c.__d.id] == true
          if type(c.art.__tex) == "number" then
            nClient = nClient + 1
            if needSolid then nBad = nBad + 1 end
          elseif c.art.__ct ~= nil then
            nSolid = nSolid + 1
            if needSolid then nMissSolid = nMissSolid + 1 end
          else nBad = nBad + 1 end          -- 本轮一个都没设（哨兵没被覆盖）
        end
      end
      local forever = TF_NS.IsForever == true
      local expClient = forever and 30 or 26      -- camelot160 那 4 张只有 1.60 端有
      local expSolid  = forever and 5 or 9
      ck("★ 卡片底图走客户端加载图（FileDataID 数字）", nClient == expClient,
         ("%d/%d"):format(nClient, expClient))
      ck("★ 客户端无图的副本落纯色底（非图片、非留白）", nSolid == expSolid,
         ("%d/%d"):format(nSolid, expSolid))
      ck("★ 客户端确实无图的那 5 个必落纯色", nMissSolid == 5, nMissSolid)
      ck("★ 底图来源与副本一一对应（错配 = 0）", nBad == 0, nBad)
    end

    -- ---------- 反复刷新：升级路径 ----------
    FRAMES = 0
    PLAYER_LEVEL = 58; U:UpdateDungeons()
    ck("★ 升到 58 后列表子帧仍是同一对象", U.dungeonListChild == child0)
    ck("★ 升到 58 零新建帧（池化，不重建）", FRAMES == 0, FRAMES)
    ck("升到 58 不换池", U.dungeonListPool == pool0)

    FRAMES = 0
    PLAYER_LEVEL = 16; U:UpdateDungeons()
    PLAYER_LEVEL = 30; U:UpdateDungeons()
    PLAYER_LEVEL = 60; U:UpdateDungeons()
    PLAYER_LEVEL = 16; U:UpdateDungeons()
    ck("★ 反复切换等级零新建帧", FRAMES == 0, FRAMES)
    ck("★ 反复切换等级子帧恒定", U.dungeonListChild == child0)

    -- ---------- 详情：掉落明细（数据来自 ns.DungeonLoot） ----------
    -- ★ 2026-10-09 懒构建：详情滚动容器也走 DG.EnsureDetailBuilt()（渲染入口按需补建）；
    --   沙盒里插件命名空间是 TF_NS，DG 走 ns.DungeonModule 导出口。
    TF_NS.DungeonModule.EnsureDetailBuilt()
    local dc0 = U.dungeonDetailChild
    local pool0 = U.dungeonDetailPool
    ck("详情滚动容器 + 子帧都在", U.dungeonDetailScroll ~= nil and dc0 ~= nil)
    ck("★ 详情子帧父级 = 详情滚动容器", dc0.__parent == U.dungeonDetailScroll)
    ck("详情池是两级（来源标题 + 物品行）",
       type(pool0) == "table" and type(pool0.hdr) == "table" and type(pool0.item) == "table")

    local loot = TF_NS.DungeonLoot
    local nDg = 0
    if type(loot) == "table" then for _ in pairs(loot) do nDg = nDg + 1 end end
    ck("掉落数据已装载且覆盖 36 个副本（35 副本 + 奥妮克希亚的巢穴）", nDg == 36, nDg)

    local hall, scholo, stockade, emptyDg, noDropDg, dm
    for _, d in ipairs(data.dungeons) do
      if d.id == "hall_of_thanes" then hall = d
      elseif d.id == "scholomance" then scholo = d
      elseif d.id == "the_stockade" then stockade = d
      elseif d.id == "the_drowned_city" then emptyDg = d
      elseif d.id == "excavation_wetlands" then noDropDg = d
      elseif d.id == "the_deadmines" then dm = d end
    end
    ck("定位到 6 个样例副本", hall and scholo and stockade and emptyDg and noDropDg and dm)

    -- 首次渲染：领主大厅 = 4 来源 / 13 件
    -- 先把常驻的物品数据监听器建出来（它只 create 一个 Frame），
    -- 免得它混进「首次渲染新建了多少行帧」的计数里
    TF_NS.DungeonModule.EnsureItemListener()
    -- 隐藏 tooltip（RequestItem 的第三路触发）也是常驻一次性帧：先让它建出来，
    -- 之后任何请求都不该再新建帧 —— 顺手把这条钉住，也免得它混进首屏帧计数。
    TF_NS.DungeonModule.RequestItem(6948, true)
    FRAMES = 0
    TF_NS.DungeonModule.RequestItem(6949, true)
    ck("★ 物品预热帧只建一次（再次 RequestItem 零新建帧）", FRAMES == 0, FRAMES)
    FRAMES = 0
    U:ShowDungeonDetail(hall)
    ck("★ 首次渲染后子帧仍是构建时那个", U.dungeonDetailChild == dc0)
    ck("来源标题池 = 4", #pool0.hdr == 4, #pool0.hdr)
    ck("物品行池 = 13（首次新建）", #pool0.item == 13, #pool0.item)
    ck("首次渲染恰好新建 35 帧（2026-10-14 心愿星标钮：22 + 13 行掉落 × 1 星标钮）",
       FRAMES == 35, FRAMES)
    ck("行帧父级 = 详情子帧", pool0.item[1].__parent == dc0)
    ck("行帧绑了 __it（悬停能出物品提示框）", pool0.item[1].__it ~= nil)
    -- 此刻桩里还没有任何客户端物品口（GetItemInfo / C_Item 都是 nil）：名字只能是占位文案、
    -- 部位留空、图标退客户端自带问号图。这条同时守住「客户端没数据时绝不回退站点名」。
    ck("★★ 客户端无数据时行帧名是占位文案（不回退站点名）",
       pool0.item[1].name.__text == "暂时没有客户端数据", pool0.item[1].name.__text)
    ck("★ 客户端无数据时部位行留空", (pool0.item[1].tp.__text or "") == "", pool0.item[1].tp.__text)
    ck("★ 客户端无数据时图标退客户端自带问号图",
       tostring(pool0.item[1].icon.__tex or ""):find("QuestionMark", 1, true) ~= nil,
       pool0.item[1].icon.__tex)
    ck("进详情后列表隐藏 / 详情显示",
       U.dungeonListScroll.__shown == false and U.dungeonDetail.__shown == true)
    ck("详情标题已填", (U.dungeonDetailTitle.__text or "") ~= "", U.dungeonDetailTitle.__text)
    ck("详情元信息已填", (U.dungeonDetailMeta.__text or "") ~= "", U.dungeonDetailMeta.__text)
    ck("有掉落时顶部空态提示隐藏", U.dungeonDetailNote.__shown == false)

    -- 池扩容 / 回缩：通灵学院 16 来源 / 292 件 → 监狱 3 来源 / 5 件
    U:ShowDungeonDetail(scholo)
    ck("通灵学院：来源 16 / 行 292", #pool0.hdr == 16 and #pool0.item == 292,
       (#pool0.hdr) .. "/" .. (#pool0.item))
    FRAMES = 0
    U:ShowDungeonDetail(stockade)
    ck("★ 缩到「监狱」零新建帧", FRAMES == 0, FRAMES)
    ck("池只增不减（仍 292）", #pool0.item == 292, #pool0.item)
    local shownRows = 0
    for _, r in ipairs(pool0.item) do if r.__shown then shownRows = shownRows + 1 end end
    -- ★ fc 回铺后监狱 3 件 → 36 件（件数随数据浮动，从数据现算：Σ来源物品数）
    local _stockRows = 0
    for _, src in ipairs(TF_NS.DungeonLoot[stockade.id] or {}) do
      _stockRows = _stockRows + #(src[5] or {})
    end
    ck("只显示「数据行数」行、其余隐藏（池复用不缩容）",
       _stockRows > 0 and shownRows == _stockRows,
       shownRows .. " / 数据 " .. _stockRows)

    -- 反复切换（含空数据副本）→ 子帧恒定 + 不再新建帧
    FRAMES = 0
    U:ShowDungeonDetail(hall)
    U:ShowDungeonDetail(scholo)
    U:ShowDungeonDetail(emptyDg)
    U:ShowDungeonDetail(hall)
    ck("★ 反复切换 4 次零新建帧", FRAMES == 0, FRAMES)
    ck("★ 反复切换子帧恒定", U.dungeonDetailChild == dc0)

      -- ★★ 团本详情 = 跳转复用五人本整套（2026-10-11 二稿）
      do
        local RM = TF_NS.RaidModule
        local _det = RM.DETAILS and RM.DETAILS["奥妮克希亚的巢穴"]
        local _nDet = 0
        if RM.DETAILS then for _ in pairs(RM.DETAILS) do _nDet = _nDet + 1 end end
        ck("★★ 团本详情数据只登记 奥妮克希亚的巢穴（id onyxias_lair / 60 级 / 尘泥沼泽 / 首领 1）",
           _det ~= nil and _det.id == "onyxias_lair" and _det.levelMin == 60 and _det.levelMax == 60
           and _det.zone == "尘泥沼泽" and #(_det.bosses or {}) == 1 and _nDet == 1,
           _det and tostring(_det.id))
        do
          local _al = TF_NS.DungeonQuestAlias and TF_NS.DungeonQuestAlias["onyxias_lair"]
          ck("★★ 奥巢任务签 = 开门链别名清单 25 条（A 11 + H 14）",
             _al ~= nil and #_al == 25, _al and tostring(#_al))
          local _rows = TF_NS.DungeonQuests and TF_NS.DungeonQuests["onyxias_lair"]
          ck("★★ 开门链补缺行 16 条落在 onyxias_lair 块（A6 + H10）",
             _rows ~= nil and #_rows == 16, _rows and tostring(#_rows))
          local _ids = {}
          if _rows then for _, _rq in ipairs(_rows) do _ids[_rq[1]] = true end end
          ck("★★ 补缺行 id 无全局撞车（含 4241 深渊美酒节行，靠确定性排序由奥巢行胜出）",
             _ids[4182] and _ids[6403] and _ids[6501] and _ids[4941] and _ids[6585] and _ids[6601]
             and not _ids[6502] and not _ids[6602] and not _ids[4903])
          local _gd = TF_NS.DungeonGuide and TF_NS.DungeonGuide["onyxias_lair"]
          ck("★★ 奥巢攻略条目：tagline + 8 条提示（开门 5 + 战斗 3）+ 双阵营入口说明",
             _gd ~= nil and type(_gd.tagline) == "string" and _gd.tips and #_gd.tips == 8
             and _gd.entrance and _gd.entrance.H and _gd.entrance.A,
             _gd and type(_gd.tagline))
          ck("★★ 奥巢攻略补全（2026-10-11）：trash 卫士巡逻队 + Onyxia 三阶段打法（en 名对齐掉落表）",
             _gd.trash and #_gd.trash == 1 and _gd.trash[1].title and _gd.trash[1].text
             and _gd.bosses and #_gd.bosses == 1 and _gd.bosses[1].en == "Onyxia"
             and type(_gd.bosses[1].text) == "string" and #_gd.bosses[1].text >= 200,
             _gd.bosses and tostring(_gd.bosses[1] and _gd.bosses[1].en))
          local _bs = TF_NS.BossSkills and TF_NS.BossSkills["onyxias_lair"]
          local _ob = _bs and _bs["Onyxia"]
          ck("★★ 奥巢首领技能 = 5 条法术 id 行（扫击/翼击/火球/深呼吸/恐吓咆哮=14100，与掉落表 en 名同键）",
             _ob ~= nil and #_ob == 5 and _ob[1][3] == 15847 and _ob[2][3] == 18500
             and _ob[3][3] == 18392 and _ob[4][3] == 17086 and _ob[5][3] == 14100,
             _ob and tostring(#_ob))
        end
        do
          local _lt = TF_NS.DungeonLoot and TF_NS.DungeonLoot["onyxias_lair"]
          local _src = _lt and _lt[1]
          ck("★★ 奥巢掉落表 = Onyxia 单来源 20 件（头颅必掉 100%）",
             _src ~= nil and _src[1] == "Onyxia" and _src[4] == "10184"
             and #(_src[5] or {}) == 20 and _src[5][1][1] == 18423 and _src[5][1][2] == 100,
             _src and tostring(#(_src[5] or {})))
          ck("★★ 奥巢地图：客户端瓦片层 + 入口钉 33.9,20.7 + 首领钉 67.2,30.7 + 世界地图入口 1445",
             TF_NS.BossPos and TF_NS.BossPos["onyxias_lair"]
             and TF_NS.BossPos["onyxias_lair"]["Onyxia"][1][1] == 67.2
             and TF_NS.MapPins and TF_NS.MapPins["onyxias_lair"]
             and TF_NS.MapPins["onyxias_lair"].entrance[1][1] == 33.9
             and TF_NS.DungeonEntry and TF_NS.DungeonEntry["onyxias_lair"] ~= nil
             and TF_NS.DungeonEntry["onyxias_lair"][1] == 1445)
          local _art = U.CardArtFor and U.CardArtFor({ id = "onyxias_lair" })
          ck("★★ 奥巢卡面美术 = OnyxiasLairWide TGA",
             type(_art) == "string" and _art:find("OnyxiasLairWide", 1, true) ~= nil,
             type(_art) == "string" and _art or tostring(_art))
          ck("★★ 列表渲染后奥巢卡 art 已贴图并压暗（预告卡保持纯色底）",
             RM.cards[3] ~= nil and RM.cards[3].art ~= nil
             and RM.cards[3].art.__shown == true and RM.cards[3].dim.__shown == true
             and RM.cards[1].art.__shown ~= true,
             RM.cards[3] and tostring(RM.cards[3].art.__shown))
        end
        ck("★★ 奥妮克希亚的巢穴卡 = 可点入口（entry = true），其余首批卡不可点",
           RM.DATA.raids[3] ~= nil and RM.DATA.raids[3].entry == true
           and RM.DATA.raids[1].entry == nil and RM.DATA.raids[2].entry == nil)
        local _rec = RM.DungeonRec and RM.DungeonRec("奥妮克希亚的巢穴")
        ck("★★ DungeonRec 产出五人本详情所需的记录字段",
           _rec ~= nil and _rec.id == "onyxias_lair" and _rec.name == "奥妮克希亚的巢穴"
           and _rec.nameEn == "Onyxia's Lair" and _rec.levelMin == 60
           and _rec.levelMax == 60 and _rec.zone == "尘泥沼泽" and _rec.bossCount == 1
           and _rec.raid == true,
           _rec and tostring(_rec.id .. "/" .. tostring(_rec.raid)))
        ck("★★ 列表卡渲染时挂 rec（点击门控的数据来源，漏挂 = 点击静默无效）",
           RM.cards[3] ~= nil and RM.cards[3].rec == RM.DATA.raids[3]
           and RM.cards[1].rec == RM.DATA.raids[1],
           RM.cards[3] and tostring(RM.cards[3].rec == RM.DATA.raids[3]))
        local _okOpen, _errOpen = pcall(function() RM.OpenDetail("奥妮克希亚的巢穴") end)
        ck("★★ 点卡跳转：切到 5 人本页 + 打开同款详情（curSub / 详情记录 / 详情可见）",
           _okOpen and U.curSub == "Dungeons" and U.dungeonDetailCur ~= nil
           and U.dungeonDetailCur.id == "onyxias_lair" and U.dungeonDetailCur.raid == true
           and U.dungeonDetail ~= nil
           and U.dungeonDetail.__shown == true and U.raidPage.__shown == false,
           tostring(_errOpen or (U.curSub .. " / " .. tostring(U.dungeonDetailCur and U.dungeonDetailCur.id))))
        ck("★★ 跳转后返回键按来源分流：文案「‹ 团本」",
           U.dungeonBack ~= nil and U.dungeonBack:GetText() == "‹ 团本",
           U.dungeonBack and tostring(U.dungeonBack:GetText()))
        local _okCapsule = pcall(function() U:SetSubCapsule("Raids") end)
        ck("★★ 胶囊 override 可调（SetSubCapsule 挂上且不报错）",
           _okCapsule and type(U.SetSubCapsule) == "function",
           tostring(_okCapsule))
        local _okBackDun = pcall(function() U:SwitchSub("Dungeons") end)
        ck("★★ 团本详情态点「5 人本」胶囊：团本来源详情关掉回列表（SwitchSub 分支）",
           _okBackDun and U.curSub == "Dungeons" and U.dungeonDetail ~= nil
           and U.dungeonDetail.__shown == false,
           tostring(U.curSub))
        local _okBack = pcall(function() U:SwitchSub("Raids") end)
        ck("★★ 顶栏切回团本：团本页显、五人本页（含详情）收起",
           _okBack and U.curSub == "Raids" and U.raidPage.__shown == true
           and U.dungeonPage ~= nil and U.dungeonPage.__shown == false,
           tostring(U.curSub))
        local _okGuard = pcall(function() RM.OpenDetail("深穴") end)
        ck("★★ 未登记的团本不响应打开（无数据即拒绝，留在团本页）",
           _okGuard and U.curSub == "Raids"
           and (U.dungeonDetailCur == nil or U.dungeonDetailCur.id ~= 10),
           tostring(U.curSub))
        U:SwitchSub("Raids")
      end


    -- ★ 分类现在**只认客户端 classID**（原先按站点「部位」中文串判定）：桩里得先装上
    --   客户端物品口，否则客户端不认识任何物品 → 全归 other → 筛选档位恒空。
    --   塞恩大厅只有 1 件任务物品 = 274286 杜尔根·挽歌之锤的头颅（classID 12 = Questitem），
    --   其余按护甲（classID 4 = Armor）造；这正是「分类不再依赖站点中文串」的实测点。
    GetItemInfo, GetItemInfoInstant = nil, nil
    C_Item = {
      GetItemInfoInstant = function(id)
        if id == 274286 then return id, "任务", "任务物品", "", 135005, 12, 0 end
        return id, "护甲", "板甲", "INVTYPE_WAIST", 135005, 4, 1
      end,
    }
    U:ShowDungeonDetail(hall)

    -- 筛选行：只改可见性，绝不新建帧；数量按副本全部掉落算
    local nBtn = 0
    for _ in pairs(U.dungeonFilterBtns or {}) do nBtn = nBtn + 1 end
    ck("筛选按钮共 5 个（全部/武器/护甲/任务物品/仅新增）", nBtn == 5, nBtn)

    U:ShowDungeonDetail(hall)
    U:SetDungeonFilter("all")
    local nAll = 0
    for _, r in ipairs(pool0.item) do if r.__shown then nAll = nAll + 1 end end
    ck("「全部」下塞恩大厅 13 行（fc 回铺后池仍复用 13 帧显隐渲染全部掉落）", nAll == 13, nAll)
    -- 塞恩大厅只有 1 件任务物品（杜尔根·挽歌之锤的头颅）
    U:SetDungeonFilter("quest")
    local nQ = 0
    for _, r in ipairs(pool0.item) do if r.__shown then nQ = nQ + 1 end end
    ck("「任务物品」下只剩 1 行", nQ == 1, nQ)
    ck("筛选后标题池不膨胀", #pool0.hdr == 16, #pool0.hdr)
    -- ★ 2026-09-22：筛选按钮从「按 key 建表」改成**数组 + 渲染时重设语义**
    --   （掉落与任务两个页签共用一行：掉落 5 格、任务 3 格，用不到的当场隐藏）。
    --   ★★ 2026-10-04 方案 A：掉落页 1 号重设「类型」下拉（__key=__typeMenu）、2-5 隐藏
    --   （任务页签照旧全用）。点 1 号展开下拉菜单建 2 帧（下拉层，属预期）；2-5 隐藏态点击零新建。
    for i, key in ipairs({ "__typeMenu", "weapon", "armor", "quest", "new" }) do
      local bt = U.dungeonFilterBtns[i]
      ck("筛选按钮 " .. i .. " 存在且 __key 正确（1 号 = 类型下拉）",
         bt ~= nil and bt.__key == key and bt.__mode == "loot",
         bt and (tostring(bt.__mode) .. "/" .. tostring(bt.__key)))
      FRAMES = 0
      if bt and bt.__scripts and bt.__scripts.OnClick then
        bt.__scripts.OnClick()
      end
      if i == 1 then
        ck("点「类型」下拉展开 = 1 弹层 + #FILTERS 行（Hui ShowMenu 每开重建）",
           FRAMES == 1 + #TF_NS.DungeonModule.FILTERS, FRAMES)
      else
        ck("点筛选「" .. key .. "」（隐藏态）零新建帧", FRAMES == 0, FRAMES)
      end
      ck("点筛选「" .. key .. "」子帧恒定", U.dungeonDetailChild == dc0)
    end
    U:SetDungeonFilter("all")

    -- ---------- 详情：卡片墙几何（4 列 · 双行卡） ----------
    local DGn = TF_NS.DungeonModule
    local cw, chh = DGn.LOOT_CARD_W, DGn.LOOT_CARD_H
    ck("卡片 228 × 44（4 列 · 双行——2026-10-13 三外缘拉平：内容贴 detail 边，栅格 0 起）",
       cw == 228 and chh == 44, cw .. "x" .. chh)
    ck("卡片列数 = 4（2026-10-01 用户：一行 3 件 → 4 件）", DGn.LOOT_COLS == 4, DGn.LOOT_COLS)
    ck("★ 3 列 + 列距刚好装进滚动内容宽（末张卡右缘不越界）",
       cw * DGn.LOOT_COLS + (DGn.LOOT_COLS - 1) * DGn.LOOT_GAP_X <= DGn.CHILD_W,
       (cw * DGn.LOOT_COLS + (DGn.LOOT_COLS - 1) * DGn.LOOT_GAP_X) .. " / " .. DGn.CHILD_W)
    -- 容量守门：全库最长物品名 16 个汉字，中文全角字宽 ≈ 字号，故「字号 × 16」≈ 需要宽度。
    -- ★ 基准卡宽固定按「3 列」算，不取 DG.LOOT_CARD_W —— 变异验证是全部变异一次性注入的，
    --   若把列数也一起改掉，卡变宽会把「字号超标」这条掩盖掉（实测踩过）。
    local ref3 = math.floor((DGn.CHILD_W - 2 * DGn.LOOT_GAP_X) / 3)
    ck("★ 名称字号 ≤ 15（16 号在 3 列卡内会溢出；要更大必须改列数）",
       DGn.LOOT_FS_NAME <= 15, DGn.LOOT_FS_NAME)
    ck("★ 最长名字（16 字）在 3 列卡内放得下",
       DGn.LOOT_FS_NAME * 16 + 6 + DGn.LOOT_ICON + 7 + 7 <= ref3,
       (DGn.LOOT_FS_NAME * 16 + 6 + DGn.LOOT_ICON + 14) .. " / " .. ref3)

    U:ShowDungeonDetail(hall)
    U:SetDungeonFilter("all")
    -- SetPoint 记录的是最后一次调用的原始参数：("TOPLEFT", child, "TOPLEFT", x, y)
    local function px(cc) return cc.__pts and cc.__pts[4] end
    local function py(cc) return cc.__pts and cc.__pts[5] end
    local d1, d2, d3 = pool0.item[1], pool0.item[2], pool0.item[3]
    ck("卡片尺寸落在控件上", d1.__w == cw and d1.__h == chh, tostring(d1.__w) .. "x" .. tostring(d1.__h))
    ck("★ 同一排三张卡 x = 0 / 236 / 472（4 列：栅格 0 起，228 + 8 列距）",
       px(d1) == 0 and px(d2) == 236 and px(d3) == 472,
       tostring(px(d1)) .. "/" .. tostring(px(d2)) .. "/" .. tostring(px(d3)))
    ck("★ 同一排三张卡 y 一致（统一左上角锚，不混中心锚）",
       py(d1) == py(d2) and py(d2) == py(d3), tostring(py(d1)))
    -- 第 4 组「杜尔根·挽歌之锤」4 件 = 4 列下一整排（池下标 10..13，2026-10-01 起 4 列）
    -- ★ 2026-10-09 fc 回铺后组数/件数全变 → 下标写死必红，改钉**摆位规律**：
    --   x 只能落在 4 列上（0/236/472/708）；向右走必是 +236（同一排）；
    --   回卷到第 1 列必向下走至少一整行（换行/换组都成立）。首行贴顶。
    do
      local _colset = { [0]=true, [236]=true, [472]=true, [708]=true }
      local _badgeo, _shownG = 0, 0
      local _pvx, _pvy = nil, nil
      for _, r in ipairs(pool0.item) do
        if r.__shown then
          _shownG = _shownG + 1
          local xx, yy = px(r), py(r)
          if not _colset[xx] then _badgeo = _badgeo + 1
          elseif _pvx ~= nil and xx ~= 0 and xx <= _pvx then _badgeo = _badgeo + 1
          elseif _pvx ~= nil and xx == 0
                 and yy > _pvy - (DGn.LOOT_CARD_H + DGn.LOOT_GAP_Y) then
            _badgeo = _badgeo + 1
          end
          _pvx, _pvy = xx, yy
        end
      end
      ck("★ 4 列摆位规律（x 循环 4 列 0/236/472/708、向右必 +236、回第 1 列必降一整行）",
         _shownG > 0 and _badgeo == 0,
         _shownG .. " 行 / 异常 " .. _badgeo)
    end
    ck("★ 组间距 = 排距 + 标题行高 + 组间留白（高度算法不变形）",
       py(d1) - py(pool0.item[4]) == (chh + DGn.LOOT_GAP_Y) + DGn.LOOT_HDR_H + DGn.LOOT_GRP_GAP,
       tostring(py(d1) - py(pool0.item[4])))
    ck("卡片绑了 __it（悬停取值来源不变）", d1.__it ~= nil and d3.__it ~= nil)

    -- 底色复位（2026-10-10 hui 圆角卡改走 HuiCardState）：
    --   hui 路径 = 刷新后悬停胶囊 __hov 全部隐藏（底显隐由视图定）；
    --   旧路径   = SetBackdropColor 末次落在常态 alpha。两路任一成立即可。
    local seenA = {}
    local card0 = pool0.item[1]
    local origBd = card0.SetBackdropColor
    card0.SetBackdropColor = function(self, r, g, b, a)
      seenA[#seenA + 1] = a
      return origBd(self, r, g, b, a)
    end
    U:ShowDungeonDetail(hall)
    card0.SetBackdropColor = origBd
    local lastA = seenA[#seenA]
    local lootStateOK = true
    if card0.__huiCard then
      if card0.__hov then
        for _, t in ipairs(card0.__hov) do
          if t.__shown ~= false then lootStateOK = false end
        end
      end
    end
    ck("★ 每轮刷新都把卡片复位成常态（hui=悬停胶囊全隐 / 旧路径=常态 alpha）",
       (card0.__huiCard and lootStateOK) or (lastA ~= nil and math.abs(lastA - DGn.LOOT_CARD_BG) < 1e-6),
       tostring(lastA))

    -- ---------- 详情：物品展示**只用客户端数据**（站点物品属性已整体弃用） ----------
    -- 用户决定（2026-09-22）：站点口径不准 ——「水蛇法袍」站点 q=2 绿而游戏内 3 蓝，
    -- 全库 1807 件里 444 件不一致 → 名字 / 品质 / 部位 / 图标 / 分类全部只认客户端，
    -- 客户端拿不到就显示「暂时没有客户端数据」，**绝不回退站点**。
    --   名字：C_Item.GetItemInfo（异步）→ GetItemNameByID（同步）
    --   品质：同上 · 部位 / 图标 / 分类：C_Item.GetItemInfoInstant（同步静态数据，不必等）
    -- 品质色表索引基准：QUALTAB 是「quality + 1」的 1 基表，写 QUALTAB[q] 会整体偏一档
    -- （quality 3 蓝 → 取到绿）。真机上 ITEM_QUALITY_COLORS 是 0 基，桩里没有该全局，
    -- 所以只有这条断言能拦住偏移。
    local q3r, q3g, q3b = DGn.QColor(3)
    ck("★ 品质色按 quality 索引（3 = 稀有/蓝：b 大 g 小；错位一格会给出绿）",
       q3b > 0.5 and q3g < 0.5, q3r .. "," .. q3g .. "," .. q3b)

    -- 本端真实形态的客户端桩：全局 GetItemInfo / GetItemInfoInstant **都不存在**
    -- （实机 /tf qual 体检就是这个结果），只有 C_Item 命名空间下的口。
    GetItemInfo, GetItemInfoInstant = nil, nil
    C_Item = {
      GetItemInfo = function(id) return "测试装备", nil, 5 end,
      GetItemInfoInstant = function(id) return id, "护甲", "板甲", "INVTYPE_WAIST", 135005, 4, 1 end,
    }
    INVTYPE_WAIST = "腰部"
    U:ShowDungeonDetail(hall)
    U:SetDungeonFilter("all")

    -- ① 客户端有数据 → 名字 / 品质 / 部位 / 图标 / 分类全部按客户端（命名空间兜底真的生效）
    local er, eg, eb = DGn.QColor(5)
    local nBadColor, nName, nMeta = 0, 0, 0
    for _, r in ipairs(pool0.item) do
      if r.__shown and r.__it then
        local tc = r.name.__textColor
        if not (tc and math.abs(tc[1] - er) < 1e-6
                    and math.abs(tc[2] - eg) < 1e-6
                    and math.abs(tc[3] - eb) < 1e-6) then
          nBadColor = nBadColor + 1
        end
        if r.name.__text == "测试装备" then nName = nName + 1 end
        if r.tp.__text == "腰部 · 板甲" then nMeta = nMeta + 1 end
      end
    end
    ck("★ 卡片名色走客户端品质（客户端说 5 → 全部橙）",
       nBadColor == 0, nBadColor .. " 张没按客户端品质上色（期望 " .. er .. "," .. eg .. "," .. eb .. "）")
    ck("★★ 名字取客户端（全局口不存在 → 命名空间兜底真的生效）",
       nName > 0, nName .. " 张写了客户端名")
    ck("★ 部位行由客户端静态数据拼出（INVTYPE_WAIST → 腰部 · 板甲）",
       nMeta > 0, nMeta .. " 张写了「腰部 · 板甲」")
    ck("★ 图标取客户端 fileID（135005）",
       tostring(pool0.item[1].icon.__tex or "") == "135005", pool0.item[1].icon.__tex)
    ck("★ 分类走客户端 classID（4 = 护甲）", DGn.CatOf(1) == "armor", tostring(DGn.CatOf(1)))

    -- ② 客户端一点数据都没有 → 占位文案 + 灰字 + 空部位 + 问号图，**绝不回退站点**
    C_Item, INVTYPE_WAIST = nil, nil
    U:ShowDungeonDetail(hall)
    local r1c
    for _, r in ipairs(pool0.item) do if r.__shown and r.__it then r1c = r; break end end
    ck("★★ 客户端无数据时卡片名是占位文案（不回退站点名）",
       r1c.name.__text == "暂时没有客户端数据", r1c.name.__text)
    ck("★ 占位名是灰色（不是任何品质色）",
       r1c.name.__textColor and math.abs(r1c.name.__textColor[1] - 0.55) < 1e-6,
       r1c.name.__textColor and r1c.name.__textColor[1])
    ck("★ 客户端无数据时部位行留空、图标退问号图",
       (r1c.tp.__text or "") == ""
       and tostring(r1c.icon.__tex or ""):find("QuestionMark", 1, true) ~= nil,
       tostring(r1c.tp.__text) .. " / " .. tostring(r1c.icon.__tex))
    ck("★ 客户端无数据时分类归 other（不猜）", DGn.CatOf(1) == "other", tostring(DGn.CatOf(1)))

    -- ③ 只有同步口（GetItemNameByID / GetItemQualityByID）可用时名字与品质照样出得来
    --    —— 这就是「不必等异步到货、首帧就正确」的关键路径。
    C_Item = {
      GetItemNameByID = function(id) return "同步装备" end,
      GetItemQualityByID = function(id) return 4 end,
    }
    U:ShowDungeonDetail(hall)
    local sr, sg = DGn.QColor(4)
    ck("★★ 同步口可用时名字 / 品质照样出得来（不必等异步到货）",
       r1c.name.__text == "同步装备"
       and r1c.name.__textColor and math.abs(r1c.name.__textColor[1] - sr) < 1e-6,
       r1c.name.__text .. " / " .. tostring(r1c.name.__textColor and r1c.name.__textColor[1]))

    -- ④ 数据到货：占位名 + 灰字自动换成客户端真名 + 客户端品质，且只改、不重排
    local wailing
    for _, d in ipairs(data.dungeons) do
      if d.id == "wailing_caverns" then wailing = d end
    end
    C_Item = nil
    U:ShowDungeonDetail(wailing)
    local card6465, y6465
    for _, r in ipairs(pool0.item) do
      if r.__shown and r.__it and r.__it[1] == 6465 then card6465 = r; y6465 = py(r) end
    end
    ck("哀嚎洞穴里有 6465「水蛇法袍」这张卡（到货重刷的样本）", card6465 ~= nil)
    ck("★ 到货前该卡是占位文案",
       card6465 ~= nil and card6465.name.__text == "暂时没有客户端数据",
       card6465 and card6465.name.__text)
    local ev2 = DGn.__itemEvt
    C_Item = {
      GetItemInfo = function(id) return "水蛇法袍", nil, 3 end,
      GetItemInfoInstant = function(id) return id, "护甲", "布甲", "INVTYPE_CHEST", 135005, 4, 1 end,
    }
    INVTYPE_CHEST = "胸部"
    if ev2 and ev2.__scripts and ev2.__scripts.OnEvent then
      ev2.__scripts.OnEvent(ev2, "GET_ITEM_INFO_RECEIVED", 6465, true)
    end
    if SWEEPS then
      for i = #SWEEPS, 1, -1 do
        local s = SWEEPS[i]
        SWEEPS[i] = nil
        if s and s.fn then s.fn() end
      end
    end
    local cr, cg, cb = DGn.QColor(3)
    local tc2 = card6465 and card6465.name.__textColor
    ck("★ 到货后卡片名与色自动换成客户端口径（占位灰 → 真名 + 稀有蓝）",
       card6465 ~= nil and card6465.name.__text == "水蛇法袍"
       and tc2 and math.abs(tc2[1] - cr) < 1e-6 and math.abs(tc2[2] - cg) < 1e-6
            and math.abs(tc2[3] - cb) < 1e-6,
       (card6465 and card6465.name.__text) .. " / " .. (tc2 and table.concat(tc2, ",")))
    ck("★ 到货重刷顺带补上部位行（名字 / 品质 / 部位同源同刷）",
       card6465 ~= nil and card6465.tp.__text == "胸部 · 布甲", card6465 and card6465.tp.__text)
    ck("★ 到货重刷只改文字与颜色、不重排（位置不变）",
       card6465 ~= nil and py(card6465) == y6465, tostring(y6465))
    -- ④ 本端真实形态：全局 GetItemInfo / GetItemInfoInstant **为 nil**，客户端物品数据
    --    只在 C_Item 命名空间下（实机 `/tf qual` 体检就是这个结果）。裸调全局恒回 nil，
    --    于是品质静默回落站点 q —— 用户看到的就是「插件绿色、游戏蓝色」。
    GetItemInfo, GetItemInfoInstant = nil, nil
    C_Item = {
      GetItemInfo = function(id) return "NsItem", nil, 5 end,
      GetItemInfoInstant = function(id) return id, "护甲", "布甲", "", 135005, 4, 1 end,
    }
    ck("★ 取数口识别到命名空间形态（本端 GetItemInfo 不在全局）",
       DGn.ItemApiName() == "C_Item.GetItemInfo（命名空间）", tostring(DGn.ItemApiName()))
    U:ShowDungeonDetail(hall)
    local xr, xg, xb = DGn.QColor(5)
    local nNs = 0
    for _, r in ipairs(pool0.item) do
      if r.__shown and r.__it then
        local tc = r.name.__textColor
        if tc and math.abs(tc[1] - xr) < 1e-6 and math.abs(tc[2] - xg) < 1e-6
              and math.abs(tc[3] - xb) < 1e-6 then nNs = nNs + 1 end
      end
    end
    ck("★★ 全局取数口缺失时仍按客户端品质上色（命名空间兜底真的生效）",
       nNs > 0, nNs .. " 张按客户端（命名空间）品质上色")
    ck("★ 图标也能从命名空间取（同步静态数据，与站点图标名无关）",
       DGn.ItemIcon(1) == 135005, tostring(DGn.ItemIcon(1)))
    C_Item = nil
    U:ShowDungeonDetail(hall)

    -- 空数据副本（沉没之城：站点连 boss 名单都没公布）
    FRAMES = 0
    U:ShowDungeonDetail(emptyDg)
    ck("★ 空数据副本零新建帧", FRAMES == 0, FRAMES)
    ck("空数据副本提示「尚未公布 boss 名单」",
       U.dungeonDetailNote.__shown == true
       and tostring(U.dungeonDetailNote.__text or ""):find("boss 名单", 1, true) ~= nil,
       U.dungeonDetailNote.__text)
    local anyRow = 0
    for _, r in ipairs(pool0.item) do if r.__shown then anyRow = anyRow + 1 end end
    ck("空数据副本不显示任何物品行", anyRow == 0, anyRow)

    -- 有名单、掉落未公布 → 每个来源一行「暂无掉落数据」。
    -- ★ 2026-10-09 fc 全量回铺后「有名单、无掉落」中间态已绝迹：要么有掉落、
    --   要么连名单都没有（走上面 3500 的空态）。改钉终态 + 场景守卫：
    --   全库扫不到该形态时记绿（合法终态）；将来再出现则继续按空态口径验。
    local realNoDrop
    for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
      local ld = TF_NS.DungeonLoot and TF_NS.DungeonLoot[dg.id]
      if ld ~= nil and next(ld) ~= nil then
        local _allEmpty = true
        for _, s in ipairs(ld) do
          if #(s[5] or {}) > 0 then _allEmpty = false break end
        end
        if _allEmpty then realNoDrop = dg break end
      end
    end
    ck("★ fc 全量回铺后全库无「有名单、无掉落」副本（中间态绝迹 = 合法终态）",
       realNoDrop == nil)
    if realNoDrop then
      U:ShowDungeonDetail(realNoDrop)
      -- 注意：池只增不减，所以这里数「显示中」的标题行，不能数池长度
      local shownHdr = 0
      for _, h in ipairs(pool0.hdr) do if h.name.__shown then shownHdr = shownHdr + 1 end end
      ck("未公布掉落：来源标题全亮出", shownHdr > 0, shownHdr)
      local noteRows = 0
      for _, r in ipairs(pool0.item) do
        if r.__shown and r.note.__shown then noteRows = noteRows + 1 end
      end
      ck("未公布掉落：每来源一行「暂无掉落数据」", noteRows == shownHdr, noteRows .. "/" .. shownHdr)
      ck("未公布掉落：顶部空态提示隐藏", U.dungeonDetailNote.__shown == false)
    end

    U:ShowDungeonDetail(hall)   -- 收尾回到有数据的副本

    -- ---------- 滚轮：内容超出一屏时能往下滚 ----------
    -- 用户症状：「很多内容一页放不下，但是又不能往下滑」。根因 = 详情 ScrollFrame 没绑滚轮。
    -- 先纯算术验证 DG.WheelScroll 本身（自带上下夹取）。
    local DGw = TF_NS.DungeonModule
    local fv = 0
    local fakeScroll = {
      GetHeight = function() return 100 end,
      GetVerticalScroll = function() return fv end,
      SetVerticalScroll = function(_, v) fv = v end,
    }
    local fakeChild = { GetHeight = function() return 300 end }
    DGw.WheelScroll(fakeScroll, fakeChild, -1)
    ck("★ 下滚一步 = 48px", fv == 48, fv)
    DGw.WheelScroll(fakeScroll, fakeChild, 1)
    ck("★ 上滚一步回到顶", fv == 0, fv)
    DGw.WheelScroll(fakeScroll, fakeChild, 1)
    ck("★ 到顶不越界（夹在 0）", fv == 0, fv)
    fv = 9999
    DGw.WheelScroll(fakeScroll, fakeChild, -1)
    ck("★ 到底不越界（上限 = 内容高 - 视口高 = 200）", fv == 200, fv)
    fv = 0
    DGw.WheelScroll(fakeScroll, { GetHeight = function() return 50 end }, -1)
    ck("★ 内容不足一屏时不滚", fv == 0, fv)
    local okNil = pcall(DGw.WheelScroll, nil, nil, -1)
    ck("★ 缺参不报错（scroll/child 为 nil 直接返回）", okNil == true)

    -- 真控件：详情容器 + 卡片都挂了 OnMouseWheel，且转发真的落到滚动容器上。
    -- ⚠️ 桩的 GetHeight / GetVerticalScroll 都在 NUMERIC 表里 → 一律回 100：
    --    直接跑「视口 100 / 内容 100」会算出 maxScroll = 0，转发有没有生效根本看不出来。
    --    所以临时把四个取值点换成有意义的数（视口 200 / 内容 500），跑完立刻还原。
    U:ShowDungeonDetail(scholo)                      -- 292 件，内容远超一屏
    local dscroll, dc = U.dungeonDetailScroll, U.dungeonDetailChild
    local lscroll, lc = U.dungeonListScroll, U.dungeonListChild
    ck("★ 详情滚动容器挂了 OnMouseWheel（本次「滚不动」的根因）",
       dscroll.__scripts ~= nil and dscroll.__scripts.OnMouseWheel ~= nil)
    local dcard = pool0.item[1]
    local lcard = U.dungeonListPool.card[1]
    ck("★ 掉落卡片挂了 OnMouseWheel（鼠标压在卡上也能滚）",
       dcard ~= nil and dcard.__scripts ~= nil and dcard.__scripts.OnMouseWheel ~= nil)
    ck("★ 列表卡片挂了 OnMouseWheel（鼠标压在卡上也能滚）",
       lcard ~= nil and lcard.__scripts ~= nil and lcard.__scripts.OnMouseWheel ~= nil)

    -- ⚠️ GetVerticalScroll 也必须一起换：桩恒回 100，不换的话「下滚 48」会算成 100+48=148
    --    （实测踩过：列表那侧漏换 → 只有列表这条红）。
    local okp = {
      dH = dscroll.GetHeight, dV = dscroll.GetVerticalScroll, dS = dscroll.SetVerticalScroll,
      dchH = dc.GetHeight, lH = lscroll.GetHeight, lS = lscroll.SetVerticalScroll,
      lV = lscroll.GetVerticalScroll, lcH = lc.GetHeight,
    }
    local dv, lv = 0, 0
    dscroll.GetHeight = function() return 200 end
    dc.GetHeight = function() return 500 end
    dscroll.GetVerticalScroll = function() return dv end
    dscroll.SetVerticalScroll = function(_, v) dv = v; return dscroll end
    lscroll.GetHeight = function() return 200 end
    lc.GetHeight = function() return 500 end
    lscroll.GetVerticalScroll = function() return lv end
    lscroll.SetVerticalScroll = function(_, v) lv = v; return lscroll end

    dcard.__scripts.OnMouseWheel(dcard, -1)
    ck("★ 压在掉落卡片上滚轮 → 详情下滚 48px", dv == 48, dv)
    dv = 0
    dscroll.__scripts.OnMouseWheel(dscroll, -1)
    ck("★ 详情容器自身滚轮也能滚（48px）", dv == 48, dv)
    dv = 0
    dscroll.__scripts.OnMouseWheel(dscroll, 1)
    ck("★ 上滚不越界（夹在 0）", dv == 0, dv)
    dv = 400
    dscroll.__scripts.OnMouseWheel(dscroll, -1)
    ck("★ 到底了再滚不越界（上限 500-200 = 300）", dv == 300, dv)
    lcard.__scripts.OnMouseWheel(lcard, -1)
    ck("★ 压在列表卡片上滚轮 → 列表下滚 48px", lv == 48, lv)
    dv = 777
    U:ShowDungeonDetail(hall)
    ck("★ 开详情把滚动位置复位到顶（换副本不残留上一本的滚动位置）", dv == 0, dv)

    dscroll.GetHeight, dscroll.GetVerticalScroll = okp.dH, okp.dV
    dscroll.SetVerticalScroll, dc.GetHeight = okp.dS, okp.dchH
    lscroll.GetHeight, lscroll.SetVerticalScroll, lc.GetHeight = okp.lH, okp.lS, okp.lcH
    lscroll.GetVerticalScroll = okp.lV

    -- ---------- 掉落物品的鼠标提示 ----------
    -- 用户诉求：悬停某件装备要能直接看到「这件装备是干什么的 / 有什么数值」。
    -- 两级取值：客户端能解析 itemID 就走原生（SetItemByID / SetHyperlink）；解析不出就只给
    -- 「客户端确实拿得到的名字 / 部位 + 一句实话」。★ 站点物品资料已整体弃用（2026-09-22）。
    -- ★ 2026-09-22 第二轮：**提示框上连「站点」二字都不许出现** —— 用户原话「标出站点出处，
    --   搞得好像我这些数据都是从网站上拷下来的」。掉率只在卡片上以纯数字呈现（DG.Pct）。
    ck("★★ 站点提示数据文件已卸下（ns.DungeonTips / DungeonTipsF 都不存在）",
       TF_NS.DungeonTips == nil and TF_NS.DungeonTipsF == nil)

    local row
    for _, r in ipairs(pool0.item) do
      if not row and r.__shown and r.__it then row = r end
    end
    ck("详情里有绑了 __it 的物品行（悬停提示的取值来源）", row ~= nil)
    if row then
      local it = row.__it
      ck("物品行挂了 OnEnter / OnLeave",
         row.__scripts.OnEnter ~= nil and row.__scripts.OnLeave ~= nil)

      -- 情形①：客户端什么都说不出（命名空间与全局取数口都不在）→ 两行：itemID + 直言未收录，
      --         **没有任何站点物品资料、也没有「加载中」这类承诺**（判据必须能被证伪）。
      C_Item = nil
      GetItemInfo, GetItemInfoInstant = nil, nil
      GameTooltip.SetItemByID = false
      GameTooltip.SetHyperlink = function(self) self.__n = 1 end
      GameTooltip.NumLines = function(self) return self.__n or 0 end
      TOOLTIP_LINES = {}
      row.__scripts.OnEnter(row)
      local n1 = #TOOLTIP_LINES
      local joined = table.concat(TOOLTIP_LINES, "\n")
      ck("★★ 客户端未收录时提示框直言「客户端未收录此物品」",
         joined:find("客户端未收录此物品", 1, true) ~= nil,
         n1 .. " 行：" .. tostring(TOOLTIP_LINES[1]))
      ck("★★ 兜底提示框不再渲染任何站点物品资料（无「物品等级」/「需要等级」行）",
         joined:find("物品等级", 1, true) == nil
         and joined:find("需要等级", 1, true) == nil, n1 .. " 行")
      ck("★★ 提示框上不出现「站点」/「掉率」字样（掉率只在卡片上以纯数字呈现）",
         joined:find("站点", 1, true) == nil and joined:find("掉率", 1, true) == nil,
         n1 .. " 行")
      ck("★ 连名字都没有时首行给 itemID（不拿站点名顶上）",
         tostring(TOOLTIP_LINES[1]):find("物品 #", 1, true) ~= nil, TOOLTIP_LINES[1])
      ck("★ 客户端连静态数据都没有 → 绝不承诺「加载中 / 稍后自动刷新」",
         joined:find("加载中", 1, true) == nil
         and joined:find("自动刷新", 1, true) == nil, n1 .. " 行")

      -- 情形①b：同步口给得出名字（但详细数据仍未到货）→ 首行是真名 + 客户端品质；
      --          末行仍按「客户端静态库有没有这件」判 —— 这里没有 → 照样不承诺。
      C_Item = {
        GetItemNameByID = function(i) return "同步装备" end,
        GetItemQualityByID = function(i) return 3 end,
      }
      TOOLTIP_LINES = {}
      row.__scripts.OnEnter(row)
      ck("★ 同步口有名字时首行显示客户端真名",
         tostring(TOOLTIP_LINES[1]) == "同步装备", tostring(TOOLTIP_LINES[1]))
      ck("★ 有名字但静态数据仍无 → 末行照旧不承诺刷新",
         tostring(TOOLTIP_LINES[2]) == "客户端未收录此物品", tostring(TOOLTIP_LINES[2]))

      -- 情形①c：★ 判据可证伪的正例 —— 客户端静态库认得这件（图标 / 部位都在，只是详细
      --          数据还没到货）→ 这时才允许承诺「加载中，稍后自动刷新」。
      INVTYPE_WAIST = "腰部"
      C_Item = {
        GetItemInfoInstant = function(i)
          return i, "护甲", "锁甲", "INVTYPE_WAIST", 134001, 4, 3
        end,
      }
      TOOLTIP_LINES = {}
      row.__scripts.OnEnter(row)
      ck("★★ 客户端已收录（Instant 有值）才承诺「加载中」",
         table.concat(TOOLTIP_LINES, "\n"):find("加载中", 1, true) ~= nil,
         table.concat(TOOLTIP_LINES, " | "))
      ck("★ 没名字时首行退给客户端静态数据的「部位 · 子类」（不是空壳）",
         tostring(TOOLTIP_LINES[1]) == "腰部 · 锁甲", tostring(TOOLTIP_LINES[1]))
      C_Item = nil

      -- 情形②：客户端拿不出缓存（GetItemInfo 仍 nil）→ 绝不走 SetItemByID 同步装载
      --        （真机事故：未缓存条目悬停一次 = 一帧几百次 SetItemByID 同步装载 = 卡死），
      --        退占位兜底并走 RequestItem 按需加载。
      GetItemInfo = nil
      local _sentinel = 0
      GameTooltip.SetItemByID = function(self, i)
        _sentinel = _sentinel + 1
        TOOLTIP_LINES[#TOOLTIP_LINES + 1] = "BYID:" .. tostring(i); self.__n = 5
      end
      GameTooltip.SetHyperlink = function(self, link)
        TOOLTIP_LINES[#TOOLTIP_LINES + 1] = "LINK:" .. tostring(link); self.__n = 5
      end
      TOOLTIP_LINES = {}
      row.__scripts.OnEnter(row)
      ck("★★ 未缓存绝不走 SetItemByID 同步装载（真机一帧几百次的卡死源）",
         _sentinel == 0, "SetItemByID 被调 " .. _sentinel .. " 次")
      ck("★ 未缓存退占位兜底（未收录直言 / 承诺加载中二选一）",
         #TOOLTIP_LINES >= 2
         and (table.concat(TOOLTIP_LINES, "\n"):find("客户端未收录此物品", 1, true) ~= nil
              or table.concat(TOOLTIP_LINES, "\n"):find("加载中", 1, true) ~= nil),
         table.concat(TOOLTIP_LINES, " | "))

      -- 情形②b：缓存态（GetItemInfo 有值）→ 走 SetHyperlink 出真·游戏内原生内容
      GetItemInfo = function(i) return "缓存装备" end
      TOOLTIP_LINES = {}
      row.__scripts.OnEnter(row)
      ck("★ 缓存态走 SetHyperlink 出原生内容（掉落清单同源取值）",
         #TOOLTIP_LINES == 1
         and tostring(TOOLTIP_LINES[1]):find("LINK:item:", 1, true) ~= nil,
         table.concat(TOOLTIP_LINES, " | "))

      -- 情形③：原生只出 1 行（客户端其实没数据）→ 必须退回**客户端口径兜底**，
      --        不留空壳提示框、也不拿站点资料把它填满。
      GameTooltip.SetHyperlink = function(self) self.__n = 1 end
      TOOLTIP_LINES = {}
      row.__scripts.OnEnter(row)
      ck("★ 原生只出一行时退回客户端口径兜底（明说未收录，不填站点资料）",
         #TOOLTIP_LINES >= 2
         and table.concat(TOOLTIP_LINES, "\n"):find("客户端未收录此物品", 1, true) ~= nil
         and table.concat(TOOLTIP_LINES, "\n"):find("物品等级", 1, true) == nil,
         #TOOLTIP_LINES .. " 行")

      -- ---------- 提示框换肤：装备提示框不套插件皮（2026-09-23 用户口径）----------
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

      -- ---------- 按需加载：预热 + 数据到货自动重刷 ----------
      -- 桩里没有 C_Item，装一个只记账的替身
      local DG = TF_NS.DungeonModule
      local req = {}
      -- ★ C_Timer 桩：DG.ScheduleNameSweep 用它排「到货重扫」。把排队的回调记下来，
      --   既能断言「排了几次」，也能在桩里演示「数据晚到 → 自己补名」的过程。
      --   ★★ 2026-10-09 懒构建 + 分帧泵：RunSteps 的自续泵用 After(0, pump) 排帧，
      --   桩若只记录不执行，渲染永远停在首块（pending 堆积、池只建 13/292）⇒
      --   t==0（分帧泵自续）**立即执行**（等价「C_Timer 缺失时同步跑完」的离线契约），
      --   t>0（业务重扫等）保留排队记录供断言。
      local SWEEPS = {}
      C_Timer = { After = function(t, fn)
          if t == 0 then fn(); return end
          SWEEPS[#SWEEPS + 1] = { t = t, fn = fn }
      end, NewTimer = function(t, fn)
          if t == 0 then fn(); return {} end
          SWEEPS[#SWEEPS + 1] = { t = t, fn = fn }
          return {}
      end }
      GetItemInfo = nil            -- 逼出「占位 → 到货 → 补名」这条真实链路
      C_Item = { RequestLoadItemDataByID = function(i) req[i] = true end }
      DG.__asked = {}
      U:ShowDungeonDetail(hall)
      local nReq = 0
      for _ in pairs(req) do nReq = nReq + 1 end
      ck("★ 打开详情预热了本副本全部物品ID（客户端按需加载）", nReq >= 13, nReq)

      -- ---------- ★★ 用户诉求②：不能只有图标、没有名字 ----------
      -- 实机症状：整页「图标 + 部位 · 子类 + 掉率」齐全，唯独名字全是占位。
      -- 图标 / 部位走 GetItemInfoInstant（静态、随叫随有），名字走 GetItemInfo
      -- （要等详细数据到货）→ 到货那一下没接住，卡片就永远停在占位上。
      ck("★★ 打开详情排了 4 次「到货重扫」（与 DG.SWEEP_AT 一致）", #SWEEPS == 4, #SWEEPS)
      local pool = U.dungeonDetailPool and U.dungeonDetailPool.item
      local nPool = pool and #pool or 0
      local function nPlaceholder()
        local n = 0
        for i = 1, nPool do
          local c = pool[i]
          if c and tostring(c.name.__text) == "暂时没有客户端数据" then n = n + 1 end
        end
        return n
      end
      local nBeforePh = nPlaceholder()
      ck("★ 重扫前确实存在占位卡（这条断言不能恒真）",
         nPool > 0 and nBeforePh > 0, nBeforePh .. "/" .. nPool)
      -- 模拟「数据在首屏之后才到货」，且到货事件整个不触发（私服常态）：
      -- 只能靠排队的重扫自己把名字补上。
      local SWP = {}
      C_Item = { GetItemNameByID = function(i) SWP[i] = true; return "重扫到货名" end,
                 GetItemQualityByID = function(i) return 3 end }
      if SWEEPS[1] and SWEEPS[1].fn then SWEEPS[1].fn() end
      local nAfterPh = nPlaceholder()
      ck("★★ 定时重扫把名字补成客户端真值（数据晚到也能自己出现）",
         nAfterPh == 0, nAfterPh .. "/" .. nPool)
      local nMark = 0
      for i = 1, nPool do
        if pool[i] and pool[i].__named then nMark = nMark + 1 end
      end
      ck("★ 重扫后每张卡都打了 __named 标记", nMark == nPool, nMark .. "/" .. nPool)
      SWP = {}
      if SWEEPS[2] and SWEEPS[2].fn then SWEEPS[2].fn() end
      local nSwp = 0
      for _ in pairs(SWP) do nSwp = nSwp + 1 end
      ck("★ 已到货的卡不再重复取值（第 2 次重扫零取数）", nSwp == 0, nSwp)
      C_Item = nil
      GetItemInfo = nil

      -- ★ 官方异步口：Item:CreateFromItemID(id):ContinueOnItemLoad(cb)
      --   暴雪整个 Lua 侧**从不调用** C_Item.RequestLoadItemDataByID（全源码零命中）——
      --   加载请求其实是 C 端在 tooltip / 异步回调（ItemEventListener → ASYNC_ITEM）管线里
      --   自己发的。所以这一路（Blizzard_Journeys 给奖励物品用的范式）才是「一定会发」的那条。
      local asyncN, ASYNC_CB = 0, nil
      Item = { CreateFromItemID = function(_, i)
        return { ContinueOnItemLoad = function(_, cb) asyncN = asyncN + 1; ASYNC_CB = cb end }
      end }
      DG.__asked = {}
      DG.RequestItem(it[1], true)
      ck("★★ 请求第④路：官方异步口 Item:CreateFromItemID + ContinueOnItemLoad",
         asyncN == 1, asyncN)
      ck("★ 官方异步回调挂的是卡片重刷（到货直接刷，不等事件顺序）",
         type(ASYNC_CB) == "function")
      -- 回调真的能把卡片刷成客户端真值：先让同步口给得出名字，再手动触发回调
      C_Item = {
        GetItemNameByID = function(i) return "官方异步名" end,
        GetItemQualityByID = function(i) return 3 end,
      }
      if ASYNC_CB then ASYNC_CB() end
      if SWEEPS then
        for i = #SWEEPS, 1, -1 do
          local s = SWEEPS[i]
          SWEEPS[i] = nil
          if s and s.fn then s.fn() end
        end
      end
      ck("★★ 官方异步回调触发后卡片名字刷成客户端真值",
         row.name ~= nil and tostring(row.name.__text) == "官方异步名",
         row.name and tostring(row.name.__text) or "nil")
      Item = nil

      DG.__itemEvt = nil            -- 重建监听，才能拿到它的 OnEvent
      DG.EnsureItemListener()
      local ev = DG.__itemEvt
      ck("★ 装了 GET_ITEM_INFO_RECEIVED 监听（到货重刷）",
         ev ~= nil and ev.__scripts.OnEvent ~= nil)

      -- 先悬停：此刻客户端还拿不出内容 → 兜底
      GameTooltip.SetItemByID = false
      GameTooltip.SetHyperlink = function(self) self.__n = 1 end
      GameTooltip.NumLines = function(self) return self.__n or 0 end
      row.__mouseOver = true
      TOOLTIP_LINES = {}
      row.__scripts.OnEnter(row)
      local nBefore = #TOOLTIP_LINES

      -- 数据到货：客户端能解析了（GetItemInfo 开始返回值），鼠标还停在这一行 → 必须自动换成原生
      GetItemInfo = function(i) return "到货装备" end
      GameTooltip.SetHyperlink = function(self, link)
        TOOLTIP_LINES[#TOOLTIP_LINES + 1] = "LINK:" .. tostring(link); self.__n = 5
      end
      TOOLTIP_LINES = {}
      if ev and ev.__scripts.OnEvent then
        ev.__scripts.OnEvent(ev, "GET_ITEM_INFO_RECEIVED", it[1], true)
      end
      ck("★ 物品数据到货后自动把兜底换成游戏原生属性",
         nBefore >= 2 and #TOOLTIP_LINES == 1
         and tostring(TOOLTIP_LINES[1]):find("LINK:item:", 1, true) ~= nil,
         nBefore .. " 行 -> " .. #TOOLTIP_LINES .. " 行")

      -- 鼠标已移开时到货 → 不得重刷（否则留一个孤零零的提示框）
      GameTooltip.SetItemByID = false
      GameTooltip.SetHyperlink = function(self) self.__n = 1 end
      row.__scripts.OnEnter(row)
      GameTooltip.SetItemByID = function(self, i)
        TOOLTIP_LINES[#TOOLTIP_LINES + 1] = "BYID:" .. tostring(i); self.__n = 5
      end
      row.__mouseOver = false
      TOOLTIP_LINES = {}
      if ev and ev.__scripts.OnEvent then
        ev.__scripts.OnEvent(ev, "GET_ITEM_INFO_RECEIVED", it[1], true)
      end
      ck("★ 鼠标已移开时到货不再重刷（不留孤儿提示框）", #TOOLTIP_LINES == 0, #TOOLTIP_LINES)

      C_Item, Item = nil, nil
      DG.__asked = {}
      DG.__itemEvt = nil
      row.__mouseOver = nil

      -- 收尾还原全局：后面的图标路径等断言不受影响
      GetItemInfo = nil
      GameTooltip.SetItemByID = false
      GameTooltip.SetHyperlink = nil
      GameTooltip.NumLines = nil
      TOOLTIP_LINES = {}
    end

    -- ---------- 详情：任务页（掉落 / 任务 子页签） ----------
    -- 打桩：桩里本来没有 C_QuestLog，这里装上可注入的三态口。
    local nDgQ = 0
    if type(TF_NS.DungeonQuests) == "table" then
      for _ in pairs(TF_NS.DungeonQuests) do nDgQ = nDgQ + 1 end
    end
    ck("任务清单已装载（fc 回铺后 31 个副本有数据；只增不减 ≥28）", nDgQ >= 28, nDgQ)

    QUEST_DONE, QUEST_ON = {}, {}
    C_QuestLog = {
      GetTitleForQuestID = function(id) return "客户端任务" .. tostring(id) end,
      GetQuestDifficultyLevel = function() return 16 end,
      IsQuestFlaggedCompleted = function(id) return QUEST_DONE[id] == true end,
      IsOnQuest = function(id) return QUEST_ON[id] == true end,
    }
    GetQuestLink = function(id)
      return "|cff808080|Hquest:" .. tostring(id) .. "|h[客户端任务]|r"
    end
    UnitFactionGroup = function() return "Horde" end
    RAID_CLASS_COLORS = {
      WARRIOR = { r = 0.78, g = 0.61, b = 0.43 }, PALADIN = { r = 0.96, g = 0.55, b = 0.73 },
      HUNTER = { r = 0.67, g = 0.83, b = 0.45 }, ROGUE = { r = 1.00, g = 0.96, b = 0.41 },
      PRIEST = { r = 1.00, g = 1.00, b = 1.00 }, SHAMAN = { r = 0.00, g = 0.44, b = 0.87 },
      MAGE = { r = 0.41, g = 0.80, b = 0.94 }, WARLOCK = { r = 0.58, g = 0.51, b = 0.79 },
      DRUID = { r = 1.00, g = 0.49, b = 0.04 },
    }
    local DQ = TF_NS.DungeonModule
    ck("★ 无批量口时退回逐条查询（3.80 端形态）",
       DQ.BuildQuestSnap() == false and (DQ.questDoneSet == nil))
    DQ.questDoneCache = {}

    local rf = nil
    for _, d in ipairs(data.dungeons) do if d.id == "ragefire_chasm" then rf = d end end
    ck("定位到怒焰裂谷（6 条部落任务）", rf ~= nil)

    -- ★ 2026-10-09 懒构建：任务滚动容器也走 DG.EnsureQuestLane()（详情壳在即可，幂等）
    DQ.EnsureQuestLane()
    local qchild0, qpool0 = U.dungeonQuestChild, U.dungeonQuestPool
    ck("任务滚动容器 + 子帧 + 池都在",
       U.dungeonQuestScroll ~= nil and qchild0 ~= nil and type(qpool0) == "table")
    ck("★ 任务子帧父级 = 任务滚动容器（未被解挂）", qchild0.__parent == U.dungeonQuestScroll)
    ck("任务页也有顶部进度行与空态提示", U.dungeonQuestSum ~= nil and U.dungeonQuestNote ~= nil)

    U:ShowDungeonDetail(rf)
    ck("默认页签是「掉落」", (U.dungeonTab or "loot") == "loot")
    ck("默认：掉落容器显示 / 任务容器隐藏",
       U.dungeonDetailScroll.__shown == true and U.dungeonQuestScroll.__shown == false)

    U:SetDungeonTab("quest")
    ck("切到任务页：任务容器显示 / 掉落容器隐藏",
       U.dungeonQuestScroll.__shown == true and U.dungeonDetailScroll.__shown == false)
    ck("★ 切页签不重建任务 scroll child", U.dungeonQuestChild == qchild0)
    ck("★ 两个页签按钮都在且文案正确（掉落 / 任务）",
       U.dungeonTabBtns.loot ~= nil and U.dungeonTabBtns.quest ~= nil
       and tostring(U.dungeonTabBtns.loot.__text) == "掉落"
       and tostring(U.dungeonTabBtns.quest.__text) == "任务",
       tostring(U.dungeonTabBtns.quest and U.dungeonTabBtns.quest.__text))
    local nShownQ = 0
    for _, r in ipairs(qpool0.row) do if r.__shown then nShownQ = nShownQ + 1 end end
    ck("怒焰裂谷 6 行全显示（部落玩家）", nShownQ == 6, nShownQ)
    ck("分组标题 2 个（进本前先去接 / 副本内）", #qpool0.hdr == 2, #qpool0.hdr)
    ck("★ 行绑了 __q（悬停取值来源）", qpool0.row[1].__q ~= nil)
    ck("★ 行不再有左状态色条（2026-10-13 强调条全删，行内改小卡片）",
       rawget(qpool0.row[1], "bar") == nil)
    ck("★ 行不再有右缘金标条 selMark（2026-10-13 二次：选中强调条也删）",
       rawget(qpool0.row[1], "selMark") == nil)
    ck("★ 行内小卡片：前置 / 可共享（挂行帧上，紧贴任务名右侧）",
       rawget(qpool0.row[1], "preB") ~= nil and rawget(qpool0.row[1], "shareB") ~= nil)
    ck("★★ 任务页「未完成 / 已完成」筛选钮退役，改 iOS 开关「显示已完成」（默认开）",
       U.dungeonQDoneTg ~= nil and not U.dungeonFilterBtns[5].__shown
       and (U.dungeonQFilter or "all") ~= "todo")
    ck("★ 行名走客户端（中文任务名，非本表文本）",
       tostring(qpool0.row[1].name.__text):find("客户端任务", 1, true) ~= nil,
       qpool0.row[1].name.__text)
    ck("★ 单行地点列写了起始 NPC · 地点（客户端问不到，只能本表给）",
       tostring(qpool0.row[1].sub.__text):find("雷霆崖", 1, true) ~= nil,
       qpool0.row[1].sub.__text)
    ck("★ 副行右写了「N 级可接」（无限口径，客户端问不到）",
       tostring(qpool0.row[1].lv.__text):find("级可接", 1, true) ~= nil,
       qpool0.row[1].lv.__text)
    ck("顶部进度行：已完成 0 / 6",
       tostring(U.dungeonQuestSum.__text):find("已完成 0 / 6", 1, true) ~= nil,
       U.dungeonQuestSum.__text)

    -- 三态：5722 已完成 / 5723 进行中 / 其余未完成
    QUEST_DONE[5722] = true
    QUEST_ON[5723] = true
    -- ★ 完成状态**带缓存**（3.80 无批量口 → 逐条查并缓存，见 DG.QuestDone）：
    --   改了桩必须同步作废缓存，否则行状态停在旧值 —— 下面整套断言会全变成假绿。
    DQ.QuestSnapReset()
    U:RenderDungeonQuests()
    local r1, r2, r3 = qpool0.row[1], qpool0.row[2], qpool0.row[3]
    ck("★ 已完成行：状态字「已完成」（强调条已删，状态只走名字色 + 状态字）",
       tostring(r1.meta.__text):find("已完成", 1, true) ~= nil,
       tostring(r1.meta.__text))
    ck("★ 进行中行：状态字「进行中」",
       tostring(r2.meta.__text):find("进行中", 1, true) ~= nil,
       tostring(r2.meta.__text))
    ck("★ 未完成行：状态字「未完成」",
       tostring(r3.meta.__text):find("未完成", 1, true) ~= nil, tostring(r3.meta.__text))
    ck("★ 完成行名字转绿 / 未完成行保持常态色",
       r1.name.__textColor ~= nil and math.abs(r1.name.__textColor[2] - 0.85) < 1e-6
       and r3.name.__textColor ~= nil and math.abs(r3.name.__textColor[1] - 0.88) < 1e-6,
       tostring(r1.name.__textColor and r1.name.__textColor[2]))
    ck("★ 进度行随状态跳档（已完成 1 / 6）",
       tostring(U.dungeonQuestSum.__text):find("已完成 1 / 6", 1, true) ~= nil,
       U.dungeonQuestSum.__text)
    -- 完成判定必须**真的读了状态口**：把它改成恒 false，行状态要跟着变
    -- （否则说明 QuestDone 的结果没有被用上，或者被判据缓存死了）
    QUEST_DONE[5722] = false
    DQ.QuestSnapReset()
    U:RenderDungeonQuests()
    ck("★★ 完成判定可证伪：清掉 5722 的完成态后行状态立刻回到未完成",
       tostring(qpool0.row[1].meta.__text):find("未完成", 1, true) ~= nil,
       tostring(qpool0.row[1].meta.__text))
    QUEST_DONE[5722] = true
    DQ.QuestSnapReset()
    U:RenderDungeonQuests()

    -- 筛档（任务页只用前 3 格：全部 / 未完成 / 已完成）
    U:SetQuestFilter("done")
    local nD1 = 0
    for _, r in ipairs(qpool0.row) do if r.__shown then nD1 = nD1 + 1 end end
    ck("任务筛「已完成」只剩 1 行", nD1 == 1, nD1)
    U:SetQuestFilter("todo")
    local nD2 = 0
    for _, r in ipairs(qpool0.row) do if r.__shown then nD2 = nD2 + 1 end end
    ck("任务筛「未完成」剩 5 行（含进行中）", nD2 == 5, nD2)
    U:SetQuestFilter("all")
    local nD3 = 0
    for _, r in ipairs(qpool0.row) do if r.__shown then nD3 = nD3 + 1 end end
    ck("任务筛「全部」回到 6 行", nD3 == 6, nD3)

    -- ★★ 客户端拿不到任务名（从未见过的任务）→ 占位名 + 明说没有客户端数据。
    --    这条守的是「绝不回退站点 / AtlasQuest 文本」。
    local savedTitle = C_QuestLog.GetTitleForQuestID
    C_QuestLog.GetTitleForQuestID = function() return nil end
    U:RenderDungeonQuests()
    ck("★★ 客户端拿不到任务名时给占位名「任务 #ID」（不回退本表文本）",
       tostring(qpool0.row[1].name.__text):find("任务 #", 1, true) ~= nil,
       qpool0.row[1].name.__text)
    ck("★★ 拿不到名字时状态栏明说「暂时没有客户端数据」",
       tostring(qpool0.row[1].meta.__text) == "暂时没有客户端数据",
       qpool0.row[1].meta.__text)
    ck("★ 拿不到名字时单行地点列照给（客户端问不到的那部分照给）",
       tostring(qpool0.row[1].sub.__text):find("雷霆崖", 1, true) ~= nil,
       qpool0.row[1].sub.__text)
    C_QuestLog.GetTitleForQuestID = savedTitle

    -- 阵营档：两维切换后 side 只有 A/H（all 退役），自动档 = 玩家阵营
    UnitFactionGroup = function() return "Alliance" end
    U:SetQuestSide(nil)
    U:RenderDungeonQuests()
    local nAF = 0
    for _, r in ipairs(qpool0.row) do if r.__shown then nAF = nAF + 1 end end
    ck("★ 联盟玩家自动档落「联盟」（怒焰联盟 0 条）", nAF == 0, nAF)
    ck("★ 自己阵营档写明「已按你的阵营筛选」",
       tostring(U.dungeonQuestSum.__text):find("已按你的阵营筛选", 1, true) ~= nil,
       U.dungeonQuestSum.__text)
    -- 显式切「部落」档 → 6 行 + 写明只看部落
    U:SetQuestSide("H")
    local nA2 = 0
    for _, r in ipairs(qpool0.row) do if r.__shown then nA2 = nA2 + 1 end end
    ck("★ 显式选「部落」档 → 怒焰 6 行", nA2 == 6, nA2)
    ck("★ 对方阵营档写明「只看部落阵营任务」",
       tostring(U.dungeonQuestSum.__text):find("部落阵营可接", 1, true) ~= nil,
       U.dungeonQuestSum.__text)
    ck("★ SetQuestSide 显式档已生效（部落）", U.dungeonQSide == "H")
    -- 回自己阵营（联盟）→ 0 行
    U:SetQuestSide("A")
    local nA3 = 0
    for _, r in ipairs(qpool0.row) do if r.__shown then nA3 = nA3 + 1 end end
    ck("★ 阵营档切回「联盟」→ 0 行", nA3 == 0, nA3)
    UnitFactionGroup = function() return "Horde" end
    U:SetQuestSide(nil)               -- 回自动档：部落玩家自动勾部落（side 持久化后须连 DB 一起清）
    U:RenderDungeonQuests()
    local nH2 = 0
    for _, r in ipairs(qpool0.row) do if r.__shown then nH2 = nH2 + 1 end end
    ck("★ 部落玩家自动档勾「部落」→ 6 行", nH2 == 6, nH2)

    -- ★★ 右列详情面板：页签显隐 / 点行联动 / 前导链 / 后续反查 / 奖励芯片 / 目标注释
    ck("右列详情面板在（任务页显示）", U.dungeonQDet ~= nil and U.dungeonQDet.__shown == true)
    ck("★ 进任务页自动选中第一行", U.dungeonQuestSel ~= nil)
    U:SetDungeonTab("loot")
    ck("★ 切回掉落页：右列详情隐藏",
       U.dungeonQDet.__shown == false and U.dungeonQuestScroll.__shown == false)
    U:SetDungeonTab("quest")
    local row2q = qpool0.row[2].__q
    qpool0.row[2].__scripts.OnClick()
    ck("★ 点行选中：dungeonQuestSel 指向被点行",
       U.dungeonQuestSel == row2q[1], tostring(U.dungeonQuestSel))
    ck("★ 右列名字随选中切换（客户端口径，详情名带 #ID 后缀）",
       tostring(U.dungeonQDetName.__text):find(tostring(qpool0.row[2].name.__text), 1, true) == 1,
       tostring(U.dungeonQDetName.__text))
    local row5724
    for _, r in ipairs(qpool0.row) do if r.__q and r.__q[1] == 5724 then row5724 = r end end
    ck("怒焰行里能定位 5724", row5724 ~= nil)
    row5724.__scripts.OnClick()
    local nNode = 0
    for _, nd in ipairs(U.dungeonQDetPool.node) do if nd.__shown then nNode = nNode + 1 end end
    ck("★ 5724 前导链显示 1 环（5722 已解析成 questID）", nNode == 1, nNode)
    ck("★ 前导环名字走客户端（5722 的任务名，带 #ID 后缀）",
       tostring(U.dungeonQDetPool.node[1].name.__text):find(tostring(DQ.QuestName(5722)), 1, true) == 1,
       tostring(U.dungeonQDetPool.node[1].name.__text))
    local nChip = 0
    for _, cp in ipairs(U.dungeonQDetPool.chip) do if cp.__shown then nChip = nChip + 1 end end
    ck("★ 5724 奖励芯片 4 枚（站点 itemID，名字问客户端）", nChip == 4, nChip)
    ck("★ 奖励芯片挂了 __it（到货重刷与悬停提示的取值来源）",
       U.dungeonQDetPool.chip[1].__it ~= nil and U.dungeonQDetPool.chip[1].__it[1] == 14381)
    -- ★★ 地图标记（2026-09-22）：点起始行/链节点 → DG.MarkNPC → C_Map 航点
    C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
    local savedDetCur, savedSel = U.dungeonDetailCur, U.dungeonQuestSel
    -- 当前副本（怒焰）的接任务 NPC 多在副本里、wowhead 无坐标 → 全库找一个有坐标的样例副本
    local markQ, markD
    for _, dg in ipairs(TF_NS.DungeonData.dungeons) do
      for _, qq in ipairs(DQ.QuestList(dg)) do
        if qq[16] and TF_NS.NPCLoc and TF_NS.NPCLoc[qq[16]] and qq[9] then
          for _, seg in ipairs(qq[9]) do
            if type(seg) == "number" then
              local pr = DQ.QuestRowByID(seg)
              local nid = (pr and pr[16]) or (TF_NS.QuestPreNpcID and TF_NS.QuestPreNpcID[seg])
              if nid and TF_NS.NPCLoc[nid] then
                markQ, markD = qq, dg
                break
              end
            end
          end
        end
        if markQ then break end
      end
      if markQ then break end
    end
    ck("★ 样例任务带 NPCID 且 NPCLoc 有坐标", markQ ~= nil)
    if markQ then
      U.dungeonDetailCur = markD
      U.dungeonQuestSel = markQ[1]
      U.dungeonQFilter = "all"
      U.dungeonQSide = "H"
      U:RenderDungeonQuests()
      local npcRow = U.dungeonQDetPool.npc and U.dungeonQDetPool.npc[1]
      ck("★ 有 NPCID 时起始行走可点行（pool.npc[1]）",
         npcRow ~= nil and npcRow.__shown == true and npcRow.__npc == markQ[16])
      if npcRow and npcRow.mark and npcRow.mark.__scripts and npcRow.mark.__scripts.OnClick then
        npcRow.mark.__scripts.OnClick(npcRow.mark)
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
      else
        ck("★ 起始行 mark 按钮有 OnClick", false)
      end
      -- 链节点：任意 __shown 且 __npc 的节点点击 → 航点换目标
      local hitNode
      for _, nd in ipairs(U.dungeonQDetPool.node) do
        if nd.__shown and nd.__npc then hitNode = nd break end
      end
      ck("★ 前导/后续环挂了 __npc", hitNode ~= nil)
      if hitNode then
        C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
        hitNode.__scripts.OnClick(hitNode)
        if IS_FOREVER then
          ck("★ 点链节点 → 航点指向该环起始 NPC 的地图",
             C_MAP_MARK.opened == TF_NS.NPCLoc[hitNode.__npc][1], tostring(C_MAP_MARK.opened))
        else
          ck("★ 泰坦端点链节点不落航点", C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil)
        end
      end
    end
    -- 还原现场：后续 5722/5724 断言依赖原副本与原选中
    U.dungeonDetailCur = savedDetCur
    U.dungeonQuestSel = savedSel
    U.dungeonQFilter = "all"
    U.dungeonQSide = "H"
    U:RenderDungeonQuests()
    -- 未收录坐标：明说不假装（不落航点、不崩）
    C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
    DQ.MarkNPC(999999999)
    ck("★ 未收录 NPC：不落航点只提示", C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil)
    local row5722
    for _, r in ipairs(qpool0.row) do if r.__q and r.__q[1] == 5722 then row5722 = r end end
    row5722.__scripts.OnClick()
    local nNode2 = 0
    for _, nd in ipairs(U.dungeonQDetPool.node) do if nd.__shown then nNode2 = nNode2 + 1 end end
    ck("★ 5722 的后续任务反查显示 1 条（5724）", nNode2 == 1, nNode2)
    local hasAim = false
    for _, t in ipairs(U.dungeonQDetPool.txt) do
        if t.__shown and tostring(t.__text):find("玛尔·恐怖图腾", 1, true) then hasAim = true end
    end
    ck("★ 右列显示任务目标（重写稿，非站点原文）", hasAim)

    -- ★★ 前导链追溯到源头：死亡矿井 214 → 65(源头) 132 135 141 142 155
    U:ShowDungeonDetail(dm)
    U.dungeonQSide = "A"       -- 死亡矿井是联盟任务，部落 mock 下须显式回联盟档
    U.dungeonQFilter = "all"
    U:SetDungeonTab("quest")
    local row214
    for _, r in ipairs(qpool0.row) do if r.__q and r.__q[1] == 214 then row214 = r end end
    ck("死亡矿井任务页能定位 214", row214 ~= nil)
    row214.__scripts.OnClick()
    local seq214 = {}
    for _, nd in ipairs(U.dungeonQDetPool.node) do
        if nd.__shown and nd.__preID then seq214[#seq214 + 1] = nd.__preID end
    end
    ck("★ 214 前导链追溯到源头：65→132→135→141→142→155（6 环）",
       #seq214 == 6 and seq214[1] == 65 and seq214[2] == 132 and seq214[3] == 135
       and seq214[4] == 141 and seq214[5] == 142 and seq214[6] == 155,
       table.concat(seq214, ","))
    local hasFront = false
    for _, nd in ipairs(U.dungeonQDetPool.node) do
        if nd.__shown and tostring(nd.st.__text):find("下一步", 1, true) then hasFront = true end
    end
    ck("★ 第一个没完成的环标「下一步」（当前进度所在）", hasFront)
    -- ★★ 表外链环节的副标题 = 起始 NPC（PreExtra npc/lv，2026-09-22）
    local sub132, sub65
    for _, nd in ipairs(U.dungeonQDetPool.node) do
        if nd.__shown and nd.__preID == 132 then sub132 = tostring(nd.sub.__text) end
        if nd.__shown and nd.__preID == 65 then sub65 = tostring(nd.sub.__text) end
    end
    ck("★ 表外链环节副标题 = 起始NPC · 要求等级（132 → 黑衣威利）",
       sub132 and sub132:find("黑衣威利", 1, true) and sub132:find("14 级可接", 1, true), sub132)
    ck("★ 源头环节副标题 = 起始NPC（65 → 格里安·斯托曼）",
       sub65 and sub65:find("格里安·斯托曼", 1, true) ~= nil, sub65)

    -- ---------- 前导链备注：链上某些环其实非必需（2026-09-24 用户要求）------------
    -- 用户原话：「给 2040 这个前导任务需要备注一下：不需要接 2041 就可以接」。
    -- 两条一起测：① 有备注的（2040）真渲染出来；② 没备注的（同副本 214，同样有前置）
    -- 不许长出这一行 —— 少了②，把备注写成「无备注也渲染」照样绿（等于给全表加了一行）。
    do
      U:ShowDungeonDetail(dm)
      U.dungeonQSide = "A"
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
      ck("★ 洛丹伦废墟入口 = 幽暗城正门（提瑞斯法林地 65.0,70.0——1.6.2 修正口径）",
         e2 ~= nil and e2[1] == 1420 and e2[2] == 65.0 and e2[3] == 70.0,
         e2 and (tostring(e2[1]) .. " " .. tostring(e2[2]) .. "," .. tostring(e2[3])) or "nil")
    end


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
      if hallD and chips and #chips >= 3 then
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


    -- ★★ 难度 / 职业 / 需求三字段（1654 圣骑士「正义试炼」：材料进需求列、职业专属；
    --    AtlasQuest 把它跨副本收录在死亡矿井 / 影牙（可二选一做），动态测死亡矿井里的那份）
    local hasDiffLab, hasClsLab, hasReqLab, has1654Chip, hasRewardLab = false, false, false, false, false
    U:ShowDungeonDetail(dm)
    U.dungeonQSide = "A"
    U.dungeonQFilter = "all"
    U:SetDungeonTab("quest")
    local row1654
    for _, r in ipairs(qpool0.row) do if r.__q and r.__q[1] == 1654 then row1654 = r end end
    ck("★ 死亡矿井任务页能定位 1654（圣骑士正义试炼，AtlasQuest 跨副本收录）", row1654 ~= nil)
    ck("★★ 左列行内职业小卡片（1654 → 白字小卡片「骑士」，去「圣」全名）",
       row1654 ~= nil and type(row1654.clsB) == "table" and row1654.clsB[1] ~= nil
       and row1654.clsB[1].__shown == true and row1654.clsB[1].lab ~= nil
       and tostring(row1654.clsB[1].lab.__text) == "骑士",
       row1654 and type(row1654.clsB) == "table" and row1654.clsB[1]
       and tostring(row1654.clsB[1].lab.__text))
    ck("★★★ 职业小卡片底色 = 职业色压暗（1654 圣骑士 → RAID_CLASS_COLORS.PALADIN × 0.78）",
       row1654 ~= nil and type(row1654.clsB) == "table" and row1654.clsB[1] ~= nil
       and type(row1654.clsB[1].__huiCard) == "table"
       and type(row1654.clsB[1].__huiCard.fill) == "table"
       and type(row1654.clsB[1].__huiCard.fill[1].__huiGlass) == "table"
       and math.abs(row1654.clsB[1].__huiCard.fill[1].__huiGlass.c[1] - 0.7488) < 0.01
       and math.abs(row1654.clsB[1].__huiCard.fill[1].__huiGlass.c[2] - 0.4290) < 0.01
       and math.abs(row1654.clsB[1].__huiCard.fill[1].__huiGlass.c[3] - 0.5694) < 0.01,
       row1654 and type(row1654.clsB) == "table" and row1654.clsB[1]
       and string.format("%.3f/%.3f/%.3f", row1654.clsB[1].__huiCard.fill[1].__huiGlass.c[1],
            row1654.clsB[1].__huiCard.fill[1].__huiGlass.c[2],
            row1654.clsB[1].__huiCard.fill[1].__huiGlass.c[3]))
    ck("★ 职业小卡片排在任务名右侧（1654 落点落在名称列内、不越「地点」列）",
       row1654 ~= nil and type(row1654.clsB) == "table" and row1654.clsB[1] ~= nil
       and type(row1654.clsB[1].__pts) == "table"
       and row1654.clsB[1].__pts[4] > DG.Q_X_NAME
       and row1654.clsB[1].__pts[4] <= DG.Q_X_NAME + DG.Q_W_NAME + DG.Q_BADGE_GAP,
       row1654 and type(row1654.clsB) == "table" and row1654.clsB[1]
       and tostring(row1654.clsB[1].__pts[4]))
    row1654.__scripts.OnClick()
    for _, f in ipairs(U.dungeonQDetPool.kv) do
        if f.__shown and tostring(f.__text):find("任务难度", 1, true) then hasDiffLab = true end
        if f.__shown and tostring(f.__text):find("职业", 1, true) then hasClsLab = true end
    end
    for _, f in ipairs(U.dungeonQDetPool.lab) do
        if f.__shown and tostring(f.__text) == "任务需求" then hasReqLab = true end
        if f.__shown and tostring(f.__text) == "任务奖励" then hasRewardLab = true end
    end
    for _, cp in ipairs(U.dungeonQDetPool.chip) do
        if cp.__shown and cp.__it and cp.__it[1] == 6994 then has1654Chip = true end
    end
    ck("★ 详情显示任务难度行（nfu 彩色档位数字）", hasDiffLab)
    ck("★ 详情显示职业专属行（圣骑士专属）", hasClsLab)
    ck("★ 「任务需求」节单独显示（材料 6994 进需求芯片）", hasReqLab and has1654Chip)
    ck("★ 需求物品不再混进奖励（1654 奖励已清空 → 无「任务奖励」节）", not hasRewardLab)

    -- 池化不变量：反复切页签 / 换副本，子帧恒定 + 零新建帧
    U:ShowDungeonDetail(scholo)          -- 通灵 11 条：先把行池撑到最大
    U:ShowDungeonDetail(rf)
    local poolSize = #qpool0.row
    FRAMES = 0
    U:SetDungeonTab("loot"); U:SetDungeonTab("quest")
    U:SetDungeonTab("loot"); U:SetDungeonTab("quest")
    ck("★ 反复切页签零新建帧（两页共用骨架，不重建）", FRAMES == 0, FRAMES)
    ck("★ 切页签后任务子帧恒定", U.dungeonQuestChild == qchild0)
    FRAMES = 0
    U:ShowDungeonDetail(scholo)
    U:ShowDungeonDetail(rf)
    ck("★ 任务页反复换副本零新建帧", FRAMES == 0, FRAMES)
    ck("★ 换副本后任务子帧恒定", U.dungeonQuestChild == qchild0)
    ck("★ 任务行池只增不减", #qpool0.row == poolSize, #qpool0.row)

    -- 底色复位：池化行会带着上一轮的悬停态被复用，每轮刷新必须复位（与掉落卡同款）
    local seenQA = {}
    local qrow0 = qpool0.row[1]
    local origQBd = qrow0.SetBackdropColor
    qrow0.SetBackdropColor = function(self, r, g, b, a)
      seenQA[#seenQA + 1] = a
      return origQBd(self, r, g, b, a)
    end
    U:RenderDungeonQuests()
    qrow0.SetBackdropColor = origQBd
    -- 2026-10-10 hui 圆角行：复位走 HuiCardState（非选中=胶囊隐，选中=胶囊常显+金标条）；
    --   旧路径判 SetBackdropColor alpha ∈ {常态, 选中提亮}。两路任一成立即可。
    local selQ = U.dungeonQuestSel
    local questStateOK = true
    for _, r in ipairs(qpool0.row) do
      if r.__shown and r.__huiCard and r.__hov then
        local want = (r.__q and r.__q[1] == selQ) and true or false
        for _, t in ipairs(r.__hov) do
          if t.__shown ~= want then questStateOK = false end
        end
      end
    end
    local bgOK = seenQA[#seenQA] ~= nil
    for _, a in ipairs(seenQA) do
      if math.abs(a - DGn.LOOT_CARD_BG) > 1e-6 and math.abs(a - DGn.LOOT_CARD_BG_HOVER) > 1e-6 then
        bgOK = false
      end
    end
    ck("★ 每轮刷新都把任务行复位成已知态（hui=胶囊随选中显隐 / 旧路径=常态或选中提亮）",
       questStateOK or bgOK)

    -- 选中态动态：悬停选中行再离开，金框必须还在（OnLeave 按选中态复位）
    U.dungeonQSide = "H"               -- 怒焰是部落副本；all 退役后选中态测试回部落档
    U:RenderDungeonQuests()
    U.dungeonQuestSel = qpool0.row[1].__q[1]
    U:RenderDungeonQuests()
    local selRow
    for _, r in ipairs(qpool0.row) do
      if r.__shown and r.__q and r.__q[1] == U.dungeonQuestSel then selRow = r end
    end
    ck("★ 有选中行可测（选中行在池里且显示）", selRow ~= nil)
    local leaveCol
    local origBrd = selRow.SetBackdropBorderColor
    selRow.SetBackdropBorderColor = function(self, rr, gg, bb, aa) leaveCol = { rr, gg, bb, aa } end
    selRow.__scripts.OnEnter(selRow)
    selRow.__scripts.OnLeave(selRow)
    selRow.SetBackdropBorderColor = origBrd
    -- 2026-10-10 hui 圆角行：选中行的提亮态 = 悬停胶囊常显（OnLeave 不得冲掉）
    local selStillHi = false
    if selRow.__huiCard and selRow.__hov then
      selStillHi = true
      for _, t in ipairs(selRow.__hov) do
        if t.__shown ~= true then selStillHi = false end
      end
    end
    ck("★ 悬停离开后选中行仍是提亮态（hui=选中胶囊常显 / 旧路径=金框）",
       selStillHi or (leaveCol ~= nil and math.abs(leaveCol[2] - 0.82) < 1e-6 and math.abs(leaveCol[3]) < 1e-6),
       leaveCol and table.concat(leaveCol, ","))

    -- 切回掉落页：任务滚动区必须收起来，且掉落页仍然正常
    U:SetDungeonTab("loot")
    ck("切回掉落页：掉落容器显示 / 任务容器隐藏",
       U.dungeonDetailScroll.__shown == true and U.dungeonQuestScroll.__shown == false)
    FRAMES = 0
    U:SetDungeonFilter("all")
    ck("切回掉落页后筛选仍走掉落档位", U.dungeonFilterBtns[1].__mode == "loot")
    ck("掉落页渲染零新建帧", FRAMES == 0, FRAMES)

    C_QuestLog, GetQuestLink, UnitFactionGroup = nil, nil, nil

    -- 返回按钮的 OnClick（桩把脚本记在 __scripts 里）
    local back = U.dungeonBack
    if back and back.__scripts and back.__scripts.OnClick then
      back.__scripts.OnClick()
      ck("★ 点「返回」后列表恢复显示", U.dungeonListScroll.__shown == true)
      ck("★ 点「返回」后大卡片恢复显示", U.dungeonListCard and U.dungeonListCard.__shown == true)
      ck("点「返回」后详情隐藏", U.dungeonDetail.__shown == false)
    else
      ck("返回按钮存在且有 OnClick", false)
    end

    -- ★ 2026-10-10 定案：列表为唯一视图，子视图切换入口已删（总览只留代码不留入口）
    ck("子视图切换入口已删（dungeonViewBtns 为空）",
      not U.dungeonViewBtns or next(U.dungeonViewBtns) == nil)
    if U.UpdateDungeons then
      U:UpdateDungeons()
      ck("UpdateDungeons 后列表显示（唯一视图）", U.dungeonListScroll.__shown == true)
      ck("★ UpdateDungeons 后大卡片显示", U.dungeonListCard and U.dungeonListCard.__shown == true)
      ck("★ UpdateDungeons 后子帧仍恒定", U.dungeonListChild == child0)
    end


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

    -- ---------- 物品卡 Ctrl+点击 → 试衣间试穿（2026-10-13 用户要求）----------
    do
      local _dr, _ctrl = nil, false
      DressUpItemLink = function(l) _dr = l end
      IsControlKeyDown = function() return _ctrl end

      local _card
      for _, _r in ipairs(U.dungeonDetailPool and U.dungeonDetailPool.item or {}) do
        if not _card and _r.__it then _card = _r end
      end
      if _card and _card.__scripts and _card.__scripts.OnClick then
        local _id = _card.__it[1]
        GetItemInfo = function()
          return "测试装备", "|cffa335ee|Hitem:" .. tostring(_id) .. ":0:0:0:0:0:0:0|h[测试装备]|h|r", 4
        end
        _ctrl, _dr = true, nil
        _card.__scripts.OnClick(_card, "LeftButton")
        ck("★★ Ctrl+左键点物品卡 → DressUpItemLink 收到完整链接（试衣间）",
           _dr ~= nil and tostring(_dr):find("|Hitem:", 1, true) ~= nil, tostring(_dr))
        _ctrl, _dr = false, nil
        _card.__scripts.OnClick(_card, "LeftButton")
        ck("★ 不按 Ctrl 点物品卡不碰试衣间", _dr == nil, tostring(_dr))
        _ctrl, _dr = true, nil
        _card.__scripts.OnClick(_card, "RightButton")
        ck("★ Ctrl+右键不试穿（只认左键）", _dr == nil, tostring(_dr))
      end

      local _em = TF_NS.ExploreModule
      local _rw
      for _, _r in ipairs(_em and _em.rwRows or {}) do
        if _r.__it and _r.__scripts and _r.__scripts.OnClick then _rw = _r break end
      end
      ck("★ 任务书奖励行挂了 OnClick（装备可点）", _rw ~= nil)
      if _rw then
        _ctrl, _dr = true, nil
        _rw.__scripts.OnClick(_rw, "LeftButton")
        ck("★★ 任务书奖励行 Ctrl+点击 → 试衣间（裸 id 兼容）",
           _dr ~= nil and tostring(_dr):find("|Hitem:", 1, true) ~= nil, tostring(_dr))
        _ctrl, _dr = true, nil
        _rw.__scripts.OnClick(_rw, "RightButton")
        ck("★ 任务书奖励行右键不试穿", _dr == nil, tostring(_dr))
      end

      DressUpItemLink, IsControlKeyDown, GetItemInfo = nil, nil, nil
    end

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
          ck("★ 专业页子页签 = 7 个槽位（总览/训练师/配方/采集/升级/板条箱/工匠文书；遭劫货物暂撤）",
             #allTabs == 7
             and allTabs[1] == "overview" and allTabs[2] == "trainer"
             and allTabs[3] == "recipe" and allTabs[4] == "gather"
             and allTabs[5] == "leveling" and allTabs[6] == "crate"
             and allTabs[7] == "writ",
             #allTabs)

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
          ck("★ 渲染覆盖面够（专业×子页签 组合 >= 22）", n1 >= 22, n1)

          local _f1 = FRAMES
          local n2, bad2, why2 = sweep()
          ck("★ 第二遍全量渲染同样不报错（渲染可重入）",
             bad2 == nil, bad2 and (bad2 .. " → " .. tostring(why2)))
          ck("★★ 第二遍全量重渲染零新建帧（池化复用，不是每切一次建一套）",
             FRAMES == _f1, FRAMES - _f1)
          ck("★ 两遍覆盖的组合数一致（第二遍没有偷偷少渲染）", n2 == n1, n1 .. " / " .. n2)

          -- ---------- 工匠文书详情：三张卡中卡（2026-10-12 用户）----------
          local _fw = FRAMES
          local okW = pcall(function() PD.Show("crates"); PD.SetTab("writ") end)
          ck("★★ 工匠文书页渲染不报错", okW == true)
          ck("★ 工匠文书页零新建帧（卡中卡复用 secCards 池，不新建帧）", FRAMES == _fw, FRAMES - _fw)
          ck("★★ 工匠文书详情四段卡中卡：secCount = 4", PD.secCount == 4, tostring(PD.secCount))
          do
            local _nSec = 0
            for _, c in ipairs(PD.secCards or {}) do
              if c.IsShown and c:IsShown() then _nSec = _nSec + 1 end
            end
            ck("★★ 段落卡可见数 ∈ [3,4]（头部/汇总/总结恒有；材料段要有配方登记）",
               _nSec >= 3 and _nSec <= 4, _nSec)
          end
          do
            local _heads, _fs14 = {}, 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.kind == "head" then _heads[tostring(sp.text or "")] = true end
              if sp.col == 2 and sp.fs == 14 then _fs14 = _fs14 + 1 end
            end
            ck("★★ 详情含「成本汇总 / 总结」两个卡中卡标题（16 默认档）",
               _heads["成本汇总"] == true and _heads["总结"] == true)
            ck("★★ 卡中卡正文行走 fs=14（材料/成本/总结三组）", _fs14 >= 5, _fs14)
          end
          do
            local RA = TF_NS.ProfRouteAuto
            local _oldP = RA and RA.AHPriceOf or nil
            if RA then RA.AHPriceOf = function() return 100 end end
            local okC = pcall(function() PD.SetTab("crate") end)
            ck("★★ 板条箱页渲染不报错", okC == true)
            ck("★★ 板条箱详情三段卡中卡：secCount = 3", PD.secCount == 3, tostring(PD.secCount))
            local _nCrate, _tagBest, _buyRow = 0, false, false
            for _, sp in ipairs(PD.specs or {}) do
              if sp.sec and sp.col == 2 then _nCrate = _nCrate + 1 end
              if sp.tag and sp.tag.text == "最省" then _tagBest = true end
              if type(sp.text) == "string" and sp.text:find("购买 ") then _buyRow = true end
            end
            ck("★★ 板条箱详情卡内行数 >= 6（头部2 + 凑法1 + 总结3）", _nCrate >= 6, _nCrate)
            ck("★★ 最便宜凑法行挂「最省」标签", _tagBest)
            ck("★★ 总结卡含「购买 物品名」行", _buyRow)
            if RA then RA.AHPriceOf = _oldP end
          end

          do
            local _lw = tonumber(PD.splitLW) or 0
            local _shift = tonumber(PD.OwnR and PD.OwnR()) or 0
            local _base = tonumber(PD.CRATE_OWN_R) or 0
            ck("★★ 自身价格列左移量 = 左列行宽 8%（OWN_SHIFT 0.12 → 0.08，即自上次位置右移 4%）",
               _lw > 0 and (_shift - _base) >= _lw * 0.07 and (_shift - _base) <= _lw * 0.09,
               ("行宽=%s 基准=%s 现偏移=%s 位移=%s"):format(_lw, _base, _shift, _shift - _base))
          end

          -- ---------- 数据下限（防「又同步回旧数据 / 生成器漏发射」）----------
          local D, RC, LV, GA = TF_NS.ProfData,
                                (TF_NS.EnsureProfRecipes and TF_NS.EnsureProfRecipes() or nil),
                                TF_NS.ProfLeveling, TF_NS.ProfGathering
          ck("★★ 16 个导航条目都在（order 表，15 专业 + 板条箱）", #(D.order or {}) == 16, #(D.order or {}))
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

          do
            local _t = {}
            for _, k in ipairs(PD.TabsFor("poisons") or {}) do _t[#_t + 1] = k end
            ck("★★ 毒药页子页签 = 配方+升级（总览已删）",
               #_t == 2 and _t[1] == "recipe" and _t[2] == "leveling",
               table.concat(_t, ","))
            local _lv = LV and LV.poisons
            local _n, _c = 0, 0
            if _lv and type(_lv.steps) == "table" then
              for _, st in ipairs(_lv.steps) do
                _n = _n + 1
                _c = _c + (st[4] or 0)
              end
            end
            ck("★ 毒药升级路线 = 13 段 / 200 次制作", _n == 13 and _c == 200,
               tostring(_n) .. " / " .. tostring(_c))
            local _okP = pcall(function() PD.Show("poisons") end)
            local _okL = pcall(function() PD.SetTab("leveling") end)
            ck("★★ 毒药 · 升级页渲染不报错", _okP == true and _okL == true)
            ck("★ 毒药升级页真的画出了行（不是空页）",
               #(PD.specs or {}) > 0, #(PD.specs or {}))
            do
              local _st = 0
              for _, r in ipairs(PD.specs or {}) do
                if r.lvstep then _st = _st + 1 end
              end
              ck("★ 毒药升级页 13 段路线行全部落位", _st == 13, _st)
            end
            do
              local _lt = PD.LevelTool and PD.LevelTool()
              local _has = false
              if _lt then
                for _, b in ipairs(_lt) do
                  if b.key == "recalc" then _has = true end
                end
              end
              ck("★ 毒药升级页工具行无「重新计算」按钮", _has == false)
            end
            ck("★ 毒药升级页信息卡供数（lvSummary 就位且无自动路线）",
               PD.lvSummary ~= nil and PD.lvSummary.auto == false,
               PD.lvSummary and tostring(PD.lvSummary.auto))
            DungeonsForeverDB.prof.autoRoute = true
            DungeonsForeverDB.prof.autoScheme = "optim"
            local _okR2 = pcall(function() PD.SetTab("recipe") end)
            local _okL2 = pcall(function() PD.SetTab("leveling") end)
            ck("★★ 毒药 · 强开自动路线仍走固定路线",
               _okR2 == true and _okL2 == true
               and PD.lvSummary ~= nil and PD.lvSummary.auto == false,
               PD.lvSummary and tostring(PD.lvSummary.auto))
            do
              local _gap = 0
              for _, r in ipairs(PD.specs or {}) do
                if r.kind == "text" and tostring(r.text or ""):find("缺口", 1, true) then
                  _gap = _gap + 1
                end
              end
              ck("★ 毒药升级页无缺口/错误报告行", _gap == 0, _gap)
            end
            DungeonsForeverDB.prof.autoRoute = nil
            DungeonsForeverDB.prof.autoScheme = nil
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

          -- ---------- 护甲片副行改写 KitSub（2026-10-15）----------
          KS1 = PD.KitSub("永久附着于物品，30 级",
            "Permanently increase the Stamina value by 4 and armor value by 32 of an item worn on the chest, legs, hands or feet. Only usable on items level 25 and above.")
          ck("★★ 护甲片副行改写：要求等级 + 属性按出现序拼接（厚重护甲片实样）",
             KS1 == "要求30级 耐力+4 护甲+32", KS1)
          KS2 = PD.KitSub("永久附着于物品",
            "Permanently increase the Stamina value by 1 and the Armor value by 8 of an item worn on the chest, legs, hands or feet.")
          ck("★★ 无等级护甲片：只拼属性不带头", KS2 == "耐力+1 护甲+8", KS2)
          KS3 = PD.KitSub("永久附着於物品，60 級",
            "Permanently increase the Defense Skill by 4 and the Stamina value by 10 of an item worn on the chest, legs, hands, or feet. Only usable on items level 45 and above.")
          ck("★★ 繁体副行可解析 + 防御技能/耐力双属性（出现序）",
             KS3 == "要求60级 防御技能+4 耐力+10", KS3)
          KS4 = PD.KitSub("永久附着于物品",
            "Attaches spurs to your boots that increase your mounted movement speed slightly.")
          ck("★★ 无属性可解析（马刺类）回退原文", KS4 == "永久附着于物品", KS4)
          KS5 = PD.KitSub("普通副行", "whatever")
          ck("★★ 非附着类副行原样返回（门控不误伤）", KS5 == "普通副行", KS5)
          KS1, KS2, KS3, KS4, KS5 = nil, nil, nil, nil, nil

          -- ---------- 配方搜索 + 名称列现算（2026-10-09）----------
          do
            ck("★★ 名称列按本页现算（在 [MIN,MAX] 内、材料列 = 行宽-右保留-起点-8）",
               PD.RECIPE_NAME_W ~= nil
               and PD.RECIPE_NAME_W >= PD.RECIPE_NAME_MIN
               and PD.RECIPE_NAME_W <= PD.RECIPE_NAME_MAX
               and PD.MAT_X == PD.RECIPE_NAME_W + PD.RECIPE_NAME_PAD
               -- 2026-10-10：右保留 = 难度条 + 拍卖列 + 成本列，右三列互相零间距（用户）
               and PD.MAT_W == PD.MAT_ROW_W
                   - (6 + PD.DiffBarW() + PD.REC_AH_W + PD.REC_COST_W)
                   - PD.MAT_X - 8)
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

          -- ---------- 配方页排序（2026-10-13，参考板条箱）：运行时排序 ----------
          do
            local function _col(mode, field, desc)
              PD.recipeSort = mode
              PD.recipeSortDesc = desc and true or false
              local rs = {}
              PD.RowsRecipe(rs)
              local v, n = {}, 0
              for _, s in ipairs(rs) do
                if s ~= nil and s.it ~= nil and (s.kind == "row" or s.kind == nil) then
                  n = n + 1
                  rawset(v, n, s[field])
                end
              end
              return v, n
            end
            local function _ordered(v, n, desc)
              local ok, seenNil = true, false
              for i = 1, n do
                local x = rawget(v, i)
                if x == nil then
                  seenNil = true
                else
                  if seenNil then ok = false end
                  local p = (i > 1) and rawget(v, i - 1) or nil
                  if p ~= nil then
                    if desc and x > p then ok = false end
                    if (not desc) and x < p then ok = false end
                  end
                end
              end
              return ok
            end
            local _, _n0 = _col(nil, "costVal")
            local _cost, _c1 = _col("cost", "costVal", false)
            ck("★★ 配方页「制作成本」升序：成本非降序且行数不丢",
               _n0 > 0 and _c1 == _n0 and _ordered(_cost, _c1, false),
               tostring(_n0) .. " 行")
            local _costD, _c2 = _col("cost", "costVal", true)
            ck("★★ 配方页「制作成本」降序：成本非升序（第二次点击切降序生效）",
               _c2 == _n0 and _ordered(_costD, _c2, true),
               tostring(_c2) .. " 行")
            local _diff, _d1 = _col("diff", "diffVal", false)
            local _dn = 0
            for i = 1, _d1 do if rawget(_diff, i) ~= nil then _dn = _dn + 1 end end
            ck("★★ 配方页「难度」升序：学等级非降序、无值排末尾，且行数不丢",
               _dn > 0 and _d1 == _n0 and _ordered(_diff, _d1, false),
               tostring(_dn) .. " 行有难度")
            local _, _g1 = _col("gap", "gapVal", false)
            ck("★ 配方页「差距」排序：不崩、行数不丢", _g1 == _n0)
            local _, _a1 = _col("ah", "ahVal", false)
            ck("★ 配方页「拍卖」排序：不崩、行数不丢", _a1 == _n0)
            PD.recipeSort = nil
            PD.recipeSortDesc = false
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
            ck("★★ 升级页 v2 单栏化定稿（PD.lvSplit = false；旧右栏退役进购物清单子页）",
               PD.lvSplit == false)
            ck("★★ 单栏下竖向分栏线隐藏（lvSplit=false → divider:Hide）",
               PD.divider ~= nil and PD.divider.__shown ~= true)
            -- ★ v2 单栏化：行宽 = 整幅 LV_ROW_W（RowsLeveling 现算），不再分左右栏
            local _full, _other = 0, 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__w and r.__w > 0 then
                if r.__w == (PD.LV_ROW_W or 0) then _full = _full + 1
                else _other = _other + 1 end
              end
            end
            ck("★★ 升级页单栏：全部行宽 = LV_ROW_W 整幅（无左右栏分工）",
               _full > 0 and _other == 0, tostring(_full) .. " / 其他 " .. tostring(_other))
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
            ck("★★ 分段行存在（alchemy fc 回铺后 18 段）且全部落在单栏（col=1）",
               _st == 18 and _notleft == 0,
               tostring(_st) .. " / 不在单栏 " .. tostring(_notleft))
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
                -- 次数右缘贴**三列最左锚**（pts[2] 是锚对象、pts[4] 是 x —— 桩的记录格式）。
                -- ★ 2026-10-10 三列拆分：次数 @LV_CNT2_R、单次 @LV_UNIT_R、总花费 @LV_CNT_R。
                local cp = r.c.__pts
                if not (cp and cp[2] == r and cp[4] == -PD.LV_CNT2_R) then _cntbad = _cntbad + 1 end
              end
            end
            ck("★★ 渲染后分段行的「配方名 + ~N 次制作」真的画上了（18 段全中）",
               _painted == 18, _painted)
            ck("★★ 左栏「~N 次制作」右缘落在三列最左锚 PD.LV_CNT2_R（不压单次/总花费列）",
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
            ck("★★ 材料区预算足够宽（炼金 ≥280 —— 2026-10-10 三列拆分让出花费列后仍不截成「…」）",
               PD.LV_MAT_W >= 280,
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
            --   ★ 2026-10-10：卡片挪到等级列正下方，**不占行内预算**（可用宽不再扣卡宽）；
            --     三列拆分：再扣单次/总花费两列宽 + 2×LV_COL_GAP 列距 —— 与 RowsLeveling
            --     里的 avail 同一条式子。
            do
            local _avail = PD.LV_ROW_W - PD.TBL_MAT_RPAD - PD.LV_NAME_X - PD.TBL_NAME_GAP
                           - PD.LV_CNT_W - PD.LV_UNIT_W - PD.LV_TOT_W
                           - PD.TBL_CNT_GAP - 2 * PD.LV_COL_GAP
            ck("★★ 名称列 + 材料区正好吃满可用宽（不留白 —— 余量全给材料块；"
               .. "v2 口径：卡片不占行内预算）",
               _avail > 0 and PD.LV_NAME_W + PD.LV_MAT_W == _avail,
               "LV_NAME_W=" .. PD.LV_NAME_W .. " + LV_MAT_W=" .. PD.LV_MAT_W
               .. " = " .. (PD.LV_NAME_W + PD.LV_MAT_W) .. " / avail=" .. _avail)
            end
            ck("★ 材料优先分配：至少保住了名称列下限（材料区拿的是余量，不是被名称列挤掉）",
               PD.LV_NAME_W >= PD.TBL_NAME_MIN and PD.LV_MAT_W > 0,
               "LV_NAME_W=" .. PD.LV_NAME_W .. " / LV_MAT_W=" .. PD.LV_MAT_W)
            -- ★ 2026-10-09 v2 单栏化：右栏退役，全页不存在 col = 2 的行
            local _r2 = 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.col == 2 and sp.kind == "row" then _r2 = _r2 + 1 end
            end
            ck("★★ v2 单栏定稿：右栏退役（无 col = 2 的行）", _r2 == 0, _r2)
            -- 悬停带「配方名 + 来源 + 材料全量」：行级提示框已退役（2026-10-09），
            --   改走 IconZone 热区（图标 + 名称列）→ 产物物品提示框补全信息。
            local _iz = 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__iconZone and r.__iconZone.__it ~= nil
                 and r.__iconZone.__shown ~= false then _iz = _iz + 1 end
            end
            ck("★★ 升级分段行悬停走 IconZone 热区（产物物品提示框，行内放不下的信息不丢）",
               _iz == 18, _iz)
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
            -- ★ 总览单列（2026-10-10 用户定）：简介/开发备注/数字速览删除后不再分栏。
            ck("★ 总览页单列（lvSplit 灭、分栏变量复位、分栏线举手隐藏）",
               PD.lvSplit == false and PD.divider.__shown == false
               and PD.hideDivider == true
               and PD.splitLW == nil and PD.splitRW == nil)
            local _ovL, _ovR = 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.col == 2 then _ovR = _ovR + 1 else _ovL = _ovL + 1 end
            end
            ck("★★ 总览单列：全部行 col=1（右栏行 0 残留）", _ovL > 0 and _ovR == 0,
               tostring(_ovL) .. "L / " .. tostring(_ovR) .. "R")
            local _ovSecs, _ovSecRows = 0, 0
            for _, c in ipairs(PD.secCards or {}) do
              if c.__shown ~= false then _ovSecs = _ovSecs + 1 end
            end
            for _, sp in ipairs(PD.specs or {}) do
              if sp.sec then _ovSecRows = _ovSecRows + 1 end
            end
            ck("★★ 总览每个内容块一张段落卡（速览已删后存量段，≤ 卡池上限）",
               _ovSecs >= 2 and _ovSecs <= (PD.SEC_CARD_MAX or 8) and _ovSecRows >= 6,
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
              ck("★★ 宫格 16 张卡都建出来了（16 条目 × 四段分组）", _ixn == 16, _ixn)
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
                ck("★★ 点营地卡 → 直达总览页对照表（camping + bonus 视图，四合一）",
                   PD.cur == "camping" and PD.tab == "overview" and PD.campView == "bonus"
                   and PD.wantBonusTable == true and PD.bonusTable.__shown == true,
                   tostring(PD.cur) .. "/" .. tostring(PD.tab) .. "/" .. tostring(PD.campView))
              end
              PD.Show("alchemy")
              PD.SetTab("overview")
              ck("★ 离开全部专业 → 宫格整块隐藏、举手复位",
                 PD.ixRoot.__shown == false and PD.wantIndexGrid == false,
                 tostring(PD.ixRoot.__shown) .. "/" .. tostring(PD.wantIndexGrid))
            end
            -- ⑱ 全部专业页退役 + 默认/记忆（2026-10-10 用户）
            do
              ck("★ 左列不再有「全部专业」按钮（navKey 无 __index）",
                 PD.navKey.__index == nil)
              DungeonsForeverDB = DungeonsForeverDB or {}
              DungeonsForeverDB.prof = DungeonsForeverDB.prof or {}
              DungeonsForeverDB.prof.lastSlug = nil
              DungeonsForeverDB.prof.lastTab = nil
              PD.cur = nil
              PD.Open()
              ck("★★ 首次进专业页 → 默认已学主要专业（桩无 GetProfessions ⇒ 首个导航项）",
                 PD.cur ~= nil and PD.cur ~= "__index" and PD.cur == (PD.navOrder or {})[1],
                 tostring(PD.cur))
              local _mtab = "overview"
              for _, t in ipairs({ "recipe", "gather", "leveling" }) do
                if PD.avail and PD.avail[t] then _mtab = t break end
              end
              PD.SetTab(_mtab)
              ck("★★ 切子页签 → 记忆落库（lastSlug/lastTab）",
                 DungeonsForeverDB.prof.lastSlug == PD.cur
                 and DungeonsForeverDB.prof.lastTab == _mtab,
                 tostring(DungeonsForeverDB.prof.lastSlug) .. "/" ..
                 tostring(DungeonsForeverDB.prof.lastTab) .. " / 期望 " .. tostring(_mtab))
              PD.cur = nil
              PD.Open()
              ck("★★ 模拟重开 → 回到上次离开的（专业+子页签）",
                 PD.cur == DungeonsForeverDB.prof.lastSlug and PD.tab == _mtab,
                 tostring(PD.cur) .. "/" .. tostring(PD.tab))
            end
            PD.Show("alchemy")
            PD.SetTab("leveling")
            -- ★ 2026-10-09 v2 单栏化定稿：升级页不再举手分栏（lvSplit 恒 false），
            --   总览的 0.62 举手自然不外溢 —— 分栏常量退役但引用位保留兜底。
            ck("★ 升级页 v2 单栏定稿（lvSplit 不举手、0.62 分栏不外溢）",
               PD.lvSplit == false and PD.splitLW == nil and PD.splitRW == nil)
            PD.Show("alchemy")
            PD.SetTab("overview")

            -- ② 四合一（2026-10-10）：camping 总览页直出对照表（营地页签退役）
            PD.Show("camping")
            PD.SetTab("overview")
            ck("★★ camping 总览直出对照表（bonus 视图举手，对照总表就绪）",
               PD.campView == "bonus" and PD.wantBonusTable == true
               and PD.bonusTable ~= nil and PD.bonusTable.__shown == true,
               tostring(PD.campView) .. "/" .. tostring(PD.wantBonusTable))
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
            PD.SetTab("overview")
            -- ②b 四合一：总览页段落卡（传承/营地/速览… ≤ SEC_CARD_MAX）
            ck("★★ 有营地数据的专业总览套段落卡（段数 ≥2 且 ≤ 卡池上限）",
               PD.hasSecs == true and PD.secCount >= 2
               and PD.secCount <= (PD.SEC_CARD_MAX or 8)
               and PD.bonusTable.__shown == false, tostring(PD.secCount))
            local _campCards = 0
            for _, c in ipairs(PD.secCards or {}) do
              if c.__shown ~= false then _campCards = _campCards + 1 end
            end
            ck("★★ 可见段落卡数 = 段数", _campCards == PD.secCount,
               tostring(_campCards) .. " 卡 / " .. tostring(PD.secCount) .. " 段")
            local _campZ = 0
            for _, r in ipairs(PD.rows or {}) do
              if r.__shown ~= false and r.__z then _campZ = _campZ + 1 end
            end
            ck("★★ 段落卡页不出斑马纹（与总览同口径）", _campZ == 0, _campZ)
            -- ★★ D1 去重：旧「营地三档」行（技能 N · 物件名）不再出现在总览
            local _dupCamp = 0
            for _, sp in ipairs(PD.specs or {}) do
              if type(sp.text) == "string"
                 and sp.text:find("^技能 %d+ · ", 1) then _dupCamp = _dupCamp + 1 end
            end
            ck("★★ D1 去重生效：总览无旧「营地三档」行", _dupCamp == 0, _dupCamp)
            -- ★★ 联盟/部落坐标行同列直出（每阵营一行：有军需官出军需官行，否则兜底营地行）
            local _campRows = {}
            for _, sp in ipairs(PD.specs or {}) do
              if type(sp.text) == "string"
                 and (sp.text:find("军需官 · ", 1, true) or sp.text:find("营地 · ", 1, true)) then
                _campRows[#_campRows + 1] = sp
              end
            end
            ck("★★ 联盟/部落坐标行同列（2 行、字体色互异）",
               #_campRows == 2 and _campRows[1].nameColor ~= nil
               and (_campRows[1].nameColor[1] ~= _campRows[2].nameColor[1]
                    or _campRows[1].nameColor[3] ~= _campRows[2].nameColor[3]),
               tostring(#_campRows))
            PD.Show("camping")
            PD.SetTab("overview")
            ck("★ 切走再切回来 → 对照总表还在总览页",
               PD.campView == "bonus" and PD.wantBonusTable == true
               and PD.bonusTable.__shown == true)
            PD.Show("alchemy")

            -- ⑲ 营地/军需官 → 地图标记（2026-09-24 用户：点军需官坐标在地图上标记 + 这一段汉化）
            -- ★★ 二轮（用户实机报「未收录该位置的地图」）：无限服源码 1.60.1 全库没有
            --    C_Map.GetMapInfoFromAreaID → 主路径改静态映射（CAMP_AREA_MAP），
            --    本块**不**挂该 API 桩模拟真机；区域名走 GetAreaInfo（无限服有）。
            do
              PD.Show("alchemy")
              PD.SetTab("overview")
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
              local _vspecA, _vspecH
              for _, sp in ipairs(PD.specs or {}) do
                if type(sp.text) == "string" and sp.text:find("军需官 · 妮娜·神火", 1, true) then _vspecA = sp end
                if type(sp.text) == "string" and sp.text:find("军需官 · 药剂师杜蕾尔", 1, true) then _vspecH = sp end
              end
              ck("★ 军需官行副行 = 组织·区域·地点（zh.json + GetAreaInfo 套用）",
                 _vspecA ~= nil and _vspecA.sub == "艾泽拉斯商会 · 赤脊山 · 三岔口"
                 and _vspecH ~= nil and _vspecH.sub == "杜隆塔尔补给与后勤 · 贫瘠之地 · 十字路口外",
                 _vspecA and tostring(_vspecA.sub) or "nil")
              ck("★★ 两行都可点且带悬停提示（act + lines）",
                 _vspecA ~= nil and type(_vspecA.act) == "function" and _vspecA.lines ~= nil
                 and _vspecH ~= nil and type(_vspecH.act) == "function" and _vspecH.lines ~= nil)
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              _vspecA.act()
              ck("★★ 点联盟军需官行 → 航点落赤脊山(1433) 10.8,72.4 并开图（静态映射主路径）",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1433
                 and C_MAP_MARK.wp.x == 10.8 / 100 and C_MAP_MARK.wp.y == 72.4 / 100
                 and C_MAP_MARK.opened == 1433,
                 C_MAP_MARK.wp and tostring(C_MAP_MARK.wp.uiMapID) or "nil")
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              _vspecH.act()
              ck("★★ 点部落军需官行 → 航点落贫瘠之地(1413) 49.8,29.4",
                 C_MAP_MARK.wp ~= nil and C_MAP_MARK.wp.uiMapID == 1413
                 and C_MAP_MARK.wp.x == 49.8 / 100 and C_MAP_MARK.wp.y == 29.4 / 100)
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
              PD.SetTab("overview")
              local _vspecA2
              for _, sp in ipairs(PD.specs or {}) do
                if type(sp.text) == "string" and sp.text:find("军需官 · 妮娜·神火", 1, true) then _vspecA2 = sp end
              end
              ck("★ 区域名回落数据原文（zh.json 兜底仍是中文）",
                 _vspecA2 ~= nil and _vspecA2.sub == "艾泽拉斯商会 · 赤脊山 · 三岔口",
                 _vspecA2 and tostring(_vspecA2.sub) or "nil")
              -- 未知区域：静态表和 API 都没有 → 明说不假装（不放航点、不开图）
              C_MAP_MARK.wp, C_MAP_MARK.opened = nil, nil
              PD.MarkCampPoint(9999, 10.0, 20.0)
              ck("★★ 未知区域明说不假装：不放航点、不开图",
                 C_MAP_MARK.wp == nil and C_MAP_MARK.opened == nil)
              PD.Show("alchemy")
            end

            -- ③ 阈值染色（2026-10-10 新口径）：阈值彩色文字带退役 → 难度全交四段色条
            --   （PaintDiffBar，色取 SB_COL 四段两两不同）；有阈值行 right 置 nil 防叠印，
            --   无阈值行才走 TierText 文字兜底。
            PD.Show("alchemy")
            PD.SetTab("recipe")
            local _bar, _keep, _bad = 0, 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.sbdiff then
                _bar = _bar + 1
                if sp.right == nil then _keep = _keep + 1 end
              end
              local t = sp.right
              if type(t) == "string" and t:find("黄绿灰", 1, true) then _bad = _bad + 1 end
            end
            ck("★★ 有阈值的配方行走四段色条（sbdiff 落了）且文字带置 nil 防叠印",
               _bar > 0 and _keep == _bar, tostring(_bar) .. " 条 / right=nil " .. tostring(_keep))
            ck("★★ 配方行不再出现「黄绿灰」三个字", _bad == 0, _bad)
            local _c2, _c3, _c4 = PD.SB_COL[2], PD.SB_COL[3], PD.SB_COL[4]
            local _same = (_c2[1] == _c3[1] and _c2[2] == _c3[2] and _c2[3] == _c3[3])
               or (_c3[1] == _c4[1] and _c3[2] == _c4[2] and _c3[3] == _c4[3])
               or (_c2[1] == _c4[1] and _c2[2] == _c4[2] and _c2[3] == _c4[3])
            ck("★★ 黄 / 绿 / 灰 三段色确实互不相同（同一个色 = 等于没染）",
               PD.SB_COL ~= nil and not _same)

            -- ④ 四合一：传承/说明退出页签（内容并入总览合段）
            ck("★★ 子页签序 = 总览/训练师/配方/采集/升级/板条箱/工匠文书、第 8 颗不存在（遭劫货物暂撤）",
               PDM.PROF_SUBTABS[2] ~= nil and PDM.PROF_SUBTABS[2].key == "trainer"
               and PDM.PROF_SUBTABS[5] ~= nil and PDM.PROF_SUBTABS[5].key == "leveling"
               and PDM.PROF_SUBTABS[6] ~= nil and PDM.PROF_SUBTABS[6].key == "crate"
               and PDM.PROF_SUBTABS[7] ~= nil and PDM.PROF_SUBTABS[7].key == "writ"
               and PDM.PROF_SUBTABS[8] == nil,
               PDM.PROF_SUBTABS[8] and PDM.PROF_SUBTABS[8].key or "nil")

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
            local _nrow, _tog = 0, 0
            for _, sp in ipairs(PD.specs or {}) do
              if sp.kind == "row" then _nrow = _nrow + 1 end
              if sp.kind == "row" and sp.togKey then _tog = _tog + 1 end
            end
            -- ★ 1.7.1 设置双卡：老开关 2 个 + 自动路线 5 个（行数随功能增减，
            --   钉「每行都绑了 togKey」而不是钉行数）
            ck("★★ ㉒ 设置页开关行全带 togKey（≥2：灰显 + 高亮；1.7.1 起另有自动路线五开关）",
               _tog >= 2 and _nrow == _tog, _nrow .. " 行 / " .. _tog .. " 绑键")
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
              ck("★★ ㉒ 当前段唯一且上限跨着 42（= 下一格；分段随 fc 数据浮动不写死 58/45）",
                 _ncur == 1 and _curHi ~= nil and _curHi > 42, tostring(_curHi))
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

          -- ---------- 切回副本页：三页互斥不破、副本页照旧可用 ----------
          U:SwitchSub("Dungeons")
          ck("★ 切回 5人本 → 专业页隐藏", U.profPage.__shown == false)
          ck("★ 切回 5人本 → 副本页显示且仍是已构建态",
             U.dungeonPage.__shown == true and U.dungeonBuilt == true)
        end
      end
    end
    -- 页面重建（UI:Build 复位路径）：池与子帧必须整体丢弃，不能跨页复用
    ck("页面复位时池引用已清空准备重建",
       U.dungeonDetailChild == dc0 and U.dungeonListChild == child0)
  end)
  if not ok then
    -- ★ 报错文本里可能带换行（Lua 的报错常跟一行源码位置）：不回换成空格的话，
    --   Python 侧 split('\n') 会把一行拆成两行，诊断直接丢（已踩过一次）。
    R[#R + 1] = "FAIL\tLua 断言块抛异常\t["
      .. tostring(err):gsub("[\r\n]+", " "):sub(1, 400) .. "]"
    R[#R + 1] = "TRACE\t" .. tostring(debug and debug.traceback and debug.traceback(err, 2) or "no-traceback")
      :gsub("[\r\n]+", " || "):gsub("\t", " ")
  end
  return table.concat(R, "\n")
end)()
'''


def main():
    section('无限副本手册 · 副本页回归检查（TF_BUILD=%d，加载自 beta 副本）' % CLIENT_BUILD)
    static_guard()

    toc = open(TOC, encoding='utf-8', errors='replace').read()
    import re as _re
    files = [_re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
            for l in toc.splitlines()
            if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    # ★★ 2026-10-09 懒构建 + 分帧泵：T.STUB 的 C_Timer.After 是**丢弃回调**的空桩，
    #    RunSteps 的自续泵（After(0, pump)）排进去就再也不会跑 ⇒ 渲染永远停在首块
    #    （pending 堆积、通灵池只建 13/292、几何断言全错位）。这里覆盖成：
    #    t==0（分帧泵自续）**立即执行**（等价「C_Timer 缺失时同步跑完」的离线契约），
    #    t>0（到货重扫等业务定时）**记录排队**（SWEEPS 计数断言沿用；后续 3804 块再接管）。
    lua.execute(r'''
C_Timer = { After = function(t, fn)
    if t == 0 then fn(); return end
    SWEEPS = SWEEPS or {}
    SWEEPS[#SWEEPS + 1] = { t = t, fn = fn }
end, NewTimer = function(t, fn)
    if t == 0 then fn(); return {} end
    SWEEPS = SWEEPS or {}
    SWEEPS[#SWEEPS + 1] = { t = t, fn = fn }
    return {}
end }
''')
    # ★★ 环境与客户端同形（2026-09-29 实机事故）：WoW 的 Lua **没有 os 库**
    #    （暴雪用全局 time() / date() / difftime() 顶替），而 lupa 自带完整标准库
    #    → 「写了 os.* 的代码」在离线 harness 恒绿、实机必崩（团本页倒计时就栽在这）。
    #    这里把 os 抹掉、补上全局 time()（固定时刻，便于断言「无参调用」那条路径）。
    #    注意：桩自身不用 os，所以抹掉是安全的；哪天桩要用，得先在这里补等价实现。
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute('GetCursorPosition = function() return 400, 300 end')
    lua.execute("BG.hui.OnThemeChange = function(fn) end")  # ⑳ 主题监听桩
    lua.execute('UnitClass = function() return "盗贼", "ROGUE", 4 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute(
        'do local orig = GetBuildInfo; GetBuildInfo = function(...) '
        'local a,b,c,d = orig(...); return a, b, c, %d, e end end' % CLIENT_BUILD)
    # 地图标记桩（2026-09-22）：记录 SetUserWaypoint / OpenWorldMap 的实参供动态断言
    lua.execute(r'''
UIErrorsFrame = { AddMessage = function() end }
C_SuperTrack = { SetSuperTrackedUserWaypoint = function() end }
C_MAP_MARK = { wp = nil, opened = nil }
UiMapPoint = {
  CreateFromCoordinates = function(mapID, x, y)
    return { uiMapID = mapID, x = x, y = y }
  end,
}
C_Map = {
  CanSetUserWaypointOnMap = function() return true end,
  SetUserWaypoint = function(pt) C_MAP_MARK.wp = pt end,
  OpenWorldMap = function(mapID) C_MAP_MARK.opened = mapID end,
}
''')

    # ★ 提示框换肤的桩（2026-09-23，见 mk_df_check.py 第⑫步）：
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
    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')

    section('按真实 TOC 顺序加载 %d 个文件' % len(files))
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        chunk = loadfile(rel)
        if chunk is None:
            ck('加载 %s' % rel, False, 'loadfile 返回 nil')
            return 1
        try:
            chunk()
        except Exception as e:
            ck('加载 %s' % rel, False, str(e)[:200])
            return 1
    print('   全部 %d 个 Lua 文件加载完成' % len([f for f in files if not f.lower().endswith('.xml')]))

    section('行为断言')
    out = lua.eval(LUA_SCRIPT)
    for line in (out or '').split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            ck('Lua 侧输出缺制表符（疑似多行文本被拆行）', False, line[:300])
            continue
        ck(parts[1], parts[0] == 'OK', parts[2] if len(parts) > 2 else None)

    section('结论')
    print('通过 %d 项 / 失败 %d 项' % (len(PASSED), len(FAILED)))
    if FAILED:
        for f in FAILED:
            print('  ✗ %s' % f)
        return 1
    print('  ✓ 全部通过')
    return 0



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


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""团本页 · 国服比外服晚 1 天（幂等补丁）

改动三件事，一次写好（锚点命中数 != 1 就中止，已打过就 SKIP）：
  1) Core/RaidUI.lua —— 首批开放日由 RU.FirstOpenText() 按地区算出（表里不再写死）；
     倒计时锚点走 RU.UnlockAt(shift)；两页共用 RecDateText()。
  2) _temp/df_dungeon_check.py + _temp/mk_df_check.py —— 断言同步 + 补 4 条静态 / 6 条运行时。

用法：python _temp/_patch_raid_cn.py      （幂等，可重复跑）
"""
import io
import os
import py_compile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

RAID = os.path.join(ROOT, 'Core', 'RaidUI.lua')
CHECKS = [os.path.join(HERE, 'df_dungeon_check.py'),
          os.path.join(HERE, 'mk_df_check.py')]


def read(path):
    with io.open(path, 'rb') as f:
        raw = f.read()
    return raw.decode('utf-8').replace('\r\n', '\n'), (b'\r\n' in raw)


def write(path, txt, crlf):
    if crlf:
        txt = txt.replace('\n', '\r\n')
    with io.open(path, 'wb') as f:
        f.write(txt.encode('utf-8'))


def sub1(path, txt, old, new, marker):
    """整段替换：old 必须恰好命中 1 次；marker 已在文件里则视为已打过。"""
    if marker in txt:
        print('  SKIP %s' % marker)
        return txt, False
    n = txt.count(old)
    if n != 1:
        raise SystemExit('!! 锚点命中 %d 次（应为 1）：%s\n   %r' % (n, path, old[:90]))
    print('  OK   %s' % marker)
    return txt.replace(old, new), True


# ─────────────────────────────────────────────────────────────────────────────
# 1) Core/RaidUI.lua
# ─────────────────────────────────────────────────────────────────────────────
RAID_EDITS = [
    # ① 文件头：补「国服 +1 天」这条口径
    (
        '-- ★ 倒计时只到「分」（用户 2026-09-29 定）：官方开放时刻本身是按惯例推算的，\n'
        '--   给到秒是假精度；RU.CountdownText(nowSec) 是纯函数（默认取 os.time()），\n'
        '--   Build 里挂 1 秒 OnUpdate 重算，只在文本变化时才 SetText。\n'
        '--   RU.DATA.unlockAt = 2026-12-09 13:00 PST 的 epoch（首批三座同日开启）。\n',
        '-- ★ 倒计时只到「分」（用户 2026-09-29 定）：官方开放时刻本身是按惯例推算的，\n'
        '--   给到秒是假精度；RU.CountdownText(nowSec, shift) 是纯函数（默认取 os.time()），\n'
        '--   Build 里挂 1 秒 OnUpdate 重算，只在文本变化时才 SetText。\n'
        '--   RU.DATA.unlockAt = 2026-12-09 13:00 PST 的 epoch（首批三座同日开启）。\n'
        '--\n'
        '-- ★★ 国服比外服晚 1 天（用户 2026-09-29 定）：排期基准是**外服口径**\n'
        '--   （RU.DATA.firstOpen = 2026-12-09），zhCN 客户端（国服）整体后移一天 ——\n'
        '--   页面显示「2026 年 12 月 10 日」，倒计时锚点同步 +86400。\n'
        '--   判定收在 RU.DayShift(cn)：显式传 true / false 可覆盖，不传则按\n'
        '--   GetLocale() == "zhCN" 自动判；改天数只动 RU.CN_SHIFT（台服 zhTW / enUS\n'
        '--   都按外服口径走）。首批三座的 date 由 RU.FirstOpenText(shift) 算出来，\n'
        '--   表里不再写死日期；时间线节点标签与卡片日期共用 RecDateText()，两页不会各显示一个日期。\n',
        '国服比外服晚 1 天',
    ),
    # ② 常量：移位天数
    (
        'RU.RULES_DESC_X = 96\n\n'
        'RU.DATA = {\n',
        'RU.RULES_DESC_X = 96\n\n'
        'RU.CN_SHIFT = 1\n\n'
        'RU.DATA = {\n',
        'RU.CN_SHIFT = 1',
    ),
    # ③ 数据：首批日期改成结构化基准（只留第一档的 y/m/d，表里不再写死字符串）
    (
        '    updated = "2026-09-24",\n'
        '    unlockAt = 1796850000,\n'
        '    raids = {\n'
        '        { name = "深穴", size = 10, date = "2026 年 12 月 9 日", first = true },\n'
        '        { name = "海加尔峰", size = 20, zone = "海加尔山", date = "2026 年 12 月 9 日", first = true },\n'
        '        { name = "奥妮克希亚的巢穴", size = 40, zone = "尘泥沼泽", date = "2026 年 12 月 9 日", first = true },\n',
        '    updated = "2026-09-24",\n'
        '    unlockAt = 1796850000,\n'
        '    firstOpen = { y = 2026, m = 12, d = 9 },\n'
        '    raids = {\n'
        '        { name = "深穴", size = 10, first = true },\n'
        '        { name = "海加尔峰", size = 20, zone = "海加尔山", first = true },\n'
        '        { name = "奥妮克希亚的巢穴", size = 40, zone = "尘泥沼泽", first = true },\n',
        'firstOpen = { y = 2026, m = 12, d = 9 }',
    ),
    # ④ 地区判定 + 日期/锚点解析（纯函数，便于离线断言两档）
    (
        'local function SizeText(n)\n'
        '    if type(n) == "number" then return format("%d%s", n, L["人"]) end\n'
        '    return L["未公布"]\n'
        'end\n',
        'local function SizeText(n)\n'
        '    if type(n) == "number" then return format("%d%s", n, L["人"]) end\n'
        '    return L["未公布"]\n'
        'end\n'
        '\n'
        'local function IsCnClient()\n'
        '    return type(GetLocale) == "function" and GetLocale() == "zhCN"\n'
        'end\n'
        '\n'
        'function RU.DayShift(cn)\n'
        '    if cn == nil then cn = IsCnClient() end\n'
        '    return cn and RU.CN_SHIFT or 0\n'
        'end\n'
        '\n'
        'function RU.UnlockAt(shift)\n'
        '    return RU.DATA.unlockAt + RU.DayShift(shift) * 86400\n'
        'end\n'
        '\n'
        'function RU.FirstOpenText(shift)\n'
        '    local f = RU.DATA.firstOpen\n'
        '    return format(L["%d 年 %d 月 %d 日"], f.y, f.m, f.d + RU.DayShift(shift))\n'
        'end\n'
        '\n'
        'local function RecDateText(rec)\n'
        '    if rec.date then return rec.date end\n'
        '    if rec.first then return RU.FirstOpenText() end\n'
        '    return L["未公布"]\n'
        'end\n',
        'function RU.DayShift(cn)',
    ),
    # ⑤ 倒计时：锚点跟着地区走
    (
        'function RU.CountdownText(nowSec)\n'
        '    local remain = RU.DATA.unlockAt - (nowSec or os.time())\n',
        'function RU.CountdownText(nowSec, shift)\n'
        '    local remain = RU.UnlockAt(shift) - (nowSec or os.time())\n',
        'function RU.CountdownText(nowSec, shift)',
    ),
    # ⑥ 时间线聚节点：标签改用解析后的日期
    (
        'local function BuildNodes()\n'
        '    local out = {}\n'
        '    for _, rec in ipairs(RU.DATA.raids) do\n'
        '        local last = out[#out]\n'
        '        if last and last.date == rec.date then\n'
        '            last.rows[#last.rows + 1] = rec\n'
        '        else\n'
        '            out[#out + 1] = { date = rec.date, first = rec.first == true, rows = { rec } }\n',
        'local function BuildNodes()\n'
        '    local out = {}\n'
        '    for _, rec in ipairs(RU.DATA.raids) do\n'
        '        local label = RecDateText(rec)\n'
        '        local last = out[#out]\n'
        '        if last and last.date == label then\n'
        '            last.rows[#last.rows + 1] = rec\n'
        '        else\n'
        '            out[#out + 1] = { date = label, first = rec.first == true, rows = { rec } }\n',
        'local label = RecDateText(rec)',
    ),
    # ⑦ 卡墙卡片日期：同一个解析函数
    (
        '    c.date:SetText(rec.date or L["未公布"])\n',
        '    c.date:SetText(RecDateText(rec))\n',
        'c.date:SetText(RecDateText(rec))',
    ),
    # ⑧ 卡墙分档标题右侧的说明也走解析后的日期
    (
        '          title = L["首批开启"], note = L["2026 年 12 月 9 日 · 同日开启"] },\n',
        '          title = L["首批开启"], note = RU.FirstOpenText() .. " · " .. L["同日开启"] },\n',
        'note = RU.FirstOpenText() .. " · " .. L["同日开启"]',
    ),
]

print('== 1) Core/RaidUI.lua ==')
txt, crlf = read(RAID)
changed = 0
for old, new, marker in RAID_EDITS:
    txt, hit = sub1(RAID, txt, old, new, marker)
    changed += 1 if hit else 0
if changed:
    write(RAID, txt, crlf)
print('   RaidUI 落盘 = %s（行尾 %s，共 %d 处）'
      % (bool(changed), 'CRLF' if crlf else 'LF', changed))


# ─────────────────────────────────────────────────────────────────────────────
# 2) 两份 harness：静态断言
# ─────────────────────────────────────────────────────────────────────────────
STATIC_OLD = (
    "    ck('★★ RaidUI 倒计时到「分」（纯函数 RU.CountdownText，默认 os.time()）',\n"
    "       'function RU.CountdownText(nowSec)' in _ra\n"
    "       and 'RU.DATA.unlockAt - (nowSec or os.time())' in _ra)\n"
)
STATIC_NEW = (
    "    ck('★★ RaidUI 倒计时到「分」（纯函数 RU.CountdownText，默认 os.time()）',\n"
    "       'function RU.CountdownText(nowSec, shift)' in _ra\n"
    "       and 'RU.UnlockAt(shift) - (nowSec or os.time())' in _ra)\n"
    "    ck('★★ 国服比外服晚 1 天（RU.CN_SHIFT + RU.DayShift，zhCN 自动判 / 可显式覆盖）',\n"
    "       'RU.CN_SHIFT = 1' in _ra\n"
    "       and 'function RU.DayShift(cn)' in _ra\n"
    "       and 'if cn == nil then cn = IsCnClient() end' in _ra\n"
    "       and 'GetLocale() == \"zhCN\"' in _ra)\n"
    "    ck('★★ 首批开放日不写死（表里只留 firstOpen 基准，日期按地区算）',\n"
    "       'firstOpen = { y = 2026, m = 12, d = 9 }' in _ra\n"
    "       and '2026 年 12 月 9 日' not in _ra\n"
    "       and 'function RU.FirstOpenText(shift)' in _ra\n"
    "       and 'format(L[\"%d 年 %d 月 %d 日\"], f.y, f.m, f.d + RU.DayShift(shift))' in _ra)\n"
    "    ck('★★ 时间线节点标签与卡墙卡片日期共用 RecDateText（两页不许各显示一个日期）',\n"
    "       'local function RecDateText(rec)' in _ra\n"
    "       and 'local label = RecDateText(rec)' in _ra\n"
    "       and 'c.date:SetText(RecDateText(rec))' in _ra\n"
    "       and 'note = RU.FirstOpenText() .. \" · \" .. L[\"同日开启\"]' in _ra)\n"
)
STATIC_MARKER = "国服比外服晚 1 天（RU.CN_SHIFT + RU.DayShift"

# 运行时断言：把「首批同日开启」与「倒计时」两块换掉
RT_OPEN_OLD = (
    "      ck(\"★★ 首批同日开启（三座共用 2026-12-09 这个窗口）\",\n"
    "         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].date == \"2026 年 12 月 9 日\"\n"
    "         and RM.DATA.raids[1].first == true and RM.DATA.raids[3].first == true)\n"
)
RT_OPEN_NEW = (
    "      ck(\"★★ 首批同日开启（三座共用同一个开放窗口，日期由地区算出）\",\n"
    "         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].date == nil\n"
    "         and RM.DATA.raids[1].first == true and RM.DATA.raids[3].first == true)\n"
    "      ck(\"★★ 时间线首节点标签 = 地区算出的开放日（桩 GetLocale=zhCN ⇒ 国服口径）\",\n"
    "         RM ~= nil and RM.nodes ~= nil and RM.nodes[1].date == RM.FirstOpenText()\n"
    "         and RM.nodes[1].date == \"2026 年 12 月 10 日\",\n"
    "         tostring(RM and RM.nodes and RM.nodes[1] and RM.nodes[1].date))\n"
)
RT_OPEN_MARKER = "地区算出的开放日（桩 GetLocale=zhCN"

RT_CD_OLD = (
    "        ck(\"★★ 倒计时到「分」：剩 1 天 1 小时 1 分\",\n"
    "           RM.CountdownText(_tgt - (86400 + 3600 + 60)) == \"距首批开放还有 1 天 1 小时 1 分\",\n"
    "           RM.CountdownText(_tgt - (86400 + 3600 + 60)))\n"
    "        ck(\"★★ 倒计时跨过开放时刻即显示「已开启」\",\n"
    "           RM.CountdownText(_tgt + 10) == \"已开启\", RM.CountdownText(_tgt + 10))\n"
)
RT_CD_NEW = (
    "        ck(\"★★ 地区移位：外服 0 天 / 国服 1 天（显式覆盖两档）\",\n"
    "           RM.DayShift(false) == 0 and RM.DayShift(true) == 1\n"
    "           and RM.UnlockAt(false) == _tgt and RM.UnlockAt(true) == _tgt + 86400,\n"
    "           tostring(RM.DayShift(false)) .. \" / \" .. tostring(RM.DayShift(true)))\n"
    "        ck(\"★★ 自动判定（桩 GetLocale = zhCN ⇒ 国服口径，锚点 +1 天）\",\n"
    "           RM.DayShift() == 1 and RM.UnlockAt() == _tgt + 86400,\n"
    "           tostring(RM.UnlockAt()))\n"
    "        ck(\"★★ 开放日文案：外服 2026 年 12 月 9 日 / 国服 2026 年 12 月 10 日\",\n"
    "           RM.FirstOpenText(false) == \"2026 年 12 月 9 日\"\n"
    "           and RM.FirstOpenText(true) == \"2026 年 12 月 10 日\",\n"
    "           RM.FirstOpenText(false) .. \" / \" .. RM.FirstOpenText(true))\n"
    "        ck(\"★★ 倒计时到「分」：各按自己的锚点算 ⇒ 都是 1 天 1 小时 1 分\",\n"
    "           RM.CountdownText(_tgt - (86400 + 3600 + 60), false)\n"
    "               == \"距首批开放还有 1 天 1 小时 1 分\"\n"
    "           and RM.CountdownText(_tgt + 86400 - (86400 + 3600 + 60), true)\n"
    "               == \"距首批开放还有 1 天 1 小时 1 分\",\n"
    "           RM.CountdownText(_tgt - (86400 + 3600 + 60), false))\n"
    "        ck(\"★★ 国服在外服开放时刻尚未开启（锚点确实后移了一天）\",\n"
    "           RM.CountdownText(_tgt + 10, true) ~= \"已开启\"\n"
    "           and RM.CountdownText(_tgt + 86400 + 10, true) == \"已开启\",\n"
    "           RM.CountdownText(_tgt + 10, true))\n"
    "        ck(\"★★ 倒计时跨过开放时刻即显示「已开启」（两档各自跨点）\",\n"
    "           RM.CountdownText(_tgt + 10, false) == \"已开启\",\n"
    "           RM.CountdownText(_tgt + 10, false))\n"
)
RT_CD_MARKER = "国服在外服开放时刻尚未开启"

print('== 2) harness 两份 ==')
for path in CHECKS:
    print(' %s' % os.path.basename(path))
    txt, crlf = read(path)
    changed = 0
    for old, new, marker in ((STATIC_OLD, STATIC_NEW, STATIC_MARKER),
                             (RT_OPEN_OLD, RT_OPEN_NEW, RT_OPEN_MARKER),
                             (RT_CD_OLD, RT_CD_NEW, RT_CD_MARKER)):
        txt, hit = sub1(path, txt, old, new, marker)
        changed += 1 if hit else 0
    if changed:
        compile(txt, path, 'exec')   # 落盘前语法自检（Lua 语法混进 Python 段会在这里炸）
        write(path, txt, crlf)
        py_compile.compile(path, doraise=True)
    print('   落盘 = %s（行尾 %s，共 %d 处）'
          % (bool(changed), 'CRLF' if crlf else 'LF', changed))

print('\npy_compile OK；全部补丁幂等完成。')

# -*- coding: utf-8 -*-
"""一趟改完三件事（2026-09-29 用户实机反馈）：

  ① 时间轴轴线戳出窗口  —— RenderTimeline 里轴线尾端锚错了参照点：
       `SetPoint("BOTTOMLEFT", RU.page, "BOTTOMLEFT", x, -(y))`
     BOTTOMLEFT 锚点的 y 是「自下缘向上」，负值 = 往页面**下面**画 →
     轴线从首节点一路穿过底注、戳出窗口底边（实机截图实锤）。
     改成两端都锚 `TOPLEFT`：y 负值即向下，尾端落在 y 处。

  ② 补倒计时（用户口径：到「分」，不给秒）
     纯函数 `RU.CountdownText(nowSec)`（默认 os.time()），Build 里挂 1 秒 OnUpdate
     重算、只在文本变化时才 SetText。锚点 unlockAt = 2026-12-09 13:00 PST。

  ③ 「国服待确定」注释挂到「团本规则」里 禁止 GDKP 那行的描述右侧。

同时把这几条钉进两份 harness（静态闸 + 运行时闸）。
幂等：重复跑不会重复插入；每个旧串必须恰好命中 1 次，否则报错退出。
"""
import io
import os
import py_compile
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FAIL = []


def patch(name, pairs):
    path = os.path.join(ROOT, name)
    with io.open(path, encoding='utf-8') as f:
        src = f.read()
    nl = '\r\n' if '\r\n' in src else '\n'
    if nl != '\n':
        src = src.replace('\r\n', '\n')
    for tag, old, new in pairs:
        old_n = old.replace('\n', nl) if False else old
        if new in src:
            print('  [SKIP ] %-46s %s' % (name, tag))
            continue
        cnt = src.count(old)
        if cnt != 1:
            FAIL.append('%s :: %s 旧串命中 %d 次（应为 1）' % (name, tag, cnt))
            print('  [FAIL ] %-46s %s (命中 %d)' % (name, tag, cnt))
            continue
        src = src.replace(old, new)
        print('  [OK   ] %-46s %s' % (name, tag))
    if nl != '\n':
        src = src.replace('\n', nl)
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(src)


# ───────────────────────── Core/RaidUI.lua ─────────────────────────
RA_HEADER_OLD = '''-- ★ 不做秒级倒计时（用户 2026-09-29 定）：官方开放时刻本身是按惯例推算的，
--   秒表会给出一个假精度，只写日期。'''

RA_HEADER_NEW = '''-- ★ 倒计时只到「分」（用户 2026-09-29 定）：官方开放时刻本身是按惯例推算的，
--   给到秒是假精度；RU.CountdownText(nowSec) 是纯函数（默认取 os.time()），
--   Build 里挂 1 秒 OnUpdate 重算，只在文本变化时才 SetText。
--   RU.DATA.unlockAt = 2026-12-09 13:00 PST 的 epoch（首批三座同日开启）。
--
-- ★★ 时间轴轴线两端都必须锚页面的 TOPLEFT：尾端若写成
--   `SetPoint("BOTTOMLEFT", page, "BOTTOMLEFT", x, -(y))`，BOTTOMLEFT 的 y 是自下缘
--   向上量，负值等于往页面**下方**画 —— 轴线会穿过底部注记、一路戳出窗口
--   （2026-09-29 实机截图实锤）。
--
-- ★ 「国服待确定」注记挂在「团本规则」里 禁止 GDKP 那行的描述右侧（用户 2026-09-29 定）。'''

RA_DATA_OLD = '''RU.DATA = {
    updated = "2026-09-24",'''

RA_DATA_NEW = '''RU.DATA = {
    updated = "2026-09-24",
    unlockAt = 1796850000,'''

RA_CD_OLD = '''local function SizeText(n)
    if type(n) == "number" then return format("%d%s", n, L["人"]) end
    return L["未公布"]
end'''

RA_CD_NEW = '''local function SizeText(n)
    if type(n) == "number" then return format("%d%s", n, L["人"]) end
    return L["未公布"]
end

function RU.CountdownText(nowSec)
    local remain = RU.DATA.unlockAt - (nowSec or os.time())
    if remain <= 0 then return L["已开启"] end
    local d = floor(remain / 86400)
    local h = floor(remain % 86400 / 3600)
    local m = floor(remain % 3600 / 60)
    return format(L["距首批开放还有 %d 天 %d 小时 %d 分"], d, h, m)
end

local function UpdateCD()
    if not RU.cd then return end
    local txt = RU.CountdownText()
    if RU.cdTxt ~= txt then
        RU.cdTxt = txt
        RU.cd:SetText(txt)
    end
end'''

RA_AXIS_OLD = '''    RU.axis:SetPoint("BOTTOMLEFT", RU.page, "BOTTOMLEFT", RU.X + RU.TL_AXIS, -(y - RU.TL_NODE_GAP))'''

RA_AXIS_NEW = '''    RU.axis:SetPoint("BOTTOMLEFT", RU.page, "TOPLEFT", RU.X + RU.TL_AXIS, -(y - RU.TL_NODE_GAP))'''

RA_RENDER_OLD = '''    RU.timeline:SetShown(tab == "timeline")
    RU.list:SetShown(tab == "list")'''

RA_RENDER_NEW = '''    RU.timeline:SetShown(tab == "timeline")
    RU.list:SetShown(tab == "list")
    UpdateCD()'''

RA_NOTE_OLD = '''    local note = MakeFS(page, 14, C_DIM, "LEFT")
    note:SetPoint("TOPLEFT", page, "TOPLEFT", RU.X + 2, -RU.NOTE_Y)
    note:SetText(L["首发即开放 10 / 20 / 40 人团本，2027 年的后续梯队已在排期"])'''

RA_NOTE_NEW = '''    local note = MakeFS(page, 14, C_DIM, "LEFT")
    note:SetPoint("TOPLEFT", page, "TOPLEFT", RU.X + 2, -RU.NOTE_Y)
    note:SetText(L["首发即开放 10 / 20 / 40 人团本，2027 年的后续梯队已在排期"])

    RU.cd = MakeFS(page, 14, C_GOLD, "RIGHT")
    RU.cd:SetPoint("TOPRIGHT", page, "TOPRIGHT", -(RU.X + 2), -RU.NOTE_Y)

    local tick = CreateFrame("Frame", nil, page)
    tick:SetScript("OnUpdate", function(_, elapsed)
        RU.cdAcc = (RU.cdAcc or 0) + elapsed
        if RU.cdAcc >= 1 then
            RU.cdAcc = 0
            UpdateCD()
        end
    end)'''

RA_RULES_OLD = '''    for i, rule in ipairs(RU.DATA.rules) do
        local rx = RU.X + 2 + ((i - 1) % 2) * RU.RULES_COL2
        local ry = RU.RULES_TOP + floor((i - 1) / 2) * RU.RULES_ROW_H
        local rn = MakeFS(ls, 14, C_TEXT, "LEFT")
        rn:SetPoint("TOPLEFT", page, "TOPLEFT", rx, -ry)
        rn:SetText(L[rule[1]])
        local rd = MakeFS(ls, 14, C_DIM, "LEFT")
        rd:SetPoint("TOPLEFT", page, "TOPLEFT", rx + RU.RULES_DESC_X, -ry)
        rd:SetText(L[rule[2]])
    end'''

RA_RULES_NEW = '''    local gdkpDesc
    for i, rule in ipairs(RU.DATA.rules) do
        local rx = RU.X + 2 + ((i - 1) % 2) * RU.RULES_COL2
        local ry = RU.RULES_TOP + floor((i - 1) / 2) * RU.RULES_ROW_H
        local rn = MakeFS(ls, 14, C_TEXT, "LEFT")
        rn:SetPoint("TOPLEFT", page, "TOPLEFT", rx, -ry)
        rn:SetText(L[rule[1]])
        local rd = MakeFS(ls, 14, C_DIM, "LEFT")
        rd:SetPoint("TOPLEFT", page, "TOPLEFT", rx + RU.RULES_DESC_X, -ry)
        rd:SetText(L[rule[2]])
        if rule[1] == "禁止 GDKP" then gdkpDesc = rd end
    end
    if gdkpDesc then
        RU.cnNote = MakeFS(ls, 14, C_GREY, "LEFT")
        RU.cnNote:SetPoint("LEFT", gdkpDesc, "RIGHT", 14, 0)
        RU.cnNote:SetText(L["国服待确定"])
    end'''

RAIDUI = [
    ('header: 倒计时/轴线/国服 口径', RA_HEADER_OLD, RA_HEADER_NEW),
    ('DATA.unlockAt', RA_DATA_OLD, RA_DATA_NEW),
    ('RU.CountdownText + UpdateCD', RA_CD_OLD, RA_CD_NEW),
    ('轴线尾端锚回 TOPLEFT', RA_AXIS_OLD, RA_AXIS_NEW),
    ('Render 里重算倒计时', RA_RENDER_OLD, RA_RENDER_NEW),
    ('Build: 倒计时帧 + 1 秒 OnUpdate', RA_NOTE_OLD, RA_NOTE_NEW),
    ('Build: 国服待确定 注释', RA_RULES_OLD, RA_RULES_NEW),
]

# ───────────────────────── harness（两份同源）─────────────────────────
H_STATIC_OLD = """    ck('★★ RaidUI 不做秒级倒计时（无 OnUpdate / 无 unlockAt，只写日期）',
       'OnUpdate' not in _ra and 'unlockAt' not in _ra)"""

H_STATIC_NEW = """    ck('★★ RaidUI 倒计时到「分」（纯函数 RU.CountdownText，默认 os.time()）',
       'function RU.CountdownText(nowSec)' in _ra
       and 'RU.DATA.unlockAt - (nowSec or os.time())' in _ra)
    ck('★★ RaidUI 倒计时不给秒（格式串只有 天/小时/分）',
       '距首批开放还有 %d 天 %d 小时 %d 分' in _ra and '%d 秒' not in _ra)
    ck('★★ RaidUI 时间轴轴线两端都锚页面 TOPLEFT（BOTTOMLEFT+负偏移会戳出窗口）',
       'RU.axis:SetPoint("BOTTOMLEFT", RU.page, "TOPLEFT"' in _ra
       and 'RU.axis:SetPoint("BOTTOMLEFT", RU.page, "BOTTOMLEFT"' not in _ra)
    ck('★★ 「国服待确定」注记挂 禁止 GDKP 行描述右侧',
       'L["国服待确定"]' in _ra
       and 'RU.cnNote:SetPoint("LEFT", gdkpDesc, "RIGHT", 14, 0)' in _ra)"""

H_RT_OLD = """        ck("★★ 卡墙整体不压到底部「团本规则」块", _ps.bottom < RM.RULES_RULE_Y,
           tostring(_ps.bottom) .. " < " .. tostring(RM.RULES_RULE_Y))
      end"""

H_RT_NEW = """        ck("★★ 卡墙整体不压到底部「团本规则」块", _ps.bottom < RM.RULES_RULE_Y,
           tostring(_ps.bottom) .. " < " .. tostring(RM.RULES_RULE_Y))
      end

      -- ★★ 倒计时（纯函数：喂定点 nowSec 即可复现）/ 国服待确定注记（2026-09-29 补）
      do
        local _tgt = RM.DATA.unlockAt
        ck("★★ 倒计时锚点 = 首批开放时刻 2026-12-09 13:00 PST",
           _tgt == 1796850000, _tgt)
        ck("★★ 倒计时到「分」：剩 1 天 1 小时 1 分",
           RM.CountdownText(_tgt - (86400 + 3600 + 60)) == "距首批开放还有 1 天 1 小时 1 分",
           RM.CountdownText(_tgt - (86400 + 3600 + 60)))
        ck("★★ 倒计时跨过开放时刻即显示「已开启」",
           RM.CountdownText(_tgt + 10) == "已开启", RM.CountdownText(_tgt + 10))
        ck("★★ 「国服待确定」注记已建且文案正确",
           RM.cnNote ~= nil and tostring(RM.cnNote.__text) == "国服待确定",
           RM.cnNote and tostring(RM.cnNote.__text))
      end"""

HARNESS = [
    ('静态：倒计时/轴线/国服 四条', H_STATIC_OLD, H_STATIC_NEW),
    ('运行时：倒计时 + 国服注释', H_RT_OLD, H_RT_NEW),
]

print('== Core/RaidUI.lua ==')
patch(os.path.join('Core', 'RaidUI.lua'), RAIDUI)

for hname in ('df_dungeon_check.py', 'mk_df_check.py'):
    print('== _temp/%s ==' % hname)
    patch(os.path.join('_temp', hname), HARNESS)

for f in (os.path.join(ROOT, '_temp', 'df_dungeon_check.py'),
          os.path.join(ROOT, '_temp', 'mk_df_check.py')):
    py_compile.compile(f, doraise=True)
print('\npy_compile OK（2 份 harness）')

if FAIL:
    print('\n!! 有旧串未命中：')
    for x in FAIL:
        print('   ' + x)
    sys.exit(1)
print('全部补丁就位。')

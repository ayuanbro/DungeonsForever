# -*- coding: utf-8 -*-
"""专业页：大列表分帧 + 主界面顶部进度条（2026-10-09）。

背景：配方页「全部」最多 300 条，原来在渲染那一帧里同步 CreateFrame 出全部行帧
      —— 一帧几百个对象，弱机器上主线程一次堵上百毫秒（用户：进度条）。
做法：与副本掉落页**同一套**（DG.Gate 进度条 + DG.PushStep/DG.RunSteps 分帧器 +
      DG.Loader 每帧预算 + DG.LOOT_ROW_FRAME_CAP 数量闸），只是行池/版式是专业页自己的。

幂等：锚点命中数 != 1 就中止；已打过则 SKIP。
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
TARGET = os.path.join(DF, 'Core', 'ProfessionUI.lua')

def load(p):
    raw = open(p, 'rb').read()
    crlf = raw.count(b'\r\n') > 0
    txt = raw.decode('utf-8')
    if crlf:
        assert txt.count('\r\n') == raw.count(b'\n'), 'CRLF 行尾不整齐'
        return txt.replace('\r\n', '\n'), True
    return txt, False

def save(p, txt, crlf):
    out = txt.replace('\n', '\r\n') if crlf else txt
    data = out.encode('utf-8')
    if crlf:
        assert data.count(b'\n') == data.count(b'\r\n'), '落盘会混进裸 LF'
    open(p, 'wb').write(data)

# ── 各段补丁：(标签, old, new) ───────────────────────────────────────────
PATCHES = []

# ① 文件头纪律说明：补一条「生长 = 分帧 + 顶部进度条」
PATCHES.append(('head-note', '''--   · 行池按需生长（沿副本页做法），但设 PD.ROW_CAP 封顶，并在封顶处明说「还有 N 条」——
--     宁可提示用分类缩小范围，也不让一次「全部」把帧数顶到几千（最大 512 条）。
''', '''--   · 行池按需生长（沿副本页做法），但设 PD.ROW_CAP 封顶，并在封顶处明说「还有 N 条」——
--     宁可提示用分类缩小范围，也不让一次「全部」把帧数顶到几千（最大 512 条）。
--   · ★★ 行池「生长」自 2026-10-09 起走**分帧 + 主界面顶部进度条**（与副本掉落页
--     同一套家伙：进度条 / 分帧器 / 每帧预算都复用 DG 那边的）：渲染只算版式，
--     行帧记进待建表逐批建 —— 大页最多 300 条，不再把几百个对象砸在「点开」那一帧上。
--     量小走快速通道（不闪进度条）。
'''))

# ② 常量区：待建表 + 同步阈值
PATCHES.append(('queue-const', '''PD.rows, PD.toolBtns = {}, {}
PD.specs = nil
''', '''PD.rows, PD.toolBtns = {}, {}
PD.specs = nil

-- ★★ 大列表分帧 + 顶部进度条：渲染只算版式，把「还没建的行」记进 PD.__pendRows，
--   随后按每帧预算逐批建。进度分母入队时就算好、只增不减；进度条复用主界面
--   最顶上那根。少于 PD.ROW_SYNC_MAX 行直接同步建完（闪一下比不闪更难受）。
PD.__pendRows = {}
PD.ROW_SYNC_MAX = 20
'''))

# ③ 三个函数：插在 PD.PaintRows 之前
PATCHES.append(('funcs', '''function PD.PaintRows(rows)
''', '''-- 单个待建行：建帧 + 摆位 + 上数据（行帧已在池里则跳过）。
-- ★ 间距行（kind == "gap"）也进待建表：行池按索引取用，跳号会在池里留空洞，
--   「末尾多余的隐藏一下」那条就数不准了；建出来立刻 Hide，与同步路径同观感。
function PD.RealizePendingRow(e)
    if not e then return end
    local r = PD.rows[e.idx]
    if not r then
        local ok, made = pcall(PD.Row, e.idx)
        if not ok or not made then return end
        r = made
    end
    if e.gap then
        r:Hide()
        return
    end
    r:ClearAllPoints()
    r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", e.x, -e.top)
    r:SetSize(e.w, e.h)
    r:Show()
    PD.BindRow(r, e.spec, e.h)
end

-- 逐批建（每帧受载入档位的时间预算 + 单块数量闸夹住；与掉落页同一套闸）。
function PD.BuildPendRows()
    local list = PD.__pendRows
    if not list then
        PD.__pendRows = {}
        DG.Gate.Finish()
        return
    end
    local t0 = DG.__nowMs()
    local left = DG.LOOT_ROW_FRAME_CAP
    while #list > 0 and left > 0 do
        PD.RealizePendingRow(table.remove(list, 1))
        DG.Gate.Advance(1)
        left = left - 1
        local t1 = t0 and DG.__nowMs()
        if t1 and (t1 - t0) >= DG.Loader.budgetMs then break end
    end
    if #list > 0 then
        DG.PushStep(PD.BuildPendRows)
    else
        DG.Gate.Finish()
        if PD.DEMO_SAVE then PD.EndGateDemo() end
    end
end

-- 渲染收尾入口：量小同步建完（快速通道，不闪进度条）；量大交分帧器 + 进度条。
-- ★ 离线桩 / 没有可用 C_Timer 的环境由 DG.RunSteps 递归同步跑完 ——
--   「调用方返回时一切就绪」这条离线契约不破。
function PD.FlushPendingRows()
    local n = #PD.__pendRows
    if n == 0 then
        DG.Gate.Finish()
        return
    end
    if n < PD.ROW_SYNC_MAX then
        for k = 1, n do PD.RealizePendingRow(PD.__pendRows[k]) end
        PD.__pendRows = {}
        DG.Gate.Finish()
        if PD.DEMO_SAVE then PD.EndGateDemo() end
        return
    end
    DG.Gate.Begin(n)
    DG.PushStep(PD.BuildPendRows)
    DG.RunSteps()
end

function PD.PaintRows(rows)
'''))

# ④ PaintRows：取帧从「当场建」改成「池里有就用，没有记进待建表」
PATCHES.append(('grab', '''        local h = PD.RowHeight(spec)
        local r = PD.Row(i)
''', '''        local h = PD.RowHeight(spec)
        local r = PD.rows[i]
'''))

PATCHES.append(('gap', '''        if spec.kind == "gap" then
            r:Hide()
            if span then
''', '''        if spec.kind == "gap" then
            if r then
                r:Hide()
            else
                PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true }
            end
            if span then
'''))

PATCHES.append(('row', '''            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", x, -top)
            r:SetSize(w, h)
            r:Show()
            if spec.kind == "row" and col and not spec.sec then
                zc[col] = zc[col] + 1
                spec.z = (zc[col] % 2 == 0)
            else
                spec.z = nil
            end
            PD.BindRow(r, spec, h)
''', '''            if spec.kind == "row" and col and not spec.sec then
                zc[col] = zc[col] + 1
                spec.z = (zc[col] % 2 == 0)
            else
                spec.z = nil
            end
            if r then
                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", x, -top)
                r:SetSize(w, h)
                r:Show()
                PD.BindRow(r, spec, h)
            else
                PD.__pendRows[#PD.__pendRows + 1] =
                    { idx = i, spec = spec, x = x, w = w, top = top, h = h }
            end
'''))

# ⑤ PaintRows 收尾：交分帧器
PATCHES.append(('flush', '''    PD.child:SetHeight(math.max(h1, y[2]) + 10)
    return truncated
end
''', '''    PD.child:SetHeight(math.max(h1, y[2]) + 10)
    PD.FlushPendingRows()
    return truncated
end
'''))

# ⑥ Render：每轮开头丢掉上一轮排下、还没建的行
PATCHES.append(('render-reset', '''    PD.hideDivider = false
    PD.secCount = 0
''', '''    PD.hideDivider = false
    PD.secCount = 0
    -- ★ 上一轮排下、还没建的行必须丢掉（玩家已经点到别的专业 / 别的子页签了），
    --   否则它们会在新页面上冒出来。
    PD.__pendRows = {}
'''))

# ⑦ 设置页开关：行帧可能还没建出来，别对 nil 取层级
PATCHES.append(('toggles', '''        if PD.setOpen and spec.togKey then
            ti = ti + 1
            local tg = PD.setToggles[ti]
            tg:ClearAllPoints()
            tg:SetPoint("RIGHT", PD.rows[i], "RIGHT", -8, 0)
            tg:SetFrameLevel((PD.rows[i]:GetFrameLevel() or 0) + 10)
            tg:SetChecked(PD.Setting(spec.togKey))
            tg.__key = spec.togKey
            tg:Show()
        end
''', '''        local rr = PD.rows[i]
        if PD.setOpen and spec.togKey and rr then
            ti = ti + 1
            local tg = PD.setToggles[ti]
            tg:ClearAllPoints()
            tg:SetPoint("RIGHT", rr, "RIGHT", -8, 0)
            tg:SetFrameLevel((rr:GetFrameLevel() or 0) + 10)
            tg:SetChecked(PD.Setting(spec.togKey))
            tg.__key = spec.togKey
            tg:Show()
        end
'''))

# ⑧ 文件尾：进度条自检 / 演示
PATCHES.append(('demo', '''function PD.Refresh()
    if not PD.built then return end
    if not PD.cur then PD.cur = "__index" end
    PD.Render()
end
''', '''function PD.Refresh()
    if not PD.built then return end
    if not PD.cur then PD.cur = "__index" end
    PD.Render()
end

-- ══ 进度条自检 / 演示（/dfprofgate） ═══════════════════════════════════
--   ★ 为什么需要这个命令：行池只增不减 —— 同一个专业第二次打开就是复用已经建好的
--     行帧（真·瞬时，本就不该亮条）。只有「第一次把池子撑大的那个专业」看得见它，
--     好机器上几乎一闪而过 ⇒ 留一条能随时复现的入口（与 /dfgate 同款）。
--   ★ 演示做法：把三道闸临时放宽到「必定触发」（多小都亮 / 一律分帧 / 每帧只建 2 行），
--     再清空行池重新渲染一次 ⇒ 当前专业就把进度条走完一遍。
--     收工由 PD.EndGateDemo 统一还原（队列抽干是唯一可靠的「活干完了」信号）。
PD.DEMO_SAVE = nil

function PD.StartGateDemo()
    if PD.DEMO_SAVE then PD.EndGateDemo() end
    PD.DEMO_SAVE = {
        syncMax  = PD.ROW_SYNC_MAX,
        minSteps = DG.Gate.minSteps,
        rowCap   = DG.LOOT_ROW_FRAME_CAP,
    }
    PD.ROW_SYNC_MAX       = 0     -- 一律走分帧（正式值 20）
    DG.Gate.minSteps      = 0     -- 多小都亮（正式值 24）
    DG.LOOT_ROW_FRAME_CAP = 2     -- 每帧只建 2 行 ⇒ 才看得清（正式值 16）
    -- 清空行池：池子只增不减，不清的话「复用已有行帧」会让待建表为空 ⇒ 进度条照旧不亮
    for i = #PD.rows, 1, -1 do PD.rows[i]:Hide() end
    PD.rows = {}
    PD.Render()
end

function PD.EndGateDemo()
    local s = PD.DEMO_SAVE
    PD.DEMO_SAVE = nil
    if not s then return end
    PD.ROW_SYNC_MAX       = s.syncMax
    DG.Gate.minSteps      = s.minSteps
    DG.LOOT_ROW_FRAME_CAP = s.rowCap
end

if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERPROFGATE1 = "/dfprofgate"
    SlashCmdList["DUNGEONSFOREVERPROFGATE"] = function()
        if PD.DEMO_SAVE then
            PD.EndGateDemo()
            print("|cff46bf72[无限副本手册]|r " .. L["已还原。"])
            return
        end
        if not PD.built or not PD.cur then
            print("|cff46bf72[无限副本手册]|r "
                  .. L["先打开一个专业的配方页，再运行这个命令。"])
            return
        end
        PD.StartGateDemo()
        print("|cff46bf72[无限副本手册]|r "
              .. L["演示：每帧只建 2 行，进度条会走完一遍。"])
    end
end
'''))


def main():
    check = '--check' in sys.argv
    txt, crlf = load(TARGET)
    print('目标 %s（换行 %s）' % (TARGET, 'CRLF' if crlf else 'LF'))
    ok = True
    for tag, old, new in PATCHES:
        n = txt.count(old)
        if n == 1:
            print('  [OK ] %-14s 命中 1 次' % tag)
            if not check:
                txt = txt.replace(old, new, 1)
        elif txt.count(new) == 1:
            print('  [SKIP] %-14s 已打过（new 已存在）' % tag)
        else:
            print('  [BAD] %-14s 锚点命中 %d 次（要求恰好 1 次）' % (tag, n))
            ok = False
    if not ok:
        print('锚点不齐，未落盘。')
        return 2
    if check:
        print('（--check：未写盘）')
        return 0
    save(TARGET, txt, crlf)
    print('已写盘。')
    return 0


if __name__ == '__main__':
    sys.exit(main())

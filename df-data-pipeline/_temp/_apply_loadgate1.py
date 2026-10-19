# -*- coding: utf-8 -*-
"""第五刀 · 第一段：DG.Loader（每帧预算调度器）+ DG.Gate（载入进度条）。

改 Core/DungeonUI.lua（CRLF 手写件）：
  ① DG.RunSteps 的 pump 加「时间闸 + 数量闸」，任务可主动让出（返回真值）
  ② 派生前插入 DG.Loader / DG.Gate / /dfspeed
  ③ U:Build 里读一次档（DG.Loader.Init）

用法：python _apply_loadgate1.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(DF, 'Core', 'DungeonUI.lua')
BAK = os.path.join(HERE, '_bak_DungeonUI_loadgate.lua.bak')

raw = io.open(SRC, 'rb').read()
txt = raw.decode('utf-8')
style = '\r\n' if '\r\n' in txt else '\n'
flat = txt.replace('\r\n', '\n')

if not os.path.isfile(BAK):
    io.open(BAK, 'wb').write(raw)
    print('备份 ->', BAK)


def rep(old, new, tag):
    global flat
    n = flat.count(old)
    if n != 1:
        print('!! [%s] 锚点命中 %d 次（应为 1）' % (tag, n))
        sys.exit(1)
    flat = flat.replace(old, new, 1)
    print('OK  [%s]' % tag)


# ── ① pump 加预算闸 ──────────────────────────────────────────────────────
rep(
    '''    local function pump()
        local fn = table.remove(DG.pendingSteps, 1)
        if not fn then
            DG.stepping = false
            return
        end
        local ok, err = pcall(fn)
        if not ok then
            print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(err))
        end
''',
    '''    local function pump()
        -- ★★★ 第五刀：每帧预算（见 DG.Loader）—— 时间闸 + 数量闸，任一触发即停手。
        --   任务若返回真值 = 「本帧让出」（放回队首，下一帧接着来）。
        local t0 = DG.__nowMs()
        local n = 0
        while true do
            local fn = table.remove(DG.pendingSteps, 1)
            if not fn then
                DG.stepping = false
                return
            end
            local ok, res = pcall(fn)
            if not ok then
                print("|cffff5040[无限副本手册] 分帧构建出错（已跳过该块）：|r" .. tostring(res))
                res = nil
            end
            if res then
                table.insert(DG.pendingSteps, 1, fn)
                break
            end
            n = n + 1
            if n >= DG.Loader.budgetObj then break end
            local t1 = t0 and DG.__nowMs()
            if t1 and (t1 - t0) >= DG.Loader.budgetMs then break end
        end
''',
    'pump 预算闸')

# ── ② 插入 DG.Loader / DG.Gate / /dfspeed ────────────────────────────────
LOADER = '''-- ══════════════════════════════════════════════════════════════════════════
-- ★★★ 第五刀 · 统一分帧调度器 DG.Loader（2026-10-03「有些用户电脑很差」）
--   ──────────────────────────────────────────────────────────────────────
--   前四刀解决的是「哪一帧付哪笔钱」，但**单帧里到底建多少**一直没有上限：
--   黑石深渊点副本那一帧要建 249 个对象（详情外壳 + 168 个掉落行帧）—— 好机器
--   只是打个顿，差电脑主线程一次阻塞上百毫秒 ⇒ Windows 判定无响应、整窗涂灰。
--
--   DG.Loader 给每一帧加两道闸，任一触发就立刻停手、剩下的排到下一帧：
--     · 时间闸 debugprofilestop：**真机自适应** —— 好机器一帧多跑几个、差机器
--       一帧少跑几个。这正是「有些用户电脑很差」的正解：不必猜用户配置，也不必
--       让所有人陪跑最慢的节奏。
--     · 数量闸 budgetObj：计时口不可用 / 计时异常时的兜底，防一帧失控。
--
--   ★★ 单位必须是**毫秒，不是个数**：一个空 frame 约 0.05ms，而一次首次贴图
--      加载能到 2ms —— 差 20 倍以上。按「个数」分帧，碰上重对象照样卡死。
--   ★★ 同步兜底不破：C_Timer 不可用（离线 harness / 极端环境）时 pump 一路跑到底，
--      「调用方返回时一切就绪」这条契约不变 ⇒ 全部离线断言不受影响。
-- ══════════════════════════════════════════════════════════════════════════
DG.Loader = {
    budgetMs  = 4,      -- 每帧时间预算（ms）
    budgetObj = 96,     -- 每帧对象预算（兜底）
    preset    = "normal",
}
DG.LOADER_PRESETS = { eco = 2, normal = 4, turbo = 8 }
DG.LOADER_LABEL = { eco = L["省电"], normal = L["标准"], turbo = L["激进"] }

function DG.Loader.SetBudget(k)
    local v = DG.LOADER_PRESETS[k]
    if type(v) ~= "number" then return false end
    DG.Loader.budgetMs = v
    DG.Loader.preset = k
    DB().loadBudget = (k ~= "normal") and k or nil
    return true
end

-- 读档（幂等；U:Build 里调一次）
function DG.Loader.Init()
    local k = DB().loadBudget
    if DG.LOADER_PRESETS[k] then
        DG.Loader.budgetMs = DG.LOADER_PRESETS[k]
        DG.Loader.preset = k
    else
        DG.Loader.preset = "normal"
        DG.Loader.budgetMs = DG.LOADER_PRESETS.normal
    end
end

-- 计时口：真机 debugprofilestop 返毫秒；离线 / 极端环境没有它 ⇒ 只靠数量闸。
function DG.__nowMs()
    local f = debugprofilestop
    if type(f) == "function" then
        local ok, v = pcall(f)
        if ok and type(v) == "number" then return v end
    end
    return nil
end

-- ══ 载入进度条 ═══════════════════════════════════════════════════════════
--   ★ 用户 2026-10-03 拍板「顶部细条（像浏览器加载）」：**不遮内容** ——
--     骨架和已经建好的部分都能看见。所以这里没有遮罩，只有两样东西：
--       · 内容区上缘 3px 的细进度条；满进度即时消失。
--       · 内容区右下角一枚状态胶囊（「正在载入… NN%」+「跳过」）。
--     胶囊落右下角而不是右上：顶部那两排挤着页签 / 筛选 / 视图按钮，浮在那里
--     会压住可点控件（本插件版式最密的区域）。
--   ★ 跳过 = **只撤进度条，剩下的继续在后台分帧建** —— 不走「一次啃完」那条路
--     （那就等于把卡死还回来），也不丢数据（列表随后自己补齐）。
-- ══════════════════════════════════════════════════════════════════════════
DG.Gate = { on = false, total = 0, done = 0, minSteps = 24, skipped = false, w = CONTENT_W }

function DG.Gate.Ensure()
    if DG.Gate.bar then return true end
    local panel = U.panel or (U.dungeonPage and U.dungeonPage:GetParent())
    if not panel then return false end
    local bar = CreateFrame("Frame", nil, panel)
    bar:SetFrameLevel(panel:GetFrameLevel() + 20)
    bar:SetPoint("TOPLEFT", panel, "TOPLEFT", 0, 0)
    bar:SetPoint("TOPRIGHT", panel, "TOPRIGHT", 0, 0)
    bar:SetHeight(3)
    bar.bg = bar:CreateTexture(nil, "BACKGROUND")
    bar.bg:SetAllPoints()
    bar.bg:SetColorTexture(0, 0, 0, 0.45)
    bar.fill = bar:CreateTexture(nil, "ARTWORK")
    bar.fill:SetPoint("TOPLEFT", bar, "TOPLEFT", 0, 0)
    bar.fill:SetPoint("BOTTOMLEFT", bar, "BOTTOMLEFT", 0, 0)
    bar.fill:SetWidth(1)
    bar.fill:SetColorTexture(Unpack(C_GOLD))
    bar:Hide()
    DG.Gate.bar = bar

    local pill = CreateFrame("Frame", nil, panel, "BackdropTemplate")
    pill:SetFrameLevel(panel:GetFrameLevel() + 21)
    pill:SetSize(186, 26)
    pill:SetPoint("BOTTOMRIGHT", panel, "BOTTOMRIGHT", -10, 10)
    pill:SetBackdrop({
        bgFile = "Interface\\\\Buttons\\\\WHITE8x8",
        edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",
        edgeSize = 1,
    })
    pill:SetBackdropColor(0, 0, 0, 0.72)
    pill:SetBackdropBorderColor(1, 0.82, 0, 0.45)
    pill.text = MakeFS(pill, 12, C_TEXT, "LEFT")
    pill.text:SetPoint("LEFT", pill, "LEFT", 10, 0)
    do
        local sk = CreateFrame("Button", nil, pill)
        sk:SetSize(48, 18)
        sk:SetPoint("RIGHT", pill, "RIGHT", -5, 0)
        local sl = MakeFS(sk, 12, C_GOLD, "CENTER")
        sl:SetPoint("CENTER", sk, "CENTER", 0, 0)
        sl:SetText(L["跳过"])
        sk:SetScript("OnClick", function() DG.Gate.Skip() end)
        pill.skip = sk
    end
    pill:Hide()
    DG.Gate.pill = pill
    return true
end

function DG.Gate.Paint()
    local bar, pill = DG.Gate.bar, DG.Gate.pill
    local total = DG.Gate.total
    local pct = 0
    if total > 0 then pct = math.floor(DG.Gate.done / total * 100 + 0.5) end
    if pct < 0 then pct = 0 elseif pct > 100 then pct = 100 end
    if bar then
        bar.fill:SetWidth(math.max(1, math.floor(DG.Gate.w * pct / 100)))
    end
    if pill and pill.text then
        pill.text:SetText(L["正在载入…"] .. " " .. pct .. "%")
    end
end

function DG.Gate.HideUI()
    if DG.Gate.bar then DG.Gate.bar:Hide() end
    if DG.Gate.pill then DG.Gate.pill:Hide() end
end

-- 进度分母**入队时就算好**、只增不减；量太小则走快速通道（不闪进度条）。
function DG.Gate.Begin(n)
    DG.Gate.total = n or 0
    DG.Gate.done = 0
    DG.Gate.skipped = false
    if DG.Gate.total < DG.Gate.minSteps then return end
    DG.Gate.on = true
    if DG.Gate.Ensure() then
        DG.Gate.bar:Show()
        DG.Gate.pill:Show()
    end
    DG.Gate.Paint()
end

function DG.Gate.Advance(k)
    DG.Gate.done = DG.Gate.done + (k or 1)
    if DG.Gate.on then DG.Gate.Paint() end
end

function DG.Gate.Skip()
    DG.Gate.skipped = true
    DG.Gate.on = false
    DG.Gate.HideUI()
end

function DG.Gate.Finish()
    DG.Gate.done = DG.Gate.total
    DG.Gate.on = false
    DG.Gate.HideUI()
end

-- 载入速度档位：省电 2ms / 标准 4ms / 激进 8ms（默认标准）。
-- ★ 三档的单帧耗时都远低于卡顿阈值（Windows 约 200ms 才判无响应）——
--   档位只决定「总时长」，不决定「会不会卡」。
if type(SlashCmdList) == "table" then
    SLASH_DUNGEONSFOREVERSPEED1 = "/dfspeed"
    SlashCmdList["DUNGEONSFOREVERSPEED"] = function(msg)
        local k = tostring(msg or ""):lower():gsub("%s+", "")
        if DG.LOADER_PRESETS[k] then
            DG.Loader.SetBudget(k)
            print("|cff46bf72[无限副本手册]|r " .. L["载入速度"] .. " = "
                  .. (DG.LOADER_LABEL[k] or k) .. "（" .. DG.LOADER_PRESETS[k] .. "ms/帧）")
            return
        end
        print("|cff46bf72[无限副本手册]|r " .. L["载入速度"] .. "："
              .. L["省电"] .. " / " .. L["标准"] .. " / " .. L["激进"]
              .. "（" .. L["当前"] .. " = " .. (DG.LOADER_LABEL[DG.Loader.preset] or "standard") .. "）")
    end
end

-- ★ 行池「待建表」：渲染时算好版式、把还没建的行帧记在这里，随后按每帧预算逐批建。
--   ★ 每轮渲染开头**整体重置** —— 上一轮排下但还没建的行（比如玩家已经点到别的副本）
--     必须丢掉，否则它们会在新页面上冒出来。
DG.__pendRows = {}

'''
rep('DG.pendingSteps = {}\nDG.stepping = false\nfunction DG.PushStep(fn)',
    LOADER + 'DG.pendingSteps = {}\nDG.stepping = false\nfunction DG.PushStep(fn)',
    'DG.Loader + DG.Gate')

# ── ③ U:Build 里读一次档 ──────────────────────────────────────────────────
rep('''    U.building = true

    local saved = DB().subTab''',
    '''    U.building = true
    DG.Loader.Init()          -- ★ 载入速度档位（/dfspeed），默认标准 4ms

    local saved = DB().subTab''',
    'U:Build 读档')
# ─────────────────────────────────────────────────────────────────────────
out = flat.replace('\n', style)
io.open(SRC, 'wb').write(out.encode('utf-8'))
crlf = out.count('\r\n')
print('字节 %d，CRLF %d，裸 LF %d' % (len(out.encode('utf-8')), crlf, out.count('\n') - crlf))
assert '\r\n' not in out.replace('\r\n', '', out.count('\r\n')) or True
assert out.count('\n') - crlf == 0, '有裸 LF'
print('完成')

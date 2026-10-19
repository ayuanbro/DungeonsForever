# -*- coding: utf-8 -*-
"""快捷按钮栏（右侧第二条吸附栏）· 一次性落盘脚本。

在源侧树就地打补丁（不新增生成器；改完用 sync_beta.py --apply 推 beta）：
  1. Core/QuickBar.lua      新建（LF）
  2. Core/Core.lua          加 ns.QuickCfg / 默认表（LF）
  3. Core/DungeonUI.lua     加 ns.ShowDungeonDetail（CRLF，逐字节替换保行尾）
  4. Core/ExploreUI.lua     加 EG.ShowSub（LF）
  5. Core/MainFrame.lua     导出 ns.SettingsPopup + 开设置时同步快捷栏（LF）
  6. DungeonsForever.toc    追加 Core\\QuickBar.lua

幂等：重复运行会因锚点 count != 1 而报错退出，不会写坏文件。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _norm(s):
    return s.replace('\r\n', '\n')


def enc(s, crlf):
    return _norm(s).replace('\n', '\r\n' if crlf else '\n').encode('utf-8')


def is_crlf(b):
    return b'\r\n' in b


def patch(rel, pairs):
    p = os.path.join(ROOT, *rel.split('/'))
    with open(p, 'rb') as f:
        data = f.read()
    crlf = is_crlf(data)
    for old, new in pairs:
        ob = enc(old, crlf)
        nb = enc(new, crlf)
        n = data.count(ob)
        if n != 1:
            print('!! 锚点命中 %d 次（应为 1）: %s' % (n, rel))
            return False
        data = data.replace(ob, nb, 1)
    with open(p, 'wb') as f:
        f.write(data)
    print('  已改 %-26s CRLF=%-6d 裸LF=%-6d' % (rel, data.count(b'\r\n'),
                                              data.count(b'\n') - data.count(b'\r\n')))
    return True


# ---------------------------------------------------------------- QuickBar.lua
QB_LUA = '''-- =============================================================================
-- DungeonsForever · 主窗口右侧「快捷按钮栏」
--
--   贴主窗右缘的第二条吸附栏（与「设置」/「装备过滤」槽位并存、互不挤占）：
--     · 推荐五人本 —— 按玩家等级实时算（沿用副本页 DG.GroupOf 的 rec 桶），
--                     点条目直接进该副本详情
--     · 专业       —— 列表口径由设置决定：只看已学 / 全部
--     · 探索       —— 显示哪几个子页由设置里的多选决定
--   总开关与各分组开关存 DungeonsForeverDB.ui.quick（读写都走 Core.lua 的 ns.QuickCfg）。
--
--   约束：字号仅 11 / 14 / 16；面板宽 100（左右内边距 8 → 内容宽 84）；
--         父级 = 主窗口（随窗显隐、继承缩放）；条目名超宽走**换行**而不是截断
--         （「血色修道院：…」这一族名字前缀相同，截断后互相认不出来）；
--         本文件只挂 QB.* 与 ns.*，不定义裸全局函数。
--
--   ★ 本文件不是生成物，是手写件，直接改本文件即可。
-- =============================================================================

local _, ns = ...

if not ns.IsTitan then return end

local L = ns.L

local QB = {}
ns.QuickBar = QB

-- 几何 -----------------------------------------------------------------------
QB.W = 100                     -- 面板宽
QB.SLOT2 = 236                 -- 第二槽左缘 = 设置槽 220 + 间距 8 + 再留 8
QB.PAD = 8                     -- 左右内边距
QB.CW = QB.W - QB.PAD * 2      -- 内容宽 84
QB.TEXT_PAD = 4                -- 条目内文本左缩进
QB.FS_HEAD, QB.FS_NAME, QB.FS_AUX = 16, 14, 11
QB.HEAD_Y, QB.BODY_Y = -10, -36
QB.GRP_H, QB.GAP = 20, 3

local C_WHITE = { 1, 1, 1 }
local C_TEXT  = { 0.88, 0.88, 0.88 }
local C_DIM   = { 0.62, 0.62, 0.62 }
local C_GOLD  = { 1, 0.82, 0 }
local C_AUX   = { 0.55, 0.62, 0.70 }

local strbyte, strsub, format = string.byte, string.sub, format or string.format

-- 探索子页：键与 Core/ExploreUI.lua 的 CurSub 口径一致；栏内用短标签。
local EXPLORE_DEFS = {
    { key = "books",   text = L["40本书"] },
    { key = "rewards", text = L["奖励总览"] },
    { key = "bag",     text = L["睡袋"] },
    { key = "bm",      text = L["战斗法师"] },
}

local function Accent()
    local a = ns.hui and ns.hui.ACCENT
    if a then return a[1], a[2], a[3] end
    return 0x46 / 255, 0xbf / 255, 0x72 / 255
end

local function Fs(parent, size, color)
    local fs = parent:CreateFontString(nil, "OVERLAY")
    fs:SetFont(ns.FONT, size, "")
    if color then fs:SetTextColor(color[1], color[2], color[3]) end
    return fs
end

local function Outline(bt, on)
    local H = ns.ProfHost
    if not (H and H.SetOutline) then return end
    H.SetOutline(bt, on, 1, 0.82, 0)
end

-- UTF-8 按「字」切 —— 按字节切会切出半个汉字。
local function Chars(s)
    local out, i, n = {}, 1, #s
    while i <= n do
        local b = strbyte(s, i) or 0
        local len = 1
        if b >= 0xF0 then len = 4
        elseif b >= 0xE0 then len = 3
        elseif b >= 0xC0 then len = 2 end
        out[#out + 1] = strsub(s, i, i + len - 1)
        i = i + len
    end
    return out
end

-- 估宽：CJK ≈ 字号、其余 ≈ 0.55 字号。只用来决定条目名占 1 行还是 2 行，
-- 估偏只是行高多一档，不影响可读性。
local function EstW(text, size)
    local w = 0
    for _, ch in ipairs(Chars(text)) do
        local b = strbyte(ch, 1) or 0
        if b >= 0xE0 then w = w + size
        elseif b >= 0xC0 then w = w + size * 0.9
        else w = w + size * 0.55 end
    end
    return w
end

local NAME_W = QB.CW - QB.TEXT_PAD * 2

local function RowH(name, hasAux)
    local h = (EstW(name, QB.FS_NAME) > NAME_W) and 32 or 18
    if hasAux then h = h + 13 end
    return h + 6
end

local function PlayerLevel()
    if type(UnitLevel) ~= "function" then return 0 end
    return UnitLevel("player") or 0
end

local function DungeonRow(d)
    return {
        text = d.name,
        aux = format("%d-%d", d.levelMin or 0, d.levelMax or 0),
        tip = d.name .. "  " .. (d.nameEn or "") .. "\\n"
            .. format(L["等级 %d-%d"], d.levelMin or 0, d.levelMax or 0)
            .. " · " .. (d.zone or L["位置未知"]),
        act = "dungeon",
        id = d.id,
    }
end

-- 条目清单：三个分组按「分组头 + 条目」铺平；关掉的分组整段不产出。
function QB:Collect()
    local cfg = ns.QuickCfg()
    local DG = ns.ProfHost and ns.ProfHost.DG
    local out = {}
    local n = { dungeon = 0, prof = 0, explore = 0 }

    if cfg.groups.dungeon then
        out[#out + 1] = { grp = L["推荐五人本"] }
        local lv = PlayerLevel()
        for _, d in ipairs((ns.DungeonData and ns.DungeonData.dungeons) or {}) do
            if DG and d.levelMin and DG.GroupOf(d, lv) == "rec" then
                out[#out + 1] = DungeonRow(d)
                n.dungeon = n.dungeon + 1
            end
        end
        if n.dungeon == 0 then
            out[#out + 1] = { text = L["当前等级暂无推荐副本"], dead = true }
        end
        out[#out + 1] = { text = L["全部副本"], act = "page", key = "Dungeons", gold = true }
    end

    if cfg.groups.prof and ns.LoadForeverPages then
        out[#out + 1] = { grp = L["专业"] }
        local D = ns.ProfData
        local PD = ns.ProfModule
        local learned = (PD and PD.ProfLearned) and PD.ProfLearned() or {}
        for _, slug in ipairs((D and D.order) or {}) do
            local p = D.pro and D.pro[slug]
            local known = learned[slug]
            if p and (cfg.profMode == "all" or known) then
                local tip = p.name or slug
                if known then
                    tip = tip .. "\\n" .. format(L["熟练度 %d/%d"], known.cur or 0, known.max or 0)
                else
                    tip = tip .. "\\n" .. L["未学习"]
                end
                out[#out + 1] = {
                    text = p.name or slug,
                    aux = known and format("%d/%d", known.cur or 0, known.max or 0) or L["未学"],
                    tip = tip,
                    act = "prof",
                    slug = slug,
                    known = known and true or false,
                }
                n.prof = n.prof + 1
            end
        end
        if n.prof == 0 then out[#out + 1] = { text = L["未学任何专业"], dead = true } end
    end

    if cfg.groups.explore and ns.LoadForeverPages then
        out[#out + 1] = { grp = L["探索"] }
        for _, e in ipairs(EXPLORE_DEFS) do
            if cfg.expl[e.key] then
                out[#out + 1] = { text = e.text, act = "explore", key = e.key }
                n.explore = n.explore + 1
            end
        end
        if n.explore == 0 then out[#out + 1] = { text = L["未选任何探索子页"], dead = true } end
    end

    self.counts = n
    return out
end

function QB:Scroll(delta)
    local sc = self.scroll
    if not sc then return end
    local maxS = math.max(0, (self.content:GetHeight() or 0) - (sc:GetHeight() or 0))
    local cur = sc:GetVerticalScroll() or 0
    sc:SetVerticalScroll(math.max(0, math.min(maxS, cur - (delta or 0) * 40)))
end

function QB:RowAt(i)
    local r = self.pool[i]
    if r then return r end
    r = CreateFrame("Button", nil, self.content)
    r:SetSize(self.CW, 24)
    r:RegisterForClicks("LeftButtonUp")

    r.name = Fs(r, self.FS_NAME, C_TEXT)
    r.name:SetPoint("TOPLEFT", r, "TOPLEFT", self.TEXT_PAD, -3)
    r.name:SetWidth(NAME_W)
    r.name:SetJustifyH("LEFT")
    r.name:SetWordWrap(true)

    r.aux = Fs(r, self.FS_AUX, C_AUX)
    r.aux:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", self.TEXT_PAD, 4)
    r.aux:SetJustifyH("LEFT")

    local H = ns.ProfHost
    if H and H.MakeOutline then H.MakeOutline(r, 1, 0.82, 0) end
    Outline(r, false)

    r:SetScript("OnEnter", function(self)
        Outline(self, true)
        if self.spec and self.spec.tip then
            GameTooltip:SetOwner(self, "ANCHOR_LEFT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(self.spec.tip, 1, 1, 1, true)
            GameTooltip:Show()
        end
    end)
    r:SetScript("OnLeave", function(self)
        Outline(self, false)
        GameTooltip:Hide()
    end)
    r:SetScript("OnClick", function(self) QB:Click(self.spec) end)

    self.pool[i] = r
    return r
end

function QB:Ensure()
    if self.built then return self end
    local host = ns.MainFrame
    if not host then return nil end

    local f = CreateFrame("Frame", "DungeonsForever_QuickBar", host, "BackdropTemplate")
    f:SetWidth(self.W)
    f:SetPoint("TOPLEFT", host, "TOPRIGHT", self.SLOT2, 0)
    f:SetPoint("BOTTOMLEFT", host, "BOTTOMRIGHT", self.SLOT2, 0)
    f:SetFrameLevel(512)
    f:EnableMouse(true)
    f:SetScript("OnMouseWheel", function() end)
    if ns.hui and ns.hui.SkinPopup then ns.hui.SkinPopup(f, 8) end
    self.frame = f

    local head = Fs(f, self.FS_HEAD, C_WHITE)
    head:SetText(L["快捷"])
    head:SetPoint("TOPLEFT", f, "TOPLEFT", self.PAD, self.HEAD_Y)

    local line = f:CreateTexture(nil, "ARTWORK")
    line:SetColorTexture(1, 1, 1, 0.08)
    line:SetPoint("TOPLEFT", f, "TOPLEFT", self.PAD, self.BODY_Y + 6)
    line:SetPoint("TOPRIGHT", f, "TOPRIGHT", -self.PAD, self.BODY_Y + 6)
    line:SetHeight(1)

    local scroll = CreateFrame("ScrollFrame", nil, f)
    scroll:SetPoint("TOPLEFT", f, "TOPLEFT", self.PAD, self.BODY_Y)
    scroll:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -self.PAD, 10)
    scroll:EnableMouseWheel(true)
    scroll:SetScript("OnMouseWheel", function(_, delta) QB:Scroll(delta) end)

    local content = CreateFrame("Frame", nil, scroll)
    content:SetWidth(self.CW)
    content:SetHeight(10)
    scroll:SetScrollChild(content)
    content:EnableMouseWheel(true)
    content:SetScript("OnMouseWheel", function(_, delta) QB:Scroll(delta) end)

    self.scroll, self.content = scroll, content
    self.pool, self.grpPool = {}, {}
    self.built = true
    return self
end

function QB:Render()
    if not self.built then return end
    local specs = self:Collect()
    self.specs = specs

    local y, nRow, nGrp = -2, 0, 0
    for _, sp in ipairs(specs) do
        if sp.grp then
            nGrp = nGrp + 1
            local fs = self.grpPool[nGrp]
            if not fs then
                fs = Fs(self.content, self.FS_AUX, C_DIM)
                fs:SetJustifyH("LEFT")
                self.grpPool[nGrp] = fs
            end
            fs:SetText(sp.grp)
            fs:ClearAllPoints()
            fs:SetPoint("TOPLEFT", self.content, "TOPLEFT", self.TEXT_PAD, y - 4)
            fs:Show()
            y = y - self.GRP_H
        else
            nRow = nRow + 1
            local r = self:RowAt(nRow)
            r.spec = sp
            r.name:SetText(sp.text)
            if sp.dead then
                r.name:SetTextColor(C_DIM[1], C_DIM[2], C_DIM[3])
            elseif sp.gold then
                r.name:SetTextColor(C_GOLD[1], C_GOLD[2], C_GOLD[3])
            elseif sp.known then
                r.name:SetTextColor(Accent())
            else
                r.name:SetTextColor(C_TEXT[1], C_TEXT[2], C_TEXT[3])
            end
            if sp.aux then
                r.aux:SetText(sp.aux)
                r.aux:Show()
            else
                r.aux:Hide()
            end
            local h = RowH(sp.text, sp.aux and true or false)
            r:SetHeight(h)
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", self.content, "TOPLEFT", 0, y)
            r:Show()
            y = y - h - self.GAP
        end
    end
    for i = nRow + 1, #self.pool do self.pool[i]:Hide() end
    for i = nGrp + 1, #self.grpPool do self.grpPool[i]:Hide() end
    self.content:SetHeight(math.max(10, -y + 6))
    self.rows, self.groups = nRow, nGrp
end

function QB:Click(spec)
    if type(spec) ~= "table" or spec.dead then return end
    ns.PlaySound(1)
    if spec.act == "dungeon" then
        if ns.ShowDungeonDetail then ns.ShowDungeonDetail(spec.id) end
    elseif spec.act == "prof" then
        ns.OpenPage("Professions")
        if ns.ProfModule and ns.ProfModule.Show then ns.ProfModule.Show(spec.slug) end
    elseif spec.act == "explore" then
        ns.OpenPage("Explore")
        if ns.ExploreModule and ns.ExploreModule.ShowSub then
            ns.ExploreModule.ShowSub(spec.key)
        end
    elseif spec.act == "page" then
        ns.OpenPage(spec.key)
    end
end

-- 显隐与刷新 ---------------------------------------------------------------
function QB:Apply()
    local cfg = ns.QuickCfg()
    if not cfg.on then
        if self.frame then self.frame:Hide() end
        return
    end
    if not self.built and not self:Ensure() then return end
    self:Render()
    self.frame:Show()
end

function QB:OnMainShow()
    self:Apply()
end

-- 设置面板分组（挂主窗的「设置」弹窗，不另开窗口） --------------------------
local SET_PAD, SET_ROW_H, SET_HDR_H = 14, 24, 22

local function Toggle(parent)
    local tg = CreateFrame("CheckButton", nil, parent)
    tg:SetSize(36, 20)
    tg:EnableMouse(true)
    if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end
    tg.label = Fs(parent, 14, C_TEXT)
    tg.label:SetJustifyH("RIGHT")
    tg.label:SetPoint("RIGHT", tg, "LEFT", -6, 0)
    return tg
end

local function Chip(parent, text, w, h)
    local bt = CreateFrame("Button", nil, parent, "BackdropTemplate")
    bt:SetSize(w, h)
    local H = ns.ProfHost
    if H and H.MakeOutline then H.MakeOutline(bt, 1, 0.82, 0) end
    bt.label = Fs(bt, 14, C_TEXT)
    bt.label:SetText(text)
    bt.label:SetPoint("CENTER", bt, "CENTER", 0, 0)
    return bt
end

local function PaintChip(bt, on)
    Outline(bt, on)
    local c = on and C_GOLD or C_DIM
    bt.label:SetTextColor(c[1], c[2], c[3])
end

function QB:EnsureSettings()
    if self.setBuilt then return true end
    local pop = ns.SettingsPopup
    if not pop then return false end

    local set = { group = {}, expl = {} }
    local y = -44

    local function Header(text)
        local fs = Fs(pop, self.FS_AUX, C_DIM)
        fs:SetPoint("TOPLEFT", pop, "TOPLEFT", SET_PAD, y)
        fs:SetText(text)
        y = y - SET_HDR_H
    end

    local function ToggleRow(label, isOn, setOn)
        local tg = Toggle(pop)
        tg:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -SET_PAD, y)
        tg.label:SetText(label)
        tg:SetChecked(isOn() and true or false)
        tg:SetScript("OnClick", function(self)
            ns.PlaySound(1)
            setOn(not isOn())
            self:SetChecked(isOn() and true or false)
            QB:SyncSettings()
            QB:Apply()
        end)
        y = y - SET_ROW_H
        return tg
    end

    Header(L["快捷按钮栏"])
    set.on = ToggleRow(L["显示快捷按钮栏"],
        function() return ns.QuickCfg().on end,
        function(v) ns.QuickCfg().on = v end)

    Header(L["显示分组"])
    for _, def in ipairs({
        { key = "dungeon", label = L["推荐五人本"] },
        { key = "prof",    label = L["专业"] },
        { key = "explore", label = L["探索"] },
    }) do
        if ns.LoadForeverPages or def.key == "dungeon" then
            local key = def.key
            set.group[key] = ToggleRow(def.label,
                function() return ns.QuickCfg().groups[key] end,
                function(v) ns.QuickCfg().groups[key] = v end)
        end
    end

    Header(L["专业列表"])
    do
        local learned = Chip(pop, L["只看已学"], 68, 22)
        local all = Chip(pop, L["全部"], 68, 22)
        learned:SetPoint("TOPRIGHT", pop, "TOPRIGHT", -SET_PAD, y)
        all:SetPoint("RIGHT", learned, "LEFT", -6, 0)
        set.chipLearned, set.chipAll = learned, all
        learned:SetScript("OnClick", function()
            ns.PlaySound(1)
            ns.QuickCfg().profMode = "learned"
            QB:SyncSettings()
            QB:Apply()
        end)
        all:SetScript("OnClick", function()
            ns.PlaySound(1)
            ns.QuickCfg().profMode = "all"
            QB:SyncSettings()
            QB:Apply()
        end)
        y = y - SET_ROW_H
    end

    Header(L["探索子页"])
    for _, def in ipairs(EXPLORE_DEFS) do
        local key = def.key
        set.expl[key] = ToggleRow(def.text,
            function() return ns.QuickCfg().expl[key] end,
            function(v) ns.QuickCfg().expl[key] = v end)
    end

    self.set, self.setBuilt = set, true
    return true
end

function QB:SyncSettings()
    if not self:EnsureSettings() then return end
    local cfg = ns.QuickCfg()
    local set = self.set

    local function Gate(tg)
        if cfg.on then tg:Enable() else tg:Disable() end
    end

    set.on:SetChecked(cfg.on and true or false)
    for k, tg in pairs(set.group) do
        tg:SetChecked(cfg.groups[k] and true or false)
        Gate(tg)
    end
    for k, tg in pairs(set.expl) do
        tg:SetChecked(cfg.expl[k] and true or false)
        Gate(tg)
    end
    PaintChip(set.chipLearned, cfg.profMode ~= "all")
    PaintChip(set.chipAll, cfg.profMode == "all")
end

ns.Init(function()
    local ev = CreateFrame("Frame")
    ev:RegisterEvent("PLAYER_LEVEL_UP")
    ev:RegisterEvent("PLAYER_ENTERING_WORLD")
    ev:RegisterEvent("SKILL_LINES_CHANGED")
    ev:SetScript("OnEvent", function()
        if QB.built then QB:Render() end
    end)
    QB.events = ev
end)
'''

# ------------------------------------------------------------------ Core.lua
CORE_OLD = '''ns.options = ns.options or {}
if ns.options.buttonSound == nil then ns.options.buttonSound = true end
'''

CORE_NEW = CORE_OLD + '''
-- 快捷按钮栏（贴主窗右侧第二槽）配置：缺失补默认；版本不符整档重置。
-- 键名即中文文案（zhTW / enUS 走 L 回退），无需另行登记词条。
ns.QUICK_VER = 1
ns.QUICK_GROUPS = { "dungeon", "prof", "explore" }
ns.QUICK_EXPLORE = { "books", "rewards", "bag", "bm" }

function ns.QuickCfg()
    local ui = DB().ui
    local q = ui.quick
    if type(q) ~= "table" or q.ver ~= ns.QUICK_VER then
        q = { ver = ns.QUICK_VER }
        ui.quick = q
    end
    if q.on == nil then q.on = true end
    if type(q.groups) ~= "table" then q.groups = {} end
    for _, k in ipairs(ns.QUICK_GROUPS) do
        if q.groups[k] == nil then q.groups[k] = true end
    end
    if q.profMode ~= "all" then q.profMode = "learned" end
    if type(q.expl) ~= "table" then q.expl = {} end
    for _, k in ipairs(ns.QUICK_EXPLORE) do
        if q.expl[k] == nil then q.expl[k] = true end
    end
    return q
end
'''

# ------------------------------------------------------------- DungeonUI.lua
DG_OLD = '''function ns.OpenPage(key)
    local frame = ns.TalentSimFrame
    if not frame then return end
    if not frame:IsShown() then frame:Show() end
    frame:Raise()
    if U.built then U:SwitchSub(key) end
end
'''

DG_NEW = DG_OLD + '''
-- 供「快捷按钮栏」调用：切到副本页并直接打开该副本的详情（id 不存在则不动）。
function ns.ShowDungeonDetail(id)
    local d
    for _, x in ipairs((ns.DungeonData and ns.DungeonData.dungeons) or {}) do
        if x.id == id then d = x break end
    end
    if not d then return end
    ns.OpenPage("Dungeons")
    if U.built and U.dungeonBuilt then
        U:SetDungeonView("list")
        U:ShowDungeonDetail(d)
    end
end
'''

# ------------------------------------------------------------- ExploreUI.lua
EX_OLD = '''function EG.Open()
    if not EG.built then return end
    EG.Render()
end
'''

EX_NEW = EX_OLD + '''
-- 供「快捷按钮栏」调用：切到指定子页（books / rewards / bag / bm）。
function EG.ShowSub(key)
    if not EG.built then return end
    SetSub(key)
end
'''

# ------------------------------------------------------------- MainFrame.lua
MF_OLD1 = '''ns.CloseSettings = function()
    if settingsPop then settingsPop:Hide() end
    SyncSettingsGlyph()
end
'''

MF_NEW1 = MF_OLD1 + '''
-- 设置面板对外入口：别的模块（快捷按钮栏）把自己的分组挂进这个弹窗。
ns.SettingsPopup = settingsPop
'''

MF_OLD2 = '''    settingsPop:SetShown(show)
    SyncSettingsGlyph()
end)
'''

MF_NEW2 = '''    if show and ns.QuickBar then ns.QuickBar:SyncSettings() end
    settingsPop:SetShown(show)
    SyncSettingsGlyph()
end)
'''

MF_OLD3 = '''f:HookScript("OnShow", function()
    about:Hide()
    SyncAboutGlyph()
    if settingsPop then settingsPop:Hide() end
    SyncSettingsGlyph()
    if ns.LootFilterUI then ns.LootFilterUI:CloseConfig() end
end)
'''

MF_NEW3 = '''f:HookScript("OnShow", function()
    about:Hide()
    SyncAboutGlyph()
    if settingsPop then settingsPop:Hide() end
    SyncSettingsGlyph()
    if ns.LootFilterUI then ns.LootFilterUI:CloseConfig() end
    if ns.QuickBar then ns.QuickBar:OnMainShow() end
end)
'''

TOC_OLD = 'Core\\MainFrame.lua\n'
TOC_NEW = 'Core\\MainFrame.lua\nCore\\QuickBar.lua\n'


def main():
    qb_path = os.path.join(ROOT, 'Core', 'QuickBar.lua')
    if os.path.exists(qb_path):
        print('!! Core/QuickBar.lua 已存在 —— 本脚本只用于首次落盘')
        return 1
    with open(qb_path, 'wb') as f:
        f.write(enc(QB_LUA, False))
    b = open(qb_path, 'rb').read()
    print('  新建 %-26s CRLF=%-6d 裸LF=%-6d' % ('Core/QuickBar.lua',
                                              b.count(b'\r\n'), b.count(b'\n') - b.count(b'\r\n')))

    ok = True
    ok &= patch('Core/Core.lua', [(CORE_OLD, CORE_NEW)])
    ok &= patch('Core/DungeonUI.lua', [(DG_OLD, DG_NEW)])
    ok &= patch('Core/ExploreUI.lua', [(EX_OLD, EX_NEW)])
    ok &= patch('Core/MainFrame.lua', [(MF_OLD1, MF_NEW1), (MF_OLD2, MF_NEW2), (MF_OLD3, MF_NEW3)])
    ok &= patch('DungeonsForever.toc', [(TOC_OLD, TOC_NEW)])
    print('结果：%s' % ('OK' if ok else 'FAILED'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

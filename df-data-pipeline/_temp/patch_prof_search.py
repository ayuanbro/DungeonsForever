# -*- coding: utf-8 -*-
# 2026-10-09 配方页：搜索框（工具行右端）+ 名称列按本页现算（材料列加宽）
# 目标：Core/ProfessionUI.lua（LF）。每个锚点断言恰好命中 1 次，命中数不对即中止。
import sys, io

P = r'D:\workspace\DungeonsForever\Core\ProfessionUI.lua'
raw = open(P, 'rb').read()
crlf = raw.count(b'\r\n')
bare = raw.count(b'\n') - crlf
if crlf != 0:
    print('FATAL: 文件不是纯 LF（CRLF=%d）' % crlf); sys.exit(1)
s = raw.decode('utf-8')

def rep(old, new, tag):
    global s
    n = s.count(old)
    if n != 1:
        print('FATAL[%s]: 锚点命中 %d 次（应为 1）' % (tag, n)); sys.exit(1)
    s = s.replace(old, new, 1)
    print('OK %s' % tag)

# ---------- ① 常量区：搜索框尺寸 + 名称列现算常量 ----------
rep('''PD.MAT_W = PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - PD.MAT_X - 8
''',
'''PD.MAT_W = PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - PD.MAT_X - 8

-- 2026-10-09：名称列按本页实际名称现算（同升级页「四列全现算」口径）——
-- 名称列只留放得下本页最宽名称 / 副行的宽度，剩余全给材料列；0.40 分割只在加载期兜底。
PD.RECIPE_NAME_MIN, PD.RECIPE_NAME_MAX = 118, math.floor(PD.MAT_ROW_W * 0.38)
PD.RECIPE_NAME_PAD = 44     -- 行首图标区(~32) + 名称与材料列间距
PD.RECIPE_BADGE_W = 34      -- 「新」角标占宽
PD.SEARCH_EB_W, PD.SEARCH_W = 150, 180
PD.SEARCH_RESERVED = 190    -- 工具首行给搜索框让出的宽（框宽 + 间隙）
''', '01-constants')

# ---------- ② PaintTool：首行右端给搜索框让位 ----------
rep('''            local w, text = PD.ToolSize(def.text)
            if x > 0 and x + w > PD.RIGHT_W then row = row + 1; x = 0 end
''',
'''            local w, text = PD.ToolSize(def.text)
            local lim = PD.RIGHT_W - ((row == 0) and PD.SearchReserve() or 0)
            if x > 0 and x + w > lim then row = row + 1; x = 0 end
''', '02-painttool')

# ---------- ③ 搜索 / 现算函数（插在 RecipeSpec 之前） ----------
rep('''function PD.RecipeSpec(r)
''',
'''-- ---- 配方搜索（2026-10-09）：按配方名 / 副行 / 材料名过滤当前列表 ----
function PD.SearchReserve()
    if PD.tab == "recipe" and not PD.setOpen then return PD.SEARCH_RESERVED end
    return 0
end

function PD.SearchHit(s)
    local q = PD.searchQ
    if not q or q == "" then return true end
    local name = tostring(s.text or "")
    if name ~= "" and string.find(string.lower(name), q, 1, true) then return true end
    local sub = tostring(s.sub or "")
    if sub ~= "" and string.find(string.lower(sub), q, 1, true) then return true end
    for _, m in ipairs(s._mats or {}) do
        local nm = tostring(DG.ItemName(m[1]) or "")
        if nm ~= "" and string.find(string.lower(nm), q, 1, true) then return true end
    end
    return false
end

function PD.SearchFilter(list)
    local q = PD.searchQ
    if not q or q == "" then return list end
    local f = {}
    for _, s in ipairs(list) do
        if PD.SearchHit(s) then f[#f + 1] = s end
    end
    return f
end

-- 名称列按本页现算：量出本页最宽名称 / 副行，名称列只留放得下的宽度，剩余全给材料列
function PD.FitRecipeCols(list)
    local maxW = 0
    for _, s in ipairs(list) do
        local w = PD.TextW(s.text or "", 13)
        if s.is_new then w = w + PD.RECIPE_BADGE_W end
        local sw = PD.TextW(s.sub or "", 11)
        if sw > w then w = sw end
        if w > maxW then maxW = w end
    end
    local nameW = math.floor(math.max(PD.RECIPE_NAME_MIN,
                   math.min(PD.RECIPE_NAME_MAX, maxW + 6)))
    PD.RECIPE_NAME_W = nameW
    PD.MAT_X = nameW + PD.RECIPE_NAME_PAD
    PD.MAT_W = PD.MAT_ROW_W - PD.MAT_RIGHT_RESERVE - PD.MAT_X - 8
    for _, s in ipairs(list) do
        if s._mats then s.mats = PD.MatCol(s._mats, PD.MAT_FS, PD.MAT_W) end
        if s.text and s.text ~= "" then
            s.text = PD.Fit(s.text, 13, nameW - (s.is_new and PD.RECIPE_BADGE_W or 0))
        end
    end
end

function PD.RecipeSpec(r)
''', '03-funcs')

# ---------- ④ RowsRecipe：过滤 + 现算 + 搜索空态 ----------
rep('''    local list = PD.RecipeList()
    local total = (d.counts and d.counts.total) or #list
''',
'''    local list = PD.SearchFilter(PD.RecipeList())
    PD.FitRecipeCols(list)
    local total = (d.counts and d.counts.total) or #list
''', '04-rowsrecipe-head')

rep('''                          #list, total, unread))
    local trunc = 0
''',
'''                          #list, total, unread))
    if #list == 0 and PD.searchQ and PD.searchQ ~= "" then
        PushGap(rows)
        PushText(rows, format(L["没有名称或材料匹配「%s」的配方 —— 换个关键词再试试。"],
                              PD.searchQ), 12, C_GOLD)
        return
    end
    local trunc = 0
''', '05-rowsrecipe-empty')

# ---------- ⑤ Build：搜索框（照目标等级输入框的既有模式） ----------
rep('''    PD.tgtBox = tgt
''',
'''    PD.tgtBox = tgt

    -- 配方搜索框（2026-10-09）：配方页工具行右端，输入即按名称 / 材料过滤
    local sb = CreateFrame("Frame", nil, page)
    sb:SetSize(PD.SEARCH_W, PD.TOOL_H)
    sb:Hide()
    sb.label = MakeFS(sb, 12, C_GREY, "LEFT")
    sb.label:SetText(L["搜索"])
    sb.label:SetPoint("LEFT", sb, "LEFT", 0, 0)
    local seb = CreateFrame("EditBox", nil, sb, "BackdropTemplate")
    seb:SetBackdrop({
        bgFile = "Interface\\\\Buttons\\\\WHITE8x8",
        edgeFile = "Interface\\\\Buttons\\\\WHITE8x8",
        edgeSize = 1,
    })
    seb:SetBackdropColor(0, 0, 0, 0.55)
    seb:SetBackdropBorderColor(1, 1, 1, 0.25)
    seb:SetSize(PD.SEARCH_EB_W, PD.TOOL_H)
    seb:SetPoint("LEFT", sb.label, "RIGHT", 6, 0)
    seb:SetFont(ns.FONT, 12, ns.hui and ns.hui.FontFlags and ns.hui.FontFlags("OUTLINE") or "OUTLINE")
    seb:SetTextColor(1, 1, 1, 1)
    seb:SetJustifyH("LEFT")
    seb:SetAutoFocus(false)
    seb:SetTextInsets(5, 5, 0, 0)
    seb:SetMaxLetters(40)
    seb.ph = MakeFS(seb, 11, C_GREY, "LEFT")
    seb.ph:SetText(L["配方名 / 材料名"])
    seb.ph:SetPoint("LEFT", seb, "LEFT", 6, 0)
    seb.ph:Hide()
    local function SyncPh()
        local t = seb:GetText()
        if (t == nil or t == "") and not seb:HasFocus() then
            seb.ph:Show()
        else
            seb.ph:Hide()
        end
    end
    seb:SetScript("OnTextChanged", function(self)
        SyncPh()
        local t = string.lower(tostring(self:GetText() or ""))
        if t == (PD.searchQ or "") then return end
        PD.searchQ = t
        PD.Render()
    end)
    seb:SetScript("OnEscapePressed", function(self)
        if self:GetText() ~= "" then self:SetText("") end
        self:ClearFocus()
        SyncPh()
    end)
    seb:SetScript("OnEnterPressed", function(self)
        self:ClearFocus()
        SyncPh()
        ns.PlaySound(1)
    end)
    seb:SetScript("OnEditFocusGained", function() seb.ph:Hide() end)
    seb:SetScript("OnEditFocusLost", function() SyncPh() end)
    sb.eb = seb
    PD.searchBox = sb
''', '06-build-searchbox')

# ---------- ⑥ Render：搜索框显隐（仅配方页） ----------
rep('''            PD.tgtBox:Hide()
        end
    end

    PD.specs = rows
''',
'''            PD.tgtBox:Hide()
        end
    end

    -- 配方搜索框：仅配方页显示（工具行右端，红框位置）
    if PD.searchBox then
        if PD.tab == "recipe" and not PD.setOpen then
            PD.searchBox:ClearAllPoints()
            PD.searchBox:SetPoint("TOPRIGHT", PD.page, "TOPRIGHT",
                                  -PAGE_INSET, -(PD.BODY_TOP))
            PD.searchBox:Show()
        else
            PD.searchBox:Hide()
        end
    end

    PD.specs = rows
''', '07-render-place')

# ---------- ⑦ Show：换专业清空搜索 ----------
rep('''        PD.tab = "overview"
        PD.setOpen = false
    end
    PD.Render()
end
''',
'''        PD.tab = "overview"
        PD.setOpen = false
        PD.searchQ = nil
        if PD.searchBox then PD.searchBox.eb:SetText("") end
    end
    PD.Render()
end
''', '08-show-reset')

out = s.encode('utf-8')
if out.count(b'\r\n') != 0:
    print('FATAL: 落盘前换行自检失败（混入 CRLF）'); sys.exit(1)
open(P, 'wb').write(out)
print('写入 %d 字节，裸 LF = %d，CRLF = 0' % (len(out), out.count(b'\n')))

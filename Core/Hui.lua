local _, ns = ...

local tinsert = table.insert
local format = format
local wipe = wipe

ns.hui = ns.hui or {}

local function HCharStep(text, i)
    local b = text:byte(i)
    local step = 1
    if b >= 0xF0 then step = 4
    elseif b >= 0xE0 then step = 3
    elseif b >= 0xC0 then step = 2 end
    return text:sub(i, i + step - 1), step, ((b >= 0x80) and 1 or 0.55)
end

local function HTokenize(text)
    local toks, pos = {}, 1
    while true do
        local s, e = string.find(text, "|T.-|t", pos)
        if not s then
            if pos <= #text then toks[#toks + 1] = { t = string.sub(text, pos) } end
            break
        end
        if s > pos then toks[#toks + 1] = { t = string.sub(text, pos, s - 1) } end
        toks[#toks + 1] = { t = string.sub(text, s, e), icon = true }
        pos = e + 1
    end
    return toks
end

function ns.hui.TextW(text, fs)
    if type(text) ~= "string" then return 0 end
    local w = 0
    for _, tk in ipairs(HTokenize(text)) do
        if tk.icon then
            w = w + fs + 2
        else
            local i, n = 1, #tk.t
            while i <= n do
                local _, step, k = HCharStep(tk.t, i)
                w = w + k * fs
                i = i + step
            end
        end
    end
    return w
end

function ns.hui.Fit(text, fs, width)
    if type(text) ~= "string" then return "" end
    if ns.hui.TextW(text, fs) <= width then return text end
    local out, w = "", 0
    for _, tk in ipairs(HTokenize(text)) do
        if tk.icon then
            local cw = fs + 2
            if w + cw > width - fs then break end
            out = out .. tk.t
            w = w + cw
        else
            local i, n = 1, #tk.t
            local stop = false
            while i <= n do
                local ch, step, k = HCharStep(tk.t, i)
                local cw = k * fs
                if w + cw > width - fs then stop = true break end
                out = out .. ch
                w = w + cw
                i = i + step
            end
            if stop then break end
        end
    end
    return out .. "…"
end

ns.hui.CharStep = HCharStep

do
    local HUI_L1 = {0x10 / 255, 0x13 / 255, 0x1A / 255, 0.95}
    local HUI_ACCENT = {0x46 / 255, 0xbf / 255, 0x72 / 255, 0.95}
    local ACCENT_GREEN = {0x46 / 255, 0xbf / 255, 0x72 / 255}
    local HUI_CORNER_TL = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundCornerFill"
    local HUI_CORNER_TR = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundCornerFillTR"
    local HUI_CORNER_BL = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundCornerFillBL"
    local HUI_CORNER_BR = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundCornerFillBR"
    local GLASS_FILL_TEX = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIGlassFill"
    local GLASS_RING_TEX = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIGlassRing"
    local function SnapCornerR(r)
        if r <= 5 then return 4
        elseif r <= 7 then return 6
        elseif r <= 9 then return 8
        elseif r <= 11 then return 10
        else return 12 end
    end
    local function CornerQuadUV(point, snap)
        local c = snap / 32
        local l = point:find("LEFT") and 0 or (1 - c)
        local t = point:find("TOP") and 0 or (1 - c)
        return l, t, l, t + c, l + c, t, l + c, t + c
    end
    local HUI_CIRCLE = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUICircle"
    local C_TRACKOFF = {0x33 / 255, 0x3A / 255, 0x49 / 255}
    local C_KNOB = {0x17 / 255, 0x18 / 255, 0x1c / 255}
    local C_CTRL_BORDER = {0x4A / 255, 0x52 / 255, 0x63 / 255}
    local C_TOGGLE_BORDER = C_CTRL_BORDER
    local HUI_PILL_L = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIPillL"
    local HUI_PILL_R = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIPillR"
    local HUI_CORNER = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundCornerFill"
    local C_GRAY = {0.63, 0.63, 0.63}
    local C_RED = {0xf2 / 255, 0x53 / 255, 0x4e / 255}
    local C_CARD_BORDER = {1, 1, 1, 0.10}

    ns.hui.palette = {
        default        = { name = "灰",      deep = {0.63, 0.63, 0.63}, hue = 0,   sat = 0,    gray = true, order = 0 },
        pink           = { name = "暗粉",       deep = {0xDC / 255, 0xBC / 255, 0xC8 / 255}, hue = 338, sat = 0.38, lum = 1.5,  accent = {0xF0 / 255, 0xA8 / 255, 0xBC / 255}, order = 1 },
        orange         = { name = "橙",         deep = {0xDE / 255, 0xCB / 255, 0xBA / 255}, hue = 28,  sat = 0.42, lum = 1.3,  accent = {0xEE / 255, 0xA4 / 255, 0x63 / 255}, order = 2 },
        orangered      = { name = "橙红",       deep = {0xDD / 255, 0xC3 / 255, 0xBB / 255}, hue = 14,  sat = 0.40, lum = 1.3,  accent = {0xE9 / 255, 0x7E / 255, 0x5D / 255}, order = 3 },
        red            = { name = "红",         deep = {0xDC / 255, 0xBD / 255, 0xBC / 255}, hue = 2,   sat = 0.38, lum = 1.3,  accent = {0xE4 / 255, 0x5D / 255, 0x58 / 255}, order = 4 },
        qq             = { name = "湖蓝",       deep = {0xB1 / 255, 0xDA / 255, 0xF6 / 255}, hue = 204, sat = 0.34, accent = {0x71 / 255, 0xB3 / 255, 0xE0 / 255}, order = 5 },
        qqbright       = { name = "湖蓝亮",     deep = {0xC6 / 255, 0xE6 / 255, 0xF9 / 255}, hue = 204, sat = 0.30, lum = 1.35, accent = {0x8C / 255, 0xC6 / 255, 0xEC / 255}, order = 6 },
        zhangliangying = { name = "金棕",       deep = {0xD6 / 255, 0xB6 / 255, 0x65 / 255}, hue = 43,  sat = 0.42, accent = {0xE2 / 255, 0xBB / 255, 0x5A / 255}, order = 7 },
        graybright     = { name = "亮灰",       deep = {0.78, 0.78, 0.78}, hue = 0, sat = 0, lum = 1.5, order = 8 },
        youfeng        = { name = "青绿",       deep = {0xC3 / 255, 0xDC / 255, 0xC6 / 255}, hue = 135, sat = 0.22, accent = {0x61 / 255, 0xD1 / 255, 0x7D / 255}, order = 9 },
        tonghang       = { name = "青蓝",       deep = {0xB8 / 255, 0xE0 / 255, 0xE8 / 255}, hue = 190, sat = 0.30, accent = {0x70 / 255, 0xC9 / 255, 0xDB / 255}, order = 10 },
        youfengbright  = { name = "青绿亮",     deep = {0xD8 / 255, 0xEC / 255, 0xDA / 255}, hue = 135, sat = 0.18, lum = 1.35, accent = {0x86 / 255, 0xE0 / 255, 0x9C / 255}, order = 11 },
        tonghangbright = { name = "青蓝亮",     deep = {0xD2 / 255, 0xEE / 255, 0xF3 / 255}, hue = 190, sat = 0.26, lum = 1.35, accent = {0x97 / 255, 0xDC / 255, 0xEA / 255}, order = 12 },
        lianyi         = { name = "水蓝",       deep = {0xA1 / 255, 0xC3 / 255, 0xF6 / 255}, hue = 216, sat = 0.36, accent = {0x7F / 255, 0xA6 / 255, 0xE1 / 255}, order = 13 },
        lianyibright   = { name = "水蓝亮",     deep = {0xC0 / 255, 0xDC / 255, 0xF8 / 255}, hue = 216, sat = 0.32, lum = 1.35, accent = {0x9C / 255, 0xC0 / 255, 0xEC / 255}, order = 14 },
        black          = { name = "黑", deep = {0x46 / 255, 0xbf / 255, 0x72 / 255}, hue = 0, sat = 0, accent = {0x46 / 255, 0xbf / 255, 0x72 / 255}, order = 15,
                            blackBase = { L0 = 0x0A / 255, L1 = 0x12 / 255, L2 = 0x1A / 255, L3 = 0x24 / 255, DIV = 0x20 / 255, L4 = 0x2E / 255, L5 = 0x38 / 255 } },
    }
    local L0_GRAY = {0x0A / 255, 0x0C / 255, 0x10 / 255, 0.95}
    local L1_GRAY = {0x10 / 255, 0x13 / 255, 0x1A / 255, 0.95}
    local L2_GRAY = {0x16 / 255, 0x1A / 255, 0x22 / 255, 1}
    local L2_GRAY095 = {0x16 / 255, 0x1A / 255, 0x22 / 255, 0.95}
    local L3_GRAY = {0x20 / 255, 0x25 / 255, 0x32 / 255, 0.95}
    local DIV_GRAY = {0x1B / 255, 0x20 / 255, 0x29 / 255, 1}
    local L4_GRAY = {0x2B / 255, 0x31 / 255, 0x40 / 255, 0.95}
    local L5_GRAY = {0x38 / 255, 0x40 / 255, 0x4F / 255, 0.95}
    local LV = { L0 = 0x16 / 255, L1 = 0x2b / 255, L2 = 0x36 / 255, L3 = 0x40 / 255, DIV = 0x3a / 255, L4 = 0x4a / 255, L5 = 0x54 / 255 }
    ns.hui.layer = {
        L0 = {L0_GRAY[1], L0_GRAY[2], L0_GRAY[3], L0_GRAY[4]},
        L1 = {L1_GRAY[1], L1_GRAY[2], L1_GRAY[3], L1_GRAY[4]},
        L2 = {L2_GRAY[1], L2_GRAY[2], L2_GRAY[3], L2_GRAY[4]},
        L3 = {L3_GRAY[1], L3_GRAY[2], L3_GRAY[3], L3_GRAY[4]},
        L4 = {L4_GRAY[1], L4_GRAY[2], L4_GRAY[3], L4_GRAY[4]},
        L5 = {L5_GRAY[1], L5_GRAY[2], L5_GRAY[3], L5_GRAY[4]},
        DIV = {DIV_GRAY[1], DIV_GRAY[2], DIV_GRAY[3], DIV_GRAY[4]},
        ACCENT = {0x46 / 255, 0xbf / 255, 0x72 / 255},
    }
    ns.hui.L1_GRAY, ns.hui.L2_GRAY, ns.hui.L2_GRAY095 = L1_GRAY, L2_GRAY, L2_GRAY095
    local function hsl2rgb(h, s, l)
        h = h / 360
        local r, g, b
        if s <= 0 then
            r, g, b = l, l, l
        else
            local q = l < 0.5 and l * (1 + s) or l + s - l * s
            local p = 2 * l - q
            local function hue2rgb(t)
                if t < 0 then t = t + 1 elseif t > 1 then t = t - 1 end
                if t < 1 / 6 then return p + (q - p) * 6 * t
                elseif t < 1 / 2 then return q
                elseif t < 2 / 3 then return p + (q - p) * (2 / 3 - t) * 6
                else return p end
            end
            r = hue2rgb(h + 1 / 3); g = hue2rgb(h); b = hue2rgb(h - 1 / 3)
        end
        return r, g, b
    end
    local function sameGray(c, g)
        if not c or not g then return false end
        local tol = 0.004
        return math.abs((c[1] or 0) - g[1]) < tol and math.abs((c[2] or 0) - g[2]) < tol and math.abs((c[3] or 0) - g[3]) < tol
    end
    local function DeriveLayerColors(key)
        local p = key and ns.hui.palette[key]
        local out = {}
        local function emit(name, rgb)
            local dst = ns.hui.layer and ns.hui.layer[name]
            out[name] = { rgb[1], rgb[2], rgb[3], dst and dst[4] or 1 }
        end
        if not p then
            emit("L0", L0_GRAY)
            emit("L1", L1_GRAY)
            emit("L2", L2_GRAY)
            emit("L3", L3_GRAY)
            emit("L4", L4_GRAY)
            emit("L5", L5_GRAY)
            emit("DIV", DIV_GRAY)
        else
            local hue, sat = p.hue, p.sat
            local function tint(lvKey, lv)
                if p.blackBase then
                    local v = p.blackBase[lvKey]
                    if v then return { v, v, v } end
                end
                local r, g, b = hsl2rgb(hue, sat, math.min(1, lv * (p.lum or 1)))
                return { r, g, b }
            end
            emit("L0", tint("L0", LV.L0)); emit("L1", tint("L1", LV.L1))
            emit("L2", tint("L2", LV.L2)); emit("L3", tint("L3", LV.L3))
            emit("L4", tint("L4", LV.L4)); emit("L5", tint("L5", LV.L5))
            emit("DIV", tint("DIV", LV.DIV))
        end
        local ac = (p and p.accent) or ACCENT_GREEN
        out.ACCENT = { ac[1], ac[2], ac[3] }
        return out
    end
    local function ApplyLayerTheme(key)
        local snap = DeriveLayerColors(key)
        for _, name in ipairs({ "L0", "L1", "L2", "L3", "L4", "L5", "DIV", "ACCENT" }) do
            local dst = ns.hui.layer[name]
            local v = snap[name]
            dst[1], dst[2], dst[3] = v[1], v[2], v[3]
        end
        local ac = snap.ACCENT
        ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3] = ac[1], ac[2], ac[3]
        ns.hui.layer.ACCENT[1], ns.hui.layer.ACCENT[2], ns.hui.layer.ACCENT[3] = ac[1], ac[2], ac[3]
        HUI_ACCENT[1], HUI_ACCENT[2], HUI_ACCENT[3] = ac[1], ac[2], ac[3]
    end
    local __layerSnapshots = {}
    function ns.hui.LayerSnapshotOf(key)
        local ck = key or "_default"
        local snap = __layerSnapshots[ck]
        if not snap then
            snap = DeriveLayerColors(key)
            __layerSnapshots[ck] = snap
        end
        return snap
    end
    local function ScopeKeyForScope(scope)
        if not (ns.options and ns.options.perWindowColorTheme == 1) then return nil end
        if ns.GetWindowTheme and ns.GetWindowTheme(scope) ~= "hui" then return nil end
        local gk = DungeonsForeverDB.libHUI and DungeonsForeverDB.libHUI.colorTheme or nil
        local key = ns.GetWindowColorTheme and ns.GetWindowColorTheme(scope) or nil
        if key == nil or key == gk then return nil end
        if not (ns.hui.palette and ns.hui.palette[key]) then return nil end
        return key
    end
    function ns.hui.ScopeLayerForScope(scope)
        local key = ScopeKeyForScope(scope)
        return key and ns.hui.LayerSnapshotOf(key) or nil
    end
    function ns.hui.ScopeAccentRGBForScope(scope)
        local key = ScopeKeyForScope(scope)
        if not key then return nil end
        local p = key and ns.hui.palette and ns.hui.palette[key]
        local ac = (p and p.accent) or ACCENT_GREEN
        return { ac[1], ac[2], ac[3] }
    end

    function ns.hui.ApplyColorTheme(key)
        local prevAccentHex = ns.hui.TextHex(ns.g1 or "00FF00", "accent")
        local prevR, prevG, prevB = ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3]
        ApplyLayerTheme(key)
        if DungeonsForeverDB.libHUI then DungeonsForeverDB.libHUI.colorTheme = key end
        ns.hui.RefreshSkin()
        if ns.hui.RefreshFontObjects then ns.hui.RefreshFontObjects() end
        for _, fn in ipairs(ns.hui.__themeListeners) do pcall(fn) end
        local newAccentHex = ns.hui.TextHex(ns.g1 or "00FF00", "accent")
        ns.hui.RecolorAllThemeText(prevAccentHex, newAccentHex, prevR, prevG, prevB)
    end

    ns.hui.__scopeAccentHex = ns.hui.__scopeAccentHex or {}
    ns.hui.__scopeAccentRGB = ns.hui.__scopeAccentRGB or {}
    local function ScopeAccentOf(key)
        local p = key and ns.hui.palette and ns.hui.palette[key]
        local ac = (p and p.accent) or ACCENT_GREEN
        return format("%02x%02x%02x", ac[1] * 255 + 0.5, ac[2] * 255 + 0.5, ac[3] * 255 + 0.5),
            { ac[1], ac[2], ac[3] }
    end
    local function CollectSkinFrames(root, out)
        if not root or not root.GetChildren then return end
        if root.__huiRepaints or root.__huiRepaint then out[#out + 1] = root end
        local children = { root:GetChildren() }
        for i = 1, #children do CollectSkinFrames(children[i], out) end
    end
    local function InFrameTree(f, root)
        while f do
            if f == root then return true end
            f = f.GetParent and f:GetParent() or nil
        end
        return false
    end
    local function RecolorTextUnder(root, prevList, prevRGBs, newHex)
        if not root or not root.GetRegions then return end
        local function walk(f)
            if not f or not f.GetRegions then return end
            local regions = { f:GetRegions() }
            for i = 1, #regions do
                local r = regions[i]
                if r and r.GetObjectType and r:GetObjectType() == "FontString" then
                    local t = r:GetText()
                    if t then
                        local changed
                        for _, prevHex in ipairs(prevList) do
                            if prevHex ~= newHex and t:lower():find("|cff" .. prevHex, 1, true) then
                                local hexClass = ""
                                for j = 1, #prevHex do
                                    local ch = prevHex:sub(j, j)
                                    hexClass = hexClass .. "[" .. ch:upper() .. ch:lower() .. "]"
                                end
                                t = t:gsub("%|c[fF][fF]" .. hexClass, "|cff" .. newHex)
                                changed = true
                            end
                        end
                        if changed then r:SetText(t) end
                    end
                    if prevRGBs then
                        local cr, cg, cb = r:GetTextColor()
                        if cr then
                            for _, pc in ipairs(prevRGBs) do
                                local near = math.abs(cr - pc[1]) < 0.02
                                    and math.abs(cg - pc[2]) < 0.02 and math.abs(cb - pc[3]) < 0.02
                                if pc and near then
                                    r:SetTextColor(ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3])
                                    break
                                end
                            end
                        end
                    end
                end
            end
            local children = { f:GetChildren() }
            for i = 1, #children do walk(children[i]) end
        end
        walk(root)
    end

    function ns.WithColorThemeScope(scope, fn, ...)
        local global = DungeonsForeverDB.libHUI and DungeonsForeverDB.libHUI.colorTheme or nil
        local key = ns.GetWindowColorTheme and ns.GetWindowColorTheme(scope) or global
        if key == global then return fn(...) end
        if key ~= nil and not (ns.hui.palette and ns.hui.palette[key]) then return fn(...) end
        if ns.GetWindowTheme and ns.GetWindowTheme(scope) ~= "hui" then return fn(...) end
        local saved = {}
        for k, v in pairs(ns.hui.layer) do
            saved[k] = { v[1], v[2], v[3], v[4] }
        end
        local savedAccent = { ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3] }
        local savedHuiAccent = { HUI_ACCENT[1], HUI_ACCENT[2], HUI_ACCENT[3] }
        local savedKey = DungeonsForeverDB.libHUI and DungeonsForeverDB.libHUI.colorTheme or nil
        if DungeonsForeverDB.libHUI then DungeonsForeverDB.libHUI.colorTheme = key end
        ApplyLayerTheme(key)
        local scopeHex, scopeRGB = ScopeAccentOf(key)
        ns.hui.__scopeAccentHex[scope] = scopeHex
        ns.hui.__scopeAccentRGB[scope] = scopeRGB
        local ok, result = pcall(fn, ...)
        for k, v in pairs(saved) do
            local dst = ns.hui.layer[k]
            dst[1], dst[2], dst[3], dst[4] = v[1], v[2], v[3], v[4]
        end
        ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3] = savedAccent[1], savedAccent[2], savedAccent[3]
        HUI_ACCENT[1], HUI_ACCENT[2], HUI_ACCENT[3] = savedHuiAccent[1], savedHuiAccent[2], savedHuiAccent[3]
        if DungeonsForeverDB.libHUI then DungeonsForeverDB.libHUI.colorTheme = savedKey end
        if not ok then
            error(result, 0)
        end
        return result
    end

    function ns.hui.RefreshColorThemeScope(scope, ...)
        local roots = {}
        for i = 1, select("#", ...) do
            local r = select(i, ...)
            if r and r.GetChildren then roots[#roots + 1] = r end
        end
        if #roots == 0 then return end
        if not ns.GetWindowColorTheme then return end
        if ns.GetWindowTheme and ns.GetWindowTheme(scope) ~= "hui" then return end
        local globalKey = DungeonsForeverDB.libHUI and DungeonsForeverDB.libHUI.colorTheme or nil
        local key = ns.GetWindowColorTheme(scope)
        if key ~= nil and not (ns.hui.palette and ns.hui.palette[key]) then return end
        local prevGlobalHex, prevGlobalRGB = ScopeAccentOf(globalKey)
        local prevScopeHex, prevScopeRGB = ns.hui.__scopeAccentHex[scope], ns.hui.__scopeAccentRGB[scope]
        local needSwap = key ~= globalKey
        local saved, savedAccent, savedHuiAccent, savedKey
        if needSwap then
            saved = {}
            for k, v in pairs(ns.hui.layer) do
                saved[k] = { v[1], v[2], v[3], v[4] }
            end
            savedAccent = { ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3] }
            savedHuiAccent = { HUI_ACCENT[1], HUI_ACCENT[2], HUI_ACCENT[3] }
            savedKey = DungeonsForeverDB.libHUI and DungeonsForeverDB.libHUI.colorTheme or nil
            if DungeonsForeverDB.libHUI then DungeonsForeverDB.libHUI.colorTheme = key end
            ApplyLayerTheme(key)
        end
        for _, root in ipairs(roots) do
            local frames = {}
            CollectSkinFrames(root, frames)
            for _, f in ipairs(frames) do
                if f.__huiRepaints then
                    for _, fn in ipairs(f.__huiRepaints) do pcall(fn) end
                elseif f.__huiRepaint then
                    pcall(f.__huiRepaint, f)
                end
            end
            for fs, list in pairs(ns.hui.__textRepaints) do
                if fs and InFrameTree(fs, root) then
                    for _, apply in ipairs(list) do pcall(apply) end
                end
            end
        end
        if needSwap then
            for k, v in pairs(saved) do
                local dst = ns.hui.layer[k]
                dst[1], dst[2], dst[3], dst[4] = v[1], v[2], v[3], v[4]
            end
            ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3] = savedAccent[1], savedAccent[2], savedAccent[3]
            HUI_ACCENT[1], HUI_ACCENT[2], HUI_ACCENT[3] = savedHuiAccent[1], savedHuiAccent[2], savedHuiAccent[3]
            if DungeonsForeverDB.libHUI then DungeonsForeverDB.libHUI.colorTheme = savedKey end
        end
        local newHex, newRGB = ScopeAccentOf(key)
        local prevList = { prevGlobalHex }
        local prevRGBs = { prevGlobalRGB }
        if prevScopeHex and prevScopeHex ~= prevGlobalHex then
            prevList[#prevList + 1] = prevScopeHex
            prevRGBs[#prevRGBs + 1] = prevScopeRGB
        end
        for _, root in ipairs(roots) do
            RecolorTextUnder(root, prevList, prevRGBs, newHex)
        end
        ns.hui.__scopeAccentHex[scope] = newHex
        ns.hui.__scopeAccentRGB[scope] = newRGB
    end
    ns.hui.__skinRegistry = ns.hui.__skinRegistry or setmetatable({}, { __mode = "k" })
    function ns.hui.AddRepaint(f, fn)
        if not f then return end
        f.__huiRepaints = f.__huiRepaints or {}
        tinsert(f.__huiRepaints, fn)
        ns.hui.__skinRegistry[f] = true
    end
    function ns.hui.RefreshSkin()
        for f in pairs(ns.hui.__skinRegistry) do
            local reps = f.__huiRepaints
            if reps then
                local alive = true
                for _, fn in ipairs(reps) do
                    local ok, _ = pcall(fn)
                    if not ok then alive = false; break end
                end
                if not alive then ns.hui.__skinRegistry[f] = nil end
            elseif f.__huiRepaint then
                local ok, _ = pcall(f.__huiRepaint, f)
                if not ok then ns.hui.__skinRegistry[f] = nil end
            end
        end
        for fs, list in pairs(ns.hui.__textRepaints) do
            for _, apply in ipairs(list) do pcall(apply) end
        end
    end

    ns.hui.__textRepaints = ns.hui.__textRepaints or setmetatable({}, { __mode = "k" })
    local function themeTextRegister(fs, apply)
        apply()
        local list = ns.hui.__textRepaints[fs] or {}
        list[#list + 1] = apply
        ns.hui.__textRepaints[fs] = list
    end
    function ns.hui.SetThemeText(fs, fn)
        if not fs then return end
        themeTextRegister(fs, function() fs:SetText(fn()) end)
    end
    function ns.hui.SetThemeTextColor(fs, level)
        if not fs then return end
        themeTextRegister(fs, function()
            local c = (level == "accent") and ns.hui.ACCENT or ns.hui.TEXT[level or 1]
            fs:SetTextColor(c[1], c[2], c[3])
        end)
    end

    ns.hui.__themeRecolorRoots = ns.hui.__themeRecolorRoots or {}
    function ns.hui.AddRecolorRoot(f)
        if f then ns.hui.__themeRecolorRoots[f] = true end
    end
    function ns.hui.RecolorAllThemeText(prevHex, newHex, prevR, prevG, prevB)
        if not prevHex or not newHex or prevHex == newHex then return end
        prevHex = prevHex:lower()
        local hexClass = ""
        for i = 1, #prevHex do
            local ch = prevHex:sub(i, i)
            hexClass = hexClass .. "[" .. ch:upper() .. ch:lower() .. "]"
        end
        local ph = "%|c[fF][fF]" .. hexClass
        local function walk(f)
            if not f or not f.GetRegions then return end
            local regions = { f:GetRegions() }
            for i = 1, #regions do
                local r = regions[i]
                if r and r.GetObjectType and r:GetObjectType() == "FontString" then
                    local t = r:GetText()
                    if t and t:lower():find("|cff" .. prevHex, 1, true) then
                        r:SetText(t:gsub(ph, "|cff" .. newHex))
                    end
                    if prevR then
                        local cr, cg, cb = r:GetTextColor()
                        if cr and math.abs(cr - prevR) < 0.02 and math.abs(cg - prevG) < 0.02 and math.abs(cb - prevB) < 0.02 then
                            r:SetTextColor(ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3])
                        end
                    end
                end
            end
            local children = { f:GetChildren() }
            for i = 1, #children do walk(children[i]) end
        end
        local roots = {}
        if ns.MainFrame then roots[#roots + 1] = ns.MainFrame end
        if ns.FBMainFrame and ns.FBMainFrame ~= ns.MainFrame then roots[#roots + 1] = ns.FBMainFrame end
        for f in pairs(ns.hui.__themeRecolorRoots) do roots[#roots + 1] = f end
        for i = 1, #roots do walk(roots[i]) end
    end

    ns.hui.__themeListeners = ns.hui.__themeListeners or {}
    function ns.hui.OnThemeChange(fn)
        if type(fn) == "function" then tinsert(ns.hui.__themeListeners, fn) end
    end

    local function Paint(tex, color)
        tex:SetVertexColor(color[1], color[2], color[3])
        tex:SetAlpha(color[4] or 1)
    end

    local function Mul(c, k)
        return { math.min(1, c[1] * k), math.min(1, c[2] * k), math.min(1, c[3] * k), 1 }
    end

    local function Blend(a, b, t)
        return { a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t, a[3] + (b[3] - a[3]) * t, 1 }
    end

    local function GradCapsule(pieces, gradFn, base)
        if not pieces or not gradFn then return end
        local top, bot = gradFn(base or pieces.__huiBaseCap)
        if not top or not bot then return end
        local f = pieces.__huiFrame
        local cs = pieces.__huiCorner or 6
        local h = (f and f.GetHeight and f:GetHeight()) or 0
        local k = (h > cs * 2) and (cs / h) or 0.25
        for i = 1, 7 do
            local tex = pieces[i]
            if tex then
                local y0, y1
                if i == 3 or i == 4 or i == 6 then
                    y0, y1 = 1 - k, 1
                elseif i == 7 then
                    y0, y1 = k, 1 - k
                else
                    y0, y1 = 0, k
                end
                local c0 = Blend(top, bot, y0)
                local c1 = Blend(top, bot, y1)
                tex:SetGradient("VERTICAL", CreateColor(c1[1], c1[2], c1[3]), CreateColor(c0[1], c0[2], c0[3]))
                tex:SetAlpha(1)
            end
        end
    end

    local function GradNorm(base)
        return Mul(base, 1.18), Mul(base, 0.77)
    end

    local function GradHover(base)
        return Mul(base, 1.16), Mul(base, 0.79)
    end

    local function GradPress(base)
        return Mul(base, 0.84), Mul(base, 0.57)
    end

    local function GradSel()
        local mix = Blend(ns.hui.layer.L2, ns.hui.layer.ACCENT, 0.28)
        return Mul(mix, 1.17), Mul(mix, 0.86)
    end

    local function ButtonBase(bt)
        return ns.hui.layer[bt.__huiBaseLv or "L2"] or ns.hui.layer.L2
    end

    local function SetRing(bt, k)
        local ring = bt.__ring
        local cov = bt.__ringCover
        if not ring and not cov then return end
        local c = type(k) == "table" and k or Mul(C_CTRL_BORDER, k)
        if ring then
            for _, tex in ipairs(ring) do
                tex:SetVertexColor(c[1], c[2], c[3])
            end
        end
        if cov then
            for _, tex in ipairs(cov) do
                tex:SetVertexColor(c[1], c[2], c[3])
            end
        end
    end

    local function SetVeil(bt, on)
        local veil = bt.__huiVeil
        if not veil then return end
        for _, tex in ipairs(veil) do tex:SetShown(on) end
    end

    local function ShiftContent(bt, dy)
        if dy < 0 then
            if bt.__huiPressShift then return end
            local snap = {}
            bt.__huiPressShift = snap
            for _, r in ipairs({ bt:GetRegions() }) do
                if not r.__huiPiece and not r.__huiCap and not r.__huiBorderStrip then
                    local n = r:GetNumPoints() or 0
                    if n > 0 and n < 2 and (r.GetObjectType and r:GetObjectType() ~= "FontString") then
                        local p, rel, rp, x, y = r:GetPoint(1)
                        snap[r] = { p, rel, rp, x, y }
                        r:ClearAllPoints()
                        r:SetPoint(p, rel, rp, x, y + dy)
                    end
                end
            end
        else
            local snap = bt.__huiPressShift
            if not snap then return end
            for r, q in pairs(snap) do
                r:ClearAllPoints()
                r:SetPoint(q[1], q[2], q[3], q[4], q[5])
            end
            bt.__huiPressShift = nil
        end
    end

    local function PaintState(bt)
        if not bt or not bt.__huiAction or not bt.__huiCap or bt.__huiFrameless then return end
        if not bt:IsEnabled() then
            GradCapsule(bt.__huiCap, GradNorm, ButtonBase(bt))
            SetRing(bt, 1.00)
            SetVeil(bt, false)
            return
        end
        if bt.__huiPress then
            GradCapsule(bt.__huiCap, GradPress, ButtonBase(bt))
            SetRing(bt, 1.50)
            SetVeil(bt, true)
            return
        end
        SetVeil(bt, false)
        if bt.__huiSelected then
            if bt.__huiKind == "ghost" then
                GradCapsule(bt.__huiCap, GradNorm, ButtonBase(bt))
                SetRing(bt, 1.25)
            elseif bt.__huiKind == "tab" then
                GradCapsule(bt.__huiCap, GradSel, ButtonBase(bt))
                SetRing(bt, ns.hui.ACCENT)
            else
                GradCapsule(bt.__huiCap, GradSel, ButtonBase(bt))
                SetRing(bt, ns.hui.ACCENT)
            end
            return
        end
        if bt.__huiHover then
            GradCapsule(bt.__huiCap, GradHover, ButtonBase(bt))
            SetRing(bt, 1.25)
            return
        end
        GradCapsule(bt.__huiCap, GradNorm, ButtonBase(bt))
        SetRing(bt, 1.00)
    end

    local function BuildCapsule(f, cornerSize, color, inset, sub, gradFn)
        local ins = inset or 0
        local sl = sub or 0

        local snapR = SnapCornerR(cornerSize)
        local cornerTex = GLASS_FILL_TEX .. snapR
        local tl = f:CreateTexture(nil, "BACKGROUND", nil, sl)
        tl:SetTexture(cornerTex)
        tl:SetTexCoord(CornerQuadUV("TOPLEFT", snapR))
        tl:SetSize(cornerSize, cornerSize)
        tl:SetPoint("TOPLEFT", f, "TOPLEFT", ins, -ins)
        Paint(tl, color)

        local tr = f:CreateTexture(nil, "BACKGROUND", nil, sl)
        tr:SetTexture(cornerTex)
        tr:SetTexCoord(CornerQuadUV("TOPRIGHT", snapR))
        tr:SetSize(cornerSize, cornerSize)
        tr:SetPoint("TOPRIGHT", f, "TOPRIGHT", -ins, -ins)
        Paint(tr, color)

        local bl = f:CreateTexture(nil, "BACKGROUND", nil, sl)
        bl:SetTexture(cornerTex)
        bl:SetTexCoord(CornerQuadUV("BOTTOMLEFT", snapR))
        bl:SetSize(cornerSize, cornerSize)
        bl:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", ins, ins)
        Paint(bl, color)

        local br = f:CreateTexture(nil, "BACKGROUND", nil, sl)
        br:SetTexture(cornerTex)
        br:SetTexCoord(CornerQuadUV("BOTTOMRIGHT", snapR))
        br:SetSize(cornerSize, cornerSize)
        br:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -ins, ins)
        Paint(br, color)

        local top = f:CreateTexture(nil, "BACKGROUND", nil, sl)
        top:SetTexture("Interface/Buttons/WHITE8X8")
        Paint(top, color)
        top:SetPoint("TOPLEFT", f, "TOPLEFT", cornerSize + ins, -ins)
        top:SetPoint("BOTTOMRIGHT", f, "TOPRIGHT", -cornerSize - ins, -cornerSize - ins)
        local bottom = f:CreateTexture(nil, "BACKGROUND", nil, sl)
        bottom:SetTexture("Interface/Buttons/WHITE8X8")
        Paint(bottom, color)
        bottom:SetPoint("TOPLEFT", f, "BOTTOMLEFT", cornerSize + ins, cornerSize + ins)
        bottom:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -cornerSize - ins, ins)
        local mid = f:CreateTexture(nil, "BACKGROUND", nil, sl)
        mid:SetTexture("Interface/Buttons/WHITE8X8")
        Paint(mid, color)
        mid:SetPoint("TOPLEFT", f, "TOPLEFT", ins, -cornerSize - ins)
        mid:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -ins, cornerSize + ins)

        local pieces = {tl, tr, bl, br, top, bottom, mid}
        if gradFn then
            mid.__huiCap = true
            pieces.__huiBaseCap = color
            pieces.__huiGrad = gradFn
            pieces.__huiFrame = f
            pieces.__huiCorner = cornerSize
            GradCapsule(pieces, gradFn)
        end
        ns.hui.AddRepaint(f, function()
            if pieces.__huiRepaint then
                pieces.__huiRepaint()
                return
            end
            if pieces.__huiGrad then
                GradCapsule(pieces, pieces.__huiGrad)
            else
                for _, tex in ipairs(pieces) do
                    tex:SetVertexColor(color[1], color[2], color[3])
                    tex:SetAlpha(color[4] or 1)
                end
            end
        end)
        return pieces
    end

    local pixelStrips = setmetatable({}, { __mode = "k" })
    local pixelShowHooks = setmetatable({}, { __mode = "k" })
    local stripRepN, stripRepMs, stripScanN, stripRegN = 0, 0, 0, 0
    ns.hui.__stripStat = function() return stripRepN, stripRepMs, stripScanN, stripRegN end
    local function huiNow()
        if type(debugprofilestop) == "function" then return debugprofilestop() end
        if type(GetTime) == "function" then return GetTime() * 1000 end
        return 0
    end
    local function PixelStripSize(f)
        local ok, _, h = pcall(GetPhysicalScreenSize)
        if not ok or not h or h <= 0 then return 1 end
        local k = (f and f.GetEffectiveScale and f:GetEffectiveScale() or 1) * h / 768
        if not k or k <= 0 then return 1 end
        return math.max(1, math.floor(k + 0.5)) / k
    end
    local stripsApplying = false
    local function ReapplyStripPixelsBody(frame)
        if frame then
            local list = frame.__huiStrips
            if list then
                local s, n = PixelStripSize(frame), #list
                stripScanN = stripScanN + n
                for i = 1, n do
                    local tex = list[i]
                    if tex:GetParent() == frame then
                        if tex.__huiStripAxis == "h" then tex:SetHeight(s) else tex:SetWidth(s) end
                    end
                end
                return
            end
        end
        local cnt = 0
        for tex in pairs(pixelStrips) do
            cnt = cnt + 1
            local p = tex:GetParent()
            if p and (not frame or p == frame) then
                local s = PixelStripSize(p)
                if tex.__huiStripAxis == "h" then tex:SetHeight(s) else tex:SetWidth(s) end
            end
        end
        stripScanN = stripScanN + cnt
    end
    local function ReapplyStripPixels(frame)
        if stripsApplying then return end
        stripsApplying = true
        local t0 = huiNow()
        pcall(ReapplyStripPixelsBody, frame)
        stripRepMs = stripRepMs + (huiNow() - t0)
        stripRepN = stripRepN + 1
        stripsApplying = false
    end
    local function RegisterPixelStrip(tex, axis)
        tex.__huiStripAxis = axis
        pixelStrips[tex] = true
        stripRegN = stripRegN + 1
        local p = tex:GetParent()
        if p then
            local list = p.__huiStrips
            if not list then list = {}; p.__huiStrips = list end
            list[#list + 1] = tex
            local s = PixelStripSize(p)
            if axis == "h" then tex:SetHeight(s) else tex:SetWidth(s) end
            if not pixelShowHooks[p] then
                pixelShowHooks[p] = true
                p:HookScript("OnShow", function(self) ReapplyStripPixels(self) end)
            end
        end
    end
    do
        local ev = CreateFrame("Frame")
        ev:RegisterEvent("PLAYER_LOGIN")
        ev:SetScript("OnEvent", function()
            C_Timer.After(0, function() ReapplyStripPixels(nil) end)
        end)
        pcall(function() ev:RegisterEvent("UI_SCALE_CHANGED") end)
    end
    local BORDER_UV = {
        TOPLEFT     = { 0, 0,  0, 1,  1, 0,  1, 1 },
        TOPRIGHT    = { 1, 0,  1, 1,  0, 0,  0, 1 },
        BOTTOMLEFT  = { 0, 1,  0, 0,  1, 1,  1, 0 },
        BOTTOMRIGHT = { 1, 1,  1, 0,  0, 1,  0, 0 },
    }
    local function DrawRoundBorder(f, r, color, owner, layer, rounding, thickness, fillColor, outside, outExtra, expand)
        local ex = expand or 0
        local p = owner or f
        local alpha = color[4] or 1
        local thick = thickness or 1
        local ext = thick + (outside and (outExtra or 0) or 0)
        local shift = (outside and ext or 0) + ex
        local snapR = SnapCornerR(r)
        local pieces = {}
        local covers = {}
        local sL = not rounding or rounding == "both" or rounding == "left"
        local sR = not rounding or rounding == "both" or rounding == "right"
        local sT = rounding == "top"
        local sB = rounding == "bottom"
        local arcTL = sL or sT
        local arcTR = sR or sT
        local arcBL = sL or sB
        local arcBR = sR or sB
        local function tint(t)
            t:SetVertexColor(color[1], color[2], color[3])
            t:SetAlpha(alpha)
            pieces[#pieces + 1] = t
            return t
        end
        if thick <= 1 then
            local file = GLASS_RING_TEX .. snapR
            local q = snapR / 32
            local function corner(point)
                local t = p:CreateTexture(nil, layer or "BORDER")
                t:SetTexture(file)
                t:SetTexCoord(CornerQuadUV(point, snapR))
                t:SetSize(r, r)
                t:SetPoint(point, f, point,
                        (point:find("LEFT") and -1 or 1) * shift,
                        (point:find("TOP") and 1 or -1) * shift)
                return tint(t)
            end
            local cTL = arcTL and corner("TOPLEFT") or nil
            local cTR = arcTR and corner("TOPRIGHT") or nil
            local cBL = arcBL and corner("BOTTOMLEFT") or nil
            local cBR = arcBR and corner("BOTTOMRIGHT") or nil
            local function edgeH(top)
                local t = p:CreateTexture(nil, layer or "BORDER")
                t:SetTexture(file)
                t:SetHeight(r)
                local vp = top and "TOP" or "BOTTOM"
                local v0 = top and 0 or (1 - q)
                t:SetTexCoord(q, v0, q, v0 + q, 1 - q, v0, 1 - q, v0 + q)
                local hasL = top and arcTL or arcBL
                local hasR = top and arcTR or arcBR
                local cl = top and cTL or cBL
                local cr = top and cTR or cBR
                if hasL and cl then
                    t:SetPoint(vp .. "LEFT", cl, vp .. "RIGHT", 0, 0)
                else
                    t:SetPoint(vp .. "LEFT", f, vp .. "LEFT", 0, (top and 1 or -1) * shift)
                end
                if hasR and cr then
                    t:SetPoint(vp .. "RIGHT", cr, vp .. "LEFT", 0, 0)
                else
                    t:SetPoint(vp .. "RIGHT", f, vp .. "RIGHT", 0, (top and 1 or -1) * shift)
                end
                return tint(t)
            end
            local function edgeV(left)
                local t = p:CreateTexture(nil, layer or "BORDER")
                t:SetTexture(file)
                t:SetWidth(r)
                local hp = left and "LEFT" or "RIGHT"
                local u0 = left and 0 or (1 - q)
                t:SetTexCoord(u0, q, u0, 1 - q, u0 + q, q, u0 + q, 1 - q)
                local hasT = left and arcTL or arcTR
                local hasB = left and arcBL or arcBR
                local ct = left and cTL or cTR
                local cb = left and cBL or cBR
                if hasT and ct then
                    t:SetPoint("TOP" .. hp, ct, "BOTTOM" .. hp, 0, 0)
                else
                    t:SetPoint("TOP" .. hp, f, "TOP" .. hp, (left and -1 or 1) * shift, 0)
                end
                if hasB and cb then
                    t:SetPoint("BOTTOM" .. hp, cb, "TOP" .. hp, 0, 0)
                else
                    t:SetPoint("BOTTOM" .. hp, f, "BOTTOM" .. hp, (left and -1 or 1) * shift, 0)
                end
                return tint(t)
            end
            edgeH(true)
            edgeH(false)
            if sL or arcTL or arcBL then edgeV(true) end
            if sR or arcTR or arcBR then edgeV(false) end
            return pieces, covers
        end
        local function cornerThick(point)
            local insetSide = point:find("LEFT") and 1 or -1
            local insetVert = point:find("TOP") and -1 or 1
            local ox = -shift * insetSide
            local oy = -shift * insetVert
            local tex = GLASS_FILL_TEX .. snapR
            local outer = p:CreateTexture(nil, layer or "BORDER")
            outer:SetTexture(tex)
            outer:SetSize(r, r)
            outer:SetPoint(point, f, point, ox, oy)
            outer:SetTexCoord(CornerQuadUV(point, snapR))
            outer:SetVertexColor(color[1], color[2], color[3])
            outer:SetAlpha(alpha)
            pieces[#pieces + 1] = outer
            if r > thick then
                local inner = p:CreateTexture(nil, layer or "BORDER")
                inner:SetTexture(tex)
                inner:SetSize(r - thick, r - thick)
                inner:SetPoint(point, f, point, ox, oy)
                inner:SetTexCoord(CornerQuadUV(point, snapR))
                local fc = fillColor or color
                inner:SetVertexColor(fc[1], fc[2], fc[3])
                inner:SetAlpha(fc[4] or 1)
                covers[#covers + 1] = inner
            end
        end
        local arcInset = r - thick - (outside and (outExtra or 0) or 0) - ex
        local function hstrip(top)
            local t = p:CreateTexture(nil, layer or "BORDER")
            t:SetColorTexture(color[1], color[2], color[3], 1)
            t:SetAlpha(alpha)
            t.__huiBorderStrip = true
            local vp = top and "TOP" or "BOTTOM"
            local oy = (top and 1 or -1) * shift
            t:SetPoint(vp .. "LEFT", f, vp .. "LEFT", (top and arcTL or arcBL) and arcInset or 0, oy)
            t:SetPoint(vp .. "RIGHT", f, vp .. "RIGHT", (top and arcTR or arcBR) and -arcInset or 0, oy)
            t:SetHeight(thick)
            pieces[#pieces + 1] = t
        end
        local function vstrip(left)
            local t = p:CreateTexture(nil, layer or "BORDER")
            t:SetColorTexture(color[1], color[2], color[3], 1)
            t:SetAlpha(alpha)
            t.__huiBorderStrip = true
            local hp = left and "LEFT" or "RIGHT"
            local ox = (left and -1 or 1) * shift
            t:SetPoint("TOP" .. hp, f, "TOP" .. hp, ox, (left and arcTL or arcTR) and -arcInset or 0)
            t:SetPoint("BOTTOM" .. hp, f, "BOTTOM" .. hp, ox, (left and arcBL or arcBR) and arcInset or 0)
            t:SetWidth(thick)
            pieces[#pieces + 1] = t
        end
        if arcTL then cornerThick("TOPLEFT") end
        if arcTR then cornerThick("TOPRIGHT") end
        if arcBL then cornerThick("BOTTOMLEFT") end
        if arcBR then cornerThick("BOTTOMRIGHT") end
        hstrip(true)
        hstrip(false)
        if sL or arcTL or arcBL then vstrip(true) end
        if sR or arcTR or arcBR then vstrip(false) end
        return pieces, covers
    end

    local GLASS_SHADOW_TEX = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIBoxShadow"

    local function GlassZoneColor(c, zone)
        local a = c[4] or 1
        local r, g, b = c[1], c[2], c[3]
        local lum = (r + g + b) / 3
        if lum >= 0.85 and a < 0.9 then
            local ka = zone == "top" and 1.7 or zone == "bot" and 0.55 or 1.15
            return r, g, b, math.min(1, a * ka)
        end
        local k = zone == "top" and 0.05 or zone == "bot" and 0.012 or 0.028
        return r + (1 - r) * k, g + (1 - g) * k, b + (1 - b) * k, a
    end

    local function GlassPaint(tex)
        local g = tex.__huiGlass
        if not g then return end
        local c, zone = g.c, g.zone
        if zone == "grad" then
            tex:SetGradient("VERTICAL",
                CreateColor(GlassZoneColor(c, "bot")),
                CreateColor(GlassZoneColor(c, "top")))
            tex:SetAlpha(1)
        else
            local r, gg, b, a = GlassZoneColor(c, zone)
            tex:SetVertexColor(r, gg, b)
            tex:SetAlpha(a)
        end
    end

    function ns.hui.GlassPlate(f, color, zone)
        if not f or not f.CreateTexture then return nil end
        local tex = f:CreateTexture(nil, "BACKGROUND", nil, 1)
        tex:SetTexture("Interface/Buttons/WHITE8X8")
        tex:SetAllPoints()
        tex.__huiGlass = { c = color or ns.hui.layer.L2, zone = zone or "mid" }
        GlassPaint(tex)
        if ns.hui.AddRepaint then
            ns.hui.AddRepaint(f, function() GlassPaint(tex) end)
        end
        if ns.huiTheme == "hui" and ns.hui.IsMainUIFrame and ns.hui.IsMainUIFrame(f)
           and ns.hui.RegisterMainAlphaSurface then
            ns.hui.RegisterMainAlphaSurface(f, { tex })
        end
        return tex
    end

    local function BuildCardShadow(f, spread, alpha, sub, cr)
        if not f or not f.CreateTexture then return nil end
        spread = spread or 16
        cr = cr or 8
        local corner = spread + cr
        local fw, fh = f:GetWidth() or 0, f:GetHeight() or 0
        if (fw > 0 and fw < corner * 2) or (fh > 0 and fh < corner * 2) then return {} end
        local cUV = 0.375
        local coords = {
            { 0, cUV, 0, cUV }, { cUV, 1 - cUV, 0, cUV }, { 1 - cUV, 1, 0, cUV },
            { 0, cUV, cUV, 1 - cUV }, { cUV, 1 - cUV, cUV, 1 - cUV }, { 1 - cUV, 1, cUV, 1 - cUV },
            { 0, cUV, 1 - cUV, 1 }, { cUV, 1 - cUV, 1 - cUV, 1 }, { 1 - cUV, 1, 1 - cUV, 1 },
        }
        local pieces = {}
        for i = 1, 9 do
            local t = f:CreateTexture(nil, "BACKGROUND", nil, sub or -8)
            t:SetTexture(GLASS_SHADOW_TEX)
            t:SetTexCoord(unpack(coords[i]))
            t:SetVertexColor(0, 0, 0, 1)
            t:SetAlpha(alpha or 0.75)
            pieces[#pieces + 1] = t
        end
        local p = pieces
        p[1]:SetPoint("TOPLEFT", f, "TOPLEFT", -spread, spread)
        p[3]:SetPoint("TOPRIGHT", f, "TOPRIGHT", spread, spread)
        p[7]:SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", -spread, -spread)
        p[9]:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", spread, -spread)
        for _, i in ipairs({ 1, 3, 7, 9 }) do p[i]:SetSize(corner, corner) end
        p[2]:SetPoint("TOPLEFT", p[1], "TOPRIGHT")
        p[2]:SetPoint("BOTTOMRIGHT", p[3], "BOTTOMLEFT")
        p[8]:SetPoint("TOPLEFT", p[7], "TOPRIGHT")
        p[8]:SetPoint("BOTTOMRIGHT", p[9], "BOTTOMLEFT")
        p[4]:SetPoint("TOPLEFT", p[1], "BOTTOMLEFT")
        p[4]:SetPoint("BOTTOMRIGHT", p[7], "TOPRIGHT")
        p[6]:SetPoint("TOPLEFT", p[3], "BOTTOMLEFT")
        p[6]:SetPoint("BOTTOMRIGHT", p[9], "TOPRIGHT")
        p[5]:SetPoint("TOPLEFT", p[1], "BOTTOMRIGHT")
        p[5]:SetPoint("BOTTOMRIGHT", p[9], "TOPLEFT")
        return pieces
    end

    local function BuildRoundedBG(f, cr, color, rounding, withBorder, borderThickness, noRepaint, borderOutside, borderOutExtra, expand)
        local e = expand or 0
        if color == nil then color = ns.hui.layer.L1
        elseif sameGray(color, L0_GRAY) then color = ns.hui.layer.L0
        elseif sameGray(color, L1_GRAY) then color = ns.hui.layer.L1
        elseif sameGray(color, L2_GRAY) or sameGray(color, L2_GRAY095) then color = ns.hui.layer.L2
        elseif sameGray(color, L3_GRAY) then color = ns.hui.layer.L3 end
        local sL = not rounding or rounding == "both" or rounding == "left"
        local sR = not rounding or rounding == "both" or rounding == "right"
        local sT = rounding == "top"
        local sB = rounding == "bottom"
        local arcTL = sL or sT
        local arcTR = sR or sT
        local arcBL = sL or sB
        local arcBR = sR or sB
        local pieces = {}
        local function add(texPath, w, h, zone)
            local tex = f:CreateTexture(nil, "BACKGROUND", nil, 1)
            tex:SetTexture(texPath)
            tex:SetSize(w or cr, h or cr)
            tex.__huiGlass = { c = color, zone = zone or "mid" }
            GlassPaint(tex)
            pieces[#pieces + 1] = tex
            return tex
        end
        local snapR = SnapCornerR(cr)
        local function addCorner(point, zone)
            local tex = add(GLASS_FILL_TEX .. snapR, nil, nil, zone)
            tex:SetTexCoord(CornerQuadUV(point, snapR))
            return tex
        end
        if arcTL then addCorner("TOPLEFT", "top"):SetPoint("TOPLEFT", f, "TOPLEFT", -e, e) end
        if arcTR then addCorner("TOPRIGHT", "top"):SetPoint("TOPRIGHT", f, "TOPRIGHT", e, e) end
        if arcBL then addCorner("BOTTOMLEFT", "bot"):SetPoint("BOTTOMLEFT", f, "BOTTOMLEFT", -e, -e) end
        if arcBR then addCorner("BOTTOMRIGHT", "bot"):SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", e, -e) end
        if arcTL or arcTR then
            local ts = add("Interface/Buttons/WHITE8X8", nil, nil, "top")
            ts:SetPoint("TOPLEFT", f, "TOPLEFT", (arcTL and cr or 0) - e, e)
            ts:SetPoint("BOTTOMRIGHT", f, "TOPRIGHT", (arcTR and -cr or 0) + e, -cr + e)
        end
        if arcBL or arcBR then
            local bs = add("Interface/Buttons/WHITE8X8", nil, nil, "bot")
            bs:SetPoint("TOPLEFT", f, "BOTTOMLEFT", (arcBL and cr or 0) - e, cr - e)
            bs:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", (arcBR and -cr or 0) + e, -e)
        end
        if arcTL or arcBL then
            local ls = add("Interface/Buttons/WHITE8X8", nil, nil, "grad")
            ls:SetPoint("TOPLEFT", f, "TOPLEFT", -e, (arcTL and -cr or 0) + e)
            ls:SetPoint("BOTTOMRIGHT", f, "BOTTOMLEFT", cr - e, (arcBL and cr or 0) - e)
        end
        if arcTR or arcBR then
            local rs = add("Interface/Buttons/WHITE8X8", nil, nil, "grad")
            rs:SetPoint("TOPRIGHT", f, "TOPRIGHT", e, (arcTR and -cr or 0) + e)
            rs:SetPoint("BOTTOMLEFT", f, "BOTTOMRIGHT", -cr + e, (arcBR and cr or 0) - e)
        end
        local insetL = (arcTL or arcBL) and cr or 0
        local insetR = (arcTR or arcBR) and cr or 0
        local insetT = (arcTL or arcTR) and cr or 0
        local insetB = (arcBL or arcBR) and cr or 0
        local rect = add("Interface/Buttons/WHITE8X8", nil, nil, "grad")
        rect:SetPoint("TOPLEFT", f, "TOPLEFT", insetL - e, -insetT + e)
        rect:SetPoint("BOTTOMRIGHT", f, "BOTTOMRIGHT", -insetR + e, insetB - e)
        if not noRepaint then
            ns.hui.AddRepaint(f, function()
                for _, tex in ipairs(pieces) do
                    GlassPaint(tex)
                end
            end)
        end
        if not noRepaint and ns.huiTheme == "hui" and ns.hui.RegisterMainAlphaSurface and ns.hui.IsMainUIFrame(f) then
            ns.hui.RegisterMainAlphaSurface(f, pieces)
        end
        if withBorder then
            local border, covers = DrawRoundBorder(f, cr, C_CARD_BORDER, f, "BORDER", rounding, borderThickness, color, borderOutside, borderOutExtra, expand)
            return pieces, border, covers
        end
        return pieces
    end
    ns.hui.BuildRoundedBG = BuildRoundedBG
    ns.hui.GlassZoneColor = GlassZoneColor
    ns.hui.BuildCardShadow = BuildCardShadow
    ns.hui.BuildCapsule = BuildCapsule
    ns.hui.GlassPaint = GlassPaint

    local ROW_SEL_TEX = "Interface\\AddOns\\DungeonsForever\\Media\\DF_RowSelGrad"

    function ns.hui.PaintRowSelect(f, on)
        if not f or not f.__huiCard then return false end
        local t = f.__huiRowSelTex
        if not t then
            t = f:CreateTexture(nil, "BACKGROUND", nil, 1)
            t:SetTexture(ROW_SEL_TEX)
            t:SetAllPoints()
            t:Hide()
            f.__huiRowSelTex = t
        end
        on = on and true or false
        t:SetShown(on)
        if on then
            local ac = ns.hui.ACCENT
            t:SetVertexColor(ac[1], ac[2], ac[3], 1)
        end
        local bp = f.__huiCard
        if bp.border then
            local c = on and ns.hui.ACCENT or C_CARD_BORDER
            local a = on and 0.95 or (C_CARD_BORDER[4] or 1)
            for _, tex in ipairs(bp.border) do
                tex:SetVertexColor(c[1], c[2], c[3])
                tex:SetAlpha(a)
            end
        end
        return true
    end

    function ns.hui.GetMainAlpha()
        local v = tonumber(ns.options and ns.options.huiAlpha)
        if not v or v < 0 or v > 1 then v = 0.95 end
        return v
    end

    function ns.hui.MainAlphaK()
        if ns.huiTheme ~= "hui" then return 1 end
        return ns.hui.GetMainAlpha() / 0.95
    end

    local mainAlphaSurfaces = {}

    function ns.hui.IsMainUIFrame(f)
        if not f then return false end
        local main = ns.MainFrame
        if not main then return false end
        local cur = f
        while cur do
            if cur == main then return true end
            if cur == ns.auctionLogFrame or cur == ns.itemGuoQiFrame then return true end
            cur = cur:GetParent()
        end
        return false
    end

    function ns.hui.ApplyMainAlpha()
        local k = ns.hui.GetMainAlpha() / 0.95
        for _, entry in pairs(mainAlphaSurfaces) do
            for _, pieces in ipairs(entry.pieces) do
                for _, tex in ipairs(pieces) do
                    tex:SetAlpha((tex.__huiMainBaseA or 1) * k)
                end
            end
            for _, fn in ipairs(entry.multipliers or {}) do
                fn(k)
            end
        end
    end

    function ns.hui.RegisterMainAlphaSurface(frame, pieces)
        if not frame or not pieces or not ns.hui.AddRepaint then return end
        local entry = mainAlphaSurfaces[frame]
        if not entry then
            entry = { pieces = {}, multipliers = {} }
            mainAlphaSurfaces[frame] = entry
            function entry.Reassert()
                local k = ns.hui.GetMainAlpha() / 0.95
                for _, pl in ipairs(entry.pieces) do
                    for _, tex in ipairs(pl) do
                        tex:SetAlpha((tex.__huiMainBaseA or 1) * k)
                    end
                end
                for _, fn in ipairs(entry.multipliers) do
                    fn(k)
                end
            end
            ns.hui.AddRepaint(frame, entry.Reassert)
            frame:HookScript("OnShow", entry.Reassert)
        end
        entry.pieces[#entry.pieces + 1] = pieces
        for _, tex in ipairs(pieces) do
            if not tex.__huiMainBaseA then
                tex.__huiMainBaseA = tex:GetAlpha() or 1
            end
        end
        entry.Reassert()
    end

    function ns.hui.RegisterMainAlphaMultiplier(frame, fn)
        if not frame or not fn then return end
        local entry = mainAlphaSurfaces[frame]
        if not entry then
            entry = { pieces = {}, multipliers = {} }
            mainAlphaSurfaces[frame] = entry
            function entry.Reassert()
                local k = ns.hui.GetMainAlpha() / 0.95
                for _, pl in ipairs(entry.pieces) do
                    for _, tex in ipairs(pl) do
                        tex:SetAlpha((tex.__huiMainBaseA or 1) * k)
                    end
                end
                for _, f2 in ipairs(entry.multipliers) do
                    f2(k)
                end
            end
            ns.hui.AddRepaint(frame, entry.Reassert)
            frame:HookScript("OnShow", entry.Reassert)
        end
        entry.multipliers[#entry.multipliers + 1] = fn
        entry.Reassert()
    end

    function ns.hui.SkinShadow(f, spread, alpha, cr)
        if not f or not f.CreateTexture then return nil end
        if f.__huiShadow then return f.__huiShadow end
        local pieces = BuildCardShadow(f, spread or 16, alpha or 0.65, -8, cr or 8)
        if not pieces then return nil end
        f.__huiShadow = pieces
        if ns.hui.RegisterMainAlphaSurface and ns.hui.IsMainUIFrame(f) then
            ns.hui.RegisterMainAlphaSurface(f, pieces)
        end
        return pieces
    end

    function ns.hui.SkinPopup(f, cr, rounding, color, borderThickness, noBorder, borderOutside, borderOutExtra, expand, noAlpha)
        if ns.huiTheme ~= "hui" or not f then return end
        color = color or ns.hui.layer.L1
        if sameGray(color, L1_GRAY) then color = ns.hui.layer.L1
        elseif sameGray(color, L2_GRAY) or sameGray(color, L2_GRAY095) then color = ns.hui.layer.L2
        elseif sameGray(color, L3_GRAY) then color = ns.hui.layer.L3 end
        if f.SetBackdropColor then
            f:SetBackdropColor(0, 0, 0, 0)
        end
        if f.SetBackdropBorderColor then
            f:SetBackdropBorderColor(0, 0, 0, 0)
        end
        local pieces, borderPieces, coverPieces = BuildRoundedBG(f, cr or 8, color, rounding or "both", not noBorder, borderThickness, nil, borderOutside, borderOutExtra, expand)
        f.__huiBorderPieces = borderPieces
        local shadowPieces
        if f:GetParent() == UIParent then
            shadowPieces = ns.hui.SkinShadow(f, nil, nil, cr or 8)
        end
        local function repaintFill()
            for _, tex in ipairs(pieces) do
                tex:SetShown(true)
                GlassPaint(tex)
            end
            for _, tex in ipairs(coverPieces or {}) do
                tex:SetShown(true)
                tex:SetVertexColor(color[1], color[2], color[3])
                tex:SetAlpha(color[4])
            end
        end
        local function repaintBorder()
            if not borderPieces then return end
            for _, tex in ipairs(borderPieces) do
                tex:SetShown(true)
                tex:SetVertexColor(C_CARD_BORDER[1], C_CARD_BORDER[2], C_CARD_BORDER[3])
                tex:SetAlpha(C_CARD_BORDER[4])
            end
        end
        ns.hui.AddRepaint(f, repaintFill)
        ns.hui.AddRepaint(f, repaintBorder)
        f:HookScript("OnShow", function(frame)
            repaintFill()
            repaintBorder()
        end)
        if not noAlpha and ns.hui.RegisterMainAlphaSurface then
            local reg = { unpack(pieces) }
            for _, tex in ipairs(coverPieces or {}) do
                reg[#reg + 1] = tex
            end
            for _, tex in ipairs(shadowPieces or {}) do
                reg[#reg + 1] = tex
            end
            ns.hui.RegisterMainAlphaSurface(f, reg)
            local entry = mainAlphaSurfaces[f]
            if entry then
                tinsert(f.__huiRepaints, entry.Reassert)
                f:HookScript("OnShow", entry.Reassert)
            end
        end
        return pieces
    end

    local menuPopup = nil
    local menuOwner = nil

    local function HideDFMenu()
        if menuPopup then
            menuPopup:Hide()
            menuPopup:SetParent(nil)
        end
        menuPopup = nil
        menuOwner = nil
    end

    local function MenuParseColor(c)
        if type(c) == "table" and c[1] then
            return c[1], c[2], c[3], c[4] or 1
        end
        if type(c) == "string" and #c >= 10 and c:sub(1, 2) == "|c" then
            local r = tonumber(c:sub(5, 6), 16)
            local g = tonumber(c:sub(7, 8), 16)
            local b = tonumber(c:sub(9, 10), 16)
            if r and g and b then
                return r / 255, g / 255, b / 255, 1
            end
        end
        return nil
    end

    local MENU_EV = CreateFrame("Frame", nil, UIParent)
    MENU_EV:Hide()
    MENU_EV:RegisterEvent("GLOBAL_MOUSE_DOWN")
    MENU_EV:SetScript("OnEvent", function()
        if not (menuPopup and menuPopup:IsShown()) then return end
        if menuPopup:IsMouseOver() then return end
        if menuOwner and menuOwner.IsMouseOver and menuOwner:IsMouseOver() then return end
        HideDFMenu()
    end)

    function ns.hui.HideDFMenu()
        HideDFMenu()
    end

    function ns.hui.ShowMenu(items, opts)
        if type(items) ~= "table" or #items == 0 then return end
        opts = opts or {}
        if menuPopup and menuPopup:IsShown() and opts.owner and opts.owner == menuOwner then
            HideDFMenu()
            return
        end
        if menuPopup then
            menuPopup:Hide()
            menuPopup:SetParent(nil)
            menuPopup = nil
        end
        menuOwner = opts.owner

        local popup = CreateFrame("Frame", nil, UIParent)
        popup:SetFrameStrata("FULLSCREEN_DIALOG")
        popup:SetToplevel(true)
        popup:SetClampedToScreen(true)
        popup:EnableMouse(true)
        menuPopup = popup

        local rowH = 24
        local fsSz = tonumber(opts.fs) or 14
        if fsSz < 14 then fsSz = 14 end
        local padX = 12
        local iconSz = 18
        local iconGap = 6
        local chkSz = 16
        local chkGap = 7
        local measure = popup:CreateFontString(nil, "OVERLAY")
        measure:SetFont(ns.FONT, fsSz, "")
        local maxW = 0
        for i = 1, #items do
            local it = items[i]
            measure:SetText(it.text or "")
            local w = measure:GetStringWidth() + padX * 2
            if it.icon then w = w + iconSz + iconGap end
            if it.checked ~= nil then w = w + chkSz + chkGap end
            if w > maxW then maxW = w end
        end
        maxW = math.max(120, math.min(maxW + 6, 360))
        popup:SetSize(maxW, #items * rowH + 2)

        local L5 = ns.hui.layer.L5
        for i = 1, #items do
            local it = items[i]
            local row = CreateFrame("Button", nil, popup)
            row:SetSize(maxW - 2, rowH)
            row:SetPoint("TOPLEFT", popup, "TOPLEFT", 1, -1 - (i - 1) * rowH)
            local hl = row:CreateTexture(nil, "BACKGROUND")
            hl:SetAllPoints()
            hl:SetColorTexture(0, 0, 0, 0)
            row:SetScript("OnEnter", function()
                hl:SetColorTexture(L5[1], L5[2], L5[3], 1)
            end)
            row:SetScript("OnLeave", function()
                hl:SetColorTexture(0, 0, 0, 0)
            end)
            local tx = padX
            if it.checked ~= nil then
                local on = it.checked and true or false
                local ring = row:CreateTexture(nil, "ARTWORK")
                ring:SetSize(chkSz, chkSz)
                ring:SetPoint("LEFT", row, "LEFT", padX, 0)
                ring:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckRing")
                local disc = row:CreateTexture(nil, "ARTWORK")
                disc:SetSize(chkSz, chkSz)
                disc:SetPoint("LEFT", row, "LEFT", padX, 0)
                disc:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckDisc")
                local tick = row:CreateTexture(nil, "OVERLAY")
                tick:SetSize(chkSz, chkSz)
                tick:SetPoint("LEFT", row, "LEFT", padX, 0)
                tick:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\CheckMark")
                ring:SetShown(not on)
                disc:SetShown(on)
                tick:SetShown(on)
                if on then
                    disc:SetVertexColor(0.91, 0.78, 0.42)
                    tick:SetVertexColor(1, 1, 1, 1)
                else
                    ring:SetVertexColor(0.42, 0.41, 0.38, 0.9)
                end
                tx = padX + chkSz + chkGap
            end
            if it.icon then
                local ic = row:CreateTexture(nil, "ARTWORK")
                ic:SetSize(iconSz, iconSz)
                ic:SetPoint("LEFT", row, "LEFT", padX, 0)
                ic:SetTexture(it.icon)
                tx = padX + iconSz + iconGap
            end
            local fs = row:CreateFontString(nil, "OVERLAY")
            fs:SetPoint("LEFT", row, "LEFT", tx, 0)
            fs:SetFont(ns.FONT, fsSz, "")
            fs:SetJustifyH("LEFT")
            fs:SetText(it.text or "")
            local cr, cg, cb, ca = MenuParseColor(it.color)
            if not cr then
                cr, cg, cb = ns.hui.TextColor(nil, 1)
                ca = 1
            end
            if it.checked == false then
                cr, cg, cb, ca = 0.55, 0.58, 0.65, 1
            end
            fs:SetTextColor(cr, cg, cb, ca)
            local fn = it.func
            row:SetScript("OnClick", function()
                HideDFMenu()
                if type(fn) == "function" then fn() end
            end)
        end

        ns.hui.SkinPopup(popup, 8, "both", ns.hui.layer.L0)

        local scale = UIParent:GetEffectiveScale()
        if opts.anchor and opts.anchor.IsObjectType and opts.anchor:IsObjectType("Frame") then
            popup:ClearAllPoints()
            popup:SetPoint("TOPLEFT", opts.anchor, "BOTTOMLEFT", 0, -4)
        else
            local cx, cy = GetCursorPosition()
            popup:ClearAllPoints()
            popup:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", cx / scale + 2, cy / scale - 4)
        end
        popup:Show()
    end

    function ns.hui.AttachContentPanel(page, anchor, topInset, bottomInset, sideInset)
        if not page or not anchor then return end
        local s = sideInset or 6
        local t = topInset or 32
        local b = bottomInset or 26
        local cr = 8
        local L1 = ns.hui.layer.L1
        local function tex(path)
            local x = page:CreateTexture(nil, "BACKGROUND", nil, -8)
            x:SetTexture(path)
            x:SetSize(cr, cr)
            return x
        end
        local tl = tex(HUI_CORNER_TL)
        tl:SetPoint("TOPLEFT", anchor, "TOPLEFT", s, -t)
        local tr = tex(HUI_CORNER_TR)
        tr:SetPoint("TOPRIGHT", anchor, "TOPRIGHT", -s, -t)
        local bl = tex(HUI_CORNER_BL)
        bl:SetPoint("BOTTOMLEFT", anchor, "BOTTOMLEFT", s, b)
        local br = tex(HUI_CORNER_BR)
        br:SetPoint("BOTTOMRIGHT", anchor, "BOTTOMRIGHT", -s, b)
        local ls = tex("Interface/Buttons/WHITE8X8")
        ls:SetPoint("TOPLEFT", anchor, "TOPLEFT", s, -t - cr)
        ls:SetPoint("BOTTOMRIGHT", anchor, "BOTTOMLEFT", s + cr, b + cr)
        local rs = tex("Interface/Buttons/WHITE8X8")
        rs:SetPoint("TOPRIGHT", anchor, "TOPRIGHT", -s, -t - cr)
        rs:SetPoint("BOTTOMLEFT", anchor, "BOTTOMRIGHT", -s - cr, b + cr)
        local mid = tex("Interface/Buttons/WHITE8X8")
        mid:SetPoint("TOPLEFT", anchor, "TOPLEFT", s + cr, -t)
        mid:SetPoint("BOTTOMRIGHT", anchor, "BOTTOMRIGHT", -s - cr, b)
        Paint(tl, L1)
        Paint(tr, L1)
        Paint(bl, L1)
        Paint(br, L1)
        Paint(ls, L1)
        Paint(rs, L1)
        Paint(mid, L1)

        local l1texs = {tl, tr, bl, br, ls, rs, mid}
        ns.hui.AddRepaint(page, function()
            for _, tex in ipairs(l1texs) do Paint(tex, ns.hui.layer.L1) end
        end)

        ns.hui.RegisterMainAlphaSurface(page, l1texs)

        local BC = "Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundCorner"
        local function btex(path, w, h)
            local x = page:CreateTexture(nil, "BORDER", nil, -8)
            x:SetTexture(path)
            if w then x:SetSize(w, h) end
            x:SetVertexColor(C_CARD_BORDER[1], C_CARD_BORDER[2], C_CARD_BORDER[3])
            x:SetAlpha(C_CARD_BORDER[4])
            return x
        end
        local bcorners = {
            { "TOPLEFT",     s, -t },
            { "TOPRIGHT",   -s, -t },
            { "BOTTOMLEFT",  s,  b },
            { "BOTTOMRIGHT", -s,  b },
        }
        for _, c in ipairs(bcorners) do
            local x = btex(BC, cr, cr)
            x:SetPoint(c[1], anchor, c[1], c[2], c[3])
            local uv = BORDER_UV[c[1]]
            x:SetTexCoord(uv[1], uv[2], uv[3], uv[4], uv[5], uv[6], uv[7], uv[8])
        end
        local x = btex("Interface/Buttons/WHITE8X8")
        x:SetPoint("TOPLEFT", anchor, "TOPLEFT", s + cr - 1, -t)
        x:SetPoint("TOPRIGHT", anchor, "TOPRIGHT", -s - cr + 1, -t)
        RegisterPixelStrip(x, "h")
        x = btex("Interface/Buttons/WHITE8X8")
        x:SetPoint("BOTTOMLEFT", anchor, "BOTTOMLEFT", s + cr - 1, b)
        x:SetPoint("BOTTOMRIGHT", anchor, "BOTTOMRIGHT", -s - cr + 1, b)
        RegisterPixelStrip(x, "h")
        x = btex("Interface/Buttons/WHITE8X8")
        x:SetPoint("TOPLEFT", anchor, "TOPLEFT", s, -t - cr + 1)
        x:SetPoint("BOTTOMLEFT", anchor, "BOTTOMLEFT", s, b + cr - 1)
        RegisterPixelStrip(x, "w")
        x = btex("Interface/Buttons/WHITE8X8")
        x:SetPoint("TOPRIGHT", anchor, "TOPRIGHT", -s, -t - cr + 1)
        x:SetPoint("BOTTOMRIGHT", anchor, "BOTTOMRIGHT", -s, b + cr - 1)
        RegisterPixelStrip(x, "w")
    end

    function ns.hui.AttachBossCard(page, tlWidget, brWidget, l, t, r, b, cr, color, bottomWidget, topWidget)
        cr = cr or 6
        local L2 = color or ns.hui.layer.L2
        local bb = bottomWidget or brWidget
        local tt = topWidget or tlWidget
        local cardTexs = {}
        local x = page:CreateTexture(nil, "BACKGROUND", nil, -8)
        x:SetTexture(HUI_CORNER_TL)
        x:SetSize(cr, cr)
        x:SetPoint("LEFT", tlWidget, "LEFT", l, 0)
        x:SetPoint("TOP", tt, "TOP", 0, t)
        Paint(x, L2); cardTexs[#cardTexs + 1] = x
        x = page:CreateTexture(nil, "BACKGROUND", nil, -8)
        x:SetTexture(HUI_CORNER_TR)
        x:SetSize(cr, cr)
        x:SetPoint("RIGHT", brWidget, "RIGHT", r, 0)
        x:SetPoint("TOP", tt, "TOP", 0, t)
        Paint(x, L2); cardTexs[#cardTexs + 1] = x
        x = page:CreateTexture(nil, "BACKGROUND", nil, -8)
        x:SetTexture(HUI_CORNER_BL)
        x:SetSize(cr, cr)
        x:SetPoint("LEFT", tlWidget, "LEFT", l, 0)
        x:SetPoint("BOTTOM", bb, "BOTTOM", 0, b)
        Paint(x, L2); cardTexs[#cardTexs + 1] = x
        x = page:CreateTexture(nil, "BACKGROUND", nil, -8)
        x:SetTexture(HUI_CORNER_BR)
        x:SetSize(cr, cr)
        x:SetPoint("RIGHT", brWidget, "RIGHT", r, 0)
        x:SetPoint("BOTTOM", bb, "BOTTOM", 0, b)
        Paint(x, L2); cardTexs[#cardTexs + 1] = x
        x = page:CreateTexture(nil, "BACKGROUND", nil, -8)
        x:SetTexture("Interface/Buttons/WHITE8X8")
        x:SetPoint("LEFT", tlWidget, "LEFT", l, 0)
        x:SetPoint("TOP", tt, "TOP", 0, t - cr)
        x:SetPoint("BOTTOM", bb, "BOTTOM", 0, b + cr)
        Paint(x, L2); cardTexs[#cardTexs + 1] = x
        x = page:CreateTexture(nil, "BACKGROUND", nil, -8)
        x:SetTexture("Interface/Buttons/WHITE8X8")
        x:SetPoint("RIGHT", brWidget, "RIGHT", r, 0)
        x:SetPoint("TOP", tt, "TOP", 0, t - cr)
        x:SetPoint("BOTTOM", bb, "BOTTOM", 0, b + cr)
        Paint(x, L2); cardTexs[#cardTexs + 1] = x
        x = page:CreateTexture(nil, "BACKGROUND", nil, -8)
        x:SetTexture("Interface/Buttons/WHITE8X8")
        x:SetPoint("LEFT", tlWidget, "LEFT", l + cr, 0)
        x:SetPoint("RIGHT", brWidget, "RIGHT", r - cr, 0)
        x:SetPoint("TOP", tt, "TOP", 0, t)
        x:SetPoint("BOTTOM", bb, "BOTTOM", 0, b)
        Paint(x, L2); cardTexs[#cardTexs + 1] = x

        ns.hui.AddRepaint(page, function()
            for _, tex in ipairs(cardTexs) do Paint(tex, ns.hui.layer.L2) end
        end)

        ns.hui.RegisterMainAlphaSurface(page, cardTexs)

        local function btex(path)
            local bx = page:CreateTexture(nil, "BORDER", nil, -8)
            bx:SetTexture(path)
            bx:SetVertexColor(C_CARD_BORDER[1], C_CARD_BORDER[2], C_CARD_BORDER[3])
            bx:SetAlpha(C_CARD_BORDER[4])
            return bx
        end
        local bcorners = {
            { "TOPLEFT",     { "LEFT", tlWidget, "LEFT", l, 0 },  { "TOP", tt, "TOP", 0, t } },
            { "TOPRIGHT",    { "RIGHT", brWidget, "RIGHT", r, 0 }, { "TOP", tt, "TOP", 0, t } },
            { "BOTTOMLEFT",  { "LEFT", tlWidget, "LEFT", l, 0 },  { "BOTTOM", bb, "BOTTOM", 0, b } },
            { "BOTTOMRIGHT", { "RIGHT", brWidget, "RIGHT", r, 0 }, { "BOTTOM", bb, "BOTTOM", 0, b } },
        }
        for _, c in ipairs(bcorners) do
            local bx = btex("Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundCorner")
            bx:SetSize(cr, cr)
            bx:SetPoint(unpack(c[2]))
            bx:SetPoint(unpack(c[3]))
            local uv = BORDER_UV[c[1]]
            bx:SetTexCoord(uv[1], uv[2], uv[3], uv[4], uv[5], uv[6], uv[7], uv[8])
        end
        local bx = btex("Interface/Buttons/WHITE8X8")
        bx:SetPoint("LEFT", tlWidget, "LEFT", l, 0)
        bx:SetPoint("TOP", tt, "TOP", 0, t - cr + 1)
        bx:SetPoint("BOTTOM", bb, "BOTTOM", 0, b + cr - 1)
        RegisterPixelStrip(bx, "w")
        bx = btex("Interface/Buttons/WHITE8X8")
        bx:SetPoint("RIGHT", brWidget, "RIGHT", r, 0)
        bx:SetPoint("TOP", tt, "TOP", 0, t - cr + 1)
        bx:SetPoint("BOTTOM", bb, "BOTTOM", 0, b + cr - 1)
        RegisterPixelStrip(bx, "w")
        bx = btex("Interface/Buttons/WHITE8X8")
        bx:SetPoint("LEFT", tlWidget, "LEFT", l + cr - 1, 0)
        bx:SetPoint("RIGHT", brWidget, "RIGHT", r - cr + 1, 0)
        bx:SetPoint("TOP", tt, "TOP", 0, t)
        RegisterPixelStrip(bx, "h")
        bx = btex("Interface/Buttons/WHITE8X8")
        bx:SetPoint("LEFT", tlWidget, "LEFT", l + cr - 1, 0)
        bx:SetPoint("RIGHT", brWidget, "RIGHT", r - cr + 1, 0)
        bx:SetPoint("BOTTOM", bb, "BOTTOM", 0, b)
        RegisterPixelStrip(bx, "h")
    end

    function ns.hui.CreateSegmentedControl(host)
        local padX, padY = 3, 2
        local trackH = host:GetHeight() + padY * 2

        local track = CreateFrame("Frame", nil, host)
        track:SetPoint("TOPLEFT", host, "TOPLEFT", -padX, padY)
        track:SetPoint("BOTTOMRIGHT", host, "BOTTOMRIGHT", padX, -padY)
        local trackPieces = BuildCapsule(track, trackH / 2, ns.hui.layer.L1, nil, nil, GradNorm)
        if ns.hui.RegisterMainAlphaSurface and ns.hui.IsMainUIFrame(host) then
            ns.hui.RegisterMainAlphaSurface(track, trackPieces)
        end

        local sliderH = host:GetHeight() + 2
        local sliderY = (sliderH - host:GetHeight()) / 2
        local slider = CreateFrame("Frame", nil, host)
        slider:SetHeight(sliderH)
        local capW = sliderH / 2
        local capL = slider:CreateTexture(nil, "BORDER")
        capL:SetTexture(HUI_PILL_L)
        capL:SetSize(capW, sliderH)
        capL:SetPoint("TOPLEFT")
        Paint(capL, HUI_ACCENT)
        local capR = slider:CreateTexture(nil, "BORDER")
        capR:SetTexture(HUI_PILL_R)
        capR:SetSize(capW, sliderH)
        capR:SetPoint("TOPRIGHT")
        Paint(capR, HUI_ACCENT)
        local mid = slider:CreateTexture(nil, "BORDER")
        mid:SetTexture("Interface/Buttons/WHITE8X8")
        Paint(mid, HUI_ACCENT)
        mid:SetPoint("TOPLEFT", capL, "TOPRIGHT", 0, 0)
        mid:SetPoint("BOTTOMRIGHT", capR, "BOTTOMLEFT", 0, 0)
        slider:Hide()

        local ctrl = {buttons = {}, offsets = {}, slider = slider}

        function ctrl:AttachButtons(buttons)
            ctrl.buttonList = buttons
            local acc = 0
            for _, bt in ipairs(buttons) do
                ctrl.buttons[bt] = true
                ctrl.offsets[bt] = acc
                acc = acc + bt:GetWidth()
            end
        end

        local DURATION = 0.25
        local function ApplyThumb(x, w)
            slider:ClearAllPoints()
            slider:SetPoint("TOPLEFT", host, "TOPLEFT", x, sliderY)
            slider:SetWidth(w)
        end

        function ctrl:SetSelected(bt, animate)
            local toX = ctrl.offsets[bt]
            if not toX then return end
            local toW = bt:GetWidth()
            local fromX = ctrl.vx or toX
            local fromW = ctrl.vw or toW
            ctrl.x = toX
            ctrl.current = bt
            slider:Show()
            if animate and (fromX ~= toX or fromW ~= toW) then
                ctrl.animFromX, ctrl.animFromW = fromX, fromW
                ctrl.animToX, ctrl.animToW = toX, toW
                ctrl.animT = 0
                slider:SetScript("OnUpdate", function(s, elapsed)
                    ctrl.animT = ctrl.animT + elapsed
                    local p = ctrl.animT / DURATION
                    if p >= 1 then
                        s:SetScript("OnUpdate", nil)
                        ctrl.vx, ctrl.vw = ctrl.animToX, ctrl.animToW
                        ApplyThumb(ctrl.vx, ctrl.vw)
                        return
                    end
                    local e = 1 - (1 - p) * (1 - p)
                    ctrl.vx = ctrl.animFromX + (ctrl.animToX - ctrl.animFromX) * e
                    ctrl.vw = ctrl.animFromW + (ctrl.animToW - ctrl.animFromW) * e
                    ApplyThumb(ctrl.vx, ctrl.vw)
                end)
            else
                slider:SetScript("OnUpdate", nil)
                ctrl.vx, ctrl.vw = toX, toW
                ApplyThumb(toX, toW)
            end
        end

        function ctrl:HasButton(bt)
            return ctrl.buttons[bt] == true
        end

        function ctrl:ClearSelection()
            ctrl.current = nil
            ctrl.x = nil
            ctrl.vx, ctrl.vw = nil, nil
            slider:SetScript("OnUpdate", nil)
            slider:Hide()
        end

        ns.hui.AddRepaint(host, function()
            Paint(capL, HUI_ACCENT)
            Paint(capR, HUI_ACCENT)
            Paint(mid, HUI_ACCENT)
        end)

        return ctrl
    end

    function ns.hui.BuildRoundBorder(f, r, color, owner, layer, rounding, thickness, fillColor, outside, outExtra, expand)
        return DrawRoundBorder(f, r, color, owner, layer, rounding, thickness, fillColor, outside, outExtra, expand)
    end
    ns.hui.PixelStripSize = PixelStripSize

    local C_TEXT = {
        [1] = {0.95, 0.96, 0.98},
        [2] = {0xd4 / 255, 0xd4 / 255, 0xd4 / 255},
        [3] = {0xa0 / 255, 0xa0 / 255, 0xa0 / 255},
        [4] = {0x88 / 255, 0x88 / 255, 0x88 / 255},
    }
    local C_ACCENT = {0x46 / 255, 0xbf / 255, 0x72 / 255, 1}
    ns.hui.TEXT = C_TEXT
    ns.hui.ACCENT = C_ACCENT
    ns.hui.CARD_BORDER = C_CARD_BORDER

    function ns.hui.GetThemeBorderColor()
        local key = DungeonsForeverDB.libHUI and DungeonsForeverDB.libHUI.colorTheme
        local p = key and ns.hui.palette and ns.hui.palette[key]
        if p and p.deep then
            return { p.deep[1], p.deep[2], p.deep[3], 1 }
        end
        return C_CARD_BORDER
    end

    function ns.hui.TextColor(classic, level)
        if ns.huiTheme == "hui" then
            local c = (level == "accent") and ns.hui.ACCENT or C_TEXT[level or 1]
            return c[1], c[2], c[3]
        end
        if type(classic) == "table" then
            return classic[1], classic[2], classic[3]
        end
        return tonumber(classic:sub(1, 2), 16) / 255, tonumber(classic:sub(3, 4), 16) / 255, tonumber(classic:sub(5, 6), 16) / 255
    end

    function ns.hui.TextHex(classic, level)
        if ns.huiTheme ~= "hui" then return classic end
        local c = (level == "accent") and ns.hui.ACCENT or C_TEXT[level or 1]
        return format("%02x%02x%02x", c[1] * 255 + 0.5, c[2] * 255 + 0.5, c[3] * 255 + 0.5)
    end

    function ns.hui.FontFlags(classic)
        if ns.huiTheme == "hui" then return "" end
        return classic or "OUTLINE"
    end

    function ns.hui.BidOutlineFlags(classic, key)
        local flags = classic or "OUTLINE"
        if ns.huiTheme ~= "hui" then
            return flags
        end
        local v = ns.options and ns.options[key]
        if v == nil then
            v = 1
        end
        if v == 1 then
            return flags
        end
        return ""
    end

    function ns.hui.CountFlags(fallback, key)
        key = key or "itemCountOutline"
        if ns.options and ns.options[key] == 0 then
            return ns.hui.FontFlags(fallback)
        end
        return "OUTLINE"
    end

    local countFontRefresh = {}
    function ns.hui.RegisterItemCountFontRefresh(key, fn)
        if type(fn) == "function" then
            countFontRefresh[key or "itemCountOutline"] = fn
        end
    end
    function ns.hui.RefreshItemCountFonts(key)
        key = key or "itemCountOutline"
        local fn = countFontRefresh[key]
        if fn then pcall(fn) end
    end

    local huiFontObjs = {}
    function ns.hui.FontObject(level, size)
        local key = level .. "_" .. size
        if not huiFontObjs[key] then
            local c = (level == "accent") and ns.hui.ACCENT or C_TEXT[level]
            local f = CreateFont("ns.hui.FontText_" .. key)
            f:SetFont(ns.FONT, size, "")
            f:SetTextColor(c[1], c[2], c[3])
            f.__huiLevel = level
            huiFontObjs[key] = f
        end
        return huiFontObjs[key]
    end
    function ns.hui.RefreshFontObjects()
        for _, f in pairs(huiFontObjs) do
            local level = f.__huiLevel
            if level then
                local c = (level == "accent") and ns.hui.ACCENT or C_TEXT[level]
                f:SetTextColor(c[1], c[2], c[3])
            end
        end
    end

    local tooltipSkins = {}

    local function IsOwnedFrame(f)
        if not f or not f.GetName then return false end
        local ok, name = pcall(f.GetName, f)
        if not ok or not name then return false end
        return name:sub(1, 15) == "DungeonsForever"
    end

    local function TooltipOwnerIsMine(tt)
        if not tt or not tt.GetOwner then return false end
        local ok, owner = pcall(tt.GetOwner, tt)
        if not ok or not owner then return false end
        local roots = ns.hui.__ttRoots
        local f = owner
        while f and f ~= UIParent do
            if IsOwnedFrame(f) then return true end
            if roots and roots[f] then return true end
            f = f.GetParent and f:GetParent() or nil
        end
        if f == UIParent and (IsOwnedFrame(owner) or (roots and roots[owner])) then return true end
        return false
    end

    function ns.hui.RegisterTooltipRoot(f)
        if not f then return end
        ns.hui.__ttRoots = ns.hui.__ttRoots or {}
        ns.hui.__ttRoots[f] = true
    end

    local function AddonLoaded(name)
        local fn = IsAddOnLoaded
        if type(fn) ~= "function" then return false end
        local ok, loaded = pcall(fn, name)
        return ok and loaded and true or false
    end

    local ttItemMark = {}
    function ns.hui.MarkTipItem(tt, on)
        if tt then ttItemMark[tt] = on and true or nil end
    end
    do
        hooksecurefunc(GameTooltip, "SetOwner", function(tt) ttItemMark[tt] = nil end)
        hooksecurefunc(GameTooltip, "SetHyperlink", function(tt) ttItemMark[tt] = true end)
    end

    local function TooltipHasItemContent(tt)
        if ttItemMark[tt] then return true end
        local fn = tt and tt.GetItem
        if type(fn) ~= "function" then return false end
        local ok, _, link = pcall(fn, tt)
        return ok and link ~= nil
    end

    local function CollectForeign(root)
        local list = {}
        local seen = { [root] = true }
        local q = { root }
        local i = 1
        while i <= #q do
            local f = q[i]
            i = i + 1
            for _, c in ipairs({ f:GetChildren() }) do
                if not seen[c] then
                    seen[c] = true
                    q[#q + 1] = c
                end
            end
            for _, r in ipairs({ f:GetRegions() }) do
                if r.IsObjectType and r:IsObjectType("Texture") and not r.__huiPiece then
                    list[#list + 1] = { r, r:IsShown() }
                end
            end
        end
        return list
    end
    local tipApplying = false
    local function ApplyTooltipSkinBody(tt, on)
        local s = tooltipSkins[tt]
        if not s then return end
        s.on = on
        local FILL = ns.hui.layer.L3 or ns.hui.layer.L2 or ns.hui.layer.L1
        for _, tex in ipairs(s.fill) do
            tex:SetShown(on)
            if on then
                tex:SetVertexColor(FILL[1], FILL[2], FILL[3])
                tex:SetAlpha(FILL[4])
            end
        end
        for _, tex in ipairs(s.border) do tex:SetShown(on) end
        for _, tex in ipairs(s.shadow) do
            tex:SetShown(on)
            if on and s.shadowA then tex:SetAlpha(s.shadowA) end
        end
        if on then
            for _, e in ipairs(s.nineTex) do
                if e[2] then e[1]:SetShown(false) end
            end
            if tt.NineSlice then tt.NineSlice:SetAlpha(0) end
        else
            if tt.NineSlice then tt.NineSlice:SetAlpha(s.nineAlpha or 1) end
            for _, e in ipairs(s.nineTex or {}) do e[1]:SetShown(e[2]) end
        end
    end
    local function ApplyTooltipSkin(tt, on)
        local s = tt and tooltipSkins[tt]
        if not s then return end
        s.on = on
        if tipApplying then return end
        tipApplying = true
        pcall(ApplyTooltipSkinBody, tt, on)
        tipApplying = false
    end

    local function UnskinItemTooltip(tt)
        ttItemMark[tt] = true
        local s2 = tooltipSkins[tt]
        if s2 and s2.on then ApplyTooltipSkin(tt, false) end
    end

    local itemPostCallDone = false
    local function HookItemUnskin(tt)
        if tt.HasScript then
            local ok, has = pcall(tt.HasScript, tt, "OnTooltipSetItem")
            if ok and has then
                if pcall(tt.HookScript, tt, "OnTooltipSetItem", function() UnskinItemTooltip(tt) end) then return end
            end
        end
        if itemPostCallDone then return end
        if not (TooltipDataProcessor and TooltipDataProcessor.AddTooltipPostCall) then return end
        local td = Enum and Enum.TooltipDataType
        if not (td and td.Item ~= nil) then return end
        itemPostCallDone = true
        pcall(TooltipDataProcessor.AddTooltipPostCall, td.Item, UnskinItemTooltip)
    end

    function ns.hui.SkinGameTooltip(tt)
        if not tt or tt.__huiSkinned then return end
        tt.__huiSkinned = true
        local FILL = ns.hui.layer.L3 or ns.hui.layer.L2 or ns.hui.layer.L1
        local EDGE = ns.hui.layer.L5 or ns.hui.layer.DIV
        local s = {
            fill = BuildRoundedBG(tt, 8, FILL, "both"),
            border = ns.hui.BuildRoundBorder(tt, 8, EDGE) or {},
            shadow = BuildCardShadow(tt, 16, 0.6, -8, 8) or {},
            shadowA = 0.6,
            ownScoped = true,
        }
        for _, tex in ipairs(s.shadow) do
            tex.__huiPiece = true
            tex.__huiShadowPiece = true
            tex:Hide()
        end
        s.nineAlpha = tt.NineSlice and tt.NineSlice:GetAlpha() or 1
        s.nineTex = {}
        for _, tex in ipairs(s.fill) do tex.__huiPiece = true end
        for _, tex in ipairs(s.border) do tex.__huiPiece = true end
        tooltipSkins[tt] = s
        hooksecurefunc(GameTooltip, "SetOwner", function(tt)
            local s2 = tooltipSkins[tt]
            if s2 and s2.on then ApplyTooltipSkin(tt, false) end
        end)
        tt:HookScript("OnUpdate", function(f)
            local s2 = tooltipSkins[f]
            if not (s2 and s2.on) then return end
            local now = GetTime and GetTime() or 0
            if now - (s2.scanT or 0) < 0.2 then return end
            s2.scanT = now
            for _, e in ipairs(CollectForeign(f)) do
                if e[2] and e[1]:IsShown() then
                    e[1]:SetShown(false)
                    s2.nineTex[#s2.nineTex + 1] = e
                end
            end
            if f.NineSlice and f.NineSlice.GetAlpha and f.NineSlice:GetAlpha() ~= 0 then f.NineSlice:SetAlpha(0) end
        end)
        tt:HookScript("OnShow", function()
            if not s.snapDone then
                s.snapDone = true
                s.nineTex = CollectForeign(tt)
            end
            local on = ns.huiTheme == "hui"
            if on and s.ownScoped then
                on = TooltipOwnerIsMine(tt)
                if on and TooltipHasItemContent(tt) then on = false end
            end
            if on ~= s.on then ApplyTooltipSkin(tt, on) end
        end)
        HookItemUnskin(tt)
        ApplyTooltipSkin(tt, false)
    end

    function ns.hui.RefreshGameTooltipSkin()
        if not ns.hui.__tooltipStyleHooked then
            ns.hui.__tooltipStyleHooked = true
            if SharedTooltip_SetBackdropStyle then
                hooksecurefunc("SharedTooltip_SetBackdropStyle", function(tooltip)
                    local s = tooltip and tooltipSkins[tooltip]
                    if s and s.on then ApplyTooltipSkin(tooltip, true) end
                end)
            end
        end
        local themeOn = ns.huiTheme == "hui"
        for tt, s in pairs(tooltipSkins) do
            local on = themeOn
            if s.ownScoped then
                if tt:IsShown() then
                    on = on and TooltipOwnerIsMine(tt) and not TooltipHasItemContent(tt)
                else
                    on = false
                end
            end
            if s.on ~= on then ApplyTooltipSkin(tt, on) end
        end
    end

    pcall(ns.hui.SkinGameTooltip, GameTooltip)
    pcall(ns.hui.SkinGameTooltip, ItemRefTooltip)
    pcall(ns.hui.RefreshGameTooltipSkin)
    do
        local f = CreateFrame("Frame")
        f:RegisterEvent("PLAYER_LOGIN")
        f:SetScript("OnEvent", function()
            C_Timer.After(0, function()
                ns.hui.RefreshGameTooltipSkin()
            end)
        end)
    end

    local HUI_EDIT_BORDER_NORMAL = {0.30, 0.30, 0.28, 0.85}
    function ns.hui.SetEditBorder(edit, r, g, b, a)
        if not edit then return end
        if edit.HUIEdgeTop then
            for _, key in ipairs({ "HUIEdgeTop", "HUIEdgeBottom", "HUIEdgeLeft", "HUIEdgeRight",
                "HUICornerTL", "HUICornerTR", "HUICornerBL", "HUICornerBR" }) do
                local tex = edit[key]
                if tex then
                    if r == 1 and g == 1 and b == 1 then
                        tex:SetVertexColor(HUI_EDIT_BORDER_NORMAL[1], HUI_EDIT_BORDER_NORMAL[2], HUI_EDIT_BORDER_NORMAL[3])
                        tex:SetAlpha(HUI_EDIT_BORDER_NORMAL[4])
                    else
                        tex:SetVertexColor(r, g, b)
                        tex:SetAlpha(a or 1)
                    end
                end
            end
        elseif edit.Left then
            edit.Left:SetVertexColor(r, g, b, a or 1)
            edit.Right:SetVertexColor(r, g, b, a or 1)
            edit.Middle:SetVertexColor(r, g, b, a or 1)
        end
    end

    function ns.hui.SkinDropDown(dd)
        if not dd or dd.__huiDropDown or ns.huiTheme ~= "hui" then return end
        dd.__huiDropDown = true
        dd:EnableMouse(true)
        dd.__huiDDH = dd:GetHeight()

        for _, key in ipairs({ "Left", "Middle", "Right" }) do
            local tex = dd[key]
            if tex then tex:Hide() end
        end

        local ARROW_GRAY = { 0.62, 0.64, 0.67 }
        local btn = dd.Button
        if btn then
            btn:ClearAllPoints()
            btn:SetPoint("RIGHT", dd, "RIGHT", -2, 0)
            btn:SetSize(18, 18)
            local function HideNativeArrow()
                for _, reg in ipairs({ btn:GetRegions() }) do
                    if reg:GetObjectType() == "Texture" then
                        reg:SetAlpha(0)
                        reg:Hide()
                    end
                end
            end
            HideNativeArrow()
            for _, m in ipairs({ "Enable", "Disable", "SetEnabled" }) do
                hooksecurefunc(btn, m, HideNativeArrow)
            end
            dd:HookScript("OnShow", HideNativeArrow)
        end

        local arrow = dd.__huiArrow
        if not arrow then
            arrow = dd:CreateTexture(nil, "OVERLAY")
            arrow:SetSize(12, 12)
            arrow:SetPoint("RIGHT", dd, "RIGHT", -8, 0)
            arrow:SetTexture("Interface/AddOns/DungeonsForever/Media/textures/arrow.tga")
            arrow:SetRotation(math.pi)
            arrow:SetVertexColor(ARROW_GRAY[1], ARROW_GRAY[2], ARROW_GRAY[3])
            dd.__huiArrow = arrow
        end

        local text = dd.Text
        if text then
            text:ClearAllPoints()
            text:SetPoint("LEFT", dd, "LEFT", 10, 0)
            text:SetPoint("RIGHT", dd, "RIGHT", -22, 0)
            text:SetJustifyH("CENTER")
            text:SetFont(ns.FONT, 13, "")
            text:SetTextColor(0.92, 0.93, 0.95)
        end

        ns.hui.BuildRoundedBG(dd, 6, { 0x16 / 255, 0x1A / 255, 0x22 / 255, 0.5 }, "both")
        local NORMAL = { 0x4A / 255, 0x52 / 255, 0x63 / 255 }
        local border = ns.hui.BuildRoundBorder(dd, 6, NORMAL, dd, "OVERLAY", "both", 1) or {}
        local function Paint(c)
            for _, tex in ipairs(border) do
                if tex.__huiBorderStrip then
                    tex:SetColorTexture(c[1], c[2], c[3], 1)
                    tex:SetAlpha(c[4] or 1)
                else
                    tex:SetVertexColor(c[1], c[2], c[3])
                    tex:SetAlpha(c[4] or 1)
                end
            end
        end
        for _, tex in ipairs(border) do tex:SetShown(true) end
        dd:HookScript("OnEnter", function() Paint(ns.hui.ACCENT) end)
        dd:HookScript("OnLeave", function() Paint(NORMAL) end)
    end

    function ns.hui.SkinButton(bt, opts)
        if not bt or bt.__huiAction or not bt.SetBackdropBorderColor then return end
        if ns.huiTheme ~= "hui" then return end
        bt.__huiAction = true
        local noFrame = (opts == true) or (type(opts) == "table" and opts.noFrame == true) or bt.__huiNoFrame == true
        if noFrame then bt.__huiNoFrame = true end
        local C_BORDER = C_CTRL_BORDER
        local C_BG = {0x16 / 255, 0x1A / 255, 0x22 / 255}
        bt:SetBackdrop({
            bgFile = "Interface/ChatFrame/ChatFrameBackground",
            edgeFile = "Interface/ChatFrame/ChatFrameBackground",
            edgeSize = 1,
        })
        local bodyK = 1
        local function ApplyBody(base)
            bt:SetBackdropColor(C_BG[1], C_BG[2], C_BG[3], base * bodyK)
        end
        ApplyBody(0)
        bt:SetBackdropBorderColor(0, 0, 0, 0)
        if bt.bg then bt.bg:SetColorTexture(0, 0, 0, 0) end
        local fs = bt:GetFontString()
        if fs then
            fs:ClearAllPoints()
            fs:SetPoint("CENTER", 0, -1)
            fs:SetJustifyH("CENTER")
            fs:SetTextColor(1, 1, 1)
            fs:SetFont(ns.FONT, 15, "")
        end

        local borderFrame
        local function BuildBorderFrame()
            if noFrame then return end
            ns.hui.__skinBuilds = (ns.hui.__skinBuilds or 0) + 1
            if borderFrame then borderFrame:Hide(); borderFrame:SetParent(nil) end
            borderFrame = CreateFrame("Frame", nil, bt)
            borderFrame:SetAllPoints()
            local ring, covers = ns.hui.BuildRoundBorder(borderFrame, 6, C_BORDER)
            bt.__ring = ring
            bt.__ringCover = covers
            if bt.__huiVeil then
                for _, tex in ipairs(bt.__huiVeil) do tex:Hide() end
            end
            bt.__huiVeil = BuildCapsule(borderFrame, 6, {0, 0, 0, 0.28}, 0, 0)
            for _, tex in ipairs(bt.__huiVeil) do tex:Hide() end
        end
        local function BuildCapFrame()
            if noFrame or bt.__huiCap then return end
            local w, h = bt:GetWidth() or 0, bt:GetHeight() or 0
            if w > 0 and h > 0 then
                bt.__huiCap = BuildCapsule(bt, 6, ButtonBase(bt), 0, 4, GradNorm)
                if bt.__huiCap then
                    bt.__huiCap.__huiRepaint = function() PaintState(bt) end
                end
            end
        end
        local function TryBuild()
            ns.hui.__tryBuilds = (ns.hui.__tryBuilds or 0) + 1
            if noFrame then return end
            if borderFrame and bt.__huiCap then return end
            local w, h = bt:GetWidth() or 0, bt:GetHeight() or 0
            if w > 0 and h > 0 then
                if not borderFrame then BuildBorderFrame() end
                BuildCapFrame()
                PaintState(bt)
            end
        end
        TryBuild()
        if not noFrame and not (borderFrame and bt.__huiCap) then
            local function tryBuildOnce()
                if not (borderFrame and bt.__huiCap) then TryBuild() end
            end
            bt:HookScript("OnSizeChanged", tryBuildOnce)
            hooksecurefunc(bt, "SetSize", tryBuildOnce)
            hooksecurefunc(bt, "SetWidth", tryBuildOnce)
            hooksecurefunc(bt, "SetHeight", tryBuildOnce)
        end

        local function huiOnEnter()
            if not bt:IsEnabled() then return end
            bt.__huiHover = true
            PaintState(bt)
        end
        local function huiOnLeave()
            bt.__huiHover = nil
            ShiftContent(bt, 1)
            bt.__huiPress = nil
            PaintState(bt)
            if fs and bt:IsEnabled() and not bt.__huiKeepTextColor then
                if bt.__huiSelected then
                    fs:SetTextColor(1, 1, 1)
                elseif bt.__huiIdleText then
                    fs:SetTextColor(ns.hui.TEXT[3][1], ns.hui.TEXT[3][2], ns.hui.TEXT[3][3])
                else
                    fs:SetTextColor(1, 1, 1)
                end
            end
        end
        local function pressOn()
            if not bt:IsEnabled() then return end
            if bt.__huiPress then return end
            bt.__huiPress = true
            ShiftContent(bt, -1)
            PaintState(bt)
        end
        local function pressOff()
            if not bt.__huiPress then return end
            bt.__huiPress = nil
            ShiftContent(bt, 1)
            PaintState(bt)
        end
        hooksecurefunc(bt, "SetScript", function(_, scriptType, ...)
            if scriptType == "OnEnter" then bt:HookScript("OnEnter", huiOnEnter) end
            if scriptType == "OnLeave" then bt:HookScript("OnLeave", huiOnLeave) end
        end)
        bt:HookScript("OnEnter", huiOnEnter)
        bt:HookScript("OnLeave", huiOnLeave)
        bt:HookScript("OnMouseDown", pressOn)
        bt:HookScript("OnMouseUp", pressOff)
        bt:HookScript("OnHide", pressOff)
        hooksecurefunc(bt, "SetEnabled", function(_, enabled)
            if not enabled then pressOff() end
            if fs then
                if enabled then
                    if not bt.__huiKeepTextColor then fs:SetTextColor(1, 1, 1) end
                else
                    fs:SetTextColor(0.5, 0.5, 0.5)
                end
            end
            PaintState(bt)
        end)
        if ns.hui.IsMainUIFrame(bt) then
            ns.hui.RegisterMainAlphaMultiplier(bt, function(k)
                bodyK = k
                ApplyBody(0)
            end)
        end
        ns.hui.AddRepaint(bt, function()
            PaintState(bt)
        end)
    end

    function ns.hui.SetTabUnderline(bt, on)
        if not bt or not bt.CreateTexture then return end
        if not bt.__huiTabLine then
            local ln = bt:CreateTexture(nil, "OVERLAY")
            ln:SetColorTexture(ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3], 1)
            ln:SetHeight(2)
            ln:SetPoint("BOTTOMLEFT", bt, "BOTTOMLEFT", 3, 1)
            ln:SetPoint("BOTTOMRIGHT", bt, "BOTTOMRIGHT", -3, 1)
            ln:Hide()
            bt.__huiTabLine = ln
        end
        bt.__huiTabLine:SetShown(on and true or false)
    end

    ns.hui.GradNorm = GradNorm

    function ns.hui.SetButtonFrameless(bt, on)
        if not bt or not bt.__huiAction then return end
        local onv = on and true or false
        if bt.__huiFrameless == onv then return end
        bt.__huiFrameless = onv
        bt.__huiNoFrame = onv
        local function apply(pieces, show)
            if not pieces then return end
            for i = 1, #pieces do
                local tex = pieces[i]
                if tex and tex.SetShown then tex:SetShown(show) end
            end
        end
        apply(bt.__ring, not onv)
        apply(bt.__ringCover, not onv)
        apply(bt.__huiCap, not onv)
        if not onv then PaintState(bt) end
    end

    function ns.hui.SetButtonSelected(bt, on, kind, idleText)
        if not bt then return end
        local onv = on and true or false
        local kv = kind or "main"
        if bt.__huiSelected == onv and bt.__huiKind == kv then return end
        bt.__huiSelected = onv
        bt.__huiKind = kv
        if idleText ~= nil then bt.__huiIdleText = idleText end
        local fs = bt.GetFontString and bt:GetFontString()
        if fs and not bt.__huiKeepTextColor then
            if onv then
                fs:SetTextColor(1, 1, 1)
            elseif bt.__huiIdleText then
                fs:SetText(bt.__huiIdleText)
                fs:SetTextColor(ns.hui.TEXT[3][1], ns.hui.TEXT[3][2], ns.hui.TEXT[3][3])
            elseif kv == "tab" then
                fs:SetTextColor(ns.hui.TEXT[3][1], ns.hui.TEXT[3][2], ns.hui.TEXT[3][3])
            end
        end
        if bt.__huiTabLine then bt.__huiTabLine:Hide() end
        PaintState(bt)
    end

    function ns.hui.MakeDangerButton(bt)
        if not bt or bt.__huiDanger or not bt.SetBackdropBorderColor then return end
        if ns.huiTheme ~= "hui" then return end
        ns.hui.SkinButton(bt)
        bt.__huiDanger = true
        local texs = BuildCapsule(bt, 6, C_RED)
        for _, tex in ipairs(texs) do
            tex:SetDrawLayer("BACKGROUND", 5)
        end
        local capsuleK = 1
        local function ApplyCapsule(base)
            for _, tex in ipairs(texs) do
                tex:SetAlpha(base * capsuleK)
            end
        end
        hooksecurefunc(bt, "SetEnabled", function(_, enabled)
            ApplyCapsule(enabled and 1 or 0.25)
        end)
        if ns.hui.IsMainUIFrame(bt) then
            ns.hui.RegisterMainAlphaMultiplier(bt, function(k)
                capsuleK = k
                ApplyCapsule(bt:IsEnabled() and 1 or 0.25)
            end)
        end
    end

    function ns.hui.MakeAccentButton(bt)
        if not bt or bt.__huiAccent or not bt.SetBackdropBorderColor then return end
        if ns.huiTheme ~= "hui" then return end
        ns.hui.SkinButton(bt)
        bt.__huiAccent = true
        local texs = BuildCapsule(bt, 6, ns.hui.ACCENT)
        for _, tex in ipairs(texs) do
            tex:SetDrawLayer("BACKGROUND", 5)
        end
        local capsuleK = 1
        local function ApplyCapsule(base)
            for _, tex in ipairs(texs) do
                tex:SetAlpha(base * capsuleK)
            end
        end
        bt:HookScript("OnEnter", function()
            if bt:IsEnabled() then
                local h1 = math.min(ns.hui.ACCENT[1] + 0.10, 1)
                local h2 = math.min(ns.hui.ACCENT[2] + 0.10, 1)
                local h3 = math.min(ns.hui.ACCENT[3] + 0.10, 1)
                for _, tex in ipairs(texs) do
                    tex:SetVertexColor(h1, h2, h3)
                end
            end
        end)
        bt:HookScript("OnLeave", function()
            for _, tex in ipairs(texs) do
                tex:SetVertexColor(ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3])
            end
        end)
        hooksecurefunc(bt, "SetEnabled", function(_, enabled)
            ApplyCapsule(enabled and 1 or 0.25)
        end)
        if ns.hui.IsMainUIFrame(bt) then
            ns.hui.RegisterMainAlphaMultiplier(bt, function(k)
                capsuleK = k
                ApplyCapsule(bt:IsEnabled() and 1 or 0.25)
            end)
        end
        ns.hui.AddRepaint(bt, function()
            for _, tex in ipairs(texs) do
                tex:SetVertexColor(ns.hui.ACCENT[1], ns.hui.ACCENT[2], ns.hui.ACCENT[3])
            end
        end)
    end

    local function ToggleKnobX(on, bt)
        local W = (bt and bt.__huiW) or 36
        local K = (bt and bt.__huiKnob) or 14
        return on and (W - K - 3) or 3
    end
    local function PaintTrack(texs, c)
        for _, tex in ipairs(texs) do
            if tex.__isColor then
                tex:SetColorTexture(c[1], c[2], c[3], 1)
            else
                tex:SetVertexColor(c[1], c[2], c[3])
            end
        end
    end
    local function ApplyToggleState(bt, texs, knob, animate)
        animate = animate and true or false
        local on = bt.__huiOn
        if on == nil then on = bt:GetChecked() and true or false end
        bt.__huiOn = on
        local toX = ToggleKnobX(on, bt)
        local toC = on and HUI_ACCENT or ns.hui.layer.L4
        bt.__huiAnim = false
        if not animate then
            knob:ClearAllPoints()
            knob:SetPoint("LEFT", bt, "LEFT", toX, 0)
            knob:SetSize(bt.__huiKnob or 14, bt.__huiKnob or 14)
            PaintTrack(texs, toC)
            bt.__huiKnobX = toX
            bt.__huiColor = toC
            return
        end
        bt.__huiAnimFromX = bt.__huiKnobX or toX
        bt.__huiAnimToX = toX
        bt.__huiAnimFromC = bt.__huiColor or toC
        bt.__huiAnimToC = toC
        bt.__huiAnimEl = 0
        bt.__huiAnimDur = 0.14
        bt.__huiAnim = true
    end

    function ns.hui.ReskinToggle(bt, w, h)
        if bt.__huiToggle then return end
        local TW, TH = w or 36, h or 20
        local KNOB = TH - 6
        bt.__huiW, bt.__huiKnob = TW, KNOB
        bt.__huiToggle = true
        local ours = {}
        local border = CreateFrame("Frame", nil, bt)
        border:SetPoint("TOPLEFT", 1, -1)
        border:SetPoint("BOTTOMRIGHT", -1, 1)
        local borderTexs = BuildCapsule(border, KNOB / 2 + 1, C_TOGGLE_BORDER)
        for _, t in ipairs(borderTexs) do
            ours[t] = true
        end
        ours[border] = true
        local track = CreateFrame("Frame", nil, bt)
        track:SetPoint("TOPLEFT", 2, -2)
        track:SetPoint("BOTTOMRIGHT", -2, 2)
        local texs = BuildCapsule(track, KNOB / 2 + 1, ns.hui.layer.L1)
        for _, t in ipairs(texs) do
            t:SetDrawLayer("BORDER")
            ours[t] = true
        end
        ours[track] = true
        local knob = CreateFrame("Frame", nil, bt)
        knob:SetSize(KNOB, KNOB)
        local knobTex = knob:CreateTexture(nil, "ARTWORK")
        knobTex:SetTexture(HUI_CIRCLE)
        knobTex:SetAllPoints()
        local lum0 = (ns.hui.layer.L0[1] + ns.hui.layer.L0[2] + ns.hui.layer.L0[3]) / 3
        local kc0 = lum0 > 0.5 and {1, 1, 1} or C_KNOB
        knobTex:SetVertexColor(kc0[1], kc0[2], kc0[3])
        ours[knobTex] = true
        ours[knob] = true
        ns.hui.__skinRegistry[track] = nil
        track.__huiRepaints = nil
        ns.hui.AddRepaint(bt, function()
            ApplyToggleState(bt, texs, knob, false)
            local lum = (ns.hui.layer.L0[1] + ns.hui.layer.L0[2] + ns.hui.layer.L0[3]) / 3
            local kc = lum > 0.5 and {1, 1, 1} or C_KNOB
            knobTex:SetVertexColor(kc[1], kc[2], kc[3])
        end)
        local TEX_SETTERS = {
            "SetNormalTexture", "SetPushedTexture", "SetCheckedTexture",
            "SetHighlightTexture", "SetDisabledTexture",
        }
        local purging = false
        local function PurgeNative()
            if purging then return end
            purging = true
            for _, m in ipairs(TEX_SETTERS) do
                if bt[m] then
                    if not pcall(bt[m], bt, "") then
                        local getter = m:gsub("^Set", "Get")
                        if bt[getter] then
                            local ok, tex = pcall(bt[getter], bt)
                            if ok and tex then
                                tex:SetAlpha(0)
                                tex:Hide()
                            end
                        end
                    end
                end
            end
            if bt.SetBackdrop then
                pcall(bt.SetBackdrop, bt, nil)
            end
            for _, reg in ipairs({ bt:GetRegions() }) do
                if reg:GetObjectType() == "Texture" and not ours[reg] then
                    reg:SetAlpha(0)
                    reg:Hide()
                end
            end
            for _, ch in ipairs({ bt:GetChildren() }) do
                if not ours[ch] and not ch.__huiToggleKeep then
                    ch:Hide()
                end
            end
            purging = false
        end
        local function SafePurge()
            pcall(PurgeNative)
        end
        PurgeNative()
        for _, m in ipairs(TEX_SETTERS) do
            if bt[m] then
                hooksecurefunc(bt, m, SafePurge)
            end
        end
        if bt.SetBackdrop then
            hooksecurefunc(bt, "SetBackdrop", SafePurge)
        end
        bt:SetSize(TW, TH)
        if bt.Text then
            bt.Text:ClearAllPoints()
            bt.Text:SetPoint("LEFT", bt, "LEFT", TW + 2, 0)
            bt:SetHitRectInsets(0, -(bt.Text:GetWidth() or 60), 0, 0)
        end
        local origSetChecked = bt.SetChecked
        bt.SetChecked = function(self, v)
            self.__huiOn = not not v
            origSetChecked(self, v)
            SafePurge()
            ApplyToggleState(self, texs, knob, false)
        end
        local function ToggleOnUpdate(_, d)
            if not bt.__huiAnim then return end
            bt.__huiAnimEl = bt.__huiAnimEl + d
            local t = bt.__huiAnimEl >= bt.__huiAnimDur and 1 or bt.__huiAnimEl / bt.__huiAnimDur
            local e = 1 - (1 - t) * (1 - t)
            local x = bt.__huiAnimFromX + (bt.__huiAnimToX - bt.__huiAnimFromX) * e
            knob:ClearAllPoints()
            knob:SetPoint("LEFT", bt, "LEFT", x, 0)
            knob:SetSize(KNOB, KNOB)
            local fc, tc = bt.__huiAnimFromC, bt.__huiAnimToC
            PaintTrack(texs, {
                fc[1] + (tc[1] - fc[1]) * e,
                fc[2] + (tc[2] - fc[2]) * e,
                fc[3] + (tc[3] - fc[3]) * e,
            })
            if t >= 1 then
                bt.__huiAnim = false
                bt.__huiKnobX = bt.__huiAnimToX
                bt.__huiColor = bt.__huiAnimToC
            end
        end
        bt:HookScript("OnUpdate", ToggleOnUpdate)
        bt:HookScript("OnClick", function()
            SafePurge()
            bt.__huiOn = bt:GetChecked() and true or false
            ApplyToggleState(bt, texs, knob, true)
            if bt.__huiClickTimer then
                pcall(bt.__huiClickTimer.Cancel, bt.__huiClickTimer)
            end
            bt.__huiClickTimer = ns.After(0.16, function()
                bt.__huiClickTimer = nil
                if not bt:IsShown() then return end
                bt.__huiOn = bt:GetChecked() and true or false
                ApplyToggleState(bt, texs, knob, false)
            end)
        end)
        local C_ACCENT_HOVER = { math.min(ns.hui.ACCENT[1] + 0.10, 1), math.min(ns.hui.ACCENT[2] + 0.10, 1), math.min(ns.hui.ACCENT[3] + 0.10, 1) }
        bt:HookScript("OnEnter", function()
            if not bt:IsEnabled() then return end
            bt.__huiAnim = false
            local c = bt.__huiOn and C_ACCENT_HOVER or ns.hui.layer.L5
            PaintTrack(texs, c)
            bt.__huiColor = c
        end)
        bt:HookScript("OnLeave", function()
            ApplyToggleState(bt, texs, knob, true)
        end)
        local function SyncOnShow()
            SafePurge()
            bt.__huiOn = bt:GetChecked() and true or false
            ApplyToggleState(bt, texs, knob, false)
        end
        bt:HookScript("OnShow", SyncOnShow)
        bt:HookScript("OnEnable", SyncOnShow)
        bt:HookScript("OnDisable", SyncOnShow)
        SafePurge()
        ApplyToggleState(bt, texs, knob, false)
    end

    function ns.hui.ReskinSlider(s, noWheel)
        if not s or s.__huiSlider then return end
        if ns.huiTheme ~= "hui" then return end
        s.__huiSlider = true
        for _, reg in ipairs({ s:GetRegions() }) do
            if reg:GetObjectType() == "Texture" then
                reg:Hide()
            end
        end
        if s.SetBackdrop then
            pcall(function() s:SetBackdrop(nil) end)
        end
        local function HideForeign()
            for _, ch in ipairs({ s:GetChildren() }) do
                if ch ~= s.edit and ch ~= s.button then
                    ch:Hide()
                end
            end
        end
        HideForeign()
        s:HookScript("OnShow", function()
            if s.SetBackdrop then pcall(function() s:SetBackdrop(nil) end) end
            HideForeign()
        end)
        s:SetThumbTexture(HUI_CIRCLE)
        local thumb = s:GetThumbTexture()
        if thumb then
            thumb:SetTexture(HUI_CIRCLE)
            thumb:SetSize(16, 16)
            thumb:SetVertexColor(1, 1, 1)
            thumb:Show()
        end
        local trackBg = s:CreateTexture(nil, "BACKGROUND")
        trackBg:SetColorTexture(ns.hui.layer.L1[1], ns.hui.layer.L1[2], ns.hui.layer.L1[3], 1)
        trackBg:SetPoint("LEFT", 6, 0)
        trackBg:SetPoint("RIGHT", -6, 0)
        trackBg:SetHeight(6)
        ns.hui.AddRepaint(s, function()
            trackBg:SetColorTexture(ns.hui.layer.L1[1], ns.hui.layer.L1[2], ns.hui.layer.L1[3], 1)
        end)
        local trackFill = s:CreateTexture(nil, "BORDER")
        trackFill:SetColorTexture(HUI_ACCENT[1], HUI_ACCENT[2], HUI_ACCENT[3], 1)
        trackFill:SetPoint("LEFT", 6, 0)
        trackFill:SetHeight(6)
        local function UpdateFill()
            local mn, mx = s:GetMinMaxValues()
            local v = s:GetValue()
            local ratio = 0
            if mx and mn and mx > mn then
                ratio = (v - mn) / (mx - mn)
            end
            trackFill:SetWidth((s:GetWidth() - 12) * ratio)
        end
        s:HookScript("OnValueChanged", UpdateFill)
        s:HookScript("OnSizeChanged", UpdateFill)
        if not noWheel then
            s:EnableMouseWheel(true)
            s:HookScript("OnMouseWheel", function(self, delta)
                local step = self:GetValueStep() or 1
                self:SetValue(self:GetValue() + (delta > 0 and step or -step))
            end)
        end
        if s.Text and type(s.Text) ~= "function" then s.Text:SetTextColor(1, 1, 1) end
        if s.Low and type(s.Low) ~= "function" then s.Low:SetTextColor(C_GRAY[1], C_GRAY[2], C_GRAY[3]) end
        if s.High and type(s.High) ~= "function" then s.High:SetTextColor(C_GRAY[1], C_GRAY[2], C_GRAY[3]) end
        UpdateFill()
        ns.hui.AddRepaint(s, function()
            trackFill:SetColorTexture(HUI_ACCENT[1], HUI_ACCENT[2], HUI_ACCENT[3], 1)
        end)
    end

    function ns.hui.RoundIcon(tex)
        if not tex or tex.__huiRounded then return end
        if ns.huiTheme ~= "hui" then return end
        if not tex.AddMaskTexture then return end
        local f = tex:GetParent()
        if not f then return end
        tex.__huiRounded = true
        local mask = f:CreateMaskTexture(nil, "OVERLAY")
        mask:SetAllPoints(tex)
        mask:SetTexture("Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundRectMask",
            "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
        tex:AddMaskTexture(mask)
    end

    function ns.hui.RoundImage(tex, radiusFrac)
        if not tex or tex.__huiRoundImage then return end
        if ns.huiTheme ~= "hui" then return end
        if not tex.AddMaskTexture then return end
        local f = tex:GetParent()
        if not f then return end
        tex.__huiRoundImage = true
        radiusFrac = radiusFrac or 0.02
        local mask = f:CreateMaskTexture(nil, "OVERLAY")
        mask:SetAllPoints(f)
        mask:SetTexture("Interface/AddOns/DungeonsForever/Media/LibHUI/HUIRoundImageMask",
            "CLAMPTOBLACKADDITIVE", "CLAMPTOBLACKADDITIVE")
        tex:AddMaskTexture(mask)
        local border = nil
        local function RebuildBorder()
            if border then
                for _, t in ipairs(border) do t:Hide() end
            end
            local w = f:GetWidth()
            if w and w > 0 then
                border = ns.hui.BuildRoundBorder(f, w * radiusFrac, ns.hui.CARD_BORDER, nil, "OVERLAY")
                for _, t in ipairs(border) do t:SetShown(true) end
            end
        end
        RebuildBorder()
        f:HookScript("OnSizeChanged", RebuildBorder)
        return mask
    end

end

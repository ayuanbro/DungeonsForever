local _, ns = ...

local A = {}
ns.AreaDraw = A

local WHITE = "Interface\\Buttons\\WHITE8X8"
local DOT = "Interface\\AddOns\\DungeonsForever\\Media\\textures\\route_dot"

A.FILL_A = 0.20
A.FILL_A_OVL = 0.55
A.FILL_BAND = 2
A.RINGS = {}
A.EDGE_W = 2
A.EDGE_A = 0.95
A.BASE_SUB = 3
A.SUB_MAX = 7
A.MAX_TEX = 1400

local floor, ceil, sqrt, atan2 = math.floor, math.ceil, math.sqrt, math.atan2

local rotOk
local LAYER = "ARTWORK"

local function poolOf(host)
    local p = host.__adPool
    if not p then
        p = { list = {}, n = 0 }
        host.__adPool = p
    end
    return p
end

local function grab(p, host)
    local i = p.n + 1
    p.n = i
    local t = p.list[i]
    if not t then
        t = host:CreateTexture(nil, "ARTWORK")
        p.list[i] = t
    end
    return t
end

local function subOf(base, k)
    local s = base + k
    if s > A.SUB_MAX then s = A.SUB_MAX end
    return s
end

local function rect(t, host, x, y, w, h, r, g, b, a, sub)
    t:SetTexture(WHITE)
    t:SetVertexColor(r, g, b, a)
    t:ClearAllPoints()
    t:SetPoint("TOPLEFT", host, "TOPLEFT", x, -y)
    t:SetSize(w, h)
    t:SetDrawLayer(LAYER, sub)
    t:Show()
end

local function disc(t, host, x, y, d, r, g, b, a, sub)
    t:SetTexture(DOT)
    t:SetVertexColor(r, g, b, a)
    t:ClearAllPoints()
    t:SetPoint("CENTER", host, "TOPLEFT", x, -y)
    t:SetSize(d, d)
    t:SetDrawLayer(LAYER, sub)
    t:Show()
end

local function bar(t, host, x1, y1, x2, y2, w, r, g, b, a, sub)
    local dx, dy = x2 - x1, y2 - y1
    local len = sqrt(dx * dx + dy * dy)
    if len < 0.4 then
        disc(t, host, x1, y1, w, r, g, b, a, sub)
        return
    end
    t:SetTexture(WHITE)
    t:SetVertexColor(r, g, b, a)
    t:ClearAllPoints()
    t:SetPoint("CENTER", host, "TOPLEFT", (x1 + x2) * 0.5, -(y1 + y2) * 0.5)
    t:SetSize(len, w)
    t:SetRotation(-atan2(dy, dx))
    t:SetDrawLayer(LAYER, sub)
    t:Show()
end

local hits = {}

local function fillSpan(p, host, xs, ys, n, r, g, b, a, band, sub)
    local y0, y1 = ys[1], ys[1]
    for i = 2, n do
        local v = ys[i]
        if v < y0 then y0 = v end
        if v > y1 then y1 = v end
    end
    local y = floor(y0) - 1
    local yEnd = y1 + 1
    while y < yEnd do
        local yc = y + band * 0.5
        local h = 0
        for i = 1, n do
            local j = i % n + 1
            local ay, by = ys[i], ys[j]
            if (ay <= yc and by > yc) or (by <= yc and ay > yc) then
                local t = (yc - ay) / (by - ay)
                h = h + 1
                hits[h] = xs[i] + (xs[j] - xs[i]) * t
            end
        end
        if h >= 2 then
            for i = 2, h do
                local v = hits[i]
                local k = i - 1
                while k >= 1 and hits[k] > v do
                    hits[k + 1] = hits[k]
                    k = k - 1
                end
                hits[k + 1] = v
            end
            for i = 1, h - 1, 2 do
                local x1, x2 = hits[i], hits[i + 1]
                local w = x2 - x1
                if w > 0.5 then
                    rect(grab(p, host), host, x1 - 1, y, w + 2, band, r, g, b, a, sub)
                end
            end
        end
        y = y + band
    end
end

local function chain(p, host, x1, y1, x2, y2, w, r, g, b, a, sub)
    local dx, dy = x2 - x1, y2 - y1
    local len = sqrt(dx * dx + dy * dy)
    local step = w * 0.55
    if step < 1 then step = 1 end
    local k = ceil(len / step)
    if k < 1 then k = 1 end
    for i = 0, k do
        local u = i / k
        disc(grab(p, host), host, x1 + dx * u, y1 + dy * u, w, r, g, b, a, sub)
    end
end

local function stroke(p, host, xs, ys, n, w, r, g, b, a, sub, closed)
    local last = n
    if not closed then last = n - 1 end
    for i = 1, last do
        local j = i % n + 1
        local x1, y1, x2, y2 = xs[i], ys[i], xs[j], ys[j]
        if rotOk then
            bar(grab(p, host), host, x1, y1, x2, y2, w, r, g, b, a, sub)
        else
            chain(p, host, x1, y1, x2, y2, w, r, g, b, a, sub)
        end
        if closed then
            disc(grab(p, host), host, x1, y1, w, r, g, b, a, sub)
        end
    end
    if not closed then
        disc(grab(p, host), host, xs[n], ys[n], w, r, g, b, a, sub)
    end
end

local function convert(pts, cw, ch)
    local n = floor(#pts / 2)
    local xs, ys = {}, {}
    local kx, ky = cw * 0.01, ch * 0.01
    for i = 1, n do
        xs[i] = pts[i * 2 - 1] * kx
        ys[i] = pts[i * 2] * ky
    end
    return xs, ys, n
end

function A.Clear(host)
    local p = host and host.__adPool
    if not p then return end
    for i = 1, p.n do
        p.list[i]:Hide()
    end
    p.n = 0
end

function A.Paint(host, cw, ch, items, r, g, b, opts)
    A.Clear(host)
    if not (host and items and cw and ch) then return 0 end
    if cw < 2 or ch < 2 then return 0 end

    if rotOk == nil then
        local probe = host:CreateTexture(nil, "ARTWORK")
        rotOk = pcall(probe.SetRotation, probe, 0)
        probe:Hide()
    end

    local base = A.BASE_SUB
    LAYER = "ARTWORK"
    local fillA = A.FILL_A
    if opts then
        if opts.base then base = opts.base end
        if opts.layer then LAYER = opts.layer end
        if opts.fillA then fillA = opts.fillA end
    end

    r, g, b = r or 1, g or 1, b or 1

    local prep = {}
    local totalH = 0
    local cnt = 0
    for i = 1, #items do
        local it = items[i]
        local pts = it and it.pts
        if pts and #pts >= 6 then
            local xs, ys, n = convert(pts, cw, ch)
            local y0, y1 = ys[1], ys[1]
            for k = 2, n do
                if ys[k] < y0 then y0 = ys[k] end
                if ys[k] > y1 then y1 = ys[k] end
            end
            local closed = it.kind ~= "line" and n >= 3
            prep[i] = { xs = xs, ys = ys, n = n, closed = closed }
            totalH = totalH + (y1 - y0)
            cnt = cnt + 1
        end
    end
    if cnt == 0 then return 0 end

    local band = A.FILL_BAND
    local budget = A.MAX_TEX * 0.55
    if band < 1 then band = 1 end
    if totalH / band > budget then
        band = ceil(totalH / budget)
        if band > 40 then band = 40 end
    end

    local rings = A.RINGS
    local nr = #rings

    for i = 1, #items do
        local e = prep[i]
        if e and e.closed then
            fillSpan(poolOf(host), host, e.xs, e.ys, e.n, r, g, b, fillA, band, subOf(base, 0))
        end
    end

    for i = 1, #items do
        local e = prep[i]
        if e then
            local p = poolOf(host)
            for k = 1, nr do
                local ring = rings[k]
                stroke(p, host, e.xs, e.ys, e.n, ring[1], r, g, b, ring[2], subOf(base, 1), e.closed)
            end
            stroke(p, host, e.xs, e.ys, e.n, A.EDGE_W, r, g, b, A.EDGE_A, subOf(base, 2), e.closed)
        end
    end

    return poolOf(host).n
end

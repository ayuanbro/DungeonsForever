import sys

PATH = "Core/DungeonUI.lua"

raw = open(PATH, "rb").read()
crlf = raw.count(b"\r\n") > 0
text = raw.replace(b"\r\n", b"\n").decode("utf-8") if crlf else raw.decode("utf-8")


def L(*lines):
    return "\n".join(lines)


PATCHES = []

PATCHES.append((
    L('    U.dungeonQOVPool = { node = {}, line = {}, lab = {} }'),
    L('    U.dungeonQOVPool = { node = {}, line = {}, lab = {}, arc = {} }'),
))

PATCHES.append((
    L('    for _, l in ipairs(pool.line) do l:Hide() end',
      '    local nLine = 0'),
    L('    for _, l in ipairs(pool.line) do l:Hide() end',
      '    for _, t in ipairs(pool.arc) do t:Hide() end',
      '    local nArc = 0',
      '    local nLine = 0'),
))

PATCHES.append((
    L('    local function path(lc, pts)'),
    L('    local LINEW = 2.5',
      '    local ARC_TEX = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\DFLineArc"',
      '    local ARC_UV = (DG.Q_OV_RAD + LINEW / 2) / 16',
      '    local function takeArc()',
      '        nArc = nArc + 1',
      '        local t = pool.arc[nArc]',
      '        if not t then',
      '            t = canvas:CreateTexture(nil, "ARTWORK")',
      '            t:SetTexture(ARC_TEX)',
      '            pool.arc[nArc] = t',
      '        end',
      '        t:Show()',
      '        return t',
      '    end',
      '    local function rawArc(px, py, ix, iy, ox, oy, r, lc)',
      '        local cx = px - ix * r + ox * r',
      '        local cy = py - iy * r + oy * r',
      '        local out = r + LINEW / 2',
      '        local sx = (ox ~= 0) and -ox or ix',
      '        local sy = (oy ~= 0) and -oy or iy',
      '        local x0 = (sx > 0) and cx or cx - out',
      '        local y0 = (sy > 0) and cy or cy - out',
      '        local u = ARC_UV',
      '        local a, b, c, d = 0, 0, 0, u',
      '        local e, f, g, h = u, 0, u, u',
      '        if sx < 0 then a, c, e, g = u, u, 0, 0 end',
      '        if sy < 0 then b, d, f, h = u, 0, u, 0 end',
      '        local t = takeArc()',
      '        t:SetTexCoord(a, b, c, d, e, f, g, h)',
      '        t:SetSize(out, out)',
      '        t:ClearAllPoints()',
      '        t:SetPoint("TOPLEFT", canvas, "TOPLEFT", x0, -y0)',
      '        t:SetVertexColor(lc[1], lc[2], lc[3], 0.9)',
      '    end',
      '    local function path(lc, pts)'),
))

PATCHES.append((
    L('                local px, py = pts[i + 1][1], pts[i + 1][2]',
      '                local ex, ey = px - ux * r, py - uy * r',
      '                local o = seg[i + 1]',
      '                local fx, fy = px, py',
      '                if o.len > 0.05 then',
      '                    fx, fy = px + o.x / o.len * r, py + o.y / o.len * r',
      '                end',
      '                local m1x, m1y = (4 * ex + 4 * px + fx) / 9, (4 * ey + 4 * py + fy) / 9',
      '                local m2x, m2y = (ex + 4 * px + 4 * fx) / 9, (ey + 4 * py + 4 * fy) / 9',
      '                rawSeg(ex, ey, m1x, m1y, lc)',
      '                rawSeg(m1x, m1y, m2x, m2y, lc)',
      '                rawSeg(m2x, m2y, fx, fy, lc)'),
    L('                local px, py = pts[i + 1][1], pts[i + 1][2]',
      '                local o = seg[i + 1]',
      '                local vx, vy = 0, 0',
      '                if o.len > 0.05 then vx, vy = o.x / o.len, o.y / o.len end',
      '                rawArc(px, py, ux, uy, vx, vy, r, lc)'),
))

check_only = "--check" in sys.argv
bad = 0
for idx, (old, new) in enumerate(PATCHES, 1):
    n = text.count(old)
    if n != 1:
        print("  FAIL patch %d hits=%d : %s" % (idx, n, old.split("\n")[0][:60]))
        bad += 1
        continue
    print("  ok   patch %d hits=1 : %s" % (idx, old.split("\n")[0][:60]))
    if not check_only:
        text = text.replace(old, new, 1)

if check_only or bad:
    print("check rc=%d" % bad)
    sys.exit(1 if bad else 0)

out = text.replace("\n", "\r\n").encode("utf-8") if crlf else text.encode("utf-8")
open(PATH, "wb").write(out)
print("written %s (%s, %d bytes)" % (PATH, "CRLF" if crlf else "LF", len(out)))

import sys

PATH = "Core/DungeonUI.lua"

raw = open(PATH, "rb").read()
crlf = raw.count(b"\r\n") > 0
nl = b"\r\n" if crlf else b"\n"
text = raw.replace(b"\r\n", b"\n").decode("utf-8") if crlf else raw.decode("utf-8")


def L(*lines):
    return "\n".join(lines)


PATCHES = []

PATCHES.append((
    L('DG.Q_OV_GAP = 20'),
    L('DG.Q_OV_GAP = 20',
      'DG.Q_OV_RAD = 6'),
))

PATCHES.append((
    L('    local function vline(x, yTop, yBot, lc)',
      '        local l = takeLine()',
      '        l:SetColorTexture(lc[1], lc[2], lc[3], 0.9)',
      '        l:SetStartPoint("TOPLEFT", canvas, x, -yTop)',
      '        l:SetEndPoint("TOPLEFT", canvas, x, -yBot)',
      '    end'),
    L('    local RAD = DG.Q_OV_RAD or 6',
      '    local function rawSeg(x1, y1, x2, y2, lc)',
      '        if math.abs(x2 - x1) < 0.05 and math.abs(y2 - y1) < 0.05 then return end',
      '        local l = takeLine()',
      '        l:SetColorTexture(lc[1], lc[2], lc[3], 0.9)',
      '        l:SetStartPoint("TOPLEFT", canvas, x1, -y1)',
      '        l:SetEndPoint("TOPLEFT", canvas, x2, -y2)',
      '    end',
      '    local function path(lc, pts)',
      '        local n = #pts',
      '        if n < 2 then return end',
      '        local seg = {}',
      '        for i = 1, n - 1 do',
      '            local dx = pts[i + 1][1] - pts[i][1]',
      '            local dy = pts[i + 1][2] - pts[i][2]',
      '            seg[i] = { x = dx, y = dy, len = math.sqrt(dx * dx + dy * dy) }',
      '        end',
      '        local cutIn, cutOut = {}, {}',
      '        for i = 1, n do cutIn[i], cutOut[i] = 0, 0 end',
      '        for i = 2, n - 1 do',
      '            local a, b = seg[i - 1], seg[i]',
      '            if a.len > 0.05 and b.len > 0.05 then',
      '                local ax, ay = a.x / a.len, a.y / a.len',
      '                local bx, by = b.x / b.len, b.y / b.len',
      '                if math.abs(ax - bx) > 0.01 or math.abs(ay - by) > 0.01 then',
      '                    local r = math.min(RAD, a.len - cutOut[i - 1], b.len)',
      '                    if r >= 1.5 then',
      '                        cutIn[i], cutOut[i] = r, r',
      '                    end',
      '                end',
      '            end',
      '        end',
      '        for i = 1, n - 1 do',
      '            local s = seg[i]',
      '            local ux, uy = 0, 0',
      '            if s.len > 0.05 then ux, uy = s.x / s.len, s.y / s.len end',
      '            rawSeg(pts[i][1] + ux * cutOut[i], pts[i][2] + uy * cutOut[i],',
      '                    pts[i + 1][1] - ux * cutIn[i + 1], pts[i + 1][2] - uy * cutIn[i + 1], lc)',
      '            local r = cutIn[i + 1]',
      '            if r > 0 and i < n - 1 then',
      '                local px, py = pts[i + 1][1], pts[i + 1][2]',
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
      '                rawSeg(m2x, m2y, fx, fy, lc)',
      '            end',
      '        end',
      '    end',
      '    local function vline(x, yTop, yBot, lc)',
      '        rawSeg(x, yTop, x, yBot, lc)',
      '    end'),
))

PATCHES.append((
    L('        local midY = (y1 + y2) / 2',
      '        vline(x1, y1, midY, lc)',
      '        local l = takeLine()',
      '        l:SetColorTexture(lc[1], lc[2], lc[3], 0.9)',
      '        l:SetStartPoint("TOPLEFT", canvas, x1, -midY)',
      '        l:SetEndPoint("TOPLEFT", canvas, x2, -midY)',
      '        vline(x2, midY, y2, lc)'),
    L('        local midY = (y1 + y2) / 2',
      '        path(lc, { { x1, y1 }, { x1, midY }, { x2, midY }, { x2, y2 } })'),
))

PATCHES.append((
    L('    local function hline(y, x1, x2, lc)',
      '        local l = takeLine()',
      '        l:SetColorTexture(lc[1], lc[2], lc[3], 0.9)',
      '        l:SetStartPoint("TOPLEFT", canvas, x1, -y)',
      '        l:SetEndPoint("TOPLEFT", canvas, x2, -y)',
      '    end'),
    L('    local function hline(y, x1, x2, lc)',
      '        rawSeg(x1, y, x2, y, lc)',
      '    end'),
))

PATCHES.append((
    L('        local lx = math.max(0, x - nw / 2 - 6)',
      '        vline(x, y1, y1 + 8, lc)',
      '        hline(y1 + 8, x, lx, lc)',
      '        vline(lx, y1 + 8, y2 - 8, lc)',
      '        hline(y2 - 8, lx, x, lc)',
      '        vline(x, y2 - 8, y2, lc)'),
    L('        local lx = math.max(0, x - nw / 2 - 6)',
      '        path(lc, { { x, y1 }, { x, y1 + 8 }, { lx, y1 + 8 }, { lx, y2 - 8 }, { x, y2 - 8 }, { x, y2 } })'),
))

PATCHES.append((
    L('        local spineY = (DG.Q_OV_H + rowY(0)) / 2',
      '        hline(spineY, math.min(startCX + nw / 2, colX[1] + nw / 2), colX[nCols] + nw / 2, DG.Q_OV_TODO)',
      '        vline(startCX + nw / 2, DG.Q_OV_H, spineY, DG.Q_OV_TODO)',
      '        for c = 1, nCols do',
      '            local topQ = chains[packs[c][1]][1]',
      '            vline(colX[c] + nw / 2, spineY, rowY(0), lineColor(topQ, nil))',
      '        end'),
    L('        local spineY = (DG.Q_OV_H + rowY(0)) / 2',
      '        local xTop = startCX + nw / 2',
      '        local xL = math.min(xTop, colX[1] + nw / 2)',
      '        local xR = colX[nCols] + nw / 2',
      '        local bendR = math.min(RAD, rowY(0) - spineY)',
      '        local bend = (xR - xL) > bendR * 2',
      '        if bend then',
      '            hline(spineY, xL + bendR, xR - bendR, DG.Q_OV_TODO)',
      '        else',
      '            hline(spineY, xL, xR, DG.Q_OV_TODO)',
      '        end',
      '        vline(xTop, DG.Q_OV_H, spineY, DG.Q_OV_TODO)',
      '        for c = 1, nCols do',
      '            local topQ = chains[packs[c][1]][1]',
      '            local lc = lineColor(topQ, nil)',
      '            local xc = colX[c] + nw / 2',
      '            if bend and xc == xL then',
      '                path(lc, { { xL + bendR, spineY }, { xL, spineY }, { xL, rowY(0) } })',
      '            elseif bend and xc == xR then',
      '                path(lc, { { xR - bendR, spineY }, { xR, spineY }, { xR, rowY(0) } })',
      '            else',
      '                vline(xc, spineY, rowY(0), lc)',
      '            end',
      '        end'),
))

PATCHES.append((
    L('                vline(x1, bn.__oy + DG.Q_OV_H, corrY, lc)',
      '                if x1 ~= x2 then hline(corrY, x1, x2, lc) end'),
    L('                if x1 == x2 then',
      '                    vline(x1, bn.__oy + DG.Q_OV_H, corrY, lc)',
      '                else',
      '                    path(lc, { { x1, bn.__oy + DG.Q_OV_H }, { x1, corrY }, { x2, corrY } })',
      '                end'),
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

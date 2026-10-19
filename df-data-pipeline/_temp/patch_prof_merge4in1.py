# -*- coding: utf-8 -*-
"""专业页四合一：营地/传承/说明 并入总览，页签 7→4。
锚定字节替换（CRLF 保持不变），每个锚点必须唯一命中，否则报错退出。
"""
import sys, io

F = r"D:\workspace\DungeonsForever\Core\ProfessionUI.lua"

data = open(F, "rb").read()

def A(s):
    return s.replace("\n", "\r\n").encode("utf-8")

patches = []

patches.append((
    "-- 渲染 13 个专业的总览 / 营地 / 配方 / 采集 / 升级 / Legacy / 说明；只对无限服加载。",
    "-- 渲染 13 个专业的总览 / 配方 / 采集 / 升级；只对无限服加载。",
))

patches.append((
'''DG.PROF_SUBTABS = {
    { key = "overview", text = L["总览"] },
    { key = "camp",     text = L["营地"] },
    { key = "recipe",   text = L["配方"] },
    { key = "gather",   text = L["采集"] },
    { key = "leveling", text = L["升级"] },
    { key = "legacy",   text = L["传承"] },
    { key = "notes",    text = L["说明"] },
}''',
'''DG.PROF_SUBTABS = {
    { key = "overview", text = L["总览"] },
    { key = "recipe",   text = L["配方"] },
    { key = "gather",   text = L["采集"] },
    { key = "leveling", text = L["升级"] },
}''',
))

patches.append((
'''                if slug == "camping" then
                    PD.Show("camping")
                    PD.campView = "bonus"
                    PD.SetTab("camp")
                else''',
'''                if slug == "camping" then
                    PD.Show("camping")
                    PD.campView = "bonus"
                else''',
))

patches.append((
'''    PD.ixNote:SetText(L["营地档位对照表 →「营地系统 → 职业加成」"])''',
'''    PD.ixNote:SetText(L["营地档位对照表 →「营地系统」"])''',
))

patches.append((
'''    if not p then return out end
    if slug == "camping" then out[#out + 1] = "camp" end
    if p.camp and #p.camp > 0 then out[#out + 1] = "camp" end
    local r = R[slug]''',
'''    if not p then return out end
    local r = R[slug]''',
))

patches.append((
'''    if LV and LV[slug] then out[#out + 1] = "leveling" end
    if p.perks and #p.perks > 0 then out[#out + 1] = "legacy" end
    out[#out + 1] = "notes"
    return out''',
'''    if LV and LV[slug] then out[#out + 1] = "leveling" end
    return out''',
))

patches.append((
'''        local txt = (def.key == "camp" and PD.cur == "camping")
                    and L["职业加成"] or def.text''',
'''        local txt = def.text''',
))

patches.append((
'''                if def.key == "camp" and PD.cur == "camping" then
                    bt:SetText(L["职业加成"])
                else
                    bt:SetText(def.text)
                end''',
'''                bt:SetText(def.text)''',
))

patches.append((
'''    local h1 = y[1]
    if PD.wantIndexGrid and PD.ixRoot then''',
'''    local h1 = math.max(y[1], y[2])
    if PD.wantIndexGrid and PD.ixRoot then''',
))

# ── RowsOverview 整体重写 ──
OLD_OVERVIEW = '''function PD.RowsOverview(rows)
    if PD.cur == "__index" then
        local new, camps, perks, pts = 0, 0, 0, 0
        for _, slug in ipairs(D.order or {}) do
            local p = D.pro[slug]
            local r = R[slug]
            if r and r.rows then
                for _, it in ipairs(r.rows) do if it[11] then new = new + 1 end end
            end
            if p and p.camp then camps = camps + #p.camp end
            if p and p.perks then perks = perks + #p.perks end
            if p and p.miles then
                for _, m in ipairs(p.miles) do pts = pts + (m[3] or 0) end
            end
        end
        PushHead(rows, L["这份手册里有什么"])
        PushText(rows, format(
            L["%d 个专业 · 新增配方 %d 条 · 营地物件 %d 个 · 传承里程碑 %d 点 · 特权 %d 个"],
            #(D.order or {}), new, camps, pts, perks), 12)
        PushGap(rows)
        return
    end

    local p = D.pro[PD.cur]
    if not p then return end
    PushGap(rows, 6, 1)
    PushGap(rows, 6, 2)

    PushHead(rows, L["简介"], 1)
    local lede = (type(p.lede) == "string" and p.lede ~= "") and p.lede or p.summary
    PushText(rows, lede, 12, nil, 1)
    PushGap(rows, PD.OV_GUT, 1)
    if p.cert or p.title then
        PushHead(rows, L["认证与称号"], 1)
        if p.cert then
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H, col = 1, it = { p.cert[1] },
                text = p.cert[2] or "?",
                sub = format(L["解锁称号：%s"], p.cert[5] or "?"),
                right = format(L["技能 %d"], p.cert[4] or 0),
                lines = { { p.cert[2] or "?" },
                          { format(L["解锁称号：%s"], p.cert[5] or "?"), 1, 0.82, 0 } },
            }
        end
        if p.title then PushText(rows, p.title, 12, C_GOLD, 1) end
        PushGap(rows, PD.OV_GUT, 1)
    end
    if p.bonuses and #p.bonuses > 0 then
        PushHead(rows, L["共同变化"], 1)
        for _, b in ipairs(p.bonuses) do
            PushText(rows, format("%s：%s", b[1] or "?", b[4] or ""), 12, nil, 1)
        end
        PushGap(rows, PD.OV_GUT, 1)
    end
    if p.camp and #p.camp > 0 then
        PushHead(rows, L["营地三档"], 1)
        for _, c in ipairs(p.camp) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 1, icon = c[3],
                text = format(L["技能 %d · %s"], c[4] or 0, c[2] or "?"),
                right = c[6] or c[7] or "",
            }
        end
    end

    local miles = p.miles or {}
    local mpts = 0
    for _, m in ipairs(miles) do mpts = mpts + (m[3] or 0) end
    local function stat(label, value)
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H1, col = 2,
            nameColor = C_GREY, text = label, right = value,
        }
    end
    PushHead(rows, L["数字速览"], 2)
    if p.cert then stat(L["认证技能"], format(L["技能 %d"], p.cert[4] or 0)) end
    if p.recipes or p.sub then
        stat(L["配方规模"], format(L["%d 条 · %d 个分类"], p.recipes or 0, p.sub or 0))
    end
    if #miles > 0 then stat(L["里程碑"], format(L["%d 点"], mpts)) end
    if p.camp and #p.camp > 0 then stat(L["营地"], format(L["%d 档"], #p.camp)) end
    if p.perks and #p.perks > 0 then stat(L["传承特权"], format(L["%d 个"], #p.perks)) end
    PushGap(rows, PD.OV_GUT, 2)
    if #miles > 0 then
        PushHead(rows, L["里程碑与传承点数"], 2)
        for _, m in ipairs(miles) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 2, text = m[1] or "?",
                right = format(L["技能 %d · %d 点"], m[2] or 0, m[3] or 0),
            }
        end
    end

    local secN = 0
    for _, sp in ipairs(rows) do
        if sp.kind == "head" then
            secN = secN + 1
            sp.sec = secN
        elseif sp.kind ~= "gap" then
            sp.sec = secN
        end
    end
    PD.secCount = secN
end'''

NEW_OVERVIEW = '''local C_ALLIANCE = { 0.40, 0.80, 0.94 }
local C_HORDE = { 1.00, 0.30, 0.25 }

function PD.RowsOverview(rows)
    if PD.cur == "__index" then
        local new, camps, perks, pts = 0, 0, 0, 0
        for _, slug in ipairs(D.order or {}) do
            local p = D.pro[slug]
            local r = R[slug]
            if r and r.rows then
                for _, it in ipairs(r.rows) do if it[11] then new = new + 1 end end
            end
            if p and p.camp then camps = camps + #p.camp end
            if p and p.perks then perks = perks + #p.perks end
            if p and p.miles then
                for _, m in ipairs(p.miles) do pts = pts + (m[3] or 0) end
            end
        end
        PushHead(rows, L["这份手册里有什么"])
        PushText(rows, format(
            L["%d 个专业 · 新增配方 %d 条 · 营地物件 %d 个 · 传承里程碑 %d 点 · 特权 %d 个"],
            #(D.order or {}), new, camps, pts, perks), 12)
        PushGap(rows)
        PushHead(rows, L["怎么读这份手册"])
        PushText(rows, L["左侧选专业、右侧切子页。子页按数据是否存在自动启用：采集类没有配方与升级路线（但有节点表）。物品名与图标全部由客户端提供，客户端还没加载到的会先显示占位、随后自动补上。"], 12)
        PushGap(rows)
        PushHead(rows, L["数据版本"])
        PushText(rows, format(L["build %s · 更新于 %s"],
                              tostring(D.build or "?"), tostring(D.updated or "?")), 12)
        PushGap(rows)
        PushHead(rows, L["状态标签说明"])
        local seen, list = {}, {}
        for _, slug in ipairs(D.order or {}) do
            local p = D.pro[slug]
            if p and p.status and not seen[p.status] then
                seen[p.status] = true
                list[#list + 1] = p.status
            end
        end
        for _, st in ipairs(list) do
            rows[#rows + 1] = { kind = "text", text = "· " .. st, color = C_GREY }
        end
        return
    end

    local p = D.pro[PD.cur]
    if not p then return end
    PushGap(rows, 6, 1)
    PushGap(rows, 6, 2)

    PushHead(rows, L["简介"], 1)
    rows[#rows + 1] = {
        kind = "row", h = PD.ROW_H1, col = 1,
        text = p.status or L["未标注"], right = p.kind or "",
    }
    local lede = (type(p.lede) == "string" and p.lede ~= "") and p.lede or p.summary
    PushText(rows, lede, 12, nil, 1)
    if p.cert or p.title then
        PushGap(rows, 4, 1)
        if p.cert then
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H, col = 1, it = { p.cert[1] },
                text = p.cert[2] or "?",
                sub = format(L["解锁称号：%s"], p.cert[5] or "?"),
                right = format(L["技能 %d"], p.cert[4] or 0),
                lines = { { p.cert[2] or "?" },
                          { format(L["解锁称号：%s"], p.cert[5] or "?"), 1, 0.82, 0 } },
            }
        end
        if p.title then PushText(rows, p.title, 12, C_GOLD, 1) end
    end
    PushGap(rows, PD.OV_GUT, 1)

    local miles = p.miles or {}
    local hasPerks = p.perks and #p.perks > 0
    if #miles > 0 or hasPerks then
        PushHead(rows, L["传承"], 1)
        for _, m in ipairs(miles) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, col = 1, text = m[1] or "?",
                right = format(L["技能 %d · %d 点"], m[2] or 0, m[3] or 0),
            }
        end
        if #miles > 0 and hasPerks then PushGap(rows, 4, 1) end
        for _, pid in ipairs(p.perks or {}) do
            local pk = D.perks[pid]
            if pk then
                local open = PD.perkOpen[pid]
                local lines = { { pk[6] or "" } }
                if pk[8] then
                    for _, u in ipairs(pk[8]) do lines[#lines + 1] = { u, 0.9, 0.7, 0.4 } end
                end
                rows[#rows + 1] = {
                    kind = "row", col = 1, icon = pk[2], text = pk[1] or "?",
                    sub = (pk[6] or ""):sub(1, 90),
                    right = format(L["满级 %s"], tostring(pk[4])),
                    right2 = open and L["收起逐级文本"]
                                      or format(L["展开 %d 级文本"], #(pk[5] or {})),
                    lines = lines,
                    act = function()
                        PD.perkOpen[pid] = not PD.perkOpen[pid]
                        PD.Render()
                    end,
                }
                if open and pk[5] then
                    for i, t in ipairs(pk[5]) do
                        rows[#rows + 1] = { kind = "text", col = 1,
                                            text = format("%d. %s", i, t), color = C_TEXT }
                    end
                end
            end
        end
        PushGap(rows, PD.OV_GUT, 1)
    end

    local lv = LV[PD.cur]
    local hasCampObjs = p.camp and #p.camp > 0
    local hasCampPts = lv and (lv.camps or lv.vendor) and true or false
    if hasCampObjs or hasCampPts then
        PushHead(rows, L["营地"], 1)
        for _, c in ipairs(p.camp or {}) do
            local lines = {}
            local function Add(label, v)
                if v and v ~= "" then lines[#lines + 1] = { label .. "：" .. v } end
            end
            Add(L["角色"], c[7])
            Add(L["增益"], c[6])
            Add(L["取代"], c[8])
            Add(L["互斥"], c[9])
            Add(L["容量"], c[10])
            if c[11] and #c[11] > 0 then
                lines[#lines + 1] = { format(L["材料：%s"], PD.MatText(c[11])), 0.7, 0.7, 0.7 }
            end
            if c[12] and c[12][1] then
                lines[#lines + 1] = { format(L["图纸：%s"], DG.ItemName(c[12][1])) }
            end
            rows[#rows + 1] = {
                kind = "row", col = 1, icon = c[3],
                text = c[2] or "?",
                sub = c[5] or "",
                right = format(L["技能 %d"], c[4] or 0),
                lines = lines,
            }
        end
        if hasCampObjs and hasCampPts then PushGap(rows, 4, 1) end
        for _, side in ipairs({ "a", "h" }) do
            local fc = (side == "a") and C_ALLIANCE or C_HORDE
            local camp = lv and lv.camps and lv.camps[side]
            if camp then
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc,
                    text = format(L["营地 · %s"], camp[3] or "?"),
                    sub = format("%s · %s", PD.CampZoneName(camp[6], tostring(camp[2] or "")), tostring(camp[1] or "")),
                    right = format("%.1f, %.1f", camp[4] or 0, camp[5] or 0),
                    lines = {
                        { L["点击：在地图上标记此位置"], 1, 0.82, 0 },
                        { format("%s %.1f, %.1f", tostring(camp[2] or ""), camp[4] or 0, camp[5] or 0), 0.75, 0.75, 0.75 },
                    },
                    act = function() PD.MarkCampPoint(camp[6], camp[4], camp[5]) end,
                }
            end
            local vd = lv and lv.vendor and lv.vendor[side]
            if vd then
                rows[#rows + 1] = {
                    kind = "row", col = 1, nameColor = fc, icon = vd[4],
                    text = format(L["军需官 · %s"], tostring(vd[1])),
                    sub = tostring(vd[3] or ""),
                    right = format("%.1f, %.1f", vd[5] or 0, vd[6] or 0),
                    lines = {
                        { L["点击：在地图上标记该 NPC"], 1, 0.82, 0 },
                        { format("%.1f, %.1f", vd[5] or 0, vd[6] or 0), 0.75, 0.75, 0.75 },
                    },
                    act = function() PD.MarkCampPoint(vd[7], vd[5], vd[6]) end,
                }
            end
        end
        PushGap(rows, PD.OV_GUT, 1)
    end

    if p.steps and #p.steps > 0 then
        PushHead(rows, p.steps_title or L["怎么开始"], 1)
        if p.steps_note then PushText(rows, p.steps_note, 12, C_GREY, 1) end
        for i, st in ipairs(p.steps) do
            rows[#rows + 1] = {
                kind = "row", col = 1,
                text = format("%d. %s", i, st[1] or ""), sub = st[2] or "",
                lines = { { st[1] or "" }, { st[2] or "", 0.85, 0.85, 0.85 } },
            }
        end
        PushGap(rows, PD.OV_GUT, 1)
    end
    if p.racials and #p.racials > 0 then
        PushHead(rows, L["种族相关"], 1)
        for _, rc in ipairs(p.racials) do PushText(rows, "· " .. (rc[3] or ""), 12, nil, 1) end
        PushGap(rows, PD.OV_GUT, 1)
    end

    local function stat(label, value)
        rows[#rows + 1] = {
            kind = "row", h = PD.ROW_H1, col = 2,
            nameColor = C_GREY, text = label, right = value,
        }
    end
    PushHead(rows, L["数字速览"], 2)
    if p.cert then stat(L["认证技能"], format(L["技能 %d"], p.cert[4] or 0)) end
    if p.recipes or p.sub then
        stat(L["配方规模"], format(L["%d 条 · %d 个分类"], p.recipes or 0, p.sub or 0))
    end
    if p.camp and #p.camp > 0 then stat(L["营地"], format(L["%d 档"], #p.camp)) end
    if hasPerks then stat(L["传承特权"], format(L["%d 个"], #p.perks)) end
    PushGap(rows, PD.OV_GUT, 2)
    PushHead(rows, L["开发备注"], 2)
    local noted = false
    if p.tips and #p.tips > 0 then
        for _, t in ipairs(p.tips) do PushText(rows, "· " .. t, 12, nil, 2) end
        noted = true
    end
    if p.verify and #p.verify > 0 then
        if noted then PushGap(rows, 4, 2) end
        for _, t in ipairs(p.verify) do PushText(rows, "· " .. t, 12, { 0.95, 0.78, 0.35 }, 2) end
        noted = true
    end
    if not noted then PushText(rows, L["暂无备注"], 12, C_GREY, 2) end

    if PD.cur == "camping" and PD.campView == "bonus" then
        PushHead(rows, L["全部专业的营地物件档位对照"], nil, 16)
        rows[#rows].noSec = true
    end

    local secN = 0
    for _, sp in ipairs(rows) do
        if sp.kind == "head" and not sp.noSec then
            secN = secN + 1
            sp.sec = secN
        elseif sp.kind ~= "gap" then
            sp.sec = secN
        end
    end
    PD.secCount = secN
end'''

patches.append((OLD_OVERVIEW, NEW_OVERVIEW))

# ── 删 RowsCamp ──
OLD_CAMP_HEAD = "function PD.RowsCamp(rows, side)"
OLD_CAMP_TAIL = "function PD.MatIconTex(id, px)"
i1 = data.find(A(OLD_CAMP_HEAD))
i2 = data.find(A(OLD_CAMP_TAIL))
assert i1 != -1 and i2 != -1 and i1 < i2, "RowsCamp anchor fail"

# ── 删 RowsLegacy + RowsNotes ──
OLD_LN_HEAD = "function PD.RowsLegacy(rows)"
OLD_LN_TAIL = "function PD.RowsSettings(rows)"
j1 = data.find(A(OLD_LN_HEAD))
j2 = data.find(A(OLD_LN_TAIL))
assert j1 != -1 and j2 != -1 and j1 < j2, "RowsLegacy/Notes anchor fail"

patches.append((
'''    elseif PD.tab == "overview" then
        PD.lvSplit = (PD.cur ~= "__index")
        PD.wantIndexGrid = (PD.cur == "__index")
        PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.OV_SPLIT)
        PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
        PD.hasSecs = true
        PD.hideDivider = true
        PD.RowsOverview(rows)
    elseif PD.tab == "camp" then
        local hasCamp = (D.pro[PD.cur] and D.pro[PD.cur].camp) and true or false
        if not hasCamp then PD.campView = "bonus" end
        tool = {}
        if hasCamp then
            tool[#tool + 1] = { key = "a", text = L["联盟"], on = PD.campView == "a" }
            tool[#tool + 1] = { key = "h", text = L["部落"], on = PD.campView == "h" }
            handler = function(k) PD.campView = k; PD.Render() end
        end
        if PD.campView == "bonus" then
            PD.hasSecs = false
            PushGap(rows, 6)
            PushHead(rows, L["全部专业的营地物件档位对照"], nil, 16)
            PD.wantBonusTable = true
        else
            PD.hasSecs = true
            PD.RowsCamp(rows, PD.campView)
        end
    elseif PD.tab == "recipe" then''',
'''    elseif PD.tab == "overview" then
        PD.lvSplit = (PD.cur ~= "__index")
        PD.wantIndexGrid = (PD.cur == "__index")
        PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.OV_SPLIT)
        PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW
        PD.hasSecs = true
        PD.hideDivider = true
        if PD.cur == "camping" then
            PD.campView = "bonus"
            PD.wantBonusTable = true
        end
        PD.RowsOverview(rows)
    elseif PD.tab == "recipe" then''',
))

patches.append((
'''    elseif PD.tab == "legacy" then
        PD.RowsLegacy(rows)
    else
        PD.RowsNotes(rows)
    end''',
'''    else
        PD.RowsOverview(rows)
    end''',
))

for old, new in patches:
    ob, nb = A(old), A(new)
    c = data.count(ob)
    if c != 1:
        print("FAIL: anchor count=%d for: %s" % (c, old[:60].replace("\n", "\\n")))
        sys.exit(1)
    data = data.replace(ob, nb)

# 两段整删（锚点定位，含中间全部内容）
camp_start = data.find(A(OLD_CAMP_HEAD))
camp_end = data.find(A(OLD_CAMP_TAIL))
assert camp_start != -1 and camp_end > camp_start
data = data[:camp_start] + data[camp_end:]

ln_start = data.find(A(OLD_LN_HEAD))
ln_end = data.find(A(OLD_LN_TAIL))
assert ln_start != -1 and ln_end > ln_start
data = data[:ln_start] + data[ln_end:]

# 终检：残留引用必须清零
for bad in [b'"camp"', b'"legacy"', b'"notes"', b"RowsCamp", b"RowsLegacy", b"RowsNotes",
            b"p.bonuses", b"p.unknowns", b'\xe8\x81\x8c\xe4\xb8\x9a\xe5\x8a\xa0\xe6\x88\x90" ']:
    pass
for bad, label in [
    (b'PD.RowsCamp', "RowsCamp"), (b'PD.RowsLegacy', "RowsLegacy"), (b'PD.RowsNotes', "RowsNotes"),
    (b'tab == "camp"', 'tab=="camp"'), (b'tab == "legacy"', 'tab=="legacy"'),
    (b'key = "camp"', 'key=camp'), (b'key = "legacy"', 'key=legacy'), (b'key = "notes"', 'key=notes'),
]:
    if data.count(bad) != 0:
        print("FAIL: residual %s x%d" % (label, data.count(bad)))
        sys.exit(1)

open(F, "wb").write(data)
print("OK: %d bytes written, patches applied" % len(data))

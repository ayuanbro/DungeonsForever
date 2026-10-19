# -*- coding: utf-8 -*-
"""Core/ProfessionUI.lua 补丁：左导航去提示框 + 采集页区域名/节点名走客户端 + 钓鱼采集页两列。

为什么写成脚本而不是几个 Edit：本文件同一天要改多处，**同一文件并行发多条 Edit 会互相覆盖**
（后发的 read-modify-write 拿的是旧内容，先发的那条被静默吃掉，工具却报成功）。
脚本里每条锚点断言**恰好命中 1 次**，不对就整体中止、一个字节都不落盘。

用法：
    python patch_prof_ui.py --check   # 只验锚点命中数
    python patch_prof_ui.py           # 逐条替换并写回（LF 保持 LF）
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(os.path.dirname(HERE), 'Core', 'ProfessionUI.lua')


def die(msg):
    sys.stderr.write('patch_prof_ui: %s\n' % msg)
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# ① 左列导航去掉鼠标提示框（用户 2026-09-24）
# ═══════════════════════════════════════════════════════════════════════════
TOOLTIP = [
    # 别名表里去掉 SetTip —— 留着不用的 local 会让 luacheck 多一条 unused 警告
    ('local SetOutline, SetTip, Unpack = Host.SetOutline, Host.SetTip, Host.Unpack',
     'local SetOutline, Unpack = Host.SetOutline, Host.Unpack'),

    ('''    -- ── 左列导航：总览 + 13 个专业，按 主专业 / 次专业 / 营地系统 分组 ──
    PD.nav = {}
    local navY = 0
    local function navEntry(key, text, icon, tip)''',
     '''    -- ── 左列导航：总览 + 13 个专业，按 主专业 / 次专业 / 营地系统 分组 ──
    -- ★ 用户 2026-09-24：左列导航**不要鼠标提示框** —— 名字 + 图标已经把「这是哪个专业」
    --   说清楚了，悬停再弹一层 title / summary 只会挡视线（原来这里挂的是 SetTip）。
    --   那些文案在「总览」页本来就有一份，不必再重复到提示框里。
    PD.nav = {}
    local navY = 0
    local function navEntry(key, text, icon)'''),

    ('''        bt:SetScript("OnClick", function() PD.Show(key) end)
        if tip then SetTip(bt, tip) end
        PD.nav[#PD.nav + 1] = bt''',
     '''        bt:SetScript("OnClick", function() PD.Show(key) end)
        PD.nav[#PD.nav + 1] = bt'''),

    ('    navEntry("__index", L["全部专业"], "inv_misc_book_11", L["统计 / 营地对照表 / 怎么读"])',
     '    navEntry("__index", L["全部专业"], "inv_misc_book_11")'),

    ('                navEntry(slug, p.name or slug, p.icon, p.title or p.summary)',
     '                navEntry(slug, p.name or slug, p.icon)'),
]

# ═══════════════════════════════════════════════════════════════════════════
# ② 区域名取数口（与 SpellName 同款：客户端优先、拿不到给 ID 占位）
# ═══════════════════════════════════════════════════════════════════════════
ZONENAME = [
    ('''    if type(nm) == "string" and nm ~= "" then return nm end
    return format(L["法术 #%d"], id)
end

-- 任务名：与 SpellName 同款「客户端优先、拿不到给占位」。''',
     '''    if type(nm) == "string" and nm ~= "" then return nm end
    return format(L["法术 #%d"], id)
end

-- 区域名：数据表里只有 AreaTable 区域 ID（对照表见 _temp/fc_zones.py），中文名问客户端。
-- ★ 与 SpellName 同一条口径：客户端拿不到就显示「区域 #ID」占位，**绝不回落英文名**
--   （站点的 JSON 里给的是英文区域名，那正是这次要消掉的东西）。
-- ★ C_Map 要**现取**、不缓存成顶层 local：桩与实机都可能后挂/撤掉它，缓存住就成了
--   「离线测得出、实机恒 nil」（或反过来）的假覆盖。
DG.ZoneName = function(id)
    if type(id) ~= "number" then return L["无数据"] end
    local m = C_Map
    local fn = m and m.GetAreaInfo
    if type(fn) == "function" then
        local ok, nm = pcall(fn, id)
        if ok and type(nm) == "string" and nm ~= "" then return nm end
    end
    return format(L["区域 #%d"], id)
end

-- 任务名：与 SpellName 同款「客户端优先、拿不到给占位」。'''),
]

# ═══════════════════════════════════════════════════════════════════════════
# ③ 采集页：区域名走客户端 + 节点行标题改用首个产出物的客户端中文名
# ═══════════════════════════════════════════════════════════════════════════
GATHER = [
    ('''function PD.ZoneText(list, maxN)
    if not list or #list == 0 then return L["无数据"] end
    local t = {}
    for i, z in ipairs(list) do
        if maxN and i > maxN then t[#t + 1] = "…"; break end
        t[#t + 1] = format("%s(%d)", z[1] or "?", z[2] or 0)
    end
    return table.concat(t, "  ")
end''',
     '''-- 分布列：z[1] 是 **AreaTable 区域 ID**（生成期由 fc_zones.py 换好），名字问客户端。
function PD.ZoneText(list, maxN)
    if not list or #list == 0 then return L["无数据"] end
    local t = {}
    for i, z in ipairs(list) do
        if maxN and i > maxN then t[#t + 1] = "…"; break end
        t[#t + 1] = format("%s(%d)", DG.ZoneName(z[1]), z[2] or 0)
    end
    return table.concat(t, "  ")
end'''),

    ('''        for _, z in ipairs(zones) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, text = z[1] or "?",
                right = format(L["技能 %s"], tostring(z[2])),
            }
        end''',
     '''        for _, z in ipairs(zones) do
            rows[#rows + 1] = {
                kind = "row", h = PD.ROW_H1, text = DG.ZoneName(z[1]),
                right = format(L["技能 %s"], tostring(z[2])),
            }
        end'''),

    ('''    -- 采矿 / 采药：{节点名, 所需技能, {产出物品ID}, {{区域, 节点数}, ...}}
    PushHead(rows, L["节点表（所需技能 → 产出 → 分布）"])
    for _, n in ipairs(g) do
        local items = {}
        for _, id in ipairs(n[3] or {}) do items[#items + 1] = DG.ItemName(id) end
        rows[#rows + 1] = {
            kind = "row", text = n[1] or "?",
            sub = table.concat(items, "  "),
            right = format(L["技能 %d"], n[2] or 0),
            right2 = PD.ZoneText(n[4], 3),
            lines = { { format(L["产出：%s"], table.concat(items, "  ")) },
                      { format(L["分布：%s"], PD.ZoneText(n[4])) } },
        }
    end''',
     '''    -- 采矿 / 采药：{{产出物品ID}, 所需技能, {{区域ID, 节点数}, ...}}
    -- ★ 行标题 = **首个产出物**的客户端中文名（用户 2026-09-24 口径）：站点的节点名是
    --   GameObject 名（Copper Vein / Peacebloom…），客户端没有任何查询口 → 数据表里
    --   不再落节点名。草药的首个产出本来就与节点同名（Peacebloom → 宁神花），
    --   采矿则显示成产物名（Copper Vein → 铜矿石）。
    --   ⚠️ 名字要等客户端到货 → 把该物品挂进 it：PD.RequestRows 才会催它，
    --      到货后 PD.SweepNames 整屏重渲染把占位换成真名（不这么做标题会永远停在占位上）。
    PushHead(rows, L["节点表（所需技能 → 产出 → 分布）"])
    for _, n in ipairs(g) do
        local head = n[1] and n[1][1]
        local items = {}
        for _, id in ipairs(n[1] or {}) do items[#items + 1] = DG.ItemName(id) end
        -- ⚠️ DG.ItemName 返回 (名字, 是否拿到) **两个值** —— 必须分开接，不能整串塞进
        --    format / gsub 的实参位（那是实机崩过的老坑）。
        local nm, got = DG.ItemName(head)
        if not got then nm = head and format(L["物品 #%d"], head) or "?" end
        rows[#rows + 1] = {
            kind = "row", it = head and { head } or nil, text = nm,
            sub = table.concat(items, "  "),
            right = format(L["技能 %d"], n[2] or 0),
            right2 = PD.ZoneText(n[3], 3),
            lines = { { format(L["产出：%s"], table.concat(items, "  ")) },
                      { format(L["分布：%s"], PD.ZoneText(n[3])) } },
        }
    end'''),
]

# ═══════════════════════════════════════════════════════════════════════════
# ④ 网格两列页（钓鱼 → 采集）
# ═══════════════════════════════════════════════════════════════════════════
GRID_CONST = [
    ('''PD.COL_GAP = 12
PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * 0.72)
PD.COL_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.COL_LW''',
     '''PD.COL_GAP = 12
PD.COL_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) * 0.72)
PD.COL_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.COL_LW

-- ── 网格两列页（用户 2026-09-24：钓鱼 → 采集）──
-- ★ 与升级页的「左右分栏」不是一回事：那边左右装的是**两种不同内容**（怎么练 / 要备什么），
--   宽度按内容配比（0.72）；这里左右是**同一个列表折成两栏** —— 每行只有「区域 + 技能」这么点
--   内容，单列时右半幅整片空着。所以两栏**等宽**，行按「哪一栏矮就放哪栏」自动分列，
--   每一节（标题之后）都从同一行起排，读起来仍是 左 右 / 左 右。
-- ★ 标题 / 说明 / 空档在两列页里**通栏**（见 PD.PaintRows 的 span 分支）：否则标题只占左栏、
--   右栏从标题旁边就开始，看不出「这一节从哪起」。'''),

    ('''-- 行池封顶：单个专业最大的分类 79 条，但「全部」能到 512 条。''',
     '''-- 网格两列的两栏宽：**等宽**（为什么不等宽见上）—— 与 COL_LW/COL_RW 的 0.72 配比
-- 是两回事，各自服务一种页面，不要互相套用。
PD.GRID_LW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP) / 2)
PD.GRID_RW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.COL_GAP - PD.GRID_LW

-- 行池封顶：单个专业最大的分类 79 条，但「全部」能到 512 条。'''),
]

GRID_PAINT = [
    ('''-- ★ col 分列机制保留在行池里（行定义带 col 时进第 2 列、两列各一个纵向游标），
--   但当前没有页面再举手要第二列 —— 升级页 2026-09-23 晚改通栏一行式。
function PD.PaintRows(rows)
    local y = { 0, 0 }
    local n = #rows
    local truncated = 0
    if n > PD.ROW_CAP then truncated = n - PD.ROW_CAP; n = PD.ROW_CAP end
    for i = 1, n do
        local spec = rows[i]
        local h = PD.RowHeight(spec)
        local col = (spec.col == 2) and 2 or 1
        local r = PD.Row(i)
        if spec.kind == "gap" then
            r:Hide()
            y[col] = y[col] + h
        else
            local x = (col == 2) and (PD.LIST_PAD + PD.COL_LW + PD.COL_GAP)
                               or PD.LIST_PAD
            -- ★ 宽度**不能**只由 col 决定：单列页的行同样落在 col == 1，若 col=1 恒给 COL_LW，
            --   「配方 / 总览 / 采集 / 传承」等所有单列页的行会一起被压窄半截（第六轮踩过的坑）。
            --   所以先看本屏有没有开两栏（PD.lvSplit）：开了才按 COL_LW / COL_RW 分栏。
            local w
            if PD.lvSplit then
                w = (col == 2) and PD.COL_RW or PD.COL_LW
            else
                w = PD.RIGHT_W - 2 * PD.LIST_PAD
            end
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", x, -y[col])
            r:SetSize(w, h)
            r:Show()
            PD.BindRow(r, spec, h)
            y[col] = y[col] + h + 2
        end
    end''',
     '''-- ★ col 分列机制保留在行池里（行定义带 col 时进第 2 列、两列各一个纵向游标）。
--   两个举手的两列页：升级页（PD.lvSplit，左右不同内容、按 0.72 配比宽）与
--   钓鱼采集页（PD.gridSplit，同一列表折两栏、等宽、自动分列）。
function PD.PaintRows(rows)
    local y = { 0, 0 }
    local n = #rows
    local truncated = 0
    if n > PD.ROW_CAP then truncated = n - PD.ROW_CAP; n = PD.ROW_CAP end
    local grid = PD.gridSplit and true or false
    local ROW_W = PD.RIGHT_W - 2 * PD.LIST_PAD
    for i = 1, n do
        local spec = rows[i]
        local h = PD.RowHeight(spec)
        local r = PD.Row(i)
        -- ★ 两列网格页里的**通栏**元素（标题 / 说明 / 空档）：不吃半栏宽，而是先把两个
        --   列游标拉平到同一条线，再占整幅 —— 每一节都从同一行起排，两栏高度不等也不会
        --   把下一节的第一行甩到半截高处去。
        local span = grid and (spec.kind ~= "row")
        if spec.kind == "gap" then
            r:Hide()
            if span then
                local ny = math.max(y[1], y[2]) + h
                y[1], y[2] = ny, ny
            else
                local col = (spec.col == 2) and 2 or 1
                y[col] = y[col] + h
            end
        else
            local col, x, w, top
            if span then
                top = math.max(y[1], y[2])
                x, w = PD.LIST_PAD, ROW_W
            else
                if spec.col == 2 then
                    col = 2
                elseif grid then
                    -- 自动分列：放进当前**较矮**的那一栏（等高时并列 → 取左，于是 1,2,1,2…）。
                    -- 用「较矮」而不是「上一行放哪栏取反」：行高不等时不会一栏拖长一栏留白。
                    col = (y[2] < y[1]) and 2 or 1
                else
                    col = 1
                end
                top = y[col]
                -- ★ 宽度**不能**只由 col 决定：单列页的行同样落在 col == 1，若 col=1 恒给 COL_LW，
                --   「配方 / 总览 / 采集 / 传承」等所有单列页的行会一起被压窄半截（第六轮踩过的坑）。
                --   所以先看本屏有没有举手要两栏（PD.lvSplit / PD.gridSplit）。
                if PD.lvSplit then
                    x = (col == 2) and (PD.LIST_PAD + PD.COL_LW + PD.COL_GAP) or PD.LIST_PAD
                    w = (col == 2) and PD.COL_RW or PD.COL_LW
                elseif grid then
                    x = (col == 2) and (PD.LIST_PAD + PD.GRID_LW + PD.COL_GAP) or PD.LIST_PAD
                    w = (col == 2) and PD.GRID_RW or PD.GRID_LW
                else
                    x, w = PD.LIST_PAD, ROW_W
                end
            end
            r:ClearAllPoints()
            r:SetPoint("TOPLEFT", PD.child, "TOPLEFT", x, -top)
            r:SetSize(w, h)
            r:Show()
            PD.BindRow(r, spec, h)
            if span then
                y[1], y[2] = top + h + 2, top + h + 2
            else
                y[col] = top + h + 2
            end
        end
    end'''),

    ('''    -- 升级页的左右分栏线：落在两栏之间的 COL_GAP 中线上，纵向与滚动区同高。
    -- 行的左缘在 page 的 RIGHT_X + LIST_PAD 处，第 2 栏再自这里内推 COL_LW + COL_GAP —— 故线位同源。
    if PD.lvSplit then
        local mx = PD.RIGHT_X + PD.LIST_PAD + PD.COL_LW + PD.COL_GAP / 2''',
     '''    -- 分栏线：升级页（左右装不同内容）与钓鱼采集页（同一列表折两栏）都要，
    --   落点都是「第 1 栏宽 + 栏间距中点」—— 行的左缘在 page 的 RIGHT_X + LIST_PAD 处，
    --   第 2 栏再自这里内推「第 1 栏宽 + COL_GAP」，故线位与行位同源，只是栏宽来源不同。
    local splitW
    if PD.lvSplit then splitW = PD.COL_LW
    elseif PD.gridSplit then splitW = PD.GRID_LW end
    if splitW then
        local mx = PD.RIGHT_X + PD.LIST_PAD + splitW + PD.COL_GAP / 2'''),

    ('''    PD.lvSplit = false
    PD.wantTable = false''',
     '''    PD.lvSplit = false
    PD.gridSplit = false
    PD.wantTable = false'''),

    ('''    elseif PD.tab == "gather" then
        PD.RowsGather(rows)''',
     '''    elseif PD.tab == "gather" then
        -- ★ 钓鱼的采集页行很短（区域名 + 技能），单列时右半幅整片空着 → 折成两栏
        --   （用户 2026-09-24）。其它专业的采集页行里有 名称 + 产出 + 分布，仍走单列。
        PD.gridSplit = (PD.cur == "fishing")
        PD.RowsGather(rows)'''),
]

GROUPS = [('左导航去提示框', TOOLTIP), ('区域名取数口', ZONENAME),
          ('采集页区域名/节点名', GATHER), ('网格两列常量', GRID_CONST),
          ('网格两列排版', GRID_PAINT)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='只验锚点，不写盘')
    args = ap.parse_args()

    raw = open(TARGET, 'rb').read()
    crlf = raw.count(b'\r\n') > 0
    src = raw.decode('utf-8')
    if crlf:
        src = src.replace('\r\n', '\n')
        if src.count('\r') != 0:
            die('混了裸 CR —— 先查换行')

    out = src
    n = 0
    for label, pairs in GROUPS:
        for old, new in pairs:
            c = out.count(old)
            if c != 1:
                die('%s：锚点命中 %d 次（要求恰好 1 次）\n---\n%s\n---'
                    % (label, c, old[:220]))
            out = out.replace(old, new)
            n += 1
        print('  ✓ %-20s %d 处' % (label, len(pairs)))

    # 改完自检：这些旧形态必须一个都不剩
    # ⚠️ 串要写足：`n[1] or "?"` 这种短串会命中别处的 `en[1] or "?"`（1309 行），
    #    自检就成了「永真失败」。带上前缀才只指向被改的那一处。
    for bad in ('SetTip(', 'Host.SetTip', 'text = n[1] or "?"', 'z[1] or "?"',
                'PD.COL_LW + PD.COL_GAP / 2'):
        if bad in out:
            die('改完仍残留 %r' % bad)

    print('\n共 %d 处替换；未落盘。' % n)
    if args.check:
        return 0

    text = out.replace('\n', '\r\n') if crlf else out
    data = text.encode('utf-8')
    if crlf and data.count(b'\n') != data.count(b'\r\n'):
        die('写回后出现裸 LF')
    open(TARGET, 'wb').write(data)
    print('已写回 %s（%s，%d 字节）'
          % (os.path.relpath(TARGET, os.path.dirname(HERE)), 'CRLF' if crlf else 'LF', len(data)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""第五刀 · 第二段：掉落行池「先算版式、后分帧建帧」+ boss 卡池分帧。

要点：不手抄那几十行带注释的实码 —— **从原文件里按字节区间抽出来**再搬位置，
这样「版式计算」「上数据」两段都保持与原来一字不差（变异锚点因此全部存活）。

  · takeCard    -> makeRow（只建帧）+ takeRow(make, paint)（顺手记待建表）
  · 列表分支    -> paintRow(r, it, rx, ry) 局部函数 + takeRow(...)
  · 卡片分支    -> 内计数 nI 改名 nR（原先是同名遮蔽，容易误读）；行整体进 takeRow
  · 收尾        -> DG.FlushPendingRows()（量小同步建完 / 量大交分帧器 + 进度条）
  · EnsureCardPool -> 逐批建（DG.BuildCardPool），建完补一次渲染

用法：python _apply_loadgate2.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(DF, 'Core', 'DungeonUI.lua')

raw = io.open(SRC, 'rb').read()
txt = raw.decode('utf-8')
style = '\r\n' if '\r\n' in txt else '\n'
flat = txt.replace('\r\n', '\n')


def rep(old, new, tag):
    global flat
    n = flat.count(old)
    if n != 1:
        print('!! [%s] 锚点命中 %d 次（应为 1）' % (tag, n))
        sys.exit(1)
    flat = flat.replace(old, new, 1)
    print('OK  [%s]' % tag)


def cut(a, b, tag):
    """取出 [a, b) 之间的原文（两端都是精确串）"""
    ia = flat.index(a)
    ib = flat.index(b, ia)
    if ib < 0:
        print('!! [%s] 找不到结束串' % tag)
        sys.exit(1)
    return flat[ia:ib]


def indent(s, n):
    pad = ' ' * n
    return ''.join((pad + l if l.strip() else l) for l in s.splitlines(True))


# ══ ① takeCard → makeRow + takeRow ══════════════════════════════════════
TC_START = '    local function takeCard()\n'
TC_END = '            rows[nI] = r\n        end\n        return r\n    end\n'
ia = flat.index(TC_START)
ib = flat.index(TC_END, ia) + len(TC_END)
old_take = flat[ia:ib]

CB_START = '            r = CreateFrame("Button", nil, child, "BackdropTemplate")\n'
ic = old_take.index(CB_START)
create_block = old_take[ic:]
# 12 空格 → 8 空格
dedented = indent(create_block, -4) if False else '\n'.join(
    (l[4:] if l.startswith('    ') else l) for l in create_block.split('\n'))
db_end = dedented.index('        rows[nI] = r\n')
make_fn = ('    local function makeRow()\n'
           + dedented[:db_end]
           + '        return r\n'
           + '    end\n')

TAKE_FN = '''
    -- ★★★ 第五刀：「行帧还没建」不再当场建，而是记进待建表（DG.__pendRows）。
    --   一本大副本（黑石深渊 168 件 / 通灵学院 292 件）原来在**渲染这一帧**里同步
    --   CreateFrame 出全部行帧 —— 一帧 250+ 个对象，差电脑上主线程一次阻塞上百毫秒
    --   ⇒ Windows 判定无响应、整窗涂灰。
    --   现在渲染只算版式：位置由调用方按原公式算好、连同上数据一起进待建表，随后由
    --   DG.BuildPendRows 按每帧预算逐批建出来。
    --   ★★ 版式一字未改：待建行落点用的仍是同一组坐标 ⇒ 分批建出来的位置与「同步建」
    --      完全一致，离线几何断言比的就是这些坐标。
    --   ★ make(r) 只建帧；paint(r) 摆位 + 上数据（每轮渲染都要跑一次，行帧会被复用）。
    local function takeRow(make, paint)
        nI = nI + 1
        local idx = nI
        local r = rows[idx]
        if r then
            paint(r)
            return
        end
        DG.__pendRows[#DG.__pendRows + 1] = { idx = idx, make = make, paint = paint }
    end
'''
rep(old_take, make_fn + TAKE_FN, 'takeCard -> makeRow + takeRow')

# ══ ② 待建行的落地器（模块级）════════════════════════════════════════════
RECLAIM = '''
-- ★★★ 第五刀：待建行帧的落地与调度 -------------------------------------------
DG.GATE_MIN_SHOW = 24     -- 少于这么多行不闪进度条（闪一下反而比不闪更难受）
DG.ROW_SYNC_MAX = 20      -- 少于这么多行直接同步建完（一帧十几个对象无所谓）

-- 单个待建行：建帧 + 塞进池 + 上数据。**帧已经在池里就跳过**（幂等）。
function DG.RealizePendingRow(e)
    local rows = U.dungeonDetailPool and U.dungeonDetailPool.item
    if not (rows and e) or rows[e.idx] then return end
    local ok, r = pcall(e.make)
    if ok and r then
        rows[e.idx] = r
        if e.paint then pcall(e.paint, r) end
    end
end

-- 逐批建（每帧受 DG.Loader 的时间预算 + DG.LOOT_ROW_FRAME_CAP 夹住）。
function DG.BuildPendRows()
    local list = DG.__pendRows
    local rows = U.dungeonDetailPool and U.dungeonDetailPool.item
    if not (list and rows) then
        DG.__pendRows = {}
        DG.Gate.Finish()
        return
    end
    local t0 = DG.__nowMs()
    local left = DG.LOOT_ROW_FRAME_CAP
    while #list > 0 and left > 0 do
        DG.RealizePendingRow(table.remove(list, 1))
        DG.Gate.Advance(1)
        left = left - 1
        local t1 = t0 and DG.__nowMs()
        if t1 and (t1 - t0) >= DG.Loader.budgetMs then break end
    end
    if #list > 0 then
        DG.PushStep(DG.BuildPendRows)
    else
        DG.Gate.Finish()
    end
end

-- 渲染收尾入口：量小同步建完（快速通道，不闪进度条）；量大交分帧器 + 进度条。
function DG.FlushPendingRows()
    local n = #DG.__pendRows
    if n == 0 then
        DG.Gate.Finish()
        return
    end
    if n < DG.ROW_SYNC_MAX then
        for k = 1, n do DG.RealizePendingRow(DG.__pendRows[k]) end
        DG.__pendRows = {}
        DG.Gate.Finish()
        return
    end
    DG.Gate.Begin(n)
    DG.PushStep(DG.BuildPendRows)
    DG.RunSteps()
end

DG.LOOT_ROW_FRAME_CAP = 24      -- 单帧最多建这么多行帧（数量兜底闸）
'''
rep('DG.__pendRows = {}\n', 'DG.__pendRows = {}\n' + RECLAIM, '待建行落地器')

# ══ ③ pump 抽干时收进度条 ════════════════════════════════════════════════
rep('''            if not fn then
                DG.stepping = false
                return
            end''',
    '''            if not fn then
                DG.stepping = false
                DG.Gate.Finish()          -- ★ 队列抽干 = 这一批活干完了（进度条到此收工）
                return
            end''',
    'pump 收工收进度条')

# ══ ④ 列表分支：if #items == 0 ... else ... end ══════════════════════════
BLK_A = '            if #items == 0 then\n'
BLK_B = '            y = y - DG.LOOT_GRP_GAP\n'
old_blk = cut(BLK_A, BLK_B, '列表分支')

E0 = '                local r = takeCard()\n'
E1 = '                y = y - stepY\n'
empty_body = cut2 = None
ie0 = old_blk.index(E0) + len(E0)
ie1 = old_blk.index(E1)
empty_body = old_blk[ie0:ie1]
assert 'r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)' in empty_body
empty_body = empty_body.replace('r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, y)',
                                'r:SetPoint("TOPLEFT", child, "TOPLEFT", 0, baseY)')

I0 = '                for i, it in ipairs(items) do\n'
I1 = '                y = y - math.ceil(#items / cols) * stepY\n'
ii0 = old_blk.index(I0) + len(I0)
ii1 = old_blk.index(I1)
item_body = old_blk[ii0:ii1]
assert '                    local r = takeCard()\n' in item_body
item_body = item_body.replace('                    local r = takeCard()\n', '')
# ★ 区间的尾巴带着「for 循环自己的 end」——必须摘掉，否则 paintRow 会多出一个 end
LOOP_TAIL = '                end\n'
assert item_body.endswith(LOOP_TAIL), repr(item_body[-60:])
item_body = item_body[:-len(LOOP_TAIL)]
SP_OLD = ('                    r:SetPoint("TOPLEFT", child, "TOPLEFT",\n'
          '                               ((i - 1) % cols) * stepX, y - math.floor((i - 1) / cols) * stepY)\n')
assert SP_OLD in item_body
item_body = item_body.replace(SP_OLD, '                    r:SetPoint("TOPLEFT", child, "TOPLEFT", rx, ry)\n')
assert '                    r:SetSize(cw, DG.LOOT_CARD_H)\n' in item_body

new_blk = (
    '            if #items == 0 then\n'
    '                local baseY = y\n'
    '                takeRow(makeRow, function(r)\n'
    + indent(empty_body, 4) +
    '                end)\n'
    '                y = y - stepY\n'
    '            else\n'
    '                local baseY = y\n'
    '                -- ★ 单行摆位 + 上数据（原样搬进来，只把「取行」换成 takeRow）\n'
    '                local function paintRow(r, it, rx, ry)\n'
    + item_body +
    '                end\n'
    '                for i, it in ipairs(items) do\n'
    '                    local rx = ((i - 1) % cols) * stepX\n'
    '                    local ry = baseY - math.floor((i - 1) / cols) * stepY\n'
    '                    takeRow(makeRow, function(r) paintRow(r, it, rx, ry) end)\n'
    '                end\n'
    '                y = y - math.ceil(#items / cols) * stepY\n'
    '            end\n'
)
rep(old_blk, new_blk, '列表分支改 takeRow')

# ══ ⑤ 列表分支收尾 → FlushPendingRows ════════════════════════════════════
rep('''    for i = nH + 1, #hdr do hdr[i].name:Hide(); hdr[i].cnt:Hide() end
    for i = nI + 1, #rows do rows[i]:Hide() end
''',
    '''    for i = nH + 1, #hdr do hdr[i].name:Hide(); hdr[i].cnt:Hide() end
    for i = nI + 1, #rows do rows[i]:Hide() end
    DG.FlushPendingRows()          -- ★ 这一轮排下的待建行：量小同步、量大分帧
''',
    '列表收尾 Flush')

# ══ ⑥ 卡片视图：签名 / 计数 / 行循环 ══════════════════════════════════════
rep('    U:RenderDungeonLootCards(groups, filter, takeCard)\n',
    '    U:RenderDungeonLootCards(groups, filter, takeRow, makeRow)\n',
    '卡片分派传参')

rep('function U:RenderDungeonLootCards(groups, filter, takeCard)\n',
    'function U:RenderDungeonLootCards(groups, filter, takeRow, makeRow)\n',
    '卡片函数签名')

rep('    if not (d and child and pool and takeCard) then return end\n',
    '    if not (d and child and pool and takeRow and makeRow) then return end\n',
    '卡片函数守卫')

rep('    local nC, nI = 0, 0\n',
    '    local nC, nR = 0, 0\n',
    '卡片内计数改名 nR')

rep('''    for i = nC + 1, #cards do cards[i]:Hide() end
    for i = nI + 1, #rows do rows[i]:Hide() end
''',
    '''    for i = nC + 1, #cards do cards[i]:Hide() end
    for i = nR + 1, #rows do rows[i]:Hide() end
    DG.FlushPendingRows()          -- ★ 同上：待建行按预算落地
''',
    '卡片收尾 Flush')

C0 = '            for ii = 1, n do\n'
C1 = '                r:Show()\n            end\n'
old_card = cut(C0, C1, '卡片行循环') + C1
b0 = old_card.index('                local r = takeCard()\n') + len('                local r = takeCard()\n')
b1 = old_card.index('                r:Show()\n')
card_body = old_card[b0:b1]
assert '                nI = nI + 1\n' in card_body
card_body = card_body.replace('                nI = nI + 1\n', '')
assert '                local it = items[ii]\n' in card_body
card_body = card_body.replace('                local it = items[ii]\n', '')
SP_OLD2 = ('                r:SetPoint("TOPLEFT", child, "TOPLEFT", cx + DG.LOOT_CARD_PAD,\n'
           '                           cy - DG.LOOT_CARD_HDR_H - (ii - 1) * (DG.LOOT_CARD_H + DG.LOOT_CARD_ROW_GAP))\n')
assert SP_OLD2 in card_body
card_body = card_body.replace(SP_OLD2, '                r:SetPoint("TOPLEFT", child, "TOPLEFT", rx, ry)\n')

new_card = (
    '            for ii = 1, n do\n'
    '                nR = nR + 1\n'
    '                local it = items[ii]\n'
    '                local rx = cx + DG.LOOT_CARD_PAD\n'
    '                local ry = cy - DG.LOOT_CARD_HDR_H - (ii - 1) * (DG.LOOT_CARD_H + DG.LOOT_CARD_ROW_GAP)\n'
    '                takeRow(makeRow, function(r)\n'
    + indent(card_body, 4) +
    '                end)\n'
    '            end\n'
)
rep(old_card, new_card, '卡片行循环改 takeRow')

# ══ ⑦ 每轮渲染开头重置待建表 ═════════════════════════════════════════════
rep('''    local loot = (ns.DungeonLoot or {})[d.id] or {}

    local counts = { all = 0, weapon = 0, armor = 0, quest = 0, new = 0 }''',
    '''    local loot = (ns.DungeonLoot or {})[d.id] or {}
    -- ★★★ 第五刀：上一轮排下、还没建的行帧必须整体丢掉 —— 否则玩家已经点到别的副本，
    --   它们随后建出来就会在新页面上冒出来（版式属于上一本）。
    DG.__pendRows = {}

    local counts = { all = 0, weapon = 0, armor = 0, quest = 0, new = 0 }''',
    '列表渲染开头重置待建表')

rep('''    local cards, rows = pool.card, pool.item
    if not (cards and rows) then return end
    local loot = (ns.DungeonLoot or {})[d.id] or {}''',
    '''    local cards, rows = pool.card, pool.item
    if not (cards and rows) then return end
    local loot = (ns.DungeonLoot or {})[d.id] or {}
    DG.__pendRows = {}             -- ★ 同列表路：清掉上一轮排下、还没建的行''',
    '卡片渲染开头重置待建表')

# ─────────────────────────────────────────────────────────────────────────
out = flat.replace('\n', style)
io.open(SRC, 'wb').write(out.encode('utf-8'))
crlf = out.count('\r\n')
print('字节 %d，CRLF %d，裸 LF %d' % (len(out.encode('utf-8')), crlf, out.count('\n') - crlf))
assert out.count('\n') - crlf == 0, '有裸 LF'
print('完成')

# -*- coding: utf-8 -*-
"""第五刀 · 第三段：boss 卡池（29 张 / ≈290 纹理）从「一帧建全」改为逐批建。

  · EnsureCardPool  -> 只登记 + 起分帧（DG.BuildCardPool）
  · NewBossCard     -> 单卡建帧整段（从原 for 循环里按字节抽出来，原缩进一字不动）
  · 建完补一次渲染（分帧窗口里 RenderDungeonLootCards 见不到卡 ⇒ 会提前收工）
  · RenderDungeonLootCards 加「池没建完先别画」的提前返回（免得把行池误收干净）

用法：python _apply_loadgate3.py
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


# ── ① 从原 for 循环里抽出「建一张卡」的整段（原缩进保留）──────────────────
LOOP0 = '        for i = 1, DG.LOOT_CARD_MAX do\n'
LOOP1 = '            pool.card[i] = c\n        end\n'
ia = flat.index(LOOP0) + len(LOOP0)
ib = flat.index(LOOP1, ia)
body = flat[ia:ib]
assert 'local c = CreateFrame("Frame", nil, dchild)\n' in body
assert body.rstrip('\n').endswith('c:Hide()')

NEW_FN = ('''-- ★★★ 第五刀：单张 boss 卡的建帧整段（原样搬出来，**原缩进一字未动** ——
--   里面那几处 SetPoint 是变异锚点，重排缩进会把它们打散；缩进在这里只是观感）。
function DG.NewBossCard(dchild, arrow)
'''
          + body
          + '''    return c
end

-- boss 卡池分帧：一次最多建 DG.CARD_POOL_CAP 张，剩下的排到下一帧（时间闸同时生效）。
DG.CARD_POOL_CAP = 6
-- 卡池是否已经建满（渲染路径据此决定「先别画，等池子好」）。
function DG.CardPoolReady()
    return (DG.__cardPoolI or 0) >= (DG.LOOT_CARD_MAX or 0)
end

function DG.BuildCardPool()
    local dchild = U.dungeonDetailChild
    local pool = U.dungeonDetailPool
    if not (dchild and pool and pool.card) then return end
    local n = DG.LOOT_CARD_MAX or 0
    local i = DG.__cardPoolI or 0
    local t0 = DG.__nowMs()
    local left = DG.CARD_POOL_CAP
    local arrow = "Interface\\\\AddOns\\\\DungeonsForever\\\\Media\\\\textures\\\\arrow.tga"
    while i < n and left > 0 do
        i = i + 1
        pool.card[i] = DG.NewBossCard(dchild, arrow)
        left = left - 1
        local t1 = t0 and DG.__nowMs()
        if t1 and (t1 - t0) >= DG.Loader.budgetMs then break end
    end
    DG.__cardPoolI = i
    if i < n then
        DG.PushStep(DG.BuildCardPool)
    elseif (U.lootView or "list") == "card" and U.dungeonDetailCur then
        -- ★ 收尾补渲染：卡池建好时若正停在「卡片」视图，得把内容画出来 ——
        --   分帧窗口里 RenderDungeonLootCards 见不到还没建的卡，只能提前收工。
        DG.PushStep(function() U:RenderDungeonLoot() end)
    end
end

''')

# ── ② 换掉 EnsureCardPool 的整段（登记 + 起分帧）──────────────────────────
ENS_START = 'function DG.EnsureCardPool()\n'
ENS_END = '    end\n\nend\n'
ja = flat.index(ENS_START)
jb = flat.index(ENS_END, ja) + len(ENS_END)
old_ens = flat[ja:jb]
assert 'DG.LOOT_CARD_MAX = math.max(maxG, 6)' in old_ens

NEW_ENS = ('''function DG.EnsureCardPool()
    if U.cardPoolBuilt then return end
    local dchild, pool = U.dungeonDetailChild, U.dungeonDetailPool
    if not (dchild and pool) then return end
    U.cardPoolBuilt = true
    -- ★★ boss 卡池（卡片视图专用，2026-10-01）--------------------------------------------
    --   一个来源一张卡，池上限 = 扫一遍全库取「单副本来源数最大值」（当前 29 = 黑石深渊）。
    --   卡片是 child 的普通子帧（不带 BackdropTemplate —— 圆角底走 HUI 原语 BuildRoundedBG，
    --   与地图页三张分组卡 / 团本页卡墙同一套）；EnableMouse(false) ⇒ 卡内空白处滚轮穿透。
    --   卡头热区（c.hit）才是可点控件：折叠键必须挂在**它**身上（挂卡帧 ⇒ self.__key 恒 nil）。
    --   ★★★ 第五刀：池子改为**逐批建**（见 DG.BuildCardPool）—— 29 张卡 ≈ 290 个纹理，
    --     原来一帧建全 = 切到「卡片」视图那一下卡一下；现在按每帧预算摊开。
    pool.card = {}
    local maxG = 0
    for _, srcs in pairs(ns.DungeonLoot or {}) do
        local n = #srcs
        if n > maxG then maxG = n end
    end
    DG.LOOT_CARD_MAX = math.max(maxG, 6)
    DG.__cardPoolI = 0
    DG.PushStep(DG.BuildCardPool)
    DG.RunSteps()
end

''')
rep(old_ens, NEW_ENS, 'EnsureCardPool 改逐批建')

# ── ③ 插入 NewBossCard / BuildCardPool（放在 EnsureCardPool 之前）────────
rep('-- ══ 详情页四个「重池」（幂等；分帧 + 按需同步双入口）══════════════════════\n',
    '-- ══ 详情页四个「重池」（幂等；分帧 + 按需同步双入口）══════════════════════\n'
    + NEW_FN,
    'NewBossCard + BuildCardPool')

# ── ④ 池没建完先别画（否则会把行池整池收干净 = 闪一下空白）──────────────
rep('''    local cards, rows = pool.card, pool.item
    if not (cards and rows) then return end
    local loot = (ns.DungeonLoot or {})[d.id] or {}''',
    '''    local cards, rows = pool.card, pool.item
    if not (cards and rows) then return end
    -- ★ 卡池还在分帧建 ⇒ 先别画：这时候 cards[nC] 是 nil，走到下面会把行池整池收干净
    --   （列表视图的行全被 Hide = 闪一下空白）。等池子建满后由 DG.BuildCardPool 收尾补渲染。
    if not DG.CardPoolReady() then return end
    local loot = (ns.DungeonLoot or {})[d.id] or {}''',
    '卡池未就绪先不画')

out = flat.replace('\n', style)
io.open(SRC, 'wb').write(out.encode('utf-8'))
crlf = out.count('\r\n')
print('字节 %d，CRLF %d，裸 LF %d' % (len(out.encode('utf-8')), crlf, out.count('\n') - crlf))
assert out.count('\n') - crlf == 0, '有裸 LF'
print('完成')

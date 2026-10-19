# -*- coding: utf-8 -*-
"""第六刀（续）· boss 卡池进载入闸门。

背景：第四刀已经让「切卡片视图」那一帧不建卡（RunSteps 首块也排到下一帧）、
第五刀又把卡池改成每帧 ≤ DG.CARD_POOL_CAP 张；**但这条链没进 DG.Gate**：
  · 切到卡片视图后那 5 个块是「静默」跑的（顶部细条不亮、也没有跳过键）；
   · 进度分母口径与行池不一致（行池 Begin(行数)，卡池啥都不 Begin）。
本次三处：
  ① DG.BuildCardPool：首块调 DG.Gate.Begin(卡数) + 每建一张 DG.Gate.Advance(1)；
     ★ Begin 放在**首块**而不是 DG.EnsureCardPool —— 切视图那一帧必须零帧
       （harness 有 `FRAMES == _fPre` 钉着），连进度条都不该在那一帧建。
  ② DG.EnsureCardPool：补 DG.__cardPoolBegun = nil（每本重置，幂等重建时不带着上一轮的状态）。
  ③ /dfgate demo：把 DG.CARD_POOL_CAP 一起放宽到 1 并纳入 DEMO_SAVE/EndDemo 还原；
     若当前正停在「卡片」视图，顺带把卡池清掉重来（清前先 Hide 旧卡帧，否则两份卡叠着）
     ⇒ 卡片视图那条进度条同样能肉眼复现。

★ 锚点全部按字面相邻的代码行写、文件里唯一；改完仍须 CRLF、裸 LF 必须为 0。
"""
import io
import sys

P = 'Core/DungeonUI.lua'

PATCHES = []

# ── ① 卡池逐张进闸门 ────────────────────────────────────────────────────────
PATCHES.append((
    '卡池 Begin/Advance',
    '    local n = DG.LOOT_CARD_MAX or 0\r\n'
    '    local i = DG.__cardPoolI or 0\r\n'
    '    local t0 = DG.__nowMs()\r\n'
    '    local left = DG.CARD_POOL_CAP\r\n',
    '    local n = DG.LOOT_CARD_MAX or 0\r\n'
    '    local i = DG.__cardPoolI or 0\r\n'
    '    -- ★★★ 第六刀（续）：卡池也进载入闸门 —— 进度分母 = 这一本要建的总卡数。\r\n'
    '    --   ★ Begin 放**首块**而**不是** DG.EnsureCardPool：切「卡片」视图那一帧\r\n'
    '    --     必须零新建帧（harness 有 `FRAMES == _fPre` 钉着），连进度条都不该\r\n'
    '    --     在那一帧建出来 —— 那一帧是玩家手指底下的那一帧。\r\n'
    '    if not DG.__cardPoolBegun then\r\n'
    '        DG.__cardPoolBegun = true\r\n'
    '        DG.Gate.Begin(n)\r\n'
    '    end\r\n'
    '    local t0 = DG.__nowMs()\r\n'
    '    local left = DG.CARD_POOL_CAP\r\n'))

PATCHES.append((
    '卡池每张 Advance',
    '        pool.card[i] = DG.NewBossCard(dchild, arrow)\r\n'
    '        left = left - 1\r\n',
    '        pool.card[i] = DG.NewBossCard(dchild, arrow)\r\n'
    '        DG.Gate.Advance(1)\r\n'
    '        left = left - 1\r\n'))

# ── ② 每本重置「已 Begin」旗标 ─────────────────────────────────────────────
PATCHES.append((
    'EnsureCardPool 重置旗标',
    '    DG.LOOT_CARD_MAX = math.max(maxG, 6)\r\n'
    '    DG.__cardPoolI = 0\r\n'
    '    DG.PushStep(DG.BuildCardPool)\r\n',
    '    DG.LOOT_CARD_MAX = math.max(maxG, 6)\r\n'
    '    DG.__cardPoolI = 0\r\n'
    '    DG.__cardPoolBegun = nil\r\n'
    '    DG.PushStep(DG.BuildCardPool)\r\n'))

# ── ③ 演示：卡池也放宽 + 卡片视图下清池重来 ─────────────────────────────────
PATCHES.append((
    'StartDemo 存卡池额度',
    '        rowCap   = DG.LOOT_ROW_FRAME_CAP,\r\n'
    '    }\r\n',
    '        rowCap   = DG.LOOT_ROW_FRAME_CAP,\r\n'
    '        cardCap  = DG.CARD_POOL_CAP,\r\n'
    '    }\r\n'))

PATCHES.append((
    'StartDemo 放宽卡池额度',
    '    DG.LOOT_ROW_FRAME_CAP = 2     -- 每帧只建 2 行 ⇒ 才看得清（正式值 16）\r\n',
    '    DG.LOOT_ROW_FRAME_CAP = 2     -- 每帧只建 2 行 ⇒ 才看得清（正式值 16）\r\n'
    '    DG.CARD_POOL_CAP      = 1     -- 每帧只建 1 张卡 ⇒ 卡片视图那条条也看得清（正式值 6）\r\n'))

PATCHES.append((
    'StartDemo 清卡池',
    '    if U.dungeonDetailCur then U:SetDungeonTab("loot") end\r\n',
    '    -- ★ 正停在「卡片」视图时把 boss 卡池也清掉重来 ⇒ 卡片那条进度条同样能复现。\r\n'
    '    --   清之前先 Hide 旧卡帧：卡池表一清，旧帧还挂在 child 上 ⇒ 两份卡叠着。\r\n'
    '    if (U.lootView or "list") == "card" and U.dungeonDetailPool then\r\n'
    '        local cs = U.dungeonDetailPool.card\r\n'
    '        if cs then\r\n'
    '            for i = #cs, 1, -1 do cs[i]:Hide() end\r\n'
    '        end\r\n'
    '        U.cardPoolBuilt = nil\r\n'
    '        DG.__cardPoolI = 0\r\n'
    '    end\r\n'
    '    if U.dungeonDetailCur then U:SetDungeonTab("loot") end\r\n'))

PATCHES.append((
    'EndDemo 还原卡池额度',
    '    DG.LOOT_ROW_FRAME_CAP = s.rowCap\r\n',
    '    DG.LOOT_ROW_FRAME_CAP = s.rowCap\r\n'
    '    DG.CARD_POOL_CAP      = s.cardCap or 6\r\n'))


def main():
    with io.open(P, 'rb') as f:
        data = f.read()
    txt = data.decode('utf-8')
    for name, old, new in PATCHES:
        n = txt.count(old)
        if n != 1:
            print('FAIL: [%s] 锚点命中 %d 次（期望 1）' % (name, n))
            return 1
        txt = txt.replace(old, new)
        print('  已改：%s' % name)
    out = txt.encode('utf-8')
    bare = out.count(b'\n') - out.count(b'\r\n')
    if bare != 0:
        print('FAIL: 出现裸 LF %d 个' % bare)
        return 1
    with io.open(P, 'wb') as f:
        f.write(out)
    print('OK: boss 卡池已进闸门；bytes=%d CRLF=%d 裸LF=0'
          % (len(out), out.count(b'\r\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""DungeonUI.lua：① 分帧器「首块不抢当前帧」；② 预建链摘掉 boss 卡池与地图页。

背景（2026-10-03「点副本就卡死」第四刀，用户拍板「按 2 做」）：
  · 实测首次点开任意副本 = 284 帧 / 2098 纹理 / 342 字体串，且**与副本数据量无关**
    （挖掘场 10 件与通灵学院 292 件首开代价一模一样）⇒ 全是「池按全局上限预建」的固定开销。
  · 拆开看：地图页整页 138 帧 / 1153 纹理、boss 卡池 58 帧 / 580 纹理，两块都是
    「用到才需要」的东西，却被无条件下进预建链；而 DG.RunSteps 的 pump() 是**裸调**，
    所以「点击那一帧」同步吃掉队列第一块（外壳 80 + 卡池 58 = 138 帧直接砸在手指上）。
  · 修法：① pump 首块排到下一帧（C_Timer 不可用时同步兜底，离线契约不破）；
          ② 卡池 / 地图页移出预建链，改由各自的渲染入口按需补建（它们本来就有 Ensure* 兜底）；
          ③ 地图页自身再拆成「外壳同步 + 四个重池逐帧」（见 Core/MapUI.lua）。

只改 Core/DungeonUI.lua（CRLF）。用法：python _temp/_apply_lazychain.py
"""
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PATH = os.path.join(ROOT, 'Core', 'DungeonUI.lua')

data = open(PATH, 'rb').read()
assert data.count(b'\r\n') == data.count(b'\n'), 'DungeonUI.lua 必须全 CRLF'

shutil.copyfile(PATH, os.path.join(HERE, '_bak_DungeonUI_lazychain.lua.bak'))


def j(*lines):
    return ('\r\n'.join(lines) + '\r\n').encode('utf-8')


def rep(old, new, tag):
    global data
    n = data.count(old)
    assert n == 1, '%s: 锚点命中 %d 次（应恰好 1 次）' % (tag, n)
    data = data.replace(old, new, 1)
    print('  ✓ %s' % tag)


# ── ① RunSteps：首块也排到下一帧 ────────────────────────────────────────────
rep(j('            DG.stepping = false',
      '        end',
      '    end',
      '    pump()',
      'end'),
    j('            DG.stepping = false',
      '        end',
      '    end',
      '    -- ★★★ 2026-10-03「点副本就卡死」第四刀：**首块也不抢当前帧**。',
      '    --   此前这里是裸的 `pump()` —— 「点开副本」那一帧会同步吃掉队列第一块',
      '    --   （实测正是 MapUI 整页 138 帧 / 945 纹理那一坨，砸在玩家点下去的那一下）。',
      '    --   现在统一排到下一帧；只有 C_Timer 不可用（离线桩 / 极端环境）才同步兜底，',
      '    --   保证「调用方返回时一切就绪」这条离线契约不破。',
      '    if type(C_Timer) == "table" and type(C_Timer.After) == "function" then',
      '        C_Timer.After(0, pump)',
      '    else',
      '        pump()',
      '    end',
      'end'),
    'RunSteps 首块异步')

# ── ② 预建链：摘掉卡池 + 地图页 ────────────────────────────────────────────
rep(j('    -- ★ 分帧：四块重池摊到随后的空闲帧里建（首屏只付壳体 ≈ 25 帧）。',
      '    --   每块都幂等；切页/切视图时若还没轮到，会由对应的 Ensure* 同步补建。',
      '    DG.PushStep(DG.EnsureCardPool)',
      '    DG.PushStep(DG.EnsureQuestLane)',
      '    DG.PushStep(DG.EnsureGuideLane)',
      '    DG.PushStep(DG.EnsureMapPage)',
      '    DG.RunSteps()'),
    j('    -- ★ 分帧：重池摊到随后的空闲帧里建（首屏只付壳体 ≈ 25 帧）。',
      '    --   每块都幂等；切页/切视图时若还没轮到，会由对应的 Ensure* 同步补建。',
      '    --',
      '    -- ★★★ 2026-10-03「点副本就卡死」第四刀：**不再预建 boss 卡池与地图页**。',
      '    --   实测这两块是首开成本的大头，且都属于「用到才需要」：',
      '    --     · boss 卡池（58 帧 / 580 纹理）只有掉落页切到「卡片」视图才用 ——',
      '    --       RenderDungeonLootCards / U:SetLootView 自己会补建（DG.EnsureCardPool）；',
      '    --     · 地图页（138 帧 / 1153 纹理）只有切到「地图」页签才用 ——',
      '    --       U:RenderDungeonTab 的 map 分支自己会补建（DG.EnsureMapPage）。',
      '    --   预建 = 玩家点开副本时白付 196 帧，正好砸在点下去那一下。',
      '    --   ★ 任务两栏 / 攻略栏仍预建：各只是两个滚动容器 + 几行文字，很轻，且是常用页签。',
      '    DG.PushStep(DG.EnsureQuestLane)',
      '    DG.PushStep(DG.EnsureGuideLane)',
      '    DG.RunSteps()'),
    '预建链摘掉卡池 + 地图页')

open(PATH, 'wb').write(data)
print('DungeonUI.lua：字节 %d，CRLF %d，裸 LF %d'
      % (len(data), data.count(b'\r\n'), data.count(b'\n') - data.count(b'\r\n')))
for probe in ('C_Timer.After(0, pump)', 'DG.PushStep(DG.EnsureCardPool)',
              'DG.PushStep(DG.EnsureMapPage)', 'DG.PushStep(DG.EnsureQuestLane)',
              'DG.PushStep(DG.EnsureGuideLane)'):
    print('  %-34s x%d' % (probe, data.count(probe.encode())))

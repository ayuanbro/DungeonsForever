# -*- coding: utf-8 -*-
"""MapUI.lua：把 M.Build 拆成「外壳同步 + 四个重池逐帧 + 收尾补渲染」。

★ 关键手法：四个重池的**原代码块按行原样搬运**到新的 local function 里，不重排、不改缩进
  —— 因为「模块级 local function（函数体 4 空格）」与「M.Build 内一层 for（循环体 8 空格）」
  的缩进完全一致，搬完每条代码行逐字节不变 ⇒ 现有变异锚点一个都不会失配。
  （_anchor_range.py 已核对：M.Build 内共 5 条锚点，全是单行/相邻两行，缩进必须保持一致。）

只改 Core/MapUI.lua（LF）。用法：python _temp/_apply_mapstage.py
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PATH = os.path.join(ROOT, 'Core', 'MapUI.lua')

data = open(PATH, encoding='utf-8').read()
assert '\r' not in data, 'MapUI.lua 应为 LF'
lines = data.split('\n')          # 行号 = 下标 + 1


def L(a, b):
    """取 1-based 闭区间 [a, b] 的行，返回 list[str]。"""
    return lines[a - 1:b]


def chk(a, want_prefix, tag):
    got = lines[a - 1]
    assert got.startswith(want_prefix), '%s: 第 %d 行应为 %r，实际 %r' % (tag, a, want_prefix, got)


# ── 边界核对（错一行就整个方案失准，先钉死）───────────────────────────────
chk(561, 'function M.Build(detail, hero)', 'M.Build 头')
chk(562, '    local frame = CreateFrame', '外壳起点')
chk(597, '    pins:Hide()', '外壳 A 终点')
chk(599, '    local pinBtns = {}', '钉点池起点')
chk(620, '    end', '钉点池终点')
chk(622, '    -- 楼层按钮条', '外壳 B 起点')
chk(694, '    listNote:Hide()', '外壳 B 终点')
chk(696, '    local listRows = {}', '列表行池起点')
chk(718, '    end', '列表行池终点')
chk(720, '    -- 详情模式', '外壳 C 起点')
chk(738, '    detName:SetWordWrap(false)', '外壳 C 终点')
chk(745, '    local blocks = {}', '卡片块起点')
chk(796, '    blkLoot.hit.__key, blkSkill.hit.__key, blkGuide.hit.__key = "loot", "skill", "guide"',
    '卡片块中段')
chk(815, '    detGd:SetWordWrap(true)', '卡片块终点')
chk(817, '    -- 掉落行池', '行池起点')
chk(889, '    end', '行池终点')
chk(891, '    frame.canvas = canvas', '赋值段起点')
chk(927, 'end', 'M.Build 尾')
chk(929, 'function M.WheelScroll', '后继函数')

SHELL_A = L(562, 597)
PINS = L(599, 620)
SHELL_B = L(622, 694)
LISTROWS = L(696, 718)
SHELL_C = L(720, 738)
BLOCKS = L(745, 815)
ROWS = L(817, 889)


def indent(block, pad):
    return [(' ' * pad + s if s.strip() else s) for s in block]


HEAD = '''-- ── 构建（外壳同步 + 重池逐帧；渲染路径零新建帧）────────────────────────────
--
-- ★★★ 2026-10-03「点副本就卡死」第四刀：整页一次 Build 实测 **138 帧 / 1153 纹理 /
--   202 字体串**，且其中 **30 条首领行 + 30 条掉落行 + 16 个钉点 + 3 张分组卡**占绝对多数，
--   而它们绝大多数时间根本用不上（列表模式看不见卡片；没切到地图页时整页都看不见）。
--   于是改成「外壳同步 + 四个重池逐帧 + 收尾补渲染」：
--     · 外壳（画布 / 12 块瓦片 / 空态 / 钉点容器 / 楼层面条 / 隐藏 boss 开关 / 右栏三容器）
--       同步建 —— 只有几十个对象，切到地图页那一刻不吃力，地图画面也立刻出得来；
--     · 四个重池走 DG.PushStep 逐帧建：钉点 → 首领列表行 → 三张分组卡 → 掉落行 / 技能行；
--     · 每块幂等；**池没建好时 SyncBar / SyncPins / SyncSide 一律安全空转**（各自开头的就绪判断），
--       所以「刚切到地图页、池还在建」的那几帧既不报错、也不会画出半吊子内容；
--     · 最后一块（M.EnsureFinal）建完补一次渲染 —— 右栏与钉点最坏 ~0.1s 内补齐。
--   ★ 离线（C_Timer 不可用）由 DG.PushStep 的同步兜底一次跑完 ⇒ 断言看到的仍是全量。
--   ★ 顺序有依赖：卡片块必须排在行块之前 —— 掉落行 / 技能行的父帧就是那三张卡。
--
-- 帧只在 Build / Ensure* 里建一次（12 块贴图 + 楼层按钮池 + 钉点池 + 列表/掉落/技能行池）；
-- Paint / 选中 / 切层只改贴图、文字与显隐，零新建帧。

-- ① 钉点池（16 个 boss 钉点：骷髅贴图 + 圆角遮罩 + 名字）
local function BuildPins(frame)
    if frame.poolPins then return end
    frame.poolPins = true
    local pins = frame.pins
{PINS}
    frame.pinBtns = pinBtns
end

-- ② 右栏「首领列表」行池（30 行）
local function BuildListRows(frame)
    if frame.poolList then return end
    frame.poolList = true
    local listChild, innerW = frame.listChild, frame.innerW
{LISTROWS}
    frame.listRows = listRows
end

-- ③ 右栏详情模式的三张分组卡（卡帧 + 卡头热区 + 折叠箭头 + 标题）
local function BuildBlocks(frame)
    if frame.poolBlocks then return end
    frame.poolBlocks = true
    local detChild, innerW = frame.detChild, frame.innerW
{BLOCKS}
    frame.blkLoot, frame.blkSkill, frame.blkGuide = blkLoot, blkSkill, blkGuide
    frame.detLtTtl, frame.detLtCnt, frame.detLtNote = detLtTtl, detLtCnt, detLtNote
    frame.detSkTtl = detSkTtl
    frame.detGdTtl, frame.detGd = detGdTtl, detGd
end

-- ④ 掉落行池 + 技能行池（父 = 「掉落」/「boss技能」两张卡）
local function BuildSideRows(frame)
    if frame.poolRows then return end
    frame.poolRows = true
    local innerW = frame.innerW
    local blkLoot, blkSkill = frame.blkLoot, frame.blkSkill
{ROWS}
    frame.lootRows, frame.skillRows = lootRows, skillRows
end

-- ⑤ 收尾：池全部就位。此刻若正停在地图页，补一次渲染
--   （分帧窗口内的 SyncBar / SyncPins / SyncSide 都空转了，右栏与钉点还空着）
local function BuildFinal(frame)
    if frame.poolsBuilt then return end
    frame.poolsBuilt = true
    if frame:IsShown() then M.Paint(M.curD) end
end
-- 供 harness / 变异测试点名调用（也是 M.Build 内排队用的就是这几个引用）
M.EnsurePins = BuildPins
M.EnsureListRows = BuildListRows
M.EnsureBlocks = BuildBlocks
M.EnsureSideRows = BuildSideRows
M.EnsureFinal = BuildFinal

function M.Build(detail, hero)
{SHELL_A}
{SHELL_B}
{SHELL_C}

    -- ── 池化字段（外壳部分；四个重池的字段由各自的分帧块补）──
    frame.canvas = canvas
    frame.tiles = tiles
    frame.customTex = customTex
    frame.empty = empty
    frame.pins = pins
    frame.bar = bar
    frame.btns = btns
    frame.bossBtn = bossBtn
    frame.innerW = innerW
    frame.side = side
    frame.listScroll = listScroll
    frame.listChild = listChild
    frame.listHdr = listHdr
    frame.listNote = listNote
    frame.detScroll = detScroll
    frame.detChild = detChild
    frame.detBack = detBack
    frame.detName = detName
    frame.detChildW = innerW - M.BLK_PAD * 2
    -- 「隐藏 boss」开关状态：与 dungeonTab / dungeonView 同一张存档表（跨角色共享）；
    -- 缺省 nil = 不隐藏。**布尔化再存 M**（存档里可能是任意历史值，直接当条件用会埋雷）。
    M.hideBoss = (DungeonsForeverDB and DungeonsForeverDB.dungeon
                  and DungeonsForeverDB.dungeon.mapBossHidden) and true or false
    M.frame = frame
    -- ── 重活一律不占当前帧：四个池 + 收尾全部排队 ──
    local queued = (type(DG) == "table" and type(DG.PushStep) == "function")
    if queued then
        DG.PushStep(BuildPins)
        DG.PushStep(BuildListRows)
        DG.PushStep(BuildBlocks)
        DG.PushStep(BuildSideRows)
        DG.PushStep(BuildFinal)
        DG.RunSteps()
    else
        -- 同步兜底（离线桩 / 极端环境）：调用方返回时一切就绪
        BuildPins(frame)
        BuildListRows(frame)
        BuildBlocks(frame)
        BuildSideRows(frame)
        BuildFinal(frame)
    end
    return frame
end'''

HEAD = (HEAD
        .replace('{PINS}', '\n'.join(PINS))
        .replace('{LISTROWS}', '\n'.join(LISTROWS))
        .replace('{BLOCKS}', '\n'.join(BLOCKS))
        .replace('{ROWS}', '\n'.join(indent(ROWS, 0)))
        .replace('{SHELL_A}', '\n'.join(SHELL_A))
        .replace('{SHELL_B}', '\n'.join(SHELL_B))
        .replace('{SHELL_C}', '\n'.join(SHELL_C)))

new_lines = lines[:558] + HEAD.split('\n') + lines[927:]
out = '\n'.join(new_lines)

open(PATH + '.bak_mapstage', 'w', encoding='utf-8', newline='').write(data)
open(PATH, 'w', encoding='utf-8', newline='').write(out)

print('MapUI.lua：%d 行 -> %d 行，字节 %d -> %d' % (len(lines), len(new_lines), len(data), len(out)))
print('CRLF =', out.count('\r\n'), ' 裸 LF =', out.count('\n') - out.count('\r\n'))
for probe in ('local function BuildPins(frame)',
              'local function BuildListRows(frame)',
              'local function BuildBlocks(frame)',
              'local function BuildSideRows(frame)',
              'local function BuildFinal(frame)',
              'M.EnsurePins = BuildPins',
              'DG.PushStep(BuildFinal)',
              '        frame.poolsBuilt = true'):
    print('  %-40s x%d' % (probe, out.count(probe)))

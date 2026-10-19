# -*- coding: utf-8 -*-
"""一次性字节补丁：HUD 固定路线也按「目标等级」显示（2026-10-11 用户）。

用户原话：「hud 固定路线显示也需要 根据我设置等级 显示」

根因：`routeFor` 的固定分支直接 `return "fixed", lv.steps`（全量 1–300）；
而专业页 `RowsLeveling` 走的是 `ClipFixedSteps(lv.steps, PD.LvTarget())`
（跨目标的段：止点裁到目标、制作数量按 (目标−起)/(止−起) 比例折算 ceil）。
⇒ 专业页设了目标 200，HUD 却一路显示到 300，段标分母 / 购物清单 / 完成判定全对不上。
自动路线不受影响（`opts.target` 已在 RA 内部 clamp）。

三处编辑：
  1. 新增 `clipFixedSteps`（口径与专业页 ClipFixedSteps 逐字一致）。
  2. `routeFor` 固定分支改走裁剪 + `routeTarget(slug)`。
  3. 新增 `PF.RefreshRoute`：目标等级改了立刻按新目标重推指针并重画
     （`PF.Sync` 内已有「设置变更 ⇒ 同步到专业页」的反向联动，这里做正向）。

用法：python _temp/patch_hud_targetclip.py [--dry]
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'Core', 'ProfFollow.lua')

EDIT1_OLD = '''-- 返回 mode("auto"/"fixed") + 段落表；自动不可用时回落固定路线
local function routeFor(slug, skill)
'''

EDIT1_NEW = '''-- 固定路线按「目标等级」裁剪（2026-10-11 用户：HUD 固定路线也要按我设的等级显示）。
--   口径与专业页 ClipFixedSteps 逐字一致：跨目标的段把止点裁到目标，
--   制作数量按 (目标−起)/(止−起) 比例折算并 ceil（最少 1）。target 为 nil / >=300 时原样返回。
--   ★ 自动路线不受影响：它的 opts.target 已在 Core/ProfRouteAuto.lua 内部 clamp。
local function clipFixedSteps(steps, target)
    if not target or target >= 300 then return steps end
    local out = {}
    for _, st in ipairs(steps or {}) do
        local a, b = st[1], st[2]
        if a > target then break end
        local nb, nq = math.min(b, target), st[4] or 0
        local isClip = b > target
        if isClip then
            nq = math.max(1, math.ceil(nq * (target - a) / (b - a) - 1e-9))
        end
        out[#out + 1] = { a, nb, st[3], nq, _clip = isClip or nil }
    end
    return out
end

-- 返回 mode("auto"/"fixed") + 段落表；自动不可用时回落固定路线
local function routeFor(slug, skill)
'''

EDIT2_OLD = '''    local lv = LV[slug]
    return "fixed", (lv and lv.steps) or nil
end
'''

EDIT2_NEW = '''    local lv = LV[slug]
    -- ★ 固定路线必须按「目标等级」裁剪后再交给 HUD（2026-10-11 用户）。
    --   原先直接返回 lv.steps（全量 1–300）⇒ 专业页设了目标、HUD 却一路画到 300，
    --   段标分母 / 购物清单 / 完成判定全和专业页对不上。
    return "fixed", clipFixedSteps(lv and lv.steps or nil, routeTarget(slug))
end
'''

EDIT3_OLD = '''    local d = derivedStep(s.slug, s.skill or 0)
    if d and d > (s.step or 1) then s.step = d end
end

function PF.Toggle(slug)
'''

EDIT3_NEW = '''    local d = derivedStep(s.slug, s.skill or 0)
    if d and d > (s.step or 1) then s.step = d end
end

-- 目标等级变了 ⇒ 固定路线的段落表随之变短/变长，HUD 需要立刻按新目标重推指针并重画。
--   PF.Sync 里已有「设置变更 ⇒ 同步到专业页」的反向联动，这里补正向（专业页改完
--   只会 pcall(PD.Render) 重画专业页，HUD 的 rkey 不会自动刷新）。
function PF.RefreshRoute(slug)
    local s = st()
    if not (s and s.slug) then return end
    if slug and slug ~= s.slug then return end
    PF.Sync()
    if PF.f and PF.f:IsShown() then pcall(PF.Paint) end
end

function PF.Toggle(slug)
'''

DRY = '--dry' in sys.argv
b = io.open(SRC, 'rb').read()
assert b.count(b'\r') == 0, '源文件不是纯 LF，先查（本项目禁 CRLF）'
txt = b.decode('utf-8')

edits = [('新增 clipFixedSteps 裁剪器', EDIT1_OLD, EDIT1_NEW),
         ('routeFor 固定分支按目标裁剪', EDIT2_OLD, EDIT2_NEW),
         ('新增 PF.RefreshRoute（等级改了立刻重推）', EDIT3_OLD, EDIT3_NEW)]
for name, old, new in edits:
    cnt = txt.count(old)
    assert cnt == 1, '锚点命中 %d 次（要求 1）：%s' % (cnt, name)
    txt = txt.replace(old, new, 1)
    print('[OK] %s' % name)

if DRY:
    print('（--dry：未写盘）')
    sys.exit(0)

io.open(SRC, 'wb').write(txt.encode('utf-8'))
b2 = io.open(SRC, 'rb').read()
assert b2.count(b'\r') == 0, '写回后出现 CR'
print('写入 %s：%d → %d 字节' % (SRC, len(b), len(b2)))

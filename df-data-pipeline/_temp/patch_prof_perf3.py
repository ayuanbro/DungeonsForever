# -*- coding: utf-8 -*-
"""补丁 3：配方页渲染的通用开销（2026-10-09 第二轮，承接 patch_prof_perf2）。

patch_prof_perf2 之后单帧 Render 28.5ms → 9.0ms，但两个通用热点还在：
  · PD.TextW 被一帧调 3000 次，而它是**逐字符 UTF-8 解码 + 查表**的纯 Lua 循环。
    配方页要量的大量文本高度重复（同一种皮出现在几百条配方里；「3×」这种数量串
    更是满天飞）⇒ 记忆化命中率极高，只影响耗时、不影响任何取值。
  · PD.RequestRows 对每行的产物 + 每种材料各调一次 DG.RequestItem + DG.ItemName，
    511 条配方实测 1349 次；同一材料跨配方重复 ⇒ 按 id 去重后大幅下降
    （DG.RequestItem 本来就靠 DG.__asked 幂等；PD.notReady 只被 SweepNames 用来
    「有没有任一未到货」判断，去重不改变语义）。

用法：
    python _temp/patch_prof_perf3.py --check
    python _temp/patch_prof_perf3.py
"""
import os
import sys

TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      os.pardir, 'Core', 'ProfessionUI.lua')

# ── 1. PD.TextW 记忆化 ────────────────────────────────────────────────
E1_OLD = '''PD.TextW = function(text, fs) return ns.hui.TextW(text, fs) end
'''
E1_NEW = '''-- ★ 量宽记忆化（2026-10-09 第二轮：点开配方页那一瞬间的卡顿）：
--   ns.hui.TextW 是**逐字符 UTF-8 解码 + 查表**的纯 Lua 循环，而配方页一帧要量
--   三千来次 —— 同一页里要量的文本高度重复（同一种皮出现在几百条配方里、「3×」
--   这种数量串满天飞）⇒ 按 (字号, 文本) 记忆化，命中率极高。
--   只影响耗时、不影响任何取值（TextW 对 (text, fs) 是纯函数）。
--   条数封顶，超了整表清空 —— 配方页的文本集合天然收敛，不会无限涨。
local _twMemo, _twN = {}, 0
PD.TextW = function(text, fs)
    if type(text) ~= "string" or fs == nil then return ns.hui.TextW(text, fs) end
    local m = _twMemo[fs]
    if not m then m = {}; _twMemo[fs] = m end
    local w = m[text]
    if w ~= nil then return w end
    w = ns.hui.TextW(text, fs)
    if _twN >= 8192 then
        _twMemo, _twN = {}, 0
        m = {}
        _twMemo[fs] = m
    end
    m[text] = w
    _twN = _twN + 1
    return w
end
'''

# ── 2. PD.RequestRows 按 id 去重 ──────────────────────────────────────
E2_OLD = '''function PD.RequestRows(rows)
    if not DG.RequestItem then return end
    local wait = {}
    local function want(id)
        if not id then return end
        DG.RequestItem(id)
        if not select(2, DG.ItemName(id)) then wait[#wait + 1] = id end
    end
'''
E2_NEW = '''function PD.RequestRows(rows)
    if not DG.RequestItem then return end
    local wait = {}
    -- ★ 按 id 去重（2026-10-09 第二轮）：一页几百条配方，同一种材料跨配方反复出现
    --   （实测 511 条 => 1349 次请求，去重后只剩唯一 id）。DG.RequestItem 本来就
    --   靠 DG.__asked 幂等，wait 只被 SweepNames 用来判「有没有任一未到货」⇒
    --   去重不改变语义，纯省掉重复的函数调用。
    local seen = {}
    local function want(id)
        if not id or seen[id] then return end
        seen[id] = true
        DG.RequestItem(id)
        if not select(2, DG.ItemName(id)) then wait[#wait + 1] = id end
    end
'''

EDITS = [
    ('1 PD.TextW 记忆化', E1_OLD, E1_NEW),
    ('2 PD.RequestRows 去重', E2_OLD, E2_NEW),
]


def heal(text, raw):
    if b'\r\n' in raw and raw.count(b'\n') == raw.count(b'\r\n'):
        return text.replace('\r\n', '\n').replace('\n', '\r\n')
    return text.replace('\r\n', '\n')


def main():
    check = '--check' in sys.argv
    raw = open(TARGET, 'rb').read()
    src = raw.decode('utf-8')
    print('目标 %s：%d 字节，CRLF=%d / 裸 LF=%d'
          % (os.path.basename(TARGET), len(raw), raw.count(b'\r\n'),
             raw.count(b'\n') - raw.count(b'\r\n')))
    bad = 0
    out = src
    for name, old, new in EDITS:
        o, n = heal(old, raw), heal(new, raw)
        c_old, c_new = out.count(o), out.count(n)
        if c_new == 1 and c_old == 0:
            print('  [SKIP] %-28s 已应用' % name)
            continue
        if c_old != 1:
            print('  [BAD ] %-28s 锚点 %d 次' % (name, c_old))
            bad += 1
            continue
        if c_new >= 1:
            print('  [BAD ] %-28s 替换串已存在 %d 次' % (name, c_new))
            bad += 1
            continue
        out = out.replace(o, n)
        print('  [OK  ] %-28s 锚点 1 次' % name)
    if bad:
        print('✗ %d 处有问题，未写盘' % bad)
        return 2
    if check:
        print('✓ 预检通过（--check，未写盘）')
        return 0
    if out == src:
        print('✓ 无需改动')
        return 0
    open(TARGET, 'wb').write(out.encode('utf-8'))
    back = open(TARGET, 'rb').read()
    print('✓ 已写盘：%d → %d 字节，CRLF=%d / 裸 LF=%d'
          % (len(raw), len(back), back.count(b'\r\n'),
             back.count(b'\n') - back.count(b'\r\n')))
    return 0


if __name__ == '__main__':
    sys.exit(main())

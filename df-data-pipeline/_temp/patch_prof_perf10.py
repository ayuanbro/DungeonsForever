# -*- coding: utf-8 -*-
"""第六刀（产品）：把实机 77.6ms 里两笔「引擎调用」砍掉。

实机 /dfprofperf（12:48，制皮·recipe = 77.6ms）：
    细分：扫描 11.8 · 建spec 4.5 · 列宽材料 17.9（其中 材料串 17.2）
    取名 2228 次 / 取名(引擎) 1586 次
⇒ 两笔可砍的：

① **材料图标查询没记忆化**。PD.MatCol 每行每个材料都走
   PD.MatIconTex → DG.ItemIcon → DG.ItemInfo(id)（= GetItemInfo，零缓存引擎调用）。
   一页 300 行 × 平均 3 材料 ≈ 900 次 ⇒ 与物品名同源、同一个 id 不可能变。
   修法：加 PD.ItemIcon 记忆化（与 PD.ItemName 共用同一次清空时机）。

② **PD.ScanRecipe 给全量 511 行量宽，而列表只画 300 行**。
   maxW 只用来定**名称列宽度**，300 行之后的行根本进不了列表 ⇒ 那 211 行的
   量宽（211 次 ItemName + 422 次 TextW）是纯白做。计数 n 仍保持精确（抬头要用）。

口径不变：①只改「从哪拿图标」，②只改「给谁量宽」；两处都不动任何取值。
CRLF 自愈 + --check 预检 + 幂等哨兵。
"""

import io
import os
import sys

PROD = 'Core/ProfessionUI.lua'
SENTINEL = 'function PD.ItemIcon(id)'

# ── 1 记忆表：加图标表，与物品名一起清 ──────────────────────────────
E1_OLD = (
    'local _nmMemo, _nmN = {}, 0\r\n'
    'function PD.ResetItemNameMemo()\r\n'
    '    _nmMemo, _nmN = {}, 0\r\n'
    'end\r\n'
)
E1_NEW = (
    'local _nmMemo, _nmN = {}, 0\r\n'
    'local _icMemo, _icN = {}, 0\r\n'
    'function PD.ResetItemNameMemo()\r\n'
    '    _nmMemo, _nmN = {}, 0\r\n'
    '    _icMemo, _icN = {}, 0\r\n'
    'end\r\n'
)

# ── 2 新增 PD.ItemIcon（物品名之后、PD.Wrap 之前）────────────────────
E2_OLD = (
    '    _nmMemo[id] = { nm, got }\r\n'
    '    _nmN = _nmN + 1\r\n'
    '    return nm, got\r\n'
    'end\r\n'
    '\r\n'
    'PD.Wrap = function(text, fs, width)\r\n'
)
E2_NEW = (
    '    _nmMemo[id] = { nm, got }\r\n'
    '    _nmN = _nmN + 1\r\n'
    '    return nm, got\r\n'
    'end\r\n'
    '\r\n'
    '-- ★★ 材料图标记忆化（2026-10-09 第六轮；实机 /dfprofperf：列宽材料 17.9ms、\r\n'
    '--   取名(引擎) 1586 次）。PD.MatCol 每行每个材料都算一次图标串，而\r\n'
    '--   PD.MatIconTex → DG.ItemIcon → DG.ItemInfo(id)（= GetItemInfo）是**零缓存**的\r\n'
    '--   引擎调用 —— 一页 300 行 × 平均 3 材料 ≈ 900 次，与物品名**同源**。\r\n'
    '--   同一个 id 在一次渲染里图标不可能变 ⇒ 与 PD.ItemName 共用同一次清空时机\r\n'
    '--   （PD.ResetItemNameMemo 两表一起清），到货重扫自然拿到新图标。\r\n'
    'function PD.ItemIcon(id)\r\n'
    '    if id == nil then return FALLBACK_ICON end\r\n'
    '    local c = _icMemo[id]\r\n'
    '    if c ~= nil then return c end\r\n'
    '    local tex = DG.ItemIcon(id)\r\n'
    '    if _icN >= 8192 then _icMemo, _icN = {}, 0 end\r\n'
    '    _icMemo[id] = tex\r\n'
    '    _icN = _icN + 1\r\n'
    '    return tex\r\n'
    'end\r\n'
    '\r\n'
    'PD.Wrap = function(text, fs, width)\r\n'
)

# ── 3 MatIconTex 改走记忆化 ──────────────────────────────────────────
E3_OLD = (
    'function PD.MatIconTex(id, px)\r\n'
    '    px = px or 14\r\n'
    '    local ic = DG.ItemIcon(id)\r\n'
)
E3_NEW = (
    'function PD.MatIconTex(id, px)\r\n'
    '    px = px or 14\r\n'
    '    local ic = PD.ItemIcon(id)   -- ★ 记忆化：同一材料在一页里被算几十次\r\n'
)

# ── 4 ScanRecipe 只给画得出来的行量宽 ────────────────────────────────
E4_OLD = (
    '            if PD.RawHit(r, q) then\r\n'
    '                n = n + 1\r\n'
    '                -- 与 PD.FitRecipeCols 的自扫逐字同口径：名称可为空（名字还没到货）\r\n'
    '                -- 时也照样把「新角标 + 副行」计入最宽值。\r\n'
    '                local nm = PD.ItemName(r[2])\r\n'
    '                local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0\r\n'
    '                if r[11] then w = w + PD.RECIPE_BADGE_W end\r\n'
    '                local sw = PD.TextW(tostring(r[5] or ""), 11)\r\n'
    '                if sw > w then w = sw end\r\n'
    '                if w > maxW then maxW = w end\r\n'
    '            end\r\n'
)
E4_NEW = (
    '            if PD.RawHit(r, q) then\r\n'
    '                n = n + 1\r\n'
    '                -- ★★ 2026-10-09 第六轮：**只给画得出来的行量宽**。\r\n'
    '                --   列宽（maxW → PD.RECIPE_NAME_W）只要放得下**真正画出来的**那些\r\n'
    '                --   行就够了；第 301 条往后根本不进列表 ⇒ 给它们量宽是纯白做\r\n'
    '                --   （实测每次点开白量 211 次 ItemName + 422 次 TextW）。\r\n'
    '                --   计数 n 仍然**精确**（抬头要显示真实总数）。\r\n'
    '                if n <= PD.ROW_CAP then\r\n'
    '                    -- 与 PD.FitRecipeCols 的自扫逐字同口径：名称可为空（名字还没到货）\r\n'
    '                    -- 时也照样把「新角标 + 副行」计入最宽值。\r\n'
    '                    local nm = PD.ItemName(r[2])\r\n'
    '                    local w = (nm and nm ~= "" and PD.TextW(nm, 13)) or 0\r\n'
    '                    if r[11] then w = w + PD.RECIPE_BADGE_W end\r\n'
    '                    local sw = PD.TextW(tostring(r[5] or ""), 11)\r\n'
    '                    if sw > w then w = sw end\r\n'
    '                    if w > maxW then maxW = w end\r\n'
    '                end\r\n'
    '            end\r\n'
)

EDITS = [
    ('1 记忆表加图标表', E1_OLD, E1_NEW),
    ('2 新增 PD.ItemIcon', E2_OLD, E2_NEW),
    ('3 MatIconTex 走记忆化', E3_OLD, E3_NEW),
    ('4 ScanRecipe 只量可见行', E4_OLD, E4_NEW),
]


def heal(s, raw):
    """把裸 \\n 补成文件自身的行尾（CRLF 探针自愈）。"""
    nl = '\r\n' if b'\r\n' in raw else '\n'
    if nl == '\n':
        return s
    return s.replace('\r\n', '\n').replace('\n', nl)


def main():
    check = '--check' in sys.argv
    raw = open(PROD, 'rb').read()
    src = raw.decode('utf-8')
    bad, out = 0, src
    for name, old, new in EDITS:
        o, n = heal(old, raw), heal(new, raw)
        c_o, c_n = out.count(o), out.count(n)
        if c_n == 1 and c_o == 0:
            print('  [SKIP] %-26s 已应用' % name)
            continue
        if c_o != 1:
            print('  [BAD ] %-26s 锚点 %d 次' % (name, c_o))
            bad += 1
            continue
        if c_n >= 1:
            print('  [BAD ] %-26s 替换串已存在 %d 次' % (name, c_n))
            bad += 1
            continue
        out = out.replace(o, n, 1)
        print('  [OK  ] %-26s 锚点 1 次' % name)
    if bad:
        print('  ✗ %d 处未通过，未落盘' % bad)
        return 1
    if check:
        print('  [OK  ] 预检通过（未落盘）')
        return 0
    if out != src:
        with open(PROD, 'wb') as f:
            f.write(out.encode('utf-8'))
        print('  [OK  ] 已写入 %s' % PROD)
    return 0


if __name__ == '__main__':
    sys.exit(main())

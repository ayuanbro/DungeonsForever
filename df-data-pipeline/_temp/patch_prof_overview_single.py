# -*- coding: utf-8 -*-
# 总览页：删简介段 / 删开发备注段 / 改单列 / BODY_TOP 间距 10→8；同步 harness 断言。
import re

def load(p):
    d = open(p, "rb").read().decode("utf-8")
    return d

def save(p, d):
    open(p, "wb").write(d.encode("utf-8"))

P = r"D:\workspace\DungeonsForever\Core\ProfessionUI.lua"
d = load(P)
crlf = d.count("\r\n")
assert d.count("\n") - crlf == 0, "ProfessionUI: bare LF"

def rep1(old, new):
    global d
    assert d.count(old) == 1, "anchor not unique: " + old[:60]
    d = d.replace(old, new)

# 1) 大卡内容与胶囊轨道底边间距 10 → 8（用户定案：卡↔上方轨道 = 8）
rep1("PD.BODY_TOP = PD.SUB_Y + PD.SUB_H + 10",
     "PD.BODY_TOP = PD.SUB_Y + PD.SUB_H + 8")

# 2) OV_SPLIT 退役（总览改单列，常量再无使用点）
rep1("PD.OV_SPLIT = 0.62\r\n", "")

# 3) 删简介段（PushHead 简介 → 段尾 OV_GUT 空档行，含 lede/认证/称号）
i0 = d.index('    PushHead(rows, L["简介"], 1)\r\n')
i1 = d.index('    PushGap(rows, PD.OV_GUT, 1)\r\n', i0) + len('    PushGap(rows, PD.OV_GUT, 1)\r\n')
blk = d[i0:i1]
for key in ("lede", "p.cert", "p.title"):
    assert key in blk, key
d = d[:i0] + d[i1:]

# 4) 顶部双列空档 → 单列
rep1("    PushGap(rows, 6, 1)\r\n    PushGap(rows, 6, 2)\r\n",
     "    PushGap(rows, 6, 1)\r\n")

# 5) 数字速览 col 2 → 1
rep1('rows[#rows + 1] = {\r\n            kind = "row", h = PD.ROW_H1, col = 2,\r\n'
     '            nameColor = C_GREY, text = label, right = value,\r\n        }',
     'rows[#rows + 1] = {\r\n            kind = "row", h = PD.ROW_H1, col = 1,\r\n'
     '            nameColor = C_GREY, text = label, right = value,\r\n        }')
rep1('PushHead(rows, L["数字速览"], 2)', 'PushHead(rows, L["数字速览"], 1)')
rep1("PushGap(rows, PD.OV_GUT, 2)", "PushGap(rows, PD.OV_GUT, 1)")

# 6) 删开发备注段（PushHead → 暂无备注行）
i0 = d.index('    PushHead(rows, L["开发备注"], 2)\r\n')
mark = '    if not noted then PushText(rows, L["暂无备注"], 12, C_GREY, 2) end\r\n'
i1 = d.index(mark, i0) + len(mark)
blk = d[i0:i1]
for key in ("p.tips", "p.verify", "noted"):
    assert key in blk, key
d = d[:i0] + d[i1:]

# 7) Render：总览不再举手两栏（升级页购物清单子页的两栏不受影响）
rep1("        PD.lvSplit = (PD.cur ~= \"__index\")\r\n"
     "        PD.wantIndexGrid = (PD.cur == \"__index\")\r\n"
     "        PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.OV_SPLIT)\r\n"
     "        PD.splitRW = PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT - PD.splitLW\r\n",
     "        PD.lvSplit = false\r\n"
     "        PD.wantIndexGrid = (PD.cur == \"__index\")\r\n")

save(P, d)
crlf2 = d.count("\r\n")
assert d.count("\n") - crlf2 == 0
print("ProfessionUI ok: CRLF", crlf2, "bareLF", d.count("\n") - crlf2)

# ---------- harness ----------
H = r"D:\workspace\DungeonsForever\_temp\df_dungeon_check.py"
h = load(H)

def hrep(old, new):
    global h
    assert h.count(old) == 1, "harness anchor not unique: " + old[:60]
    h = h.replace(old, new)

# ⑨ 总览分栏断言 → 总览单列（OV_SPLIT 退役）
hrep("""    ck('★ 总览分栏 0.62 举手（splitLW 按 OV_GUT 沟距算、优先于 COL_LW；升级页不举手仍 0.80）',
       'PD.OV_SPLIT = 0.62' in profui
       and 'PD.splitLW = math.floor((PD.RIGHT_W - 2 * PD.LIST_PAD - PD.OV_GUT) * PD.OV_SPLIT)' in profui
       and 'PD.splitLW or PD.COL_LW' in profui)""",
"""    ck('★ 总览单列（2026-10-10 用户定：简介/开发备注删除后不再分栏，OV_SPLIT 退役）',
       'PD.OV_SPLIT' not in profui
       and '        PD.lvSplit = false\\r\\n' in profui
       and 'PushHead(rows, L["数字速览"], 1)' in profui)""")

# 卡片净距断言：`, 2)` 空档行已并入单列
hrep("       and 'PushGap(rows, PD.OV_GUT, 2)' in profui\n",
     "       and 'PushGap(rows, PD.OV_GUT, 2)' not in profui\n")

# 四合一条：开发备注/简介退役改判缺席
hrep("       and 'PushHead(rows, L[\"传承\"], 1)' in profui\n"
     "       and 'PushHead(rows, L[\"开发备注\"], 2)' in profui)",
     "       and 'PushHead(rows, L[\"传承\"], 1)' in profui\n"
     "       and 'PushHead(rows, L[\"开发备注\"]' not in profui\n"
     "       and 'PushHead(rows, L[\"简介\"]' not in profui)")

save(H, h)
print("harness ok")

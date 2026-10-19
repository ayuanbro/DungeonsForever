# -*- coding: utf-8 -*-
"""fix13: 阵营按钮统一到页签行右端 + 阵营色文字 + 声望页接入。
目标状态（三页一致）：
  facBtn1/2 锚 PV.page TOPRIGHT（TAB_Y 行），文字 部落=红 / 联盟=蓝；
  军衔 rankBadge 改锚卡片；RenderRep 显示按钮（数据本就按 PV.faction 分）。
在开发仓 D:\\workspace\\DungeonsForever 上操作。"""
import io, json, re, os, shutil, subprocess

TARGET = r"D:\workspace\DungeonsForever\Core\PvPUI.lua"
REPORT = r"D:\workspace\DungeonsForever\_temp\pvp_fix13_report.json"
BAK = r"D:\workspace\DungeonsForever\_temp\_bak_PvPUI_fix13.lua"
BAK2 = r"C:\Users\Administrator\.workbuddy\df_backups\_bak_PvPUI_fix13.lua"

ALLY = 'bt:GetFontString():SetTextColor(0.40, 0.62, 1.00, 1)'
HORDE = 'bt:GetFontString():SetTextColor(1.00, 0.36, 0.26, 1)'
POS1 = 'PV.facBtn1:SetPoint("TOPRIGHT", PV.page, "TOPRIGHT", -(PV.X + 2), -PV.TAB_Y)'
POS2 = 'PV.facBtn2:SetPoint("TOPRIGHT", PV.facBtn1, "TOPLEFT", -4, 0)'
SHOW = 'PV.facBtn1:Show()\n    PV.facBtn2:Show()'
OUTLINE = ('SetOutline(PV.facBtn1, PV.faction == "A", 1, 0.82, 0)\n'
           '    SetOutline(PV.facBtn2, PV.faction == "H", 1, 0.82, 0)')

steps = []
def step(name, ok, detail=""):
    steps.append({"name": name, "ok": bool(ok), "detail": str(detail)[:300]})

s = io.open(TARGET, encoding="utf-8").read()

# ---- T1 创建块：阵营色文字（收敛） ----
c_anchor = 'bt.__huiKeepTextColor = true\n        bt.__fac = (i == 1) and "A" or "H"'
if ALLY in s and HORDE in s:
    step("fac_color_already", True)
else:
    step("c_anchor", s.count(c_anchor) == 1, "n=%d" % s.count(c_anchor))
    s = s.replace(c_anchor,
        'bt.__huiKeepTextColor = true\n'
        '        ' + ALLY + '\n'
        '        ' + HORDE + '\n'
        '        bt.__fac = (i == 1) and "A" or "H"', 1)
    step("fac_color_added", ALLY in s and HORDE in s)

# ---- T2 RenderRanks：按钮改锚 page ----
if POS1 in s and s.count(POS1) == 3:
    step("pos_already", True, "count=%d" % s.count(POS1))
else:
    old_rank1 = 'PV.facBtn1:SetPoint("TOPRIGHT", PV.rankCard, "TOPRIGHT", -8, -2)'
    step("rank_anchor_old", s.count(old_rank1) == 1, "n=%d" % s.count(old_rank1))
    s = s.replace(old_rank1, POS1, 1)
    step("rank_pos", s.count(POS1) >= 1)

# ---- T3 rankBadge 改锚卡片 ----
old_badge = 'PV.rankBadge:SetPoint("TOPRIGHT", PV.facBtn2, "TOPLEFT", -6, -2)'
new_badge = 'PV.rankBadge:SetPoint("TOPRIGHT", PV.rankCard, "TOPRIGHT", -12, -4)'
if new_badge in s:
    step("badge_already", True)
else:
    step("badge_old", s.count(old_badge) == 1, "n=%d" % s.count(old_badge))
    s = s.replace(old_badge, new_badge, 1)
    step("badge_moved", new_badge in s)

# ---- T4 RenderSets：两处 TOPLEFT child 锚 → page 锚 ----
old_sets = ('PV.facBtn2:ClearAllPoints()\n'
            '    PV.facBtn2:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.W - 76 - PV.TAB_STEP, -(y + 1))\n'
            '    PV.facBtn2:Show()\n'
            '    PV.facBtn1:ClearAllPoints()\n'
            '    PV.facBtn1:SetPoint("TOPLEFT", PV.child, "TOPLEFT", PV.W - 76, -(y + 1))\n'
            '    PV.facBtn1:Show()')
new_sets = ('PV.facBtn2:ClearAllPoints()\n'
            '    ' + POS2 + '\n'
            '    PV.facBtn2:Show()\n'
            '    PV.facBtn1:ClearAllPoints()\n'
            '    ' + POS1 + '\n'
            '    PV.facBtn1:Show()')
if new_sets in s:
    step("sets_already", True)
else:
    step("sets_old", s.count(old_sets) == 1, "n=%d" % s.count(old_sets))
    s = s.replace(old_sets, new_sets, 1)
    step("sets_moved", new_sets in s)

# ---- T5 RenderRep：插入按钮块 ----
rep_anchor = 'function PV.RenderRep()\n    local y = 0'
rep_block = ('function PV.RenderRep()\n'
             '    local y = 0\n'
             '    -- ★ 声望页阵营切换（数据本就按 PV.faction 分，点击 OnClick 走 PV.Render 全量重渲）\n'
             '    PV.facBtn1:ClearAllPoints()\n'
             '    ' + POS1 + '\n'
             '    PV.facBtn2:ClearAllPoints()\n'
             '    ' + POS2 + '\n'
             '    ' + SHOW + '\n'
             '    ' + OUTLINE)
if '-- ★ 声望页阵营切换' in s:
    step("rep_already", True)
else:
    step("rep_anchor", s.count(rep_anchor) == 1, "n=%d" % s.count(rep_anchor))
    s = s.replace(rep_anchor, rep_block, 1)
    step("rep_added", '-- ★ 声望页阵营切换' in s)

# ---- 后断言 ----
step("post_pos_count", s.count(POS1) == 3, "count=%d" % s.count(POS1))
step("post_pos2_count", s.count(POS2) == 3, "count=%d" % s.count(POS2))
step("post_no_rankcard_anchor", 'facBtn1:SetPoint("TOPRIGHT", PV.rankCard' not in s)
step("post_no_sets_child_anchor", 'facBtn1:SetPoint("TOPLEFT", PV.child' not in s
      and 'facBtn2:SetPoint("TOPLEFT", PV.child' not in s)
step("post_colors", ALLY in s and HORDE in s)

if not all(st["ok"] for st in steps):
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    io.open(REPORT, "w", encoding="utf-8").write(json.dumps(
        {"aborted": "assert failed", "steps": steps}, ensure_ascii=False, indent=1))
    print("FIX13 ABORT", json.dumps({"failed": [st["name"] for st in steps if not st["ok"]]}))
    raise SystemExit(1)

shutil.copy2(TARGET, BAK)
try:
    shutil.copy2(TARGET, BAK2)
except Exception:
    pass
io.open(TARGET, "w", encoding="utf-8", newline="").write(s)
s2 = io.open(TARGET, encoding="utf-8").read()
step("reread", s2.count(POS1) == 3 and ALLY in s2 and '-- ★ 声望页阵营切换' in s2)

LC = r"D:/workspace/tool/luacheck.exe"
try:
    p = subprocess.run([LC, TARGET, "--no-max-string-line-length"], capture_output=True, text=True, timeout=120)
    lc = {"code": p.returncode, "out": (p.stdout or "") + (p.stderr or "")}
except Exception as e:
    lc = {"code": None, "out": repr(e)}
step("luacheck_0err", ("0 errors" in lc["out"]) or (lc["code"] == 0), lc["out"][-200:])

os.makedirs(os.path.dirname(REPORT), exist_ok=True)
io.open(REPORT, "w", encoding="utf-8").write(json.dumps(
    {"aborted": None, "steps": steps, "luacheck": lc}, ensure_ascii=False, indent=1))
print("FIX13 OK" if all(st["ok"] for st in steps) else "FIX13 FAIL",
      json.dumps({"failed": [st["name"] for st in steps if not st["ok"]]}))

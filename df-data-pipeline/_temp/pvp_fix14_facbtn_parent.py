# -*- coding: utf-8 -*-
"""fix14: 阵营按钮不可见修复——父级 child(滚动层) 改 page(页签层)。
锚在 page TAB_Y 行的控件，父级必须同为 page，否则被 ScrollFrame 裁剪。
顺带全量核验军衔页 12 项目标状态。"""
import io, json, re, os, shutil, subprocess

TARGET = r"D:\workspace\DungeonsForever\Core\PvPUI.lua"
CLIENT = r"D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever\Core\PvPUI.lua"
REPORT = r"D:\workspace\DungeonsForever\_temp\pvp_fix14_report.json"
BAK2 = r"C:\Users\Administrator\.workbuddy\df_backups\_bak_PvPUI_fix14.lua"

steps = []
def step(name, ok, detail=""):
    steps.append({"name": name, "ok": bool(ok), "detail": str(detail)[:300]})

s = io.open(TARGET, encoding="utf-8").read()

old_create = 'local bt = NewButton(child, i == 1 and L["联盟"] or L["部落"], PV.TAB_W, PV.TAB_H, 14)'
new_create = 'local bt = NewButton(page, i == 1 and L["联盟"] or L["部落"], PV.TAB_W, PV.TAB_H, 14)'
if new_create in s:
    step("parent_already", True)
else:
    step("create_anchor", s.count(old_create) == 1, "n=%d" % s.count(old_create))
    s = s.replace(old_create, new_create, 1)
    step("parent_moved", new_create in s)

# 后断言：按钮锚 page 且父级 page
step("post_pos", s.count('PV.facBtn1:SetPoint("TOPRIGHT", PV.page') == 3)
step("post_parent", new_create in s)

if not all(st["ok"] for st in steps):
    io.open(REPORT, "w", encoding="utf-8").write(json.dumps({"aborted": "assert failed", "steps": steps}, ensure_ascii=False, indent=1))
    print("FIX14 ABORT", json.dumps({"failed": [st["name"] for st in steps if not st["ok"]]}))
    raise SystemExit(1)

shutil.copy2(TARGET, BAK2)
io.open(TARGET, "w", encoding="utf-8", newline="").write(s)
s2 = io.open(TARGET, encoding="utf-8").read()
step("reread", new_create in s2)

# 全量状态核验（防并行回退的附带损伤）
checks = {
    "carry_rankUI": 'PV.rankUI = CreateFrame("Frame", nil, PV.rankCard)' in s2,
    "carry_capUI": 'PV.capUI = CreateFrame("Frame", nil, PV.capCard)' in s2,
    "zebra": s2.count('SetColorTexture(1, 1, 1, 0.06)') >= 2,
    "capcard_428": 'PV.capCard = NewRoundCard(PV.W - 508, 536)' in s2,
    "chip_row_parent": 'chip:SetParent(row)' in s2,
    "chip_id_fix": 'chip.__id = all[k]' in s2,
    "request_item": 'Host.DG.RequestItem(all[k])' in s2,
    "badslash": len(re.findall(r'(?<!\\)\\PvPRank', s2)) == 0,
    "facbtn_clear_sets": 'PV.facBtn1:ClearAllPoints()' in s2,
    "fonts14_rankrows": re.search(r'r\.pts = MakeFS\(r, 14,', s2) is not None,
    "scroll_inset": 'scroll:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -4, PV.X)' in s2,
}
for k, v in checks.items():
    step("state_" + k, v)

LC = r"D:/workspace/tool/luacheck.exe"
try:
    p = subprocess.run([LC, TARGET, "--no-max-string-line-length"], capture_output=True, text=True, timeout=120)
    lc = {"code": p.returncode, "out": (p.stdout or "") + (p.stderr or "")}
except Exception as e:
    lc = {"code": None, "out": repr(e)}
step("luacheck_0err", ("0 errors" in lc["out"]) or (lc["code"] == 0), lc["out"][-200:])

io.open(REPORT, "w", encoding="utf-8").write(json.dumps(
    {"aborted": None, "steps": steps, "luacheck": lc}, ensure_ascii=False, indent=1))
print("FIX14 OK" if all(st["ok"] for st in steps) else "FIX14 FAIL",
      json.dumps({"failed": [st["name"] for st in steps if not st["ok"]]}))

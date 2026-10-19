# -*- coding: utf-8 -*-
"""fix15: 阵营按钮文字色被 Hui SetEnabled 钩子刷白——启用分支补 __huiKeepTextColor 判断。
OnLeave(1795) 已尊重标记，SetEnabled(1807) 漏了 => 阵营色被冲回白色。"""
import io, json, shutil, subprocess

TARGET = r"D:\workspace\DungeonsForever\Core\Hui.lua"
REPORT = r"D:\workspace\DungeonsForever\_temp\pvp_fix15_report.json"
BAK2 = r"C:\Users\Administrator\.workbuddy\df_backups\_bak_Hui_fix15.lua"

OLD = '''        hooksecurefunc(bt, "SetEnabled", function(_, enabled)
            ApplyBody(enabled and 0.5 or 0.25)
            if fs then
                if enabled then
                    fs:SetTextColor(1, 1, 1)
                else
                    fs:SetTextColor(0.5, 0.5, 0.5)
                end
            end
        end)'''
NEW = '''        hooksecurefunc(bt, "SetEnabled", function(_, enabled)
            ApplyBody(enabled and 0.5 or 0.25)
            if fs then
                if enabled then
                    -- ★ __huiKeepTextColor：按钮自带文字色（阵营色等）不被启用钩子刷白
                    if not bt.__huiKeepTextColor then fs:SetTextColor(1, 1, 1) end
                else
                    fs:SetTextColor(0.5, 0.5, 0.5)
                end
            end
        end)'''

steps = []
def step(name, ok, detail=""):
    steps.append({"name": name, "ok": bool(ok), "detail": str(detail)[:300]})

s = io.open(TARGET, encoding="utf-8").read()
if NEW in s:
    step("already", True)
else:
    step("anchor_one", s.count(OLD) == 1, "n=%d" % s.count(OLD))
    if s.count(OLD) == 1:
        s = s.replace(OLD, NEW, 1)
        step("patched", NEW in s)

if not all(st["ok"] for st in steps):
    io.open(REPORT, "w", encoding="utf-8").write(json.dumps({"aborted": "assert failed", "steps": steps}, ensure_ascii=False, indent=1))
    print("FIX15 ABORT", json.dumps({"failed": [st["name"] for st in steps if not st["ok"]]}))
    raise SystemExit(1)

shutil.copy2(TARGET, BAK2)
io.open(TARGET, "w", encoding="utf-8", newline="").write(s)
s2 = io.open(TARGET, encoding="utf-8").read()
step("reread", NEW in s2)

LC = r"D:/workspace/tool/luacheck.exe"
try:
    p = subprocess.run([LC, TARGET, "--no-max-string-line-length"], capture_output=True, text=True, timeout=120)
    lc = {"code": p.returncode, "out": (p.stdout or "") + (p.stderr or "")}
except Exception as e:
    lc = {"code": None, "out": repr(e)}
step("luacheck_0err", ("0 errors" in lc["out"]) or (lc["code"] == 0), lc["out"][-200:])

io.open(REPORT, "w", encoding="utf-8").write(json.dumps({"aborted": None, "steps": steps, "luacheck": lc}, ensure_ascii=False, indent=1))
print("FIX15 OK" if all(st["ok"] for st in steps) else "FIX15 FAIL",
      json.dumps({"failed": [st["name"] for st in steps if not st["ok"]]}))

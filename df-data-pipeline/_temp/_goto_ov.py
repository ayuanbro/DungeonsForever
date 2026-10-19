import subprocess
import sys
import time

WX = r"D:\workspace\project-024-wuxian-workshop\.venv\Scripts\wuxian.exe"

HIT = """
local t = "%s"
local root = _G.DungeonsForever_MainFrame
local q = { root }
local i = 1
while i <= #q do
    local f = q[i]
    i = i + 1
    for _, c in ipairs({ f:GetChildren() }) do q[#q + 1] = c end
    for _, r in ipairs({ f:GetRegions() }) do
        local s = r.GetText and r:GetText()
        if s and s == t and type(f.Click) == "function" then
            f:Click()
            return "ok"
        end
    end
end
return "missing"
"""

CARD = """
local root = _G.DungeonsForever_MainFrame
local q = { root }
local i = 1
while i <= #q do
    local f = q[i]
    i = i + 1
    for _, c in ipairs({ f:GetChildren() }) do q[#q + 1] = c end
    for _, r in ipairs({ f:GetRegions() }) do
        local s = r.GetText and r:GetText()
        if s and s:find("怒焰") and type(f.Click) == "function" then
            f:Click()
            return "ok"
        end
    end
end
return "missing"
"""

SHOW = """
local root = _G.DungeonsForever_MainFrame
if not root:IsShown() then SlashCmdList["DUNGEONSFOREVER"]("fb") end
return tostring(root:IsShown())
"""


def run(code, timeout=25):
    p = subprocess.run([WX, "run", "--timeout", str(timeout), code],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or "").strip().splitlines()[-1:] or [""]


def main():
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
    subprocess.run([WX, "reload"], capture_output=True, text=True)
    time.sleep(9)
    print("show:", run(SHOW))
    time.sleep(delay)
    print("card:", run(CARD))
    time.sleep(delay)
    print("任务:", run(HIT % "任务"))
    time.sleep(delay)
    print("总览:", run(HIT % "总览"))
    time.sleep(delay)
    p = subprocess.run([WX, "snap", "--max-width", "0"], capture_output=True, text=True)
    print("snap:", (p.stdout or "").strip())


main()

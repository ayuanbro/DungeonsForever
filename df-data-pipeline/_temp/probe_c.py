import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
lua = ("/run local D=DungeonsForeverDB local m=_G.DungeonsForever_MainFrame "
       "local ok,e=pcall(ns.Open) "
       "D.dfProbe2={ok=ok,err=(e and tostring(e)) or '',s=m:IsShown(),a=m:GetAlpha(),"
       "hold=D.dfPrimeHold}")
r = subprocess.run([py, "_temp/bg_chat.py", "--open", lua], env=env)
time.sleep(2)
r = subprocess.run([py, "_temp/bg_chat.py", "--open", "/reload"], env=env)
time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"dfProbe2"')
print(txt[i:i+260] if i >= 0 else "NO dfProbe2")

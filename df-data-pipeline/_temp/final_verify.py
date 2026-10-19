import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    r = subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    if r.returncode: sys.exit("chat fail: " + s)
    time.sleep(1)
chat("/run DungeonsForeverDB.dfPrimeHold=nil DungeonsForeverDB.dfProbe=nil DungeonsForeverDB.dfProbe2=nil DungeonsForeverDB.dfPrime=nil")
chat("/reload"); time.sleep(6)
chat("/run DungeonsForeverDB.dfAutoTest=true DungeonsForeverDB.dfAutoTestDelay=0.5")
chat("/reload"); time.sleep(24)
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"dfAutoTestResult"')
print(txt[i:i+900] if i >= 0 else "NO RESULT")
print("---flags---")
import re
for k in ("dfPrimeHold", "dfProbe", "dfAutoTest"):
    print(k, "present" if '"'+k+'"' in txt else "clean")

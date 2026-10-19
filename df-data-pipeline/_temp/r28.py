import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
chat("/run DungeonsForeverDB.dfWhite=nil DungeonsForeverDB.dfWhiteRes=nil DungeonsForeverDB.dfBlizRes=nil")
chat("/run DungeonsForeverDB.dfAutoTest=true DungeonsForeverDB.dfAutoTestDelay=0.5")
chat("/reload"); time.sleep(24)
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
k = txt.find('"segOpen"')
print("SEGOPEN:", txt[k:txt.find('}', k)] if k >= 0 else "")

import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
def run_case(delay, wait, tag):
    chat("/run DungeonsForeverDB.dfAutoTest=true DungeonsForeverDB.dfAutoTestDelay=" + str(delay))
    chat("/reload"); time.sleep(wait)
    chat("/reload"); time.sleep(8)
    sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
    txt = open(sv, encoding="utf-8", errors="replace").read()
    k = txt.find('"segOpen"')
    print(tag, txt[k:txt.find('}', k)] if k >= 0 else "NO SEG")
    i = txt.find('"diag"')
    print(tag, "DIAG:", txt[i:txt.find('"', i+8)+1] if i >= 0 else "")
run_case(0.5, 24, "IMMED")
run_case(8, 34, "DEL8")

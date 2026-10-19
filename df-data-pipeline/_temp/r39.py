import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
def run_case(extra, delay, wait, tag):
    chat("/run " + extra + " DungeonsForeverDB.dfAutoTest=true DungeonsForeverDB.dfAutoTestDelay=" + str(delay))
    chat("/reload"); time.sleep(wait)
    chat("/reload"); time.sleep(8)
    sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
    txt = open(sv, encoding="utf-8", errors="replace").read()
    k = txt.find('"segOpen"')
    print(tag, txt[k:txt.find('}', k)] if k >= 0 else "NO SEG")
run_case("DungeonsForeverDB.ui=DungeonsForeverDB.ui or {} DungeonsForeverDB.ui.reveal=false", 0.5, 24, "NOREVEAL")

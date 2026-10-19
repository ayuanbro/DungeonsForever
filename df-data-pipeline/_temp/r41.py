import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    r = subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env, capture_output=True, text=True)
    print(r.stdout.strip()[:100], r.stderr.strip()[:100])
    time.sleep(1)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
print("mtime before:", os.path.getmtime(sv))
chat("/run DungeonsForeverDB.dfProbeOK=1")
chat("/reload"); time.sleep(8)
print("mtime after:", os.path.getmtime(sv))
txt = open(sv, encoding="utf-8", errors="replace").read()
print("probeOK:", '"dfProbeOK" = 1' in txt or '"dfProbeOK"' in txt)
i = txt.find('"dfIdleRes"')
print("idleRes present:", i >= 0)

import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
r = subprocess.run([py, "_temp/bg_chat.py", "--open", "/reload"], env=env)
time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"dfProbe"')
print(txt[i:i+220] if i >= 0 else "NO dfProbe")

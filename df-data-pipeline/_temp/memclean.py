import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
keys = ["dfAutoTest","dfAutoTestResult","dfAutoTestDelay","dfMemProbe","dfPrebuild","dfNoPrebuild","dfm","dfmc","dfmc2","dfmg","dfmr","dfsb","frA","frB","frBG","frBR","frBP","frBE","frBC","frBF","frBB","frBT","frBV","dfPbLog","memLog","memErr","dfIdleRes","dfProbeOK","dfProbe","dfProbe2","dfWhite","dfWhiteRes","dfBlizRes","dfGhost","dfIconOff","dfTextOff","dfRevealHeavy","dfPbBuilt"]
cmd = "/run " + " ".join("DungeonsForeverDB.%s=nil" % k for k in keys)
print("len:", len(cmd))
chat(cmd)
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read().decode("utf-8", "replace")
left = [k for k in keys if ('"%s"' % k) in data]
print("leftover:", left if left else "clean")

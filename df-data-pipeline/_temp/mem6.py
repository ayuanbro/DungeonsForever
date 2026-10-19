import subprocess, sys, time, os, json
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
chat("/run DungeonsForeverDB.dfNoPrebuild=true DungeonsForeverDB.dfm=nil")
chat("/reload"); time.sleep(10)
chat("/run DungeonsForeverDB.dfm={b=collectgarbage'count'}")
chat("/run DF_NS.Open() DF_NS.DungeonUI.SwitchSub'Gear' collectgarbage'collect' DungeonsForeverDB.dfm.gear=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Raids' collectgarbage'collect' DungeonsForeverDB.dfm.raids=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Professions' collectgarbage'collect' DungeonsForeverDB.dfm.prof=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Explore' collectgarbage'collect' DungeonsForeverDB.dfm.explore=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Collections' collectgarbage'collect' DungeonsForeverDB.dfm.colls=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Factions' collectgarbage'collect' DungeonsForeverDB.dfm.facs=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Bis' collectgarbage'collect' DungeonsForeverDB.dfm.bis=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Tier' collectgarbage'collect' DungeonsForeverDB.dfm.tier=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'PvP' collectgarbage'collect' DungeonsForeverDB.dfm.pvp=collectgarbage'count'")
chat("/run DF_NS.Toggle()")
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read().replace(b"\r\n", b"\n").decode("utf-8", "replace")
i = data.find('"dfm"')
j = i
while True:
    j = data.find("\n}", j + 1)
    if j < 0 or data[j+2:j+3] != ",":
        break
seg = data[i:j]
vals = {}
for line in seg.split("\n"):
    line = line.strip().rstrip(",")
    if line.startswith('["') and "= " in line and "{" not in line:
        k = line.split('"')[1]
        try: vals[k] = float(line.split("= ")[1])
        except: pass
prev = None
for k in ("b", "gear", "raids", "prof", "explore", "colls", "facs", "bis", "tier", "pvp"):
    if k not in vals: print(k, "MISSING"); continue
    d = "" if prev is None else "  (+%.2f MB)" % ((vals[k]-prev)/1024)
    print(f"{k:10s} {vals[k]/1024:9.2f} MB{d}")
    prev = vals[k]

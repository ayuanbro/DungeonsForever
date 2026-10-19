import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
def probe(tag):
    chat("/run local c,r=0,0 local function w(f) c=c+1 for _,k in ipairs({f:GetRegions()}) do r=r+1 end for _,k in ipairs({f:GetChildren()}) do w(k) end end w(_G.DungeonsForever_MainFrame) DungeonsForeverDB.fr" + tag + "={f=c,g=r,h=collectgarbage'count'}")
chat("/run DungeonsForeverDB.dfNoPrebuild=nil DungeonsForeverDB.frA=nil DungeonsForeverDB.frB=nil")
chat("/reload"); time.sleep(10)
probe("A")
chat("/run DungeonsForeverDB.dfNoPrebuild=true")
chat("/reload"); time.sleep(10)
probe("B")
chat("/run DF_NS.Open() DF_NS.DungeonUI.SwitchSub'Gear' collectgarbage'collect' DungeonsForeverDB.frBG=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Raids' collectgarbage'collect' DungeonsForeverDB.frBR=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Professions' collectgarbage'collect' DungeonsForeverDB.frBP=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Explore' collectgarbage'collect' DungeonsForeverDB.frBE=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Collections' collectgarbage'collect' DungeonsForeverDB.frBC=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Factions' collectgarbage'collect' DungeonsForeverDB.frBF=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Bis' collectgarbage'collect' DungeonsForeverDB.frBB=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Tier' collectgarbage'collect' DungeonsForeverDB.frBT=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'PvP' collectgarbage'collect' DungeonsForeverDB.frBV=collectgarbage'count'")
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read().replace(b"\r\n", b"\n").decode("utf-8", "replace")
import re
for k in ("frA", "frB", "frBG", "frBR", "frBP", "frBE", "frBC", "frBF", "frBB", "frBT", "frBV"):
    i = data.find('"%s"' % k)
    if i < 0:
        print(k, "MISSING"); continue
    j = data.find("},", i)
    seg = data[i:j]
    d = {}
    for line in seg.split("\n"):
        line = line.strip().rstrip(",")
        if line.startswith('["'):
            key = line.split('"')[1]
            val = line.split("= ")[1] if "= " in line else ""
            d[key] = val
    print(k, d)

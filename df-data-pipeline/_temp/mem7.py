import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
chat("/run DungeonsForeverDB.dfPrebuild=nil DungeonsForeverDB.dfNoPrebuild=nil DungeonsForeverDB.dfm=nil DungeonsForeverDB.dfMemProbe=nil")
chat("/reload"); time.sleep(10)
chat("/run local c,r=0,0 local function w(f) c=c+1 for _,k in ipairs({f:GetRegions()}) do r=r+1 end for _,k in ipairs({f:GetChildren()}) do w(k) end end w(_G.DungeonsForever_MainFrame) DungeonsForeverDB.dfmc={f=c,g=r}")
chat("/run DF_NS.Open() DF_NS.DungeonUI.SwitchSub'Gear' collectgarbage'collect' DungeonsForeverDB.dfmg=collectgarbage'count'")
chat("/run DF_NS.DungeonUI.SwitchSub'Raids' collectgarbage'collect' DungeonsForeverDB.dfmr=collectgarbage'count'")
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read().replace(b"\r\n", b"\n").decode("utf-8", "replace")
import re
for k in ("dfmc", "dfmg", "dfmr"):
    m = re.search(r'\["%s"\] = ([\d.{][^,}]*|{[^}]*})' % k, data)
    print(k, m.group(1) if m else "MISSING")

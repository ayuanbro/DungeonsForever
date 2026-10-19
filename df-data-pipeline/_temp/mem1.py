import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
chat("/run DungeonsForeverDB.memLog=nil")
chat("/reload"); time.sleep(8)
chat("/run DungeonsForeverDB.memLog={} DungeonsForeverDB.memLog.base=collectgarbage'count'")
chat("/run ns.Open() ns.DungeonUI.SwitchSub'Gear' collectgarbage'collect' DungeonsForeverDB.memLog.Gear=collectgarbage'count' ns.Toggle()")
chat("/run ns.Open() ns.DungeonUI.SwitchSub'Raids' collectgarbage'collect' DungeonsForeverDB.memLog.Raids=collectgarbage'count'")
chat("/run ns.DungeonUI.SwitchSub'Professions' collectgarbage'collect' DungeonsForeverDB.memLog.Prof=collectgarbage'count'")
chat("/run ns.DungeonUI.SwitchSub'Explore' collectgarbage'collect' DungeonsForeverDB.memLog.Explore=collectgarbage'count'")
chat("/run ns.DungeonUI.SwitchSub'Collections' collectgarbage'collect' DungeonsForeverDB.memLog.Colls=collectgarbage'count'")
chat("/run ns.DungeonUI.SwitchSub'Factions' collectgarbage'collect' DungeonsForeverDB.memLog.Facs=collectgarbage'count'")
chat("/run ns.DungeonUI.SwitchSub'Bis' collectgarbage'collect' DungeonsForeverDB.memLog.Bis=collectgarbage'count'")
chat("/run ns.DungeonUI.SwitchSub'Tier' collectgarbage'collect' DungeonsForeverDB.memLog.Tier=collectgarbage'count'")
chat("/run ns.DungeonUI.SwitchSub'PvP' collectgarbage'collect' DungeonsForeverDB.memLog.PvP=collectgarbage'count'")
chat("/run ns.Toggle() collectgarbage'collect' DungeonsForeverDB.memLog.afterClose=collectgarbage'count'")
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"memLog"')
print(txt[i:txt.find('}', i)+1] if i >= 0 else "NO memLog")

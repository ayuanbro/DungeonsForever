import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
chat("/reload"); time.sleep(8)
chat("/run DF_NS.Open() DF_NS.DungeonUI.SwitchSub'Raids' local sb=DF_NS.DungeonUI.subBuilt local s='' if sb then for k in pairs(sb) do s=s..k..'='..tostring(sb[k])..' ' end end DungeonsForeverDB.dfsb=s")
chat("/run local c,r=0,0 local function w(f) c=c+1 for _,k in ipairs({f:GetRegions()}) do r=r+1 end for _,k in ipairs({f:GetChildren()}) do w(k) end end w(_G.DungeonsForever_MainFrame) DungeonsForeverDB.dfmc2={f=c,g=r}")
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read().replace(b"\r\n", b"\n").decode("utf-8", "replace")
i = data.find('"dfsb"')
print("SB:", data[i:i+300] if i >= 0 else "MISSING")
i = data.find('"dfmc2"')
print("CNT:", data[i:i+200] if i >= 0 else "MISSING")

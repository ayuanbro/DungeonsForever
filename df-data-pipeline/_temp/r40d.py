import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
chat("/run DungeonsForeverDB.dfAutoTest=nil DungeonsForeverDB.dfIdleRes=nil")
chat("/reload"); time.sleep(7)
chat("/run dfS={} dfSL=0 dfF=CreateFrame'Frame' dfF:Show() dfF:SetScript('OnUpdate',function(s) local n=debugprofilestop() local d=n-dfSL dfSL=n if d>0 and d<5000 then dfS[#dfS+1]=d end end)")
time.sleep(9)
chat("/run dfF:SetScript('OnUpdate',nil) dfMX=0 dfC=0")
chat("/run for i,v in ipairs(dfS) do if v>dfMX then dfMX=v end if v>100 then dfC=dfC+1 end end")
chat("/run DungeonsForeverDB.dfIdleRes={mx=dfMX,c=dfC,n=#dfS}")
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"dfIdleRes"')
print("IDLE:", txt[i:txt.find('}', i)] if i >= 0 else "NO dfIdleRes")

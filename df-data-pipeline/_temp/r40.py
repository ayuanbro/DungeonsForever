import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
mk = "/run dfS={} dfSL=0 dfF=CreateFrame'Frame' dfF:Show() dfF:SetScript('OnUpdate',function(s) local n=debugprofilestop() local d=n-dfSL dfSL=n if d>0 and d<5000 then dfS[#dfS+1]=d end end)"
fin = "/run dfF:SetScript('OnUpdate',nil) local mx,c=0,0 local sp='' for i,v in ipairs(dfS) do if v>mx then mx=v end if v>100 and c<10 then c=c+1 sp=sp..format('%.1f:%.0f ',i/60,v) end end DungeonsForeverDB.dfIdleRes={mx=mx,c100=c,sp=sp,n=#dfS}"
chat("/run DungeonsForeverDB.dfAutoTest=nil")
chat("/reload"); time.sleep(2)
chat(mk)
time.sleep(9)
chat(fin)
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"dfIdleRes"')
print("IDLE:", txt[i:txt.find('}', i)] if i >= 0 else "NO dfIdleRes")

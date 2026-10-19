import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
mk = "/run dfS={} dfSL=0 dfF=CreateFrame'Frame' dfF:Show() dfF:SetScript('OnUpdate',function(s) local n=debugprofilestop() local d=n-dfSL dfSL=n if d>0 and d<5000 then dfS[#dfS+1]=d end end)"
fin = "/run dfF:SetScript('OnUpdate',nil) ToggleCharacter('PaperDollFrame') local mx,c=0,0 for _,v in ipairs(dfS) do if v>mx then mx=v end if v>40 then c=c+1 end end DungeonsForeverDB.dfBlizRes={mx=mx,c=c,n=#dfS}"
chat("/reload"); time.sleep(6)
chat(mk)
chat("/run ToggleCharacter('PaperDollFrame')"); time.sleep(6)
chat(fin)
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"dfBlizRes"')
print("BLIZ:", txt[i:i+120] if i >= 0 else "NO dfBlizRes")

import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
c1 = "/run dfW=CreateFrame'Frame' dfW:SetBackdrop{bgFile='Interface\\\\Buttons\\\\WHITE8x8'} dfW:SetBackdropColor(0.06,0.07,0.1,0.95) dfW:SetSize(900,560) dfW:SetPoint'CENTER' dfW:SetFrameStrata'HIGH'"
c2 = "/run dfW.s={} dfW.l=0 dfW:Show() dfW:SetScript('OnUpdate',function(s) local n=debugprofilestop() local d=n-s.l s.l=n if d>0 and d<5000 then s.s[#s.s+1]=d end end)"
fin = "/run dfW:SetScript('OnUpdate',nil) dfW:Hide() local mx,c=0,0 for _,v in ipairs(dfW.s) do if v>mx then mx=v end if v>40 then c=c+1 end end DungeonsForeverDB.dfWhiteRes={mx=mx,c=c,n=#dfW.s}"
print("len1=%d len2=%d lenF=%d" % (len(c1), len(c2), len(fin)))
chat("/reload"); time.sleep(6)
chat(c1); chat(c2); time.sleep(6)
chat(fin)
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"dfWhiteRes"')
print("WHITE:", txt[i:i+120] if i >= 0 else "NO dfWhiteRes")

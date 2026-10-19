import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
mk = ("/run local W=CreateFrame('Frame',nil,UIParent) "
      "W:SetBackdrop{bgFile='Interface\\\\Buttons\\\\WHITE8x8'} "
      "W:SetBackdropColor(0.06,0.07,0.1,0.95) W:SetSize(900,560) "
      "W:SetPoint('CENTER') W:SetFrameStrata('HIGH') "
      "W.s={} W.l=debugprofilestop() "
      "W:SetScript('OnUpdate',function(s) local n=debugprofilestop() local d=n-s.l s.l=n "
      "if d>0 and d<5000 then s.s[#s.s+1]=d end end) "
      "W:Show() dfW=W DungeonsForeverDB.dfWhiteN=nil")
fin = ("/run local W=dfW if W then W:SetScript('OnUpdate',nil) W:Hide() end "
       "local mx,c=0,0 if W then for _,v in ipairs(W.s) do if v>mx then mx=v end if v>40 then c=c+1 end end "
       "DungeonsForeverDB.dfWhiteRes={mx=mx,c=c,n=(W and #W.s) or 0} end")
chat("/reload"); time.sleep(6)
chat(mk); time.sleep(6)
chat(fin)
chat("/reload"); time.sleep(8)
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"dfWhiteRes"')
print("WHITE:", txt[i:i+120] if i >= 0 else "NO dfWhiteRes")

import sys, subprocess
lua = (
    "/run local D=DungeonsForeverDB local m=_G.DungeonsForever_MainFrame "
    "D.dfProbe={a1=m:GetAlpha(),s1=m:IsShown()} ns.Open() "
    "D.dfProbe.a2=m:GetAlpha() D.dfProbe.s2=m:IsShown()"
)
r = subprocess.run([sys.executable, "_temp/bg_chat.py", "--open", lua])
sys.exit(r.returncode)

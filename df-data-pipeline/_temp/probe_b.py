import sys, subprocess
lua = "/run local D=DungeonsForeverDB local m=_G.DungeonsForever_MainFrame D.dfProbe.s3=m:IsShown() D.dfProbe.a3=m:GetAlpha()"
r = subprocess.run([sys.executable, "_temp/bg_chat.py", "--open", lua])
sys.exit(r.returncode)

import subprocess, sys, time, os
env = dict(os.environ, MSYS_NO_PATHCONV="1")
py = "C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
def chat(s):
    subprocess.run([py, "_temp/bg_chat.py", "--open", s], env=env)
    time.sleep(1)
chat("/run DungeonsForeverDB.dfAutoTest=nil DungeonsForeverDB.dfAutoTestResult=nil DungeonsForeverDB.dfAutoTestDelay=nil DungeonsForeverDB.dfIdleRes=nil")
print("cleaned")

import subprocess
import sys

WX = r"D:\workspace\project-024-wuxian-workshop\.venv\Scripts\wuxian.exe"

path = sys.argv[1]
timeout = sys.argv[2] if len(sys.argv) > 2 else "40"
code = open(path, "r", encoding="utf-8").read()
r = subprocess.run([WX, "run", "--timeout", timeout, code],
                   capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout.strip())
if r.returncode != 0:
    print("STDERR:", r.stderr.strip())

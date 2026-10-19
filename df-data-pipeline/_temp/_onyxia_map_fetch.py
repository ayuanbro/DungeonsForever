import json, os, subprocess, sys
LYCHEEDEV = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-6/lycheedev.cmd"
HOME = r"D:\workspace\project-021-lycheedev\data\lycheedev-home"
INSTALL = r"D:/Game/World of Warcraft/_classic_beta_"
PIN = "PIN-4cd78d2321a6e39c0288710cdd625542af87324553e566d2be6e361fc5095903"
OUT = r"D:/workspace/DungeonsForever/_temp/_onyxia_map_png"
os.makedirs(OUT, exist_ok=True)

def run(args):
    env = dict(os.environ); env["LYCHEEDEV_HOME"] = HOME
    p = subprocess.run([LYCHEEDEV] + args, capture_output=True, text=True, env=env)
    return json.loads(p.stdout)

d = run(["asset", "search", "--snapshot", PIN, "--listfile", "community-csv",
         "--query", "interface/worldmap/onyxiaslair", "--limit", "200", "--format", "json"])
files = (d.get("result") or {}).get("files") or []
print("found", len(files))
import re
tiles = {}
for f in files:
    m = re.match(r"^interface/worldmap/onyxiaslair/onyxiaslair1_(\d+)\.blp$", f.get("fileName") or "")
    if m: tiles[int(m.group(1))] = f["fileDataID"]
print(sorted(tiles.items()))
for n, fid in sorted(tiles.items()):
    outp = os.path.join(OUT, "t%d.png" % n)
    if os.path.exists(outp): continue
    r = run(["asset", "export", "--snapshot", PIN, "--installation", INSTALL,
             "--file-id", str(fid), "--encoding", "png", "--output", outp, "--format", "json"])
    if not r.get("ok"): print("export fail", n, r.get("error"))
from PIL import Image
grid = Image.new("RGB", (1024, 768), (0, 0, 0))
for n in range(1, 13):
    p = os.path.join(OUT, "t%d.png" % n)
    if not os.path.exists(p): print("missing", n); continue
    im = Image.open(p).convert("RGB")
    col = (n - 1) % 4; row = (n - 1) // 4
    grid.paste(im, (col * 256, row * 256))
grid.save(os.path.join(OUT, "onyxia_full.png"))
print("stitched")

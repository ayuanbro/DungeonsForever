# -*- coding: utf-8 -*-
"""对每个候选组导出首块瓦片（png），用于视觉核对是不是副本内地图。"""
import io, json, os, subprocess

LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
OUT = r"D:/workspace/DungeonsForever/_temp/_mapcheck"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")
os.makedirs(OUT, exist_ok=True)

inv = json.load(open("_map_inv.json", encoding="utf-8"))
ex = json.load(open("_map_exists.json", encoding="utf-8"))
seen = {}
for did, cands in inv.items():
    for c in cands:
        seen.setdefault(c["path"], c)

def safe(p):
    return p.replace("Interface\WorldMap\\", "").replace("\\", "__")

todo = [(p, seen[p]) for p in sorted(seen) if ex.get(p, {}).get("ok")]
print("待导出 %d 块" % len(todo), flush=True)
done = 0
for i, (p, c) in enumerate(todo, 1):
    f = os.path.join(OUT, safe(p) + ".png")
    if os.path.exists(f) and os.path.getsize(f) > 1000:
        done += 1; continue
    r = subprocess.run([LYCH, "asset", "export", "--snapshot", PIN, "--installation", INST,
                        "--file-id", str(c["firstFid"]), "--encoding", "png",
                        "--output", f, "--overwrite", "--format", "json"],
                       capture_output=True, text=True, env=env, shell=True)
    ok = os.path.exists(f) and os.path.getsize(f) > 1000
    if ok: done += 1
    print("%3d/%d %-42s %s" % (i, len(todo), safe(p), "ok" if ok else "FAIL"), flush=True)
print("\n导出成功 %d/%d" % (done, len(todo)))

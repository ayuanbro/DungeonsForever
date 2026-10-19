# -*- coding: utf-8 -*-
"""批量验证候选瓦片组在本客户端是否真实存在（asset inspect --offline）。"""
import io, json, os, subprocess, sys

LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
INST = "D:/Game/World of Warcraft/_classic_beta_"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")

inv = json.load(open("_map_inv.json", encoding="utf-8"))
seen = {}
for did, cands in inv.items():
    for c in cands:
        seen.setdefault(c["path"], c)

out = {}
order = sorted(seen)
for i, p in enumerate(order, 1):
    c = seen[p]
    r = subprocess.run([LYCH, "asset", "inspect", "--snapshot", PIN, "--installation", INST,
                        "--file-id", str(c["firstFid"]), "--offline", "--format", "json"],
                       capture_output=True, text=True, env=env, shell=True)
    ok, code = False, ""
    try:
        d = json.loads(r.stdout)
        ok = bool(d.get("ok"))
        if not ok:
            e = d.get("error") or {}
            code = str(e.get("code") or e.get("message") or "")[:60]
    except Exception as ex:
        code = "parse:" + str(ex)[:40]
    out[p] = {"ok": ok, "code": code, "fid": c["firstFid"], "n": c["n"]}
    print("%3d/%d %-4s %-46s %s" % (i, len(order), "Y" if ok else "N", p, code), flush=True)

json.dump(out, open("_map_exists.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n存在 %d / %d" % (sum(1 for v in out.values() if v["ok"]), len(out)))

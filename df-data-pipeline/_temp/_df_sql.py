# -*- coding: utf-8 -*-
"""在 forever 客户端上跑只读 SQL（lycheedev data sql）。用法: _df_sql.py "<sql>" """
import json, os, subprocess, sys
LYCH = r"C:/Users/Administrator/.workbuddy/binaries/node/versions/22.22.2-3/lycheedev.cmd"
PIN = "PIN-b4d284e3188d08779c84dd1537b28e34a57e2ff609b67a423c0204bd1d43bbeb"
env = dict(os.environ, LYCHEEDEV_HOME=r"D:\workspace\project-021-lycheedev\data\lycheedev-home")
def q(sql):
    r = subprocess.run([LYCH, "data", "sql", "--snapshot", PIN,
                        "--installation", "D:/Game/World of Warcraft",
                        "--sql", sql, "--format", "json"],
                       capture_output=True, text=True, env=env, shell=True)
    d = json.loads(r.stdout)
    if not d.get("ok"):
        return None, d.get("error")
    res = d["result"]["result"]
    return res, None
if __name__ == "__main__":
    res, err = q(sys.argv[1])
    if err:
        print("ERR", json.dumps(err, ensure_ascii=False)[:300]); raise SystemExit(1)
    cols, rows = res.get("columns"), res.get("rows") or []
    print("cols:", cols)
    print("n =", len(rows))
    for x in rows:
        print("  ", json.dumps(x, ensure_ascii=False))

import sqlite3, sys, json

db = "D:/workspace/project-021-lycheedev/data/lycheedev-home/state/toolkit.sqlite"
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
cur = con.cursor()

print("== tables ==")
for (n,) in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    print("  ", n)

print("== key prefixes ==")
try:
    rows = cur.execute("SELECT key, length(value) FROM documents").fetchall()
    pref = {}
    for k, ln in rows:
        p = k.split("/")[0]
        pref[p] = pref.get(p, 0) + 1
    for p, c in sorted(pref.items()):
        print(f"   {p}: {c}")
except Exception as e:
    print("  err", e)

print("== keys (session/work/bootstrap/probe) ==")
for k, ln in cur.execute("SELECT key, length(value) FROM documents").fetchall():
    if any(k.startswith(x) for x in ("session/", "work/", "bootstrap/", "probe/")):
        print(f"   {k}   len={ln}")

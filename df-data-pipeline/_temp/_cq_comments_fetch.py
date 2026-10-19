import json, io, os, re, subprocess, time, sys
import urllib.request
from playwright.sync_api import sync_playwright

QB = r"C:/Program Files (x86)/Tencent/QQBrowser/QQBrowser.exe"
PORT = 9222
PROFILE = r"D:/workspace/DungeonsForever/_temp/_qqb_profile"
OUT = r"D:/workspace/DungeonsForever/_temp/_cq_comments_raw.json"
IDS = json.load(io.open(r"D:/workspace/DungeonsForever/_temp/_cq_quest_ids.json", encoding="utf-8"))

proc = subprocess.Popen([
    QB, f"--remote-debugging-port={PORT}",
    f"--user-data-dir={PROFILE}",
    "--no-first-run", "--no-default-browser-check",
    "--disable-features=Translate", "--window-position=3200,0",
    "about:blank",
])
ok = False
for _ in range(30):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2)
        ok = True
        break
    except Exception:
        time.sleep(1)
if not ok:
    print("CDP not ready")
    sys.exit(1)

data = {}
if os.path.exists(OUT):
    try:
        data = json.load(io.open(OUT, encoding="utf-8"))
    except Exception:
        data = {}

with sync_playwright() as p:
    br = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = br.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(30000)
    todo = [i for i in IDS if str(i) not in data]
    print("todo", len(todo), flush=True)
    for k, qid in enumerate(todo):
        url = f"https://cn.wowhead.com/quest={qid}"
        for attempt in (1, 2):
            try:
                page.goto(url, timeout=40000, wait_until="domcontentloaded")
                page.wait_for_timeout(1800)
                res = page.evaluate("() => ({ c: (window.lv_comments0 || null), t: (document.title || '') })")
                c = res.get("c")
                if isinstance(c, list):
                    data[str(qid)] = {
                        "title": res.get("t", ""),
                        "n": len(c),
                        "comments": [
                            {
                                "body": x.get("body", ""),
                                "rating": x.get("rating", 0),
                                "date": x.get("date", ""),
                                "replies": [
                                    {"body": r.get("body", ""), "rating": r.get("rating", 0)}
                                    for r in (x.get("replies") or [])
                                ],
                            }
                            for x in c
                            if not x.get("deleted")
                        ],
                    }
                else:
                    data[str(qid)] = {"title": res.get("t", ""), "n": 0, "comments": []}
                break
            except Exception as e:
                if attempt == 2:
                    data[str(qid)] = {"title": "", "n": -1, "comments": [], "err": str(e)[:120]}
                else:
                    time.sleep(2)
        if k % 10 == 0 or k == len(todo) - 1:
            with io.open(OUT, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"{k+1}/{len(todo)} done (last={qid})", flush=True)

with io.open(OUT, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)
print("ALL DONE", len(data), flush=True)
try:
    proc.terminate()
except Exception:
    pass

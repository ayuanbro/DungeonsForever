import json, io, os, re, subprocess, time, sys, urllib.request
from playwright.sync_api import sync_playwright

QB = r"C:/Program Files (x86)/Tencent/QQBrowser/QQBrowser.exe"
PORT = 9222
PROFILE = r"D:/workspace/DungeonsForever/_temp/_qqb_profile"
QID = sys.argv[1] if len(sys.argv) > 1 else "78261"

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

with sync_playwright() as p:
    br = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = br.contexts[0]
    page = ctx.new_page()
    page.set_default_timeout(40000)
    url = f"https://www.wowhead.com/forever/cn/quest={QID}"
    page.goto(url, timeout=45000, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)
    res = page.evaluate("""() => {
        const vars = {};
        for (const k of Object.keys(window)) {
            if (k.indexOf('lv_comments') === 0) vars[k] = (window[k]||[]).length;
        }
        return {
            title: document.title,
            vars: vars,
            hasJump: !!document.querySelector('#jump-to-comments'),
            nComments: document.querySelectorAll('.comment').length,
            bodyLen: (document.body && document.body.innerText || '').length,
        };
    }""")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    c = page.evaluate("() => window.lv_comments0 || null")
    if isinstance(c, list) and c:
        out = {
            "title": res.get("title", ""),
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
        io.open(r"D:/workspace/DungeonsForever/_temp/_cq_refetch.json", "w", encoding="utf-8").write(
            json.dumps({QID: out}, ensure_ascii=False, indent=1))
        print("saved", len(c), "comments")
    page.close()
proc.terminate()

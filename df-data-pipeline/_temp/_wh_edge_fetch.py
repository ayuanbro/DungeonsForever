import subprocess, time, sys, urllib.request
from playwright.sync_api import sync_playwright

EDGE = r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
PORT = 9223
PROFILE = r"D:/workspace/DungeonsForever/_temp/_edge_pw_profile"
OUT = r"D:/workspace/DungeonsForever/_temp/_wh_q92434.html"
URL = "https://www.wowhead.com/forever/cn/quest=92434/blood-in-the-streets"

proc = subprocess.Popen([
    EDGE, f"--remote-debugging-port={PORT}",
    f"--user-data-dir={PROFILE}",
    "--headless=new", "--no-first-run", "--no-default-browser-check",
    "--disable-blink-features=AutomationControlled",
    "--proxy-server=http://127.0.0.1:7897",
    "--window-size=1400,2000", "--window-position=3200,0",
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
    print("CDP port not ready")
    sys.exit(1)

with sync_playwright() as p:
    br = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = br.contexts[0]
    page = ctx.new_page()
    page.goto(URL, timeout=60000, wait_until="domcontentloaded")
    time.sleep(9)
    html = page.content()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("len", len(html))

proc.terminate()

import subprocess, time, sys, urllib.request
from playwright.sync_api import sync_playwright

QB = r"C:/Program Files (x86)/Tencent/QQBrowser/QQBrowser.exe"
PORT = 9222
PROFILE = r"D:/workspace/DungeonsForever/_temp/_qqb_profile"
URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.wowhead.com/zhCN/item=1194"
OUT = "D:/workspace/DungeonsForever/_temp/_cdp_test.html"

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
    print("CDP 端口未就绪")
    sys.exit(1)

with sync_playwright() as p:
    br = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
    ctx = br.contexts[0]
    page = ctx.new_page()
    page.goto(URL, timeout=60000, wait_until="domcontentloaded")
    time.sleep(8)
    html = page.content()
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("len", len(html))
    print("sold-by count:", html.count("sold-by"))
    print("title:", page.title())
    low = html[:3000].lower()
    print("ban?:", ("403" in low) or ("access denied" in low) or ("captcha" in low) or ("请稍后" in html))
    page.close()
    br.close()
print("saved:", OUT)

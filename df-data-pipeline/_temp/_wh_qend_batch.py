import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

ROOT = r"D:/workspace/DungeonsForever"
QB = r"C:/Program Files (x86)/Tencent/QQBrowser/QQBrowser.exe"
PORT = 9222
PROFILE = ROOT + "/_temp/_qqb_profile"
CACHE = ROOT + "/_temp/_wh_qend"
OUT = ROOT + "/_temp/_wh_qend_raw.json"


def quest_ids():
    src = io.open(ROOT + "/Core/Data/Data_DungeonQuests.lua", encoding="utf-8").read()
    ids = set()
    for m in re.finditer(r'\{ (\d{3,7}), "[AH]", ', src):
        ids.add(int(m.group(1)))
    for m in re.finditer(r'\[(\d{3,7})\] = \{ lv', src):
        ids.add(int(m.group(1)))
    return sorted(ids)


def grab_json_block(html, marker):
    i = html.find(marker)
    if i < 0:
        return None
    i = html.find("(", i)
    if i < 0:
        return None
    depth = 0
    for j in range(i, len(html)):
        c = html[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return html[i + 1:j + 1]
    return None


def parse_page(html):
    res = {"end": [], "start": []}
    blk = grab_json_block(html, "var myMapper = new Mapper(")
    if blk:
        try:
            data = json.loads(blk)
        except Exception:
            data = None
        if isinstance(data, dict):
            objs = data.get("objectives") or {}
            for area, node in objs.items():
                if not isinstance(node, dict):
                    continue
                zone = node.get("zone") or ""
                for lvl in node.get("levels") or []:
                    for it in lvl or []:
                        if not isinstance(it, dict):
                            continue
                        pt = it.get("point")
                        if pt not in ("end", "start"):
                            continue
                        co = it.get("coord") or []
                        if len(co) < 2:
                            continue
                        res[pt].append({
                            "npcid": it.get("id"),
                            "name": it.get("name") or "",
                            "x": co[0],
                            "y": co[1],
                            "zone": zone,
                            "area": area,
                        })
    if not res["end"]:
        m = re.search(r'结束于：<a href="[^"]*npc=(\d+)"[^>]*>([^<]+)</a>', html)
        if m:
            res["end"].append({"npcid": int(m.group(1)), "name": m.group(2),
                               "x": None, "y": None, "zone": "", "area": None})
    return res


def ensure_browser():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2)
        return None
    except Exception:
        pass
    proc = subprocess.Popen([
        QB, f"--remote-debugging-port={PORT}",
        f"--user-data-dir={PROFILE}",
        "--no-first-run", "--no-default-browser-check",
        "--disable-features=Translate", "--window-position=3200,0",
        "about:blank",
    ])
    for _ in range(30):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2)
            return proc
        except Exception:
            time.sleep(1)
    print("CDP 端口未就绪")
    sys.exit(1)


def main():
    limit = 0
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        limit = int(sys.argv[1])
    os.makedirs(CACHE, exist_ok=True)
    ids = quest_ids()
    todo = [q for q in ids if not os.path.exists(f"{CACHE}/{q}.json")]
    if limit:
        todo = todo[:limit]
    print(f"total={len(ids)} todo={len(todo)}", flush=True)
    if not todo:
        return
    proc = ensure_browser()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.connect_over_cdp(f"http://127.0.0.1:{PORT}")
        ctx = br.contexts[0]
        page = ctx.new_page()
        t0 = time.time()
        for n, qid in enumerate(todo, 1):
            url = f"https://www.wowhead.com/forever/cn/quest={qid}"
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")
            except Exception as e:
                print(f"[{n}/{len(todo)}] {qid} goto-fail {e}", flush=True)
                continue
            html = None
            for _ in range(12):
                try:
                    html = page.content()
                except Exception:
                    time.sleep(0.5)
                    continue
                if "myMapper" in html or "结束于" in html:
                    break
                time.sleep(0.5)
            if html is None:
                continue
            res = parse_page(html)
            with io.open(f"{CACHE}/{qid}.json", "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False)
            el = time.time() - t0
            print(f"[{n}/{len(todo)}] {qid} end={len(res['end'])} start={len(res['start'])} {el/n:.1f}s/页", flush=True)
        page.close()
    if proc:
        proc.terminate()
    merged = {}
    for fn in os.listdir(CACHE):
        if fn.endswith(".json"):
            merged[fn[:-5]] = json.load(io.open(f"{CACHE}/{fn}", encoding="utf-8"))
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1)
    print("merged", len(merged), "->", OUT, flush=True)


if __name__ == "__main__":
    main()

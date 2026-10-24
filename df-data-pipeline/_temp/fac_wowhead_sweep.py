# -*- coding: utf-8 -*-
"""全量扫描 DBC 缺失任务：wowhead Side 字段裁决（classic 先，forever 兜底）。"""
import json
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

OUT = "_temp/fac_wowhead_sweep.json"


def load_ours():
    src = open("D:/workspace/DungeonsForever/Core/Data/Data_DungeonQuests.lua",
               encoding="utf-8").read()
    ids = []
    cur = None
    for line in src.splitlines():
        m = re.match(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{', line)
        if m:
            cur = m.group(1)
            continue
        if cur is None or not line.strip().startswith("{ "):
            continue
        m2 = re.match(r'^\s*\{\s*(\d+),\s*("(?:A|H)"|nil)\s*,', line)
        if m2:
            ids.append(int(m2.group(1)))
    return sorted(set(ids))


def fetch(u, tries=4):
    for _ in range(tries):
        r = subprocess.run(
            ["curl", "-s", "-L", "-x", "http://127.0.0.1:7897",
             "https://r.jina.ai/" + u], capture_output=True, timeout=90)
        h = r.stdout.decode("utf-8", "replace")
        if len(h) > 8000:
            return h
        time.sleep(5)
    return h


def side_of(h):
    m = re.search(r'Side:.{0,20}?(Alliance|Horde|Both|None)', h)
    if m:
        return m.group(1)
    for lit in ('Side: Alliance', 'Side: Horde', 'Side: Both', 'Side: None'):
        if lit in h:
            return lit.split(': ')[1]
    return None


def title_of(h):
    t = re.search(r'^Title: (.{0,70})', h, re.M)
    return t.group(1) if t else ""


def main():
    qj = json.load(open("_temp/questie/questie_forever.json", encoding="utf-8"))
    races = qj["quest_races"]
    todo = [q for q in load_ours()
            if str(q) not in races and q not in (1654, 8418, 7647, 1049)]
    print(f"待扫 {len(todo)} 个任务", flush=True)
    try:
        done = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        done = {}
    n = 0
    for q in todo:
        if str(q) in done and done[str(q)].get("side"):
            continue
        n += 1
        side, zone, name = None, None, ""
        for z in ("classic", "forever"):
            h = fetch(f"https://www.wowhead.com/{z}/quest={q}")
            s = side_of(h)
            if s:
                side, zone, name = s, z, title_of(h)
                break
            time.sleep(1.5)
        done[str(q)] = {"side": side, "zone": zone, "name": name}
        if n % 10 == 0 or side is None:
            print(f"[{n}] {q} -> {side} {name}", flush=True)
        json.dump(done, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        time.sleep(2)
    print(f"完成，共 {len(done)} 条", flush=True)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""抓 wowhead quest 页的任务地图坐标 -> _gqf_quest_coords.json
输出: {qid: {"area": zoneId(areaID), "x": float, "y": float}}"""
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_gqf_name_cache.json")
OUT = os.path.join(HERE, "_gqf_quest_coords.json")

MAPPER_RE = re.compile(
    r'new Mapper\(\{.*?"objectives":\{"(\d+)":\{"zone":"[^"]*"'
    r'.*?"coord":\[([0-9.]+),([0-9.]+)\]', re.S)


def fetch(session, qid):
    r = session.get("https://www.wowhead.com/forever/quest=%d" % qid,
                    timeout=30)
    if r.status_code != 200:
        return None
    m = MAPPER_RE.search(r.text)
    if not m:
        return None
    return {"area": int(m.group(1)),
            "x": float(m.group(2)), "y": float(m.group(3))}


def main():
    from curl_cffi import requests
    sess = requests.Session(
        impersonate="safari17_0",
        proxies={"https": "http://127.0.0.1:7897",
                 "http": "http://127.0.0.1:7897"})
    qcache = json.load(open(CACHE, encoding="utf-8"))["quests"]
    todo = sorted(v["id"] for v in qcache.values() if v.get("id"))
    out = {}
    if os.path.exists(OUT):
        try:
            out = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            out = {}
    print("quest coords todo %d, done %d" % (len(todo), len(out)),
          flush=True)
    fails = 0
    got = 0
    for qid in todo:
        if str(qid) in out:
            continue
        try:
            d = fetch(sess, qid)
            fails = 0
        except Exception:
            fails += 1
            d = None
            if fails >= 5:
                print("network down, abort", flush=True)
                break
            time.sleep(10)
        out[str(qid)] = d
        if d:
            got += 1
        print("quest %d -> %s" % (qid, d), flush=True)
        json.dump(out, open(OUT, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=0)
        time.sleep(2.5)
    hit = sum(1 for v in out.values() if v)
    print("coords hit %d/%d" % (hit, len(todo)), flush=True)


if __name__ == "__main__":
    main()

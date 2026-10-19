# -*- coding: utf-8 -*-
import io, json, re, sys, time
sys.stdout.reconfigure(encoding="utf-8")
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36"}
UNI = re.compile(r"\\u([0-9a-fA-F]{4})")
ANCHOR = re.compile(r"\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]")

# 1) 数据行解码定位
src = io.open("../Core/Data/Data_DungeonQuests.lua", encoding="utf-8").read()
for key in ("哈文法", "瘟疫肉块", "禁锢灵魂的遗物", "玛洛尔", "克罗卡斯", "马杜克镇长"):
    for m in re.finditer(r"^.*%s.*$" % key, src, re.M):
        line = m.group(0)
        qm = re.match(r"\s*\{ (\d{3,6})", line)
        tail = re.findall(r"\{(\d{4,5}(?:, \d{4,5})*)\}", line)
        print(key, "q=", qm.group(1) if qm else "?", "itemids=", tail[:3], "|", line[:110])
    print()

def _get(url):
    for a in range(4):
        try:
            r = requests.get(url, headers=HDRS, proxy="http://127.0.0.1:7897",
                             impersonate="chrome", timeout=20)
        except Exception as e:
            print(" ERR", e); time.sleep(5); continue
        if r.status_code == 403:
            time.sleep((15, 25, 35, 45)[a]); continue
        return r
    return None

def ttl(url):
    r = _get(url)
    if r is None or r.status_code != 200:
        print(url, "->", r.status_code if r else None); return
    m = re.search(r"<title>(.*?)</title>", r.text, re.S)
    print(url.split("wowhead.com/")[-1], "->", m.group(1).strip() if m else None)

# 2) 物品/任务标题
for iid in (17044, 17045, 13982, 13986, 13984, 14002):
    ttl("https://www.wowhead.com/item=%d" % iid); time.sleep(1)

# 3) 克罗卡斯 (q7703 giver) 与 哈文法 (ccnq7621/7622)
for qid in (7703, 7621, 7622):
    r = _get("https://www.wowhead.com/classic/cn/quest=%d" % qid)
    if r is None or r.status_code != 200:
        print("ccnq%d none" % qid); continue
    txt = UNI.sub(lambda m: chr(int(m.group(1), 16)), r.text).replace("\\/", "/")
    ms = re.findall(r"(?:开始|结束)于：?\s*\[url=[^\]]*?npc=(\d+)\]([^[]+?)\[/url\]", txt)
    print("ccnq%d 锚:" % qid, ms[:4])
    if ms:
        ttl("https://www.wowhead.com/npc=%s" % ms[0][0])

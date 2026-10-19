# -*- coding: utf-8 -*-
"""列出多-giver 链的 data 未决成员 与 页面候选(中文, ID, EN官方名)，供人工对齐。"""
import io, json, os, re, sys, time

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_enus_wowhead.json")
cache = json.load(io.open(CACHE, encoding="utf-8"))
from curl_cffi import requests
HDRS = {"User-Agent": "Mozilla/5.0"}

def fetch_en(nid):
    key = "npc%d" % nid
    if key in cache and cache[key]:
        return cache[key]
    r = requests.get("https://www.wowhead.com/npc=%d" % nid, headers=HDRS,
                     proxy="http://127.0.0.1:7897", impersonate="chrome", timeout=20)
    t = None
    if r.status_code == 200:
        m = re.search(r"<title>(.*?)</title>", r.text, re.S)
        if m:
            t = re.sub(r"\s*-\s*NPC\s*-\s*.*$", "", m.group(1).strip())
    cache[key] = t
    json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))
    time.sleep(0.3)
    return t

GROUPS = {
    8151: ['卡瑞·雷角', '科索祖尔'],
    8233: ['奥莫克', '安妮莎尔', '奥米尔·火眼', '东尼·罗曼诺领主'],
    8250: ['瑟斯顿·科萨恩', '朱莉·雷线', '艾尔莎林', '恩尤'],
    8254: ['高阶牧师劳瑞娜', '马拉凯·克罗斯', '柯布神父', '阿斯塔利·逐星', '贾德莉亚',
           '艾萨莱斯特', '拉札鲁斯神父', '塞欧杜斯·霜须', '布莱纳·火崖', '克塞拉', '女祭司阿兰希雅'],
    8417: ['克里斯多夫·沃克', '凯夫·重锤', '达纳斯·刃咏'],
    8419: ['格罗达尔', '米尔科特', '卡尔·噬灵(✓?)', '泽弗洛斯特(✓)', '理查·科尔文', '瑟斯哈特',
           '亚历山大·考德尔', '厄苏拉·德林', '卢瑟·匹克曼', '山达尔', '卡托什'],
    9063: ['图拉克·符文图腾', '希尔·符文图腾', '德纳萨里安', '沙德拉斯·月树',
           '塞瑞德兰(✓)', '加诺斯·轻蹄', '戴兜帽的高赫尼'],
}
for qid, members in sorted(GROUPS.items()):
    pairs = cache.get("ccnq%d" % qid, {})
    print("=== q%d ===" % qid)
    print("  data 未决:", members)
    for cn, nid in sorted(pairs.items(), key=lambda x: x[1]):
        if cn == 'map':
            continue
        print("   候选: %s npc%d → %s" % (cn, nid, fetch_en(nid)))
json.dump(cache, io.open(CACHE, "w", encoding="utf-8"))

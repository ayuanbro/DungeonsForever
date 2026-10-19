# -*- coding: utf-8 -*-
"""对所有 foreverchanges 副本页出现过的任务，抓取任务详情页「阵营」字段，
与 Data_DungeonQuests.lua 的第 2 列阵营逐条比对。"""
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

SITE_QUESTS = "_temp/fc_site_quests.json"
OURS = "Core/Data/Data_DungeonQuests.lua"
SITE2OURS = {
    "excavation-site": "excavation_wetlands",
    "scarlet-monastery-graveyard": "sm_graveyard",
    "scarlet-monastery-library": "sm_library",
    "scarlet-monastery-armory": "sm_armory",
    "scarlet-monastery-cathedral": "sm_cathedral",
    "zulfarrak": "zul_farrak",
    "stratholme-main-gate": "strathlome_main",
    "stratholme-service-gate": "strathlome_service",
}


def fetch_side(qid):
    try:
        r = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "40",
             f"https://foreverchanges.pro/zh-cn/quest/{qid}"],
            capture_output=True, timeout=60)
        h = r.stdout.decode("utf-8", "replace")
    except Exception as e:
        return qid, None, str(e)
    fs = {}
    for m in re.finditer(r'<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>', h, re.S):
        k = ' '.join(re.sub(r'<[^>]+>', '', m.group(1)).split())
        v = ' '.join(re.sub(r'<[^>]+>', '', m.group(2)).split())
        fs[k] = v
    fac = fs.get("阵营", "")
    tag = "?"
    if "双方" in fac:
        tag = "b"
    elif fac and all(x in fac for x in ("联盟",)) and "部落" in fac:
        tag = "b"
    elif "联盟" in fac and "部落" not in fac:
        tag = "a"
    elif "部落" in fac and "联盟" not in fac:
        tag = "h"
    elif fac and "," in fac and "人类" in fac:
        tag = "b"
    return qid, tag, fac


def parse_ours():
    src = open(OURS, encoding="utf-8").read()
    out = {}
    cur = None
    dkg = re.compile(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{')
    row = re.compile(r'^\s*\{\s*(\d+),\s*(nil|"([AH])")\s*,')
    for line in src.splitlines():
        m = dkg.match(line)
        if m and 'ns.DungeonQuests' not in line:
            cur = m.group(1)
            out[cur] = {}
            continue
        if cur is None:
            continue
        mr = row.match(line)
        if mr:
            out[cur][int(mr.group(1))] = (mr.group(3) or 'b').lower()
    return out


def main():
    site = json.load(open(SITE_QUESTS, encoding="utf-8"))
    ours = parse_ours()
    allq = {}
    for slug, qs in site.items():
        key = SITE2OURS.get(slug, slug.replace("-", "_"))
        for qid in qs:
            allq.setdefault(int(qid), set()).add(key)
    ids = sorted(allq)
    print(f"站点任务总数 {len(ids)}，开始抓取详情页…", flush=True)
    res = {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for qid, tag, fac in ex.map(fetch_side, ids):
            res[qid] = (tag, fac)
    print("抓取完成\n", flush=True)

    mism = []
    for qid in ids:
        tag, fac = res[qid]
        for key in allq[qid]:
            o = ours.get(key, {}).get(qid)
            if o is None:
                continue
            if tag not in ("a", "h", "b"):
                continue
            if tag != o:
                mism.append((qid, key, tag, o, fac, site_ctx(site, qid)))
    print(f"===== 阵营不一致（站点详情页 vs 我方）: {len(mism)} =====")
    for qid, key, tag, o, fac, grp in mism:
        print(f"  quest {qid:6d} [{key}] 站点={tag} 我方={o}  站点阵营字段={fac!r}")
    json.dump({"mismatch": mism, "all": {str(k): v for k, v in res.items()}},
              open("_temp/fc_quest_side_verify.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def site_ctx(site, qid):
    for slug, qs in site.items():
        if qid in qs:
            return qs[qid].get("group", "")
    return ""


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

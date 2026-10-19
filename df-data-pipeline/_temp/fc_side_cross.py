# -*- coding: utf-8 -*-
"""三方交叉裁决副本任务阵营：fc 详情页 / wuxianwow side / 我方第 2 列。"""
import json
import re
import sys

SITE_QUESTS = "_temp/fc_site_quests.json"
SIDE_VERIFY = "_temp/fc_quest_side_verify.json"
WX = "_temp/_wx_quests.json"
OURS = "Core/Data/Data_DungeonQuests.lua"
SITE2OURS = {
    "excavation-site": "excavation_wetlands",
    "scarlet-monastery-graveyard": "sm_graveyard",
    "scarlet-monastery-library": "sm_library",
    "scarlet-monastery-armory": "sm_armory",
    "scarlet-monastery-cathedral": "sm_cathedral",
    "zulfarrak": "zul_farrak",
    "stratholme-main-gate": "stratholme_main",
    "stratholme-service-gate": "stratholme_service",
}


def parse_ours():
    src = open(OURS, encoding="utf-8").read()
    out, cur = {}, None
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


def wx_side(e):
    if not e:
        return None
    s = e.get('side')
    if s:
        return {'联盟': 'a', '部落': 'h', '双方阵营': 'b'}.get(s.strip())
    t = e.get('tmp', {}).get('side') if isinstance(e.get('tmp'), dict) else None
    if t:
        return {'联盟': 'a', '部落': 'h'}.get(t.strip())
    return None


def main():
    site = json.load(open(SITE_QUESTS, encoding="utf-8"))
    ours = parse_ours()
    sv = json.load(open(SIDE_VERIFY, encoding="utf-8"))["all"]
    wx = {str(x['id']): x for x in json.load(
        open(WX, encoding="utf-8"))["quests"]}

    rows = []
    for slug, qs in site.items():
        key = SITE2OURS.get(slug, slug.replace("-", "_"))
        for qid, meta in qs.items():
            qid = int(qid)
            o = ours.get(key, {}).get(qid)
            fc_tag, fc_fac = (sv.get(str(qid)) or ['?', ''])[:2]
            w = wx_side(wx.get(str(qid)))
            rows.append((qid, key, o, fc_tag, fc_fac, w,
                         wx.get(str(qid), {}).get('title', '')))

    print("===== 我方缺失（网站有、我方无）=====")
    seen = set()
    for qid, key, o, fc, fac, w, t in rows:
        if o is None and qid not in seen:
            seen.add(qid)
            print(f"  {qid:7d} [{key:24s}] fc={fc} wx={w} {t}")
    print(f"  合计 {len(seen)}")

    print("\n===== 阵营三方对照（不一致）=====")
    n = 0
    for qid, key, o, fc, fac, w, t in rows:
        if o is None:
            continue
        votes = [x for x in (fc, w) if x]
        if not votes:
            continue
        if any(v != o for v in votes):
            n += 1
            print(f"  {qid:7d} [{key:22s}] 我方={o} fc={fc}({fac}) wx={w}  {t}")
    print(f"  合计 {n}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

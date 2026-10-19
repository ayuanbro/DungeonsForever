# -*- coding: utf-8 -*-
"""对网站上出现但不在我方主表的任务，判定其归属：
主表 / PreExtra 前置表 / Alias 别名表 / PreNote 注释表 / 真缺口。"""
import json
import re
import sys

SRC = "Core/Data/Data_DungeonQuests.lua"
SITE_QUESTS = "_temp/fc_site_quests.json"
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


def main():
    src = open(SRC, encoding="utf-8").read()
    # 主表 id
    ids = set(re.findall(r'^\s*\{\s*(\d+),\s*(?:nil|"[AH]"),', src, re.M))
    ids = {int(x) for x in ids}
    # 挂在其它表里的 id（[123] = {...} 形式）
    tbl = {}
    for sec in ("DungeonQuestAlias", "DungeonQuestPreExtra",
                "DungeonQuestPreNote", "DungeonQuestShare"):
        m = re.search(r'ns\.%s\s*=\s*\{' % sec, src)
        if not m:
            continue
        body = src[m.end():]
        nxt = re.search(r'\nns\.[A-Za-z]+\s*=\s*\{', body)
        if nxt:
            body = body[:nxt.start()]
        tbl[sec] = {int(x) for x in re.findall(r'\[(\d+)\]\s*=', body)}
    for sec, s in tbl.items():
        print(f"{sec}: {len(s)} 个 id")

    site = json.load(open(SITE_QUESTS, encoding="utf-8"))
    byid = {}
    for slug, qs in site.items():
        key = SITE2OURS.get(slug, slug.replace("-", "_"))
        for qid, meta in qs.items():
            byid.setdefault(int(qid), (key, meta))

    print("\n===== 网站有、我方主表无 =====")
    for qid in sorted(byid):
        if qid in ids:
            continue
        key, meta = byid[qid]
        where = [s for s in tbl if qid in tbl[s]]
        tag = ("已在 " + "/".join(where)) if where else "★ 真缺口"
        print(f"  {qid:7d} [{key:22s}] side={meta['side']} "
              f"name={meta['name'][:38]:38s} {tag}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

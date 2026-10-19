# -*- coding: utf-8 -*-
"""抓 foreverchanges.pro 五人本页面，比对掉落与任务（含阵营分组）。"""
import json
import re
import subprocess
import sys

SITE_DUNGEONS = [
    "hall-of-thanes", "ragefire-chasm", "ruins-of-lordaeron", "wailing-caverns",
    "the-deadmines", "shadowfang-keep", "blackfathom-deeps", "the-stockade",
    "excavation-site", "city-of-dalaran", "gnomeregan", "razorfen-kraul",
    "scarlet-monastery-graveyard", "scarlet-monastery-library", "the-drowned-city",
    "scarlet-monastery-armory", "razorfen-downs", "scarlet-monastery-cathedral",
    "kroldok-stronghold", "uldaman", "zulfarrak", "maraudon", "alcaz-prison",
    "sunken-temple", "blackrock-depths", "dire-maul-east", "blackmaw-hold",
    "lower-blackrock-spire", "dire-maul-north", "dire-maul-west", "scholomance",
    "shapers-terrace", "stratholme-main-gate", "stratholme-service-gate",
    "upper-blackrock-spire",
]

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


def fetch(url):
    r = subprocess.run(["curl", "-s", "-L", "--max-time", "60", url],
                       capture_output=True, timeout=90)
    return r.stdout.decode("utf-8", "replace")


def parse_loot(html):
    bosses = []
    sec_re = re.compile(r'<section id="([^"]+)" class="lb-boss[^"]*"[^>]*>')
    h2_re = re.compile(r'<h2[^>]*>(.*?)</h2>')
    item_re = re.compile(r'href="/zh-cn/item/(\d+)"')
    cnt_re = re.compile(r'掉落<small>(\d+)</small>')
    secs = list(sec_re.finditer(html))
    for m in secs:
        body = html[m.start():m.end() + 20000]
        body = body[:body.find("</section>")]
        h2 = h2_re.search(body)
        name = h2.group(1) if h2 else m.group(1)
        items = item_re.findall(body)
        cnt = cnt_re.search(body)
        bosses.append({"id": m.group(1), "name": name, "items": items,
                       "declared": int(cnt.group(1)) if cnt else None})
    return bosses


def parse_quests(html):
    """返回 {task_id: {'side': a/h/b, 'name': en, 'lvl': ...}}"""
    out = {}
    marks = []
    for m in re.finditer(r'<div class="dgx-side"([^>]*)>(.*?)<h3>(.*?)</h3>',
                         html, re.S):
        attrs, h3 = m.group(1), m.group(3)
        ds = re.search(r'data-side="([ah])"', attrs)
        label = ' '.join(re.sub(r'<[^>]+>', '', h3).split())
        if ds:
            side = ds.group(1)
        elif '双方' in label:
            side = 'b'
        elif '联盟' in label:
            side = 'a'
        elif '部落' in label:
            side = 'h'
        else:
            side = 'b'
        marks.append((m.start(), side, label))
    for q in re.finditer(r'<section class="dgx-quest" id="quest-(\d+)"([^>]*)>'
                         r'(.*?)</section>', html, re.S):
        qid = int(q.group(1))
        body = q.group(3)
        prev = [s for s in marks if s[0] < q.start()]
        side, label = (prev[-1][1], prev[-1][2]) if prev else ('b', '')
        nm = re.search(r'<h4[^>]*>(.*?)</h4>', body, re.S)
        name = ' '.join(re.sub(r'<[^>]+>', '', nm.group(1)).split()) if nm else ''
        lvl = re.search(r'<p>([^<]*)</p>', body)
        out[qid] = {"side": side, "name": name,
                    "lvl": (' '.join(lvl.group(1).split()) if lvl else ''),
                    "group": label}
    return out


def parse_ours_loot():
    src = open(r"D:/workspace/DungeonsForever/Core/Data/Data_DungeonLoot.lua",
               encoding="utf-8").read()
    dungeons = {}
    cur = None
    cur_boss = None
    dkg = re.compile(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{')
    boss_re = re.compile(r'^\s*\{\s*"((?:[^"\\]|\\.)*)",\s*"((?:[^"\\]|\\.)*)"')
    item_re = re.compile(r'^\s*\{\s*(\d+)')
    for line in src.splitlines():
        m = dkg.match(line)
        if m and 'ns.DungeonLoot' not in line:
            cur = m.group(1)
            dungeons[cur] = []
            continue
        if cur is None:
            continue
        mb = boss_re.match(line)
        if mb:
            cur_boss = {"en": mb.group(1), "zh": mb.group(2), "items": []}
            dungeons[cur].append(cur_boss)
            continue
        mi = item_re.match(line)
        if mi and cur_boss is not None:
            cur_boss["items"].append(int(mi.group(1)))
    return dungeons


def parse_ours_quests():
    src = open(r"D:/workspace/DungeonsForever/Core/Data/Data_DungeonQuests.lua",
               encoding="utf-8").read()
    out = {}
    cur = None
    dkg = re.compile(r'^\s*\["([a-z_0-9]+)"\]\s*=\s*\{')
    row_re = re.compile(
        r'^\s*\{\s*(\d+),\s*(nil|"([AH])")\s*,\s*(\d+)\s*,\s*([^,]+)')
    for line in src.splitlines():
        m = dkg.match(line)
        if m and 'ns.DungeonQuests' not in line:
            cur = m.group(1)
            out[cur] = {}
            continue
        if cur is None:
            continue
        mr = row_re.match(line)
        if mr:
            qid = int(mr.group(1))
            side = mr.group(3) if mr.group(3) else 'b'
            out[cur][qid] = {"side": side.lower(), "req": mr.group(4)}
    return out


def main():
    site_loot, site_quests = {}, {}
    for slug in SITE_DUNGEONS:
        html = fetch(f"https://foreverchanges.pro/zh-cn/dungeons/{slug}")
        if len(html) < 50000:
            print(f"!! {slug}: page too small {len(html)}", flush=True)
        site_loot[slug] = parse_loot(html)
        site_quests[slug] = parse_quests(html)
        print(f"ok {slug}: {len(site_loot[slug])} loot-boss / "
              f"{len(site_quests[slug])} quests", flush=True)
    json.dump(site_loot, open("_temp/fc_site_dumps.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(site_quests, open("_temp/fc_site_quests.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    ours_loot = parse_ours_loot()
    ours_quests = parse_ours_quests()
    json.dump(ours_loot, open("_temp/fc_ours_dumps.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(ours_quests, open("_temp/fc_ours_quests.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n===== 掉落对比 =====")
    loot_report = []
    tot = 0
    for slug in SITE_DUNGEONS:
        key = SITE2OURS.get(slug, slug.replace("-", "_"))
        s_all = set()
        for b in site_loot[slug]:
            s_all.update(int(i) for i in b["items"])
        o_all = set()
        for b in ours_loot.get(key, []):
            o_all.update(b["items"])
        missing = sorted(s_all - o_all)
        extra = sorted(o_all - s_all)
        loot_report.append({"site": slug, "ours": key,
                            "missing": missing, "extra": extra})
        flag = "  <<<" if (missing or extra) else ""
        print(f"{slug:32s} 站{len(s_all):4d} 我{len(o_all):4d} "
              f"缺{len(missing):3d} 多{len(extra):3d}{flag}")
        tot += len(missing)
    print(f"总缺失掉落: {tot}")
    json.dump(loot_report, open("_temp/fc_dungeon_diff.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n===== 任务对比 =====")
    q_report = []
    for slug in SITE_DUNGEONS:
        key = SITE2OURS.get(slug, slug.replace("-", "_"))
        s = site_quests[slug]
        o = ours_quests.get(key, {})
        miss = sorted(set(s) - set(o))
        extra = sorted(set(o) - set(s))
        mismatch = []
        for qid in sorted(set(s) & set(o)):
            if s[qid]["side"] != o[qid]["side"]:
                mismatch.append({"id": qid, "site": s[qid]["side"],
                                 "ours": o[qid]["side"],
                                 "name": s[qid]["name"],
                                 "group": s[qid]["group"]})
        q_report.append({"site": slug, "ours": key, "site_n": len(s),
                         "ours_n": len(o), "missing": miss, "extra": extra,
                         "side_mismatch": mismatch})
        if miss or extra or mismatch:
            print(f"{slug:32s} 站{len(s):3d} 我{len(o):3d} "
                  f"缺{miss} 多{extra} 阵营异{mismatch}")
    json.dump(q_report, open("_temp/fc_quest_diff.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

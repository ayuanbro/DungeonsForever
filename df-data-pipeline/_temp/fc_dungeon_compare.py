# -*- coding: utf-8 -*-
"""抓取 foreverchanges.pro 35 个五人本页面，与 Core/Data/Data_DungeonLoot.lua 对比掉落差距。"""
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
    r = subprocess.run(
        ["curl", "-s", "-L", "--max-time", "60", url],
        capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "replace")


def parse_page(html):
    bosses = []
    sec_re = re.compile(r'<section id="([^"]+)" class="lb-boss[^"]*"[^>]*>')
    h2_re = re.compile(r'<h2[^>]*>(.*?)</h2>')
    item_re = re.compile(r'href="/zh-cn/item/(\d+)"')
    cnt_re = re.compile(r'掉落<small>(\d+)</small>')
    secs = list(sec_re.finditer(html))
    for idx, m in enumerate(secs):
        body = html[m.start():m.end() + 20000]
        body = body[:body.find("</section>")]
        h2 = h2_re.search(body)
        name = h2.group(1) if h2 else m.group(1)
        items = item_re.findall(body)
        cnt = cnt_re.search(body)
        bosses.append({"id": m.group(1), "name": name, "items": items,
                       "declared": int(cnt.group(1)) if cnt else None})
    return bosses


def parse_ours():
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


def main():
    site = {}
    for slug in SITE_DUNGEONS:
        html = fetch(f"https://foreverchanges.pro/zh-cn/dungeons/{slug}")
        if len(html) < 50000:
            print(f"!! {slug}: page too small {len(html)}", flush=True)
        site[slug] = parse_page(html)
        print(f"ok {slug}: {len(site[slug])} bosses", flush=True)
    json.dump(site, open("_temp/fc_site_dumps.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    ours = parse_ours()
    json.dump(ours, open("_temp/fc_ours_dumps.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    report = []
    for slug in SITE_DUNGEONS:
        key = SITE2OURS.get(slug, slug.replace("-", "_"))
        sb = {b["id"]: b for b in site[slug]}
        ob = {b["zh"]: b for b in ours.get(key, [])}
        s_all, o_all = set(), set()
        for b in site[slug]:
            s_all.update(int(i) for i in b["items"])
        for b in ours.get(key, []):
            o_all.update(b["items"])
        missing = sorted(s_all - o_all)
        extra = sorted(o_all - s_all)
        report.append({
            "site": slug, "ours": key,
            "site_bosses": len(sb), "ours_bosses": len(ob),
            "site_items": len(s_all), "ours_items": len(o_all),
            "missing_in_ours": missing,
            "extra_in_ours": extra,
            "boss_missing": [b["id"] for b in site[slug]
                             if b["id"] not in {b2["id"] for b2 in site[slug]} and False],
        })
    json.dump(report, open("_temp/fc_dungeon_diff.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n===== 对比汇总 =====")
    tot_miss = 0
    for r in report:
        flag = "  <<<" if (r["missing_in_ours"] or r["extra_in_ours"]) else ""
        print(f"{r['site']:32s} 站{r['site_items']:4d} 我{r['ours_items']:4d} "
              f"缺{len(r['missing_in_ours']):3d} 多{len(r['extra_in_ours']):3d}"
              f" boss 站{r['site_bosses']} 我{r['ours_bosses']}{flag}")
        tot_miss += len(r["missing_in_ours"])
    print(f"\n总缺失条目: {tot_miss}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()

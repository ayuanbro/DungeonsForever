# -*- coding: utf-8 -*-
"""批量抓 Wowhead forever 的 *-dungeon-overview-location-rewards 攻略页。

输出：_ref_wowhead/wh_ov_<slug>.html；成功/失败清单写 _ov_fetch_report.json
"""
from curl_cffi import requests
import os, json, time, re

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_ref_wowhead")
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

# 已知 slug（达拉然页侧栏）+ 按我方 35 本猜的 slug（含备选）
CANDIDATES = [
    # 已确认
    "ragefire-chasm", "wailing-caverns", "the-deadmines", "shadowfang-keep",
    "blackfathom-deeps", "the-stockade", "gnomeregan",
    "razerfen-kraul", "razorfen-downs",
    "scarlet-monastery-graveyard", "scarlet-monastery-library",
    "scarlet-monastery-armory", "scarlet-monastery-cathedral",
    "excavation-site-wetlands", "city-of-dalaran", "hall-of-thanes", "ruins-of-lordaeron",
    # 猜测
    "uldaman", "zulfarrak", "zul-farrak", "maraudon", "sunken-temple",
    "scholomance", "blackrock-depths",
    "lower-blackrock-spire", "upper-blackrock-spire", "blackrock-spire",
    "dire-maul-east", "dire-maul-north", "dire-maul-west", "dire-maul",
    "stratholme-main-gate", "stratholme-service-gate", "stratholme",
    "the-drowned-city", "kroldok-stronghold", "alcaz-prison",
    "blackmaw-hold", "shapers-terrace",
]

SUF = "-dungeon-overview-location-rewards"


def main():
    report = {}
    for slug in CANDIDATES:
        fn = os.path.join(OUT, "wh_ov_%s.html" % slug)
        if os.path.exists(fn) and os.path.getsize(fn) > 20000:
            report[slug] = "cache"
            print("%-38s cache" % slug)
            continue
        url = "https://www.wowhead.com/forever/guide/%s%s" % (slug, SUF)
        try:
            r = requests.get(url, proxies=PROXIES, impersonate="chrome110", timeout=40)
            if r.status_code == 200 and "guide-content" in r.text:
                open(fn, "w", encoding="utf-8").write(r.text)
                report[slug] = "ok %d" % len(r.text)
                print("%-38s ok %d" % (slug, len(r.text)))
            else:
                report[slug] = "miss %s" % r.status_code
                print("%-38s miss %s" % (slug, r.status_code))
        except Exception as e:
            report[slug] = "FAIL %s" % e
            print("%-38s FAIL %s" % (slug, e))
        time.sleep(1.5)
    json.dump(report, open(os.path.join(HERE, "_ov_fetch_report.json"), "w"), indent=1)
    print("done ->", "_ov_fetch_report.json")


if __name__ == "__main__":
    main()

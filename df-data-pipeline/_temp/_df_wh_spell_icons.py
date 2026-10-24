# -*- coding: utf-8 -*-
"""抓 wowhead 法术图标 slug（法术页左上角那张贴图）。

输出：
  _temp/_wh_spell_icons.json = { str(spellid): "ability_warrior_cleave", … }

用途：Data_BossSkills 行第 4 位 = 图标 slug；实机客户端 GetSpellInfo 查不到
（无限服技能库不全 / 返回数字 iconID）时，MapUI 回落 `Interface/Icons/<slug>`。
"""
from curl_cffi import requests
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

ICON_PATS = [
    re.compile(r"images/wow/icons/(?:large|medium)/([\w-]+)\.jpg"),
    re.compile(r"data-icon-name=\"([\w-]+)\""),
    re.compile(r"\"icon\"\s*:\s*\"([\w-]+)\""),
]


def fetch(url):
    # CF 限流退避：15/25/35/45s 重试（与 _df_wh_names2.py 同口径）；网络异常也算一次失败
    for wait in (0, 15, 25, 35, 45):
        if wait:
            time.sleep(wait)
        try:
            r = requests.get(url, proxies=PROXIES, impersonate="chrome110", timeout=30)
        except Exception:
            continue
        if r.status_code == 200:
            return r.text
    return ""


def icon_slug(html):
    for pat in ICON_PATS:
        m = pat.search(html)
        if m:
            return m.group(1)
    return ""


def main():
    guide = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
    want = set()
    for v in guide.values():
        for b in v.values():
            want.update(int(x) for x in re.findall(r"«S(\d+)»", b["text"]))
            want.update(int(x) for x in (b.get("spells") or []))
    want = sorted(want)

    out_p = os.path.join(HERE, "_wh_spell_icons.json")
    icons = {}
    if os.path.exists(out_p):
        icons = json.load(open(out_p, encoding="utf-8"))
    todo = [i for i in want if not icons.get(str(i))]  # 空结果也要重抓
    print("法术图标待抓 %d / %d" % (len(todo), len(want)))
    for i in todo:
        # ★ classic 页没有永恒服自定义法术（2026-09-30 实锤：1293228 等只有 forever 区有）⇒ 空了回退 forever
        slug = icon_slug(fetch("https://www.wowhead.com/classic/spell=%d" % i))
        if not slug:
            slug = icon_slug(fetch("https://www.wowhead.com/forever/spell=%d" % i))
        icons[str(i)] = slug
        print("spell %6d  icon=%s" % (i, slug or "(空)"))
        time.sleep(0.4)
        json.dump(icons, open(out_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n_ok = sum(1 for v in icons.values() if v)
    print("完成：%d/%d 有 slug" % (n_ok, len(icons)))


if __name__ == "__main__":
    main()

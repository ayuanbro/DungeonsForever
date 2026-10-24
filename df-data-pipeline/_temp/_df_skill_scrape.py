# -*- coding: utf-8 -*-
"""抓 foreverchanges.pro 各副本页的「首领技能」（zh-CN / en / zh-TW 三种语言）。

站点结构（每个 boss 一段）：
  <section id="<slug>" class="lb-boss" …><header>…<h2 id="h-<slug>">名字</h2><p>16级</p></header>
    <div class="lb-fight"><ul>
      <li><img …/><div><p class="lb-ability"><strong>技能名</strong><span class="dj-flag" …></span></p>
          <p>说明</p></div></li> …
    </ul></div>
    <ul class="lb-rows">…掉落…</ul>
  </section>

三语页面**结构一致、boss 顺序一致** ⇒ 按下标对齐，键取英文页的英文名。
缓存：_ref/dg_<slug>.html(zh-CN) · _ref_en/…(en) · _ref_tw/…(zh-TW)；二次运行不再联网。

输出：_temp/_boss_skills_raw.json = { 副本id: { 英文boss名: { zhCN:[[n,d]…], zhTW:[…], enUS:[…] } } }
"""
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = "http://127.0.0.1:7897"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 与 _df_pin_scrape.py 同一张表：本插件 id → 站点 slug（27 个有客户端内地图的副本）
SLUG = {
    "ragefire_chasm": "ragefire-chasm",
    "wailing_caverns": "wailing-caverns",
    "the_deadmines": "the-deadmines",
    "shadowfang_keep": "shadowfang-keep",
    "blackfathom_deeps": "blackfathom-deeps",
    "the_stockade": "the-stockade",
    "gnomeregan": "gnomeregan",
    "razorfen_kraul": "razorfen-kraul",
    "razorfen_downs": "razorfen-downs",
    "sm_graveyard": "scarlet-monastery-graveyard",
    "sm_library": "scarlet-monastery-library",
    "sm_armory": "scarlet-monastery-armory",
    "sm_cathedral": "scarlet-monastery-cathedral",
    "uldaman": "uldaman",
    "zul_farrak": "zulfarrak",
    "maraudon": "maraudon",
    "sunken_temple": "sunken-temple",
    "blackrock_depths": "blackrock-depths",
    "dire_maul_east": "dire-maul-east",
    "dire_maul_north": "dire-maul-north",
    "dire_maul_west": "dire-maul-west",
    "lower_blackrock_spire": "lower-blackrock-spire",
    "upper_blackrock_spire": "upper-blackrock-spire",
    "scholomance": "scholomance",
    "stratholme_main": "stratholme-main-gate",
    "stratholme_service": "stratholme-service-gate",
    "city_of_dalaran": "city-of-dalaran",
    # 2026-09-30 晚：两个自制副本也有 lb-boss/lb-fight 技能段
    "hall_of_thanes": "hall-of-thanes",
    "ruins_of_lordaeron": "ruins-of-lordaeron",
}

# 语言 → (缓存目录, url 前缀)
LOC = {
    "zhCN": ("_ref", "zh-cn/"),
    "enUS": ("_ref_en", ""),
    "zhTW": ("_ref_tw", "zh-tw/"),
}

SEC = re.compile(r'<section id="[^"]+" class="lb-boss"[^>]*>(.*?)</section>', re.S)
H2 = re.compile(r'<h2[^>]*>(.*?)</h2>', re.S)
FIGHT = re.compile(r'class="lb-fight">(.*?)</ul></div>', re.S)
LI = re.compile(r'<li>(.*?)</li>', re.S)
STG = re.compile(r'<strong>(.*?)</strong>', re.S)
DESC = re.compile(r'</p>\s*<p>(.*?)</p>', re.S)
# 技能图标 slug（/icon/ability_warrior_cleave.jpg）——上游没有 spell id，
# 这个 slug 存下来用于运行时「按名反查后校验图标」，防同名玩家法术误配。
ICONS = re.compile(r'/icon/([A-Za-z0-9_\-]+)\.(?:jpg|png)', re.S)
TAGS = re.compile(r'<[^>]+>')
ENTS = [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
        ("&#x27;", "'"), ("&apos;", "'"), ("&nbsp;", " ")]


def unesc(s):
    for a, b in ENTS:
        s = s.replace(a, b)
    return TAGS.sub("", s).strip()


def fetch(loc, slug):
    sub, pre = LOC[loc]
    out = os.path.join(HERE, sub, "dg_%s.html" % slug)
    if os.path.exists(out) and os.path.getsize(out) > 20000:
        return open(out, encoding="utf-8", errors="replace").read()
    url = "https://foreverchanges.pro/%sdungeons/%s" % (pre, slug)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["curl", "-s", "-x", PROXY, "-A", UA, "-o", out, url], check=False)
    time.sleep(0.8)
    try:
        return open(out, encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


def parse(html):
    """→ [ (boss 名, [ (技能名, 说明, 图标slug), … ] ), … ]（保持页面顺序）"""
    out = []
    for m in SEC.finditer(html):
        body = m.group(1)
        nm = H2.search(body)
        name = unesc(nm.group(1)) if nm else ""
        ab = []
        f = FIGHT.search(body)
        if f:
            for li in LI.finditer(f.group(1)):
                s = STG.search(li.group(1))
                if not s:
                    continue
                d = DESC.search(li.group(1))
                ic = ICONS.search(li.group(1))
                ab.append([unesc(s.group(1)), unesc(d.group(1)) if d else "",
                           ic.group(1) if ic else ""])
        out.append((name, ab))
    return out


def main():
    res, miss = {}, []
    for did, slug in SLUG.items():
        by_loc = {}
        for loc in ("enUS", "zhCN", "zhTW"):
            html = fetch(loc, slug)
            if not html:
                miss.append("%s/%s" % (did, loc))
                continue
            by_loc[loc] = parse(html)
        en = by_loc.get("enUS") or []
        if not en:
            continue
        row = {}
        for i, (en_name, _ab) in enumerate(en):
            entry = {}
            for loc in ("zhCN", "zhTW", "enUS"):
                loc_list = by_loc.get(loc) or []
                if i < len(loc_list) and loc_list[i][1]:
                    entry[loc] = loc_list[i][1]
            if entry:
                row[en_name] = entry
        res[did] = row
        n = sum(len(v.get("zhCN", [])) for v in row.values())
        print("%-22s boss=%-3d 技能(zhCN)=%d" % (did, len(row), n))
    json.dump(res, open(os.path.join(HERE, "_boss_skills_raw.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    print("— 缺页:", miss or "无")
    print("— 落盘 _temp/_boss_skills_raw.json")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""专业训练师定位数据生成器。
数据源：icy-veins wow-forever 各专业页训练师表（/mappin mapID x y 已是 classic uiMapID）。
产物：Core/Data/Data_ProfTrainers.lua —— 单文件内嵌 zhCN/zhTW/enUS 三语名，无需覆盖层。
中文名策略：高置信度字典直译 + 缺失回退英文（字典可持续增补后重跑）。
"""
import html as htmllib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "Core", "Data", "Data_ProfTrainers.lua")
CACHE = os.path.join(HERE, "_icv")

PROFS = ["alchemy", "blacksmithing", "enchanting", "engineering", "herbalism",
         "inscription", "jewelcrafting", "leatherworking", "mining", "skinning",
         "tailoring", "cooking", "first-aid", "fishing"]

try:
    import opencc
    _cc = opencc.OpenCC("s2t")
    def s2t(s):
        return _cc.convert(s)
except Exception:
    def s2t(s):
        return s

RANK_ZH = {
    "Apprentice": "学徒", "Journeyman": "技工", "Expert": "专家",
    "Artisan": "工匠", "Master": "大师", "Grand Master": "宗师",
}

NAME_ZH = {
    "Betty Quin": "贝蒂·奎恩",
    "Annora": "安诺拉",
    "Kitta Firewind": "基塔·火风",
    "Lucan Cordell": "卢坎·科德尔",
    "Vanessa Sellers": "瓦妮莎·塞勒斯",
    "Hgarth": "加加斯",
    "Godan": "戈丹",
    "Jhag": "加格",
    "Vance": "万斯",
    "Alanna Raveneye": "阿兰娜·鸦眼",
    "Lalina Summermoon": "拉琳娜·夏月",
    "Mot Dawnstrider": "莫特·破晓者",
    "Teg Dawnstrider": "泰格·破晓者",
    "Malcomb Wynn": "马尔科姆·韦恩",
    "Lavinia Crowe": "拉维妮娅·克罗",
    "Nasalanna Windsinger": "娜萨拉娜·风歌",
    "Eaysaa Brightgust": "伊萨·明风",
    "Xylinnia Starshine": "希琳妮亚·星辉",
    "Taladan": "塔拉丹",
    "Gimble Thistlefuzz": "金布尔·刺球果",
    "Pa'zula": "帕祖拉",
    "Thonys Pillarstone": "索洛尼斯·支柱石",
}

ZONE_ZH = {
    "Stormwind City": "暴风城", "Ironforge": "铁炉堡", "Darnassus": "达纳苏斯",
    "Teldrassil": "泰达希尔", "Orgrimmar": "奥格瑞玛", "Undercity": "幽暗城",
    "Thunder Bluff": "雷霆崖", "Tirisfal Glades": "提瑞斯法林地",
    "Durotar": "杜隆塔尔", "Feralas": "菲拉斯", "Elwynn Forest": "艾尔文森林",
    "Alterac Mountains": "奥特兰克山脉", "Stonetalon Mountains": "石爪山脉",
    "Uldaman": "奥达曼", "Zephras Isle": "泽风岛", "Silvermoon City": "银月城",
    "Eversong Woods": "永歌森林", "Exodar": "埃索达", "Azuremyst Isle": "秘蓝岛",
    "Booty Bay": "藏宝海湾", "Ratchet": "棘齿城", "Gadgetzan": "加基森",
    "Everlook": "永望镇", "Thelsamar": "塞尔萨玛", "Aerie Peak": "鹰巢山",
    "Desolace": "凄凉之地", "Darkshore": "黑海岸", "Bloodhoof Village": "血蹄村",
    "Brill": "布瑞尔", "Sen'jin Village": "森金村", "Dalaran": "达拉然",
    "Feathermoon Stronghold": "羽月要塞", "Dustwallow Marsh": "尘泥沼泽",
    "Stranglethorn Vale": "荆棘谷", "Hillsbrad Foothills": "希尔斯布莱德丘陵",
    "Ashenvale": "灰谷", "Duskwood": "暮色森林", "Loch Modan": "洛克莫丹",
    "Mulgore": "莫高雷", "Barrens": "贫瘠之地", "Tanaris": "塔纳利斯",
    "Winterspring": "冬泉谷", "Searing Gorge": "灼热峡谷", "Badlands": "荒芜之地",
    "Swamp of Sorrows": "悲伤沼泽", "Dun Morogh": "丹莫罗", "Teldrassil": "泰达希尔",
}

MAP_FIX = {2991: 2521}

SUB_ZH = {
    "Mage Quarter": "法师区", "The Great Forge": "大锻炉",
    "Craftsmen's Terrace": "工匠区", "The Drag": "暗巷区",
    "The Apothecarium": "药剂师区", "Oracle Glade": "先知林地",
    "Shen'dar Village": "辛德村", "Valanaar": "瓦拉纳",
    "Undergloom": "幽光谷", "Thunder Bluff": "雷霆崖",
    "Tower of Azora": "阿佐拉之塔", "Sun Rock Retreat": "日石壁垒",
    "Feathermoon Stronghold": "羽月要塞", "Inside Uldaman": "奥达曼副本内",
    "Dalaran": "达拉然", "Cenarion Enclave": "塞纳里奥区",
    "The Valley of Spirits": "灵魂谷", "Spirit Rise": "灵魂高地",
    "Falcon Square": "猎鹰广场", "Trade District": "贸易区",
    "The War Quarter": "战争区", "The Magic Quarter": "魔法区",
    "Farstriders' Square": "游侠广场", "The Royal Exchange": "皇家交易区",
    "Forlorn Cavern": "幽暗洞窟", "Hall of Explorers": "探险者大厅",
    "Temple of the Moon": "月神殿", "The Exodar": "埃索达",
    "Goldshire": "闪金镇", "Kharanos": "卡拉诺斯", "Dolanaar": "多兰纳尔",
    "Aldrassil": "奥达西尔", "Razor Hill": "剃刀岭", "Bloodhoof Village": "血蹄村",
    "Brill": "布瑞尔", "Splintertree Post": "碎木岗哨",
    "Sun Rock Retreat": "日石壁垒", "Camp Taurajo": "陶拉祖营地",
    "Freewind Post": "自由风哨站", "Shadowprey Village": "暗影猎手村",
    "Booty Bay": "藏宝海湾", "Ratchet": "棘齿城", "Gadgetzan": "加基森",
    "Everlook": "永望镇", "Light's Hope Chapel": "圣光之愿礼拜堂",
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def fetch(slug):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, slug + ".html")
    if os.path.exists(p) and os.path.getsize(p) > 10000:
        return open(p, encoding="utf-8", errors="replace").read()
    url = "https://www.icy-veins.com/wow-forever/%s?area=area_1" % slug
    r = subprocess.run(["curl", "-s", "--max-time", "40", "-x",
                        "http://127.0.0.1:7897", "-A", UA, url, "-o", p],
                       capture_output=True)
    if not os.path.exists(p) or os.path.getsize(p) < 10000:
        raise RuntimeError("fetch fail: %s" % slug)
    return open(p, encoding="utf-8", errors="replace").read()


def strip(s):
    s = re.sub(r"<[^>]+>", "", s)
    return htmllib.unescape(s).strip()


def parse_ranks(seg, prof_title_word):
    out = []
    m = re.search(r"<h2[^>]*>\s*%s Trainers" % prof_title_word, seg)
    if not m:
        m = re.search(r"<h2[^>]*>[^<]*Trainers in WoW Forever", seg)
    if not m:
        return None, None
    end = seg.find("</section>", m.end())
    nxt = seg.find("<h2", m.end())
    if end < 0 or (0 <= nxt < end):
        end = nxt if nxt > 0 else len(seg)
    sec = seg[m.start():end if end > 0 else len(seg)]
    km = re.search(r"<table>.*?</table>", sec, re.S)
    ranks = []
    if km:
        for tr in re.findall(r"<tr>(.*?)</tr>", km.group(0), re.S):
            tds = re.findall(r"<td>(.*?)</td>", tr, re.S)
            if len(tds) >= 4:
                name = strip(tds[0])
                if name in RANK_ZH:
                    def num(s):
                        s = strip(s)
                        try:
                            return float(s)
                        except ValueError:
                            return None
                    ranks.append({"en": name, "cap": num(tds[1]),
                                  "sk": num(tds[2]), "lv": num(tds[3])})
    trs = []
    pos = 0
    while True:
        hm = re.search(r'<h3[^>]*>([\d\-]+):\s*(Alliance|Horde)</h3>', sec[pos:])
        if not hm:
            break
        rng, fac = hm.group(1), "A" if hm.group(2) == "Alliance" else "H"
        chunk = sec[pos + hm.end():]
        stop = re.search(r"<h3", chunk)
        chunk = chunk[:stop.start()] if stop else chunk
        for tr in re.findall(r"<tr>(.*?)</tr>", chunk, re.S):
            tds = re.findall(r"<td>(.*?)</td>", tr, re.S)
            if len(tds) < 3:
                continue
            pm = re.search(r"/mappin (\d+) ([\d.]+) ([\d.]+)", tds[2])
            if not pm:
                continue
            loc = strip(tds[1])
            note = ""
            nm = re.search(r"\(([^)]+)\)", loc)
            if nm:
                note = nm.group(1)
                loc = (loc[:nm.start()] + loc[nm.end():]).strip(" ,")
            if "," in loc:
                sub, zone = loc.rsplit(",", 1)
                sub, zone = sub.strip(), zone.strip()
            else:
                sub, zone = None, loc.strip()
            trs.append({"rng": rng, "fac": fac, "en": strip(tds[0]),
                        "sub": sub, "zone": zone, "note": note,
                        "map": int(pm.group(1)),
                        "x": float(pm.group(2)), "y": float(pm.group(3))})
        pos += hm.end()
    return ranks, trs


def zh_of(en, dic):
    base = re.sub(r"\s*\([^)]*\)\s*$", "", en).strip()
    return dic.get(en) or dic.get(base) or WOWHEAD_ZH.get(en) or WOWHEAD_ZH.get(base) or base


def _load_wowhead_zh():
    npcid_p = os.path.join(HERE, "_trainers_npcid.json")
    zh_p = os.path.join(HERE, "_trainers_zh.json")
    try:
        npcid = json.load(open(npcid_p, encoding="utf-8"))
        zhdb = json.load(open(zh_p, encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for en, eid in npcid.items():
        z = zhdb.get(str(eid))
        if z:
            out[en] = z
    return out


WOWHEAD_ZH = _load_wowhead_zh()


def emit_lua(data):
    L = []
    L.append("local _, ns = ...")
    L.append("")
    L.append("ns.ProfTrainers = {")
    for slug in PROFS:
        d = data.get(slug)
        if not d:
            continue
        L.append('    ["%s"] = {' % slug)
        L.append("        ranks = {")
        for rk in d["ranks"]:
            zh = RANK_ZH.get(rk["en"], rk["en"])
            L.append('            { en = "%s", zh = "%s", tw = "%s", cap = %s, sk = %s, lv = %s },' % (
                rk["en"], zh, s2t(zh),
                ("%g" % rk["cap"]) if rk["cap"] is not None else "nil",
                ("%g" % rk["sk"]) if rk["sk"] is not None else "nil",
                ("%g" % rk["lv"]) if rk["lv"] is not None else "nil"))
        L.append("        },")
        L.append("        list = {")
        for t in d["list"]:
            nz = zh_of(t["en"], NAME_ZH)
            zz = zh_of(t["zone"], ZONE_ZH)
            locz = zz
            loct = s2t(locz)
            note = t["note"]
            loc_en = t["zone"]
            if note:
                loc_en = loc_en + " (" + note + ")"
            L.append('            { rng = "%s", fac = "%s", map = %d, x = %g, y = %g, '
                     'en = "%s", zh = "%s", tw = "%s", '
                     'loc_en = %s, loc_zh = %s, loc_tw = %s },' % (
                         t["rng"], t["fac"], MAP_FIX.get(t["map"], t["map"]), t["x"], t["y"],
                         t["en"].replace('"', '\\"'), nz, s2t(nz),
                         '"%s"' % loc_en.replace('"', '\\"'),
                         '"%s"' % locz.replace('"', '\\"'),
                         '"%s"' % loct.replace('"', '\\"')))
        L.append("        },")
        L.append("    },")
    L.append("}")
    return "\n".join(L)


HEAD = ''


def main():
    data = {}
    for slug in PROFS:
        h = fetch(slug)
        word = {"first-aid": "First Aid"}.get(
            slug, slug.replace("-", " ").title().replace("And", "and"))
        seg = h
        ranks, trs = parse_ranks(seg, word)
        if not trs:
            print("%-15s 无训练师表" % slug)
            continue
        rng_rank = {}
        for i, rk in enumerate(ranks or []):
            lo = None
            prev = ranks[i - 1]["cap"] + 1 if i > 0 and ranks[i - 1]["cap"] else 1
            lo = prev if rk["cap"] else None
            rng_rank[rk["en"]] = rk
        data[slug] = {"ranks": ranks or [], "list": trs}
        print("%-15s ranks=%d trainers=%d" % (slug, len(ranks or []), len(trs)))
    body = emit_lua(data)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(HEAD + body + "\n")
    print("written:", OUT)


if __name__ == "__main__":
    main()

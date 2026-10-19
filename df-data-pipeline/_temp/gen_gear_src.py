# -*- coding: utf-8 -*-
"""装备库来源补缺生成器（GQF 全家桶 + PvP 套装表 + Lootified + 世界掉落等级段）
用法：
  python gen_gear_src.py --check   只算差异
  python gen_gear_src.py --apply   把 src 补丁 + GearWDLv + GearSrcQ 写进
                                   Core/Data/{,zhTW/,enUS/}Data_Gear.lua
可重复执行：先按 _temp/_gqf_applied.json 记录的 id 摘除上轮条目再重插。
第三方译名缓存：_temp/_gqf_name_cache.json（_gqf_fetch_names.py 产出）。
区域名映射：_temp/_wago_AreaTable_{en,zh}.csv（wago.tools 1.60.1.70338）。
"""
import csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = sys.executable

KIND_ZH = {
    "boss_drop": "首领掉落", "vendor": "商人", "quest_reward": "任务奖励",
    "world_drop": "世界掉落", "rare_npc": "稀有掉落", "raid_trash": "小怪掉落",
    "object_drop": "物件", "container": "容器", "fishing": "钓鱼",
    "special": "特殊获取", "mail": "邮件", "profession": "制造",
    "seasonal_quest": "任务奖励", "boss_chest": "首领掉落",
}
KIND_EN = {
    "boss_drop": "Boss drop", "vendor": "Vendor", "world_drop": "World drop",
    "rare_npc": "Rare spawn", "raid_trash": "Trash mob", "object_drop": "Object",
    "container": "Container", "fishing": "Fishing", "special": "Special",
    "mail": "Mail", "profession": "Crafted",
}
CC = None
def s2t(s):
    global CC
    if CC is None:
        try:
            from opencc import OpenCC
            CC = OpenCC("s2t")
        except Exception:
            CC = False
    return CC.convert(s) if CC else s

def load_lua(path, holder, varargs=False):
    from lupa import lua51
    L = lua51.LuaRuntime()
    lt = lambda v: L.eval('type')(v)
    src = open(path, 'rb').read().decode('utf-8', 'replace')
    t = L.table(); L.globals()[holder] = t
    f = L.eval("function(src,name) local f,err=loadstring(src,name) "
               "if not f then error(err) end return f end")(
        src, os.path.basename(path))
    if varargs:
        f("addon", t)
    else:
        f("addon", t)
    return L, lt

def gqf_facts(L, lt):
    GQ = L.globals().GearQuest
    out = {}
    for fk in [str(k) for k in GQ.Data.keys() if str(k).endswith('Facts')]:
        tb = GQ.Data[fk]
        for k in tb.keys():
            v = tb[k]
            if lt(v) == 'table' and v['sourceType'] is not None \
                    and str(v['sourceType']) != 'unsourced':
                out.setdefault(int(k), v)
    return out

def main():
    mode = "--apply" if "--apply" in sys.argv else "--check"
    # ---------- 我方装备库 ----------
    L1, lt1 = load_lua(os.path.join(ROOT, 'Core/Data/Data_Gear.lua'), 'NSG')
    NSG = L1.globals().NSG; NSG.EnsureGearData()
    G = NSG.GearData
    src = G['src']
    have = set(int(k) for k in src.keys())
    names, missing = {}, set()
    for row in G['items'].values():
        iid = int(row[1]); names[iid] = str(row[2])
        if iid not in have:
            missing.add(iid)
    applied_p = os.path.join(HERE, '_gqf_applied.json')
    prev_applied = []
    if os.path.exists(applied_p):
        try:
            prev_applied = json.load(open(applied_p, encoding='utf-8'))["src"]
        except Exception:
            prev_applied = []
    missing |= set(prev_applied)

    # ---------- 区域映射（wago AreaTable） ----------
    zone = {}
    zarea = {}
    p_en = os.path.join(HERE, '_wago_AreaTable_en.csv')
    p_zh = os.path.join(HERE, '_wago_AreaTable_zh.csv')
    if os.path.exists(p_en) and os.path.exists(p_zh):
        en = {r['AreaName_lang']: r['ID']
              for r in csv.DictReader(open(p_en, encoding='utf-8'))
              if r['AreaName_lang']}
        zh = {r['ID']: r['AreaName_lang']
              for r in csv.DictReader(open(p_zh, encoding='utf-8'))}
        zone = {k: zh.get(v, "") for k, v in en.items()}
        zarea = {k: int(v) for k, v in en.items() if str(v).isdigit()}
    else:
        print("⚠ 缺 AreaTable csv，区域退化为英文")

    # ---------- GQF ----------
    L2, lt2 = load_lua(
        r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/"
        r"GearQuestForever/Data.lua", 'GearQuest')
    base = (r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns")
    import glob
    for d in sorted(glob.glob(os.path.join(base, 'GearQuestForever_*'))):
        for p in sorted(glob.glob(os.path.join(d, 'Data.*.generated.lua'))):
            s2 = open(p, 'rb').read().decode('utf-8', 'replace')
            f = L2.eval("function(src,name) local f,err=loadstring(src,name) "
                        "if not f then error(err) end return f end")(
                s2, os.path.basename(p))
            f("addon", L2.globals().GearQuest)
    facts = gqf_facts(L2, lt2)

    qitem, qlv_db, qnpc, qobj, nspawn, ospawn, qrace_db = \
        {}, {}, {}, {}, {}, {}, {}
    try:
        qd = json.load(open(os.path.join(HERE, 'questie', 'questie_forever.json'),
                            encoding='utf-8'))
        qitem = {int(k): v for k, v in qd["item_rewards"].items()}
        qlv_db = {int(k): int(v) for k, v in qd["quest_reqLevel"].items()}
        qnpc = {int(k): int(v) for k, v in qd["quest_npc"].items()}
        qobj = {int(k): int(v) for k, v in qd["quest_obj"].items()}
        qrace_db = {int(k): int(v) for k, v in qd["quest_races"].items()}
        nspawn = {int(k): {int(z): xy for z, xy in v.items()}
                  for k, v in qd["npc_spawns"].items()}
        ospawn = {int(k): {int(z): xy for z, xy in v.items()}
                  for k, v in qd["obj_spawns"].items()}
    except Exception as _qe:
        print("⚠ QuestieDB 提取件缺失:", _qe)

    # ---------- 译名缓存 ----------
    cache = {"npcs": {}, "quests": {}}
    pc = os.path.join(HERE, '_gqf_name_cache.json')
    if os.path.exists(pc):
        try:
            cache = json.load(open(pc, encoding='utf-8'))
        except Exception:
            pass

    # ---------- 任务地图定位（areaID→mapID + wowhead 坐标） ----------
    amap = {}
    try:
        LAM, _ = load_lua(os.path.join(ROOT, 'Core/Data/Data_AreaMap.lua'),
                          'NSAM')
        amap = {int(k): int(v)
                for k, v in LAM.globals().NSAM.AreaMap.items()}
    except Exception:
        pass
    qcoords = {}
    pco = os.path.join(HERE, '_gqf_quest_coords.json')
    if os.path.exists(pco):
        try:
            qcoords = json.load(open(pco, encoding='utf-8'))
        except Exception:
            qcoords = {}

    # ---------- 我方 boss en→zh 与副本 slug→zh ----------
    L3, lt3 = load_lua(os.path.join(ROOT, 'Core/Data/Data_DungeonLoot.lua'),
                       'NSL')
    ours = L1.globals().NSL if False else L3.globals().NSL
    boss_zh = {}
    for slug in ours.DungeonLoot.keys():
        for s in ours.DungeonLoot[slug].values():
            en, zhb = str(s[1]), str(s[2])
            if en and zhb:
                boss_zh.setdefault(en, zhb)
    dung_zh = {}
    try:
        L4, _ = load_lua(os.path.join(ROOT, 'Core/Data/Data_Dungeons.lua'),
                         'NSD4')
        DD = L4.globals().NSD4.DungeonData
        if lt3(DD) == 'table' and lt3(DD.dungeons) == 'table':
            for d in DD.dungeons.values():
                dung_zh[str(d.id)] = str(d.name)
    except Exception:
        pass

    # ---------- Lootified locale 离线译名（name EN→zh） ----------
    loc_zh = {}
    try:
        LL, llt = load_lua(
            r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/"
            r"Lootified/Data/Locale_zhCN.lua", 'NSLJ')
        LT = LL.globals().NSLJ.Locales.zhCN()
        nm = LT['name']
        if llt(nm) == 'table':
            for k, v in nm.items():
                loc_zh[str(k)] = str(v)
    except Exception:
        pass

    # ---------- 组装补丁 ----------
    newsrc = {}   # id -> {"zh": "k|p", "en": "k|p"}
    srcq = {}     # id -> questID
    sqlv = {}     # id -> 任务接取需求等级
    qmark = {}    # questID -> zone EN 名
    gqf_ids = set()

    def place_zh(v, allow_npc=True):
        segs = []
        z = zone.get(str(v['zone']) if v['zone'] is not None else "", "")
        if z:
            segs.append(z)
        if allow_npc and v['npc'] is not None:
            en = str(v['npc'])
            nz = (boss_zh.get(en) or loc_zh.get(en)
                  or (cache["npcs"].get(en) or {}).get("zh"))
            if nz:
                segs.append(nz)
        return "·".join(segs)

    def place_en(v, allow_npc=True):
        segs = []
        if v['zone'] is not None:
            segs.append(str(v['zone']))
        if allow_npc and v['npc'] is not None:
            en = str(v['npc'])
            nz = (boss_zh.get(en) or loc_zh.get(en)
                  or (cache["npcs"].get(en) or {}).get("zh"))
            segs.append(nz or en)
        return " - ".join(segs) if segs else "Classic"

    for i in sorted(missing):
        v = facts.get(i)
        if v is None:
            continue
        st = str(v['sourceType'])
        gqf_ids.add(i)
        if st == "quest_reward" or st == "seasonal_quest":
            qn = str(v['questName']) if v['questName'] is not None else None
            qz = None
            if qn:
                qz = (cache["quests"].get(qn) or {}).get("zh")
                if qz and qz.startswith('[') and qz.endswith(']'):
                    qz = qn
                qid = (cache["quests"].get(qn) or {}).get("id")
                if qid:
                    srcq[i] = qid
                if v['reqLevel'] is not None and int(v['reqLevel']) > 0:
                    sqlv[i] = int(v['reqLevel'])
            pz = qz or place_zh(v, allow_npc=False) or ""
            pe = ("Quest: " + qn) if qn else "Quest reward"
            pe = pe + "|" + (str(v['zone']) if v['zone'] is not None
                             else "")
            if qid and v['zone'] is not None:
                qmark[str(qid)] = str(v['zone'])
            newsrc[i] = {"zh": "任务奖励|" + pz, "en": pe}
        else:
            kz = KIND_ZH.get(st, st)
            ke = KIND_EN.get(st, st)
            npcs_ok = st not in ("object_drop", "container")
            pz = place_zh(v, npcs_ok) or ""
            pe = place_en(v, npcs_ok)
            if st == "profession":
                prof = str(v['profession']) if v['profession'] is not None else ""
                pz = {"Tailoring": "裁缝", "Blacksmithing": "锻造",
                      "Leatherworking": "制皮", "Engineering": "工程学",
                      "Alchemy": "炼金"}.get(prof, prof or "制造")
                pe = prof or "Crafted"
            newsrc[i] = {"zh": kz + "|" + pz, "en": ke + "|" + pe}

    qfix = {}
    for k, v in src.items():
        s = str(v)
        m = re.match(r"任务：.*\|.*，(\d+)级起$", s)
        if m:
            qfix[int(k)] = int(m.group(1))
            continue
        m = re.match(r"任务奖励\|.*，(\d+)级起$", s)
        if m:
            qfix[int(k)] = int(m.group(1))
            continue
        m = re.match(r"任务：.*\|(\d+)级起$", s)
        if m:
            qfix[int(k)] = int(m.group(1))
            continue
        m = re.match(r"任务奖励\|(\d+)级起$", s)
        if m:
            qfix[int(k)] = int(m.group(1))
    qn0, qv0 = len(srcq), len(sqlv)
    for i in sorted(have):
        if i in srcq:
            continue
        cur = str(src[i]) if i in src else ""
        if not cur.startswith("任务奖励") and i not in qfix:
            continue
        qlist = qitem.get(i)
        if qlist:
            qid = min(qlist, key=lambda q_: (qlv_db.get(q_, 999), q_))
            srcq[i] = qid
            if qlv_db.get(qid, 0) > 0:
                sqlv.setdefault(i, qlv_db[qid])
        if i in qfix:
            sqlv.setdefault(i, qfix[i])
    print("QuestieDB 补任务 ID %d，接取等级 %d" % (len(srcq) - qn0, len(sqlv) - qv0))

    # PvP 套装表
    def deep_ids(v, out, depth=0):
        if depth > 6:
            return
        if isinstance(v, (int, float)):
            x = int(v)
            if 1000 < x < 999999:
                out.add(x)
        elif lt1(v) == 'table':
            for x in v.values():
                deep_ids(x, out, depth + 1)
    pvp = set()
    L5, lt5 = load_lua(os.path.join(ROOT, 'Core/Data/Data_PvPSets.lua'), 'NZP')
    def deep5(v, out, depth=0):
        if depth > 6:
            return
        if isinstance(v, (int, float)):
            x = int(v)
            if 1000 < x < 999999:
                out.add(x)
        elif lt5(v) == 'table':
            for x in v.values():
                deep5(x, out, depth + 1)
    deep5(L5.globals().NZP, pvp)
    for i in sorted((missing & pvp) - gqf_ids):
        gqf_ids.add(i)
        newsrc[i] = {"zh": "商人|PvP 军需官", "en": "Vendor|PvP vendors"}

    # Lootified（去掉 GQF/PvP 已覆盖的）
    L6, lt6 = load_lua(
        r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/"
        r"Lootified/Data/Instances.lua", 'NLJ')
    inst = L6.globals().NLJ.Data.Instances
    loot_map = {}
    for I in inst.values():
        dzh = dung_zh.get(str(I['key']), "")
        for b in I['bosses'].values():
            ben, bzh = str(b['name']), boss_zh.get(str(b['name']))
            for it in b['loot'].values():
                loot_map[int(it)] = (dzh, ben, bzh)
    L7, _ = load_lua(
        r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns/"
        r"Lootified/Data/WorldDrops.lua", 'NLJ2')
    wd = L7.globals().NLJ2.Data.WorldDrops
    lv_from_range, npc_field = {}, {}
    for k in wd.keys():
        p = str(wd[k]).split('|')
        iid = int(k)
        if len(p) >= 7 and p[4] and p[5]:
            lv_from_range[iid] = (int(p[4]), int(p[5]))
        elif len(p) >= 4 and p[3].strip():
            npc_field[iid] = p[3]
    wm = L7.globals().NLJ2.Data.WorldMobs
    def npc_lv(field):
        los, his = [], []
        for tok in field.split(';'):
            head = tok.split(':')[0]
            if not head.isdigit():
                continue
            m = wm[int(head)]
            if m is not None:
                los.append(int(m[2])); his.append(int(m[3]))
        return (min(los), max(his)) if los else None

    for i in sorted(missing - gqf_ids):
        t = loot_map.get(i)
        if t:
            dzh, ben, bzh = t
            pz = "·".join(x for x in (dzh, bzh or ben) if x) or ben
            newsrc[i] = {"zh": "首领掉落|" + pz, "en": "Boss drop|" + ben}
            gqf_ids.add(i)
    for i in sorted(missing - gqf_ids):
        if i in npc_field:
            r = npc_lv(npc_field[i])
            if r:
                newsrc[i] = {"zh": "怪物掉落",
                             "en": "Mob drop"}
                lv_from_range.setdefault(i, r)
                gqf_ids.add(i)

    # ---------- 世界掉落等级段（只动现有 世界掉落 条目） ----------
    wdlv = {}
    for i in have:
        cur = str(src[i])
        if not cur.startswith("世界掉落"):
            continue
        if i in lv_from_range:
            wdlv[i] = lv_from_range[i]
        elif i in npc_field:
            r = npc_lv(npc_field[i])
            if r:
                wdlv[i] = r

    # ---------- 汇总 ----------
    zh_only_src = {i: newsrc[i]["zh"] for i in newsrc}
    print("新来源 %d（GQF %d + PvP %d + Lootified %d）"
          % (len(newsrc), len([i for i in newsrc if i in facts]),
             len([i for i in newsrc if i not in facts and i in pvp]),
             len([i for i in newsrc if i not in facts and i not in pvp])))
    nocache = [i for i in newsrc if "|" not in newsrc[i]["zh"]
               or newsrc[i]["zh"].endswith("|")]

    # ---------- 任务地图表 ----------
    qmap = {}
    for qid, zen in qmark.items():
        c = qcoords.get(qid)
        mid = None
        if c and c.get("area") in amap:
            mid = amap[c["area"]]
            if mid:
                qmap[qid] = [mid, c["x"], c["y"]]
        if mid is None:
            aid = zarea.get(zen)
            if aid and aid in amap and amap[aid]:
                qmap[qid] = [amap[aid]]
    for i, qid in sorted(srcq.items()):
        if qid in qmap:
            continue
        loc = None
        npc = qnpc.get(qid)
        if npc and npc in nspawn:
            loc = nspawn[npc]
        else:
            obj = qobj.get(qid)
            if obj and obj in ospawn:
                loc = ospawn[obj]
        if not loc:
            continue
        for z, xy in sorted(loc.items()):
            mid = amap.get(z)
            if mid:
                qmap[qid] = [mid, xy[0], xy[1]]
                break

    qrace = {}
    for qid in set(srcq.values()):
        low = qrace_db.get(qid, 0) & 0xFFFFFFFF
        if low == 77:
            qrace[qid] = "a"
        elif low == 178:
            qrace[qid] = "h"

    print("世界掉落等级段 %d；任务 ID %d；任务等级 %d；任务地图 %d；阵营任务 a%d/h%d"
          % (len(wdlv), len(srcq), len(sqlv), len(qmap),
             sum(1 for v in qrace.values() if v == "a"),
             sum(1 for v in qrace.values() if v == "h")))
    if mode == "--check":
        return

    # ---------- 写三个文件 ----------
    for v in newsrc.values():
        z = v["zh"].replace("（经典旧世）", "")
        if z.endswith("|经典旧世"):
            z = z[:-len("|经典旧世")]
        v["zh"] = z
        e = v["en"].replace(", in Classic", "").replace(" (Classic)", "")
        if e.endswith("|Classic"):
            e = e[:-len("|Classic")]
        v["en"] = e
    applied = {"src": prev_applied, "wdlv": True, "srcq": True}

    targets = [
        (os.path.join(ROOT, 'Core/Data/Data_Gear.lua'), 'zh', False),
        (os.path.join(ROOT, 'Core/Data/zhTW/Data_Gear.lua'), 'tzh', False),
        (os.path.join(ROOT, 'Core/Data/enUS/Data_Gear.lua'), 'en', True),
    ]
    for path, lang, is_en in targets:
        raw = open(path, 'rb').read()
        nl = '\r\n' if b'\r\n' in raw else '\n'
        txt = raw.decode('utf-8')
        lines = txt.split('\n')
        # 摘除上轮（按 id 精确匹配行首 [id]="..." 形态的单条目行）
        if applied["src"]:
            drop = set(applied["src"])
            pat = re.compile(r'^\s*\[(\d+)\]=')
            lines = [ln for ln in lines
                     if not (pat.match(ln)
                             and int(pat.match(ln).group(1)) in drop)]
        lines = [ln for ln in lines
                 if not ln.startswith("ns.GearWDLv =")
                 and not ln.startswith("ns.GearSrcQ =")
                 and not ln.startswith("ns.GearSrcQLv =")
                 and not ln.startswith("ns.GearQuestMap =")
                 and not ln.startswith("ns.GearQuestRace =")]
        # 定位 src 块：从 "  src = {" 起找下一个 "  }," 收口行
        si = next(i for i, ln in enumerate(lines)
                  if ln.startswith("  src = {"))
        ei = next(i for i in range(si + 1, len(lines))
                  if lines[i].startswith("  },"))
        key = "en" if is_en else "zh"
        rx_clean = {
            "zh": re.compile(r'（经典旧世）|\|经典旧世(?=")'),
            "tzh": re.compile(r'（經典舊世）|\|經典舊世(?=")'),
            "en": re.compile(r', in Classic| \(Classic\)'
                             r'|\|In Classic(?=")|\|Classic(?=")')}[lang]
        rx_qsrc = {
            "zh": [
                (re.compile(r'"任务：[^|"]*\|([^"]*)，(\d+)级起"'),
                 r'"任务奖励|\1"'),
                (re.compile(r'"任务奖励\|([^"]*)，(\d+)级起"'), r'"任务奖励|\1"'),
                (re.compile(r'"任务：[^|"]*\|\d+级起"'), r'"任务奖励"'),
                (re.compile(r'"任务奖励\|\d+级起"'), r'"任务奖励"'),
            ],
            "tzh": [
                (re.compile(r'"任務：[^|"]*\|([^"]*)，(\d+)級起"'),
                 r'"任務獎勵|\1"'),
                (re.compile(r'"任務獎勵\|([^"]*)，(\d+)級起"'), r'"任務獎勵|\1"'),
                (re.compile(r'"任務：[^|"]*\|\d+級起"'), r'"任務獎勵"'),
                (re.compile(r'"任務獎勵\|\d+級起"'), r'"任務獎勵"'),
            ],
            "en": [
                (re.compile(r'"Quest: [^|"]*\|([^"]*), from level (\d+)"'),
                 r'"Quest reward|\1"'),
                (re.compile(r'"Quest reward\|([^"]*), from level (\d+)"'),
                 r'"Quest reward|\1"'),
                (re.compile(r'"Quest: [^|"]*\|from level \d+"'),
                 r'"Quest reward"'),
                (re.compile(r'"Quest reward\|from level \d+"'),
                 r'"Quest reward"'),
            ],
        }[lang]
        for j in range(si, ei):
            before = lines[j]
            ln2 = rx_clean.sub('', lines[j])
            for _rx, _rp in rx_qsrc:
                ln2 = _rx.sub(_rp, ln2)
            if lang == 'zh' and '251485' in before:
                print("调试251485 命中A:", bool(rx_qsrc[0][0].search(before)),
                      "命中B:", bool(rx_qsrc[1][0].search(before)),
                      "changed:", ln2 != before)
            if ln2 != lines[j]:
                lines[j] = ln2
        _qcnt = sum(1 for ln in lines if '级起"' in ln or '級起"' in ln
                    or 'from level' in ln)
        print("调试: 旧格式残留行", _qcnt, "lang=", lang)
        for _ln in lines:
            k = _ln.find("级起")
            if k < 0:
                k = _ln.find("級起")
            if k < 0 and "from level" in _ln:
                k = _ln.find("from level")
            if k >= 0:
                print("调试: 残留上下文", repr(_ln[max(0, k-60):k+12]))
        ins = []
        for i in sorted(newsrc):
            v = newsrc[i][key]
            if lang == 'tzh':
                v = s2t(v)
            ins.append('    [%d]="%s",' % (i, v.replace('"', '\\"')))
        lines = lines[:ei] + ins + lines[ei:]
        parts = ["[%d]={%d,%d}" % (i, wdlv[i][0], wdlv[i][1])
                 for i in sorted(wdlv)]
        lines = insert_before_return(
            lines, "ns.GearWDLv = { " + ", ".join(parts) + " }")
        qparts = ["[%d]=%d" % (i, srcq[i]) for i in sorted(srcq)]
        lines = insert_before_return(
            lines, "ns.GearSrcQ = { " + ", ".join(qparts) + " }")
        lparts = ["[%d]=%d" % (i, sqlv[i]) for i in sorted(sqlv)]
        lines = insert_before_return(
            lines, "ns.GearSrcQLv = { " + ", ".join(lparts) + " }")
        mparts = []
        for q in sorted(qmap, key=int):
            loc = qmap[q]
            if len(loc) == 3:
                mparts.append("[%s]={%d,%.1f,%.1f}" % (q, loc[0],
                                                       loc[1], loc[2]))
            else:
                mparts.append("[%s]={%d}" % (q, loc[0]))
        lines = insert_before_return(
            lines, "ns.GearQuestMap = { " + ", ".join(mparts) + " }")
        rparts = ['[%d]="%s"' % (q, qrace[q])
                  for q in sorted(qrace, key=int)]
        lines = insert_before_return(
            lines, "ns.GearQuestRace = { " + ", ".join(rparts) + " }")
        open(path, 'wb').write('\n'.join(lines).encode('utf-8'))
        print("已写", path)
    json.dump({"src": sorted(newsrc), "wdlv": True, "srcq": True},
              open(applied_p, 'w', encoding='utf-8'))
    print("applied 记录 ->", applied_p)

def insert_before_return(lines, newline):
    for idx, ln in enumerate(lines):
        if ln.strip() == "return ns.GearData":
            return lines[:idx] + [newline] + lines[idx:]
    raise SystemExit("return ns.GearData 未定位")

if __name__ == "__main__":
    main()

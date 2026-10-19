# -*- coding: utf-8 -*-
"""GQF 装备来源补充 · 离线译名解析（零网络版）
数据源全部来自本地 Lootified 插件文件：
  Data/Quests.lua        Data.Quests / InstanceQuests = [questID]={name=EN,...}
  Data/Locale_zhCN.lua   Locales.zhCN(): name(EN->zh) / questName(ID->zh) / npc(ID->zh)
  Data/WorldDrops.lua    Data.WorldMobs = [npcID]={name,...}
产物：_temp/_gqf_name_cache.json {"npcs":{EN:{id,zh}}, "quests":{EN:{id,zh}}}
任务 zh 缺失没关系：id 进 GearSrcQ 后由运行时 C_QuestLog.GetTitleForQuestID 显示。
"""
import json, os, re, subprocess, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROXY = "http://127.0.0.1:7897"
CACHE = os.path.join(HERE, "_gqf_name_cache.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"

class NetDown(Exception):
    pass

_JINA_FAILS = 0

def jina(url, timeout=45):
    global _JINA_FAILS
    if _JINA_FAILS >= 4:
        raise NetDown("jina circuit open")
    for i in range(3):
        try:
            r = subprocess.run(["curl", "-s", "-x", PROXY, "-A", UA,
                                "--max-time", str(timeout), url],
                               capture_output=True, timeout=timeout + 10)
            if r.returncode == 0 and r.stdout:
                txt = r.stdout.decode("utf-8", "replace")
                low = txt.lower()
                if "markdown content" in low and len(txt) > 300:
                    _JINA_FAILS = 0
                    return txt
                if "403" in low and len(txt) < 400:
                    _JINA_FAILS += 1
                    time.sleep(15)
                    continue
                time.sleep(15)
                continue
        except Exception:
            pass
        time.sleep(10)
    _JINA_FAILS += 1
    if _JINA_FAILS >= 4:
        raise NetDown("jina circuit open")
    return ""

def wx_quest_title(qid):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "quests",
                                  "arguments": {"id": int(qid)}}})
    try:
        r = subprocess.run(["curl", "-s", "-x", PROXY, "-X", "POST",
                            "https://wuxianwow.com/mcp",
                            "-H", "Content-Type: application/json",
                            "-H", "Accept: application/json, text/event-stream",
                            "-d", body, "--max-time", "30"],
                           capture_output=True, timeout=40)
        raw = r.stdout.decode("utf-8", "replace")
        if not raw.startswith("{"):
            for line in raw.splitlines():
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    break
        m = json.loads(raw)
        txt = m["result"]["content"][0]["text"]
        d = json.loads(txt)
        t = d.get("title") or d.get("display_name") or ""
        if t.startswith("任务 #"):
            return None
        return t or None
    except Exception:
        return None

def nether_title(kind, eid):
    try:
        r = subprocess.run(["curl", "-s", "-x", PROXY, "--max-time", "25",
                            "https://nether.wowhead.com/forever/tooltip/%s/%d?locale=zhCN"
                            % (kind, eid)],
                           capture_output=True, timeout=35)
        if r.returncode == 0 and r.stdout:
            d = json.loads(r.stdout.decode("utf-8", "replace"))
            n = d.get("name")
            return n or None
    except Exception:
        pass
    return None

SEARCH_RE = re.compile(r'href="[^"]*/forever/(npc|quest)=(\d+)[^"]*"[^>]*>'
                       r'([^<]*)<')
BRACK = re.compile(r"^\[(.*)\]$")
TITLE_RE = re.compile(r"^Title:\s*(.+?)\s*$", re.M)

_PW_EXE = (r"C:/Users/Administrator/AppData/Local/ms-playwright/"
           r"chromium-1247/chrome-win64/chrome.exe")


def make_browser():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    br = pw.chromium.launch(headless=True, executable_path=_PW_EXE,
                            proxy={"server": PROXY})
    pg = br.new_page(user_agent=UA)
    return pw, br, pg


def pw_search(pg, kind, name):
    from urllib.parse import quote
    url = ("https://www.wowhead.com/forever/search?q=" + quote(name))
    pg.goto(url, wait_until="domcontentloaded", timeout=45000)
    pg.wait_for_timeout(3500)
    html = pg.content()
    if len(html) < 5000 or "Just a moment" in html:
        raise NetDown("cf challenge / empty shell")
    low = name.lower()
    first = None
    for m in SEARCH_RE.finditer(html):
        if m.group(1) != kind:
            continue
        if first is None:
            first = int(m.group(2))
        if m.group(3).strip().lower() == low:
            return int(m.group(2))
    return first


BASE = (r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns"
        r"/Lootified/Data")


def lootified_all():
    from lupa import lua51
    L = lua51.LuaRuntime()
    lt = lambda v: L.eval('type')(v)

    def load(path, holder):
        src = open(path, 'rb').read().decode('utf-8', 'replace')
        t = L.table(); L.globals()[holder] = t
        f = L.eval("function(src,name) local f,err=loadstring(src,name) "
                   "if not f then error(err) end return f end")(
            src, os.path.basename(path))
        f("addon", t)
        return t

    Q = load(os.path.join(BASE, 'Quests.lua'), 'NSQ').Data
    LC = load(os.path.join(BASE, 'Locale_zhCN.lua'),
              'NSLC').Locales.zhCN()
    WD = load(os.path.join(BASE, 'WorldDrops.lua'), 'NSW').Data

    q_en2id = {}

    def harvest(T):
        for k in T.keys():
            v = T[k]
            if lt(v) != 'table':
                continue
            if v['name'] is not None and (v['start'] is not None
                                          or v['obj'] is not None
                                          or v['level'] is not None):
                q_en2id.setdefault(str(v['name']), int(k))
                continue
            for k2 in v.keys():
                v2 = v[k2]
                if lt(v2) == 'table' and v2['name'] is not None \
                        and (v2['start'] is not None or v2['obj'] is not None
                             or v2['level'] is not None):
                    q_en2id.setdefault(str(v2['name']), int(k2))

    for tn in ('Quests', 'InstanceQuests'):
        T = Q[tn]
        if lt(T) == 'table':
            harvest(T)

    n_en2id = {}
    wm = WD.WorldMobs
    for k in wm.keys():
        m = wm[k]
        if m is not None:
            n_en2id.setdefault(str(m[1]), int(k))
    for tn in ('Quests', 'InstanceQuests'):
        T = Q[tn]
        if lt(T) != 'table':
            continue

        def npc_harvest(T2):
            for k in T2.keys():
                v = T2[k]
                if lt(v) != 'table':
                    continue
                for fld in ('start', 'ender', 'pre'):
                    s = v[fld]
                    if lt(s) == 'table' and s['kind'] is not None \
                            and str(s['kind']) == 'npc' \
                            and s['name'] is not None \
                            and s['id'] is not None:
                        n_en2id.setdefault(str(s['name']), int(s['id']))

        npc_harvest(T)

    loc_names = {str(k): str(v) for k, v in LC['name'].items()}
    loc_quests = {int(k): str(v) for k, v in LC['questName'].items()}
    loc_npc = {int(k): str(v) for k, v in LC['npc'].items()}
    return q_en2id, n_en2id, loc_names, loc_quests, loc_npc


def load_needed():
    from lupa import lua51
    L = lua51.LuaRuntime()

    def lt(v):
        return L.eval('type')(v)
    GQ = L.table(); L.globals()['GearQuest'] = GQ

    def loadlua(path, varargs):
        src = open(path, 'rb').read().decode('utf-8', 'replace')
        f = L.eval("function(src,name) local f,err=loadstring(src,name) "
                   "if not f then error(err) end return f end")(
            src, os.path.basename(path))
        if varargs:
            f("addon", GQ)
        else:
            f()
    base = r"D:/Game/World of Warcraft/_classic_beta_/Interface/AddOns"
    loadlua(os.path.join(base, "GearQuestForever", "Data.lua"), True)
    for d in sorted(__import__('glob').glob(
            os.path.join(base, 'GearQuestForever_*'))):
        for p in sorted(__import__('glob').glob(
                os.path.join(d, 'Data.*.generated.lua'))):
            loadlua(p, False)
    facts = {}
    for fk in [str(k) for k in GQ.Data.keys() if str(k).endswith('Facts')]:
        tb = GQ.Data[fk]
        for k in tb.keys():
            v = tb[k]
            if lt(v) == 'table' and v['sourceType'] is not None \
                    and str(v['sourceType']) != 'unsourced':
                facts.setdefault(int(k), v)
    prev = []
    ap = os.path.join(HERE, '_gqf_applied.json')
    if os.path.exists(ap):
        try:
            prev = json.load(open(ap, encoding='utf-8'))["src"]
        except Exception:
            prev = []
    npc_names = set(); quest_names = set()
    for i in prev:
        v = facts.get(int(i))
        if v is None:
            continue
        if v['npc'] is not None:
            npc_names.add(str(v['npc']))
        if v['questName'] is not None:
            quest_names.add(str(v['questName']))
    return sorted(npc_names), sorted(quest_names)


def main():
    cache = {"npcs": {}, "quests": {}}
    if os.path.exists(CACHE):
        try:
            cache = json.load(open(CACHE, encoding='utf-8'))
        except Exception:
            pass
    q_en2id, n_en2id, loc_names, loc_quests, loc_npc = lootified_all()
    print("offline maps: quest-name %d / npc-name %d / loc.name %d / "
          "loc.quest %d / loc.npc %d"
          % (len(q_en2id), len(n_en2id), len(loc_names),
             len(loc_quests), len(loc_npc)), flush=True)
    npcs, quests = load_needed()
    print("npc %d / quest %d" % (len(npcs), len(quests)), flush=True)

    def good(e):
        return e is not None and e.get("id") is not None \
            and e.get("zh") is not None

    qid_hit = zh_hit = nid_hit = nzh_hit = 0

    for name in quests:
        cur = cache["quests"].get(name)
        if good(cur):
            qid_hit += 1; zh_hit += 1
            continue
        qid = q_en2id.get(name)
        zh = loc_quests.get(qid) if qid else None
        e = {"id": (cur or {}).get("id") or qid,
             "zh": (cur or {}).get("zh") or zh}
        if e["id"]:
            qid_hit += 1
        if e["zh"]:
            zh_hit += 1
        cache["quests"][name] = e
    for name in npcs:
        cur = cache["npcs"].get(name)
        if good(cur):
            nid_hit += 1; nzh_hit += 1
            continue
        nid = n_en2id.get(name)
        zh = (loc_npc.get(nid) if nid else None) or loc_names.get(name)
        e = {"id": (cur or {}).get("id") or nid,
             "zh": (cur or {}).get("zh") or zh}
        if e["id"]:
            nid_hit += 1
        if e["zh"]:
            nzh_hit += 1
        cache["npcs"][name] = e
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)
    print("offline: quest id %d/%d zh %d/%d; npc id %d/%d zh %d/%d"
          % (qid_hit, len(quests), zh_hit, len(quests),
             nid_hit, len(npcs), nzh_hit, len(npcs)), flush=True)

    # ---------- 网络补抓（Playwright 搜索 + nether 标题，带熔断） ----------
    net = 0
    fails = 0

    def save():
        json.dump(cache, open(CACHE, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=0)
    try:
        pw, br, pg = make_browser()
        todo_q = [n for n in quests
                  if (cache["quests"].get(n) or {}).get("zh") is None]
        todo_n = [n for n in npcs
                  if (cache["npcs"].get(n) or {}).get("zh") is None]
        print("net todo: quest %d / npc %d"
              % (len(todo_q), len(todo_n)), flush=True)
        for name in todo_q:
            e = cache["quests"].setdefault(name, {})
            eid = None
            if e.get("id") is None:
                try:
                    eid = pw_search(pg, "quest", name)
                    fails = 0
                except Exception:
                    fails += 1
                    eid = None
                    if fails >= 4:
                        raise NetDown("browser 4 连败")
                if eid:
                    e["id"] = eid
                    net += 1
                time.sleep(2.5)
            if e.get("id") and e.get("zh") is None:
                zh = nether_title("quest", e["id"])
                if not zh:
                    zh = wx_quest_title(e["id"])
                if zh:
                    e["zh"] = zh
                    net += 1
                time.sleep(1.5)
            save()
            time.sleep(2.5)
        for name in todo_n:
            e = cache["npcs"].setdefault(name, {})
            eid = None
            if e.get("id") is None:
                try:
                    eid = pw_search(pg, "npc", name)
                    fails = 0
                except Exception:
                    fails += 1
                    eid = None
                    if fails >= 4:
                        raise NetDown("browser 4 连败")
                if eid:
                    e["id"] = eid
                    net += 1
                time.sleep(2.5)
            if e.get("id") and e.get("zh") is None:
                zh = nether_title("npc", e["id"])
                if zh:
                    e["zh"] = zh
                    net += 1
                time.sleep(1.5)
            save()
            time.sleep(2.5)
        pw.stop()
    except NetDown as ex:
        print("网络熔断：%s（进度已落盘，稍后重跑可续）" % ex, flush=True)
    except Exception as ex:
        print("网络段异常：%r（进度已落盘）" % ex, flush=True)
    save()
    print("net fetched %d" % net, flush=True)
    print("cache -> %s" % CACHE, flush=True)


if __name__ == "__main__":
    main()

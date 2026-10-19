# -*- coding: utf-8 -*-
"""采集 wowhead 首领技能的「名称 + 说明」兜底文案（客户端给不出时的最后一道）。

为什么需要：部分技能（永恒服自定义 id、或客户端技能库无 description 条目的经典 id ——
2026-10-01 实机「心灵震爆」只有名字、没有文本）在游戏内取不到说明；
本表按 id 落 wowhead 原文，运行期**只在客户端全链拿不到时**使用（客户端有数据时始终以客户端为准）。

数据源（两路，优先复用缓存）：
  1. `_temp/**/*.html` 里 wowhead 页面的 `WH.Gatherer.addData(6, …)` 块
     —— 攻略页/法术页都带这坨，含 name_zhcn|enus + description_zhcn|enus（免联网）；
  2. 缓存里仍缺的 id → 抓 https://www.wowhead.com/forever/{cn,en}/spell=<id> 补。

输出：_temp/_wh_spell_desc.json
  { "<id>": { "zh": 名, "zhDesc": 描述, "en": 名, "enDesc": 描述 } }

用法：
  $PY _df_wh_spell_desc.py            # 全量（缓存优先，缺的联网补）
  $PY _df_wh_spell_desc.py --scan     # 只扫缓存，不联网
  $PY _df_wh_spell_desc.py 1293228 …  # 只补指定 id
"""
import glob
import io
import json
import os
import re
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "_wh_spell_desc.json")
sys.path.insert(0, HERE)

PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                  " (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.wowhead.com/",
}

BLOCK = re.compile(r"WH\.Gatherer\.addData\(\s*6\s*,\s*\d+\s*,\s*(\{.*?\})\s*\)\s*;", re.S)
ENTRY = re.compile(r'"(\d+)":\{"name_(zhcn|enus)":"(.*?)","icon":"(.*?)"'
                   r'(.*?)description_(?:zhcn|enus)":"(.*?)"\}', re.S)


def clean(s):
    if not s:
        return ""
    s = s.replace("\\/", "/").replace('\\"', '"')
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\u200b", "")
    return re.sub(r"\s+", " ", s).strip()


def scan_caches():
    """扫 _temp 下所有 HTML 缓存里的法术 Gatherer 块 → ({sid:(名,desc)}, {sid:(名,desc)})。"""
    zh, en = {}, {}
    files = [p for p in glob.glob(os.path.join(HERE, "**", "*.html"), recursive=True)]
    for path in files:
        try:
            s = open(path, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "Gatherer.addData(6" not in s:
            continue
        for m in BLOCK.finditer(s):
            for mm in ENTRY.finditer(m.group(1)):
                sid = int(mm.group(1))
                loc = mm.group(2)
                nm = clean(mm.group(3))
                ds = clean(mm.group(6))
                if not ds:
                    continue
                (zh if loc == "zhcn" else en).setdefault(sid, (nm, ds))
    print("— 缓存扫描：%d 个 HTML；zh 命中 %d 条 / en 命中 %d 条" % (len(files), len(zh), len(en)))
    return zh, en


def fetch(sid, loc):
    """抓一个法术页的名+说明。站点前缀依次试 forever → classic → 无前缀
    （经典老 id 在永远服页可能没有，classic 页有；反过来也一样）。"""
    from curl_cffi import requests
    for prefix in ("forever", "classic", ""):
        seg = ("%s/" % prefix) if prefix else ""
        url = "https://www.wowhead.com/%s%s/spell=%d" % (seg, loc, sid)
        for wait in (0, 15, 25, 35, 45):
            if wait:
                time.sleep(wait)
            try:
                r = requests.get(url, proxies=PROXIES, impersonate="chrome110",
                                 headers=HEADERS, timeout=30)
            except Exception as e:
                print("  ! %s err %s" % (url, e))
                continue
            if r.status_code != 200:
                print("  ! %s -> %d" % (url, r.status_code))
                continue
            m = BLOCK.search(r.text)
            if not m:
                print("  ! %s 无 Gatherer 数据" % url)
                continue
            e = ENTRY.search(m.group(1))
            if not e:
                print("  ! %s Gatherer 无本 id 条目" % url)
                break  # 换站点前缀再试
            return clean(e.group(3)), clean(e.group(6))
    return "", ""


def target_ids():
    """BossSkills 会用到的全部法术 id（与 gen_boss_skills 同一份 wowhead 来源）。"""
    import gen_boss_skills as G
    wh = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
    ids = set()
    for did in G.DUN7:
        for _boss, v in (wh.get(did) or {}).items():
            ids.update(v.get("spells") or [])
    return sorted(ids)


def main():
    argv = sys.argv[1:]
    scan_only = "--scan" in argv
    explicit = sorted({int(a) for a in argv if a.isdigit()})
    try:
        db = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        db = {}

    zh, en = scan_caches()
    ids = explicit or target_ids()
    print("— 目标 id %d 个；缓存已覆盖 zh %d / en %d"
          % (len(ids), len([i for i in ids if i in zh]), len([i for i in ids if i in en])))

    need_zh = [i for i in ids if i not in zh]
    need_en = [i for i in ids if i not in en]
    print("— 需联网补：zh %d 条，en %d 条" % (len(need_zh), len(need_en)))

    scanned = {}
    for i in ids:
        if i in zh or i in en:
            n_zh, d_zh = zh.get(i, ("", ""))
            n_en, d_en = en.get(i, ("", ""))
            scanned[str(i)] = {"zh": n_zh, "zhDesc": d_zh, "en": n_en, "enDesc": d_en}

    for sid in need_zh:
        if scan_only:
            break
        nm, ds = fetch(sid, "cn")
        scanned.setdefault(str(sid), {"zh": "", "zhDesc": "", "en": "", "enDesc": ""})
        scanned[str(sid)]["zh"], scanned[str(sid)]["zhDesc"] = nm, ds
        print("%d zh: %r / %r" % (sid, nm, ds[:34]))
        time.sleep(3)
    for sid in need_en:
        if scan_only:
            break
        cur = scanned.setdefault(str(sid), {"zh": "", "zhDesc": "", "en": "", "enDesc": ""})
        nm, ds = fetch(sid, "en")
        cur["en"], cur["enDesc"] = nm, ds
        print("%d en: %r / %r" % (sid, nm, ds[:34]))
        time.sleep(3)

    # 合并：新扫描/抓取的覆盖旧值；显式补的 id 只动该 id
    for k, v in scanned.items():
        if explicit and int(k) not in explicit:
            continue
        merged = dict(db.get(k) or {})
        for f in ("zh", "zhDesc", "en", "enDesc"):
            if v.get(f):
                merged[f] = v[f]
        db[k] = merged
    json.dump(db, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    miss_zh = [k for k in map(str, ids) if not (db.get(k) or {}).get("zhDesc")]
    miss_en = [k for k in map(str, ids) if not (db.get(k) or {}).get("enDesc")]
    print("— 落盘 %d 条；目标中缺 zh 描述 %d 条 %s；缺 en 描述 %d 条 %s"
          % (len(db), len(miss_zh), miss_zh[:12], len(miss_en), miss_en[:12]))


if __name__ == "__main__":
    main()

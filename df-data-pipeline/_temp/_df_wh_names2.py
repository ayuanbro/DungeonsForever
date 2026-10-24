# -*- coding: utf-8 -*-
"""补抓名字：正文引用的 npc 中英名 + 缺失的 spell 中英名。

输出：
  _temp/_wh_npc_names.json   = { str(npcid): {"zh": …, "en": …} }
  _temp/_wh_spell_names.json 追补缺失条目
"""
from curl_cffi import requests
import json
import os
import re
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROXIES = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}


def fetch(url):
    # CF 限流退避：15/25/35/45s 重试；网络异常也算一次失败（2026-09-30：裸抛 Timeout 会崩掉整轮）
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


def zh_name(h):
    if not h:
        return ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def en_name(h):
    if not h:
        return ""
    m = re.search(r"<title>(.*?)</title>", h)
    if not m:
        return ""
    t = m.group(1)
    for sep in ("—", "\u2014"):
        if sep in t:
            return t.split(sep)[0].strip()
    return t.strip()


def load(p):
    if os.path.exists(os.path.join(HERE, p)):
        return json.load(open(os.path.join(HERE, p), encoding="utf-8"))
    return {}


# ── NPC 名 ──
npcs = load("_wh_npc_names.json")
guide = json.load(open(os.path.join(HERE, "_wh_guide_raw.json"), encoding="utf-8"))
want = sorted({int(x) for v in guide.values() for b in v.values()
               for x in re.findall(r"«N(\d+)»", b["text"])})
todo = [i for i in want if not npcs.get(str(i), {}).get("zh")]
print("NPC 待抓 %d / %d" % (len(todo), len(want)))
for i in todo:
    # ★ 永恒服自定义 NPC 只有 forever 区有（2026-09-30：263438 等在 classic 永远空）⇒ classic 空了回退 forever
    zh = zh_name(fetch("https://www.wowhead.com/classic/cn/npc=%d" % i))
    if not zh:
        zh = zh_name(fetch("https://www.wowhead.com/forever/cn/npc=%d" % i))
    time.sleep(0.4)
    en = en_name(fetch("https://www.wowhead.com/forever/npc=%d" % i)) if zh else ""
    if not en:
        en = en_name(fetch("https://www.wowhead.com/classic/npc=%d" % i))
    time.sleep(0.4)
    npcs[str(i)] = {"zh": zh, "en": en}
    json.dump(npcs, open(os.path.join(HERE, "_wh_npc_names.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)  # ★ 逐条落盘
    print("npc %6d  zh=%-16s en=%s" % (i, zh, en))
json.dump(npcs, open(os.path.join(HERE, "_wh_npc_names.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ── Spell 名补漏 ──
spells = load("_wh_spell_names.json")
# ★ 2026-09-30 晚：正文 «S» 引用之外，**Abilities 表的法术 id 也要**——
#   gen_boss_skills 按英文名把 wowhead 能力对回 fc 技能行，缺名就对不上。
want2 = sorted({int(x) for v in guide.values() for b in v.values()
                for x in re.findall(r"«S(\d+)»", b["text"])
                } | {int(x) for v in guide.values() for b in v.values()
                     for x in (b.get("spells") or [])})
todo2 = [i for i in want2 if str(i) not in spells or not spells[str(i)].get("zh")]
print("Spell 待补 %d / %d" % (len(todo2), len(want2)))
for i in todo2:
    # ★ classic 页没有永恒服自定义法术（2026-09-30 实锤）⇒ classic 空了回退 forever
    zh = zh_name(fetch("https://www.wowhead.com/classic/cn/spell=%d" % i))
    if not zh:
        zh = zh_name(fetch("https://www.wowhead.com/forever/cn/spell=%d" % i))
    time.sleep(0.4)
    en = en_name(fetch("https://www.wowhead.com/forever/spell=%d" % i)) if zh else ""
    if not en:
        en = en_name(fetch("https://www.wowhead.com/classic/spell=%d" % i))
    time.sleep(0.4)
    spells[str(i)] = {"zh": zh, "en": en}
    json.dump(spells, open(os.path.join(HERE, "_wh_spell_names.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)  # ★ 逐条落盘（崩了不丢已抓的）
    print("spell %6d  zh=%-16s en=%s" % (i, zh, en))
json.dump(spells, open(os.path.join(HERE, "_wh_spell_names.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("done")

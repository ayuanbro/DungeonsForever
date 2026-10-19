# -*- coding: utf-8 -*-
# 生成 Core/Data/Data_Gear.lua（装备库全量静态目录）与 enUS 覆盖层
# 数据源：foreverchanges.pro /items/zh-cn/{same,new,changed,missing}.json + sources.json
# 本地缓存：_temp/_fc_{same,new,changed,missing,sources}.json（存在则直接用，--refetch 强制重下）
import json
import os
import io
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROXY = "http://127.0.0.1:7897"
BASE = "https://foreverchanges.pro/items/zh-cn"
BASE_EN = "https://foreverchanges.pro/items"
SHARDS = ["same", "new", "changed", "missing"]
CLASS_ORDER = [2, 4, 1, 0, 7, 6, 11, 9, 5, 15, 12, 13, 18, 3, 8, 10, 14]
CLASS_NAMES = {
    0: "消耗品", 1: "容器", 2: "武器", 3: "宝石", 4: "护甲", 5: "材料",
    6: "弹药", 7: "商品", 8: "物品强化", 9: "配方", 10: "货币", 11: "箭袋",
    12: "任务", 13: "钥匙", 14: "永久", 15: "其它", 18: "魔兽世界时光徽章",
}
EN_CLASS_NAMES = {
    0: "Consumable", 1: "Container", 2: "Weapon", 3: "Gem", 4: "Armor",
    5: "Material", 6: "Ammo", 7: "Merchandise", 8: "Item Enhancement",
    9: "Recipe", 10: "Money", 11: "Quiver", 12: "Quest", 13: "Key",
    14: "Permanent", 15: "Misc.", 18: "WoW Token",
}

HEAD_EN = '''local _, ns = ...
if (type(GetLocale) ~= "function") or GetLocale() ~= "enUS" then return end'''


def fetch(name, base=None, tag=""):
    base = base or BASE
    path = os.path.join(HERE, "_fc_%s%s.json" % (tag, name))
    if os.path.exists(path) and "--refetch" not in sys.argv:
        return json.load(open(path, encoding="utf-8"))
    import urllib.request
    req = urllib.request.Request(
        "%s/%s.json" % (base, name),
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    data = opener.open(req, timeout=120).read()
    with open(path, "wb") as f:
        f.write(data)
    return json.loads(data.decode("utf-8"))


def lua_str(s):
    if s is None:
        return '""'
    s = str(s)
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", "\\n").replace("\r", "").replace("\t", " ")
    return '"%s"' % s


def merge_shards(shards):
    order = {"same": 0, "new": 1, "changed": 2, "missing": 3}
    seen = {}
    for name in SHARDS:
        for e in shards[name]:
            i = e.get("i")
            if i is None:
                continue
            old = seen.get(i)
            if old is None or order[name] < order[old.get("_shard", "missing")]:
                e = dict(e)
                e["_shard"] = name
                seen[i] = e
    return sorted(seen.values(), key=lambda e: e["i"])


def build_lua(items, used_cls, by_cls, sub_tree, src_map, cls_names,
              name_getter, header):
    out = io.StringIO()
    w = out.write
    w(header)
    w("ns.EnsureGearData = function()\n")
    w("if ns.GearData then return ns.GearData end\n")
    w("ns.GearData = {\n")
    w('  ver = %d,\n' % (len(items),))
    w("  cls = { %s },\n" % ", ".join(
        "{%d,%s}" % (c, lua_str(cls_names.get(c, cls_names.get(15)))) for c in used_cls))
    w("  sub = {\n")
    for c in used_cls:
        subs = sub_tree.get(str(c)) or sub_tree.get(c)
        if not subs:
            continue
        pairs = ", ".join("{%d,%s}" % (int(k), lua_str(v))
                          for k, v in sorted(subs.items(), key=lambda x: int(x[0])))
        w("    [%d] = { %s },\n" % (c, pairs))
    w("  },\n")
    w("  src = {\n")
    chunk = []
    for i in sorted(src_map):
        chunk.append("[%d]=%s" % (i, lua_str(src_map[i])))
    for j in range(0, len(chunk), 400):
        w("    " + ", ".join(chunk[j:j + 400]) + ",\n")
    w("  },\n")
    w("  items = {\n")
    row = []
    for e in items:
        s = e.get("s") or ""
        k = e.get("k") or ""
        row.append(
            "{%d,%s,%d,%s,%s,%s,%d,%d,%s,%s}" % (
                e["i"], lua_str(name_getter(e)), e.get("q", 1),
                e.get("l", 0), e.get("r", 0),
                lua_str(s), e.get("c", 15), e.get("u", 0),
                lua_str(k), lua_str(e.get("_st", ""))))
        if len(row) >= 200:
            w("    " + ", ".join(row) + ",\n")
            row = []
    if row:
        w("    " + ", ".join(row) + ",\n")
    w("  },\n  }\n")
    w("return ns.GearData\n")
    w("end\n")
    return out.getvalue()


def main():
    shards, sub_tree = {}, None
    for name in SHARDS:
        d = fetch(name)
        shards[name] = d["items"]
        if sub_tree is None:
            sub_tree = d.get("sub") or {}
    items = merge_shards(shards)
    KEEP_CLASSES = {2, 4}
    items = [e for e in items if e.get("c") in KEEP_CLASSES]
    sys.stderr.write("unique items: %d\n" % len(items))

    by_cls = {}
    for e in items:
        by_cls.setdefault(e.get("c", -1), 0)
        by_cls[e.get("c", -1)] += 1
    used_cls = [c for c in CLASS_ORDER if c in by_cls]
    for c in by_cls:
        if c not in used_cls:
            used_cls.append(c)
    sys.stderr.write("class counts: %s\n" % ", ".join(
        "%s=%d" % (c, by_cls[c]) for c in used_cls))

    src_raw = fetch("sources")
    src_map = {}
    for k, v in (src_raw.get("items") or {}).items():
        if isinstance(v, list) and len(v) >= 3 and (v[1] or v[2]):
            src_map[int(k)] = "%s|%s" % (v[1] or "", v[2] or "")
    keep_ids = {e["i"] for e in items}
    src_map = {k: v for k, v in src_map.items() if k in keep_ids}

    head = "local _, ns = ...\n\n"
    body = build_lua(items, used_cls, by_cls, sub_tree, src_map,
                     CLASS_NAMES, lambda e: e.get("n"), head)
    path = os.path.join(ROOT, "Core", "Data", "Data_Gear.lua")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    sys.stderr.write("wrote %s (%.2f MB)\n" % (
        path, os.path.getsize(path) / 1048576.0))

    en_shards = {}
    for name in SHARDS:
        en_shards[name] = fetch(name, BASE_EN, "en_").get("items") or []
    en_sub = None
    for name in SHARDS:
        d = fetch(name, BASE_EN, "en_")
        if en_sub is None:
            en_sub = d.get("sub") or {}
    en_src_raw = fetch("sources", BASE_EN, "en_")
    en_src_map = {}
    for k, v in (en_src_raw.get("items") or {}).items():
        if isinstance(v, list) and len(v) >= 3 and (v[1] or v[2]):
            en_src_map[int(k)] = "%s|%s" % (v[1] or "", v[2] or "")
    en_src_map = {k: v for k, v in en_src_map.items() if k in keep_ids}
    en_names = {}
    for name in SHARDS:
        for e in en_shards[name]:
            if e.get("ne"):
                en_names[e["i"]] = e["ne"]

    def en_name(e):
        return en_names.get(e["i"]) or e.get("n") or ("Item #" + str(e["i"]))

    en_body = build_lua(items, used_cls, by_cls, en_sub, en_src_map,
                        EN_CLASS_NAMES, en_name, HEAD_EN)
    en_path = os.path.join(ROOT, "Core", "Data", "enUS", "Data_Gear.lua")
    os.makedirs(os.path.dirname(en_path), exist_ok=True)
    with open(en_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(en_body)
    sys.stderr.write("wrote %s (%.2f MB)\n" % (
        en_path, os.path.getsize(en_path) / 1048576.0))


if __name__ == "__main__":
    main()

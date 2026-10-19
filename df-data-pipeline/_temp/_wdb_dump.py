# -*- coding: utf-8 -*-
"""客户端 WDB 缓存解析（creaturecache / questcache，zhCN + enUS）
格式（legacy WDB）：magic[4] + build u32 + locale[4] + rows u32 + ...头
记录：[id u32][size u32][offset u32] 表 + 数据块。
输出：_temp/_wdb_names.json {npcs:{id:{en,zh}}, quests:{id:{en,zh}}}
"""
import json, os, struct, sys

CACHE_DIR = (r"D:/Game/World of Warcraft/_classic_beta_/Cache/WDB")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "_wdb_names.json")


def parse_wdb(path):
    raw = open(path, 'rb').read()
    magic, build = struct.unpack_from("<4sI", raw, 0)
    locale = raw[8:12][::-1].decode('ascii', 'replace')
    recs = []
    pos = 0x18
    while pos + 8 <= len(raw):
        rid, rsize = struct.unpack_from("<II", raw, pos)
        if rsize > 65536 or pos + 8 + rsize > len(raw):
            return None
        recs.append((rid, bytes(raw[pos + 8: pos + 8 + rsize])))
        pos += 8 + rsize
    return {"build": build, "locale": locale, "recs": recs}


def strings_of(blob):
    out = []
    start = None
    for i, b in enumerate(blob + b"\x00"):
        if b == 0:
            if start is not None and i - start >= 2:
                seg = blob[start:i]
                try:
                    s = seg.decode('utf-8')
                    if s and all(ord(ch) >= 0x20 for ch in s) \
                            and any(ch.isalnum() or '\u4e00' <= ch <= '\u9fff'
                                    for ch in s):
                        out.append(s)
                except Exception:
                    pass
            start = None
        else:
            if start is None:
                start = i
    return out


def main():
    result = {"npcs": {}, "quests": {}}
    for kind, fname, store in (
            ("npc", "creaturecache.wdb", "npcs"),
            ("quest", "questcache.wdb", "quests")):
        for loc in ("zhCN", "enUS"):
            p = os.path.join(CACHE_DIR, loc, fname)
            if not os.path.exists(p):
                continue
            w = parse_wdb(p)
            if w is None:
                print("%s/%s: 解析失败" % (loc, fname), flush=True)
                continue
            print("%s/%s: build %d, %d records"
                  % (loc, fname, w["build"], len(w["recs"])), flush=True)
            for rid, blob in w["recs"]:
                ss = strings_of(blob)
                if not ss:
                    continue
                e = result[store].setdefault(rid, {})
                if loc == "zhCN":
                    e["zh"] = ss[0]
                    if len(ss) > 1:
                        e["zh2"] = ss[1]
                else:
                    e["en"] = ss[0]
                    if len(ss) > 1:
                        e["en2"] = ss[1]
    json.dump(result, open(OUT, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=0)
    n = result["npcs"]; q = result["quests"]
    print("npc %d (zh %d / en %d); quest %d (zh %d / en %d)"
          % (len(n), sum(1 for v in n.values() if 'zh' in v),
             sum(1 for v in n.values() if 'en' in v),
             len(q), sum(1 for v in q.values() if 'zh' in v),
             sum(1 for v in q.values() if 'en' in v)), flush=True)
    print("-> %s" % OUT, flush=True)
    for rid in list(q)[:3]:
        print(rid, q[rid], flush=True)


if __name__ == "__main__":
    main()

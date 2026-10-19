# -*- coding: utf-8 -*-
"""比对 _bosspos_floors_all.json 与现有 Core/Data/Data_BossPos.lua 的差异。

现有 Lua 用真 Lua 5.1（lupa）执行解析，杜绝手搓正则漏行。
"""
import json
import os

from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUR = os.path.join(DF, "Core", "Data", "Data_BossPos.lua")


def lua_table_to_py(v):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    return _conv(v)


def _conv(v):
    if hasattr(v, "keys") and not isinstance(v, dict):
        d = {}
        n = 0
        for k in v.keys():
            d[k] = _conv(v[k])
            try:
                if int(k) == len(d):
                    n = len(d)
            except Exception:
                pass
        # 数组形态 → list
        keys = set(d.keys())
        if keys and all(isinstance(k, int) or (isinstance(k, float) and k.is_integer()) for k in keys):
            ks = sorted(int(k) for k in keys)
            if ks == list(range(1, len(ks) + 1)):
                return [d[k] for k in ks]
        return d
    return v


def load_cur():
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.globals()["ns"] = L.table()
    code = open(CUR, encoding="utf-8").read().replace("local _, ns = ...", "_ = nil")
    L.execute(code)
    return _conv(L.globals().ns["BossPos"])


def main():
    def pts_map(d):
        """{en: [(x,y,floor), …]}"""
        m = {}
        for en, pts in d.items():
            m[en] = sorted((p[0], p[1], p[2] if len(p) > 2 else 1) for p in pts)
        return m

    def floors_to_pts(d):
        """_bosspos_floors_all.json {层号: [ {en,x,y}, … ]} → {en: [(x,y,floor)]}"""
        m = {}
        for flnum, rows in d.items():
            for r in rows:
                m.setdefault(r["en"], []).append((r["x"], r["y"], int(flnum)))
        for en in m:
            m[en] = sorted(m[en])
        return m

    cur = load_cur()
    raw = json.load(open(os.path.join(HERE, "_bosspos_floors_all.json"), encoding="utf-8"))
    new = {did: floors_to_pts(d) for did, d in raw.items()}

    for did in sorted(set(cur) | set(new)):
        a = pts_map(cur.get(did, {}))
        b = pts_map(new.get(did, {}))
        if a == b:
            print("%-22s 相同（%d 首领 / %d 点）" % (did, len(a), sum(len(v) for v in a.values())))
            continue
        print("%-22s ★ 差异" % did)
        for en in sorted(set(a) | set(b)):
            pa, pb = a.get(en), b.get(en)
            if pa == pb:
                continue
            if pa is None:
                print("    + %s 新增 %s" % (en, pb))
            elif pb is None:
                print("    - %s 现有被删 %s" % (en, pa))
            else:
                sa, sb = set(pa), set(pb)
                only_a = sa - sb
                only_b = sb - sa
                if only_a:
                    print("    - %s 少 %s" % (en, sorted(only_a)))
                if only_b:
                    print("    + %s 多 %s" % (en, sorted(only_b)))


if __name__ == "__main__":
    main()

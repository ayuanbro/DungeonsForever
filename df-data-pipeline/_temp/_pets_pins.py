# -*- coding: utf-8 -*-
"""从缓存的两篇 wowhead 新闻页里抠出正文 BBCode 的 map / pin / zone 标记。
用途：判定「wowhead 原文到底标没标坐标」——没标的区域热点只应打开区域地图。
"""
import re
import os
import json

BS = chr(92)  # 反斜杠，避免 JSON 转义地狱


def unescape_js(s):
    s = s.replace(BS + "/", "/")
    s = s.replace(BS + '"', '"')
    s = s.replace(BS + "n", "\n")
    try:
        s = s.encode("utf-8").decode("unicode_escape")
    except Exception:
        pass
    return s


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    for fn in ("wh_capitals_cn.html", "wh_gustjumper_cn.html"):
        p = os.path.join(root, "_ref_pets", fn)
        if not os.path.exists(p):
            print(fn, "MISSING")
            continue
        h = open(p, encoding="utf-8", errors="ignore").read()
        print("=" * 78)
        print(fn, len(h))
        for tag in ("map", "pin", "zone", "npc", "item", "object"):
            hits = re.findall(r"\[" + tag + r"[^\]]{0,120}\]", h)
            if hits:
                print("  [%s] x%d: %s" % (tag, len(hits), sorted(set(hits))[:8]))
        n = 0
        for m in re.finditer(r"printHtml\(\"((?:[^\"\\]|\\.)*)\"", h):
            n += 1
            body = re.sub(r"\s+", " ", unescape_js(m.group(1)))
            print("  ---- printHtml #%d（%d 字）----" % (n, len(body)))
            print("  " + body[:1600])
        if n == 0:
            print("  (本页没有 printHtml 正文块)")


if __name__ == "__main__":
    main()

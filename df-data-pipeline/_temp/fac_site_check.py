# -*- coding: utf-8 -*-
"""用 foreverchanges.pro 副本页的任务阵营分组交叉验证可疑任务。"""
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")

TARGETS = {
    "hall-of-thanes": [96395, 96403],
    "the-deadmines": [373],
    "razorfen-kraul": [1701],
    "uldaman": [721, 2398, 2200],
    "sunken-temple": [3445, 4143],
    "blackrock-depths": [4262, 4341, 4241],
    "dire-maul-west": [7482],
}


def fetch(url):
    r = subprocess.run(["curl", "-s", "-x", "http://127.0.0.1:7897", url],
                       capture_output=True, timeout=60)
    return r.stdout.decode("utf-8", "replace")


def parse_sides(html):
    out = {}
    for chunk in html.split('<div class="dgx-side"')[1:]:
        head = chunk[:400]
        t = re.sub(r'<[^>]+>', '', head)
        t = t[:t.find('</h3>')] if '</h3>' in t else t
        if '双方阵营' in t:
            side = 'BOTH'
        elif '联盟' in t:
            side = 'A'
        elif '部落' in t:
            side = 'H'
        else:
            side = 'UNK:' + t.strip()[:20]
        nxt = chunk.find('<div class="dgx-side">')
        body = chunk if nxt < 0 else chunk[:nxt]
        end = body.find('</section>')
        if end >= 0 and 'dgx-quest' in body[:end]:
            body = body[:body.rfind('id="quest-', 0, end)] if False else body
        for q in re.finditer(r'id="quest-(\d+)"', body):
            out[int(q.group(1))] = side
    return out


def main():
    res = {}
    for slug, ids in TARGETS.items():
        html = fetch(f"https://foreverchanges.pro/zh-cn/dungeons/{slug}")
        sides = parse_sides(html)
        print(f"{slug}: {', '.join(str(q) + '=' + sides.get(q, 'N/A') for q in ids)}")
        for q in ids:
            res[q] = [slug, sides.get(q)]
    json.dump(res, open("_temp/fac_site_check.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

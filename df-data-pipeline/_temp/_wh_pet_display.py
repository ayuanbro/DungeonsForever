# -*- coding: utf-8 -*-
"""抓 wowhead forever/cn 物品页，找宠物 3D 模型 displayId。
经验（2026-09-25）：裸 curl 被 CloudFront 按 TLS 指纹拦（Request blocked），
必须 curl_cffi Chrome 指纹 + 7897 代理。
"""
import re
import sys
from curl_cffi import requests

PROXY = "http://127.0.0.1:7897"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

ITEMS = {
    282047: "鳄鱼宝宝",
    275682: "活泼软泥怪",
    268109: "音乐跃风蛙",
    280456: "维维尔·K·尼维尔",
}

PAT_DISPLAY = re.compile(r"display[Ii]d[\"']?\s*[:=]\s*[\"']?(\d+)")
PAT_NPC = re.compile(r"/npc[=:](\d+)")
PAT_MODEL = re.compile(r"modelviewer[^\"']{0,80}", re.I)


def fetch(item_id):
    url = f"https://www.wowhead.com/forever/cn/item={item_id}"
    r = requests.get(url, impersonate="chrome124",
                     proxies={"http": PROXY, "https": PROXY},
                     headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
                     timeout=30)
    return r


def main():
    ok = 0
    for item_id, name in ITEMS.items():
        try:
            r = fetch(item_id)
        except Exception as e:
            print(f"=== item={item_id} {name} EXC: {e}")
            continue
        html = r.text or ""
        print(f"=== item={item_id} {name} http={r.status_code} len={len(html)}")
        if r.status_code != 200 or len(html) < 2000:
            continue
        ok += 1
        with open(f"wh_{item_id}.html", "w", encoding="utf-8") as f:
            f.write(html)
        title = re.search(r"<title>(.*?)</title>", html, re.S)
        if title:
            print("  title:", title.group(1).strip()[:80])
        disp = sorted(set(PAT_DISPLAY.findall(html)), key=int)
        print("  displayId:", disp[:12] if disp else "(none)")
        npcs = sorted(set(PAT_NPC.findall(html)), key=int)
        print("  npc links:", npcs[:12] if npcs else "(none)")
        mv = sorted(set(m[:60] for m in PAT_MODEL.findall(html)))
        for m in mv[:6]:
            print("  modelviewer:", m)
    print(f"[DONE] fetched_ok={ok}/{len(ITEMS)}")


if __name__ == "__main__":
    sys.exit(main())

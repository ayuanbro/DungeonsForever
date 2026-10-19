# -*- coding: utf-8 -*-
"""
DungeonsForever · 暴风城 NPC 坐标校正取数（wowhead wotlk/cn NPC 页）
================================================================
背景：无限服（1.60.x）客户端的暴风城地图已按**新生代边界**重构，而 _wh_npcloc.json
      （wowhead forever 分支）记的仍是经典边界口径 → 整张图百分比坐标系统性偏移
      （实测 5413 旧 57.4,16.0 / 新 64.6,37.2）。
口径：wowhead 的 wotlk 分支在同一张图上记的正是新生代边界坐标，故逐页取
      `g_mapperData` 第一条点位作为校正值（与 forever 分支同解析口径）。
用法：
    python _fetch_wh_wotlk_npcloc.py            # 有缓存用缓存
    python _fetch_wh_wotlk_npcloc.py --refresh  # 强制重抓
输出：_npcloc_sw_override.json  { "<npcID>": {"map":1453,"x":..,"y":..,"zone":..,"_name":..} }
缓存：_wh_wotlk_npccache/npc=<id>.txt（与 forever 缓存分开，勿混用）
"""
import json
import os
import sys
import time

from curl_cffi import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "_wh_wotlk_npccache")
OUT = os.path.join(HERE, "_npcloc_sw_override.json")
PROXIES = {"https": "http://127.0.0.1:7897", "http": "http://127.0.0.1:7897"}
WH_NPC = "https://www.wowhead.com/wotlk/cn/npc=%d"
DELAY = 0.6
RATE_SLEEP = 20.0

# 暴风城（uiMapID 1453）的 21 个 NPC —— 与 Data_NPCLoc.lua 里地图名为「暴风城」的键集一致
IDS = [332, 656, 928, 1284, 1416, 1646, 1719, 1721, 1748, 2198, 2285,
       4984, 5384, 5413, 6171, 6579, 7917, 12336, 14450, 11026, 1325]

# 名称仅用于人工核对（不进产物）
NAMES = {
    332: "马迪亚斯·肖尔", 656: "维尔德·蓟草", 928: "格雷森·沙东布瑞克公爵",
    1284: "大主教本尼迪塔斯", 1416: "格瑞曼德·艾尔默", 1646: "巴隆斯·阿历克斯顿",
    1719: "典狱官塞尔沃特", 1721: "尼科瓦·拉斯克", 1748: "伯瓦尔·弗塔根公爵",
    2198: "公告员古德曼", 2285: "雷明顿·瑞治维尔伯爵", 4984: "阿古斯·夜语",
    5384: "布罗哈恩·铁桶", 5413: "弗伦·长须", 6171: "达索瑞恩·拉尔",
    6579: "沉默的舒尼", 7917: "萨尔努修士", 12336: "克罗雷修士",
    11026: "斯普莱特", 1325: "贾斯伯·菲尔",
    14450: "孤儿监护员奈丁加尔",
}

os.makedirs(CACHE, exist_ok=True)


def get_page(nid, refresh=False):
    path = os.path.join(CACHE, "npc=%d.txt" % nid)
    if not refresh and os.path.exists(path) and os.path.getsize(path) > 500:
        return open(path, encoding="utf-8").read()
    time.sleep(DELAY)
    r = requests.get(WH_NPC % nid, impersonate="chrome", proxies=PROXIES, timeout=60)
    if r.status_code == 403:
        print("  npc=%d 403，退避 %.0fs 重试" % (nid, RATE_SLEEP))
        time.sleep(RATE_SLEEP)
        r = requests.get(WH_NPC % nid, impersonate="chrome", proxies=PROXIES, timeout=60)
    if r.status_code != 200:
        raise RuntimeError("npc=%d HTTP %d" % (nid, r.status_code))
    if len(r.text) > 500:
        open(path, "w", encoding="utf-8").write(r.text)
    return r.text


def parse_mapper(h):
    """→ 第一条 {map,x,y,zone} 或 None。取 g_mapperData 第一个地区第一条点位。"""
    i = h.find("g_mapperData")
    if i < 0:
        return None
    j = h.find("{", i)
    if j < 0:
        return None
    depth = 0
    end = None
    for k in range(j, min(j + 200000, len(h))):
        c = h[k]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    if not end:
        return None
    try:
        data = json.loads(h[j:end])
    except Exception:
        return None
    for entries in data.values():
        if not isinstance(entries, list):
            continue
        for ent in entries:
            coords = ent.get("coords") or []
            mid = ent.get("uiMapId")
            if mid and coords:
                x, y = coords[0]
                return {"map": int(mid), "x": round(float(x), 1), "y": round(float(y), 1),
                        "zone": ent.get("uiMapName") or ""}
    return None


def main():
    refresh = "--refresh" in sys.argv
    out = {}
    miss = []
    for nid in IDS:
        try:
            loc = parse_mapper(get_page(nid, refresh))
        except Exception as e:
            print("  !! npc=%d %s" % (nid, e))
            loc = None
        if not loc:
            miss.append(nid)
            print("  -- npc=%-7d %-21s 无 g_mapperData 点位" % (nid, NAMES.get(nid, "")))
            continue
        loc["_name"] = NAMES.get(nid, "")
        out[str(nid)] = loc
        print("  %s npc=%-7d %-21s map=%-5d %6.1f, %6.1f  %s"
              % ("OK" if loc["map"] == 1453 else "!!", nid, NAMES.get(nid, ""),
                 loc["map"], loc["x"], loc["y"], loc["zone"]))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("\n命中 %d/%d，缺 %s" % (len(out), len(IDS), miss or "无"))
    print("写出 %s" % OUT)


if __name__ == "__main__":
    main()

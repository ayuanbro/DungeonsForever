import io
import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "Core", "Data", "Data_ClassQuest.lua")
OUT = os.path.join(ROOT, "_temp", "_cq_item_zh.json")
PROXY = "http://127.0.0.1:7897"

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)


def ids():
    src = io.open(DATA, encoding="utf-8").read()
    found = set()
    for m in re.finditer(r"items = \{([^}]*)\}", src):
        for x in m.group(1).split(","):
            x = x.strip()
            if x.isdigit():
                found.add(int(x))
    return sorted(found)


def fetch(iid):
    url = "https://nether.wowhead.com/tooltip/item/%d?dataEnv=1&locale=zhCN" % iid
    try:
        with opener.open(url, timeout=20) as r:
            obj = json.loads(r.read().decode("utf-8"))
        nm = obj.get("name")
        if nm and re.search(r"[\u4e00-\u9fff]", nm):
            return iid, nm
    except Exception:
        return iid, None
    return iid, None


def main():
    allids = ids()
    print("items", len(allids))
    res = {}
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as fh:
            res = {int(k): v for k, v in json.load(fh).items()}
    todo = [i for i in allids if i not in res]
    print("todo", len(todo))
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for iid, nm in ex.map(fetch, todo):
            done += 1
            if nm:
                res[iid] = nm
            if done % 30 == 0:
                print("  ", done, "/", len(todo))
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump({str(k): v for k, v in sorted(res.items())}, fh,
                  ensure_ascii=False, indent=0)
    print("got", len(res))


if __name__ == "__main__":
    main()

import io
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "Core", "Data", "Data_ClassQuest.lua")
NAMES = os.path.join(ROOT, "_temp", "_cq_names.json")
OUT = os.path.join(ROOT, "_temp", "_cq_qname_zh.json")
PROXY = "http://127.0.0.1:7897"

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
)


def missing():
    src = io.open(DATA, encoding="utf-8").read()
    start = src.index("ns.ClassQuestInfo = {")
    body = src[start:]
    ids = []
    for m in re.finditer(r"\[(\d+)\] = \{", body):
        qid = int(m.group(1))
        tail = body[m.end():m.end() + 400]
        if "cn =" not in tail.split("},\n")[0]:
            ids.append(qid)
    return ids


def fetch(qid):
    url = ("https://nether.wowhead.com/tooltip/quest/%d?dataEnv=1&locale=zhCN" % qid)
    try:
        with opener.open(url, timeout=20) as r:
            obj = json.loads(r.read().decode("utf-8"))
        nm = obj.get("name")
        if nm and re.search(r"[\u4e00-\u9fff]", nm):
            return qid, nm
    except Exception:
        return qid, None
    return qid, None


def main():
    ids = missing()
    print("missing", len(ids))
    res = {}
    if os.path.exists(OUT):
        with io.open(OUT, encoding="utf-8") as fh:
            res = {int(k): v for k, v in json.load(fh).items()}
    todo = [i for i in ids if i not in res]
    print("todo", len(todo))
    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for qid, nm in ex.map(fetch, todo):
            done += 1
            if nm:
                res[qid] = nm
            if done % 20 == 0:
                print("  ", done, "/", len(todo))
                with io.open(OUT, "w", encoding="utf-8") as fh:
                    json.dump({str(k): v for k, v in sorted(res.items())}, fh,
                              ensure_ascii=False, indent=0)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump({str(k): v for k, v in sorted(res.items())}, fh,
                  ensure_ascii=False, indent=0)
    print("got", len(res))

    names = {}
    if os.path.exists(NAMES):
        with io.open(NAMES, encoding="utf-8") as fh:
            names = json.load(fh)
    add = 0
    for k, v in res.items():
        if names.get(str(k)) != v:
            names[str(k)] = v
            add += 1
    with io.open(NAMES, "w", encoding="utf-8") as fh:
        json.dump(names, fh, ensure_ascii=False, indent=0)
    print("merged", add, "names total", len(names))


if __name__ == "__main__":
    main()

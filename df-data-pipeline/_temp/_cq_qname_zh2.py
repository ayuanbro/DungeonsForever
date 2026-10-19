import io, json, os, re, urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "Core", "Data", "Data_ClassQuest.lua")
NAMES = os.path.join(ROOT, "_temp", "_cq_names.json")
OUT = os.path.join(ROOT, "_temp", "_cq_qname_zh.json")
PROXY = "http://127.0.0.1:7897"
ENVS = [8, 11, 4, 5, 3, 1]

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))


def missing():
    src = io.open(DATA, encoding="utf-8").read()
    ids = []
    for m in re.finditer(r'^\s*\[(\d+)\] = \{ n = "[^"]*", l = ', src, re.M):
        ids.append(int(m.group(1)))
    return ids


def ok(nm):
    if not nm or nm == "未知":
        return False
    if nm.startswith("[") or nm.startswith("|"):
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", nm))


def fetch(qid):
    for env in ENVS:
        url = "https://nether.wowhead.com/tooltip/quest/%d?dataEnv=%d&locale=zhCN" % (qid, env)
        try:
            with opener.open(url, timeout=20) as r:
                obj = json.loads(r.read().decode("utf-8"))
            nm = obj.get("name")
            if ok(nm):
                return qid, nm
        except Exception:
            pass
    return qid, None


ids = missing()
print("missing", len(ids))
res = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    for qid, nm in ex.map(fetch, ids):
        if nm:
            res[qid] = nm
print("got", len(res), "of", len(ids))
for k in sorted(res):
    print("  %6d %s" % (k, res[k]))
left = [i for i in ids if i not in res]
print("left", left)

nn = {}
if os.path.exists(OUT):
    nn = json.load(io.open(OUT, encoding="utf-8"))
for k, v in res.items():
    nn[str(k)] = v
io.open(OUT, "w", encoding="utf-8", newline="\n").write(
    json.dumps(nn, ensure_ascii=False, indent=0, sort_keys=True))

names = {}
if os.path.exists(NAMES):
    names = json.load(io.open(NAMES, encoding="utf-8"))
for k, v in res.items():
    names[str(k)] = v
io.open(NAMES, "w", encoding="utf-8", newline="\n").write(
    json.dumps(names, ensure_ascii=False, indent=0, sort_keys=True))
print("names total", len(names))

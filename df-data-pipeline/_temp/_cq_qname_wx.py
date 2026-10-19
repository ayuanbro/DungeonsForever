import io, json, os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "Core", "Data", "Data_ClassQuest.lua")
NAMES = os.path.join(ROOT, "_temp", "_cq_names.json")

src = io.open(DATA, encoding="utf-8").read()
ids = [int(m.group(1)) for m in re.finditer(r'^\s*\[(\d+)\] = \{ n = "[^"]*", l = ', src, re.M)]
print("missing", len(ids))

names = {}
if os.path.exists(NAMES):
    names = json.load(io.open(NAMES, encoding="utf-8"))

got = {}
for qid in ids:
    try:
        req = urllib.request.Request("https://wuxianwow.com/quest/%d" % qid,
                                     headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=25) as r:
            html = r.read().decode("utf-8", "replace")
        m = re.search(r"<title>(.*?)</title>", html)
        if not m:
            continue
        t = m.group(1).strip()
        t = re.sub(r"\s*#%d\b" % qid, "", t)
        t = re.sub(r"\s*-\s*任务.*$", "", t).strip()
        if t and re.search(r"[\u4e00-\u9fff]", t) and not t.startswith("任务"):
            got[qid] = t
    except Exception:
        pass

print("got", len(got))
for k in sorted(got):
    print("  %6d %s" % (k, got[k]))
for k, v in got.items():
    names[str(k)] = v
io.open(NAMES, "w", encoding="utf-8", newline="\n").write(
    json.dumps(names, ensure_ascii=False, indent=0, sort_keys=True))
print("names total", len(names))

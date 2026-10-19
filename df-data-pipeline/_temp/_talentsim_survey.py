import io, json, re, sys

SRC = r"D:\workspace\TalentsForever\Core\Data\Data_Talents.lua"
DF  = r"D:\workspace\DungeonsForever\Core\Data\Data_ClassTier.lua"

txt = io.open(SRC, encoding="utf-8", errors="replace").read()

classes = {}
for m in re.finditer(r'^    ([A-Z]+) = \{$', txt, re.M):
    classes[m.group(1)] = m.start()

order = list(classes.keys())
out = {}
for idx, cls in enumerate(order):
    start = classes[cls]
    end = classes[order[idx + 1]] if idx + 1 < len(order) else len(txt)
    seg = txt[start:end]
    km = re.search(r'key = "([^"]+)"', seg)
    cm = re.search(r'color = "([^"]+)"', seg)
    trees = []
    for tm in re.finditer(r'\{\s*\n\s*name = "([^"]+)",\s*\n\s*nameEn = "([^"]+)",\s*\n\s*icon = "([^"]+)"', seg):
        trees.append({"name": tm.group(1), "nameEn": tm.group(2), "icon": tm.group(3)})
    tal = seg.split("talents = {")
    counts = []
    for i in range(1, len(tal)):
        chunk = tal[i]
        counts.append(len(re.findall(r'\{\s*name = "', chunk)))
    out[cls] = {"key": km.group(1) if km else None, "color": cm.group(1) if cm else None,
                "trees": trees, "talentCounts": counts}

dftxt = io.open(DF, encoding="utf-8", errors="replace").read()
dfspec = {}
for m in re.finditer(r'^        ([A-Z]+) = \{$', dftxt, re.M):
    cls = m.group(1)
    nxt = re.search(r'^    \},', dftxt[m.end():], re.M)
    body = dftxt[m.end(): m.end() + (nxt.start() if nxt else 4000)]
    specs = re.findall(r'\{ key = "([^"]+)", name = "([^"]+)", nameEn = "([^"]+)"', body)
    dfspec[cls] = specs

report = {"classes": out, "dfSpecs": dfspec}
print(json.dumps(report, ensure_ascii=False, indent=1))

for cls in order:
    c = out[cls]
    trees = c["trees"]
    print(f'{cls:8s} key={c["key"]:9s} trees={len(trees)} counts={c["talentCounts"]}')
    for t in trees:
        print(f'    - {t["name"]} / {t["nameEn"]:22s} icon={t["icon"]}')
    dfs = dfspec.get(cls, [])
    print(f'    DF specs: {[ (s[0], s[2]) for s in dfs ]}')
    print()

total = sum(sum(c["talentCounts"]) for c in out.values())
print("TOTAL talents:", total)

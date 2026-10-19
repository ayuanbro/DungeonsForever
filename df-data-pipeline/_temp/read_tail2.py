import re
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"memMarks"')
j = txt.find("\n}", i)
seg = txt[i:j]
pat = re.compile(r'\["t"\]\s*=\s*"([^"]*)"\s*,\s*\["heap"\]\s*=\s*([\d.]+)\s*,\s*\["label"\]\s*=\s*"([^"]*)"|'
                 r'\["t"\]\s*=\s*"([^"]*)"\s*,\s*\["label"\]\s*=\s*"([^"]*)"\s*,\s*\["heap"\]\s*=\s*([\d.]+)')
recs = []
for m in pat.finditer(seg):
    if m.group(1):
        recs.append((m.group(1), m.group(3), float(m.group(2))))
    else:
        recs.append((m.group(4), m.group(5), float(m.group(6))))
for t, l, h in recs[-28:]:
    print(f"{t}  {l:14s}  {h/1024:8.2f} MB")
if not recs:
    print("PARSE FAIL")

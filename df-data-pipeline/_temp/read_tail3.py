sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"memMarks"')
j = txt.find("\n}", i)
seg = txt[i:j]
recs = []
for chunk in seg.split("},"):
    t = hl = lb = None
    for part in chunk.replace("\r", "").split("\n"):
        part = part.strip()
        if part.startswith('["t"]'):
            t = part.split('"')[1]
        elif part.startswith('["heap"]'):
            try: hl = float(part.split("= ")[1])
            except: pass
        elif part.startswith('["label"]'):
            lb = part.split('"')[1]
    if t and lb and hl:
        recs.append((t, lb, hl))
for t, l, h in recs[-30:]:
    print(f"{t}  {l:14s}  {h/1024:8.2f} MB")
print("total parsed:", len(recs))

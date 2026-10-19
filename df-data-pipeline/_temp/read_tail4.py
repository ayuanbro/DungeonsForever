sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read().replace(b"\r\n", b"\n").decode("utf-8", "replace")
print("has dfMemProbe:", '"dfMemProbe"' in data)
print("has dfPbLog:", '"dfPbLog"' in data)
print("has gearOpen:", '"gearOpen"' in data)
print("has gearData:", '"gearData"' in data)
i = data.find('"memMarks"')
j = data.find("\n}", i)
seg = data[i:j]
recs = []
for chunk in seg.split("},"):
    t = hl = lb = None
    for line in chunk.split("\n"):
        line = line.strip().rstrip(",")
        if line.startswith('["t"]'):
            t = line.split('"')[1]
        elif line.startswith('["heap"]'):
            hl = float(line.split("= ")[1])
        elif line.startswith('["label"]'):
            lb = line.split('"')[1]
    if t and lb is not None and hl:
        recs.append((t, lb, hl))
for t, l, h in recs[-32:]:
    print(f"{t}  {l:14s}  {h/1024:8.2f} MB")
print("parsed:", len(recs))

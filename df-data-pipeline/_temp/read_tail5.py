sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read().replace(b"\r\n", b"\n").decode("utf-8", "replace")
for lb in ("gearData", "catalog", "gearSkel", "profData", "gearOpen", "pb_Raids", "pb_PvP"):
    print(lb, data.count('"' + lb + '"'))
i = data.find('"memMarks"')
j = i
while True:
    j = data.find("\n}", j + 1)
    if j < 0 or data[j+2:j+3] != ",":
        break
seg = data[i:j]
recs = []
for chunk in seg.split("},"):
    t = hl = lb2 = None
    for line in chunk.split("\n"):
        line = line.strip().rstrip(",")
        if line.startswith('["t"]'):
            t = line.split('"')[1]
        elif line.startswith('["heap"]'):
            hl = float(line.split("= ")[1])
        elif line.startswith('["label"]'):
            lb2 = line.split('"')[1]
    if t and lb2 is not None and hl:
        recs.append((t, lb2, hl))
print("parsed:", len(recs))
for t, l, h in recs[-32:]:
    print(f"{t}  {l:14s}  {h/1024:8.2f} MB")

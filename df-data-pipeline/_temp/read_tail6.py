sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
data = open(sv, "rb").read().replace(b"\r\n", b"\n").decode("utf-8", "replace")
i = data.find('"memMarks"')
j = i
while True:
    j = data.find("\n}", j + 1)
    if j < 0 or data[j+2:j+3] != ",":
        break
seg = data[i:j]
recs = []
for chunk in seg.split("},"):
    t = hl = lb = None
    for line in chunk.split("\n"):
        line = line.strip().rstrip(",")
        if line.startswith('["t"]'):
            t = line.split('"')[3]
        elif line.startswith('["heap"]'):
            hl = float(line.split("= ")[1])
        elif line.startswith('["label"]'):
            lb = line.split('"')[3]
    if t and lb is not None and hl:
        recs.append((t, lb, hl))
print("parsed:", len(recs))
for t, l, h in recs[-30:]:
    print(f"{t}  {l:14s}  {h/1024:8.2f} MB")

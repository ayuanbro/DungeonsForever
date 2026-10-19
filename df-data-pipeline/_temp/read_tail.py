import re
sv = "D:/Game/World of Warcraft/_classic_beta_/WTF/Account/84254230#1/SavedVariables/DungeonsForever.lua"
txt = open(sv, encoding="utf-8", errors="replace").read()
i = txt.find('"memMarks"')
j = txt.find("\n}", i)
seg = txt[i:j]
marks = re.findall(r'\{\s*\["t"\] = "([^"]*)",\s*\["heap"\] = ([\d.]+),\s*\["label"\] = "([^"]*)",\s*\}', seg)
marks2 = re.findall(r'\{\s*\["t"\] = "([^"]*)",\s*\["label"\] = "([^"]*)",\s*\["heap"\] = ([\d.]+),\s*\}', seg)
out = marks or marks2
for t, h, l in out[-30:]:
    print(f"{t}  {l:14s}  {float(h)/1024:8.2f} MB")
if not out:
    print("PARSE FAIL"); print(seg[-800:])

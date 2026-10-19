import os, sys
ROOT = r"D:\workspace\DungeonsForever"
OLDS = [
    "D:/Game/World of Warcraft/_classic_titan_/Interface/AddOns/DungeonsForever",
    "D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\DungeonsForever",
]
NEWS = ["D:/workspace/DungeonsForever", "D:\workspace\DungeonsForever"]
changed, leftover = [], set()
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
    for fn in filenames:
        if not fn.endswith((".py", ".md", ".txt", ".bat", ".json")):
            continue
        p = os.path.join(dirpath, fn)
        if p == os.path.join(ROOT, "_temp", "_relocate_paths.py"):
            continue
        with open(p, "rb") as f:
            b = f.read()
        orig = b
        for o, n in zip(OLDS, NEWS):
            b = b.replace(o.encode(), n.encode())
        if b != orig:
            with open(p, "wb") as f:
                f.write(b)
            changed.append(os.path.relpath(p, ROOT))
        if b"_classic_titan_" in b:
            leftover.add(os.path.relpath(p, ROOT))
print("CHANGED:", len(changed))
for c in changed:
    print("  ", c)
print("LEFTOVER _classic_titan_ refs (上游 TalentsForever 等):")
for c in sorted(leftover):
    print("  ", c)

import ast, io, os

ROOT = r"D:/workspace/DungeonsForever"
SRC = io.open(os.path.join(ROOT, "_temp", "df_mut_check.py"), encoding="utf-8").read()
tree = ast.parse(SRC)
cache = {}
bad = []
total = 0
for node in tree.body:
    if not isinstance(node, ast.Assign):
        continue
    if not isinstance(node.targets[0], ast.Name):
        continue
    name = node.targets[0].id
    if not name.startswith("MUT_"):
        continue
    try:
        val = ast.literal_eval(node.value)
    except Exception:
        continue
    if not (isinstance(val, tuple) and len(val) == 2):
        continue
    path, pair = val
    if not (isinstance(pair, tuple) and len(pair) == 2):
        continue
    old, new = pair
    if not isinstance(old, bytes):
        continue
    total += 1
    p = os.path.join(ROOT, path)
    if p not in cache:
        cache[p] = io.open(p, "rb").read()
    n = cache[p].count(old)
    if n != 1:
        bad.append((name, path, n, old.decode("utf-8", "replace").strip()[:90]))

print("变异锚点总数 =", total, "| 非唯一/失配 =", len(bad))
for name, path, n, txt in bad:
    print("  [%d 次] %s | %s | %s" % (n, name, path, txt))

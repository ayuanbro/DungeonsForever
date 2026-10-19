import os, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("dfm", os.path.join(ROOT, "_temp", "df_mut_check.py"))
dfm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dfm)

bad = []
for name, sp in dfm.MUTATIONS:
    fname, old, new = dfm.split_spec(sp)
    p = os.path.join(ROOT, fname.replace('/', os.sep))
    data = open(p, 'rb').read()
    if b'\r\n' in data and data.count(b'\n') == data.count(b'\r\n'):
        old, new = old.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'), new.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    n = data.count(old)
    if n != 1:
        bad.append((name, fname, n, old[:100]))
print("total:", len(dfm.MUTATIONS), " bad:", len(bad))
for name, fname, n, old in bad:
    print(f"[{n}] {fname} | {name} | anchor: {old!r}")

import os, re, sys

def stat(path):
    with open(path, 'rb') as f:
        raw = f.read()
    txt = raw.decode('utf-8', 'replace')
    lines = txt.splitlines()
    total = len(lines)
    blank = cmt_only = tail_cmt = code = 0
    in_long = False
    for ln in lines:
        s = ln.strip()
        if in_long:
            cmt_only += 1
            if ']]' in s:
                in_long = False
            continue
        if not s:
            blank += 1
            continue
        if s.startswith('--'):
            cmt_only += 1
            if re.match(r'^--\[=*\[', s) and not re.search(r'\]\]=*$', s):
                in_long = True
            continue
        code += 1
        # trailing comment: strip strings roughly
        t = re.sub(r'"(\\.|[^"\\])*"', '""', ln)
        t = re.sub(r"'(\\.|[^'\\])*'", "''", t)
        if '--' in t:
            tail_cmt += 1
    return dict(total=total, blank=blank, cmt=cmt_only, code=code, tail=tail_cmt)

root = sys.argv[1]
rows = []
tot = dict(total=0, blank=0, cmt=0, code=0, tail=0)
for dp, dn, fn in os.walk(root):
    if 'Libs' in dp or '.git' in dp or '.workbuddy' in dp:
        continue
    for f in sorted(fn):
        if f.endswith('.lua'):
            p = os.path.join(dp, f)
            st = stat(p)
            rows.append((p, st))
            for k in tot:
                tot[k] += st[k]
for p, st in sorted(rows, key=lambda x: -x[1]['cmt']):
    print("%6d cmt | %5d tail | %6d code | %5d blank | %6d total | %s" % (
        st['cmt'], st['tail'], st['code'], st['blank'], st['total'], p))
print("---")
print("TOTAL cmt=%d tail=%d code=%d blank=%d total=%d" % (tot['cmt'], tot['tail'], tot['code'], tot['blank'], tot['total']))

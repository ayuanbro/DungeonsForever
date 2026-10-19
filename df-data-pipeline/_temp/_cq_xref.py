import io, re, os, glob, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ids = [89931,211022,211033,244808,246152,246349,246378,246393,248755,248840,251166,251361,251373,251374,251376,251379,251389,251507,251964,252359,252373,252377,252382,252389,254082,254084,254411,255853,256507,257446,257597,257648,257655,257663,257808,258043,258098,258113,258203,258785,258930,259023,259118,259611,259620,259649,262560,266847,268592,270459,272054,409289,409311,409315,410369,566037,619896,656157]
hits = {}
for path in glob.glob(os.path.join(ROOT,'Core','Data','**','*.lua'), recursive=True):
    try:
        s = io.open(path, encoding='utf-8', errors='ignore').read()
    except Exception:
        continue
    for nid in ids:
        for m in re.finditer(r'\[\s*%d\s*\]\s*=\s*\{' % nid, s):
            seg = s[m.end(): m.end()+160]
            nm = re.search(r'"([^"]*[\u4e00-\u9fff][^"]*)"', seg)
            if nm:
                hits.setdefault(nid, []).append((os.path.relpath(path, ROOT), nm.group(1)))
for nid in ids:
    print(nid, hits.get(nid, '--'))

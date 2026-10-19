import io, re, json

txt = io.open(r"D:\workspace\TalentsForever\Core\Data\Data_Talents.lua", encoding="utf-8").read()

pos = {m.group(1): m.start() for m in re.finditer(r'^    ([A-Z]+) = \{$', txt, re.M)}
order = [m.group(1) for m in re.finditer(r'^    ([A-Z]+) = \{$', txt, re.M)]

def cls_seg(cls):
    i = order.index(cls)
    s = pos[cls]
    e = pos[order[i + 1]] if i + 1 < len(order) else len(txt)
    return txt[s:e]

def trees_of(cls):
    seg = cls_seg(cls)
    parts = seg.split("talents = {")
    heads = re.findall(r'\{\s*\n\s*name = "([^"]+)",\s*\n\s*nameEn = "([^"]+)",\s*\n\s*icon = "([^"]+)"', seg)
    out = []
    for idx, h in enumerate(heads):
        body = parts[idx + 1] if idx + 1 < len(parts) else ""
        nodes = []
        pattern = (r'\{\s*name = "([^"]*)", max = (\d+), row = (\d+), col = (\d+), icon = "([^"]+)"'
                   r'[^}]*?status = "([^"]+)"[^}]*?desc = \{(.*?)\}\s*\}')
        for m in re.finditer(pattern, body, re.S):
            descs = re.findall(r'"([^"]*)"', m.group(7))
            req = re.search(r'req = (\d+)', m.group(0))
            nodes.append({
                "name": m.group(1), "max": int(m.group(2)),
                "row": int(m.group(3)), "col": int(m.group(4)),
                "icon": m.group(5), "status": m.group(6),
                "req": int(req.group(1)) if req else None,
                "desc": descs,
            })
        out.append({"name": h[0], "nameEn": h[1], "icon": h[2], "nodes": nodes})
    return out

data = {}
for cls in order:
    seg = cls_seg(cls)
    data[cls] = {
        "key": re.search(r'key = "([^"]+)"', seg).group(1),
        "color": re.search(r'color = "([^"]+)"', seg).group(1),
        "trees": trees_of(cls),
    }

payload = json.dumps(data, ensure_ascii=True)

tot = 0
for cls in order:
    counts = [len(t["nodes"]) for t in data[cls]["trees"]]
    tot += sum(counts)
print("TOTAL", tot)
print("__JSON__")
print(payload)

import json, io, re, html

RAW = r"D:/workspace/DungeonsForever/_temp/_cq_comments_raw.json"
OUT = r"D:/workspace/DungeonsForever/_temp/_cq_comments_clean.json"

d = json.load(io.open(RAW, encoding="utf-8"))


def clean(s):
    s = html.unescape(s or "")
    s = re.sub(r"\[.*?\]", "", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


out = {}
for qid, v in d.items():
    cs = v.get("comments") or []
    items = []
    for c in cs:
        body = clean(c.get("body"))
        if len(body) < 8:
            continue
        rep = []
        for r in c.get("replies") or []:
            rb = clean(r.get("body"))
            if len(rb) >= 8:
                rep.append({"b": rb, "r": r.get("rating", 0)})
        items.append({"b": body, "r": c.get("rating", 0), "rep": rep[:3]})
    items.sort(key=lambda x: -x["r"])
    if items:
        out[qid] = {"t": v.get("title", ""), "c": items[:6]}

json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print("tasks with usable comments:", len(out))

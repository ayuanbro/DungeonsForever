import base64
import json
import re
from collections import Counter

import cbor2

TOC = r"D:\workspace\DungeonsForever\_temp\questie\forever\QuestieDB\QuestieDB_Forever.toc"
pat = re.compile(r"^## X-(Item|Quest|Npc|Object)-(\d+)(-[A-Za-z0-9]+)?:\s*(\S+)\s*$", re.M)


def main():
    txt = open(TOC, encoding="utf-8", errors="replace").read()
    flags = {}
    scalar_keys = Counter()
    for m in pat.finditer(txt):
        ent, eid, suffix, val = m.group(1), int(m.group(2)), m.group(3) or "", m.group(4)
        if ent != "Quest":
            continue
        if suffix.startswith("-S"):
            try:
                row = cbor2.loads(base64.b64decode(val))
            except Exception:
                continue
            if isinstance(row, dict):
                norm = {}
                for k, v in row.items():
                    if isinstance(k, bytes):
                        try:
                            k = int(k)
                        except Exception:
                            k = k.decode("utf-8", "replace")
                    norm[k] = v
                    scalar_keys[str(k)] += 1
                if isinstance(norm.get(23), int):
                    flags[eid] = norm[23]
    print("scalar field keys seen:", sorted(scalar_keys.items())[:40])
    print("quests with flags:", len(flags))
    print("flag values:", Counter(flags.values()).most_common(20))
    bit_counts = Counter()
    for v in flags.values():
        for b in range(0, 24):
            if v & (1 << b):
                bit_counts[b] += 1
    print("bit counts:", sorted(bit_counts.items()))
    # 抽样：已知可共享 / 不可共享
    samples = [97288, 5722, 96393, 166, 1013, 914, 1486]
    for s in samples:
        print(" quest", s, "flags=", flags.get(s))
    json.dump({str(k): v for k, v in flags.items()},
              open(r"D:\workspace\DungeonsForever\_temp\_probe_quest_flags.json", "w", encoding="utf-8"))


if __name__ == "__main__":
    main()

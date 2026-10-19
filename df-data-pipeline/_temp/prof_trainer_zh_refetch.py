# -*- coding: utf-8 -*-
"""重抓 zh=NPC 脏数据的 57 个 NPC ID（低并发防限流），增量合并 _trainers_zh.json。"""
import json
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROXY = 'http://127.0.0.1:7897'
OUT = os.path.join(HERE, '_trainers_zh.json')

ids = json.load(open(os.path.join(HERE, '_trainers_bad_ids.json'), encoding='utf-8'))
db = json.load(open(OUT, encoding='utf-8'))

pat = re.compile(r'^#\s+(.+)$', re.M)


def fetch(eid):
    url = 'https://r.jina.ai/https://cn.wowhead.com/npc=%d' % eid
    for _ in range(2):
        try:
            r = subprocess.run(['curl', '-s', '-x', PROXY, url, '--max-time', '30'],
                               capture_output=True, text=True, timeout=40)
            m = pat.search(r.stdout or '')
            if m:
                t = m.group(1).strip()
                if t and 'http' not in t and 'URL Source' not in t and len(t) <= 30:
                    return eid, t
        except Exception:
            pass
        time.sleep(8)
    return eid, None


todo = [e for e in ids if str(e) not in db or db.get(str(e)) in (None, 'NPC')]
print('todo:', len(todo))
done = 0
for i in range(0, len(todo), 3):
    batch = todo[i:i + 3]
    import threading
    res = [None] * len(batch)

    def work(j, eid):
        res[j] = fetch(eid)

    ths = [threading.Thread(target=work, args=(j, e)) for j, e in enumerate(batch)]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    for j, r0 in enumerate(res):
        if r0 and r0[1]:
            db[str(r0[0])] = r0[1]
            done += 1
    json.dump(db, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print('progress %d/%d' % (min(i + 3, len(todo)), len(todo)), flush=True)
    time.sleep(6)
print('fixed:', done)

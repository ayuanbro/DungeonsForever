import re, glob
for f in glob.glob('_fc_bis/cache/*.html'):
    h = open(f, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'<a href="(/zh-cn/dungeons/[a-z0-9-]+[^"]*)">(任务：[^<]+)</a><span>([^<]*)</span>', h):
        print(f.split('/')[-1], '|', m.group(1), '|', m.group(2), '|', m.group(3))
        break
    # 任务型 boss 锚点
    q = re.search(r'<a href="(/zh-cn/dungeons/[a-z0-9-]+/quest[^"]*)">([^<]+)</a>', h)
    if q: print(f, 'QUEST-ANCHOR:', q.group(1), '|', q.group(2))
    # dungeons 锚点形态分布
    forms = set(re.sub(r'[a-z0-9-]+(?=#)', 'S', x) for x in re.findall(r'/zh-cn/dungeons/[a-z0-9-]+#[a-z0-9=]+', h))
    if f.endswith('warrior.html'):
        print('ANCHOR FORMS:', sorted(forms)[:10])

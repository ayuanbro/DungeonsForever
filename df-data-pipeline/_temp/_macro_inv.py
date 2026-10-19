# -*- coding: utf-8 -*-
import re, sys, glob, os
sys.stdout.reconfigure(encoding='utf-8')
print('--- 职业索引页里的宏指南链接 ---')
for f in ('_temp/_macro_probe2/druid_feral_legacy.html','_temp/_macro_probe2/priest_dps_legacy.html','_temp/_macro_probe2/shaman_dps_legacy.html','_temp/_macro_probe2/warrior_dps_legacy.html','_temp/_macro_probe/shub.html' if False else '_temp/_macro_probe/hub.html'):
    h = open(f, encoding='utf-8', errors='replace').read()
    hits = sorted(set(re.findall(r'href="(/(?:classic|tbc)/guide/classes/[^"]*macros[^"]*)"', h)))
    hits += sorted(set(re.findall(r'href="(/(?:classic|tbc)/guides/[^"]*macros[^"]*)"', h)))
    print(os.path.basename(f), '->', len(hits))
    for x in hits: print('    ', x)
print()
print('--- CN 版正文是否中文 ---')
def zh_ratio(s):
    return sum(1 for ch in s if '\u4e00' <= ch <= '\u9fff')
for pair in (('rogue_dps.html','_temp/_macro_probe2/rogue_dps_cn.html'),):
    a = open('_temp/_macro_pages/'+pair[0], encoding='utf-8', errors='replace').read()
    b = open(pair[1], encoding='utf-8', errors='replace').read()
    print('EN page CJK chars:', zh_ratio(a), '| CN page CJK chars:', zh_ratio(b))
    # sample heading text from CN page
    for m in list(re.finditer(r'<h3[^>]*class="heading-size-3"[^>]*>(.*?)</h3>', b, re.S))[:8]:
        print('   CN h3:', ' '.join(re.sub(r'<[^>]+>',' ',m.group(1)).split())[:60])

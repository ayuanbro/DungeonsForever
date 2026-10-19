# -*- coding: utf-8 -*-
import re, json, sys, html as H

def strip(t):
    t = re.sub(r'<script.*?</script>', ' ', t, flags=re.S)
    t = re.sub(r'<style.*?</style>', ' ', t, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = H.unescape(t)
    return re.sub(r'[ \t\r\f\v]+', ' ', t)

for tag in ['item280456', 'quest93176']:
    raw = open(f'_temp/_pet_weevil/{tag}.html', encoding='utf-8').read()
    print('=' * 100)
    print('###', tag, len(raw))
    m = re.search(r'<title>(.*?)</title>', raw, re.S)
    print('TITLE:', H.unescape(m.group(1).strip()) if m else None)

    # printHtml payload
    loads = re.findall(r'WH\.markup\.printHtml\(\s*("(?:[^"\\]|\\.)*")', raw)
    print('printHtml blocks:', len(loads))
    for i, r0 in enumerate(loads):
        try:
            txt = json.loads(r0)
        except Exception as e:
            print('  json err', e); continue
        print(f'--- block {i} len={len(txt)} ---')
        print(txt[:5000])

    # gatherer quest/item structured data
    print('--- tooltip / infobox ---')
    for pat in [r'<div id="infobox".*?(?=<div id=")', r'id="main-contents".{0,20000}']:
        mm = re.search(pat, raw, re.S)
        if mm:
            print(strip(mm.group(0))[:2500])
            break

    # objectives list
    print('--- objectives-ish (collect/slay text) ---')
    for mt in re.finditer(r'(?i)(树栖狼蛛|剔肉蝎|干草象鼻虫|树桩|科多兽坟场|风险投资公司|藏宝海湾|斯通纳德|阿拉希)', raw):
        i = mt.start()
        seg = strip(raw[max(0, i - 300):i + 300])
        print(f'  [{mt.group(0)}] …{seg.strip()[:280]}')

    # comments
    print('--- comments ---')
    for mt in re.finditer(r'(?i)comment', raw):
        pass
    cmts = re.findall(r'<div class="comment-body[^"]*"[^>]*>(.*?)</div>', raw, re.S)
    print('comment blocks:', len(cmts))
    for i, c in enumerate(cmts[:12]):
        print(f'  #{i}:', strip(c)[:600])

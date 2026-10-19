# -*- coding: utf-8 -*-
"""下载 foreverchanges.pro 的全部 CSS chunk，抽取所有选择器含 pvr- 的规则，
落成 _site_pvr_css.json（selector -> declarations）。终端只打一行摘要。"""
import io, re, json, sys, urllib.request

BASE = 'https://foreverchanges.pro'
SCAN = r'D:/workspace/DungeonsForever/_temp/_site_scan.json'
OUT = r'D:/workspace/DungeonsForever/_temp/_site_pvr_css.json'

scan = json.load(io.open(SCAN, encoding='utf-8'))
links = scan['css_links']
assert isinstance(links, list) and links, links

ua = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
css_all = []
fetched = 0
for u in links:
    url = u if u.startswith('http') else BASE + u
    try:
        req = urllib.request.Request(url, headers=ua)
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read().decode('utf-8', errors='replace')
        css_all.append(body)
        fetched += 1
    except Exception as e:  # noqa: BLE001 - 记录失败继续
        css_all.append('')

css = '\n'.join(css_all)

# 抽取规则：非贪婪匹配 selector{body}，过滤含 pvr- 的
rules = {}
for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
    sel, body = m.group(1).strip(), m.group(2).strip()
    if 'pvr' in sel and body:
        key = ' '.join(sel.split())[:120]
        val = ' '.join(body.split())
        rules[key] = (rules.get(key, '') + ' ; ' + val)[:600]

media_pvr = len(re.findall(r'@media[^{]*\{[^@]*?pvr', css))

data = {
    'fetched': fetched,
    'total_links': len(links),
    'css_bytes': len(css),
    'pvr_rules': rules,
    'pvr_rule_count': len(rules),
    'media_hits': media_pvr,
}
with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print('CSS-OK fetched=%d/%d bytes=%d pvr_rules=%d' % (
    fetched, len(links), len(css), len(rules)))

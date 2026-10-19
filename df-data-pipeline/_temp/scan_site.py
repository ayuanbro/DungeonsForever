# -*- coding: utf-8 -*-
"""扫描已下载的 foreverchanges.pro PvP 军衔页 HTML：
1) CSS 外链清单  2) 内联 style 块  3) 实际使用的 pvr-* 类名
4) 军衔表首行原始 HTML 片段  5) 周上限(pvr-weeks)块原始片段
结果写 _site_scan.json；终端只打一行 OK 摘要。"""
import io, re, os, json

SRC = r'C:/Users/Administrator/AppData/Local/Temp/pvpranks.html'
OUT = r'D:/workspace/DungeonsForever/_temp/_site_scan.json'

raw = io.open(SRC, encoding='utf-8', errors='replace').read()
size = len(raw)
assert size > 400000, size

# 1) CSS 外链
link_hrefs = re.findall(r'<link[^>]+href="([^"]+)"', raw)
css_links = [u for u in link_hrefs if '.css' in u]

# 2) 内联样式块
style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', raw, re.S)

# 3) 实际用到的 class（pvr- 前缀）
used = set()
for m in re.findall(r'class="([^"]+)"', raw):
    used.update(m.split())
pvr_classes = sorted(c for c in used if c.startswith('pvr'))

# 4) 军衔表首行片段（tr id="rank-1" 起到该行结束）
i = raw.find('id="rank-1"')
if i > -1:
    start = raw.rfind('<tr', 0, i)
    end = raw.find('</tr>', i)
    rank_row_html = raw[start:end + 5]
else:
    rank_row_html = ''

# 5) pvr-weeks 块片段
j = raw.find('pvr-weeks')
weeks_html = raw[max(0, j - 200): j + 2600] if j > -1 else ''

data = {
    'src': SRC,
    'size': size,
    'css_links': css_links,
    'inline_style_count': len(style_blocks),
    'inline_style_total_len': sum(len(b) for b in style_blocks),
    'pvr_class_count': len(pvr_classes),
    'pvr_classes': pvr_classes,
    'rank_row_html': rank_row_html[:4000],
    'weeks_html': weeks_html[:4000],
}
with io.open(OUT, 'w', encoding='utf-8', newline='') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print('SCAN-OK size=%d css=%d inline=%d pvr=%d rankrow=%d weeks=%d' % (
    size, len(css_links), len(style_blocks), len(pvr_classes),
    len(rank_row_html), len(weeks_html)))

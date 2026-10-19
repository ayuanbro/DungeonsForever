# -*- coding: utf-8 -*-
"""从抓下来的新闻页里抽正文（去 HTML 标签 + 实体）。"""
import os, re, html

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "_ref_pets")

def strip_tags(s):
    s = re.sub(r"<script.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>|</div>|</li>|</h[1-6]>|</tr>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\u00a0]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

for k in ("capitals", "gustjumper"):
    p = os.path.join(REF, "wh_%s_cn.html" % k)
    raw = open(p, encoding="utf-8").read()
    i = raw.find('news-post-content')
    j = raw.find('news-post-footer', i)
    if j < 0:
        j = raw.find('comments', i)
    seg = raw[i:j] if i >= 0 and j > i else raw
    txt = strip_tags(seg)
    out = os.path.join(REF, "_pets_%s.txt" % k)
    open(out, "w", encoding="utf-8").write(txt)
    print("=" * 70)
    print(k, "len=", len(txt))
    print(txt)

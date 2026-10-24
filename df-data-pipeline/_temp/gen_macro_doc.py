# -*- coding: utf-8 -*-
"""由 _temp/_macro_data.json 生成「全职业专精宏命令」HTML 查看页 + Markdown 镜像。"""
import html as H
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

CLS_COLOR = {
    '战士': '#C79C6E', '圣骑士': '#F58CBA', '猎人': '#ABD473', '潜行者': '#FFF569',
    '牧师': '#FFFFFF', '萨满': '#0070DE', '法师': '#69CCF0', '术士': '#9482C9',
    '德鲁伊': '#FF7D0A',
}
CLS_DARK = {'牧师': '#8a8f98', '潜行者': '#b9ad2e'}

GAPS = [
    ('战士', '武器 / 狂暴（输出）', 'wowhead Classic 无独立宏指南（同路径会跳到 TBC 版，含 TBC 专属技能，不适用于 60 级）'),
    ('圣骑士', '防护（坦克）', '同上，只有 TBC 版防护骑宏指南'),
    ('牧师', '暗影（输出）', 'wowhead Classic 只做了治疗牧宏指南'),
    ('萨满', '元素 / 增强（输出）', 'wowhead Classic 只做了恢复萨宏指南'),
    ('德鲁伊', '平衡 / 野性（猫德、熊坦）', 'wowhead Classic 只做了恢复德宏指南'),
]


def merge(cn, en):
    """CN 为主；补齐 EN 独有条目（标题去重）。"""
    titles = {x['title'] for x in cn}
    extra = []
    for e in en:
        if e['title'] not in titles:
            e2 = dict(e)
            e2['en_only'] = True
            extra.append(e2)
            titles.add(e['title'])
    return cn, extra


def md_out(data, path):
    L = ['# WoW Classic 全职业专精宏命令合集', '',
         '> 数据来源：wowhead（Classic 职业宏指南）。宏代码原样保留；说明文字取自 wowhead 原文（其中专有名词按 wowhead 中文页的本地化结果呈现，正文其余部分仍为英文原文）。', '']
    total = 0
    for it in data:
        cn, extra = merge(it['cn'], it['en'])
        total += len(cn) + len(extra)
        L.append('## %s · %s' % (it['cls'], it['spec']))
        L.append('')
        L.append('*来源页：`%s`*' % it['key'])
        L.append('')
        for e in cn + extra:
            tag = '（英文版独有）' if e.get('en_only') else ''
            L.append('### %s%s' % (e['title'], tag))
            if e['section']:
                L.append('')
                L.append('分类：%s' % e['section'])
            L.append('')
            for c in e['codes']:
                L.append('```')
                L.append(c)
                L.append('```')
                L.append('')
            if e['desc']:
                L.append(e['desc'])
                L.append('')
    L += ['## 未覆盖的专精（wowhead 无 Classic 宏指南）', '']
    for cls, spec, why in GAPS:
        L.append('- **%s · %s**：%s' % (cls, spec, why))
    L.append('')
    open(path, 'w', encoding='utf-8').write('\n'.join(L))
    return total


def html_out(data, path):
    P = []
    P.append('<div class="wrap">')
    P.append('<header><h1>WoW Classic 全职业专精宏命令合集</h1>'
             '<p class="sub">共 <b>%d</b> 个宏 · <b>%d</b> 个职业宏指南 · 抓取日期 2026-10-17 · 数据来源：wowhead</p></header>'
             % (sum(sum(len(x['codes']) for x in it['cn']) for it in data),
                len(data)))
    P.append('<nav class="chips">')
    for it in data:
        P.append('<a class="chip" style="--c:%s" href="#k_%s">%s<i>%s</i></a>'
                 % (CLS_COLOR.get(it['cls'], '#888'), it['key'], it['cls'], it['spec']))
    P.append('<a class="chip chip-gap" href="#gap">未覆盖专精</a>')
    P.append('</nav>')

    for it in data:
        cn, extra = merge(it['cn'], it['en'])
        c = CLS_COLOR.get(it['cls'], '#888')
        P.append('<section class="cls" id="k_%s" style="--c:%s">' % (it['key'], c))
        P.append('<h2><span class="dot"></span>%s <small>%s</small>'
                 '<em>%d 个宏</em></h2>' % (it['cls'], it['spec'], sum(len(x['codes']) for x in cn + extra)))
        P.append('<div class="cards">')
        for e in cn + extra:
            P.append('<article class="card">')
            P.append('<h3>%s%s</h3>' % (H.escape(e['title']),
                     ' <span class="tag-en">EN 独有</span>' if e.get('en_only') else ''))
            if e['section']:
                P.append('<div class="sec">%s</div>' % H.escape(e['section']))
            for c_i, code in enumerate(e['codes']):
                P.append('<div class="codebox"><button class="copy" type="button">复制</button>'
                         '<pre data-code="%d">%s</pre></div>'
                         % (c_i, H.escape(code)))
            if e['desc']:
                P.append('<p class="desc">%s</p>' % H.escape(e['desc']))
            P.append('</article>')
        P.append('</div></section>')

    P.append('<section class="cls gap" id="gap" style="--c:#8b8f96">')
    P.append('<h2><span class="dot"></span>未覆盖的专精<small>wowhead 无 Classic 宏指南</small></h2>')
    P.append('<ul class="gaplist">')
    for cls, spec, why in GAPS:
        P.append('<li><b style="color:%s">%s · %s</b><span>%s</span></li>'
                 % (CLS_DARK.get(cls, CLS_COLOR.get(cls, '#666')), cls, spec, H.escape(why)))
    P.append('</ul></section>')
    P.append('<footer>本页为本地参考文档 · 宏代码与说明取自 wowhead Classic 职业宏指南 · 抓取于 2026-10-17</footer>')
    P.append('</div>')

    body = '\n'.join(P)
    doc = HTML_TMPL.replace('<!--BODY-->', body)
    open(path, 'w', encoding='utf-8').write(doc)


HTML_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WoW Classic 全职业专精宏命令合集</title>
<style>
:root{--bg:#f5f6f8;--panel:#fff;--line:#e3e6ea;--tx:#1f2328;--dim:#5b6167;--mono:"Cascadia Mono",Consolas,"Courier New",monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 "Microsoft YaHei","Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
header h1{margin:0 0 6px;font-size:26px;letter-spacing:.5px}
header .sub{margin:0;color:var(--dim);font-size:13px}
nav.chips{position:sticky;top:0;z-index:9;display:flex;flex-wrap:wrap;gap:8px;padding:12px 0;margin:0 0 18px;
  background:linear-gradient(var(--bg) 70%,rgba(245,246,248,.85));border-bottom:1px solid var(--line)}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border:1px solid var(--line);border-radius:999px;
  background:var(--panel);color:var(--tx);text-decoration:none;font-size:13px;box-shadow:0 1px 1px rgba(0,0,0,.03)}
.chip b{display:none}
.chip i{font-style:normal;color:var(--dim);font-size:11px}
.chip:hover{border-color:var(--c);box-shadow:0 2px 6px rgba(0,0,0,.06)}
.chip::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--c)}
.chip-gap{color:var(--dim)}
.cls{margin:0 0 34px}
.cls h2{display:flex;align-items:center;gap:9px;margin:0 0 14px;font-size:20px;border-left:4px solid var(--c);padding-left:10px}
.cls h2 .dot{width:10px;height:10px;border-radius:50%;background:var(--c);display:none}
.cls h2 small{font-weight:400;color:var(--dim);font-size:13px}
.cls h2 em{margin-left:auto;font-style:normal;font-size:12px;color:var(--dim);background:var(--panel);
  border:1px solid var(--line);border-radius:999px;padding:2px 10px}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 15px 13px;
  box-shadow:0 1px 2px rgba(0,0,0,.03);display:flex;flex-direction:column}
.card h3{margin:0 0 6px;font-size:15.5px;line-height:1.4}
.card .sec{display:inline-block;font-size:11px;color:var(--dim);border:1px solid var(--line);
  border-radius:4px;padding:1px 6px;margin:0 0 9px;align-self:flex-start}
.codebox{position:relative;margin:0 0 9px}
.codebox pre{margin:0;background:#f2f4f7;border:1px solid #e6e9ee;border-left:3px solid var(--c);border-radius:6px;
  padding:10px 66px 10px 12px;font:13px/1.55 var(--mono);white-space:pre-wrap;word-break:break-word;color:#20242a}
.copy{position:absolute;top:7px;right:7px;font-size:11px;padding:3px 9px;border:1px solid #d3d8de;border-radius:5px;
  background:#fff;color:var(--dim);cursor:pointer}
.copy:hover{color:var(--tx);border-color:#b9c0c8}
.copy.done{color:#1a7f37;border-color:#9ad0a8;background:#f0fbf3}
.desc{margin:0;color:#3c4248;font-size:13.5px}
.tag-en{font-size:10.5px;color:#8a6d1f;background:#fdf5dd;border:1px solid #efdfae;border-radius:4px;padding:1px 5px;vertical-align:middle}
.gap .gaplist{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:10px}
.gap .gaplist li{background:var(--panel);border:1px dashed #d8dce2;border-radius:8px;padding:11px 13px;font-size:13.5px}
.gap .gaplist li span{display:block;color:var(--dim);font-size:12.5px;margin-top:3px}
footer{margin-top:26px;padding-top:14px;border-top:1px solid var(--line);color:var(--dim);font-size:12px;text-align:center}
@media(max-width:520px){.cards,.gap .gaplist{grid-template-columns:1fr}}
</style>
</head>
<body>
<!--BODY-->
<script>
document.addEventListener('click', function (ev) {
  var b = ev.target.closest('.copy');
  if (!b) return;
  var code = b.parentNode.querySelector('pre').innerText;
  navigator.clipboard.writeText(code).then(function () {
    b.textContent = '已复制'; b.classList.add('done');
    setTimeout(function () { b.textContent = '复制'; b.classList.remove('done'); }, 1200);
  });
});
</script>
</body>
</html>
"""


def main():
    data = json.load(open('_temp/_macro_data.json', encoding='utf-8'))
    os.makedirs('_temp/macros', exist_ok=True)
    n = md_out(data, '_temp/macros/wow_classic_macros.md')
    html_out(data, '_temp/macros/wow_classic_macros.html')
    print('宏条目总数:', n)
    print('输出: _temp/macros/wow_classic_macros.html / .md')


if __name__ == '__main__':
    main()

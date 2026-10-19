# -*- coding: utf-8 -*-
"""由 _temp/_rot_data.json 生成「全职业专精输出循环（Wowhead Forever 分级指南）」HTML + MD。"""
import html as H
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cc_rot import ROT  # noqa: E402

CLS_COLOR = {
    '战士': '#C79C6E', '圣骑士': '#F58CBA', '猎人': '#ABD473', '潜行者': '#FFF569',
    '牧师': '#FFFFFF', '萨满': '#0070DE', '法师': '#69CCF0', '术士': '#9482C9',
    '德鲁伊': '#FF7D0A',
}
CLS_DARK = {'牧师': '#8a8f98', '潜行者': '#b9ad2e', '战士': '#8a6a44'}

SPECKEY = {
    'arms': 'arms', 'fury': 'fury', 'protection': 'prot', 'holy': 'holy', 'retribution': 'ret',
    'beast-mastery': 'bm', 'marksmanship': 'mm', 'survival': 'surv',
    'assassination': 'assa', 'combat': 'combat', 'subtlety': 'sub',
    'discipline': 'disc', 'shadow': 'shadow', 'elemental': 'ele', 'enhancement': 'enh',
    'restoration': 'resto', 'arcane': 'arcane', 'fire': 'fire', 'frost': 'frost',
    'affliction': 'affli', 'demonology': 'demo', 'destruction': 'destro',
    'balance': 'balance', 'feral': 'feral',
}
ORDER = ['战士', '圣骑士', '猎人', '潜行者', '牧师', '萨满', '法师', '术士', '德鲁伊']


def group(data):
    """-> [(cls_zh, [ {spec_zh, cls, spec, role, L20:rec, L30:rec} ])]"""
    out = []
    for cls_zh in ORDER:
        specs = []
        keys = []
        for r in data:
            if r['cls_zh'] != cls_zh:
                continue
            if r['spec'] not in keys:
                keys.append(r['spec'])
        for sp in keys:
            recs = [r for r in data if r['cls_zh'] == cls_zh and r['spec'] == sp]
            d = {'cls': recs[0]['cls'], 'spec': sp, 'cls_zh': cls_zh,
                 'spec_zh': recs[0]['spec_zh'], 'role': recs[0]['role']}
            for r in recs:
                d['L%d' % r['lv']] = r
            specs.append(d)
        out.append((cls_zh, specs))
    return out


def items_of(rec):
    if not rec:
        return []
    return [(b['name'], b['kind'], b['items'], b['note']) for b in rec['blocks']]


def own_only(rec, other):
    """返回 rec 中独有条目文本集合（两级对照用）。"""
    if not rec or not other:
        return set()
    a = {i for _, _, its, _ in items_of(rec) for i in its}
    b = {i for _, _, its, _ in items_of(other) for i in its}
    return a - b


def plugin_count(cls_zh, spec, cls):
    row = ROT.get(cls.upper(), {})
    return len(row.get(SPECKEY.get(spec, spec), []))


def md_out(data, path):
    L = ['# WoW Forever 全职业专精输出循环（分级指南）', '',
         '> 数据来源：wowhead。内容取自 wowhead WoW Forever 各专精「Level 20 / Level 30 练级指南」的 Rotation 章节',
         '> （每专精两页，共 27 专精 × 2 = 54 页）。条目里的技能名为 wowhead 中文页的本地化名，说明文字为原文英文。', '']
    total = sum(len(its) for r in data for _, _, its, _ in items_of(r))
    L.append('共 **%d** 个专精页 · **%d** 条优先级条目。' % (len(data), total))
    L.append('')
    for cls_zh, specs in group(data):
        L.append('# %s' % cls_zh)
        L.append('')
        for sp in specs:
            L.append('## %s · %s' % (cls_zh, sp['spec_zh']))
            L.append('')
            for lv in (20, 30):
                rec = sp.get('L%d' % lv)
                if not rec:
                    continue
                L.append('### Lv%d — %s' % (lv, rec['title']))
                L.append('')
                for name, kind, its, note in items_of(rec):
                    if note:
                        L.append('*%s*' % note)
                        L.append('')
                    if not its:
                        continue
                    if name:
                        L.append('**%s**' % name)
                        L.append('')
                    for i, it in enumerate(its, 1):
                        L.append('%d. %s' % (i, it))
                    L.append('')
            L.append('')
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def html_out(data, path):
    total = sum(len(its) for r in data for _, _, its, _ in items_of(r))
    P = ['<div class="wrap">']
    P.append('<header><h1>WoW Forever 全职业专精输出循环</h1>'
             '<p class="sub">共 <b>%d</b> 个专精指南页（27 专精 × Level 20/30）· <b>%d</b> 条优先级条目 · '
             '抓取日期 2026-10-17 · 数据来源：wowhead</p></header>' % (len(data), total))
    P.append('<div class="note"><b>这是什么：</b>wowhead 在 WoW Forever 树上<b>没有独立的满级输出循环指南</b>，'
             '循环内容写在每个专精的 <b>Level 20 / Level 30 练级指南</b>里（页内 Rotation 章节）。'
             '下面的卡片按专精并列两个等级段；标 <span class="tag own">独有</span> 的条目只在该等级段出现。</div>')
    P.append('<nav class="chips">')
    for cls_zh, specs in group(data):
        P.append('<a class="chip" style="--c:%s" href="#k_%s">%s<i>%d 专精</i></a>'
                 % (CLS_COLOR.get(cls_zh, '#888'), cls_zh, cls_zh, len(specs)))
    P.append('<a class="chip chip-gap" href="#cmp">与插件数据对照</a>')
    P.append('</nav>')

    for cls_zh, specs in group(data):
        c = CLS_COLOR.get(cls_zh, '#888')
        P.append('<section class="cls" id="k_%s" style="--c:%s">' % (cls_zh, c))
        P.append('<h2><span class="dot"></span>%s</h2>' % cls_zh)
        P.append('<div class="cards">')
        for sp in specs:
            n20 = sum(len(i) for _, _, i, _ in items_of(sp.get('L20')))
            n30 = sum(len(i) for _, _, i, _ in items_of(sp.get('L30')))
            P.append('<article class="card">')
            P.append('<h3>%s <small>%s</small>'
                     '<em>Lv20 %d · Lv30 %d</em></h3>'
                     % (sp['spec_zh'], sp['role'].upper(), n20, n30))
            P.append('<div class="cols">')
            for lv in (20, 30):
                rec = sp.get('L%d' % lv)
                P.append('<div class="col">')
                if not rec:
                    P.append('<div class="lv">Lv%d</div><p class="desc">无</p></div>' % lv)
                    continue
                P.append('<div class="lv">Lv%d</div>' % lv)
                own = own_only(rec, sp.get('L%d' % (30 if lv == 20 else 20)))
                for name, kind, its, note in items_of(rec):
                    if note:
                        P.append('<p class="desc">%s</p>' % H.escape(note))
                    if not its:
                        continue
                    if name:
                        P.append('<div class="sec">%s</div>' % H.escape(name))
                    P.append('<ol class="steps">')
                    for it in its:
                        tag = ' <span class="tag own">独有</span>' if it in own else ''
                        P.append('<li>%s%s</li>' % (H.escape(it), tag))
                    P.append('</ol>')
                P.append('</div>')
            P.append('</div></article>')
        P.append('</div></section>')

    P.append('<section class="cls" id="cmp" style="--c:#8b8f96">')
    P.append('<h2><span class="dot"></span>与插件现有循环数据对照</h2>')
    P.append('<p class="desc">插件职业指南页现有 <code>ClassCombat</code> 循环为「单套通用优先级」；'
             'wowhead 为「分级两套（Lv20 / Lv30）」。下表列出条数对照。</p>')
    P.append('<table class="cmp"><thead><tr><th>专精</th><th>插件现有</th><th>wowhead Lv20</th>'
             '<th>wowhead Lv30</th></tr></thead><tbody>')
    for cls_zh, specs in group(data):
        for sp in specs:
            n20 = sum(len(i) for _, _, i, _ in items_of(sp.get('L20')))
            n30 = sum(len(i) for _, _, i, _ in items_of(sp.get('L30')))
            P.append('<tr><td>%s · %s</td><td>%d</td><td>%d</td><td>%d</td></tr>'
                     % (cls_zh, sp['spec_zh'],
                        plugin_count(cls_zh, sp['spec'], sp['cls']), n20, n30))
    P.append('</tbody></table></section>')
    P.append('<footer>本页为本地参考文档 · 内容取自 wowhead WoW Forever 分级指南的 Rotation 章节 · 抓取于 2026-10-17</footer>')
    P.append('</div>')
    doc = HTML_TMPL.replace('<!--BODY-->', '\n'.join(P))
    open(path, 'w', encoding='utf-8').write(doc)


HTML_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WoW Forever 全职业专精输出循环</title>
<style>
:root{--bg:#f5f6f8;--panel:#fff;--line:#e3e6ea;--tx:#1f2328;--dim:#5b6167}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.6 "Microsoft YaHei","Segoe UI",system-ui,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 60px}
header h1{margin:0 0 6px;font-size:26px;letter-spacing:.5px}
header .sub{margin:0;color:var(--dim);font-size:13px}
.note{margin:16px 0 4px;background:#fff;border:1px solid var(--line);border-left:4px solid #7aa7ff;
  border-radius:8px;padding:11px 14px;font-size:13.5px;color:#333a42}
nav.chips{position:sticky;top:0;z-index:9;display:flex;flex-wrap:wrap;gap:8px;padding:12px 0;margin:0 0 18px;
  background:linear-gradient(var(--bg) 70%,rgba(245,246,248,.85));border-bottom:1px solid var(--line)}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border:1px solid var(--line);border-radius:999px;
  background:var(--panel);color:var(--tx);text-decoration:none;font-size:13px;box-shadow:0 1px 1px rgba(0,0,0,.03)}
.chip i{font-style:normal;color:var(--dim);font-size:11px}
.chip::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--c)}
.chip:hover{border-color:var(--c);box-shadow:0 2px 6px rgba(0,0,0,.06)}
.chip-gap{color:var(--dim)}
.cls{margin:0 0 34px}
.cls h2{display:flex;align-items:center;gap:9px;margin:0 0 14px;font-size:20px;border-left:4px solid var(--c);padding-left:10px}
.cls h2 .dot{display:none}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(560px,1fr));gap:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 15px 12px;
  box-shadow:0 1px 2px rgba(0,0,0,.03)}
.card h3{margin:0 0 10px;font-size:15.5px;display:flex;align-items:center;gap:8px}
.card h3 small{font-weight:400;color:var(--dim);font-size:11px;border:1px solid var(--line);border-radius:4px;padding:1px 5px}
.card h3 em{margin-left:auto;font-style:normal;font-size:11.5px;color:var(--dim)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.col{background:#fafbfc;border:1px solid #edf0f3;border-radius:8px;padding:10px 11px 8px}
.lv{font-size:11.5px;font-weight:700;color:var(--c);letter-spacing:.5px;margin:0 0 7px}
.sec{font-size:12px;color:#414851;background:#eef1f5;border-radius:4px;padding:2px 7px;
  display:inline-block;margin:6px 0 5px;font-weight:600}
.steps{margin:0 0 4px;padding-left:20px;font-size:13px;color:#333a42}
.steps li{margin:0 0 3px}
.desc{margin:4px 0 6px;font-size:12.5px;color:var(--dim)}
.tag{font-size:10px;border-radius:3px;padding:0 4px;white-space:nowrap}
.tag.own{color:#8a6d1f;background:#fdf5dd;border:1px solid #efdfae}
table.cmp{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:8px;overflow:hidden;font-size:13.5px}
table.cmp th,table.cmp td{padding:7px 12px;border-bottom:1px solid var(--line);text-align:left}
table.cmp thead th{background:#f0f2f5;font-size:12.5px;color:#41474e}
table.cmp tbody tr:last-child td{border-bottom:0}
code{background:#eef1f5;border-radius:3px;padding:0 4px;font-size:12.5px}
footer{margin-top:26px;padding-top:14px;border-top:1px solid var(--line);color:var(--dim);font-size:12px;text-align:center}
@media(max-width:640px){.cards{grid-template-columns:1fr}.cols{grid-template-columns:1fr}}
</style>
</head>
<body>
<!--BODY-->
</body>
</html>
"""


def main():
    data = json.load(open('_temp/_rot_data.json', encoding='utf-8'))
    os.makedirs('_temp/rotations', exist_ok=True)
    md_out(data, '_temp/rotations/wow_forever_rotations.md')
    html_out(data, '_temp/rotations/wow_forever_rotations.html')
    total = sum(len(its) for r in data for _, _, its, _ in items_of(r))
    print('专精页:', len(data), '| 条目:', total)
    print('输出: _temp/rotations/wow_forever_rotations.html / .md')


if __name__ == '__main__':
    main()

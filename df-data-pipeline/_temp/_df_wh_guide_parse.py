# -*- coding: utf-8 -*-
"""解析 wowhead 攻略页 BBCode → 每 boss {text, spells[]}（v2）。

页面 BBCode 真源内嵌于 printHtml("…")，闭合标签带反斜杠（[\\/h3]）、换行是字面 \\r\\n。

每个 boss 框结构（两种形态）：
  A（多数副本）[h3 type=bar]<Boss>[/h3] [center][screenshot…][/center]
                [center][b]Strategy[/b][/center] <正文> [pad] [table…Abilities…[spell=ID]…[/table] [/box]
  B（诺莫瑞根）[h3 type=bar]<Boss>[/h3] [center][screenshot…][/center] <正文> [pad][br] [table…]

正文 = 截图之后、[table 之前（去掉 [b]Strategy[/b] 标记与 [pad]/[br] 尾巴）；
能力 = [b]Abilities[/b] 之后的 [spell=ID]（去重保序）。

输出：_temp/_wh_guide_raw.json = { 副本id: { bossEn: {text, spells:[id…]} } }
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_ref_wowhead")

H3 = re.compile(r'\[h3[^\]]*\](.*?)\[/h3\]', re.S)
# 永恒服新页形态（2026-09-30 洛丹伦废墟）：boss 段是 [box-highlight name="…"] 而非 h3
BOX = re.compile(r'\[box-highlight name="([^"]+)"\](.*?)(?=\[box-highlight|\[/tabs\]|\[h3|\Z)', re.S)
SHOT = re.compile(r'\[/screenshot\]\s*\[/center\]', re.S)
STRAT = re.compile(r'\[center\]\s*\[b\]Strategy\[/b\]\s*\[/center\]', re.S)
ABIL = re.compile(r'\[b\]Abilities\[/b\]')
SPELL = re.compile(r'\[spell=(\d+)\]')


def unesc(s):
    """BBCode 转义还原 + 实体 + \\uXXXX。"""
    s = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), s)
    for a, b in [("\\/", "/"), ('\\"', '"'), ("&amp;", "&"), ("&lt;", "<"),
                 ("&gt;", ">"), ("&#x27;", "'"), ("&apos;", "'"),
                 ("&quot;", '"'), ("&nbsp;", " ")]:
        s = s.replace(a, b)
    return s.strip()


def extract_bbcode(html):
    if '[h3 type=bar]' not in html:
        return None
    return (html.replace('\\/', '/')
                .replace('\\r\\n', ' ')
                .replace('\\"', '"'))


def parse_seg(name, seg):
    """单段（h3 或 box-highlight）→ (name, text, spells)。"""
    # 正文：优先截图后；没截图退回段首
    base = SHOT.search(seg)
    start_at = base.end() if base else 0
    body = seg[start_at:]
    cut = body.find('[table')
    if cut >= 0:
        body = body[:cut]
    # 去掉 A 形态的 Strategy 标记（若退回段首且存在）
    sm = STRAT.search(body)
    if sm and not base:
        body = body[sm.end():]
    # 正文 v2：先把 spell/npc 引用换成占位符（«S123»/«N456»），再剥其余标签，
    #   避免剥掉后句子缺主语。
    seg_txt = seg if not base else seg[base.end():]
    cut2 = seg_txt.find('[table')
    if cut2 >= 0:
        seg_txt = seg_txt[:cut2]
    seg_txt = STRAT.sub(' ', seg_txt)
    seg_txt = re.sub(r'\[spell=(\d+)\]', r'«S\1»', seg_txt)
    seg_txt = re.sub(r'\[npc=(\d+)\]', r'«N\1»', seg_txt)
    seg_txt = unesc(re.sub(r'\[/?[a-z]+[^\]]*\]', ' ', seg_txt))
    text = re.sub(r'\s+', ' ', seg_txt).strip()
    # 能力：Abilities 表内的 spell id（去重保序）
    am = ABIL.search(seg)
    spells = []
    if am:
        for x in SPELL.finditer(seg[am.end():]):
            sid = int(x.group(1))
            if sid not in spells:
                spells.append(sid)
    return name, text, spells


def parse_page(html):
    """→ [ (bossEn, strategy, [spellID…]) ]（保持页面顺序）"""
    bb = extract_bbcode(html)
    if not bb:
        return None, "NO_BBCODE"
    out, seen = [], set()
    heads = list(H3.finditer(bb))
    for i, m in enumerate(heads):
        name = unesc(m.group(1))
        seg_end = heads[i + 1].start() if i + 1 < len(heads) else len(bb)
        if name:
            seen.add(name)
        out.append(parse_seg(name, bb[m.end():seg_end]))
    # box-highlight 形态（永恒服新页）：h3 没覆盖到的 boss 段补进来（同名去重，h3 优先）
    for m in BOX.finditer(bb):
        name = unesc(m.group(1)).strip()
        if not name or name in seen:
            continue
        seg_end = len(m.group(2))
        out.append(parse_seg(name, m.group(2)[:seg_end]))
        seen.add(name)
    return [(n, t, s) for n, t, s in out if n], None


def main():
    res = {}
    for fn in sorted(os.listdir(SRC)):
        if not fn.startswith("wh_"):
            continue
        did = fn[3:-5]
        html = open(os.path.join(SRC, fn), encoding="utf-8", errors="replace").read()
        bosses, err = parse_page(html)
        if err:
            print("%-20s ✗ %s" % (did, err))
            continue
        row = {}
        for name, text, spells in bosses:
            if not text and not spells:
                continue  # Lore / Quests / 杂兵段
            row[name] = {"text": text, "spells": spells}
        res[did] = row
        print("%-20s boss=%d" % (did, len(row)))
        for name, v in row.items():
            print("    %-36s spells=%-24s text[%d]" % (name[:36], v["spells"], len(v["text"])))
    json.dump(res, open(os.path.join(HERE, "_wh_guide_raw.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("— 落盘 _temp/_wh_guide_raw.json")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""同步 enus_data*.py 翻译表：键是旧版中文注释的条目，键改为 strip_zh 后的新文本，
值（英文译文）按 strip_en 同规则清理。改完需重跑 gen_enus_data.py / gen_zhtw_data.py。

规则函数从 cod_strip_comments.py 导入，保证与数据文件清理完全一致。
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cod_strip_comments import strip_zh, strip_en, quote  # noqa: E402

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLES = ['enus_data_quests.py', 'enus_data_quests2.py', 'enus_data_prose.py',
          'enus_data_names.py', 'enus_data_names2.py',
          'enus_data_names3.py', 'enus_data_names_hand.py']

# python 字符串字面量（含转义）配对
LIT = r"('(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")"


def lit_body(lit):
    q = lit[0]
    body = lit[1:-1]
    if q == '"':
        return body.replace('\\"', '"').replace('\\\\', '\\')
    return body.replace("\\'", "'").replace('\\\\', '\\')


def lit_quote(body, prefer="'"):
    if prefer == "'" and ("'" not in body or "\\'" in body):
        return "'" + body.replace('\\', '\\\\').replace("'", "\\'") + "'"
    return '"' + body.replace('\\', '\\\\').replace('"', '\\"') + '"'


def process(path, dry=True):
    src = io.open(path, encoding='utf-8').read()
    out = src
    n_changed = 0
    # 逐条扫描 "键": 值 映射
    pos = 0
    pat = re.compile(LIT + r'\s*:\s*' + LIT)
    spans = []
    for m in pat.finditer(src):
        key_lit, val_lit = m.group(1), m.group(2)
        key = lit_body(key_lit)
        new_key = strip_zh(key)
        if new_key == key:
            continue
        # 键值都用同样的清理规则（英文值走 strip_en）
        new_val = strip_en(val_lit)
        new_key_lit = key_lit[0] + new_key.replace('\\', '\\\\') + key_lit[0]
        spans.append((m.start(), m.end(),
                      new_key_lit + ':' + (' ' if not new_val.startswith(' ') else '')
                      + new_val))
        n_changed += 1
    spans.sort()
    out, prev = [], 0
    for a, b, rep in spans:
        out.append(src[prev:a])
        out.append(rep)
        prev = b
    out.append(src[prev:])
    out = ''.join(out)

    print('%s: 改写 %d 条' % (os.path.basename(path), n_changed))
    if not dry and n_changed:
        io.open(path, 'w', encoding='utf-8', newline='').write(out)
    return n_changed


def main():
    dry = '--apply' not in sys.argv
    total = 0
    for name in TABLES:
        total += process(os.path.join(BASE, '_temp', name), dry)
    print('合计 %d 条（%s）' % (total, 'dry' if dry else '已写回'))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()

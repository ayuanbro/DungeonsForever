# -*- coding: utf-8 -*-
"""清空「活跃生成器」里写进 lua 的注释模板（2026-10-17：插件不带任何注释）。

· 真词法扫描（复用 strip_comments.comment_spans）：行首注释与行尾注释一起清；
· 模板里的代码行（local _, ns = ... / locale 守卫 / ns.X = {）原样保留；
· 含 %s 格式化占位的模板**不自动改**（会破坏 % 元数），只报告 —— 由人手改用法；
· 默认 dry-run；--apply 落盘；备份 _temp/_tpl_bak_20261017/；逐文件 compile 失败即回滚。
"""
import ast
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from strip_comments import comment_spans  # noqa: E402

ROOT = os.path.dirname(HERE)
BAK = os.path.join(HERE, '_tpl_bak_20261017')

LIVE = [
    'explore_gen.py', 'fc_bis.py', 'fc_gen.py', 'fc_guide.py', 'fc_pins.py', 'fc_tier.py',
    'gen_area_map.py', 'gen_boss_model.py', 'gen_boss_pos.py', 'gen_boss_skills.py',
    'gen_class_combat.py', 'gen_crates_data.py', 'gen_dungeon_entry.py', 'gen_enus.py',
    'gen_enus_data.py', 'gen_faction_qm.py', 'gen_factions_data.py', 'gen_gear_rare.py',
    'gen_gear_scrape.py', 'gen_gear_vendors.py', 'gen_locales.py', 'gen_plunder_data.py',
    'gen_prof_trainers.py', 'gen_pvp_data.py', 'gen_pvp_honor.py', 'gen_raidsets.py',
    'gen_zhtw.py', 'gen_zhtw_data.py', 'sync_data.py', 'port_dungeonsforever.py',
    '_build_pets_src.py', 'lf_gen_presets.py',
]

NAMES = re.compile(r'^(HEAD|HEADER|HEAD_COMMON|HEAD_[A-Z_]+|HEADER_[A-Z_]+|GUARD|BANNER|TXT|txt|head|banner)$')
APPEND_FUNCS = ('append', 'A', 'Ap', 'add', 'write_line')
PH = re.compile(r'%[-+ #0-9.]*[sdifgxXeE%]')


def lua_strip(value):
    """把 lua 代码文本里的注释清掉，并压掉因删除产生的空白行。"""
    spans = comment_spans(value)
    for s, e in reversed(spans):
        value = value[:s] + value[e:]
    out = [l.rstrip() for l in value.split('\n')]
    return '\n'.join(l for l in out if l.strip())


def py_literal(value):
    """生成一段 Python 源码字面量，其运行时值恰好等于 value。"""
    if '\r' in value or '\n' not in value:
        return repr(value)
    v = value.replace('\\', '\\\\')
    if "'''" in v or v.endswith('\\'):
        return repr(value)
    return "'''" + v + "'''"


def collect_hits(tree):
    """返回 [(字符串常量节点, 标签)] —— 白名单名赋值 / append 类调用的字符串实参。"""
    hits = []
    for node in ast.walk(tree):
        targets_nodes = []
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not any(NAMES.match(n) for n in names):
                continue
            targets_nodes = list(walk_strs(node.value))
            label = ','.join(names)
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            f = node.value.func
            fn = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else '')
            if fn not in APPEND_FUNCS:
                continue
            targets_nodes = [a for a in node.value.args
                             if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            label = fn + '()'
        else:
            continue
        for c in targets_nodes:
            if '--' not in c.value:
                continue
            hits.append((c, label))
    return hits


def walk_strs(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node
    elif isinstance(node, ast.List):
        for e in node.elts:
            if isinstance(e, ast.Constant) and isinstance(e.value, str):
                yield e
    elif isinstance(node, ast.Dict):
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                yield v
            elif isinstance(v, ast.List):
                for e in v.elts:
                    if isinstance(e, ast.Constant) and isinstance(e.value, str):
                        yield e


def lf_offsets(text):
    """返回行首字符偏移表（LF 文本，按行号 1 基索引）。"""
    out = [0]
    off = 0
    for ln in text.split('\n'):
        off += len(ln) + 1
        out.append(off)
    return out


def rewrite_file(path, apply):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8')
    try:
        tree = ast.parse(text)
    except SyntaxError as ex:
        print('  !! 解析失败 %s: %s' % (os.path.basename(path), ex))
        return None
    hits = collect_hits(tree)
    if not hits:
        return []
    # ★ AST 的 col_offset / end_col_offset 是**行内 UTF-8 字节偏移**
    #   ⇒ 必须按字节切；按字符切会在含多字节中文的模板上越界吃掉引号。
    starts = [0]
    off = 0
    for ln in raw.split(b'\n'):
        off += len(ln) + 1
        starts.append(off)
    edits = []
    report = []
    for c, label in hits:
        s = starts[c.lineno - 1] + c.col_offset
        e = starts[c.end_lineno - 1] + c.end_col_offset
        seg = raw[s:e].decode('utf-8')
        # 切片硬校验：必须恰好解出这个字面量，否则宁可不改
        try:
            if ast.literal_eval(seg) != c.value:
                report.append((label, c.lineno, 'SKIP-切片不符', 0, 0))
                continue
        except Exception:
            report.append((label, c.lineno, 'SKIP-切片不符', 0, 0))
            continue
        value = c.value
        if PH.search(value):
            report.append((label, c.lineno, 'SKIP-占位', len(value.split('\n')), 0))
            continue
        new = lua_strip(value)
        if new == value:
            continue
        edits.append((s, e, py_literal(new)))
        report.append((label, c.lineno, '改动',
                       len([x for x in value.split('\n') if x.strip()]),
                       len([x for x in new.split('\n') if x.strip()])))
    if not edits or not apply:
        return report
    new_raw = raw
    for s, e, rep in sorted(edits, reverse=True):
        new_raw = new_raw[:s] + rep.encode('utf-8') + new_raw[e:]
    try:
        compile(new_raw.decode('utf-8'), path, 'exec')
    except SyntaxError as ex:
        print('  !! compile 失败，回滚 %s: %s' % (os.path.basename(path), ex))
        return None
    os.makedirs(BAK, exist_ok=True)
    dst = os.path.join(BAK, os.path.basename(path) + '.bak')
    if not os.path.exists(dst):
        shutil.copy2(path, dst)
    open(path, 'wb').write(new_raw)
    return report


def main():
    apply = '--apply' in sys.argv
    skip = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--skip=')]
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    total = 0
    for b in LIVE:
        if any(s in b for s in skip):
            continue
        if only and not any(o in b for o in only):
            continue
        p = os.path.join(HERE, b)
        if not os.path.exists(p):
            continue
        rep = rewrite_file(p, apply)
        if rep is None:
            continue
        if not rep:
            continue
        print('=' * 80)
        print(b)
        for label, ln, kind, a, c in rep:
            print('   行%-5d %-12s %-8s 行数 %d -> %d' % (ln, label, kind, a, c))
            total += 1
    print('=' * 80)
    print('%s：候选点 %d 个' % ('已落盘' if apply else 'dry-run', total))


if __name__ == '__main__':
    main()

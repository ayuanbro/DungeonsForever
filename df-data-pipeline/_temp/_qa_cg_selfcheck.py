# -*- coding: utf-8 -*-
"""职业指南数据生成器 · 一次性断言自查（生成后跑）。

用法：python _temp/_qa_cg_selfcheck.py

检查项：
  A. 27 页中 sw 板块「同时」存在 good 与 bad 的页数（修复前 1，期望 22）
  B. 武器战：good 恰 3 条、bad 恰 3 条，且 bad 命中「怒气依赖」
  C. 两个生成物 Lua 里 |l| / \x05 / \x03 / \x04 出现次数（期望均 0）
  D. races 板块里 t="h4" 出现在多少个专精页
  E. 解析垃圾：h4 值属 {false,true,nil,null,none,undefined} 的元素数（期望 0）
  F. 空标题/空段落：p 或 h4 值为空串的元素数（期望 0）
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZH = os.path.join(ROOT, 'Core', 'Data', 'Data_ClassGuide.lua')
EN = os.path.join(ROOT, 'Core', 'Data', 'enUS', 'Data_ClassGuide.lua')

JUNK_VALS = {'false', 'true', 'nil', 'null', 'none', 'undefined'}

# ---- 极简 Lua 结构解析：只认生成器写出的固定缩进格式 ----
SEC_RE = re.compile(r'^\s*\{ key = "([^"]+)", flow = \{ *$')
SEC_END_RE = re.compile(r'^\s*\} \}, *$')
ELEM_RE = re.compile(r'^\s*\{ t = "([a-z0-9]+)"')
SPEC_RE = re.compile(r'^ {12}([a-z0-9_]+) = \{$')
CLASS_RE = re.compile(r'^ {8}([A-Z_]+) = \{$')
STR_RE = re.compile(r'(?<!\\)"')
VSTR_RE = re.compile(r'v = "((?:[^"\\]|\\.)*)"')


def _count_items(inner):
    return len(STR_RE.findall(inner)) // 2


def parse(path):
    """返回 {class: {spec: {seckey: {good,bad,h4,good_items,h4_vals,p_vals}}}}。"""
    data = {}
    cls = spec = sec = None
    sec_started = False
    for line in io.open(path, encoding='utf-8'):
        if not line.strip() or line.lstrip().startswith('--'):
            continue
        m = CLASS_RE.match(line)
        if m:
            cls = m.group(1)
            data.setdefault(cls, {})
            continue
        m = SPEC_RE.match(line)
        if m and not SEC_RE.match(line):
            spec = m.group(1)
            data.setdefault(cls, {}).setdefault(spec, {})
            continue
        m = SEC_RE.match(line)
        if m:
            sec = m.group(1)
            sec_started = True
            data[cls][spec][sec] = {'good': 0, 'bad': 0, 'h4': 0, 'good_items': [],
                                    'h4_vals': [], 'p_vals': []}
            continue
        if sec_started and SEC_END_RE.match(line):
            sec_started = False
            sec = None
            continue
        if sec_started and sec is not None:
            e = ELEM_RE.match(line)
            if not e:
                continue
            t = e.group(1)
            rec = data[cls][spec][sec]
            if t == 'h4':
                rec['h4'] += 1
                mv = VSTR_RE.search(line)
                if mv:
                    rec['h4_vals'].append(mv.group(1))
            elif t == 'p':
                mv = VSTR_RE.search(line)
                if mv:
                    rec['p_vals'].append(mv.group(1))
            elif t in ('good', 'bad'):
                inner = line.split('v = {', 1)[1].rsplit('} },', 1)[0]
                n = _count_items(inner)
                rec[t] += n
                if t == 'good':
                    rec['good_items'] = re.findall(r'(?<!\\)"((?:[^"\\]|\\.)*)"', inner)
    return data


def _flat(data):
    out = {}
    for c, specs in data.items():
        for s, secs in specs.items():
            out['%s/%s' % (c, s)] = secs
    return out


def report(label, data):
    flat = _flat(data)
    print('=' * 68)
    print('[%s]' % label)
    # A
    swpages = [k for k, secs in flat.items() if 'sw' in secs]
    both = [k for k, secs in flat.items() if secs.get('sw', {}).get('good')
            and secs.get('sw', {}).get('bad')]
    print('A. 有 sw 板块页 = %d；sw 同时含 good&bad = %d' % (len(swpages), len(both)))
    # B
    arms = flat.get('WARRIOR/arms', {}).get('sw', {})
    print('B. 武器战 arms: good=%d bad=%d' % (arms.get('good', 0), arms.get('bad', 0)))
    # D
    h4pages = [k for k, secs in flat.items() if secs.get('races', {}).get('h4')]
    print('D. races 板块含 h4 的专精页 = %d' % len(h4pages))
    # E
    junk = []
    for k, secs in flat.items():
        for sk, sr in secs.items():
            for v in sr['h4_vals']:
                if v.strip().lower() in JUNK_VALS:
                    junk.append('%s[%s]=%r' % (k, sk, v))
    print('E. h4 为垃圾字面量的元素 = %d' % len(junk))
    for j in junk:
        print('     ', j)
    # F
    empty = []
    for k, secs in flat.items():
        for sk, sr in secs.items():
            for v in sr['h4_vals'] + sr['p_vals']:
                if v.strip() == '':
                    empty.append('%s[%s]' % (k, sk))
    print('F. 空 p/h4 元素 = %d' % len(empty))
    return {'both': both, 'arms_g': arms.get('good', 0), 'arms_b': arms.get('bad', 0),
            'h4pages': h4pages, 'junk': junk, 'empty': empty}


def main():
    zh = parse(ZH)
    en = parse(EN)
    rz = report('zhCN', zh)
    re_ = report('enUS', en)

    print('=' * 68)
    print('C. 生成物控制字符/字面泄漏（期望全 0）')
    for label, p in (('zhCN', ZH), ('enUS', EN)):
        body = io.open(p, encoding='utf-8').read()
        print('   %-5s |l|=%-3d \\x05=%-3d \\x03=%-3d \\x04=%-3d | 独立 h4 "false"=%d'
              % (label, body.count('|l|'), body.count('\x05'), body.count('\x03'),
                 body.count('\x04'),
                 len(re.findall(r'\{ t = "h4", v = "(?:false|true|nil|null|none|undefined)" \}',
                                body))))

    # 武器战 bad 命中怒气依赖
    txt = io.open(ZH, encoding='utf-8').read()
    m = re.search(r'\{ key = "sw", flow = \{(.*?)\n\s*\} \},', txt, re.S)
    badline = [l for l in (m.group(1).splitlines() if m else []) if 't = "bad"' in l]
    baditems = re.findall(r'(?<!\\)"((?:[^"\\]|\\.)*)"', badline[0].split('v = {', 1)[1]) if badline else []
    has_rage = any('怒气依赖' in x for x in baditems)

    print('=' * 68)
    ok = (rz['arms_g'] == 3 and rz['arms_b'] == 3 and has_rage
          and len(rz['both']) >= 20 and len(re_['both']) >= 20
          and not rz['junk'] and not re_['junk']
          and not rz['empty'] and not re_['empty'])
    print('武器战 bad 命中「怒气依赖」=', has_rage)
    print('VERDICT:', 'PASS' if ok else 'CHECK')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())

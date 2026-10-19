# -*- coding: utf-8 -*-
"""锚敏感性自证：故意造「无限+杂词」并确认 assert_forever_alignment 非零退出。
三场景：PASS（真实译文）/ MISSING（去掉「无限」）/ WORDY（注入「无限+杂词」）。"""
import copy
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fc_guide as F  # noqa: E402

DATA = json.load(io.open(os.path.join(HERE, '_cg_parsed.json'), encoding='utf-8'))


def load_all():
    out = {}
    for spec in DATA:
        p = os.path.join(HERE, '_cg_trans', spec + '.json')
        out[spec] = json.load(io.open(p, encoding='utf-8')) if os.path.exists(p) else {}
    return out


def find_target(transes):
    """找一个 EN 含 Forever、且 CN 含「无限」的 (spec, key, idx)。"""
    for spec in sorted(DATA):
        tr = transes.get(spec) or {}
        tmap = {s.get('key'): s for s in (tr.get('sections') or [])}
        for sec in DATA[spec].get('sections', []):
            tsec = tmap.get(sec.get('key'))
            if not tsec:
                continue
            cf = tsec.get('flow') or []
            for i, e in enumerate(sec.get('flow', [])):
                en = F._element_text(e)
                if F._FOREVER_RE.search(en) and i < len(cf):
                    cn = F._element_text(cf[i])
                    if '无限' in cn:
                        return spec, sec.get('key'), i
    raise SystemExit('未找到目标元素')


def set_flow_text(transes, spec, key, idx, new_text):
    for s in transes[spec]['sections']:
        if s.get('key') == key:
            s['flow'][idx]['v'] = new_text
            return
    raise SystemExit('section not found')


def run(label, transes, expect_fail):
    F.load_trans = lambda spec: transes.get(spec)
    try:
        F.assert_forever_alignment(DATA)
        died = False
    except SystemExit as e:
        died = True
        msg = str(e)
    verdict = 'OK' if died == expect_fail else '**FAIL**'
    print('[%s] %-8s died=%s (expect_fail=%s) %s' % (verdict, label, died,
                                                     expect_fail,
                                                     ('| ' + msg) if died else ''))
    return verdict == 'OK'


def main():
    transes = load_all()
    spec, key, idx = find_target(transes)
    print('目标元素: %s / %s #%d\n' % (spec, key, idx))

    all_ok = True
    # 1) 真实译文 → 通过
    all_ok &= run('PASS', copy.deepcopy(transes), False)
    # 2) 去掉「无限」→ 必 die
    t2 = copy.deepcopy(transes)
    set_flow_text(t2, spec, key, idx, '这是一个没有版本名的句子。')
    all_ok &= run('MISSING', t2, True)
    # 3) 注入「无限 + 杂词」→ 必 die（旧锚的盲区）
    t3 = copy.deepcopy(transes)
    set_flow_text(t3, spec, key, idx, '在《无限》怀旧服中，联盟盗贼通常会优先选择。')
    all_ok &= run('WORDY', t3, True)
    # 3b) 「无限 + 资料片」→ 必 die
    t4 = copy.deepcopy(transes)
    set_flow_text(t4, spec, key, idx, '所有专业都已随《魔兽世界：无限》资料片重做。')
    all_ok &= run('WORDY2', t4, True)
    # 4) 合法「后续资料片」（不与版本 token 相邻）→ 不应 die
    t5 = copy.deepcopy(transes)
    set_flow_text(t5, spec, key, idx,
                  '重点强化了该专精在后续资料片中发展出的特色，详见《无限》版本说明。')
    all_ok &= run('LEGIT', t5, False)

    print('\n总体:', 'ALL OK' if all_ok else '有 FAIL')
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()

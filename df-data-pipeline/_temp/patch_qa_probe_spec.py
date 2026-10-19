# -*- coding: utf-8 -*-
"""_qa_probe_spec.py（职业指南/专精指南探针）几何锁定值联动：
TierUI TT.EDGE 20->PAGE_INSET 后 FULL_W 732->748、INNER_FULL_W 712->728。
二进制读写、保真换行；anchor 命中数不符即中止。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, '_qa_probe_spec.py')

# (old, new, 期望命中次数)
PATCHES = [
    # 注释里的取证数字（dev 探针内，非发布件）
    ('SEC_TEXT_W（=FULL_W−2×CARD_PAD=712，与内宽同值）',
     'SEC_TEXT_W（=FULL_W−2×CARD_PAD=728，与内宽同值）', 1),
    ('表格/种族/双列块满幅 712（INNER_FULL_W）',
     '表格/种族/双列块满幅 728（INNER_FULL_W）', 1),
    # 断言名 + 比较字面量
    ('ck("★ FULL_W = 732（整幅卡宽；2026-10-10 双大卡改版 RIGHT_W=CONTENT_W−192−20−8）",',
     'ck("★ FULL_W = 748（整幅卡宽；§3.3 外缘 12 后 RIGHT_W=CONTENT_W−184−12−8）",', 1),
    ('math.abs(FULLW - 732) < 0.01, FULLW)',
     'math.abs(FULLW - 748) < 0.01, FULLW)', 1),
    ('ck("★★ 段落/列表行宽 = 712（SEC_TEXT_W=FULL_W−2×CARD_PAD，与 INNER_FULL_W 同值）",',
     'ck("★★ 段落/列表行宽 = 728（SEC_TEXT_W=FULL_W−2×CARD_PAD，与 INNER_FULL_W 同值）",', 1),
    ('ck("★★ 表格/种族行宽 = 712（INNER_FULL_W=732−2×10 真的落到行上）", rowW[712] == true)',
     'ck("★★ 表格/种族行宽 = 728（INNER_FULL_W=748−2×10 真的落到行上）", rowW[728] == true)', 1),
    ('ck("★★ 无行宽超出整幅内宽 712", overInner == 0, overInner)',
     'ck("★★ 无行宽超出整幅内宽 728", overInner == 0, overInner)', 1),
    ('rowW[712] == true)',
     'rowW[728] == true)', 1),
]


def run(check_only):
    raw = open(P, 'rb').read()
    crlf = b'\r\n' in raw
    text = raw
    fails = 0
    for old, new, want in PATCHES:
        ob = old.encode('utf-8')
        nb = new.encode('utf-8')
        if crlf:
            ob = ob.replace(b'\n', b'\r\n')
            nb = nb.replace(b'\n', b'\r\n')
        n = text.count(ob)
        if n != want:
            print('  FAIL hits=%d expect=%d : %s' % (n, want, old[:50]))
            fails += 1
            continue
        text = text.replace(ob, nb, 1)
        print('  %s hits=%d : %s' % ('ok  ' if check_only else 'OK  ', n, old[:50]))
    if fails:
        return fails
    if check_only:
        return 0
    if crlf:
        assert text.count(b'\r\n') == raw.count(b'\r\n'), 'CRLF count changed'
        assert text.count(b'\n') - text.count(b'\r\n') == 0, 'bare LF introduced'
    open(P, 'wb').write(text)
    return 0


if __name__ == '__main__':
    check = '--check' in sys.argv
    print('--- %s ---' % ('DRY-RUN' if check else 'APPLY'))
    sys.exit(2 if run(check) else 0)

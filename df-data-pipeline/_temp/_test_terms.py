# -*- coding: utf-8 -*-
"""normalize_terms 清理规则单测：版本 token + 杂词 → 归一；且幂等；合法语境不动。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fc_guide as F  # noqa: E402

CASES = [
    # (输入, 期望)
    ('在《无限》怀旧服中，联盟盗贼', '在无限服中，联盟盗贼'),
    ('在《魔兽世界：无限》怀旧服中，部落盗贼', '在无限服中，部落盗贼'),
    ('所有专业都已随《魔兽世界：无限》资料片重做。', '所有专业都已随《魔兽世界：无限》重做。'),
    ('所有专业都已随《无限》资料片重做。', '所有专业都已随《无限》重做。'),
    ('《无限》经典赛季新增', '《无限》新增'),
    # 合法语境（不该动）：经典怀旧服=Classic；后续资料片=later expansion
    ('救赎之灵在《无限》中的持续时间为15秒，经典怀旧服中为10秒。',
     '救赎之灵在《无限》中的持续时间为15秒，经典怀旧服中为10秒。'),
    ('重点强化了戒律牧师在后续资料片中发展出的特色。',
     '重点强化了戒律牧师在后续资料片中发展出的特色。'),
]

ok = True
for src, exp in CASES:
    got = F.normalize_terms(src)
    idem = F.normalize_terms(got) == got
    good = (got == exp) and idem
    ok &= good
    print('%s  %r\n      -> %r\n      期望 %r  幂等=%s'
          % ('OK ' if good else '**FAIL**', src, got, exp, idem))
print('\n单测:', 'ALL OK' if ok else '有 FAIL')
sys.exit(0 if ok else 1)

# -*- coding: utf-8 -*-
"""扫宏体里「占位符之外的硬编码英文」，防止中文客户端里贴出英文技能名。"""
import re
import sys

sys.path.insert(0, r'D:\workspace\DungeonsForever\_temp')
from cc_mac import MACROS

CMD = {
    'showtooltip', 'cast', 'castsequence', 'use', 'startattack', 'stopattack',
    'stopcasting', 'cleartarget', 'targetenemy', 'petattack', 'cancelform',
    'dismount', 'focus', 'targetlasttarget', 'swapactionbar', 'target',
    'petautocastoff', 'petautocaston', 'petfollow', 'petpassive',
    'petautocasttoggle', 'petstay',
}
bad = {}
for cls, lst in MACROS.items():
    for m in lst:
        body = (m['body'] or '')
        body = re.sub(r'\{[^}]*\}', '', body)
        body = re.sub(r'\[[^\]]*\]', '', body)
        body = re.sub(r'#[^\n]*', '', body)
        body = re.sub(r'/(?:[A-Za-z]+)', lambda mo: ' ' if mo.group(0)[1:].lower() in CMD else mo.group(0), body)
        body = re.sub(r'reset=[^ ]*', '', body)
        body = re.sub(r'[,;:|]', ' ', body)
        for tok in re.findall(r'[A-Za-z]{2,}', body):
            if tok.lower() in CMD:
                continue
            bad.setdefault(tok, []).append(cls + ':' + m['name_cn'])

print('硬编码英文残留：', len(bad))
for k, v in sorted(bad.items(), key=lambda x: -len(x[1])):
    print('  %-24s %2d  %s' % (k, len(v), ', '.join(v[:3])))

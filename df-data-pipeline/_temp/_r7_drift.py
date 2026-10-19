# -*- coding: utf-8 -*-
"""R7：源仓 vs beta 实机 全量漂移核对（只读）。"""
import hashlib
import os

SRC = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
EXTS = {'.lua', '.xml', '.toc', '.tga', '.blp', '.png', '.md', '.txt'}
REPORT = os.path.join(SRC, '_temp', '_r7_drift_report.txt')

LOG = []


def files(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('_temp', '.git')]
        for f in fn:
            if os.path.splitext(f)[1].lower() in EXTS:
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, root).replace('\\', '/')
                out[rel] = hashlib.md5(open(p, 'rb').read()).hexdigest()
    return out


s = files(SRC)
b = files(BETA)
only_s = sorted(set(s) - set(b))
only_b = sorted(set(b) - set(s))
diff = sorted(k for k in (set(s) & set(b)) if s[k] != b[k])

LOG.append('源文件数 = %d   beta 文件数 = %d' % (len(s), len(b)))
LOG.append('仅源有 (%d): %s' % (len(only_s), only_s or '无'))
LOG.append('仅 beta 有 (%d): %s' % (len(only_b), only_b or '无'))
LOG.append('内容不同 (%d): %s' % (len(diff), diff or '无'))
for k in ('Core/LootFilterUI.lua', 'Core/TierUI.lua',
          'Core/Data/Data_ClassGuide.lua', 'Core/Data/zhTW/Data_ClassGuide.lua',
          'Core/Data/enUS/Data_ClassGuide.lua'):
    LOG.append('  %s  src=%s  beta=%s  same=%s'
               % (k, (s.get(k) or '-')[:12], (b.get(k) or '-')[:12], s.get(k) == b.get(k)))

with open(REPORT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(LOG) + '\n')
print('report written: %s' % REPORT)

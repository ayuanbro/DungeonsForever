# -*- coding: utf-8 -*-
"""全树核对：开发仓 vs 客户端 beta（跳过 .git / .workbuddy / _temp / __pycache__）。"""
import hashlib
import os

DEV = r'D:\workspace\DungeonsForever'
CLI = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
SKIP_DIRS = {'.git', '.workbuddy', '_temp', '__pycache__', '_fc'}


def walk(root):
    out = {}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root).replace(os.sep, '/')
            out[rel] = hashlib.md5(open(p, 'rb').read()).hexdigest()
    return out


d, c = walk(DEV), walk(CLI)
only_dev = sorted(set(d) - set(c))
only_cli = sorted(set(c) - set(d))
diff = sorted(k for k in set(d) & set(c) if d[k] != c[k])
print('dev 文件数 %d / client 文件数 %d' % (len(d), len(c)))
print('仅 dev 有 %d: %s' % (len(only_dev), only_dev[:20]))
print('仅 client 有 %d: %s' % (len(only_cli), only_cli[:20]))
print('内容不同 %d: %s' % (len(diff), diff[:20]))

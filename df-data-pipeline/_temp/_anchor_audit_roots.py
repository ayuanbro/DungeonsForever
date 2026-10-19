# -*- coding: utf-8 -*-
"""对任意根（开发仓 / 隔离树）跑变异锚点体检，输出「总数 + 异常名清单」。

用法：
    python _temp/_anchor_audit_roots.py <root> [<root2> ...]

第 1 个根写完整清单；其余根只输出「相对第 1 根的差集」（多了/少了哪些异常）。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_mut_anchors as CA  # noqa: E402


def main():
    roots = sys.argv[1:]
    if not roots:
        print('用法：python _anchor_audit_roots.py <root> [<root2> ...]')
        return 2
    res = []
    for r in roots:
        total, bad = CA.audit(r)
        names = [b[0] for b in bad]
        res.append((r, total, names))
        print('=' * 74)
        print('%s : 共 %d 条，异常 %d 条' % (r, total, len(names)))
        for nm in names:
            print('   ✗ %s' % nm)
    base = set(res[0][2])
    for r, total, names in res[1:]:
        s = set(names)
        print('=' * 74)
        print('差集 %s  vs  基准 %s' % (r, roots[0]))
        print('  仅基准有（本根已修好/更少）: %d' % len(base - s))
        for nm in sorted(base - s):
            print('    - %s' % nm)
        print('  仅本根有（本根新增异常）: %d' % len(s - base))
        for nm in sorted(s - base):
            print('    + %s' % nm)
    return 0


if __name__ == '__main__':
    sys.exit(main())

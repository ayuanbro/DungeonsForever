# -*- coding: utf-8 -*-
"""全量预检：每一条变异的**字节锚点**在产物里是否恰好命中 1 次。

为什么要有这个脚本（2026-09-23 实锤）：
  `df_check_new_muts.py` 是一条一条跑的，锚点烂掉只会**静默跳过**——它死在
  `assert src.count(old) == 1`，而那要看运气（取决于排序位置），且**只跑 DEFAULT_WANT
  的子集时根本不会碰到**。本次真实事故：SwitchSub 从「二分流」长成「三分流」后，
  三条胶囊变异的锚点全部变成 0 次，`--all` 一跑才发现 —— 也就是在这之前，
  「胶囊：SwitchSub 又把 key 丢掉」等三条断言**实际上已经没人守了**。

  → 结论：改完生成物 / harness 后，**先跑本脚本**（秒级），再跑变异逐条隔离。

用法：
    python check_mut_anchors.py            # 全量体检，有异常则 exit 1
    python check_mut_anchors.py 胶囊        # 只看名字含该片段的
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ADDON = r'D:\workspace\DungeonsForever'
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'


def audit(root=ADDON, want=None, verbose=False):
    """返回 (总数, [(名字, 文件, 命中次数)])。root 换成 BETA 可对副本侧复核。"""
    import df_mut_check as M
    bad, total = [], 0
    for name, spec in M.MUTATIONS:
        if want and want not in name:
            continue
        total += 1
        fname, old, _new = M.split_spec(spec)
        p = os.path.join(root, *fname.split('/'))
        if not os.path.exists(p):
            bad.append((name, fname, -1))
            continue
        raw = open(p, 'rb').read()
        c = raw.count(M.to_file_style(old, raw))
        if c != 1:
            bad.append((name, fname, c))
        elif verbose:
            print('  [OK ] %s   <%s>' % (name, fname))
    return total, bad


def main():
    argv = [a for a in sys.argv[1:]]
    want = argv[0] if argv else None
    total, bad = audit(ADDON, want, verbose=bool(want))
    print('=' * 74)
    print('变异锚点体检（%s）：共 %d 条，异常 %d 条' % (ADDON, total, len(bad)))
    for name, fname, c in bad:
        reason = '文件不存在' if c < 0 else ('锚点 %d 次（要求恰好 1 次）' % c)
        print('  ✗ %s   <%s>  %s' % (name, fname, reason))
    if bad:
        print('\n★ 锚点烂掉是静默的：这条变异已经**没人守**了。'
              '去 df_mut_check.py 里改锚点。')
        print('⚠️ 不要再「改完重跑 mk_df_mut.py」—— 那个生成器已经落后于产物，'
              '重跑会静默删掉产物里手加的变异（已加安全闸：默认拒绝覆盖）。')
        sys.exit(1)
    print('  ✓ 全部锚点恰好命中 1 次')


if __name__ == '__main__':
    main()

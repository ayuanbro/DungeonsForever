# -*- coding: utf-8 -*-
"""QA 最终只读复核运行器：复用 qa_ext_cls.py 的 lua51 桩 harness。

用法：python _temp/qa_final_check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import qa_ext_cls as M  # noqa: E402

M.LUA_CASE = os.path.join(HERE, 'qa_q8994.lua')


def main():
    print('=' * 72)
    print('最终复核：全副本总览节点 / 详情页长链布局 / 池复用（TF_BUILD=%d）' % M.CLIENT_BUILD)
    print('=' * 72)
    M.PASSED.clear()
    M.FAILED.clear()
    M.part_b()
    print('=' * 72)
    print('通过 %d 项 / 失败 %d 项' % (len(M.PASSED), len(M.FAILED)))
    for f in M.FAILED:
        print('  ✗ %s' % f)
    return 0


if __name__ == '__main__':
    sys.exit(main())

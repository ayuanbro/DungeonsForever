# -*- coding: utf-8 -*-
"""QA 只读探针运行器：复用 qa_ext_cls.py 的 lua51 桩 harness，只换断言脚本。

用法：python _temp/qa_ext_impact.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import qa_ext_cls as M  # noqa: E402

M.LUA_CASE = os.path.join(HERE, 'qa_ext_impact.lua')


def main():
    print('=' * 72)
    print('影响面探针：字符串 q[9] 前置 → QuestName → format("%d") 抛错的实际后果')
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

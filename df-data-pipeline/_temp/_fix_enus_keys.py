# -*- coding: utf-8 -*-
"""gen_enus.py 补 3 个新 L 键（隐藏图钉/显示图钉/点击查看任务详情）。"""
src = open('_temp/gen_enus.py', encoding='utf-8').read()
a = "    '隐藏boss': 'Hide bosses', '显示boss': 'Show bosses',\n"
assert a in src, '锚点'
src = src.replace(a, a +
    "    # 2026-10-04 开关改管全部钉点，改名「隐藏图钉」（两种文案等宽 ⇒ 按钮宽度切换不跳）\n"
    "    '隐藏图钉': 'Hide pins', '显示图钉': 'Show pins',\n"
    "    '点击查看任务详情': 'Click to open quest',\n")
open('_temp/gen_enus.py', 'w', encoding='utf-8', newline='\n').write(src)
print('已补 3 键')

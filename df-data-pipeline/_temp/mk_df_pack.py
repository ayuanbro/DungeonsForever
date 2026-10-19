# -*- coding: utf-8 -*-
"""从上游 package_zip.py 派生 DungeonsForever 的打包脚本。

上游脚本本身已含本项目要求的两条校验（引用反向扫描 / 孤儿扫描），故只需换身份常量：
  · ADDON_NAME  → DungeonsForever
  · OUT_DIR     → D:/UGit/打包后/无限副本手册
  其余逻辑逐字不动。

用法：python mk_df_pack.py → 生成 ../_temp/package_zip.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SRC = os.path.join(os.path.dirname(DF), 'TalentsForever', '_temp', 'package_zip.py')
DST = os.path.join(HERE, 'package_zip.py')

text = open(SRC, encoding='utf-8').read()

REPL = [
    ('"""TalentsForever 发布打包脚本（打包方法参照 BGLite/_temp/package_zip.py）。',
     '"""无限副本手册 发布打包脚本（从 TalentsForever/_temp/package_zip.py 派生）。'),
    ('  1. 版本号从 TalentsForever.toc 的 ## Version 读取',
     '  1. 版本号从 DungeonsForever.toc 的 ## Version 读取'),
    ('  4. 生成 ZIP（内层顶层目录固定 TalentsForever/）+ SHA-256',
     '  4. 生成 ZIP（内层顶层目录固定 DungeonsForever/）+ SHA-256'),
    ('ADDON_NAME = "TalentsForever"', 'ADDON_NAME = "DungeonsForever"'),
    (r'OUT_DIR = r"D:\UGit\打包后\TalentsForever"', r'OUT_DIR = r"D:\UGit\打包后\无限副本手册"'),
]
for old, new in REPL:
    n = text.count(old)
    if not n:
        sys.exit('替换未命中：%s' % old)
    text = text.replace(old, new)
    print('  %-46s → %d 处' % (old[:46], n))

bad = [l for l in text.split('\n') if 'TalentsForever' in l
       and '派生' not in l and 'package_zip.py' not in l]
if bad:
    sys.exit('残留：\n  ' + '\n  '.join(bad[:5]))

open(DST, 'w', encoding='utf-8', newline='\n').write(text)
print('已生成 %s（%d 行）' % (DST, text.count('\n') + 1))

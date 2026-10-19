# -*- coding: utf-8 -*-
"""给数据生成器加「注释精简」收尾：生成完统一跑一次 strip_comments。

不这样就白清了 —— 生成器会把它写出的数据文件的中间注释原样带回来。
"""
import io

HELPER = '''

def _strip_comments_after_gen():
    """注释口径（2026-09-29 用户定）：每个 Lua 只留**文件头**注释块。
    生成器写出的数据文件会重带中间注释 —— 收尾统一跑一次，与手写件同口径。"""
    import os as _os
    import sys as _sys
    _here = _os.path.dirname(_os.path.abspath(__file__))
    if _here not in _sys.path:
        _sys.path.insert(0, _here)
    import strip_comments as _S
    n = 0
    for _p in _S.walk([_os.path.join(_os.path.dirname(_here), 'Core')]):
        _raw = open(_p, 'rb').read()
        _txt = _raw.decode('utf-8')
        _new, _c, _t = _S.strip_text(_txt)
        if _new != _txt:
            open(_p, 'wb').write(_new.encode('utf-8'))
            n += 1
    if n:
        print('注释精简：收尾清理 %d 个文件' % n)
'''

TASKS = [
    ('gen_zhtw_data.py',
     "if __name__ == '__main__':\n    main()\n",
     HELPER + "\n\nif __name__ == '__main__':\n    main()\n    _strip_comments_after_gen()\n"),
    ('gen_enus_data.py',
     "if __name__ == '__main__':\n    main()\n",
     HELPER + "\n\nif __name__ == '__main__':\n    main()\n    _strip_comments_after_gen()\n"),
    ('fc_gen.py',
     "if __name__ == '__main__':\n    sys.exit(main())\n",
     HELPER + "\n\nif __name__ == '__main__':\n    _rc = main()\n    _strip_comments_after_gen()\n    sys.exit(_rc)\n"),
]

for fn, old, new in TASKS:
    src = io.open(fn, encoding='utf-8', newline='').read()
    if '_strip_comments_after_gen' in src:
        print('  %-22s 已带收尾，跳过' % fn)
        continue
    assert src.count(old) == 1, '%s 锚点命中 %d 次' % (fn, src.count(old))
    src = src.replace(old, new, 1)
    io.open(fn, 'w', encoding='utf-8', newline='').write(src)
    print('  %-22s 已加收尾' % fn)

# gen_locales.py 是模块级脚本（没有 main），直接在末尾追加
fn = 'gen_locales.py'
src = io.open(fn, encoding='utf-8', newline='').read()
if '_strip_comments_after_gen' in src:
    print('  %-22s 已带收尾，跳过' % fn)
else:
    if not src.endswith('\n'):
        src += '\n'
    src += HELPER + '\n_strip_comments_after_gen()\n'
    io.open(fn, 'w', encoding='utf-8', newline='').write(src)
    print('  %-22s 已加收尾' % fn)

print()
for fn in ('gen_zhtw_data.py', 'gen_enus_data.py', 'gen_locales.py', 'fc_gen.py'):
    import ast
    ast.parse(io.open(fn, encoding='utf-8').read())
    print('  %-22s AST OK' % fn)

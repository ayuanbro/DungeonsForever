# -*- coding: utf-8 -*-
"""只读：证明模板清理「只动了字符串常量里的注释行、没动任何代码结构」。

判定：
  ① 结构签名（把所有字符串常量换成 <str> 后重新 dump AST）= 备份/现状必须逐字相同；
  ② 每个变了的字符串常量必须满足 lua_strip(旧) == 新（注释被剥掉，代码行原样在）。
注意：NodeTransformer 会**就地替换父节点的字段** ⇒ sig 必须用新解析出来的树。
"""
import ast
import collections
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen_tpl_strip import lua_strip  # noqa: E402


def parse(path):
    return ast.parse(open(path, encoding='utf-8').read())


def sig(path):
    class T(ast.NodeTransformer):
        def visit_Constant(self, n):
            if isinstance(n.value, str):
                return ast.copy_location(ast.Constant(value='<str>'), n)
            return n

        def visit_JoinedStr(self, n):
            return ast.copy_location(ast.Constant(value='<str>'), n)

    t = T().visit(parse(path))
    ast.fix_missing_locations(t)
    return ast.dump(t)


def strs(path):
    return sorted(c.value for c in ast.walk(parse(path))
                  if isinstance(c, ast.Constant) and isinstance(c.value, str))


bad = []
nfile = 0
nstr = 0
for bak in sorted(glob.glob(os.path.join(HERE, '_tpl_bak_20261017', '*.py.bak'))):
    name = os.path.basename(bak)[:-4]
    cur = os.path.join(HERE, name)
    if not os.path.exists(cur):
        continue
    nfile += 1
    if sig(bak) != sig(cur):
        bad.append((name, '结构签名不一致（动了代码）'))
        continue
    ca = collections.Counter(strs(bak))
    cb = collections.Counter(strs(cur))
    removed = list((ca - cb).elements())      # 旧有今无
    added = list((cb - ca).elements())        # 今有旧无
    nstr += len(removed)
    # 每个「消失的旧串」剥完注释后，必须恰好等于某个「新出现的串」
    if collections.Counter(lua_strip(x) for x in removed) != collections.Counter(added):
        bad.append((name, '不是「只剥注释」：消失 %d 个 / 新增 %d 个，映射不相等'
                    % (len(removed), len(added))))
        continue
    for x in removed:
        if x.strip() and not x.lstrip().startswith('--') and '--' in x:
            # 代码行 + 行尾注释：剥完注释仍有代码，属合法
            pass
print('比对文件 %d 个；发生变化的字符串常量 %d 个' % (nfile, nstr))
print('不合规:', len(bad))
for n, m in bad:
    print('  ✗', n, m)

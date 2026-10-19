# -*- coding: utf-8 -*-
"""给「注释精简后锚点变短、命中多次」的 4 条变异补足锚点。

做法（全程 bytes 级，不碰 Edit —— Edit 会把本文件的 LF 写成双换行）：
  1) 用**清理前的备份**（_temp/_pre_comment_strip/*.bak）定位该变异的正确落点
     （旧锚带注释，在备份里唯一）；
  2) 从该落点向后逐行补足，直到「去注释后的锚」在清理后的产物里恰好命中 1 次；
  3) 把该变量定义整块改写成 _b(...) 形式（中文可直写，_b 内部 encode）。
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = r'D:\workspace\DungeonsForever'
BAK = os.path.join(HERE, '_pre_comment_strip')

WANT = ['到货后不打 __named', '任务行退回 Frame', '每轮底色复位', 'RequestItem 不再保证监听器']

raw = open('df_mut_check.py', encoding='utf-8').read()
tree = ast.parse(raw)
var_def = {}          # varname -> (value, lineno, end_lineno)
_env = {'__builtins__': {}}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 \
            and isinstance(node.targets[0], ast.Name):
        name = node.targets[0].id
        try:
            v = eval(compile(ast.Expression(node.value), '<def>', 'eval'), _env)
        except Exception:
            continue
        _env[name] = v          # 供后续表达式引用（如 _CMT.encode(...)）
        if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], bytes):
            var_def[name] = [v, node.lineno, node.end_lineno]

# 取「归一化后」的 MUTATIONS（含注释的 old 用 strip 后对比即可定位变量）


def split_raw(spec):
    if len(spec) == 2 and isinstance(spec[0], str):
        return spec[0], spec[1][0], spec[1][1]
    return 'Core/DungeonUI.lua', spec[0], spec[1]


def strip_cmt(seg):
    """与 df_mut_check._strip_cmt 同口径（此处独立实现，避免依赖归一化后的模块）。"""
    if b'--' not in seg:
        return seg
    out = []
    for ln in seg.decode('utf-8').replace('\r\n', '\n').split('\n'):
        cut = None
        i, n = 0, len(ln)
        while i < n:
            c = ln[i]
            if c == '-' and i + 1 < n and ln[i + 1] == '-':
                cut = i
                break
            if c == '"' or c == "'":
                j = i + 1
                while j < n:
                    if ln[j] == '\\':
                        j += 2
                        continue
                    if ln[j] == c:
                        j += 1
                        break
                    j += 1
                i = j
                continue
            i += 1
        if cut is None:
            out.append(ln)
        else:
            pre = ln[:cut].rstrip()
            if pre:
                out.append(pre)
    return '\n'.join(out).replace('\n', '\r\n').encode('utf-8')


def lit(seg):
    body = seg[:-2] if seg.endswith(b'\r\n') else seg
    lines = body.decode('utf-8').split('\r\n')
    if len(lines) == 1:
        return '_b(%r)' % lines[0]
    return ('(\n' + '\n'.join('    _b(%r) +' % l for l in lines[:-1])
            + '\n    _b(%r)\n)' % lines[-1])


sys.path.insert(0, HERE)
import df_mut_check as M  # noqa: E402

todo = []
for name, spec in M.MUTATIONS:
    if not any(w in name for w in WANT):
        continue
    fname, old, new = split_raw(spec)
    vname, vold = None, None
    for k, (vv, _a, _b) in var_def.items():
        if strip_cmt(vv[0]) == old:
            vname, vold = k, vv[0]
            break
    assert vname, '找不到变量：' + name
    todo.append((name, fname, vold, new, vname))
    print('  %-46s %-30s var=%s' % (name, fname, vname))

print()
newdefs = {}
for name, fname, old, new, vname in todo:
    bpath = os.path.join(BAK, *fname.split('/')) + '.bak'
    bak = open(bpath, 'rb').read()
    cur = open(os.path.join(ADDON, *fname.split('/')), 'rb').read()
    pos = bak.find(old)
    assert pos >= 0, '备份里找不到原锚：' + name
    chosen = None
    for k in range(0, 20):
        end = pos + len(old)
        add = b''
        for _ in range(k):
            i = bak.find(b'\r\n', end)
            if i < 0:
                break
            add += bak[end:i + 2]
            end = i + 2
        cand_old = strip_cmt(old + add)
        if cur.count(cand_old) == 1:
            chosen = (cand_old, new + strip_cmt(add), k)
            break
    assert chosen, '补足失败：' + name
    cand_old, cand_new, k = chosen
    print('  %-46s 向后补 %d 行 → 命中 1 次' % (name, k))
    newdefs[vname] = (lit(cand_old), lit(cand_new))

src_lines = raw.split('\n')
edits = []
for k, (dold, dnew) in newdefs.items():
    a, b = var_def[k][1], var_def[k][2]
    edits.append((a, b, '%s = (\n    %s,\n    %s,\n)'
                  % (k, dold.replace('\n', '\n    '), dnew.replace('\n', '\n    '))))
edits.sort(reverse=True)
for a, b, text in edits:
    src_lines[a - 1:b] = text.split('\n')

out = '\n'.join(src_lines)
if 'def _b(*lines):' not in out:
    anchor = 'import sys\n'
    helper = ("\n\ndef _b(*lines):\n"
              "    return ('\\r\\n'.join(lines) + '\\r\\n').encode('utf-8')\n")
    assert out.count(anchor) == 1
    out = out.replace(anchor, anchor + helper, 1)

with open('df_mut_check.py', 'w', encoding='utf-8', newline='') as f:
    f.write(out)
print()
print('已改写 %d 个变量定义（并补 _b 辅助）' % len(edits))

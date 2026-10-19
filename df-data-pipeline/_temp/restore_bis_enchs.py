# 一次性恢复：把 HEAD 版 Data_BIS.lua 各专精的 enchs={...} 字段插回当前文件（行号一一对应）
import subprocess

head = subprocess.check_output(
    ['git', 'show', 'df281e2:Core/Data/Data_BIS.lua']).decode('utf-8')
cur = open('Core/Data/Data_BIS.lua', encoding='utf-8').read()

hl = head.split('\n')
cl = cur.split('\n')
assert len(hl) == len(cl), f'行数不一致 HEAD={len(hl)} CUR={len(cl)}'

def extract(src, start):
    k = src.find('enchs={', start)
    if k < 0:
        return None
    m = k + len('enchs=')
    depth = 0
    i = m
    in_str = False
    while i < len(src):
        c = src[i]
        if in_str:
            if c == '"' and src[i - 1] != '\\':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    return src[k:i + 1]
        i += 1
    return None

out = []
restored = 0
for a, b in zip(hl, cl):
    if 'enchs={' in a and 'enchs={' not in b:
        i = a.find('enchs={')
        seg = extract(a, i)
        assert seg, '提取失败: ' + a[:80]
        anchor = '},rows={'
        j = b.find(anchor)
        assert j >= 0, 'rows 锚缺失: ' + b[:80]
        b = b[:j + 1] + ',' + seg + b[j + 1:]
        restored += 1
    out.append(b)

res = '\n'.join(out)
open('Core/Data/Data_BIS.lua', 'w', encoding='utf-8', newline='').write(res)
print('restored enchs blocks:', restored)
print('enchs total:', res.count('enchs='))

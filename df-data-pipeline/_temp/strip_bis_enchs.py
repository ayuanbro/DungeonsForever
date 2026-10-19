# 一次性清理：删除 Data_BIS.lua 各专精段中的 enchs={...} 字段（含嵌套大括号配平）
import re

PATH = 'Core/Data/Data_BIS.lua'
src = open(PATH, encoding='utf-8').read()

out = []
i = 0
removed = 0
while True:
    j = src.find('enchs={', i)
    if j < 0:
        out.append(src[i:])
        break
    out.append(src[i:j])
    # 大括号配平，k 指向 enchs={ 的 { 位置
    k = j + len('enchs=')
    depth = 0
    m = k
    in_str = False
    while m < len(src):
        c = src[m]
        if in_str:
            if c == '"' and src[m - 1] != '\\':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
        m += 1
    # 跳过整个 enchs={...}
    end = m + 1
    # 吃掉紧跟的逗号，避免留下空槽
    while end < len(src) and src[end] in ' ,\n':
        if src[end] == '\n':
            break
        end += 1
    if src[end - 1] == ',':
        end -= 1
    i = end
    removed += 1

res = ''.join(out)
open(PATH, 'w', encoding='utf-8', newline='').write(res)
print('removed enchs blocks:', removed)
print('enchs remains:', res.count('enchs='))

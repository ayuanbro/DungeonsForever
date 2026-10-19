# -*- coding: utf-8 -*-
"""恢复 Data_ProfRecipes.lua 被清空的 enchanting 段：
   ① 从 git HEAD 提取括号配平的完整段（enchants/favor/crafted）
   ② drops 回填 id（drop_loc.json，NPC 英文名精确→大小写不敏感）
   ③ enchants 行尾追 spell/created 两列（enchant_ids.json，fc_gen inject_enchant_ids 同口径）
   ④ 原位替换工作区文件里的 stub 段
"""
import json
import re
import subprocess
import sys

ROOT = r'D:\workspace\DungeonsForever'
LUA = ROOT + r'\Core\Data\Data_ProfRecipes.lua'
DLOC = ROOT + r'\_temp\_fc\data\drop_loc.json'
EIDS = ROOT + r'\_temp\_fc\data\enchant_ids.json'


def balanced(d, start):
    """从 start（指向 '{'）做括号配平，返回 end（含收尾 '}' 下标+1）。字符串感知。"""
    depth = 0
    i = start
    instr = False
    esc = False
    while i < len(d):
        ch = d[i]
        if esc:
            esc = False
        elif ch == '\\':
            esc = True
        elif ch == '"':
            instr = not instr
        elif not instr:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    raise RuntimeError('unbalanced')


head = subprocess.run(['git', '-C', ROOT, 'show', 'HEAD:Core/Data/Data_ProfRecipes.lua'],
                      capture_output=True, text=True, encoding='utf-8').stdout
i = head.find('    ["enchanting"] = {')
assert i > 0, 'HEAD 缺 enchanting 段'
b = head.index('{', i)
e = balanced(head, b)
seg = head[i:e]
assert seg.rstrip().endswith('}'), '段收尾异常'

dloc = json.load(open(DLOC, encoding='utf-8'))
by_lower = {k.lower(): v for k, v in dloc.items()}

# ① drops 回填 id
pat_drop = re.compile(r'(\{ npc="([^"]+)", zone="[^"]*", chance=[0-9.]+, lv=\{[^}]*\}) ?\}')
n_drop = [0, 0]


def sub_drop(m):
    entry, name = m.group(1), m.group(2)
    ent = dloc.get(name) or by_lower.get(name.lower())
    if ent and ent.get('id'):
        n_drop[0] += 1
        return entry + ', id=%d }' % int(ent['id'])
    n_drop[1] += 1
    return entry + ' }'


seg = pat_drop.sub(sub_drop, seg)

# ② enchants 行尾追 spell/created（15 字段口径 = ENCHANT_FIELDS）
eids = json.load(open(EIDS, encoding='utf-8'))
lines = seg.split('\n')
out = []
n_ench = [0, 0, 0]
for ln in lines:
    m = re.match(r'^(            \{ "([^"]+)",.*?\})(,?)$', ln)
    if m and re.search(r', (true|false|nil), (true|false|nil), \{?\}? \}$', m.group(1)) \
            and not re.search(r', \d+, \d+ \}$', m.group(1)):
        name = m.group(2)
        j = eids.get(name)
        if j:
            sp = j.get('spell')
            cr = j.get('created')
            n_ench[0] += 1
        else:
            sp = cr = None
            n_ench[1] += 1
        tail = ', %s, %s }' % (sp if sp else 'nil', cr if cr else 'nil')
        body = m.group(1)[:m.group(1).rfind('}')]
        out.append(body + tail + m.group(3))
    else:
        if re.match(r'^            \{ "', ln):
            n_ench[2] += 1
        out.append(ln)
seg = '\n'.join(out)

# ③ 原位替换工作区段（当前文件里可能是 stub 也可能是已恢复段，都整段换回）
cur = open(LUA, encoding='utf-8').read()
ci = cur.find('    ["enchanting"] = {')
assert ci > 0, '当前文件缺 enchanting 段'
cb = cur.index('{', ci)
ce = balanced(cur, cb)
cur2 = cur[:ci] + seg + cur[ce:]
open(LUA, 'w', encoding='utf-8', newline='').write(cur2)

print('drops 回填 id: %d / 未命中 %d' % (n_drop[0], n_drop[1]))
print('enchants 追 spell/created: %d 命中 / %d 未命中 / 其他行 %d' % (n_ench[0], n_ench[1], n_ench[2]))
print('段字节数: %d -> %d' % (ce - ci, len(seg)))

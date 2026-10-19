# -*- coding: utf-8 -*-
"""把 fc hidden-items 的 27 套部件清单落进 Data_RaidSets.lua（一次性）。

对齐规则：
- 专属 9 套按套装名精确匹配 → 整行替换 ids（5 套 { 0 } 占位换真 id，4 套已有且逐件一致仅校验）。
- t1 18 套按 fc set_id ↔ 数据 id 对齐（同为客户端 setID 体系）→ 在 name 行后插入 ids 行。

校验：27 套 / t1 18×6 件互异 / 专属 39 件互异 / 与 t1 不重叠。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
SETS_LUA = os.path.join(DF, 'Core', 'Data', 'Data_RaidSets.lua')
SRC_JSON = os.path.join(HERE, '_fc_hidden_sets.json')

EX_NAMES = {'迪菲亚执行者的套装', '克罗多克战甲', '紫罗兰巫师的法衣', '腐疗者的法衣',
            '卡利姆多的祝福', '同谋佳偶', '瘟疫之地骑手', '加利亚斯适应外衣', '祝福板甲'}


def main():
    fc = json.load(open(SRC_JSON, encoding='utf-8'))
    assert len(fc) == 27, 'fc 清单应 27 套，实得 %d' % len(fc)
    by_name = {s['name']: s for s in fc if s['name'] in EX_NAMES}
    by_sid = {int(s['set_id']): s for s in fc if s['name'] not in EX_NAMES}
    assert len(by_name) == 9 and len(by_sid) == 18

    src = open(SETS_LUA, encoding='utf-8').read().replace('\r\n', '\n')

    # ── 1) 专属 9 套：整行替换 ids ──────────────────────────────────────
    ex_replaced = 0
    for name, s in by_name.items():
        pat = re.compile(
            r'(          name  = "%s",\n)          ids   = \{[^}]*\} \},' % re.escape(name))
        m = pat.search(src)
        assert m, '专属套找不到：%s' % name
        old_ids = re.findall(r'\d+', src[m.start():m.end()])
        new_line = '          ids   = { %s } },' % ', '.join(str(p['id']) for p in s['pieces'])
        if old_ids == [str(p['id']) for p in s['pieces']]:
            print('  [同] %-12s %d 件（已有，逐件一致）' % (name, len(s['pieces'])))
            continue
        assert set(old_ids) <= {'0'} or old_ids == ['0'], \
            '专属套 %s 旧 ids 非占位却不同：%s' % (name, old_ids)
        src = src[:m.start()] + m.group(1) + new_line + src[m.end():]
        ex_replaced += 1
        print('  [换] %-12s { %s } → %d 件真 id' % (name, ', '.join(old_ids), len(s['pieces'])))
    assert ex_replaced == 5, '应恰好替换 5 套占位，实得 %d' % ex_replaced

    # ── 2) t1 18 套：name 行后插 ids 行（按 set_id ↔ id 对齐）──────────
    name_re = re.compile(
        r'          name = "[^"]+",\n(?=          bonuses = \{)')
    # 只对 t1 记录生效：逐段定位（class 行含 batch = "t1" 的记录）
    parts, pos, t1_n = [], 0, 0
    for rec in re.finditer(
            r'        \{ class = "[A-Z]+", id = (?P<id>\d+),.*?revealed = true,\n(?=          name = )',
            src, re.S):
        seg_start = src.find('          name = ', rec.end())   # name 行开始
        parts.append(src[pos:seg_start])
        pos = seg_start
        mm = re.match(name_re, src[seg_start:])
        assert mm, 't1 id %s 的 name 行形态不对' % rec.group('id')
        sid = int(rec.group('id'))
        s = by_sid[sid]
        parts.append(mm.group(0))
        parts.append('          ids   = { %s },\n' % ', '.join(str(p['id']) for p in s['pieces']))
        pos += len(mm.group(0))
        t1_n += 1
        print('  [加] t1 id %d ← fc set %s（%s）6 件' % (sid, s['set_id'], s['name']))
    parts.append(src[pos:])
    src = ''.join(parts)
    assert t1_n == 18, '应插入 18 套 t1 ids，实得 %d' % t1_n

    # ── 3) 全表校验 ────────────────────────────────────────────────────
    all_ids = [int(x) for x in re.findall(r'ids   = \{ ([0-9, ]+) \}', src)
               for x in x.split(', ')]
    assert len(all_ids) == 108 + 39, '总件数应 147，实得 %d' % len(all_ids)
    assert len(set(all_ids)) == 147, '部件 id 有重复'
    # 区段抽查（fc set 2102 首件 / 2098 首件 / 2115 首件；祝福板甲末件）
    for need in (280904, 280455, 280992, 250586, 286978, 285331, 284715, 284102):
        assert need in all_ids, '抽查件 %d 缺失' % need
    assert '{ 0 }' not in src and '{ 0},' not in src, '{ 0 } 占位仍残留'
    print('[OK] 27 套全量：t1 108 件 + 专属 39 件，互异无重复，抽查 8 件全中，{ 0 } 占位已清零')

    open(SETS_LUA, 'w', encoding='utf-8', newline='\n').write(src)
    print('已写 %s (%d B)' % (SETS_LUA, len(src.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())

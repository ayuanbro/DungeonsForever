# -*- coding: utf-8 -*-
"""坐骑来源 NPC 落数据：
1. Data_CollectionMounts.lua：为有来源 NPC 的条目追加命名键 npcs = { { npcID, "名字" }, ... }
   （既有 [6]-[12] 指南侧手工补；新条目来自 _wh_mount_npcs.json）
2. Data_NPCLoc.lua：排序插入 _wh_mount_npcloc.json 里带 g_mapperData 点位的 NPC（基表，
   zhTW/enUS 覆盖层由 gen_zhtw_data / gen_enus_data 重生成）
"""
import json, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

MOUNTS = 'Core/Data/Data_CollectionMounts.lua'
NPLOC = 'Core/Data/Data_NPCLoc.lua'

# wowhead 未本地化 NPC 的名字覆写（与 details 文案一致 / 指南侧既有叫法）
NAME_OVERRIDE = {
    218537: '迈克尼尔·瑟玛普拉格',
    256736: '休伊·桑尼戴尔',
    256400: '奥卡玛什',
    265756: '吉恩·费尔威瑟',
}


def clean_name(nm):
    nm = (nm or '').strip().strip('[]')
    return nm


def npcs_lua(arr):
    parts = ['{ %d, "%s" }' % (nid, name) for nid, name in arr]
    return 'npcs = { ' + ', '.join(parts) + ' }'


def main():
    # ── 1. mounts 表加 npcs 字段 ──────────────────────────────
    data = json.load(open('_temp/_wh_mount_npcs.json', encoding='utf-8'))
    byItem = data['byItem']
    # 指南侧既有条目的来源 NPC
    byItem['269681'] = [{'id': 265756, 'name': '吉恩·费尔威瑟'}]
    byItem['269683'] = [{'id': 265756, 'name': '吉恩·费尔威瑟'}]
    byItem['274930'] = [{'id': 265756, 'name': '吉恩·费尔威瑟'}]
    byItem['269671'] = [{'id': 265756, 'name': '吉恩·费尔威瑟'}]
    byItem['269678'] = [{'id': 265756, 'name': '吉恩·费尔威瑟'}]
    byItem['274933'] = [{'id': 265756, 'name': '吉恩·费尔威瑟'}]
    byItem['262766'] = [{'id': 256736, 'name': '休伊·桑尼戴尔'},
                        {'id': 256400, 'name': '奥卡玛什'}]

    src = open(MOUNTS, encoding='utf-8', newline='').read()
    assert src.count('\r\n') == 0
    patched = 0
    for iid_str, arr in byItem.items():
        iid = int(iid_str)
        npcs = []
        for x in arr:
            nid = int(x['id'])
            nm = NAME_OVERRIDE.get(nid) or clean_name(x['name'])
            if nm and all(nid != p[0] for p in npcs):
                npcs.append((nid, nm))
        if not npcs:
            continue
        anchor = '= { %d,' % iid
        pos = src.find(anchor)
        if pos < 0:
            print('!! item %d entry not found' % iid)
            continue
        if src[pos:pos + 400].find('npcs =') >= 0:
            print('[SAME] item %d' % iid)
            continue
        # 条目两行：锚点行 + 详情行（详情行以 ' },' 收尾）
        line_end = src.index('\n', pos)
        entry_end = src.index('\n', line_end + 1)
        assert src[entry_end - 4:entry_end] == ' },\n' or src[entry_end - 3:entry_end] == ' },', \
            'item %d tail=%r' % (iid, src[entry_end - 12:entry_end])
        insert_at = src.rfind(' },', line_end, entry_end)
        src = src[:insert_at] + ', ' + npcs_lua(npcs) + src[insert_at:]
        patched += 1
    open(MOUNTS, 'w', encoding='utf-8', newline='\n').write(src)
    print('mounts npcs patched:', patched)
    raw = open(MOUNTS, 'rb').read()
    print('  CRLF:', raw.count(b'\r\n'), 'LF:', raw.count(b'\n'))

    # ── 2. NPCLoc 插入坐标行 ─────────────────────────────────
    nploc = json.load(open('_temp/_wh_mount_npcloc.json', encoding='utf-8'))
    rows = []
    for nid_str, v in nploc.items():
        if v.get('error') or not v.get('loc'):
            continue
        loc = v['loc']
        if not loc.get('zone'):
            continue
        nid = int(nid_str)
        rows.append((nid, '    [%d] = { %d, %.1f, %.1f, "%s" },'
                     % (nid, loc['map'], loc['x'], loc['y'], loc['zone'])))
    rows.sort()
    s = open(NPLOC, encoding='utf-8', newline='').read()
    added = 0
    for nid, row in rows:
        if '[%d] =' % nid in s:
            print('[SAME] NPCLoc[%d]' % nid)
            continue
        m_open = re.search(r'\nns\.NPCLoc = \{', s)
        assert m_open, 'NPCLoc 表头找不到'
        end = s.index('\n}', m_open.end())
        seg = s[m_open.end():end]
        keys = [(int(m.group(1)), m.start()) for m in re.finditer(r'\n    \[(\d+)\] =', seg)]
        bigger = [k for k in keys if k[0] > nid]
        pos = m_open.end() + (min(bigger, key=lambda x: x[1])[1] if bigger else len(seg))
        s = s[:pos] + '\n' + row + s[pos:]
        added += 1
    open(NPLOC, 'w', encoding='utf-8', newline='\n').write(s)
    print('NPCLoc added:', added, '/', len(rows))
    raw = open(NPLOC, 'rb').read()
    print('  CRLF:', raw.count(b'\r\n'))
    for _, row in rows[:5]:
        print(' ', row.strip())


if __name__ == '__main__':
    main()

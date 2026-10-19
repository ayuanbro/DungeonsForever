# -*- coding: utf-8 -*-
"""第三轮修正：以英文 _cg_parsed.json 为锚，逐条修正 Forever 漏网译文。

只改 _temp/_cg_trans/*.json 的对应 flow 元素；写回保持原格式（indent=1，无尾换行）。
每条编辑都带「唯一性/存在性」断言，任何一条不满足即非零退出（不静默）。
用法：python _temp/_fix_forever_v3.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TD = os.path.join(HERE, '_cg_trans')


def load(spec):
    with open(os.path.join(TD, spec + '.json'), encoding='utf-8') as fh:
        return json.load(fh)


def save(spec, obj):
    with open(os.path.join(TD, spec + '.json'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, indent=1))


def tsec(tr, key):
    for s in tr['sections']:
        if s.get('key') == key:
            return s
    raise SystemExit('缺 section: %s' % key)


# mode='sub'：把元素 v 里 old 唯一替换为 new；mode='set'：整段替换为 new
EDITS = [
    # 1
    ('druid_restoration', 'races', 6, 'sub', '《魔兽世界：永燃》', '《魔兽世界：无限》'),
    # 2
    ('druid_restoration', 'prof', 1, 'sub', '《魔兽世界：永驻》', '《魔兽世界：无限》'),
    # 3
    ('druid_restoration', 'prof', 4, 'sub', '《魔兽世界：永驻》', '《魔兽世界：无限》'),
    # 4
    ('hunter_beast-mastery', 'changes', 0, 'sub', '在《魔兽世界》怀旧服中', '在《魔兽世界：无限》中'),
    # 5 —— 根因：译文 ul 首项「耐力」被复制、末项「暴击」掉队，残片漏进下一格；
    #       故一并修复 ul[3] 与 [5]（否则该 section 仍错位）。
    ('hunter_survival', 'systems', 3, 'set', None, [
        {'icon': '', 'text': '耐力：玩家每 1 点耐力为宠物提供 2 点生命值'},
        {'icon': '', 'text': '护甲：宠物获得玩家护甲值的 30%'},
        {'icon': '', 'text': '攻击强度：宠物获得玩家最高攻击强度来源的 10%'},
        {'icon': '', 'text': '暴击：宠物获得玩家暴击率的 100%'},
    ]),
    ('hunter_survival', 'systems', 4, 'set', None,
     '宠物在无限服中获得了值得注意的改动。如今所有宠物种类都至少拥有一个独特技能，'
     '其中一些在 PvE 场景中非常实用，另一些则在 PvP 中大放异彩。'
     '猎人宠物现在也会随我们的属性成长，具体如下：'),
    ('hunter_survival', 'systems', 5, 'set', None,
     '所有这些信息也可以在角色界面的宠物面板中查看和了解。'
     '宠物现在还会拥有闪避属性，并且无法再享受其他职业的增益效果。'),
    # 6 —— 根因：译文 [0] 错位为 [5] 内容、[2] 错位为 [0] 内容、[3] 前缀混入标题；
    #       一并修复 [0]/[2]/[3]。
    ('hunter_survival', 'races', 0, 'set', None,
     '为了让所有种族特长都同样出色，各种族的种族特长都经历了不少改动。'
     '就目前而言，有些种族总体上似乎更强，而另一些则可能在某种特定玩法中大放异彩。'
     '在无限服中，人类现在可以成为猎人，还可以选择新增的 Skyborne 种族。'),
    ('hunter_survival', 'races', 2, 'set', None, '无限服新增的职业-种族组合'),
    ('hunter_survival', 'races', 3, 'set', None,
     '|s1259707|Skyborne 如果战斗中存在任何元素生物，Skyborne 的种族天赋必定能让他们占据榜首位置。'
     '虽然暴雪试图让所有种族的种族天赋具备竞争力，但他们仍未放弃针对特定怪物类型的专属加成。'
     '另一个能为你的 DPS 提供可观加成的，是|s1259710|. 急速在经典服中非常稀有，'
     '因此这个效果可能比你想象中更强。'),
    # 7
    ('priest_discipline', 'changes', 0, 'sub', '在《魔兽世界》资料片中', '在《魔兽世界：无限》中'),
    # 8
    ('priest_discipline', 'changes', 1, 'sub', '《魔兽世界:资料片》', '《魔兽世界：无限》'),
    # 9
    ('priest_shadow', 'changes', 4, 'sub', '暗影牧师在魔兽世界中', '暗影牧师在《魔兽世界：无限》中'),
    # 10
    ('priest_shadow', 'viability', 0, 'sub', '虽然Forefore开发团队', '虽然无限开发团队'),
    # 11
    ('rogue_subtlety', 'races', 12, 'sub', '对于怀旧服中的部落盗贼', '对于无限服中的部落盗贼'),
    # 12
    ('shaman_elemental', 'beginner', 0, 'sub', '在永夜服目前的情况下', '在无限服目前的情况下'),
    # 13
    ('shaman_restoration', 'races', 2, 'set', None, '无限服新增的职业-种族组合'),
    # 14
    ('shaman_restoration', 'prof', 0, 'sub', '《永远的魔兽世界》', '《魔兽世界：无限》'),
    # 15
    ('warlock_affliction', 'races', 0, 'sub',
     '新增的种族/职业组合现在包括巨魔术士。', '无限服新增的种族/职业组合现在包括巨魔术士。'),
    # 16
    ('warlock_demonology', 'races', 0, 'sub',
     '就术士而言，', '无限服新增的种族/职业组合现在包括巨魔术士。就术士而言，'),
    # 17
    ('warlock_destruction', 'races', 0, 'sub',
     '新的种族/职业组合现已加入巨魔术士。', '无限服新增的种族/职业组合现已加入巨魔术士。'),
    # 18
    ('warrior_arms', 'races', 9, 'sub',
     '但在经典赛季中更偏向 PvP 导向', '但在《魔兽世界：无限》中更偏向 PvP 导向'),
    # 19
    ('warrior_arms', 'races', 16, 'sub', '武器战士专业', '无限服中武器战士的专业'),
]


def main():
    # 先把涉及的文件全部载入（同一文件多处编辑只写一次）。
    cache = {}
    for spec, key, idx, mode, old, new in EDITS:
        tr = cache.get(spec)
        if tr is None:
            tr = cache[spec] = load(spec)
        sec = tsec(tr, key)
        flow = sec['flow']
        if idx >= len(flow):
            raise SystemExit('越界: %s/%s#%d (len=%d)' % (spec, key, idx, len(flow)))
        el = flow[idx]
        if mode == 'set':
            cur = el.get('v')
            if el.get('t') == 'ul':
                assert isinstance(cur, list), '%s/%s#%d 期望 ul 列表' % (spec, key, idx)
                el['v'] = new
            else:
                assert isinstance(cur, str), '%s/%s#%d 期望字符串' % (spec, key, idx)
                el['v'] = new
            print('SET  %-24s %-8s #%-2d  %s' % (spec, key, idx, str(new)[:48]))
        else:
            cur = el.get('v')
            assert isinstance(cur, str), '%s/%s#%d 期望字符串' % (spec, key, idx)
            cnt = cur.count(old)
            if cnt != 1:
                raise SystemExit('替换锚点非唯一(%d): %s/%s#%d old=%r'
                                 % (cnt, spec, key, idx, old))
            el['v'] = cur.replace(old, new)
            print('SUB  %-24s %-8s #%-2d  %r -> %r' % (spec, key, idx, old, new))
    for spec, tr in cache.items():
        # 回写前确认格式仍可无损：indent=1。
        save(spec, tr)
        print('WROTE', os.path.join(TD, spec + '.json'))
    print('\nDONE: %d edits across %d files.' % (len(EDITS), len(cache)))


if __name__ == '__main__':
    main()

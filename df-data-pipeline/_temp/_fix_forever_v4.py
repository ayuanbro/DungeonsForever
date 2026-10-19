# -*- coding: utf-8 -*-
"""第四轮修正：
  (A) 撤回 warlock_{affliction,demonology,destruction}/races#0 的「无限服」增译（英文那句无版本名）；
  (B) 补译两处结构性缺段（生成器曾把单行 tb 当表头吞掉）：
        paladin_protection/systems  在 idx=1 插入 EN[1] 的 Pro/Con 三列表；
        warrior_protection/changes  在 idx=3 起插入 EN[3]/[4]/[5] 三个要点 tb。
      使 CN 序列与（修复后的）EN 归一序列逐元素对齐。
写回保持原格式（indent=1，无尾换行）；每条编辑带断言，任何不满足即非零退出。
用法：python _temp/_fix_forever_v4.py
"""
import json
import os

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


# (A) 撤回增译：old 前缀 → new 前缀
REVERTS = [
    ('warlock_affliction', 'races', 0,
     '无限服新增的种族/职业组合现在包括巨魔术士。', '新增的种族/职业组合现在包括巨魔术士。'),
    ('warlock_demonology', 'races', 0,
     '无限服新增的种族/职业组合现在包括巨魔术士。就术士而言，', '就术士而言，'),
    ('warlock_destruction', 'races', 0,
     '无限服新增的种族/职业组合现已加入巨魔术士。', '新的种族/职业组合现已加入巨魔术士。'),
]

# (B) 在 flow 的 at 处连续插入若干 tb；assert 该位置原元素类型 == prev_t
INSERTS = [
    ('paladin_protection', 'systems', 1, 'ul', [
        {'t': 'tb', 'v': [[
            '优势：圣骑士在战斗开始时绝不会缺资源，可以毫无资源压力地打出整套技能。',
            '',
            '劣势：在持久战中，圣骑士必须谨慎管理法力，以免资源枯竭，'
            '而且往往需要等待法力恢复后才能迎战新的敌人。',
        ]]},
    ]),
    ('warrior_protection', 'changes', 3, 'ul', [
        {'t': 'tb', 'v': [['', '应对盾牌猛击的触发：这是你优先级较高的要点之一。'
                               '|s384041|天赋能让多个技能重置|s23922|的冷却，'
                               '而|s236279|则通过自动攻击达到相同效果。']]},
        {'t': 'tb', 'v': [['', '避免怒气浪费：既然我们的目标是尽可能多地产生怒气，'
                               '那么想把这些怒气全部用掉、一点不浪费也是理所当然的。'
                               '这意味着必须平衡怒气消耗，既避免断怒，又避免怒气溢出。'
                               '|s163201|、|s6572|和|s190456|等技能都能提供高效利用怒气的方式。']]},
        {'t': 'tb', 'v': [['', '冷却好了就用！我们手上有一整套进攻型冷却技能，'
                               '尽可能频繁地使用它们至关重要，'
                               '这样才能进一步同时最大化伤害输出与怒气获取！']]},
    ]),
]


def main():
    cache = {}

    def get(spec):
        tr = cache.get(spec)
        if tr is None:
            tr = cache[spec] = load(spec)
        return tr

    for spec, key, idx, old, new in REVERTS:
        el = tsec(get(spec), key)['flow'][idx]
        cur = el.get('v')
        assert isinstance(cur, str) and cur.count(old) == 1, \
            '撤回锚点异常: %s/%s#%d old=%r' % (spec, key, idx, old)
        el['v'] = cur.replace(old, new)
        print('REVERT %-22s %-8s #%-2d -> %s' % (spec, key, idx, new[:40]))

    for spec, key, at, prev_t, elems in INSERTS:
        flow = tsec(get(spec), key)['flow']
        assert at <= len(flow), '插入越界: %s/%s#%d (len=%d)' % (spec, key, at, len(flow))
        if at < len(flow):
            assert flow[at].get('t') == prev_t, \
                '插入位类型不符: %s/%s#%d 期望 %s 实际 %s' \
                % (spec, key, at, prev_t, flow[at].get('t'))
        for k, e in enumerate(elems):
            flow.insert(at + k, e)
        print('INSERT %-22s %-8s @%d  n=%d' % (spec, key, at, len(elems)))

    for spec, tr in cache.items():
        save(spec, tr)
        print('WROTE', os.path.join(TD, spec + '.json'))
    print('\nDONE: %d reverts, %d insert-groups across %d files.'
          % (len(REVERTS), len(INSERTS), len(cache)))


if __name__ == '__main__':
    main()

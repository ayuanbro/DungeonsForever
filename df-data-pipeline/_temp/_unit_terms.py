# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '_temp')
import fc_guide as F

cases = [
    # A. 漏网面
    ('裸永恆', '永恆', '《无限》'),
    ('裸永恒中', '永恒中', '无限服中'),
    ('在永恒里', '在永恒里', '在无限服里'),
    ('魔兽世界永恒(无书名号)', '魔兽世界永恒', '魔兽世界：无限'),
    ('魔兽世界：Forever', '魔兽世界：Forever', '魔兽世界：无限'),
    ('Forever服', 'Forever服', '无限服'),
    ('永恆服', '永恆服', '无限服'),
    ('永恆版本', '永恆版本', '无限版本'),
    # C. 测试服
    ('《永久 beta》', '《永久 beta》', '无限测试服'),
    ('《无限》测试服', '《无限》测试服', '无限测试服'),
    # B. 空白规整
    ('两侧空格', '而 《无限》 的', '而《无限》的'),
    ('尾空格', '《无限》 的目标', '《无限》的目标'),
    ('前空格', '过渡到 无限版本时', '过渡到无限版本时'),
    # 副词保护
    ('副词1', '攻击和法术的暴击率就永久提高 1%', '攻击和法术的暴击率就永久提高 1%'),
    ('副词2', '使你的最大生命值永久提升4%', '使你的最大生命值永久提升4%'),
    # 专名保护
    ('永恒之井', '永恒之井的水', '永恒之井的水'),
    # 怪搭配禁止
    ('魔兽世界：永久→', '《魔兽世界：永久》', '《魔兽世界：无限》'),
    ('WoW Forever', '在《WoW Forever》中', '在《魔兽世界：无限》中'),
]
ok = True
for name, src, exp in cases:
    got = F.normalize_terms(src)
    flag = 'OK' if got == exp else 'FAIL'
    if got != exp:
        ok = False
    print('  [%s] %-22s %r -> %r' % (flag, name, src, got))
print('UNIT normalize_terms:', 'ALL PASS' if ok else 'FAIL')

# 首次出现 → 全称
flow = [
    {'t': 'p', 'v': '武器战在《无限》中很强。'},
    {'t': 'p', 'v': '《无限》还能打PvP。'},
]
out = F.normalize_flow_terms(flow)
print('--- first-occurrence promotion ---')
for f in out:
    print('   ', repr(f['v']))
print('   expect first=全称, second=短名')

# 标题保护：标题里的 无限服 不升级，正文首个版本名才升级
flow2 = [
    {'t': 'p', 'v': '无限服新增的职业-种族组合'},
    {'t': 'p', 'v': '在《无限》中人类可当猎人。'},
]
out2 = F.normalize_flow_terms(flow2)
print('--- title protected ---')
for f in out2:
    print('   ', repr(f['v']))

# 幂等
out3 = F.normalize_flow_terms(out2)
print('   idempotent:', out3 == out2)

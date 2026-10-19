# -*- coding: utf-8 -*-
"""把 25 条失守变异的锚点原文 + 当前命中数全部摊开，供逐条重锚。"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BETA = r'D:\workspace\DungeonsForever'

NAMES = [
    "专业页：右栏备料清单跑回左栏",
    "专业页：配方详情条长回来",
    "专业页：名称→材料间距吃回 12（白没留给材料）",
    "专业页：材料组不再右对齐（左起摆）",
    "攻略：页签「攻略」被摘（入口消失）",
    "攻略：掉落滚动区不让位（两层叠着显示）",
    "探索：Build 不挂 ExploreModule（行池空）",
    "详情：行池每次强制新建行帧",
    "提示框：预热空转（不请求任何物品）",
    "名字可见：重扫不再跳过已到货的卡（每轮白刷）",
    "名字可见：到货后不打 __named 标记（会被反复重扫）",
    "名字可见：绑定时不记 __named（复用的卡会被漏掉）",
    "滚轮：掉落卡片不转发（压在卡上滚不动）",
    "任务页：不监听 QUEST_LOG_UPDATE（接任务不刷新）",
    "两列：右列详情不联动（渲染尾部摘 RenderQuestDetail）",
    "任务行退回 Frame（实机 OnClick 报错）",
    "详情页收获节没了（经验/金钱/声望）",
    "「任务需求」节不显示",
    "卡片墙：列数 3 -> 2",
    "卡片墙：摘掉每轮底色复位（悬停态会残留）",
    "加载：摘掉隐藏 tooltip 兜底触发",
    "加载：RequestItem 不再保证监听器就位",
    "胶囊：SwitchSub 又把 key 丢掉（永远只显示 5人本）",
    "Shift 点击：卡片退回 Frame（实机不支持 OnClick）",
    "升级 HUD：标签挂开关身上（被 ReskinToggle 的 PurgeNative 隐藏 = 实机看不到）",
]

spec = importlib.util.spec_from_file_location('dmut', os.path.join(HERE, 'df_mut_check.py'))
m = importlib.util.module_from_spec(spec); sys.modules['dmut'] = m; spec.loader.exec_module(m)

byname = {}
for name, s in m.MUTATIONS:
    byname[name] = s

cache = {}
def read(fname):
    if fname not in cache:
        cache[fname] = open(os.path.join(BETA, *fname.split('/')), 'rb').read()
    return cache[fname]

miss = [n for n in NAMES if n not in byname]
print('未在 MUTATIONS 找到的:', miss)
print('=' * 100)
for i, n in enumerate(NAMES, 1):
    s = byname.get(n)
    if s is None:
        print('%2d  [MISSING] %s' % (i, n)); continue
    fname, old, new = m.split_spec(s)
    data = read(fname)
    o = m.to_file_style(old, data)
    c = data.count(o)
    print('%2d  cnt=%d  %s' % (i, c, n))
    print('     file=%s' % fname)
    print('     OLD=%r' % (old[:240],))
    if c != 1:
        # 逐行片段，帮助定位
        lines = o.split(b'\n')
        print('     OLD 行数=%d 首行=%r' % (len(lines), lines[0][:120]))
    print('-' * 100)

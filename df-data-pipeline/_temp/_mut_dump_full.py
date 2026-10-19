# -*- coding: utf-8 -*-
"""导出 22 条真坏锚点的完整 old/new（解码文本），供逐条重锚决策。"""
import importlib.util, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BETA = r'D:\workspace\DungeonsForever'

spec = importlib.util.spec_from_file_location('dmut', os.path.join(HERE, 'df_mut_check.py'))
m = importlib.util.module_from_spec(spec); sys.modules['dmut'] = m; spec.loader.exec_module(m)

BROKEN = [
    "专业页：右栏备料清单跑回左栏",
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
    "Shift 点击：卡片退回 Frame（实机不支持 OnClick）",
]

byname = {n: s for n, s in m.MUTATIONS}
out = []
for i, n in enumerate(BROKEN, 1):
    s = byname[n]
    fname, old, new = m.split_spec(s)
    out.append('=' * 90)
    out.append('%2d. %s   [%s]' % (i, n, fname))
    out.append('--- OLD ---')
    out.append(repr(old.decode('utf-8')))
    out.append('--- NEW ---')
    out.append(repr(new.decode('utf-8')))
open(os.path.join(HERE, '_mut22_full.txt'), 'w', encoding='utf-8').write('\n'.join(out))
print('wrote _mut22_full.txt  lines=%d' % len(out))

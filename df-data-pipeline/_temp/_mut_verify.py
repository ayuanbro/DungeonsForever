# -*- coding: utf-8 -*-
"""逐条隔离 + **基线差集**：单独注入一条变异，看它是否产生了「基线里没有的」FAIL。

`_mut_isolate.py` 只比 FAIL 数（rc/FAIL/崩），而基线本来就挂着 22 条别的工作线的红断言
⇒ 它会把「本来就没红、注入后还是没红」也算成被保住。这里改成：先跑一遍未变异基线取
FAIL 集合，再逐条注入、取差集 —— 只有**新增**红才算这条变异的守卫真的非恒真。

跑完自动从 titan 端（干净）还原 beta。
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import df_mut_check as M   # noqa: E402

HERE = M.HERE
BETA = M.BETA
TITAN = M.TITAN
PY = sys.executable

TARGETS = [
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
    "Shift 点击：卡片退回 Frame（实机不支持 OnClick）",
    # 两条「冲突」变异（锚点健康，批量注入时被同段更早的吃掉）
    "胶囊：SwitchSub 又把 key 丢掉（永远只显示 5人本）",
    "升级 HUD：标签挂开关身上（被 ReskinToggle 的 PurgeNative 隐藏 = 实机看不到）",
]

byname = {n: s for n, s in M.MUTATIONS}
miss = [n for n in TARGETS if n not in byname]
if miss:
    print('!! 名字对不上：%s' % miss)
    sys.exit(2)


def run_harness():
    r = subprocess.run([PY, os.path.join(HERE, 'df_dungeon_check.py')],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.returncode, (r.stdout or '') + (r.stderr or '')


print('跑未变异基线…')
_rc0, base_out = run_harness()
base = set(M._fail_lines(base_out))
print('基线 FAIL %d 条' % len(base))
print('=' * 70)

caught, notcaught = [], []
for nm in TARGETS:
    fname, old, new = M.split_spec(byname[nm])
    p = os.path.join(BETA, *fname.split('/'))
    orig = open(p, 'rb').read()
    o, nw = M.to_file_style(old, orig), M.to_file_style(new, orig)
    if orig.count(o) != 1:
        print('%-44s !! 锚点 %d 次' % (nm, orig.count(o)))
        notcaught.append((nm, 'anchor'))
        continue
    open(p, 'wb').write(orig.replace(o, nw))
    try:
        rc, out = run_harness()
    finally:
        shutil.copyfile(os.path.join(TITAN, *fname.split('/')), p)
    crash = 'loadfile 返回 nil' in out or 'Traceback' in out
    cur = set(M._fail_lines(out))
    newf = sorted(cur - base)
    gone = sorted(base - cur)
    tag = 'OK  ' if (newf and not crash) else ('崩' if crash else '空')
    if newf and not crash:
        caught.append(nm)
    else:
        notcaught.append((nm, tag))
    print('%-44s 新增红=%-3d 崩=%-5s 消失=%-2d' % (nm, len(newf), crash, len(gone)))
    for x in newf[:4]:
        print('        + ' + x)
    if gone:
        for x in gone[:2]:
            print('        - ' + x)
print('=' * 70)
print('逐条有效 = %d / %d' % (len(caught), len(TARGETS)))
if notcaught:
    print('未生效：')
    for nm, t in notcaught:
        print('   [%s] %s' % (t, nm))

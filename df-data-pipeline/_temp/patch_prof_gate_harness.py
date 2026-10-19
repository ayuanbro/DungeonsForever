# -*- coding: utf-8 -*-
"""给 harness 补「专业页大列表分帧 + 顶部进度条」的静态断言（2026-10-09）。

落两处：已生成产物 df_dungeon_check.py + 生成器 mk_df_check.py（两者那几段断言文本逐字相同，
项目口径是「就地改产物 + 手动抄进生成器保一致」）。
幂等：new 已存在则 SKIP。
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)

ANCHOR = "    ck('★★ 升级分段行不写「技能」二字（用户：左边就 1➡11）',\n"

BLOCK = '''    # ★★ 2026-10-09：专业页大列表「分帧 + 主界面顶部进度条」（与副本掉落页同一套家伙）。
    #   配方页「全部」最多 300 条 —— 原来在渲染那一帧里同步建出全部行帧，弱机器上主线程
    #   一次堵上百毫秒。现在渲染只算版式：行帧记进待建表，按每帧预算逐批建；
    #   进度条 / 分帧器 / 每帧预算整个复用副本掉落页那边那一套（同一根条）。
    _paint = profui[profui.index('function PD.PaintRows'):
                    profui.index('function PD.RowBorder')]
    _paintlive = '\\n'.join(l.split('--')[0] for l in _paint.split('\\n'))
    ck('★★ 专业页大列表分帧：待建表 / 每帧预算 / 进度条三件齐备（与掉落页同一套）',
       'PD.ROW_SYNC_MAX = 20' in profui
       and 'function PD.RealizePendingRow(e)' in profui
       and 'function PD.BuildPendRows()' in profui
       and 'function PD.FlushPendingRows()' in profui
       and 'DG.Gate.Begin(n)' in profui
       and 'DG.Gate.Advance(1)' in profui
       and 'DG.PushStep(PD.BuildPendRows)' in profui
       and 'DG.RunSteps()' in profui
       and 'DG.LOOT_ROW_FRAME_CAP' in profui
       and 'DG.Loader.budgetMs' in profui)
    ck('★★ 渲染那一帧不再同步建行帧（PaintRows 里没有裸建帧 / 没有直取新行，收尾交分帧器）',
       'CreateFrame' not in _paintlive
       and 'PD.Row(i)' not in _paintlive
       and 'PD.rows[i]' in _paintlive
       and 'PD.FlushPendingRows()' in _paintlive)
    ck('★ 量小走快速通道（不闪进度条），量大才交分帧器',
       '    if n < PD.ROW_SYNC_MAX then\\n' in profui
       and 'DG.Gate.Begin(n)\\n' in profui)
    ck('★ 间距行（kind == "gap"）也进待建表（跳号会在行池里留空洞）',
       'PD.__pendRows[#PD.__pendRows + 1] = { idx = i, gap = true }' in profui)
    _pr = profui[profui.index('function PD.Render()'):
                 profui.index('function PD.RequestRows')]
    ck('★ 每轮渲染开头丢掉上一轮排下、还没建的行（否则它们会在新页面上冒出来）',
       'PD.__pendRows = {}' in _pr)
    ck('★ 设置页开关不对还没建出来的行取层级（nil 索引 = 整页炸）',
       'if PD.setOpen and spec.togKey and rr then' in profui)
    ck('★ 进度条自检入口（/dfprofgate，与 /dfgate 同款）',
       'function PD.StartGateDemo()' in profui
       and 'function PD.EndGateDemo()' in profui
       and 'SLASH_DUNGEONSFOREVERPROFGATE1 = "/dfprofgate"' in profui)
'''


def patch(rel):
    p = os.path.join(DF, '_temp', rel)
    txt = open(p, encoding='utf-8').read()
    if BLOCK in txt:
        print('  [SKIP] %s 已打过' % rel)
        return True
    n = txt.count(ANCHOR)
    if n != 1:
        print('  [BAD ] %s 锚点命中 %d 次（要求恰好 1 次）' % (rel, n))
        return False
    open(p, 'w', encoding='utf-8', newline='\n').write(txt.replace(ANCHOR, BLOCK + ANCHOR, 1))
    print('  [OK  ] %s 已插入 %d 行' % (rel, BLOCK.count('\n')))
    return True


def main():
    check = '--check' in sys.argv
    if check:
        for rel in ('df_dungeon_check.py', 'mk_df_check.py'):
            txt = open(os.path.join(DF, '_temp', rel), encoding='utf-8').read()
            print('  [%s] %s 锚点 %d 次 / 已打 %s'
                  % ('OK ' if txt.count(ANCHOR) == 1 else 'BAD',
                     rel, txt.count(ANCHOR), BLOCK in txt))
        return 0
    ok = all([patch('df_dungeon_check.py'), patch('mk_df_check.py')])
    return 0 if ok else 2


if __name__ == '__main__':
    sys.exit(main())

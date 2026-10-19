# -*- coding: utf-8 -*-
"""非恒真证明（**隔离副本树**版）：把「回潮」逐条注入副本，确认对应断言真的会红。

为什么不原地改实机侧：beta 侧会被并行会话镜像回去，注入中途可能被覆盖（曾出现「白测」：
注入后目标断言没红、复跑才正常）；原地改动也有被并发读到的风险。故改成：
    1. 整棵插件树 copytree 到系统临时目录
    2. 每条注入只改副本里的 Core/TierUI.lua，用 DF_ADDON_ROOT 重定向跑 _qa_probe_spec.py
    3. 要求「目标断言出现 FAIL」且「整体有 FAIL」，然后从内存里的基准文本还原副本再进下一条
    4. 结束前删除副本树（实机侧全程未动）

退出码：0 = 全部注入都被对应断言抓住；1 = 有注入漏网（该断言是恒真的）。

用法：python _probe_nonvacuous.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable or 'python'
PROBE = os.path.join(HERE, '_qa_probe_spec.py')
SRC_ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
REL = os.path.join('Core', 'TierUI.lua')

# (标签, 源码原文（count 必须恰为 1）, 替换成, 期望变红的断言名（子串）)
INJECTIONS = [
    ('I1 职业文字退回中性色',
     'cb.__txt:SetTextColor(cr, cg, cbc)',
     'cb.__txt:SetTextColor(Unpack(sel and C_WHITE or C_DIM))',
     '左列 9 职业条目文字 = 职业色'),
    ('I2 条目间距归零',
     'TT.NAV_ITEM_GAP = 4',
     'TT.NAV_ITEM_GAP = 0',
     '左列条目确实留了间距'),
    ('I3 递进退回条目高（间距不生效）',
     'y = y + TT.NAV_ITEM_STEP',
     'y = y + TT.NAV_ITEM_H',
     '左列职业条目纵向步进 == NAV_ITEM_STEP'),
    ('I4 页签字号改回 11',
     'TT.TAB_FS = 14',
     'TT.TAB_FS = 11',
     '页签字号钉死 14'),
    ('I5 板块页签单独写 11 绕过常量',
     'NewButton(page, "", 60, TT.SEC_TAB_H, TT.TAB_FS)',
     'NewButton(page, "", 60, TT.SEC_TAB_H, 11)',
     '页签字号钉死 14'),
    ('I6 「职业排行」被染成职业色',
     'TT.navBtn:GetFontString():SetTextColor(Unpack(rankSel and C_WHITE or C_DIM))',
     'TT.navBtn:GetFontString():SetTextColor(0.78, 0.61, 0.43)',
     '「职业排行」不是职业，文字保持中性色'),
    ('I7 瓦片尺寸被改小（16≠NAV_ICON）⇒ 蒙版圆角对不上',
     'MakeIconTile(cb, TT.NAV_ICON)', 'MakeIconTile(cb, 16)',
     '圆角瓦片帧里'),
    ('I8 选中描边恒 false ⇒ 左列永远没有金色描边',
     'SetOutline(cb, sel, 1, 0.82, 0)', 'SetOutline(cb, false, 1, 0.82, 0)',
     '左列选中行 = 金色描边'),
]


def run_probe(root):
    env = dict(os.environ)
    env['DF_ADDON_ROOT'] = root
    env.setdefault('PYTHONIOENCODING', 'utf-8')
    env.setdefault('PYTHONUTF8', '1')
    p = subprocess.run([PY, PROBE], cwd=HERE, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.decode('utf-8', 'replace')
    fails = [ln.strip() for ln in out.splitlines() if ln.strip().startswith('[FAIL]')]
    m = re.search(r'通过 (\d+) / 失败 (\d+)', out)
    passed = int(m.group(1)) if m else -1
    nfail = int(m.group(2)) if m else -1
    return out, fails, passed, nfail


def main():
    tmp = tempfile.mkdtemp(prefix='df_nv_')
    root = os.path.join(tmp, 'DungeonsForever')
    rc = 0
    try:
        shutil.copytree(SRC_ADDON, root)
        target = os.path.join(root, REL)
        with open(target, encoding='utf-8', newline='') as f:
            src = f.read()

        out, fails, passed, nfail = run_probe(root)
        print('副本树基线：通过 %d / 失败 %d %s' % (passed, nfail, '<== 应当为 0' if fails else ''))
        for ln in fails:
            print('   ', ln)
        if nfail != 0:
            print('!! 副本树基线就不干净，先查实机侧')
            return 2

        for title, old, new, expect in INJECTIONS:
            if src.count(old) != 1:
                print('!! %s：锚点 count=%d（应恰为 1）' % (title, src.count(old)))
                rc = 1
                continue
            with open(target, 'w', encoding='utf-8', newline='') as f:
                f.write(src.replace(old, new))
            out, fails, passed, nfail = run_probe(root)
            hit = [ln for ln in fails if expect in ln]
            print('%-38s 失败=%-3d 目标断言变红: %s'
                  % (title, nfail, 'YES' if hit else 'NO  <== 白测!'))
            if hit:
                print('       ', hit[0][:130])
            else:
                rc = 1
                for ln in fails[:6]:
                    print('       ', ln[:130])
            with open(target, 'w', encoding='utf-8', newline='') as f:
                f.write(src)

        # 还原核对：副本应与基准逐字节一致
        with open(target, encoding='utf-8', newline='') as f:
            back = f.read()
        print('\n副本还原一致：%s' % ('OK' if back == src else '!! 不一致'))
        if back != src:
            rc = 1
        if rc == 0:
            print('非恒真证明通过：%d 条注入全部被对应断言抓住。' % len(INJECTIONS))
        else:
            print('非恒真证明失败：存在漏网注入（对应断言是恒真的）。')
        return rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())

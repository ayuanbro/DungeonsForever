# -*- coding: utf-8 -*-
"""QA 独立探针：把 df_mut_check 的 6 条「v4 装备过滤面板」变异逐条注入**临时副本树**，
用（重定向 ADDON 的）qa_lf_verify 复跑，确认对应断言真的变红（非恒真）。

只读产品文件；所有破坏都发生在 _temp/_qa_mut_tree 副本里（跑完删除）。
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = r'D:\workspace\DungeonsForever'
WORK = os.path.join(HERE, '_qa_mut_tree')
PY = sys.executable

# (标签, 相对文件, old, new, 期望变红的断言关键字)
MUTS = [
    ('M#1 互斥失效（OpenConfig 不再收设置）', 'Core/LootFilterUI.lua',
     'if ns.CloseSettings then ns.CloseSettings() end', '-- MUT: no close settings',
     'v4 互斥·OpenConfig 里收起设置弹窗'),
    ('M#2 宽度退回 560', 'Core/LootFilterUI.lua',
     'popup:SetWidth(220)', 'popup:SetWidth(560)',
     'v4 落位·配置面板为右侧固定栏'),
    ('M#3 iOS 开关没了', 'Core/LootFilterUI.lua',
     'if ns.hui and ns.hui.ReskinToggle then ns.hui.ReskinToggle(tg) end', '-- MUT: toggle skin skipped',
     'v4 控件·勾选走 iOS 开关'),
    ('M#4 折叠三角不再朝下', 'Core/LootFilterUI.lua',
     'hdr.arrD:SetRotation(math.pi)', 'hdr.arrD:SetRotation(0)',
     'v4 折叠·展开态三角朝下'),
    ('M#5 词缀显示名映射被摘', 'Core/Data/Data_LootFilter.lua',
     '["特定法术强度"] = "法术伤害",', '-- MUT: label removed',
     'v4·D.ShuXingLabel 存在'),
    ('M#6 互斥只剩单向（MainFrame 不再收过滤）', 'Core/MainFrame.lua',
     'if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then ns.LootFilterUI:CloseConfig() end',
     '-- MUT: settings no longer closes loot filter panel',
     'v4 互斥·MainFrame 开设置'),
]


def build_tree():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    shutil.copytree(SRC, WORK, ignore=shutil.ignore_patterns('.git', '_temp', '__pycache__', '.svn'))
    # 重定向 ADDON 的验证脚本（放在 _temp 里，保证 import 得到 tf_dryrun / gen_zhtw_data / strip_comments）
    vsrc = open(os.path.join(HERE, 'qa_lf_verify.py'), encoding='utf-8').read()
    assert "ADDON = r'D:\\workspace\\DungeonsForever'" in vsrc
    vsrc = vsrc.replace("ADDON = r'D:\\workspace\\DungeonsForever'",
                        "ADDON = r'%s'" % WORK.replace('\\', '\\\\'))
    out = os.path.join(HERE, '_qa_mut_verify.py')
    open(out, 'w', encoding='utf-8').write(vsrc)
    return out


def main():
    ver = build_tree()
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    rc_all = 0
    for tag, rel, old, new, anchor in MUTS:
        path = os.path.join(WORK, *rel.split('/'))
        # 从镜像恢复干净
        shutil.copyfile(os.path.join(SRC, *rel.split('/')), path)
        raw = open(path, 'rb').read()
        b_old, b_new = old.encode('utf-8'), new.encode('utf-8')
        cnt = raw.count(b_old)
        if cnt != 1:
            print('  [SKIP] %s：锚点命中 %d 次（应为 1）' % (tag, cnt))
            rc_all = 1
            continue
        open(path, 'wb').write(raw.replace(b_old, b_new))
        proc = subprocess.run([PY, ver], cwd=HERE, env=env, capture_output=True, text=True,
                              encoding='utf-8', errors='replace')
        out = (proc.stdout or '')
        fails = [l.strip() for l in out.splitlines() if l.strip().startswith('✗')]
        hit = any(anchor in l for l in fails)
        print('  [%s] %s  exit=%d  命中期望断言=%s'
              % ('OK ' if (proc.returncode != 0 and hit) else 'FAIL', tag, proc.returncode, hit))
        if not hit:
            print('       该变异下 FAIL 清单：')
            for l in fails:
                print('         ' + l)
            rc_all = 1
        # 还原该文件，避免污染下一条
        shutil.copyfile(os.path.join(SRC, *rel.split('/')), path)
    shutil.rmtree(WORK, ignore_errors=True)
    try:
        os.remove(os.path.join(HERE, '_qa_mut_verify.py'))
    except OSError:
        pass
    print('=== 结论：%s ===' % ('全部 v4 变异均被对应断言抓住' if rc_all == 0 else '存在未被抓住的变异'))
    return rc_all


if __name__ == '__main__':
    sys.exit(main())

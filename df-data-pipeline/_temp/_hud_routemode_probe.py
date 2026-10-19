# -*- coding: utf-8 -*-
"""非恒真证明（2026-10-11）：把「错误写法」注入 HUD 源码副本，要求 _hud_routemode_smoke.py 变红。

只改 tempfile 副本树（DF_ADDON_ROOT 重定向），实机侧零触碰；每条注入后从内存基准还原副本再进下一条。
任何一条「没变红 / 目标断言没红」即整体非零退出。
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
SMOKE = os.path.join(HERE, '_hud_routemode_smoke.py')
PY = sys.executable
REL = 'Core/ProfFollow.lua'

MUTS = [
    ('自动门禁失效（HUD 永远固定路线）',
     '    if PD and PD.Setting and PD.Setting("autoRoute") and RA and RA.Available() then\n',
     '    if false then\n',
     '装 Auctionator 后 HUD 切成自动路线'),

    ('无价快照也切自动（不回固定）',
     '        if res and res.priced then return "auto", res.steps end\n',
     '        if res then return "auto", res.steps end\n',
     '自动有 Auctionator 但没价格数据'),

    ('段标掉模式前缀（数据换了但看不出）',
     '    f.seg:SetText(((mode == "auto") and L["自动计算"] or L["固定路线"]) .. " · "\n'
     '                  .. format(L["段落 %d / %d"], vi, #steps))\n',
     '    f.seg:SetText(format(L["段落 %d / %d"], vi, #steps))\n',
     '固定模式：段标为'),

    ('recMap 不再并 rinfo（附魔段显示「材料未收录」）',
     '        -- 自动 / 固定路线都可能引用 rinfo 里的法术（附魔配方游离在 enchants 之外、魔棒两头都不在）\n'
     '        local lv = LV[slug]\n'
     '        if lv and type(lv.rinfo) == "table" then\n'
     '            for spell, ri in pairs(lv.rinfo) do\n'
     '                if not c[spell] then c[spell] = ri end\n'
     '            end\n'
     '        end\n',
     '',
     '附魔全部段都能取到材料'),

    ('derivedStep 绕开 routeFor（段落指针按固定路线推）',
     'local function derivedStep(slug, skill)\n'
     '    local _, steps = routeFor(slug, skill)\n',
     'local function derivedStep(slug, skill)\n'
     '    local steps = LV[slug] and LV[slug].steps\n',
     '段落指针按自动路线推导'),

    ('shopList 绕开 routeFor（购物清单仍按固定路线）',
     'local function shopList(s)\n'
     '    local _, steps = routeFor(s.slug, s.skill)\n',
     'local function shopList(s)\n'
     '    local steps = LV[s.slug] and LV[s.slug].steps\n',
     '购物清单 = 自动路线现算'),

    ('Paint 绕开 routeFor（段卡仍按固定路线画）',
     '    local mode, steps = routeFor(slug, s.skill)\n    if not steps then f:Hide() return end\n',
     '    local mode, steps = "fixed", (LV[slug] and LV[slug].steps)\n    if not steps then f:Hide() return end\n',
     '自动模式段标与自动路线段数逐字对齐'),
]


def main():
    tmp = tempfile.mkdtemp(prefix='hudprobe_')
    try:
        tree = os.path.join(tmp, 'DungeonsForever')
        shutil.copytree(ADDON, tree)
        target = os.path.join(tree, *REL.split('/'))
        base = open(target, 'rb').read()
        assert b'\r\n' not in base, 'ProfFollow 期望 LF'

        env = dict(os.environ)
        env['DF_ADDON_ROOT'] = tree

        def run():
            r = subprocess.run([PY, SMOKE], capture_output=True, text=True,
                               encoding='utf-8', errors='replace', env=env)
            out = (r.stdout or '') + (r.stderr or '')
            fails = [l.split(']', 1)[1].strip().rstrip(' ')
                     for l in out.splitlines() if l.strip().startswith('[FAIL]')]
            # 断言名里带 [extra] 的，取到第一个 '  [' 之前
            fails = [f.split('  [')[0] for f in fails]
            return r.returncode, fails, out

        rc0, fails0, _ = run()
        print('基线：rc=%d 失败 %d 条' % (rc0, len(fails0)))
        assert rc0 == 0 and not fails0, '基线不干净，先修冒烟：%r' % fails0

        bad = 0
        for label, old, new, expect in MUTS:
            data = base.replace(old.encode('utf-8'), new.encode('utf-8'))
            if data == base:
                print('!! 锚点未命中：%s' % label)
                bad += 1
                continue
            open(target, 'wb').write(data)
            rc, fails, out = run()
            hit = any(expect in f for f in fails)
            ok = rc != 0 and hit
            print('%s %-14s 失败 %d 条  目标断言变红=%s'
                  % ('✓' if ok else '✗✗', label[:12], len(fails), 'YES' if hit else 'NO（白测!）'))
            if not ok:
                bad += 1
                print('    期望命中：%s' % expect)
                for f in fails[:8]:
                    print('      FAIL: %s' % f)
            open(target, 'wb').write(base)

        print('=' * 60)
        print('非恒真：%d/%d 条注入被目标断言抓住' % (len(MUTS) - bad, len(MUTS)))
        return 1 if bad else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())

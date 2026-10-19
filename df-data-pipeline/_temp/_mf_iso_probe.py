# -*- coding: utf-8 -*-
"""隔离变异探针：证明本轮新增的断言「非恒真」。

df_mut_check 是把全部变异一次性注入同一份文件、只要求 nfail>0，且它的 static_guard()
有 pre-existing 崩溃会挡住 main() 里的断言 —— 所以那种批次证明不了「这条断言真的抓住了
这个变异」。本探针改成：把变异**逐条单独**注入一份**副本树**，用重定向 ADDON 的
df_dungeon_check 复跑，断言对应那一条必须变红。

只读产品文件；所有破坏都发生在 _temp/_mf_tree 副本里（跑完删除）。

历史轮次（累积保留，脚本长期可重跑）：
  M#A/M#B  v4 收尾轮：标题口径提示进悬停框、方案设置/重置进右上角
  M#C/M#D/M#E  v5 轮：开关标签 14、标题行压缩、开关点击显式 SetChecked
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BETA = r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever'
WORK = os.path.join(HERE, '_mf_tree')

# (标签, 相对文件, old, new, 期望变红的断言名（必须出现在 FAIL 行里）)
MUTS = [
    ('M#A 标题口径提示从悬停框里摘掉', 'Core/LootFilterUI.lua',
     '        GameTooltip:AddLine(L["勾选 = 我需要"], 0.7, 0.75, 0.8, true)\n',
     '        -- MUT: hint dropped\n',
     'LFv4 标题口径提示改为悬停 tooltip'),
    ('M#B 方案设置 / 重置 退回第二行', 'Core/LootFilterUI.lua',
     '    reset:SetPoint("TOPRIGHT", popup, "TOPRIGHT", -CFG_PAD, CFG_HDR_Y)\n',
     '    reset:SetPoint("TOPRIGHT", popup, "TOPRIGHT", -CFG_PAD, -64) -- MUT\n',
     'LFv4 方案设置 / 重置 移入面板右上角'),
    ('M#C 开关标签字号退回 11', 'Core/LootFilterUI.lua',
     '    tg.label = MakeFS(parent, 14, C_TEXT, "LEFT")\n',
     '    tg.label = MakeFS(parent, 11, C_TEXT, "LEFT") -- MUT\n',
     'LFv5 面板字号统一'),
    ('M#D 标题行间距退回旧值', 'Core/LootFilterUI.lua',
     'local CFG_ROW1_Y, CFG_HDR_Y, CFG_SCROLL_TOP = -32, -8, 58\n',
     'local CFG_ROW1_Y, CFG_HDR_Y, CFG_SCROLL_TOP = -40, -12, 66 -- MUT\n',
     'LFv5 标题行压缩'),
    ('M#E 开关点击不再显式 SetChecked', 'Core/LootFilterUI.lua',
     '                    self:SetChecked(on)\n',
     '                    -- MUT: toggle never repaints on click\n',
     'LFv5 开关点击后立即重绘'),

    # ── 套装（2026-09-30 · 团本页第三签）路径：数据层 3 条 + 界面层 2 条 ──
    ('M#F 套装 id 编号被改坏（2098–2115 覆盖断裂）', 'Core/Data/Data_RaidSets.lua',
     '        { class = "WARRIOR", id = 2102, role = "dps", spec = "武器/狂怒", armor = "板甲",\n',
     '        { class = "WARRIOR", id = 2050, role = "dps", spec = "武器/狂怒", armor = "板甲",\n',
     '套装数据 = 18 套'),
    ('M#G 套装 role 退回中文字面量', 'Core/Data/Data_RaidSets.lua',
     '        { class = "PALADIN", id = 2107, role = "heal", spec = "神圣", armor = "板甲",\n',
     '        { class = "PALADIN", id = 2107, role = "治疗", spec = "神圣", armor = "板甲",\n',
     '套装 role 只许键'),
    ('M#H 套装数据层又长出部位字段', 'Core/Data/Data_RaidSets.lua',
     '        { class = "WARRIOR", id = 2103, role = "tank", spec = "防护", armor = "板甲",\n',
     '        { class = "WARRIOR", id = 2103, role = "tank", spec = "防护", armor = "板甲", slots = { 1, 2 },\n',
     '套装数据不存部位'),
    ('M#I 套装 CurTab 不再认 sets 态', 'Core/RaidUI.lua',
     '    if t == "list" or t == "sets" then return t end\n',
     '    if t == "list" then return t end -- MUT\n',
     '套装态被 CurTab 认作合法'),
    ('M#J 套装第三颗二级页签消失', 'Core/RaidUI.lua',
     '                   { key = "sets", text = L["套装"] } }',
     '                   } -- MUT\n',
     'RaidUI 二级页签 = 时间线 / 列表 / 套装'),

    # ── 套装版式二稿（2026-09-30 · 文本一律 14 / 芯片比照页签 / 卡片 L2+圆角）──
    #    五条都是**语法合法**的退化（改值、改实参），证明版式断言不是恒真。
    ('M#K 芯片高度脱离二级页签（退回 22）', 'Core/RaidUI.lua',
     'RU.SET_CHIP_H   = RU.TAB_H',
     'RU.SET_CHIP_H   = 22 -- MUT\n',
     '套装芯片尺度比照二级页签'),
    ('M#L 卡内标签字号退回 11', 'Core/RaidUI.lua',
     'c.labels[i] = MakeFS(c, 14, C_GOLD, "LEFT")',
     'c.labels[i] = MakeFS(c, 11, C_GOLD, "LEFT") -- MUT\n',
     '套装卡内文本全部 14 号'),
    ('M#M 卡片底色不再走 L2（圆角原语退回默认档）', 'Core/RaidUI.lua',
     'ns.hui.BuildRoundedBG(c, RU.SET_RADIUS, layer.L2, "both", true, 1)',
     'ns.hui.BuildRoundedBG(c, RU.SET_RADIUS, nil, "both", true, 1) -- MUT\n',
     '套装卡片底色 = HUI 色阶 L2'),
    ('M#N 左侧竖向强调条回潮（重新贴一条竖条）', 'Core/RaidUI.lua',
     '    local ih = CreateFrame("Frame", nil, c)\n',
     '    c.bar = c:CreateTexture(nil, "ARTWORK") -- MUT\n'
     '    c.bar:SetWidth(3)\n'
     '    local ih = CreateFrame("Frame", nil, c)\n',
     '套装卡片不再绘制左侧竖向强调条'),
    ('M#O 芯片文字丢掉职业色', 'Core/RaidUI.lua',
     'cr, cg, cb = ClassColorOf(item.key)',
     'cr, cg, cb = 1, 1, 1 -- MUT\n',
     '套装芯片文字取职业色'),

    # ── 套装版式三稿（2026-09-30 · 撤标注行 / 副行并入名称行）──
    ('M#P 卡内标注行回潮', 'Core/RaidUI.lua',
     '    c.labels, c.texts = {}, {}',
     '    c.labels, c.texts, c.marks = {}, {}, {}\n'
     '    c.marks[1] = MakeFS(c, 14, C_GREY, "LEFT") -- MUT\n',
     '套装卡不再渲染技能状态标注行'),
    ('M#Q 副行退回独占一行', 'Core/RaidUI.lua',
     '    c.sub:SetPoint("LEFT", c.name, "RIGHT", RU.SET_SUB_GAP, 0)',
     '    c.sub:SetPoint("TOPLEFT", c, "TOPLEFT", 48, -40) -- MUT\n',
     '套装副行并入名称行右侧'),
]

WATCH = ['LFv4 标题口径提示改为悬停 tooltip',
         'LFv4 方案设置 / 重置 移入面板右上角',
         'LFv5 面板字号统一',
         'LFv5 标题行压缩',
         'LFv5 开关点击后立即重绘',
         'RaidUI 二级页签 = 时间线 / 列表 / 套装',
         '套装态被 CurTab 认作合法',
         '套装数据 = 18 套',
         '套装 role 只许键',
         '套装数据不存部位',
         '套装卡内文本全部 14 号',
         '套装芯片尺度比照二级页签',
         '套装芯片等宽',
         '套装芯片文字取职业色',
         '套装卡片底色 = HUI 色阶 L2',
         '套装卡片不再绘制左侧竖向强调条',
         '套装卡不再渲染技能状态标注行',
         '套装副行并入名称行右侧']


def build_tree():
    if os.path.isdir(WORK):
        shutil.rmtree(WORK)
    shutil.copytree(BETA, WORK,
                    ignore=shutil.ignore_patterns('_temp', '__pycache__', '.git', '.svn'))
    src = open(os.path.join(HERE, 'df_dungeon_check.py'), encoding='utf-8').read()
    assert BETA in src, 'ADDON 常量没找到，检查器结构变了吗'
    out = os.path.join(HERE, '_mf_dcheck.py')
    open(out, 'w', encoding='utf-8').write(src.replace(BETA, WORK))
    return out


def run(checker):
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    p = subprocess.run([sys.executable, checker], cwd=HERE, env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode('utf-8', 'replace')


def main():
    checker = build_tree()
    rc_all = 0

    rc, out = run(checker)
    base_bad = [l for l in out.split('\n') if ' FAIL ' in l or l.strip().startswith('[FAIL]')]
    ok = (rc == 0 and not base_bad)
    print('[基线] 退出码=%d  失败行=%d  → %s' % (rc, len(base_bad), 'PASS' if ok else 'FAIL'))
    for w in WATCH:
        appeared = w in out
        print('       新增断言已执行=%s  <%s>' % (appeared, w))
        if not appeared:
            ok = False
    if not ok:
        rc_all = 1
        for l in base_bad[:10]:
            print('       ' + l)

    for label, rel, old, new, expect in MUTS:
        p = os.path.join(WORK, rel.replace('/', os.sep))
        raw = open(p, 'rb').read()
        b_old, b_new = old.encode('utf-8'), new.encode('utf-8')
        assert raw.count(b_old) == 1, '%s 锚点命中 %d 次' % (label, raw.count(b_old))
        open(p, 'wb').write(raw.replace(b_old, b_new))
        rc, out = run(checker)
        hit = [l for l in out.split('\n') if 'FAIL' in l and expect in l]
        # ★ 脏抓检测：注入后若是**语法错/异常**（loadfile 返回 nil、断言块抛异常），
        #   harness 照样非零退出、也照样会红 —— 看起来「被抓住」，其实没证明任何断言非恒真。
        #   （2026-09-30 踩到：删 defs 里一条却留下 `} }` 两个右花括号 = 多余一个，整文件编译失败。）
        dirty = ('loadfile 返回 nil' in out) or ('抛异常' in out)
        has_summary = ('通过 ' in out and '失败 ' in out)
        good = (rc != 0 and len(hit) == 1 and has_summary and not dirty)
        print('[%s] 退出码=%d  定向变红=%s  汇总行=%s  脏抓=%s  → %s'
              % (label, rc, 'YES' if hit else 'NO', 'YES' if has_summary else 'NO',
                 'YES' if dirty else 'NO', 'PASS' if good else 'FAIL'))
        if dirty:
            print('       ⚠ 脏抓：注入结果是语法错/异常，不是断言变红 —— 把变异改写成语法合法形态')
        if hit:
            print('       ' + hit[0].strip())
        else:
            for l in out.split('\n'):
                if 'FAIL' in l:
                    print('       其它红项: ' + l.strip())
        if not good:
            rc_all = 1
        open(p, 'wb').write(raw)  # 还原副本

    shutil.rmtree(WORK, ignore_errors=True)
    try:
        os.remove(checker)          # 重定向出来的临时检查器
    except OSError:
        pass
    print('副本树 + 临时检查器已删除；产品文件未触碰。RESULT=%s' % ('PASS' if rc_all == 0 else 'FAIL'))
    return rc_all


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""DungeonsForever 骨架层改名：Core/Hui/Bridge/MainFrame + TOC。
   只做点名替换（先长后短，避免 sub(1,14) 这类长度敏感串被误改），逐文件报告命中数。
   用法：python port_skeleton.py
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)

# 顺序有讲究：长度敏感 / 含旧名后缀的串必须先替换
RULES = [
    # Hui.lua 的帧名前缀判定：TalentsForever=14 字符，DungeonsForever=15，长度要一起改，
    # 否则「DungeonsForeve」也会被判成本插件自有帧
    (':sub(1, 14) == "TalentsForever"', ':sub(1, 15) == "DungeonsForever"'),
    # 图标素材统一 BLP（Media/DungeonsForever.blp，256×256 DXT5 带 mip）。
    # 上游那句是 TalentsForever.blp，经下方通用兜底规则自然得到 DungeonsForever.blp；
    # 本条只负责把历史产物里残留的 .tga 引用迁到 .blp（跑完即 0 命中，幂等）。
    ('DungeonsForever.tga', 'DungeonsForever.blp'),
    # 通用兜底：路径 / 帧名 / LDB 名 / LibDBIcon 注册名 / SV 名 / taint 标识
    ('TalentsForever', 'DungeonsForever'),
    # 中文标题与打印前缀
    ('无限天赋模拟器', '无限副本手册'),
]

# 目标文件：源文件 → 目标文件（骨架 4 个）。
# ⚠️ TOC 不在列：上游 TOC 的文件清单与 Notes（/tf、Sim.lua 等）都对本插件不成立，
#    必须手写（见 DungeonsForever.toc），不能用替换生成。
FILES = [
    ('Core/Core.lua', 'Core/Core.lua'),
    ('Core/Hui.lua', 'Core/Hui.lua'),
    ('Core/Bridge.lua', 'Core/Bridge.lua'),
    ('Core/MainFrame.lua', 'Core/MainFrame.lua'),
]

for srel, drel in FILES:
    src = os.path.join(DF, srel)
    if not os.path.exists(src):
        sys.stderr.write('missing: %s\n' % src)
        sys.exit(1)
    dst = os.path.join(DF, drel)
    raw = open(src, 'rb').read()
    crlf = raw.count(b'\r\n')
    text = raw.decode('utf-8')
    report = []
    for old, new in RULES:
        n = text.count(old)
        if n:
            text = text.replace(old, new)
        report.append('%s→%s %d' % (old, new, n))
    open(dst, 'wb').write(text.encode('utf-8'))
    print('%-24s CRLF=%-5d  %s' % (drel, crlf, ' | '.join(report)))

# 残留自检：本目录内不得再出现旧身份串。
# 放行两类：①ns.TalentSimFrame —— 有意保留的宿主字段名（少改一处无收益）；
#           ②LibUIDropDownMenu_BiaoGe 的 BiaoGe 是下拉库自身注册名，不可改。
# 注释里也不再有溯源说明（2026-09-23 起），故下方不再按「剥掉行尾注释」放行任何串。
BAD_CODE = [
    'TalentsForeverDB', 'TalentsForever_MainFrame', 'TalentsForever_SourceURL',
    'Interface\\AddOns\\TalentsForever', 'Interface/AddOns/TalentsForever',
    'ns.TalentSimUI', 'ns.TalentUI', 'ns.OpenTalentSim', 'TALENTSFOREVER',
]
BAD_ANY = ['无限天赋模拟器']


def code_of(line):
    """剥掉行尾注释：残留检测只关心代码部分。"""
    i = line.find('--')
    return line if i < 0 else line[:i]


bad = []
for root, _, names in os.walk(DF):
    if os.sep + '_temp' in root:
        continue
    for name in names:
        if not name.endswith(('.lua', '.toc', '.xml')):
            continue
        p = os.path.join(root, name)
        try:
            t = open(p, 'rb').read().decode('utf-8')
        except UnicodeDecodeError:
            continue
        rel = os.path.relpath(p, DF)
        for n, line in enumerate(t.replace('\r\n', '\n').split('\n'), 1):
            code = code_of(line)
            for kw in BAD_CODE:
                if kw in code:
                    bad.append('%s:%d 代码残留 %s' % (rel, n, kw))
            for kw in BAD_ANY:
                if kw in line:
                    bad.append('%s:%d 残留 %s' % (rel, n, kw))
if bad:
    sys.stderr.write('残留旧身份串：\n  ' + '\n  '.join(bad) + '\n')
    sys.exit(2)
print('残留自检通过：代码/文案中无旧身份串（ns.TalentSimFrame 已放行）')

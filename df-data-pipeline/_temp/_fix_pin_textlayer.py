# -*- coding: utf-8 -*-
# 2026-10-04 钉点图层第二轮：跨钉遮挡——入口钉「副本入口」文字盖住旁边任务钉的「!」。
#   解法：所有钉的名字挂进一个**先建**的低层文字容器 pinText（frame level 低于全部钉按钮），
#   图标（各按钮本体 + dot OVERLAY）整体压过全部文字，跨钉也成立。
#   显隐同步：池按钮单独 Hide 的两处循环补 nm:SetText("")（textLayer 不随按钮 Hide）。
import io


def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: anchor hit %d' % (tag, n)
    return src.replace(old, new, 1)


p = '../Core/MapUI.lua'
s = rd(p)

# ① 池构造：循环前建文字层
old1 = '''    frame.__pinsReady = true
    local pins = frame.pins
    local pinBtns = {}
    for i = 1, M.MAX_PINS do'''
new1 = '''    frame.__pinsReady = true
    local pins = frame.pins
    local pinBtns = {}
    -- ★ 文字层（2026-10-04 第二轮）：全部钉的名字挂这一个**先建**的低层容器——
    --   frame level 低于所有钉按钮 ⇒ 图标（按钮本体）压过全部文字，跨钉也成立
    --   （入口钉「副本入口」四个字不许糊掉旁边任务钉的黄「!」）。
    --   ㊟ pinText 挂 pins 之下，随容器整体显隐；池按钮单独 Hide 时须同步清文字（见 SyncPins）。
    local pinText = CreateFrame("Frame", nil, pins)
    pinText:SetAllPoints()
    frame.pinText = pinText
    for i = 1, M.MAX_PINS do'''
s = rep1(s, old1, new1, 'text layer create')

# ② nm 挂文字层
old2 = '''        bt.nm = MakeFS(bt, 14, C_GOLD, "CENTER")'''
new2 = '''        bt.nm = MakeFS(pinText, 14, C_GOLD, "CENTER") -- 挂文字层：图标永远盖得住（跨钉也是）'''
s = rep1(s, old2, new2, 'nm to text layer')

# ③ 两处隐藏循环补清文字
old3 = '''    for i = n + 1, M.MAX_PINS do frame.pinBtns[i]:Hide() end'''
new3 = '''    for i = n + 1, M.MAX_PINS do
        frame.pinBtns[i]:Hide()
        frame.pinBtns[i].nm:SetText("") -- 文字不随按钮 Hide，必须同步清（否则残留压图标）
    end'''
s = rep1(s, old3, new3, 'tail hide loop')

old4 = '''    if not show then
        for i = 1, M.MAX_PINS do frame.pinBtns[i]:Hide() end
    end'''
new4 = '''    if not show then
        for i = 1, M.MAX_PINS do
            frame.pinBtns[i]:Hide()
            frame.pinBtns[i].nm:SetText("") -- 同上：文字层不随按钮收，同步清
        end
    end'''
s = rep1(s, old4, new4, 'switch hide loop')

wr(p, s)
print('MapUI.lua: 文字层改造 4 处完成')

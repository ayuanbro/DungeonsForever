# -*- coding: utf-8 -*-
"""快捷栏 v4 一次性补丁（幂等：每个锚点先验 count==1，已打过就跳过）。

用户 2026-09-30 三项：
  ① 分组头「推荐五人本 / 专业 / 探索」字号 11 → 14（与按钮文字同号）；
  ② 「全部副本」从副本组尾条挪到「推荐五人本」分组头**上方**；
  ③ 专业条目内嵌 16px **圆角**图标（单独一层与图标等大的帧挂圆角蒙版）。

只动 Core/QuickBar.lua；二进制读写保 LF 行尾。
"""
import os
import sys

SRC = r'D:\workspace\DungeonsForever\Core\QuickBar.lua'

EDITS = []


def E(old, new):
    EDITS.append((old, new))


# ---- ① 头部注释：把新口径写进契约 -------------------------------------------
E('--   约束：字号仅 11 / 14 / 16；面板宽 120（左右内边距 8 → 内容宽 104）；\n'
  '--         标题「5人本专业探索」与条目同字号（14）—— 7 个字约 92px，宽 100 装不下才放宽到 120；\n'
  '--         父级 = 主窗口（随窗显隐、继承缩放）；\n'
  '--         **条目恒单行**：等级 / 熟练度只进悬停提示，不占副行；\n'
  '--         条目名超宽按「字」截断并补「…」（绝不截半个汉字；完整名在悬停提示里）；\n'
  '--         条目 = **圆角**按钮：底与边都走 HUI 的圆角拼装原语',

  '--   约束：字号仅 11 / 14 / 16；面板宽 120（左右内边距 8 → 内容宽 104）；\n'
  '--         标题「5人本专业探索」与**分组头**（推荐五人本 / 专业 / 探索）同为 14\n'
  '--         （分组头原为 11，2026-09-30 用户定：与按钮文字同号 —— QB.FS_GRP）；\n'
  '--         ★「全部副本」摆在「推荐五人本」**分组头上方**（它是整页入口，先给；2026-09-30 用户定）；\n'
  '--         父级 = 主窗口（随窗显隐、继承缩放）；\n'
  '--         **条目恒单行**：等级 / 熟练度只进悬停提示，不占副行；\n'
  '--         条目名超宽按「字」截断并补「…」（绝不截半个汉字；完整名在悬停提示里）；\n'
  '--         ★ 专业条目内嵌 **16px 圆角图标**（图标名取 Data_Professions 的 p.icon →\n'
  '--           Interface\\Icons\\*）；图标**单独套一层与图标等大的帧**再挂蒙版 ——\n'
  '--           ns.hui.RoundIcon 把圆角蒙版挂在贴图的父帧上，父帧比图标大就裁错角（同 TierUI）；\n'
  '--           其余条目无图标，文本回到左缩进 4（带图标时 23）。\n'
  '--         条目 = **圆角**按钮：底与边都走 HUI 的圆角拼装原语')

# ---- ② 常量：分组头字号 + 图标几何 ------------------------------------------
E('QB.TEXT_PAD = 4                -- 条目内文本左缩进\n'
  'QB.FS_HEAD, QB.FS_NAME, QB.FS_AUX = 14, 14, 11\n',

  'QB.TEXT_PAD = 4                -- 无图标条目的文本左缩进\n'
  'QB.FS_HEAD, QB.FS_NAME, QB.FS_AUX = 14, 14, 11\n'
  'QB.FS_GRP = 14                 -- 分组头字号（推荐五人本 / 专业 / 探索；2026-09-30 用户定：与条目同号）\n'
  'QB.ICON = 16                   -- 专业条目内的图标边长（行高 22，上下各留 3px）\n'
  'QB.ICON_X = 3                  -- 图标左缩进\n'
  'QB.NAME_ICON_X = QB.ICON_X + QB.ICON + 4   -- 带图标条目的文本左缩进 = 23\n')

# ---- ③ 图标贴图助手（放在「圆角按钮」小节之前） ------------------------------
E('-- 圆角按钮的底与边 -------------------------------------------------------------\n',

  '-- 图标 -------------------------------------------------------------------\n'
  'local FALLBACK_ICON = (ns.ProfHost and ns.ProfHost.FALLBACK_ICON)\n'
  '    or "Interface\\\\Icons\\\\INV_Misc_QuestionMark"\n'
  '\n'
  '-- 专业图标名（Data_Professions 的 p.icon，如 "trade_alchemy"）→ 纹理；带反斜杠的当整路径。\n'
  'local function SetIcon(tex, name)\n'
  '    if type(name) == "number" then\n'
  '        tex:SetTexture(name)\n'
  '    elseif type(name) == "string" and name ~= "" then\n'
  '        if name:find("\\\\", 1, true) then\n'
  '            tex:SetTexture(name)\n'
  '        else\n'
  '            tex:SetTexture("Interface\\\\Icons\\\\" .. name)\n'
  '        end\n'
  '    else\n'
  '        tex:SetTexture(FALLBACK_ICON)\n'
  '    end\n'
  'end\n'
  '\n'
  '-- 圆角按钮的底与边 -------------------------------------------------------------\n')

# ---- ④ 条目名可用宽：带图标时右移 -------------------------------------------
E('local NAME_W = QB.CW - QB.TEXT_PAD * 2\n',

  'local NAME_W = QB.CW - QB.TEXT_PAD * 2\n'
  'local NAME_W_ICON = QB.CW - QB.NAME_ICON_X - QB.TEXT_PAD\n'
  '\n'
  '-- 条目名的可用宽：带图标的行要右移，别压到图标上。\n'
  'local function NameW(hasIcon)\n'
  '    if hasIcon then return NAME_W_ICON end\n'
  '    return NAME_W\n'
  'end\n')

# ---- ⑤ 「全部副本」挪到分组头上方 -------------------------------------------
E('    if cfg.groups.dungeon then\n'
  '        out[#out + 1] = { grp = L["推荐五人本"] }\n',

  '    -- 「全部副本」是整页入口：摆在「推荐五人本」分组头**上方**（2026-09-30 用户定）；\n'
  '    -- 它跟着副本分组开关一起显隐（组关掉 → 整段撤下）。\n'
  '    if cfg.groups.dungeon then\n'
  '        out[#out + 1] = { text = L["全部副本"], act = "page", key = "Dungeons", gold = true }\n'
  '        out[#out + 1] = { grp = L["推荐五人本"] }\n')

E('        if n.dungeon == 0 then\n'
  '            out[#out + 1] = { text = L["当前等级暂无推荐副本"], dead = true }\n'
  '        end\n'
  '        out[#out + 1] = { text = L["全部副本"], act = "page", key = "Dungeons", gold = true }\n'
  '    end\n',

  '        if n.dungeon == 0 then\n'
  '            out[#out + 1] = { text = L["当前等级暂无推荐副本"], dead = true }\n'
  '        end\n'
  '    end\n')

# ---- ⑥ 专业条目带上图标名 ---------------------------------------------------
E('                out[#out + 1] = {\n'
  '                    text = p.name or slug,\n'
  '                    tip = tip,\n',

  '                out[#out + 1] = {\n'
  '                    text = p.name or slug,\n'
  '                    icon = p.icon,\n'
  '                    tip = tip,\n')

# ---- ⑦ 条目帧里加图标位 -----------------------------------------------------
E('    PaintFill(r, self.FILL)\n'
  '    PaintEdge(r, C_EDGE)\n'
  '\n'
  '    r.name = Fs(r, self.FS_NAME, C_TEXT)\n',

  '    PaintFill(r, self.FILL)\n'
  '    PaintEdge(r, C_EDGE)\n'
  '\n'
  '    -- 专业图标：单独一层「与图标等大」的帧 —— RoundIcon 的圆角蒙版按**父帧**尺寸裁，\n'
  '    -- 父帧比图标大就会裁错角（同 TierUI 的 MakeIconTile）。\n'
  '    r.iconTile = CreateFrame("Frame", nil, r)\n'
  '    r.iconTile:SetSize(self.ICON, self.ICON)\n'
  '    r.iconTile:SetPoint("LEFT", r, "LEFT", self.ICON_X, 0)\n'
  '    r.icon = r.iconTile:CreateTexture(nil, "ARTWORK")\n'
  '    r.icon:SetPoint("TOPLEFT", r.iconTile, "TOPLEFT", 0, 0)\n'
  '    r.icon:SetPoint("BOTTOMRIGHT", r.iconTile, "BOTTOMRIGHT", 0, 0)\n'
  '    if ns.hui and ns.hui.RoundIcon then ns.hui.RoundIcon(r.icon) end\n'
  '    r.iconTile:Hide()\n'
  '\n'
  '    r.name = Fs(r, self.FS_NAME, C_TEXT)\n')

# ---- ⑧ 分组头用新字号 -------------------------------------------------------
E('                fs = Fs(self.content, self.FS_AUX, C_DIM)',
  '                fs = Fs(self.content, self.FS_GRP, C_DIM)')

# ---- ⑨ 渲染：图标显隐 + 文本锚点 + 截断宽度 ---------------------------------
E('            local r = self:RowAt(nRow)\n'
  '            r.spec = sp\n'
  '            r.name:SetText(Fit(sp.text, NAME_W, self.FS_NAME))\n',

  '            local r = self:RowAt(nRow)\n'
  '            local wantIcon = sp.icon and true or false\n'
  '            r.spec = sp\n'
  '            -- 图标位只对有图标的行开；开关切换时才动锚点（同档重复调用是空操作）。\n'
  '            if r.hasIcon ~= wantIcon then\n'
  '                r.hasIcon = wantIcon\n'
  '                r.iconTile:SetShown(wantIcon)\n'
  '                r.name:ClearAllPoints()\n'
  '                r.name:SetPoint("LEFT", r, "LEFT",\n'
  '                    wantIcon and self.NAME_ICON_X or self.TEXT_PAD, 0)\n'
  '            end\n'
  '            if wantIcon then SetIcon(r.icon, sp.icon) end\n'
  '            r.name:SetText(Fit(sp.text, NameW(wantIcon), self.FS_NAME))\n')


def main():
    data = open(SRC, 'rb').read()
    applied = skipped = 0
    for i, (old, new) in enumerate(EDITS, 1):
        ob = old.encode('utf-8')
        nb = new.encode('utf-8')
        c = data.count(ob)
        if c == 1:
            data = data.replace(ob, nb)
            applied += 1
            print('  [%02d] 已打补丁' % i)
        elif c == 0 and data.count(nb) >= 1:
            skipped += 1
            print('  [%02d] 已是最新，跳过' % i)
        else:
            print('!! [%02d] 锚点异常：old 命中 %d 次，new 命中 %d 次'
                  % (i, c, data.count(nb)))
            print('    old=%r' % old[:120])
            return 2
    if applied:
        open(SRC, 'wb').write(data)
    print('补丁 %d 处 / 跳过 %d 处；文件 %d 字节' % (applied, skipped, len(data)))
    txt = data.decode('utf-8')
    for k in ('QB.FS_GRP = 14', 'QB.ICON = 16', 'ns.hui.RoundIcon(r.icon)',
              'icon = p.icon,', 'local function NameW(hasIcon)',
              'FS_GRP, C_DIM', 'SetBackdrop', 'SetAllPoints'):
        print('  %-28s -> %d' % (k, txt.count(k)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

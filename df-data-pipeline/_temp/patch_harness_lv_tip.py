# -*- coding: utf-8 -*-
"""2026-10-09：把「分段行来源」断言的过时负条件重锚，并补一条「行级提示框退役 →
制作物 / 需求材料各自出物品提示框」的正向断言。

背景：ProfessionUI.lua 改动后 `local src, detail = PD.LevelSrc(rec)` 变成
      `local src = PD.LevelSrc(rec)`（detail 只被退役的行级提示框消费），
      旧断言里那条负条件因此恒假 ⇒ harness 多出一条 FAIL（我方）。
      同时按项目铁律给新特性补正向静态断言。

改两份（内容同源）：
  ① _temp/df_dungeon_check.py  —— 已生成的 harness
  ② _temp/mk_df_check.py       —— 生成器（内联了这段 DF 本地块，不改下次重生成就回退）

按 EOL 原样读写（两份都是 LF，但用二进制保真更稳）；每条锚点断言「恰好命中 1 次」。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ── ① 重锚：过时的负条件 → 当前形态 ─────────────────────────────────────────
OLD_NEG = r"""       and 'local src, detail = PD.LevelSrc(rec)' in profui
"""
NEW_NEG = r"""       and '            local src = PD.LevelSrc(rec)\n' in profui
"""

# ── ② 新增正向断言：插在这一条之后的收尾行后面 ──────────────────────────────
TAIL = r"""       and '                src = src,\n' in profui)
"""

NEW_CK = r"""       and '                src = src,\n' in profui)
    # ★★ 六轮（2026-10-09）：行级悬停提示框**退役**，改由「制作物 / 需求材料」各自出
    #   物品提示框。用户原话：「每行有个鼠标提示框，这个提示框不要了，改成当我们移动到
    #   制作物或需求材料的上方时，显示该物品的鼠标提示框。注意，这个提示框不使用我们的主题」。
    #   ① 分段行打 noTip（PD.Row 的 OnEnter 首行短路）⇒ 整行悬停不再出自拼段落提示框；
    #   ② 制作物热区 PD.IconZone 盖住「图标 + 名称列」、挂产物 itemID；
    #   ③ 材料块自带热区 b.zone，挂该材料 id、与图标同尺寸；
    #   ④ 两处共用 PD.WireTipZone（悬停高亮 / ShowItemTip / 滚轮转发 / Shift 发链接）。
    #   ★ 一律走 DG.ShowItemTip（= SetItemByID，带物品内容 ⇒ Hui 的 TooltipHasItemContent
    #     命中 ⇒ 强制暴雪原皮），这正是用户要的「不使用我们的主题」；热区里不得出现自绘皮肤。
    ck('★★ 升级行行级提示框退役、改出物品提示框（制作物 / 需求材料各自悬停；暴雪原皮）',
       '        if self.__noTip then return end\n' in profui
       and '    r.__noTip = spec.noTip\n' in profui
       and '                noTip = true,\n' in profui
       and 'function PD.IconZone(r)' in profui
       and '    r.__iconZone = z\n' in profui
       and '        iz.__it = itemID and { itemID } or nil\n' in profui
       and '        iz:SetSize(PD.LV_NAME_X - PD.LV_ICON_X + PD.LV_NAME_W, h)\n' in profui
       and 'function PD.WireTipZone(z, r)' in profui
       and '        if self.__it and DG.ShowItemTip then DG.ShowItemTip(self, self.__it) end\n' in profui
       and '    z:SetScript("OnMouseWheel", function(self, delta)\n' in profui
       and '    b.zone.__it = { blk.id }\n' in profui
       and '    b.zone:SetSize(PD.TBL_ICON, PD.TBL_ICON)\n' in profui
       and '    PD.WireTipZone(b.zone, r)\n' in profui
       # 行级提示框的自拼路径必须与升级行脱钩（noTip 已短路；不留下的写法）
       and '                lines = tip,\n' not in profui)
"""

TARGETS = ['df_dungeon_check.py', 'mk_df_check.py']


def patch(fn):
    p = os.path.join(HERE, fn)
    with open(p, 'rb') as f:
        raw = f.read()
    txt = raw.decode('utf-8')
    eol = '\r\n' if b'\r\n' in raw else '\n'

    # 幂等短路：已经是新形态就跳过
    if NEW_NEG in txt and "行级悬停提示框**退役**" in txt:
        print('[SKIP] %s：已是新形态' % fn)
        return 0

    n_old = txt.count(OLD_NEG)
    if n_old != 1:
        sys.exit('[FAIL] %s：旧负条件命中 %d 次（应恰好 1）' % (fn, n_old))
    n_tail = txt.count(TAIL)
    if n_tail != 1:
        sys.exit('[FAIL] %s：收尾锚点命中 %d 次（应恰好 1）' % (fn, n_tail))

    txt = txt.replace(OLD_NEG, NEW_NEG, 1)
    txt = txt.replace(TAIL, NEW_CK, 1)

    # 落盘前自检
    assert OLD_NEG not in txt, '旧负条件没清干净'
    assert NEW_NEG in txt, '新负条件没落地'
    assert "行级悬停提示框**退役**" in txt, '新断言没落地'
    assert txt.count('★★ 升级行行级提示框退役、改出物品提示框') == 1, '新断言数量异常'
    # ⚠️ 用 raw 串：这里的 \n 是文件里的**字面** backslash-n，普通串会被解释成真换行
    assert r"and '                lines = tip,\n' not in profui)" in txt, '反例锚点没落地'

    out = txt.encode('utf-8')
    if eol == '\r\n':
        out = out.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    with open(p, 'wb') as f:
        f.write(out)
    print('[OK] %s：重锚 + 补断言完成（%d → %d 字节，EOL=%s）'
          % (fn, len(raw), len(out), 'CRLF' if eol == '\r\n' else 'LF'))
    # 换行体检
    with open(p, 'rb') as f:
        chk = f.read()
    if eol == '\n':
        assert b'\r' not in chk, '裸 CR 混入'
    print('     换行体检：CRLF=%d / 裸LF=%d / 裸CR=%d'
          % (chk.count(b'\r\n'), chk.count(b'\n') - chk.count(b'\r\n'), chk.count(b'\r') - chk.count(b'\r\n')))
    return 1


tot = 0
for t in TARGETS:
    tot += patch(t)
print('[DONE] 改动文件数 = %d' % tot)

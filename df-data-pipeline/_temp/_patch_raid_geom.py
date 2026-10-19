# -*- coding: utf-8 -*-
"""给离线 harness 补「团本卡墙几何」断言（2026-09-29）。

背景：RU.RenderList 原先在**逐卡循环体内**推进 y（`y = y + g.h + RU.LS_GAP`），
于是每张卡的落点 x 增、y 也增 —— 首档 3 张大卡被排成一条斜梯，第 3 张已经压到
底部「团本规则」块上。桩的 SetPoint 只校验首参类型、不记偏移，所以离线断言全绿
也照样漏掉。修法：落点交给纯几何函数 RU.LayoutCards 一次算好。

本脚本往两个 harness 各插两处断言（静态文本闸 + 运行时纯函数闸），幂等：
已插过就跳过；锚点不唯一/找不到就报错退出，绝不静默半改。
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FILES = ["df_dungeon_check.py", "mk_df_check.py"]

# ── ① 静态闸（Python 段）──────────────────────────────────────────────────
ANCHOR_STATIC = (
    "    ck('\u2605\u2605 RaidUI 界面层不定义裸全局函数（函数一律挂 local 表 RU）',\n"
    "       not re.search(r'^function\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\(', _ra, re.M))\n"
)

INSERT_STATIC = '''
    # \u2605\u2605 卡墙几何（2026-09-29 修）：RenderList 原先在**逐卡循环体内**推进 y，
    #    首档 3 张大卡就被排成斜梯（x 增、y 也增），第 3 张已落到规则块上；
    #    桩的 SetPoint 不记偏移 -> 离线全绿也漏。现改成一次性算好落点（纯几何），
    #    这里钉住「落点来自 RU.LayoutCards，且逐卡循环里不再动 y」。
    ck('\u2605\u2605 RaidUI 卡墙落点走纯几何函数 RU.LayoutCards',
       'function RU.LayoutCards(list, w, h, y0)' in _ra
       and 'c:SetPoint("TOPLEFT", RU.page, "TOPLEFT", pos[i].x, pos[i].y)' in _ra)
    ck('\u2605\u2605 RaidUI 逐卡循环里不得再推进 y（否则卡排成斜梯）',
       re.search(r'RU\\.PaintCard\\(c, rec\\)\\s*\\n\\s*y = y \\+', _ra) is None
       and 'y = pos.bottom + RU.LS_LABEL_H' in _ra)
'''

# ── ② 运行时闸（Lua 段，纯函数直调）──────────────────────────────────────
ANCHOR_RUNTIME = (
    '      ck("\u2605\u2605 首批同日开启（三座共用 2026-12-09 这个窗口）",\n'
    '         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].date == "2026 \u5e74 12 \u6708 9 \u65e5"\n'
    '         and RM.DATA.raids[1].first == true and RM.DATA.raids[3].first == true)\n'
)

INSERT_RUNTIME = '''
      -- \u2605\u2605 卡墙几何（纯函数直调）：同档共线单行 / 不越右缘 / 不压规则块
      --    （2026-09-29 修：原先逐卡推进 y 会把卡排成斜梯，首档就压到规则块上）
      do
        local _big, _small = {}, {}
        for _, _rc in ipairs(RM.DATA.raids) do
          if _rc.first then _big[#_big + 1] = _rc else _small[#_small + 1] = _rc end
        end
        local _pb = RM.LayoutCards(_big, RM.LS_BIG_W, RM.LS_BIG_H, RM.BODY_Y + RM.LS_LABEL_H)
        local _ps = RM.LayoutCards(_small, RM.LS_SMALL_W, RM.LS_SMALL_H,
                                   _pb.bottom + RM.LS_LABEL_H)
        local _sameB, _sameS, _rb, _rs = true, true, 0, 0
        for i = 1, #_big do
          if _pb[i].y ~= _pb[1].y then _sameB = false end
          if _pb[i].x + RM.LS_BIG_W > _rb then _rb = _pb[i].x + RM.LS_BIG_W end
        end
        for i = 1, #_small do
          if _ps[i].y ~= _ps[1].y then _sameS = false end
          if _ps[i].x + RM.LS_SMALL_W > _rs then _rs = _ps[i].x + RM.LS_SMALL_W end
        end
        ck("\u2605\u2605 卡墙\u00b7首批 3 大卡共线单行且不越右缘",
           #_big == 3 and _sameB and _pb.rows == 1 and _rb <= RM.X + RM.W,
           tostring(#_big) .. " 张 / " .. tostring(_pb.rows) .. " 行 / 右缘 " .. tostring(_rb))
        ck("\u2605\u2605 卡墙\u00b7后续 4 小卡共线单行且不越右缘",
           #_small == 4 and _sameS and _ps.rows == 1 and _rs <= RM.X + RM.W,
           tostring(#_small) .. " 张 / " .. tostring(_ps.rows) .. " 行 / 右缘 " .. tostring(_rs))
        ck("\u2605\u2605 卡墙整体不压到底部「团本规则」块", _ps.bottom < RM.RULES_RULE_Y,
           tostring(_ps.bottom) .. " < " .. tostring(RM.RULES_RULE_Y))
      end
'''

MARKERS = ['RaidUI 卡墙落点走纯几何函数 RU.LayoutCards', '卡墙\u00b7首批 3 大卡共线单行且不越右缘']


def main():
    for name in FILES:
        path = os.path.join(ROOT, name)
        # newline='' 关掉通用换行翻译，原样保留 CRLF/LF，避免顺手把整文件行尾改掉
        with io.open(path, encoding='utf-8', newline='') as f:
            src = f.read()
        nl = '\r\n' if '\r\n' in src else '\n'

        already = all(m in src for m in MARKERS)
        if already:
            print('[SKIP] %s 已插过' % name)
            continue

        out = src
        for anchor, insert, tag in ((ANCHOR_STATIC, INSERT_STATIC, 'static'),
                                    (ANCHOR_RUNTIME, INSERT_RUNTIME, 'runtime')):
            a = anchor.replace('\n', nl)
            ins = insert.replace('\n', nl)
            n = out.count(a)
            if n != 1:
                print('[FAIL] %s %s 锚点命中 %d 次（要求恰好 1）' % (name, tag, n))
                return 1
            out = out.replace(a, a + ins, 1)

        # 落盘前先自检语法（Python 段），避免把 harness 写坏
        compile(out, path, 'exec')
        with io.open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(out)
        print('[OK] %s 插入 2 处（static + runtime）' % name)

    # 逐条自检插入结果
    for name in FILES:
        with io.open(os.path.join(ROOT, name), encoding='utf-8') as f:
            src = f.read()
        for m in MARKERS:
            assert src.count(m) == 1, '%s: %s 命中 %d' % (name, m, src.count(m))
        print('[VERIFY] %s 两条 marker 各 1 次' % name)
    return 0


if __name__ == '__main__':
    sys.exit(main())

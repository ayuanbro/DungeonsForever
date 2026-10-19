# -*- coding: utf-8 -*-
"""给两个 harness 文件补 TierUI 守护断言（精确锚点插入，幂等）。

(1) _temp/df_dungeon_check.py —— 静态守卫：TierUI 源码文本不得出现 stripe / STRIPE_W。
(2) _temp/_qa_probe_spec.py —— 探针：spec 模式 TT.scroll 顶锚 = -SEC_TOP，rank = -BODY_TOP。
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- (1) df_dungeon_check.py
CHK = os.path.join(HERE, 'df_dungeon_check.py')
CHK_SIG = '_tier_stripe_hits'
CHK_ANCHOR = "   'fr:EnableMouse(true)' in _tier_src)\n\n\nif __name__ == '__main__':"
CHK_BLOCK = (
    "# ★★ ㉔ 专精指南卡左侧竖条（stripe）防回潮闸（2026-09-30 用户明确不要这根条）：\n"
    "#    TierUI 源码文本（用未去注释的 _tier_src_raw）不得再出现 stripe / STRIPE_W\n"
    "#    标识符 —— 出现即 FAIL。防它被合并/回潮进来；现有幻影字段闸抓不到 card.stripe，\n"
    "#    因为它挂在 card 表上、不是 TT.* 字段。\n"
    "_tier_stripe_hits = sorted(set(re.findall(r'stripe', _tier_src_raw, flags=re.I)))\n"
    "ck('★★ ㉔ 职业指南页专精卡已无左侧竖条 stripe（防回潮：源码不得出现 stripe / STRIPE_W）',\n"
    "   not _tier_stripe_hits,\n"
    "   extra='hits: %s' % (_tier_stripe_hits or 'none'))"
)
CHK_REPL = "   'fr:EnableMouse(true)' in _tier_src)\n\n" + CHK_BLOCK + "\n\nif __name__ == '__main__':"

# ---------------------------------------------------------------- (2) _qa_probe_spec.py
PRB = os.path.join(HERE, '_qa_probe_spec.py')
PRB_SIG = 'PASS 5：滚动区顶锚分支'
PRB_ANCHOR = '\n    end\n  end)\n  if not ok then R[#R + 1] = "FAIL'
PRB_BLOCK = '''    -- ---------------- PASS 5：滚动区顶锚分支（spec 走 SEC_TOP / rank 走 BODY_TOP） ----------------
    -- PlaceScroll 先 TOPLEFT 后 BOTTOMRIGHT，桩的 __pts 只保留最后一次；故包一层 SetPoint
    -- 单独记下 TOPLEFT 的 y 分量（= -(top)）。不钉 SEC_DROP 的数值，只钉结构关系与分支走向。
    do
      local scroll = TM.scroll
      local _sp = scroll.SetPoint
      scroll.SetPoint = function(self, a, b, c, d, e)
        if a == "TOPLEFT" then self.__topY = e end
        return _sp(self, a, b, c, d, e)
      end
      ck("★ SEC_TOP 结构：== SEC_TAB_Y + SEC_TAB_H + SEC_DROP（SEC_DROP 真被消费，不钉数值）",
         math.abs(TM.SEC_TOP - (TM.SEC_TAB_Y + TM.SEC_TAB_H + TM.SEC_DROP)) < 0.001,
         tostring(TM.SEC_TOP) .. " vs " .. tostring(TM.SEC_TAB_Y + TM.SEC_TAB_H + TM.SEC_DROP))
      local sc, ss = nil, nil
      for c, l in pairs(G.specs) do
        for sp, _ in pairs(l) do if not sc then sc, ss = c, sp end end
      end
      scroll.__topY = nil
      local okSpec, errSpec = pcall(function() TM.OpenSpec(sc, ss) end)
      ck("★★ 专精模式：TT.scroll 顶锚 = -SEC_TOP（spec 分支收口正确）",
         okSpec and DungeonsForeverDB.tier.nav == "spec"
           and math.abs((scroll.__topY or 1e9) + TM.SEC_TOP) < 0.001,
         "ok=" .. tostring(okSpec) .. " nav=" .. tostring(DungeonsForeverDB.tier.nav)
           .. " topY=" .. tostring(scroll.__topY) .. " -SEC_TOP=" .. tostring(-TM.SEC_TOP)
           .. " err=" .. tostring(errSpec))
      scroll.__topY = nil
      DungeonsForeverDB.tier.nav = "rank"
      local okRank, errRank = pcall(function() TM.Render() end)
      ck("★★ 排行模式：TT.scroll 顶锚 = -BODY_TOP（rank 分支不受下移影响）",
         okRank and math.abs((scroll.__topY or 1e9) + TM.BODY_TOP) < 0.001,
         "ok=" .. tostring(okRank) .. " topY=" .. tostring(scroll.__topY)
           .. " -BODY_TOP=" .. tostring(-TM.BODY_TOP) .. " err=" .. tostring(errRank))
      ck("★★ spec/rank 顶锚互异（SEC_TOP ~= BODY_TOP，分支不串）",
         TM.SEC_TOP ~= TM.BODY_TOP, tostring(TM.SEC_TOP) .. " vs " .. tostring(TM.BODY_TOP))
      DungeonsForeverDB.tier.nav = "spec"
    end
'''
PRB_REPL = '\n    end\n\n' + PRB_BLOCK + '  end)\n  if not ok then R[#R + 1] = "FAIL'


def patch(path, sig, anchor, repl):
    with io.open(path, 'rb') as fh:
        raw = fh.read()
    s = raw.decode('utf-8')
    if sig in s:
        print('[SKIP] %s already patched (sig present)' % os.path.basename(path))
        return False
    n = s.count(anchor)
    assert n == 1, '%s: anchor hit %d (want 1)' % (os.path.basename(path), n)
    s2 = s.replace(anchor, repl)
    out = s2.encode('utf-8')
    assert out.count(b'\r\n') == raw.count(b'\r\n') == 0, 'CRLF introduced'
    with io.open(path, 'wb') as fh:
        fh.write(out)
    print('[OK] %s  (%d -> %d bytes)' % (os.path.basename(path), len(raw), len(out)))
    return True


def main():
    patch(CHK, CHK_SIG, CHK_ANCHOR, CHK_REPL)
    patch(PRB, PRB_SIG, PRB_ANCHOR, PRB_REPL)
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
把 U:RenderDungeonTab 的「渲染分派」块整体提到「可见性切换」块之前。

实机回归（2026-10-03 用户）：
  关闭时停在「地图」页签 → /reload → 打开副本详情（页签从 DB 恢复成 map）
  → 地图页一片空白；切到掉落再切回地图就正常了。

根因：懒建之后，本页签的容器可能**到这一刻才第一次被建出来**（隐藏态诞生：
EnsureQuestLane/GuideLane 主动 Hide，地图页 M.Build 也 Hide），
而可见性块是 `if U.xxx then U.xxx:SetShown(isX) end` —— 引用还是 nil ⇒ 整块跳过
⇒ 容器停在隐藏态，内容全画进看不见的帧里。下一次 RenderDungeonTab（引用已存在）才恢复。

修法：Ensure* 先建容器并渲染内容，随后的 SetShown 才切得动（与 UpdateDungeons 总览分支同序）。
"""
import io
import sys

PATH = r'Core/DungeonUI.lua'

# 要搬走的整块（含前导换行，末尾不含换行）
DISPATCH = (
    '\n'
    '    if isQuest then\n'
    '        DG.EnsureQuestLane()          -- \u2605 \u5206\u5e27\u6ca1\u8f6e\u5230\u5c31\u540c\u6b65\u8865\u5efa\uff08\u5207\u9875\u4e0d\u7a7a\u767d\uff09\n'
    '        U:RenderDungeonQuests()\n'
    '    elseif isGuide then\n'
    '        DG.EnsureGuideLane()\n'
    '        U:RenderDungeonGuide()\n'
    '    elseif isMap then\n'
    '        DG.EnsureMapPage()\n'
    '        if ns.MapModule then ns.MapModule.Paint(U.dungeonDetailCur) end\n'
    '    else\n'
    '        U:RenderDungeonLoot()\n'
    '    end'
)

ANCHOR = '    local isMap = (cur == "map")\n'

NEW_BLOCK = (
    '    local isMap = (cur == "map")\n'
    '\n'
    '    -- \u2605\u2605\u2605 \u987a\u5e8f\uff1a**\u5148\u8865\u5efa\u3001\u518d\u5207\u663e\u9690**\uff082026-10-03 \u5b9e\u673a\u56de\u5f52\uff1a/reload \u540e\u6062\u590d\u4e0a\u6b21\u300c\u5730\u56fe\u300d\u9875\u7b7e \u2192 \u6574\u9875\u7a7a\u767d\uff09\n'
    '    --   \u4e0b\u9762\u7684\u53ef\u89c1\u6027\u5757\u5168\u662f `if U.xxx then U.xxx:SetShown(isX) end` \u2014\u2014\u300c\u5f15\u7528\u5b58\u5728\u624d\u5207\u300d\u3002\n'
    '    --   \u800c\u61d2\u5efa\u4e4b\u540e\uff0c\u672c\u9875\u7b7e\u7684\u5bb9\u5668\u5b8c\u5168\u53ef\u80fd**\u5230\u8fd9\u4e00\u523b\u624d\u7b2c\u4e00\u6b21\u88ab\u5efa\u51fa\u6765**\uff08\u8be6\u60c5\u9875\u521a\u61d2\u5efa\u5b8c\u3001\n'
    '    --   \u5206\u5e27\u8fd8\u6ca1\u8f6e\u5230\uff09\u3002\u4e8e\u662f\u90a3\u51e0\u884c SetShown \u62ff\u5230 nil \u76f4\u63a5\u8df3\u8fc7\uff0c\u5bb9\u5668\u4ee5**\u9690\u85cf\u6001**\u8bde\u751f\n'
    '    --   \uff08EnsureQuestLane / EnsureGuideLane \u4e3b\u52a8 Hide\uff1b\u5730\u56fe\u9875 M.Build \u4e5f Hide\uff09\u21d2\n'
    '    --   \u5185\u5bb9\u5168\u753b\u8fdb\u4e86\u770b\u4e0d\u89c1\u7684\u5e27\u91cc = \u9875\u7b7e\u4e00\u7247\u7a7a\u767d\uff0c\u8981\u7b49\u4e0b\u4e00\u6b21 RenderDungeonTab\n'
    '    --   \uff08\u5207\u8d70\u518d\u5207\u56de\uff09\u624d\u6062\u590d\u3002\n'
    '    --   \u2605 \u5b9e\u673a\u6307\u7eb9\uff1a\u5173\u95ed\u65f6\u505c\u5728\u300c\u5730\u56fe\u300d\u9875 \u2192 /reload \u2192 \u6253\u5f00\u526f\u672c\u8be6\u60c5\u76f4\u63a5\u6062\u590d\u5730\u56fe\u9875\n'
    '    --   \u2192 \u7a7a\u5730\u56fe\uff1b\u5207\u5230\u6389\u843d\u518d\u5207\u56de\u5730\u56fe\u5c31\u597d\u4e86\u3002\n'
    '    --   \u2705 \u56e0\u6b64\u628a\u300c\u6e32\u67d3\u5206\u6d3e\u300d\u6574\u4f53\u63d0\u5230\u53ef\u89c1\u6027\u5757**\u4e4b\u524d**\uff1aEnsure* \u5148\u628a\u5bb9\u5668\u5efa\u51fa\u6765\u5e76\u6e32\u67d3\u5185\u5bb9\uff0c\n'
    '    --      \u540e\u9762\u7684 SetShown \u624d\u5207\u5f97\u52a8\u3002\u4e0e U:UpdateDungeons \u7684\u603b\u89c8\u5206\u652f\u540c\u4e00\u987a\u5e8f\uff08Ensure \u5728\u524d\uff09\u3002\n'
    '    if isQuest then\n'
    '        DG.EnsureQuestLane()\n'
    '        U:RenderDungeonQuests()\n'
    '    elseif isGuide then\n'
    '        DG.EnsureGuideLane()\n'
    '        U:RenderDungeonGuide()\n'
    '    elseif isMap then\n'
    '        DG.EnsureMapPage()\n'
    '        if ns.MapModule then ns.MapModule.Paint(U.dungeonDetailCur) end\n'
    '    else\n'
    '        U:RenderDungeonLoot()\n'
    '    end\n'
)

raw = io.open(PATH, 'rb').read()
crlf = raw.count(b'\r\n')
bare = raw.count(b'\n') - crlf
t = raw.decode('utf-8').replace('\r\n', '\n')

assert t.count(ANCHOR) == 1, 'anchor count = %d' % t.count(ANCHOR)
assert t.count(DISPATCH) == 1, 'dispatch count = %d' % t.count(DISPATCH)

t = t.replace(DISPATCH, '', 1)          # 从末尾摘掉
t = t.replace(ANCHOR, NEW_BLOCK, 1)     # 在 isMap 之后插入

# 复查：新块在可见性块之前
i_new = t.index('    if isQuest then\n        DG.EnsureQuestLane()\n')
i_vis = t.index('if U.dungeonQuestScroll then U.dungeonQuestScroll:SetShown(isQuest) end')
assert i_new < i_vis, 'order still wrong'
# 且只出现一次（末尾那份已摘掉）
for nm in ('QuestLane', 'GuideLane', 'MapPage'):
    c = t.count('        DG.Ensure' + nm + '()')      # 8 空格缩进 = 调用点（定义行是 'function DG.Ensure...'）
    assert c == 1, 'Ensure%s call-site count=%d' % (nm, c)

out = t.replace('\n', '\r\n').encode('utf-8')
io.open(PATH, 'wb').write(out)
crlf2 = out.count(b'\r\n')
bare2 = out.count(b'\n') - crlf2
print('patched OK  lines=%d  CRLF=%d  bareLF=%d' % (out.count(b'\n'), crlf2, bare2))

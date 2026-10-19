# -*- coding: utf-8 -*-
"""把「团本页空态」相关的 harness 断言改成「团本页 = RaidUI 建页」，
并补一组 Core/RaidUI.lua 的静态断言。df_dungeon_check.py 与 mk_df_check.py 同步改。"""
import io, sys

FRAG_A_OLD = """       and 'U.raidNote:SetText(L["团本数据待补"])' in _bld)"""
FRAG_A_NEW = """       and 'if ns.RaidModule then ns.RaidModule.Build(U.raidPage) end' in _bld)"""

FRAG_B_OLD = """      ck("\u2605 \u56e2\u672c\u9875\u662f\u5e38\u9a7b\u5e27\uff08\u7a7a\u6001\u9aa8\u67b6\uff09", U.raidPage ~= nil and U.raidNote ~= nil)
      ck("\u2605 \u56e2\u672c\u9875\u5360\u4f4d\u6587\u6848 = \u56e2\u672c\u6570\u636e\u5f85\u8865",
         U.raidNote ~= nil and U.raidNote.__text == "\u56e2\u672c\u6570\u636e\u5f85\u8865",
         U.raidNote and U.raidNote.__text)"""

FRAG_B_NEW = """      local RM = TF_NS.RaidModule
      ck("\u2605\u2605 \u56e2\u672c\u9875\u662f\u5e38\u9a7b\u5e27\uff08\u5df2\u63a5 RaidModule \u5efa\u9875\uff09", U.raidPage ~= nil and RM ~= nil)
      ck("\u2605\u2605 \u56e2\u672c\u9875\u4e8c\u7ea7\u9875\u7b7e = \u65f6\u95f4\u7ebf / \u5217\u8868",
         RM ~= nil and RM.tabs ~= nil and RM.tabs.timeline ~= nil and RM.tabs.list ~= nil)
      ck("\u2605\u2605 \u65f6\u95f4\u8f74\u8282\u70b9 = 3 \u6bb5\uff0812/9 \u00b7 2027 \u6625 \u00b7 2027 \u590f\uff09",
         RM ~= nil and RM.nodes ~= nil and #RM.nodes == 3,
         RM and RM.nodes and tostring(#RM.nodes))
      ck("\u2605\u2605 \u884c\u6c60 7 / \u5361\u7247\u6c60 7\uff08\u4e0e\u6570\u636e\u6761\u6570\u5bf9\u9f50\uff0c\u6e32\u67d3\u671f\u4e0d\u65b0\u5efa\u5e27\uff09",
         RM ~= nil and RM.rows ~= nil and #RM.rows == 7
         and RM.cards ~= nil and #RM.cards == 7,
         RM and RM.rows and (tostring(#RM.rows) .. " / " .. tostring(#(RM.cards or {}))))
      ck("\u2605\u2605 \u9996\u6279\u4e09\u5ea7\u4e2d\u6587\u540d = \u6df1\u7a74 / \u6d77\u52a0\u5c14\u5cf0 / \u5965\u5c3c\u514b\u5e0c\u4e9a\u7684\u5de2\u7a74",
         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].name == "\u6df1\u7a74"
         and RM.DATA.raids[2].name == "\u6d77\u52a0\u5c14\u5cf0"
         and RM.DATA.raids[3].name == "\u5965\u5c3c\u514b\u5e0c\u4e9a\u7684\u5de2\u7a74")
      ck("\u2605\u2605 \u9996\u6279\u540c\u65e5\u5f00\u542f\uff08\u4e09\u5ea7\u5171\u7528 2026-12-09 \u8fd9\u4e2a\u7a97\u53e3\uff09",
         RM ~= nil and RM.DATA ~= nil and RM.DATA.raids[1].date == "2026 \u5e74 12 \u6708 9 \u65e5"
         and RM.DATA.raids[1].first == true and RM.DATA.raids[3].first == true)"""

ANCHOR_OLD = """    ck('\u2605 UpdateActiveSub \u5728\u4e13\u4e1a\u6001\u5237\u4e13\u4e1a\u9875\u81ea\u5df1\u90a3\u4e00\u5957\uff08\u4e0d\u53bb\u78b0\u526f\u672c\u9875\uff09',
       'if self.curSub == "Professions" then' in _uas
       and 'ns.ProfModule.Refresh()' in _uas)"""

ANCHOR_NEW = ANCHOR_OLD + """

    # \u2500\u2500 \u56e2\u672c\u9875\uff08Core/RaidUI.lua\uff0c2026-09-29 \u65b0\u589e\uff1a\u65f6\u95f4\u7ebf / \u5217\u8868 \u4e24\u4e2a\u4e8c\u7ea7\u5b50\u9875\uff09\u2500\u2500
    do
      local _ra = open(os.path.join(ADDON, 'Core', 'RaidUI.lua'), encoding='utf-8',
                       errors='replace').read().replace('\\r\\n', '\\n')
      local _toc2 = open(TOC, encoding='utf-8', errors='replace').read().replace('\\r\\n', '\\n')
      local _raf = re.findall(r'MakeFS\\([^,]+,\\s*(\\d+),', _ra)
      ck('\u2605 RaidUI \u6309 toc \u987a\u5e8f\u6302\u5728 DungeonUI \u4e4b\u540e',
         'Core\\\\DungeonUI.lua\\nCore\\\\RaidUI.lua\\n' in _toc2)
      ck('\u2605\u2605 RaidUI \u5168\u7aef\u53ef\u89c1\uff08\u4e0d\u6302 LoadForeverPages \u95f8\uff09',
         'ns.LoadForeverPages' not in _ra)
      ck('\u2605\u2605 RaidUI \u5b57\u53f7\u53ea\u8bb8 11/14/16\uff08\u5168\u63d2\u4ef6\u5b57\u53f7\u6807\u51c6\u540c\u6b3e\uff09',
         _raf and all(v in ('11', '14', '16') for v in _raf), sorted(set(_raf)))
      ck('\u2605\u2605 RaidUI \u4e8c\u7ea7\u9875\u7b7e = \u65f6\u95f4\u7ebf / \u5217\u8868',
         '{ key = "timeline", text = L["\u65f6\u95f4\u7ebf"] }' in _ra
         and '{ key = "list", text = L["\u5217\u8868"] }' in _ra)
      ck('\u2605\u2605 RaidUI \u4e0d\u505a\u79d2\u7ea7\u5012\u8ba1\u65f6\uff08\u65e0 OnUpdate / \u65e0 unlockAt\uff0c\u53ea\u5199\u65e5\u671f\uff09',
         'OnUpdate' not in _ra and 'unlockAt' not in _ra)
      ck('\u2605\u2605 RaidUI \u754c\u9762\u5c42\u4e0d\u5b9a\u4e49\u88f8\u5168\u5c40\u51fd\u6570\uff08\u51fd\u6570\u4e00\u5f8b\u6302 local \u8868 RU\uff09',
         not re.search(r'^function\\s+[A-Za-z_][A-Za-z0-9_]*\\s*\\(', _ra, re.M))
    end"""


def patch(path):
    raw = open(path, 'rb').read().decode('utf-8')
    n = 0
    for old, new in ((FRAG_A_OLD, FRAG_A_NEW), (FRAG_B_OLD, FRAG_B_NEW), (ANCHOR_OLD, ANCHOR_NEW)):
        c = raw.count(old)
        if c != 1:
            print('[SKIP] %s : count=%d -> %s' % (path, c, old.strip().splitlines()[0][:60]))
            continue
        raw = raw.replace(old, new)
        n += 1
    open(path, 'wb').write(raw.encode('utf-8'))
    print('[OK] %s : %d/%d 处已改' % (path, n, 3))


for p in ('df_dungeon_check.py', 'mk_df_check.py'):
    patch(p)

# -*- coding: utf-8 -*-
"""QA 校验（只读）：前置任务数据补齐（269 条）+ cls 字段 + 总览职业小徽章。

A 部分：纯 python 解析三语 `ns.DungeonQuestExtInfo` 段 + `_temp/_ext_pre_ids.json`
B 部分：在 lua51 桩环境加载**客户端已部署副本**，跑运行时断言
       （条数 / 全副本 ext 需求覆盖 / cls 分布 / ExtQuestRow[15] / 徽章挂接与池复用）
C 部分：静态 grep（挂接点、注释、上一轮移动/滚动条代码未被改动）

用法：python _temp/qa_ext_cls.py
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)

import tf_dryrun as T  # noqa: E402
from lupa import lua51  # noqa: E402

ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever')
TOC = os.path.join(ADDON, 'DungeonsForever.toc')
CLIENT_BUILD = int(os.environ.get('TF_BUILD', '16001'))
LUA_CASE = os.path.join(HERE, 'qa_ext_cls.lua')

PASSED, FAILED = [], []


def ck(name, ok, extra=None):
    (PASSED if ok else FAILED).append(name)
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           '' if extra is None else '  [%s]' % extra))


# ---------------------------------------------------------------------------
# A. 纯 python：解析三语 ExtInfo 段
# ---------------------------------------------------------------------------
def parse_extinfo(path):
    lines = open(path, encoding='utf-8', errors='replace').read().replace('\r\n', '\n').split('\n')
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith('ns.DungeonQuestExtInfo = {'):
            start = i
            break
    if start is None:
        return None
    body = []
    for ln in lines[start + 1:]:
        if ln.rstrip() == '}':
            break
        body.append(ln)
    rows, order = {}, []
    for ln in body:
        m = re.match(r'^\s*\[(\d+)\]\s*=\s*\{(.*)\},?\s*$', ln)
        if m:
            qid = int(m.group(1))
            rows[qid] = m.group(2)
            order.append(qid)
    return rows, order


def part_a():
    print('=' * 72)
    print('A. 数据解析（纯 python）')
    print('=' * 72)
    main = parse_extinfo(os.path.join(ADDON, 'Core', 'Data', 'Data_DungeonQuests.lua'))
    zhtw = parse_extinfo(os.path.join(ADDON, 'Core', 'Data', 'zhTW', 'Data_DungeonQuests.lua'))
    enus = parse_extinfo(os.path.join(ADDON, 'Core', 'Data', 'enUS', 'Data_DungeonQuests.lua'))
    ck('三语 ExtInfo 段都能定位到', main is not None and zhtw is not None and enus is not None)

    rows, order = main
    ck('zhCN ExtInfo 条目数 = 269', len(rows) == 269, len(rows))
    ck('zhCN 无重复 id（行数 == 唯一 id 数）', len(order) == len(set(order)),
       '%d 行 / %d 唯一' % (len(order), len(set(order))))

    ids_json = set(json.load(open(os.path.join(ROOT, '_temp', '_ext_pre_ids.json'),
                                  encoding='utf-8'))['ids'])
    ck('_ext_pre_ids.json 条数 = 269', len(ids_json) == 269, len(ids_json))
    missing = sorted(ids_json - set(rows))
    extra = sorted(set(rows) - ids_json)
    ck('json 里 269 个 id 全部存在于 ExtInfo（无缺口）', not missing,
       '缺 %d 个 %s' % (len(missing), missing[:8]))
    ck('ExtInfo 无 json 之外的条目（无多余）', not extra,
       '多 %d 个 %s' % (len(extra), extra[:8]))

    cls_map = {}
    for qid, body in rows.items():
        m = re.search(r'cls = "([^"]+)"', body)
        if m:
            cls_map[qid] = m.group(1)
    n_cls = sum(1 for b in rows.values() if 'cls = "' in b)
    ck('cls = " 出现次数 = 11', n_cls == 11, n_cls)
    dist = {}
    for v in cls_map.values():
        dist[v] = dist.get(v, 0) + 1
    ck('cls 分布 = 战士 6 / 圣骑士 5', dist == {'战士': 6, '圣骑士': 5}, dist)
    ck('cls 只出现在白名单二字职业内',
       set(dist) <= {'战士', '圣骑士', '法师', '牧师', '盗贼', '萨满', '术士', '德鲁伊'},
       sorted(dist))
    cls_ids = sorted(cls_map)
    print('     cls 名单：%s' % cls_ids)

    for qid, want in ((1649, '圣骑士'), (1653, '圣骑士')):
        ck('[%d] 含 cls = "%s"' % (qid, want),
           rows.get(qid) is not None and 'cls = "%s"' % want in rows[qid],
           rows.get(qid, '')[:80])
    for qid in (373, 865):
        ck('[%d] 无 cls（非职业任务）' % qid,
           rows.get(qid) is not None and 'cls = "' not in rows[qid],
           rows.get(qid, '')[:80])

    for tag, seg in (('zhTW', zhtw), ('enUS', enus)):
        r, o = seg
        ck('%s ExtInfo 条数 = 269（与 zhCN 一致）' % tag, len(r) == 269, len(r))
        ck('%s id 集合 == zhCN' % tag, set(r) == set(rows),
           '差异 %d' % len(set(r) ^ set(rows)))
        n2 = sum(1 for b in r.values() if 'cls = "' in b)
        ck('%s cls 数 = 11（职业字段随语种同步）' % tag, n2 == 11, n2)
    return cls_ids


# ---------------------------------------------------------------------------
# B. Lua 运行时（客户端已部署副本）
# ---------------------------------------------------------------------------
DECORATE = r'''
QAFRAMES = {}
do
  local _cf = CreateFrame
  local function decorate(f)
    rawset(f, "GetWidth", function(self)
      local w = rawget(self, "__w"); if w == nil then return 100 end; return w
    end)
    rawset(f, "GetHeight", function(self)
      local h = rawget(self, "__h"); if h == nil then return 100 end; return h
    end)
    rawset(f, "SetWidth", function(self, w) rawset(self, "__w", w); return self end)
    rawset(f, "SetHeight", function(self, h) rawset(self, "__h", h); return self end)
    rawset(f, "GetEffectiveScale", function(self) return 1 end)
    rawset(f, "SetVerticalScroll", function(self, v) rawset(self, "__vs", v); return self end)
    rawset(f, "GetVerticalScroll", function(self) return rawget(self, "__vs") or 0 end)
    rawset(f, "SetHorizontalScroll", function(self, v) rawset(self, "__hs", v); return self end)
    rawset(f, "GetHorizontalScroll", function(self) return rawget(self, "__hs") or 0 end)
    rawset(f, "GetStringWidth", function(self)
      local t = rawget(self, "__text") or ""
      local n = 0
      for _ in tostring(t):gmatch("[%z\1-\127\194-\244][\128-\191]*") do n = n + 1 end
      rawset(self, "__sw", n * 12)
      return n * 12
    end)
    rawset(f, "SetPoint", function(self, a, b, c, d, e)
      local l = rawget(self, "__ptlist")
      if not l then l = {}; rawset(self, "__ptlist", l) end
      l[#l + 1] = { a, b, c, d, e }
      rawset(self, "__pts", { a, b, c, d, e })
      return self
    end)
    QAFRAMES[#QAFRAMES + 1] = f
    return f
  end
  CreateFrame = function(a, b, c, d) return decorate(_cf(a, b, c, d)) end
  QACUR = { x = 400, y = 300 }
  QADOWN = true
  GetCursorPosition = function() return QACUR.x, QACUR.y end
  IsShiftKeyDown = function() return false end
  IsMouseButtonDown = function() return QADOWN == true end
end
'''



SANITIZE = r"""
PRINTLOG = {}
QASAN = function(s)
  s = tostring(s or "")
  local out, i, n = {}, 1, #s
  while i <= n do
    local b = s:byte(i)
    local len = 0
    if b < 0x80 then len = 1
    elseif b >= 0xC2 and b <= 0xDF then len = 2
    elseif b >= 0xE0 and b <= 0xEF then len = 3
    elseif b >= 0xF0 and b <= 0xF4 then len = 4
    end
    local ok = len > 0 and (i + len - 1) <= n
    if ok and len > 1 then
      for k = 1, len - 1 do
        local cb = s:byte(i + k)
        if not cb or cb < 0x80 or cb > 0xBF then ok = false; break end
      end
    end
    if ok then out[#out + 1] = s:sub(i, i + len - 1); i = i + len
    else out[#out + 1] = "?"; i = i + 1 end
  end
  return table.concat(out)
end
print = function(...)
  local t = {}
  for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end
  PRINTLOG[#PRINTLOG + 1] = QASAN(table.concat(t, " "))
end
"""

def part_b():
    print('=' * 72)
    print('B. Lua 运行时断言（客户端副本，TF_BUILD=%d）' % CLIENT_BUILD)
    print('=' * 72)
    toc = open(TOC, encoding='utf-8', errors='replace').read()
    files = [re.sub(r'\s*\[[^\]]*\]\s*$', '', l.strip()).replace('\\', '/')
             for l in toc.splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    lua.execute(r'''
C_Timer = { After = function(t, fn)
    if t == 0 then fn(); return end
    SWEEPS = SWEEPS or {}
    SWEEPS[#SWEEPS + 1] = { t = t, fn = fn }
end }''')
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 - 3660 end')
    lua.execute('BG.hui = nil')
    lua.execute('ADDON_ROOT = %r' % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute('UIErrorsFrame = { AddMessage = function() end }')
    lua.execute(r'''
QUEST_DONE, QUEST_ON = {}, {}
C_QuestLog = {
  GetTitleForQuestID = function(id) return "客户端任务" .. tostring(id) end,
  GetQuestDifficultyLevel = function() return 16 end,
  IsQuestFlaggedCompleted = function(id) return QUEST_DONE[id] == true end,
  IsOnQuest = function(id) return QUEST_ON[id] == true end,
}
GetQuestLink = function(id) return "|cff808080|Hquest:" .. tostring(id) .. "|h[客户端任务]|r" end
UnitFactionGroup = function() return "Horde" end
UnitLevel = function() return 16 end
UnitName = function() return "QA" end
RAID_CLASS_COLORS = {
  WARRIOR = { r = 0.78, g = 0.61, b = 0.43 }, PALADIN = { r = 0.96, g = 0.55, b = 0.73 },
  ROGUE = { r = 1.00, g = 0.96, b = 0.41 }, SHAMAN = { r = 0.00, g = 0.44, b = 0.87 },
  MAGE = { r = 0.41, g = 0.80, b = 0.94 }, DRUID = { r = 1.00, g = 0.49, b = 0.04 },
  PRIEST = { r = 1.00, g = 1.00, b = 1.00 }, WARLOCK = { r = 0.58, g = 0.51, b = 0.79 },
  HUNTER = { r = 0.67, g = 0.83, b = 0.45 },
}
''')
    lua.execute(
        'do local orig = GetBuildInfo; GetBuildInfo = function(...) '
        'local a,b,c,d,e = orig(...); return a, b, c, %d, e end end' % CLIENT_BUILD)
    lua.execute(SANITIZE)
    lua.execute(DECORATE)

    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        chunk = loadfile(rel)
        if chunk is None:
            ck('加载 %s' % rel, False, 'loadfile nil')
            return
        try:
            chunk()
        except Exception as e:  # noqa: BLE001
            ck('加载 %s' % rel, False, str(e)[:300])
            return
    lua.execute('QA_CASE = %r' % LUA_CASE.replace('\\', '/'))
    probe = lua.eval('''function()
      local ok, e = pcall(dofile, QA_CASE)
      if ok then return "OK" end
      local s = tostring(e)
      local esc = s:gsub("[%z\\1-\\8\\11\\12\\14-\\31\\127-\\255]", function(c)
        return string.format("\\\\x%02X", c:byte())
      end)
      if #esc > 600 then esc = esc:sub(1, 600) end
      return "ERRESC " .. esc
    end''')
    info = probe()
    if isinstance(info, str) and info.startswith('ERRESC'):
        ck('Lua 断言块抛异常', False, info[8:])

    res = lua.globals().QARESULT
    lines = []
    if res is not None:
        i = 1
        while True:
            v = res[i]
            if v is None:
                break
            lines.append(v)
            i += 1
    for line in lines:
        if not line.strip():
            continue
        p = line.split('\t')
        if len(p) < 2:
            ck('Lua 输出缺制表符', False, line[:300])
            continue
        ck(p[1], p[0] == 'OK', p[2] if len(p) > 2 else None)


# ---------------------------------------------------------------------------
# C. 静态 grep
# ---------------------------------------------------------------------------
def part_c():
    print('=' * 72)
    print('C. 静态核查（Core/DungeonUI.lua）')
    print('=' * 72)
    src = open(os.path.join(ADDON, 'Core', 'DungeonUI.lua'), encoding='utf-8',
               errors='replace').read().replace('\r\n', '\n')
    lines = src.split('\n')

    def hits(pat):
        return [(i + 1, lines[i].strip()) for i in range(len(lines)) if re.search(pat, lines[i])]

    h_fn = hits(r'DG\.QuestOverviewClsBadge')
    ck('QuestOverviewClsBadge 共 3 处（1 定义 + place + placeExt）', len(h_fn) == 3,
       ' | '.join('%d:%s' % (n, t[:60]) for n, t in h_fn))
    h_cls = hits(r'n\.clsB')
    ck('n.clsB 共 3 处（建徽章 / 函数内取 / placeMark 隐藏）', len(h_cls) == 3,
       ' | '.join('%d:%s' % (n, t[:60]) for n, t in h_cls))
    h_ext = hits(r'info\.cls, info\.npcid')
    ck('ExtQuestRow 第 15 位 = info.cls（1 行）', len(h_ext) == 1,
       ' | '.join('%d:%s' % (n, t[:70]) for n, t in h_ext))

    # 新增区间无注释
    def seg(a, b):
        return '\n'.join(lines[a - 1:b])
    zone = seg(2030, 2180) + seg(5100, 5125)
    ck('新增区间无 lua 注释（-- / --[[ ）',
       not re.search(r'(^|\s)--', zone), re.findall(r'--[^\n]*', zone)[:3])

    # 上一轮移动/滚动条代码未被动过（期望出现次数：拖拽 tick + 滑块各 1 处 = 2）
    checks = [
        ('滚轮=平移 delta*40', r'local step = delta \* 40', 1),
        ('垂直 +step', r'sf:SetVerticalScroll\(sf:GetVerticalScroll\(\) \+ step\)', 1),
        ('拖拽 hs - dx', r'math\.min\(mx, st\.hs - dx\)', 1),
        ('拖拽 vs + dy', r'math\.min\(my, st\.vs \+ dy\)', 1),
        ('左键松开自停守卫（拖拽 + 滑块共 2 处）',
         r'pcall\(IsMouseButtonDown, "LeftButton"\)', 2),
        ('sf:EnableMouse(false)', r'sf:EnableMouse\(false\)', 1),
        ('vbar 轨道 L2', r'BuildCapsule\(vbar, 3, ns\.hui\.layer\.L2\)', 1),
        ('vbar 滑块 L4', r'BuildCapsule\(vthumb, 2, ns\.hui\.layer\.L4\)', 1),
        ('vbar 锚 +11', r'vbar:SetPoint\("TOPRIGHT", sf, "TOPRIGHT", 11, -2\)', 1),
        ('sf 右边界 -22', r'DG\.Q_LIST_W - 22, -12', 1),
        ('滑块宽 6', r'vthumb:SetWidth\(6\)', 1),
    ]
    for name, pat, want in checks:
        h = hits(pat)
        ck('上一轮行为未被破坏：%s' % name, len(h) == want,
           '行 %s' % ','.join(str(n) for n, _ in h))

    # 本次新增是否顺带改了缩放基准（P2 遗留项）
    h_scale = hits(r'GetEffectiveScale')
    ck('（记录）滑块拖拽缩放基准现状', True,
       ' | '.join('%d:%s' % (n, t.strip()[:60]) for n, t in h_scale))


def main():
    cls_ids = part_a()
    part_b()
    part_c()
    print('=' * 72)
    print('通过 %d 项 / 失败 %d 项' % (len(PASSED), len(FAILED)))
    if FAILED:
        for f in FAILED:
            print('  ✗ %s' % f)
        return 1
    print('  ✓ 全部通过')
    return 0


if __name__ == '__main__':
    sys.exit(main())

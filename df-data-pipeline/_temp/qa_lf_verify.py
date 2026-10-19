# -*- coding: utf-8 -*-
"""掉落过滤回归 · 独立验证掉落页「装备过滤」（ns.LootFilter / LootFilterUI / LootFilterData）

用途：掉落过滤功能（预设 / 判定八步 / 方案管理 / 复用池 / 红线 / 硬约束）的**离线回归检查**。
不依赖 df_dungeon_check 的既有断言：本文件自带 lupa 桩 + 自写判定。
加载**源仓库** D:\\workspace\\DungeonsForever 的全部 TOC 文件（验证针对源码侧）。
退出码：0 = 全通过；1 = 有失败；建议由 _temp/run_all_checks.py 统一驱动。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools'):
    sys.path.insert(0, r'D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\BGLite\_temp\tools')
sys.path.insert(0, HERE)

import tf_dryrun as T          # noqa: E402
from lupa import lua51         # noqa: E402

ADDON = r'D:\workspace\DungeonsForever'      # ★ 验证源码侧
TOC = os.path.join(ADDON, 'DungeonsForever.toc')


def strip_toc_cond(s):
    """剥掉 TOC 行尾的「文件行指令」（形如 `[AllowLoadTextLocale zhTW]`）。

    与 df_dungeon_check.strip_toc_cond 同口径：行指令由客户端引擎解释（不在列表里的
    语言直接跳过该文件），离线校验不模拟条件加载，但**必须**把指令从路径里剥掉，
    否则 loadfile 会拿着 `Locales/zhTW.lua [AllowLoadTextLocale zhTW]` 去开文件 → nil。
    """
    return re.sub(r"\s*\[[^\]]*\]\s*$", "", s)


PASSED, FAILED = [], []


def ck(name, ok, extra=None):
    (PASSED if ok else FAILED).append(name)
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           '' if extra is None else '  [%s]' % extra))


def section(t):
    print('=' * 72)
    print(t)
    print('=' * 72)


# ---------------------------------------------------------------------------
# Lua 侧：ck 收集器 + 环境补丁
# ---------------------------------------------------------------------------
LUA_PRELUDE = r'''
QA = { R = {} }
function QA.ck(name, ok, extra)
    QA.R[#QA.R + 1] = (ok and "OK" or "FAIL") .. "\t" .. name
        .. "\t" .. (extra ~= nil and tostring(extra) or "")
end
function QA.run(chunk)
    QA.R = {}
    local ok, err = pcall(chunk)
    if not ok then
        local tb = (debug and debug.traceback) and debug.traceback(tostring(err), 2) or tostring(err)
        QA.R[#QA.R + 1] = "FAIL\t[Lua 块抛异常]\t" .. tostring(tb):gsub("[\r\n]+", " ")
    end
    return table.concat(QA.R, "\n")
end
function QA.reset(schemes, chooseID)
    local LF = TF_NS.LootFilter
    DungeonsForeverDB = { ui = {} }
    LF.__store = nil
    local st = LF.GetStore()
    for i = #st, 1, -1 do st[i] = nil end
    for i = 1, #(schemes or {}) do st[i] = schemes[i] end
    st.chooseID = chooseID
    LF.ClearResults()
    return st
end
function QA.card(id)
    local c = { __it = { id }, SetAlpha = function(self, a) self.alpha = a end }
    return c
end
'''


def LE(lua, expr):
    """把一段含 return 的代码包成表达式后求值（lupa.eval 只接受表达式）。"""
    return lua.eval('(function()\n' + expr + '\nend)()')


def parse(lua_out, header=None):
    if header:
        section(header)
    for line in (lua_out or '').split('\n'):
        if not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            ck('Lua 侧输出异常：' + line[:200], False)
            continue
        ck(parts[1], parts[0] == 'OK', parts[2] if len(parts) > 2 else None)


def main():
    section('独立验证 · 掉落页装备过滤（源码侧 %s）' % ADDON)

    files = [strip_toc_cond(l.strip()).replace('\\', '/') for l in
             open(TOC, encoding='utf-8', errors='replace').read().splitlines()
             if l.strip() and not l.strip().startswith('##')]

    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(T.STUB)
    lua.execute('os = nil')
    lua.execute('time = function() return 1796850000 end')
    lua.execute('UnitClass = function() return "战士", "WARRIOR", 1 end')   # 战士：有 3 套预设
    lua.execute("ADDON_ROOT = %r" % ADDON.replace('\\', '/'))
    lua.execute('TF_NS = TF_NS or {}')
    lua.execute("do local o = GetBuildInfo; GetBuildInfo = function(...) "
                "local a,b,c,d = o(...); return a,b,c,16001,e end end")
    lua.execute(LUA_PRELUDE)

    loadfile = lua.eval(
        'function(rel)\n'
        '  local chunk = loadfile(ADDON_ROOT .. "/" .. rel)\n'
        '  if not chunk then return nil end\n'
        '  return function() return chunk("DungeonsForever", TF_NS) end\n'
        'end')

    section('按 TOC 加载 %d 个文件（源仓库）' % len(files))
    n = 0
    for rel in files:
        if rel.lower().endswith('.xml'):
            continue
        chunk = loadfile(rel)
        if chunk is None:
            ck('加载 %s' % rel, False, 'loadfile 返回 nil')
            return 1
        try:
            chunk()
            n += 1
        except Exception as e:                                   # noqa: BLE001
            ck('加载 %s' % rel, False, str(e)[:200])
            return 1
    print('  已加载 %d 个 Lua 文件' % n)

    # ---------------------------------------------------------------- G0
    g0 = LE(lua, r'''return QA.run(function()
        local LF, D, UI = TF_NS.LootFilter, TF_NS.LootFilterData, TF_NS.LootFilterUI
        QA.ck("三层命名空间都已装载", LF ~= nil and D ~= nil and UI ~= nil,
              tostring(LF) .. "/" .. tostring(D) .. "/" .. tostring(UI))
        QA.ck("方案上限 MAX_SCHEMES = 6", LF.MAX_SCHEMES == 6, LF.MAX_SCHEMES)
        QA.ck("变灰程度 ALPHA_DIM = 0.4（设计：固定不可调）", LF.ALPHA_DIM == 0.4, LF.ALPHA_DIM)
        QA.ck("存档版本 LF.VER = 3（v3 删主属性维度 + 词缀重做）", LF.VER == 3, LF.VER)
        local want = "Weapon,Armor,ShuXing,Class,BnetAccount,Tank"
        local hasMA = false
        for _, d in ipairs(LF.DIMENSIONS) do if d == "MainAttribute" then hasMA = true end end
        QA.ck("方案维度顺序 = 设计六维（v3 已删主属性）",
              table.concat(LF.DIMENSIONS, ",") == want and #LF.DIMENSIONS == 6,
              table.concat(LF.DIMENSIONS, ",") .. " #" .. #LF.DIMENSIONS)
        QA.ck("v3·维度清单恰 6 项且不含 MainAttribute", #LF.DIMENSIONS == 6 and not hasMA,
              "hasMainAttribute=" .. tostring(hasMA))
        QA.ck("v3·旧「主属性」维度已删（D.MainAttr / D.MainAttrOrder 均 nil）",
              D.MainAttr == nil and D.MainAttrOrder == nil,
              tostring(D.MainAttr) .. " / " .. tostring(D.MainAttrOrder))
        QA.ck("classID 常量：武器2/护甲4/任务12", D.CLASS_WEAPON == 2 and D.CLASS_ARMOR == 4
              and D.CLASS_QUEST == 12, D.CLASS_WEAPON .. "/" .. D.CLASS_ARMOR .. "/" .. D.CLASS_QUEST)
        QA.ck("固定判定项名 = 过滤职业限定/忽略战网绑定/过滤坦克",
              D.FLAG_CLASS == "过滤职业限定" and D.FLAG_BNET == "忽略战网绑定"
              and D.FLAG_TANK == "过滤坦克")
        QA.ck("ClassPrefix 非空", type(D.ClassPrefix) == "string" and D.ClassPrefix ~= "",
              D.ClassPrefix)
        QA.ck("toPattern 转义魔法字符并令空白=任意串",
              D.toPattern("a(b") == "a%(b" and D.toPattern("a b") == "a(.+)b",
              tostring(D.toPattern("a(b")) .. "/" .. tostring(D.toPattern("a b")))
        local _, nm = LF.PlayerClass()
        QA.ck("PlayerClass 桩 = WARRIOR", nm == "WARRIOR", tostring(nm))
    end)''')
    parse(g0, 'G0 · 环境自检')

    # ---------------------------------------------------------------- G1
    g1 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local E = LF.Evaluate
        local _, MY = LF.PlayerClass()
        local function S(over)
            local s = { Name="t", Icon="i", Weapon={}, Armor={}, ShuXing={},
                        Class={}, BnetAccount={}, Tank={} }
            for k, v in pairs(over or {}) do s[k] = v end
            return s
        end
        -- ① 任务物品先短路
        local s1 = S{ Weapon={["7"]=1}, Armor={["1"]=1}, ShuXing={["力量"]=1} }
        QA.ck("顺序① 任务物品(classID 12)永不变灰", E(s1, D.CLASS_QUEST, "INVTYPE_WEAPON", 7, "") == false)
        QA.ck("顺序① 任务物品备用号(9)永不变灰", E(s1, D.CLASS_QUEST_ALT, "INVTYPE_WEAPON", 7, "") == false)
        QA.ck("顺序① 对照：非任务武器且在需要集→不变灰",
              E(s1, D.CLASS_WEAPON, "INVTYPE_WEAPON", 7, "") == false)
        -- ② 战网绑定豁免
        -- ② 战网绑定豁免（用「不在需要集」的武器子类 8，确保豁免确实改变结果）
        local s2 = S{ Weapon={["8"]=1}, BnetAccount={ [D.FLAG_BNET]=1 } }
        QA.ck("顺序② 绑定文本命中→豁免（武器本会变灰被救）",
              E(s2, D.CLASS_WEAPON, "INVTYPE_WEAPON", 7, "账号绑定") == false)
        QA.ck("顺序② 非绑定文本→仍按武器（不在需要集）变灰",
              E(s2, D.CLASS_WEAPON, "INVTYPE_WEAPON", 7, "拾取后绑定") == true)
        QA.ck("顺序② 开关关时不豁免",
              E(S{ Weapon={["8"]=1} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 7, "账号绑定") == true)
        -- ③ 护甲（排除披风；副手须 HOLDABLE；不在需要集→变灰）
        QA.ck("顺序③ 护甲子类不在需要集→变灰", E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 2, "") == true)
        QA.ck("顺序③ 护甲子类在需要集→不变灰", E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "") == false)
        QA.ck("顺序③ 披风 INVTYPE_CLOAK 恒不参与护甲维度（子类不在需要集也放过）",
              E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_CLOAK", 2, "") == false)
        QA.ck("顺序③ 副手 subID=0 且 HOLDABLE 且不在需要集→变灰",
              E(S{ Armor={["6"]=1} }, D.CLASS_ARMOR, "INVTYPE_HOLDABLE", 0, "") == true)
        QA.ck("顺序③ 副手 subID=0 但非 HOLDABLE（盾）→不因此变灰",
              E(S{ Armor={["6"]=1} }, D.CLASS_ARMOR, "INVTYPE_SHIELD", 0, "") == false)
        QA.ck("顺序③ 盾牌 subID=6 在需要集→不变灰",
              E(S{ Armor={["6"]=1} }, D.CLASS_ARMOR, "INVTYPE_SHIELD", 6, "") == false)
        -- ③ 只是护甲维度放过披风；其他维度仍可变灰
        QA.ck("顺序③ 披风：护甲维度跳过，但词缀维度仍可变灰",
              E(S{ ShuXing={["智力"]=1} }, D.CLASS_ARMOR, "INVTYPE_CLOAK", 1, "+20 力量") == true)
        -- ④ 武器
        QA.ck("顺序④ 武器子类在需要集→不变灰", E(S{ Weapon={["7"]=1} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 7, "") == false)
        QA.ck("顺序④ 武器子类不在需要集→变灰", E(S{ Weapon={["7"]=1} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 8, "") == true)
        -- ⑤ 词缀
        QA.ck("顺序⑤ 词缀在需要集且命中→不变灰", E(S{ ShuXing={["力量"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "+20 力量") == false)
        QA.ck("顺序⑤ 词缀在需要集但一个都没命中→变灰", E(S{ ShuXing={["力量"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "+20 敏捷") == true)
        -- ⑥ 职业限定
        local s6 = S{ Class={ [D.FLAG_CLASS]=1 } }
        QA.ck("顺序⑥ 含职业行且不含本职业→变灰",
              E(s6, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, D.ClassPrefix .. "法师") == true)
        QA.ck("顺序⑥ 含本职业名→不变灰",
              E(s6, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, D.ClassPrefix .. MY) == false)
        QA.ck("顺序⑥ 无职业行→不触发", E(s6, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "护甲 +20") == false)
        -- ⑦ 坦克（排除饰品/圣物）
        local s7 = S{ Tank={ [D.FLAG_TANK]=1 } }
        QA.ck("顺序⑦ 护甲无坦克关键词→变灰", E(s7, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "护甲 +100") == true)
        QA.ck("顺序⑦ 含坦克关键词→不变灰", E(s7, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "招架 +10") == false)
        QA.ck("顺序⑦ 饰品 INVTYPE_TRINKET 排除", E(s7, D.CLASS_ARMOR, "INVTYPE_TRINKET", 1, "护甲 +100") == false)
        QA.ck("顺序⑦ 圣物 INVTYPE_RELIC 排除", E(s7, D.CLASS_ARMOR, "INVTYPE_RELIC", 1, "护甲 +100") == false)
        -- ⑧（v3 已删）旧「主属性」维度不存在：主属性已并入⑤词缀维度。
        -- 老存档里残留的 scheme.MainAttribute 字段必须被无视（不改判定结果）。
        QA.ck("v3·旧方案残留 MainAttribute 字段不参与判定（已并入词缀维度）",
              E(S{ MainAttribute={["力量"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "智力 +20") == false)
        -- 边界
        QA.ck("边界 typeID=nil → ShouldGrey false", LF.ShouldGrey(1, nil, nil, nil, "") == false)
        QA.ck("边界 Evaluate typeID=nil → false", E(S{ Armor={["1"]=1} }, nil, "INVTYPE_CHEST", 1, "") == false)
    end)''')
    parse(g1, 'G1 · 判定顺序（不可重排，v3 = 七步）')

    # ---------------------------------------------------------------- G2
    g2 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        GetItemInfoInstant = function(id) return id, "护甲", "板甲", "INVTYPE_CHEST", 135005, D.CLASS_ARMOR, 4 end
        -- 默认关：chooseID=nil。注意新语义「勾选=我需要」：桩物品 subID=4，
        -- 故需要集取 {["1"]=1}（不含 4），开方案后该护甲应被判为「不在需要集」→变灰。
        local st = QA.reset({
            { Name="s", Icon="i", Weapon={}, Armor={["1"]=1}, ShuXing={},
              Class={}, BnetAccount={}, Tank={} },
        }, nil)
        QA.ck("默认关：chooseID=nil 时 ShouldGrey 一律 false",
              LF.ShouldGrey(9001, D.CLASS_ARMOR, "INVTYPE_CHEST", 4, "") == false)
        local c = QA.card(9001)
        LF.Apply(c)
        QA.ck("默认关：Apply 卡片 alpha 回满(1)", c.alpha == LF.ALPHA_FULL, c.alpha)
        -- 打开方案
        st.chooseID = 1
        LF.ClearResults()
        QA.ck("开方案后：护甲不在需要集→ShouldGrey true",
              LF.ShouldGrey(9002, D.CLASS_ARMOR, "INVTYPE_CHEST", 4, "") == true)
        local c2 = QA.card(9002)
        LF.Apply(c2)
        QA.ck("开方案后：Apply 卡片 alpha=0.4", c2.alpha == LF.ALPHA_DIM, c2.alpha)
        -- 缓存
        st[1].Armor = {}
        QA.ck("结果缓存：未清缓存时读旧值", LF.ShouldGrey(9002, D.CLASS_ARMOR, "INVTYPE_CHEST", 4, "") == true)
        LF.ClearResults()
        QA.ck("ClearResults 后按新方案重算", LF.ShouldGrey(9002, D.CLASS_ARMOR, "INVTYPE_CHEST", 4, "") == false)
        -- Invalidate
        st[1].Armor = {["1"]=1}; LF.ClearResults()
        QA.ck("Invalidate 前命中", LF.ShouldGrey(9003, D.CLASS_ARMOR, "INVTYPE_CHEST", 4, "") == true)
        LF.Invalidate(9003)
        st[1].Armor = {}
        QA.ck("Invalidate 后按新方案重算", LF.ShouldGrey(9003, D.CLASS_ARMOR, "INVTYPE_CHEST", 4, "") == false)
        -- 数据未就绪（classID nil）→ 全额 + 登记补判，不崩
        GetItemInfoInstant = nil
        local c4 = QA.card(9004)
        local ok = pcall(LF.Apply, c4)
        QA.ck("客户端无物品数据时不崩且 alpha=1", ok and c4.alpha == LF.ALPHA_FULL, tostring(ok) .. "/" .. tostring(c4.alpha))
        GetItemInfoInstant = function(id) return id, "护甲", "板甲", "INVTYPE_CHEST", 135005, D.CLASS_ARMOR, 4 end
    end)''')
    parse(g2, 'G2 · 默认关 + Apply 卡片 alpha + 缓存')

    # ---------------------------------------------------------------- G3
    g3 = LE(lua, r'''return QA.run(function()
        -- 先构建 UI（掉落池）
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local U = TF_NS.DungeonUI
        PLAYER_LEVEL = 60
        UnitLevel = function() return PLAYER_LEVEL end
        -- 桩的 CheckButton.Text 兜底成 function（真端为 nil），Hui.ReskinToggle 会栽在这里。
        -- 与既有 harness（df_dungeon_check）同样把它桩掉：与本功能无关的桩限制作工作区。
        if TF_NS.hui then TF_NS.hui.ReskinToggle = function() end end
        if not U.built then U:Build() end
        U:SwitchSub("Dungeons")
        GetItemInfo, GetItemInfoInstant = nil, nil
        C_Item = { GetItemInfoInstant = function(id) return id, "护甲", "板甲", "INVTYPE_CHEST", 135005, 4, 4 end }
        local hall, emptyDg
        for _, d in ipairs(TF_NS.DungeonData.dungeons) do
            if d.id == "hall_of_thanes" then hall = d end
            if d.id == "city_of_dalaran" then emptyDg = d end      -- 9 个「源存在但掉落为空」
        end
        QA.ck("样例副本定位（塞恩大厅 / 空掉落源副本）", hall ~= nil and emptyDg ~= nil)
        U:ShowDungeonDetail(hall)                         -- 先渲染，铺满物品行池
        local pool = U.dungeonDetailPool
        QA.ck("掉落池已就位（两级池 + 已铺物品行）",
              type(pool) == "table" and type(pool.item) == "table" and #pool.item >= 13, #pool.item)
        -- 包装每张卡的 SetAlpha 记录 alpha（必须在渲染之后：池是懒建的）
        for _, r in ipairs(pool.item) do
            local o = r.SetAlpha
            r.SetAlpha = function(self, a) rawset(self, "__qaA", a); return o(self, a) end
        end
        -- 方案：需要集不含 4（桩里物品都是护甲子类 4）→ 应全部被判「不在需要集」而变灰
        local st = QA.reset({
            { Name="s", Icon="i", Weapon={}, Armor={["1"]=1}, ShuXing={},
              Class={}, BnetAccount={}, Tank={} },
        }, 1)
        LF.ApplyAll()
        local dimmed = 0
        for _, r in ipairs(pool.item) do
            if r.__shown and r.__it and rawget(r, "__qaA") == 0.4 then dimmed = dimmed + 1 end
        end
        QA.ck("有掉落副本：命中护甲的卡片被变灰（alpha=0.4）", dimmed > 0, dimmed)
        -- 切到「源存在但掉落为空」的副本：复用池卡片 alpha 必须复位为 1（不留上一轮灰值）
        U:ShowDungeonDetail(emptyDg)
        local stale = 0
        for _, r in ipairs(pool.item) do
            if r.__shown and rawget(r, "__qaA") == 0.4 then stale = stale + 1 end
        end
        QA.ck("空掉落源副本：无任何复用卡片残留灰值（alpha 复位为 1）", stale == 0, stale)
        -- 就地重算：ApplyAll 不得触发重新渲染 / 不得弹回顶部
        U:ShowDungeonDetail(hall)
        local scroll = U.dungeonDetailScroll
        local nscroll, nrender = 0, 0
        local osv, osd = scroll.SetVerticalScroll, U.ShowDungeonDetail
        scroll.SetVerticalScroll = function(self, ...) nscroll = nscroll + 1; return osv(self, ...) end
        U.ShowDungeonDetail = function(self, ...) nrender = nrender + 1; return osd(self, ...) end
        LF.ApplyAll()
        scroll.SetVerticalScroll = osv; U.ShowDungeonDetail = osd
        QA.ck("ApplyAll 就地重算：不触发重新渲染 / 不弹回顶部（两计数为 0）",
              nscroll == 0 and nrender == 0, nscroll .. "/" .. nrender)
    end)''')
    parse(g3, 'G3 · 复用池复位 + 就地重算')

    # 静态：v4 勾选框由 iOS 开关（MakeToggle）承载，OnClick 走 LF.SetOption + LF.ApplyAll
    #   （就地重算，不重渲染 / 不弹回顶部）。锚点以 v4 实际代码为准：
    #   tg:SetScript("OnClick") → cfg.cells[#cfg.cells + 1]；字段名为 self.dim / self.key。
    ui_src = open(os.path.join(ADDON, 'Core', 'LootFilterUI.lua'),
                  encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    _tg0 = ui_src.index('tg:SetScript("OnClick"')
    cbseg = ui_src[_tg0:ui_src.index('cfg.cells[#cfg.cells + 1]', _tg0)]
    ck('静态·v4 开关 OnClick 走 LF.SetOption + LF.ApplyAll（就地重算）',
       'LF.SetOption(sch, self.dim, self.key' in cbseg and 'LF.ApplyAll()' in cbseg)
    ck('静态·v4 开关 OnClick 不重渲染（无 ShowDungeonDetail）',
       'ShowDungeonDetail' not in cbseg)

    # ---------------------------------------------------------------- G4
    g4 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local st = QA.reset({}, nil)          -- 空存档，0 个方案
        local ids = {}
        for i = 1, 6 do ids[i] = LF.AddScheme("方案" .. i, "Interface\\Icons\\INV_Sword_01") end
        QA.ck("新建 6 个方案依次返回 1..6", ids[1] == 1 and ids[6] == 6,
              tostring(ids[1]) .. ".." .. tostring(ids[6]))
        QA.ck("新建后 #store == 6", #st == 6, #st)
        local r7 = LF.AddScheme("第7个", "Interface\\Icons\\INV_Axe_01")
        QA.ck("上限 6：第 7 个返回 nil", r7 == nil, tostring(r7))
        QA.ck("上限 6：第 7 个不写档（#store 仍 6）", #st == 6, #st)
        LF.RenameScheme(2, "改名后")
        QA.ck("改名生效", st[2].Name == "改名后", st[2].Name)
        LF.SetSchemeIcon(2, "Interface\\Icons\\INV_Axe_01")
        QA.ck("换图标生效", st[2].Icon == "Interface\\Icons\\INV_Axe_01", st[2].Icon)
        local n1, n2 = st[1].Name, st[2].Name
        LF.MoveScheme(1, 1)
        QA.ck("排序（1↔2 对调）", st[1].Name == n2 and st[2].Name == n1)
        QA.ck("排序边界：越界移动无副作用", (function()
            local a = st[1].Name; LF.MoveScheme(6, 1); return st[1].Name == a end)())
        LF.SetActiveScheme(3)
        QA.ck("切方案 chooseID=3", st.chooseID == 3, st.chooseID)
        LF.SetActiveScheme(99)
        QA.ck("切不存在方案→chooseID=nil", st.chooseID == nil, tostring(st.chooseID))
        LF.SetActiveScheme(3)
        local n3 = st[3].Name
        LF.DeleteScheme(2)
        QA.ck("删除后 #store==5", #st == 5, #st)
        QA.ck("删除后激活下标左移（3→2）", st.chooseID == 2, tostring(st.chooseID))
        QA.ck("删除后原 3 号元素前移", st[2].Name == n3, st[2].Name)
        LF.DeleteScheme(2)
        QA.ck("删除的正是激活方案→chooseID=nil", st.chooseID == nil, tostring(st.chooseID))
        local n0 = #st
        LF.DeleteScheme(99)
        QA.ck("删除越界索引无副作用", #st == n0, #st)
        -- 全勾 / 全不勾
        local s = st[1]
        LF.ToggleBulk(s, "all")
        QA.ck("全勾：Weapon/Armor/Tank/Class/Bnet 都有项",
              next(s.Weapon) ~= nil and next(s.Armor) ~= nil and s.Tank[D.FLAG_TANK] == 1
              and s.Class[D.FLAG_CLASS] == 1 and s.BnetAccount[D.FLAG_BNET] == 1)
        LF.ToggleBulk(s, "none")
        QA.ck("全不勾：各维度清空", next(s.Weapon) == nil and next(s.Armor) == nil
              and next(s.Tank) == nil and next(s.Class) == nil)
    end)''')
    parse(g4, 'G4 · 方案 CRUD + 上限 6')

    # ---------------------------------------------------------------- G5
    g5 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local list = LF.LoadPresets("WARRIOR")
        QA.ck("战士预设 3 套", #list == 3, #list)
        local s = list[1]
        local pre = D.Presets["WARRIOR"][1]
        -- v3 需求式（勾选=我需要）：ConvertPreset 把该套 useWeapon/useArmor 的「名称」
        -- 逐个映射为 subclassID 字符串键。期望值一律从该套 useWeapon/useArmor + 反查表推导，
        -- 不硬编码旧（v2 排除式）结论。
        local function mapKeys(names, map)
            local want, n = {}, 0
            for _, nm in ipairs(names or {}) do
                local sid = map[nm]
                if sid ~= nil then want[tostring(sid)] = 1; n = n + 1 end
            end
            return want, n
        end
        local function count(t)
            local n = 0
            for _ in pairs(t or {}) do n = n + 1 end
            return n
        end
        local function sameSet(got, want, n)
            if count(got) ~= n then return false end
            for k, v in pairs(want) do if got[k] ~= v then return false end end
            return true
        end
        local wW, wWn = mapKeys(pre.useWeapon, D.WeaponIdByName)
        local wA, wAn = mapKeys(pre.useArmor, D.ArmorIdByName)
        QA.ck("转换·需求式：Weapon 键集 = 该套 useWeapon 逐名映射（无多无少）",
              sameSet(s.Weapon, wW, wWn), "want#" .. wWn .. " got#" .. count(s.Weapon))
        QA.ck("转换·需求式：Armor 键集 = 该套 useArmor 逐名映射（无多无少）",
              sameSet(s.Armor, wA, wAn), "want#" .. wAn .. " got#" .. count(s.Armor))
        QA.ck("转换·需求式：战士-武器 useWeapon 含 双手斧1/法杖10 → 均在需要集",
              s.Weapon["1"] == 1 and s.Weapon["10"] == 1,
              "双手斧1=" .. tostring(s.Weapon["1"]) .. " 法杖10=" .. tostring(s.Weapon["10"]))
        QA.ck("转换·需求式：未列入 useWeapon 的子类（单手斧0/单手剑7）不在需要集",
              s.Weapon["0"] == nil and s.Weapon["7"] == nil,
              "单手斧0=" .. tostring(s.Weapon["0"]) .. " 单手剑7=" .. tostring(s.Weapon["7"]))
        QA.ck("转换·需求式：战士-武器 useArmor = 皮甲/锁甲/板甲 → 键 2/3/4 在内、盾牌6/布甲1 不在",
              s.Armor["2"] == 1 and s.Armor["3"] == 1 and s.Armor["4"] == 1
              and s.Armor["6"] == nil and s.Armor["1"] == nil,
              "皮2=" .. tostring(s.Armor["2"]) .. " 锁3=" .. tostring(s.Armor["3"])
              .. " 板4=" .. tostring(s.Armor["4"]) .. " 盾6=" .. tostring(s.Armor["6"])
              .. " 布1=" .. tostring(s.Armor["1"]))
        QA.ck("转换：Class/Bnet 固定项补上",
              s.Class[D.FLAG_CLASS] == 1 and s.BnetAccount[D.FLAG_BNET] == 1)
        -- ★ 坦克维度：预设数据 Tank={"过滤坦克"}，存档 schema 是 keyed
        local prot = list[3]
        QA.ck("★ 防护预设的坦克维度确实勾上（Tank[FLAG_TANK]==1）",
              prot.Tank[D.FLAG_TANK] == 1, tostring(prot.Tank[D.FLAG_TANK])
              .. " raw[1]=" .. tostring(rawget(prot.Tank, 1)))
        -- 深拷贝
        local p = D.Presets["WARRIOR"][1]
        local beforeW = #(p.useWeapon or {})
        s.Weapon["999"] = 1
        QA.ck("深拷贝：改返回方案不污染 D.Presets",
              #(p.useWeapon or {}) == beforeW)
        local l2 = LF.LoadPresets("WARRIOR")
        QA.ck("深拷贝：再次 LoadPresets 得干净副本（无 999）", l2[1].Weapon["999"] == nil)
        QA.ck("深拷贝：两次返回不同表", l2[1] ~= list[1])
        -- ApplyPreset 重建（战士-防护：useWeapon 匕首/拳套/单手斧/单手锤/单手剑/弓/弩/枪/投掷武器；
        --                       useArmor 板甲4/盾牌6）
        local st = QA.reset({
            { Name="x", Icon="i", Weapon={["8"]=1}, Armor={["9"]=1}, ShuXing={["精神"]=1},
              Class={}, BnetAccount={}, Tank={["过滤坦克"]=1} },
        }, 1)
        LF.ApplyPreset(st[1], "WARRIOR", 3)     -- 防护
        QA.ck("ApplyPreset 重建：旧 Weapon 项被清（无 8）", st[1].Weapon["8"] == nil)
        QA.ck("ApplyPreset 重建：新 Weapon 项套上（含 0 单手斧）", st[1].Weapon["0"] == 1)
        QA.ck("ApplyPreset 重建：旧 Armor 项被清（无 9）", st[1].Armor["9"] == nil)
        QA.ck("ApplyPreset 重建：新 Armor 项套上（板甲4）", st[1].Armor["4"] == 1)
        QA.ck("ApplyPreset 重建：旧 ShuXing 项被清（无 精神）", st[1].ShuXing["精神"] == nil,
              tostring(st[1].ShuXing["精神"]))
        -- v3+：预设自带 useShuXing（战士-防护 = ROLE.t2，含 力量 等）——重建后应「旧清 + 新套」。
        -- 旧断言 next(ShuXing)==nil 属 v2（排除式、预设无词缀）残留，已失效（测试 bug，非产品）。
        QA.ck("ApplyPreset 重建：新 ShuXing 项按预设套上（含 力量，非空）",
              st[1].ShuXing["力量"] == 1 and next(st[1].ShuXing) ~= nil,
              tostring(st[1].ShuXing["力量"]))
        QA.ck("ApplyPreset 重建：Class/Bnet 仍补上",
              st[1].Class[D.FLAG_CLASS] == 1 and st[1].BnetAccount[D.FLAG_BNET] == 1)
        -- 兜底（无预设职业）：11 职业现已全覆盖，故用未知职业名真正走兜底
        local fb = LF.LoadPresets("NONE_CLASS")
        QA.ck("无预设职业(NONE_CLASS)走兜底且非空", type(fb) == "table" and #fb >= 1, #fb)
        local fb2 = LF.LoadPresets(nil)
        QA.ck("classFile=nil 兜底不报错", type(fb2) == "table" and #fb2 >= 1)
        local pr = LF.LoadPresets("WARRIOR")
        QA.ck("★ 预设来源序号：LoadPresets 逐套带 PresetIdx",
              pr[1].PresetIdx == 1 and pr[3].PresetIdx == 3,
              tostring(pr[1].PresetIdx) .. "/" .. tostring(pr[3].PresetIdx))
        local stP = QA.reset({
            { Name = "我的防护", Icon = "自定义", PresetIdx = 3, Weapon = {["8"]=1}, Armor = {}, ShuXing = {},
              Class = {}, BnetAccount = {}, Tank = {} },
        }, 1)
        LF.ApplyPreset(stP[1], "WARRIOR")
        QA.ck("★ 重置按方案自身来源（PresetIdx=3 防护），不恒取第 1 套",
              stP[1].Armor["4"] == 1 and stP[1].Armor["6"] == 1 and stP[1].Tank[D.FLAG_TANK] == 1
              and stP[1].Weapon["0"] == 1,
              "板4=" .. tostring(stP[1].Armor["4"]) .. " 盾6=" .. tostring(stP[1].Armor["6"])
              .. " 坦=" .. tostring(stP[1].Tank[D.FLAG_TANK]))
        QA.ck("重置后来源序号写回（仍为 3）", stP[1].PresetIdx == 3, tostring(stP[1].PresetIdx))
        QA.ck("重置不覆盖方案自定名与图标",
              stP[1].Name == "我的防护" and stP[1].Icon == "自定义",
              tostring(stP[1].Name) .. "/" .. tostring(stP[1].Icon))
        local stZ = QA.reset({
            { Name = "未命名方案", Icon = D.DEFAULT_ICON, Weapon = {}, Armor = {}, ShuXing = {},
              Class = {}, BnetAccount = {}, Tank = {} },
        }, 1)
        LF.ApplyPreset(stZ[1], "WARRIOR")
        QA.ck("无来源方案（缺 PresetIdx）→ 兜底首套 = 战士-武器",
              stZ[1].Weapon["1"] == 1 and stZ[1].Armor["6"] == nil,
              "双手斧1=" .. tostring(stZ[1].Weapon["1"]) .. " 盾6=" .. tostring(stZ[1].Armor["6"]))
        local stN = QA.reset({
            { Name = "战士-防护", Icon = D.DEFAULT_ICON, PresetIdx = 1, Weapon = {}, Armor = {}, ShuXing = {},
              Class = {}, BnetAccount = {}, Tank = {} },
        }, 1)
        LF.ApplyPreset(stN[1], "WARRIOR")
        QA.ck("★ 方案名即预设名时以名字为准（PresetIdx 被污染也能自愈）",
              stN[1].Armor["4"] == 1 and stN[1].Armor["6"] == 1 and stN[1].PresetIdx == 3,
              "板4=" .. tostring(stN[1].Armor["4"]) .. " 盾6=" .. tostring(stN[1].Armor["6"])
              .. " 序号=" .. tostring(stN[1].PresetIdx))
        local hun = LF.LoadPresets("HUNTER")
        local stR = QA.reset({
            { Name = "猎人", Icon = "旧图标", PresetIdx = 1, Weapon = {["19"]=1}, Armor = {}, ShuXing = {},
              Class = {}, BnetAccount = {}, Tank = {} },
        }, 1)
        LF.ApplyPreset(stR[1], "HUNTER", 3)
        QA.ck("★ 显式选预设重置：名字与图标一起恢复成该套（猎人-射击）",
              stR[1].Name == "猎人-射击" and stR[1].Icon == hun[3].Icon and stR[1].PresetIdx == 3,
              tostring(stR[1].Name) .. "/" .. tostring(stR[1].PresetIdx) .. "/" .. tostring(stR[1].Icon))
        QA.ck("显式选预设重置：旧子类被清（无 19 魔杖）", stR[1].Weapon["19"] == nil,
              tostring(stR[1].Weapon["19"]))
    end)''')
    parse(g5, 'G5 · 预设转换 + 深拷贝')

    # ---------------------------------------------------------------- G6
    g6 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        -- ▉ 场景 A：无 ver（旧「排除式」档）→ 版本不一致 ⇒ 整块重置 + 重铺本职业预设
        DungeonsForeverDB = { ui = { lootFilter = { [ "未知服务器" ] = { [ "未知角色" ] = {
            { Name = 123, Weapon = { ["7"] = 1 } },
            { },
            "坏元素",
        }, chooseID = 99 } } } }
        LF.__store = nil
        local ok = pcall(function() return LF.GetStore() end)
        QA.ck("版本重置：GetStore 不报错", ok)
        local st = LF.GetStore()
        QA.ck("版本重置：ver 被置为 LF.VER(3)", DungeonsForeverDB.ui.lootFilter.ver == 3,
              tostring(DungeonsForeverDB.ui.lootFilter.ver))
        QA.ck("版本重置：旧档被整块清空并重铺本职业预设（战士 3 套）", #st == 3, #st)
        QA.ck("版本重置：旧记录 Weapon[7] 不再存在", st[1].Weapon["7"] == nil,
              tostring(st[1].Weapon["7"]))
        QA.ck("版本重置：重铺首套 = 战士-武器", st[1].Name == "战士-武器", tostring(st[1].Name))
        QA.ck("版本重置：重铺后 chooseID 复位（nil）", st.chooseID == nil, tostring(st.chooseID))
        -- ▉ 场景 B：同版本(ver=3)残缺档 → 不清空，仅由 ShapeStore 修正字段
        DungeonsForeverDB = { ui = { lootFilter = { ver = 3, [ "未知服务器" ] = { [ "未知角色" ] = {
            { Name = 123, Weapon = { ["7"] = 1 } },     -- Name 非字符串、缺 Icon 与其它维度
            { },                                        -- 几乎全缺
            "坏元素",                                   -- 非表元素
        }, chooseID = 99 } } } }
        LF.__store = nil
        local st2 = LF.GetStore()
        QA.ck("同版本残缺档：Name 非法→补默认", type(st2[1].Name) == "string" and st2[1].Name ~= "",
              tostring(st2[1].Name))
        QA.ck("同版本残缺档：Icon 缺失→补默认图标", type(st2[1].Icon) == "string" and st2[1].Icon ~= "")
        QA.ck("同版本残缺档：维度补齐为表（v3 六维）",
              type(st2[1].Armor) == "table" and type(st2[1].ShuXing) == "table"
              and type(st2[1].Class) == "table"
              and type(st2[1].BnetAccount) == "table" and type(st2[1].Tank) == "table"
              and st2[1].MainAttribute == nil)
        QA.ck("同版本残缺档：已有字段不被清（Weapon[7] 保留）", st2[1].Weapon["7"] == 1)
        QA.ck("同版本残缺档：chooseID 越界(99)→nil", st2.chooseID == nil, tostring(st2.chooseID))
        -- ▉ 场景 C：无 ver 的合法旧档 → 补 ver（重置后为 3）
        DungeonsForeverDB = { ui = { lootFilter = { [ "未知服务器" ] = { [ "未知角色" ] = {
            { Name = "旧", Icon = "i", Weapon = {}, Armor = {}, ShuXing = {},
              Class = {}, BnetAccount = {}, Tank = {} },
        } } } } }
        LF.__store = nil
        local ok2 = pcall(function() return LF.GetStore() end)
        QA.ck("无 ver 旧档：不报错且补 ver 为 3",
              ok2 and DungeonsForeverDB.ui.lootFilter.ver == 3,
              tostring(DungeonsForeverDB.ui.lootFilter.ver))
        -- ▉ 场景 D：GetRealmName / UnitName 缺失时的兜底 key
        local ok3 = pcall(function() DungeonsForeverDB = { ui = {} }; LF.__store = nil; LF.GetStore() end)
        QA.ck("缺 GetRealmName/UnitName：靠兜底 key 建条目不报错", ok3)
        QA.ck("兜底 key 条目已建（lootFilter 下有子表）",
              (function()
                  local lf = DungeonsForeverDB.ui.lootFilter
                  if type(lf) ~= "table" then return false end
                  for k, v in pairs(lf) do if k ~= "ver" and type(v) == "table" then return true end end
                  return false
              end)())
        DungeonsForeverDB = { ui = { lootFilter = { ver = 3, [ "未知服务器" ] = { [ "未知角色" ] = {
            { Name = "战士-防护", Icon = "x", Weapon = {}, Armor = {}, ShuXing = {},
              Class = {}, BnetAccount = {}, Tank = {} },
            { Name = "自定义", Icon = "y", Weapon = {}, Armor = {}, ShuXing = {},
              Class = {}, BnetAccount = {}, Tank = {} },
        }, chooseID = 1 } } } }
        LF.__store = nil
        local st4 = LF.GetStore()
        QA.ck("★ 旧档迁移：无 PresetIdx 的方案按名字反查来源（战士-防护 → 3）",
              st4[1].PresetIdx == 3, tostring(st4[1].PresetIdx))
        QA.ck("旧档迁移：名字/图标都不属预设 → 标为无来源(0)",
              st4[2].PresetIdx == 0, tostring(st4[2].PresetIdx))
    end)''')
    parse(g6, 'G6 · 老存档兼容')

    # ---------------------------------------------------------------- G7
    g7 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local U = TF_NS.DungeonUI
        -- ns.LootFilter / ns.LootFilterUI/Data 缺失时，掉落页仍能正常渲染（不白屏、不报错）
        local saveLF, saveUI, saveD = TF_NS.LootFilter, TF_NS.LootFilterUI, TF_NS.LootFilterData
        TF_NS.LootFilter, TF_NS.LootFilterUI, TF_NS.LootFilterData = nil, nil, nil
        local ok = pcall(function()
            U:SetDungeonTab("loot")
            U:RenderDungeonTab()
            U:RenderDungeonLoot()
        end)
        TF_NS.LootFilter, TF_NS.LootFilterUI, TF_NS.LootFilterData = saveLF, saveUI, saveD
        QA.ck("ns.LootFilter* 全缺时：掉落页渲染不抛错", ok)
        -- 客户端 API 全缺（GetItemInfo / C_Item 都无）时渲染不崩
        GetItemInfo, GetItemInfoInstant, C_Item = nil, nil, nil
        local ok2 = pcall(function() U:ShowDungeonDetail(TF_NS.DungeonData.dungeons[1]); U:RenderDungeonLoot() end)
        QA.ck("客户端物品 API 全缺时：渲染不抛错", ok2)
        -- ShouldGrey 空参（全部 nil）不崩
        QA.ck("ShouldGrey 全 nil 参数不崩", pcall(function() LF.ShouldGrey() end))
        -- 契约：Evaluate 的 scheme 由 ShouldGrey 保证非 nil；维度全缺的方案也不崩
        QA.ck("Evaluate(维度全缺的方案) 不崩且返回 false",
              pcall(function() return LF.Evaluate({}, D.CLASS_ARMOR, "X", 1, "y") end))
        QA.ck("Evaluate(维度全缺) 结果 = false",
              LF.Evaluate({}, D.CLASS_ARMOR, "X", 1, "y") == false)
    end)''')
    parse(g7, 'G7 · 边界 / 错误路径')

    # ---------------------------------------------------------------- G8 静态红线
    section('G8 · 红线扫描（静态）')
    lf_files = ['Core/LootFilter.lua', 'Core/LootFilterUI.lua', 'Core/Data/Data_LootFilter.lua',
                'Core/Data/zhTW/Data_LootFilter.lua', 'Core/Data/enUS/Data_LootFilter.lua']
    texts = {}
    for f in lf_files:
        texts[f] = open(os.path.join(ADDON, f.replace('/', os.sep)),
                        encoding='utf-8', errors='replace').read()
    alltext = '\n'.join(texts.values())
    toc_text = open(TOC, encoding='utf-8', errors='replace').read()

    # 第三方插件名 / 作者 / BG. 前缀 / 外部资源路径
    # 'BG.' 只禁第三方插件命名空间（BiaoGe 的 BG.），不含本插件内嵌库句柄 ns.LibBG.*
    # 外部资源路径口径（v4 修订）：一律禁指向**其他**插件的 Interface/AddOns/<别的插件>/…；
    #   本插件自身目录 Interface[/\\]AddOns[/\\]DungeonsForever[…（自引用）属 Core 全域既有惯例
    #   （Core/DungeonUI.lua:419 · Core/Hui.lua:1563 同款 arrow.tga 自引用），不算外部路径。
    forbidden = ['BiaoGe', 'BGLite', 'TalentSim', 'TalentsForever', '胡里胡涂', '黑科研']
    hits = [w for w in forbidden if w in alltext]
    _ext = re.findall(r'Interface[/\\]AddOns[/\\](?!DungeonsForever(?:[/\\]|$))([^"\'\\/]+)', alltext)
    if _ext:
        hits.append('外部插件资源路径:' + ','.join(sorted(set(_ext))))
    if re.search(r'(?<![A-Za-z_])BG\.', alltext):
        hits.append('BG. 前缀')
    ck('红线·产物无第三方插件名/作者/ BG. 前缀/外部插件资源路径（自引用豁免）', not hits, hits or 'clean')
    # 措辞
    words = ['上游', '参考', '移植', '照抄', '出处', '剥离', '抄袭']
    whits = [w for w in words if w in alltext]
    ck('红线·无「上游/参考/移植/照抄/出处/剥离」类措辞', not whits, whits or 'clean')
    # 数据来源口令：整个界面只允许一条「数据来源：wowhead」
    mf_src = open(os.path.join(ADDON, 'Core', 'MainFrame.lua'),
                  encoding='utf-8', errors='replace').read()
    n_backend = alltext.count('数据来源：wowhead')
    ck('红线·LF 各文件不新增「数据来源」口令（界面只允许一条，在关于页）', n_backend == 0, n_backend)
    ck('红线·关于页保留唯一一条「数据来源：wowhead」',
       mf_src.count('数据来源：wowhead') == 1, mf_src.count('数据来源：wowhead'))
    # 本地化覆盖层：意图区分（v3 修正 — 原断言把 zhTW 误当占位层）
    #  · enUS = 「占位层」——不含数据表（只有守卫 + 结构注释），引擎按 subclassID 判定，
    #    名称缺失无碍功能，故 enUS 客户端走简体兜底；
    #  · zhTW = 「完整数据覆盖层」——由 _temp/gen_zhtw_data.py 生成（禁手改），
    #    必须等于源文件的繁化结果（忽略注释与空行后逐行相等），且不得残留已删维度的标记。
    def _split_code_comment(line):
        code, comment, in_str, i = line, '', False, 0
        while i < len(line):
            c = line[i]
            if c == '\\' and in_str:
                i += 2
                continue
            if c in ('"', "'"):
                in_str = not in_str
            elif not in_str and line[i:i + 2] == '--':
                code, comment = line[:i], line[i:]
                break
            i += 1
        return code, comment

    def _zhtw_norm(lines):
        out = []
        for ln in lines:
            code, _ = _split_code_comment(ln)
            code = code.rstrip()
            if code.strip():
                out.append(code)
        return out

    t_en = texts['Core/Data/enUS/Data_LootFilter.lua']
    ck('覆盖占位（enUS）不含武器/护甲数据表（走简体兜底）',
       'WeaponName' not in t_en and 'Presets' not in t_en and 'ArmorName' not in t_en)

    src_lf = texts['Core/Data/Data_LootFilter.lua']
    zhtw_lf = texts['Core/Data/zhTW/Data_LootFilter.lua']
    ck('覆盖层（zhTW）为完整数据表（非占位，有意）',
       'WeaponName' in zhtw_lf and 'Presets' in zhtw_lf)
    import gen_zhtw_data as _G
    _conv_norm = _zhtw_norm([_G.convert_line(_split_code_comment(l)[0])[0]
                             for l in src_lf.replace('\r\n', '\n').split('\n')])
    _zl = zhtw_lf.replace('\r\n', '\n').split('\n')
    _gi = max(i for i, l in enumerate(_zl) if "if gl ~= 'zhTW' then return end" in l)
    _zhtw_body = _zhtw_norm(_zl[_gi + 1:])
    _zhtw_full = _zhtw_norm(_zl)
    _eq = _conv_norm == _zhtw_body
    _diff = 'src#%d zhTW#%d equal' % (len(_conv_norm), len(_zhtw_body))
    if not _eq:
        for _i in range(max(len(_conv_norm), len(_zhtw_body))):
            _a = _conv_norm[_i] if _i < len(_conv_norm) else '<缺行>'
            _b = _zhtw_body[_i] if _i < len(_zhtw_body) else '<缺行>'
            if _a != _b:
                _diff = '首个差异@%d 源繁化=%r vs zhTW=%r' % (_i, _a[:80], _b[:80])
                break
    ck('覆盖层一致性·zhTW = 源文件的繁化结果（忽略注释/空行逐行相等）', _eq, _diff)
    ck('覆盖层一致性·zhTW 正文归一化行数 = 496（全文 498，含守卫 2 行）',
       len(_zhtw_body) == 496 and len(_zhtw_full) == 498,
       'body#%d full#%d' % (len(_zhtw_body), len(_zhtw_full)))
    # 判词前先对 zhTW / 源**两侧剥注释**（避免被注释“喂饱”而恒真 / 或造成假不等）。
    _ztw_code = '\n'.join(_split_code_comment(l)[0] for l in zhtw_lf.replace('\r\n', '\n').split('\n'))
    _src_code = '\n'.join(_split_code_comment(l)[0] for l in src_lf.replace('\r\n', '\n').split('\n'))
    _gone = ['小盾', 'MainAttribute', '主屬性', '主属性']
    _ghit = [w for w in _gone if w in _ztw_code]
    ck('覆盖层一致性·zhTW 正文不含已删维度/子类标记（小盾 / MainAttribute / 主屬性）',
       not _ghit, _ghit or 'clean')
    # 戰刃/長矛/釣魚竿：源 WeaponName 有意保留全表 → 繁化后必然落在 zhTW，且只应落在
    #   D.WeaponName 段内（各 1 次）。比较前**两侧都剥注释**——源第 83 行注释含「长矛」，
    #   不剥注释会得「源 2 次 vs 覆盖层 1 次」的假不等（原失败项的根因）。
    _kept = {'戰刃': '战刃', '長矛': '长矛', '釣魚竿': '钓鱼竿'}
    _kbad = [k for k, v in _kept.items()
             if _ztw_code.count(k) == 0 or _ztw_code.count(k) != _src_code.count(v)]
    ck('覆盖层一致性·戰刃/長矛/釣魚竿 各与源 WeaponName 次数一致（剥注释后，有意保留非残留）',
       not _kbad, _kbad or 'ok')

    def _wm_leak_of(s):
        _a = s.index('D.WeaponName')
        _b = s.index('}', _a)
        _out = s[:_a] + s[_b:]
        return [k for k in _kept if k in _out]

    _wm_a = _ztw_code.index('D.WeaponName')
    _wm_b = _ztw_code.index('}', _wm_a)
    _wm_seg = _ztw_code[_wm_a:_wm_b]
    ck('覆盖层一致性·戰刃/長矛/釣魚竿 仅出现在 D.WeaponName 段内（段外 0 命中）',
       (not _wm_leak_of(_ztw_code)) and all(k in _wm_seg for k in _kept),
       _wm_leak_of(_ztw_code) or 'ok')

    # 变异自检（Python 侧）：证明上述断言非恒真（仅内存改，不写盘）
    _mut = src_lf.replace('"板甲"', '"布甲"', 1)
    if _mut != src_lf:
        _mut_norm = _zhtw_norm([_G.convert_line(_split_code_comment(l)[0])[0]
                                for l in _mut.replace('\r\n', '\n').split('\n')])
        ck('变异自检·zhTW 一致性（源改一词→比对判不等，证明非恒真）',
           _mut_norm != _zhtw_body)
    else:
        ck('变异自检·zhTW 一致性（源改一词→比对判不等，证明非恒真）', False, '未找到替换锚点')
    ck('变异自检·zhTW 禁词（正文塞入「小盾」→变红，还原→绿，证明非恒真）',
       (not _ghit) and bool([w for w in _gone if w in (_ztw_code + '\nD.__x = "小盾"')]))
    ck('变异自检·戰刃/長矛/釣魚竿 仅段内（段外塞入「長矛」→变红，还原→绿，证明非恒真）',
       (not _wm_leak_of(_ztw_code)) and bool(_wm_leak_of(_ztw_code + '\nD.__y = "長矛"')))

    # ---- v4 静态契约：配置面板落位 / 互斥 / 控件 / 折叠 / 分组 ----
    ui_code = '\n'.join(l.split('--')[0] for l in ui_src.split('\n'))

    def _cfg_block(code):
        _a = code.index('function UI:EnsureConfig')
        return code[_a:code.index('UI.cfg = cfg', _a)]

    _cfg = _cfg_block(ui_code)
    ck('v4 落位·配置面板为右侧固定栏（SetWidth(220) + SetFrameLevel(512) + TOPLEFT host,TOPRIGHT 4,0）',
       'SetWidth(220)' in _cfg and 'SetFrameLevel(512)' in _cfg
       and 'SetPoint("TOPLEFT", host, "TOPRIGHT", 4, 0)' in _cfg)
    ck('v4 落位·配置面板不再是 560×400 居中可拖 DIALOG（无 SetSize(560 / SetMovable）',
       'SetSize(560' not in _cfg and 'SetMovable' not in _cfg)

    mf_src = open(os.path.join(ADDON, 'Core', 'MainFrame.lua'),
                  encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    _open_cfg = ui_code[ui_code.index('function UI:OpenConfig'):ui_code.index('function UI:CloseConfig')]
    ck('v4 互斥·MainFrame 暴露 ns.CloseSettings', 'ns.CloseSettings = function' in mf_src)
    ck('v4 互斥·OpenConfig 里收起设置弹窗（ns.CloseSettings()）', 'ns.CloseSettings(' in _open_cfg)
    ck('v4 互斥·MainFrame 开设置时收起过滤面板（settingsBtn 带 guard 调 CloseConfig）',
       'if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then ns.LootFilterUI:CloseConfig() end' in mf_src)
    ck('v4 互斥·MainFrame 主窗 OnShow 时也收起过滤面板',
       'if ns.LootFilterUI then ns.LootFilterUI:CloseConfig() end' in mf_src)
    ck('v4 控件·勾选走 iOS 开关 ns.hui.ReskinToggle（剥注释后代码命中）',
       'ns.hui.ReskinToggle' in ui_code)
    ck('v4 控件·旧勾选件彻底删除（MakeCheck / ChatConfigCheckButtonTemplate = 0）',
       'MakeCheck' not in ui_code and 'ChatConfigCheckButtonTemplate' not in ui_code)
    ck('v4 折叠·组头 arrow.tga + tooltip「点击折叠 / 展开该组」+ collapsed 表 + UI:LayoutConfig',
       'arrow.tga' in ui_code and '点击折叠 / 展开该组' in ui_code
       and 'collapsed' in ui_code and 'UI:LayoutConfig' in ui_code)
    ck('v4 折叠·展开态三角朝下（hdr.arrD:SetRotation(math.pi)）+ 折叠态换朝上图标 arrU',
       'hdr.arrD:SetRotation(math.pi)' in ui_code and 'hdr.arrU' in ui_code)
    _go = re.search(r'local GROUP_ORDER = \{(.*?)\n\}', ui_code, re.S)
    _go_block = _go.group(1) if _go else ''
    _groups = re.findall(r'^[ \t]*\{\s*"([A-Za-z]+)"\s*,\s*"', _go_block, re.M)
    ck('v4 分组·GROUP_ORDER 恰 4 组（Weapon/Armor/ShuXing/Other）',
       _groups == ['Weapon', 'Armor', 'ShuXing', 'Other'], _groups)
    ck('v4 分组·「其他」组映射真实维度 Class/BnetAccount/Tank',
       '{ "Class", "BnetAccount", "Tank" }' in _go_block)

    # 非恒真自检：逐条破坏→红 / 还原→绿（仅内存改文本，不写盘）
    def _flip_on(tag, base, mut, pred):
        _m = mut(base)
        ck('变异自检·%s（破坏→红，还原→绿）' % tag,
           (_m != base) and (not pred(_m)) and pred(base), 'red/green')

    def _flip(tag, mut, pred):
        _flip_on(tag, ui_code, mut, pred)

    def _groups_of(code):
        _m = re.search(r'local GROUP_ORDER = \{(.*?)\n\}', code, re.S)
        blk = _m.group(1) if _m else ''
        return re.findall(r'^[ \t]*\{\s*"([A-Za-z]+)"\s*,\s*"', blk, re.M)

    _flip('v4 落位 SetWidth(220)', lambda c: c.replace('SetWidth(220)', 'SetWidth(560)', 1),
          lambda c: 'SetWidth(220)' in _cfg_block(c))
    _flip('v4 落位 无 SetMovable', lambda c: c.replace(
        'popup:SetFrameLevel(512)',
        'popup:SetFrameLevel(512)\n    popup:SetMovable(true)', 1),
        lambda c: 'SetMovable' not in _cfg_block(c))
    _flip('v4 控件 ReskinToggle 在代码中', lambda c: c.replace('ReskinToggle', 'XskinToggle'),
          lambda c: 'ns.hui.ReskinToggle' in '\n'.join(l.split('--')[0] for l in c.split('\n')))
    _flip('v4 控件 无 MakeCheck', lambda c: c.replace(
        'tg.dim, tg.key = dim, k.key',
        'MakeCheck(content); tg.dim, tg.key = dim, k.key', 1),
        lambda c: 'MakeCheck' not in '\n'.join(l.split('--')[0] for l in c.split('\n')))
    _flip('v4 折叠 点击折叠 tooltip', lambda c: c.replace('点击折叠 / 展开该组', '点击', 1),
          lambda c: '点击折叠 / 展开该组' in c)
    _flip('v4 折叠 展开态三角朝下', lambda c: c.replace(
        'hdr.arrD:SetRotation(math.pi)', 'hdr.arrD:SetRotation(0)', 1),
        lambda c: 'hdr.arrD:SetRotation(math.pi)' in c)
    _flip('v4 分组 4 组', lambda c: c.replace('    { "ShuXing", "装备词缀" },\n', '', 1),
          lambda c: _groups_of(c) == ['Weapon', 'Armor', 'ShuXing', 'Other'])
    # 互斥双向（各自独立破坏）
    _flip('v4 互斥 OpenConfig 收设置', lambda c: c.replace(
        'if ns.CloseSettings then ns.CloseSettings() end', '-- MUT', 1),
        lambda c: 'ns.CloseSettings(' in c[c.index('function UI:OpenConfig'):c.index('function UI:CloseConfig')])
    _mf_code = '\n'.join(l.split('--')[0] for l in mf_src.split('\n'))
    _flip_on('v4 互斥 MainFrame 开设置收过滤面板', _mf_code, lambda c: c.replace(
        'if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then ns.LootFilterUI:CloseConfig() end',
        '-- MUT'),
        lambda c: ('if ns.LootFilterUI and ns.LootFilterUI.CloseConfig then '
                   'ns.LootFilterUI:CloseConfig() end') in c)

    # ---------------------------------------------------------------- G9 硬约束
    ui_txt = texts['Core/LootFilterUI.lua']
    sizes = set(re.findall(r'MakeFS\([^,]+,\s*(\d+)\s*,', ui_txt))
    sizes |= set(re.findall(r'Fnt\((\d+)\)', ui_txt))
    sizes |= set(re.findall(r'SetFont\([^,]+,\s*(\d+)\s*,', ui_txt))
    bad_sizes = sorted(s for s in sizes if s not in ('11', '14', '16'))
    ck('硬约束·LootFilterUI 字号只允许 11/14/16', not bad_sizes, sorted(sizes))
    # 宽度 >520 的框体不得用 edgeFile（剥离行注释后再查真正代码）
    ui_code = '\n'.join(l.split('--')[0] for l in ui_txt.split('\n'))
    ck('硬约束·v4 配置面板为右侧固定栏（SetWidth(220) 存在，560×400 居中弹窗已废除）',
       'SetWidth(220)' in ui_code and ':SetSize(560, 400)' not in ui_code)
    ck('硬约束·>520 框体不写 edgeFile（代码中零命中）',
       'edgeFile' not in ui_code, 'edgeFile' in ui_code)
    ck('硬约束·弹窗一律走 ns.hui.SkinPopup 蒙皮',
       ui_code.count('SkinPopup') >= 2, ui_code.count('SkinPopup'))
    # 行尾
    raw_dui = open(os.path.join(ADDON, 'Core', 'DungeonUI.lua'), 'rb').read()
    raw_mf = open(os.path.join(ADDON, 'Core', 'MainFrame.lua'), 'rb').read()
    ck('硬约束·DungeonUI.lua 保持 LF',
       raw_dui.count(b'\r') == 0 and raw_dui.count(b'\n') > 0)
    ck('硬约束·MainFrame.lua 保持 LF',
       raw_mf.count(b'\r') == 0 and raw_mf.count(b'\n') > 0)

    # ---------------------------------------------------------------- G10 全职业预设（T03）
    g10 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        -- 说明：ROGUE / MAGE / WARLOCK 在 BGL（BG.FilterClassItemInfo）里本身就各只有 1 套
        -- 「职业通用」预设（无专精级），BGL 全文条件分支从不为这 3 职业追加专精。
        -- 故本检查只要求每职业 ≥1 套，不按「专精级」判定，现状即达标。
        local classes = { "WARRIOR","PALADIN","DEATHKNIGHT","SHAMAN","HUNTER",
                          "ROGUE","DRUID","MONK","MAGE","WARLOCK","PRIEST" }
        local missing, perclass = {}, {}
        local total, badname, badicon, badweap, badarmor, badtank, badkey = 0, 0, 0, 0, 0, 0, 0
        for _, cls in ipairs(classes) do
            local raw = D.Presets[cls]
            if type(raw) ~= "table" or #raw == 0 then
                missing[#missing + 1] = cls
            else
                perclass[#perclass + 1] = cls .. "=" .. #raw
                for _, p in ipairs(raw) do
                    total = total + 1
                    if type(p.name) ~= "string" or p.name == "" then badname = badname + 1 end
                    local ic = p.icon
                    if type(ic) ~= "string" or ic:find("Interface\\Icons", 1, true) == nil then
                        badicon = badicon + 1
                    end
                    for _, nm in ipairs(p.useWeapon or {}) do
                        if D.WeaponIdByName[nm] == nil then badweap = badweap + 1 end
                    end
                    for _, nm in ipairs(p.useArmor or {}) do
                        if D.ArmorIdByName[nm] == nil then badarmor = badarmor + 1 end
                    end
                end
                -- 运行时转换：含坦克的预设必须键化（Tank[FLAG_TANK]==1 且无数组残留）
                local list = LF.LoadPresets(cls)
                for i, p in ipairs(raw) do
                    local wantTank = false
                    for _, nm in ipairs(p.Tank or {}) do
                        if nm == D.FLAG_TANK then wantTank = true end
                    end
                    if wantTank then
                        local s = list[i]
                        if not (s and s.Tank and s.Tank[D.FLAG_TANK] == 1)
                           or (s and s.Tank and rawget(s.Tank, 1) ~= nil) then
                            badtank = badtank + 1
                        end
                    end
                end
                -- 转换产物无 nil 键（防御：tostring(nil) 会变字符串 "nil" 键）
                for _, s in ipairs(list) do
                    for _, dim in ipairs(LF.DIMENSIONS) do
                        local t = s[dim]
                        if type(t) ~= "table" then
                            badkey = badkey + 1
                        else
                            for k in pairs(t) do
                                if type(k) ~= "string" or k == "nil" then badkey = badkey + 1 end
                            end
                        end
                    end
                end
            end
        end
        QA.ck("T03 · 11 职业全部有预设（≥1 套）", #missing == 0,
              "缺:" .. (#missing > 0 and table.concat(missing, ",") or "无")
              .. " 已有:" .. table.concat(perclass, " "))
        QA.ck("T03 · 预设名称全部非空", badname == 0, badname .. "/" .. total)
        QA.ck("T03 · 预设图标全为客户端自带(Interface\\Icons)", badicon == 0, badicon)
        QA.ck("T03 · useWeapon 名称全部可解析（数据完整性·需求式）", badweap == 0, badweap)
        QA.ck("T03 · useArmor 名称全部可解析（数据完整性·需求式）", badarmor == 0, badarmor)
        QA.ck("★ T03 · 所有含坦克预设：Tank[FLAG_TANK]==1 且无数组残留",
              badtank == 0, badtank)
        QA.ck("T03 · ConvertPreset 产物无 nil 类键（六维均为表、键均为字符串）",
              badkey == 0, badkey)
    end)''')
    parse(g10, 'G10 · 全职业预设（T03 覆盖）')

    # ---------------------------------------------------------------- G11 点名坦克专精
    # 设计验收：以下 5 个坦克专精预设必须默认勾选坦克维度（源里 Tank 数组 +
    # 转换后 Tank["过滤坦克"]==1）。G10 只校验「已声明 Tank 的预设」，
    # 若源里漏写 Tank（如 Tank={}），G10 不会报——故此处按名逐一点名。
    g11 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local tankSpecs = { "战士-防护", "圣骑士-防护", "死亡骑士-鲜血",
                            "武僧-酒仙", "德鲁伊-巨熊" }
        local found, hit = {}, {}
        for cls, raw in pairs(D.Presets) do
            if type(raw) == "table" then
                local list = LF.LoadPresets(cls)
                for i, p in ipairs(raw) do
                    for _, want in ipairs(tankSpecs) do
                        if p.name == want then
                            found[want] = true
                            if list[i] and list[i].Tank and list[i].Tank[D.FLAG_TANK] == 1 then
                                hit[want] = true
                            end
                        end
                    end
                end
            end
        end
        for _, want in ipairs(tankSpecs) do
            QA.ck("★ T03 · 坦克专精「" .. want .. "」Tank[FLAG_TANK]==1",
                  found[want] == true and hit[want] == true,
                  "存在=" .. tostring(found[want]) .. " 命中=" .. tostring(hit[want]))
        end
    end)''')
    parse(g11, 'G11 · 点名坦克专精（默认勾坦克）')

    # ---------------------------------------------------------------- G12 需求式语义专项
    # 本轮诉求①：勾选 = 我需要。逐维度覆盖「命中→不变灰 / 未命中→变灰 / 空集→不生效」
    # 及两条细分（披风恒不参与护甲维度、副手 subID==0 须 INVTYPE_HOLDABLE）、Nothave 排除词。
    g12 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local E = LF.Evaluate
        local function S(over)
            local s = { Name="t", Icon="i", Weapon={}, Armor={}, ShuXing={},
                        Class={}, BnetAccount={}, Tank={} }
            for k, v in pairs(over or {}) do s[k] = v end
            return s
        end
        -- ① 武器
        QA.ck("需求式·武器：需要集含该子类→不变灰",
              E(S{ Weapon={["7"]=1} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 7, "") == false)
        QA.ck("需求式·武器：需要集不含该子类→变灰",
              E(S{ Weapon={["7"]=1} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 8, "") == true)
        QA.ck("需求式·武器：集合为空→该维度不生效（恒不变灰）",
              E(S{ Weapon={} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 8, "") == false)
        -- ② 护甲
        QA.ck("需求式·护甲：需要集含该子类→不变灰",
              E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "") == false)
        QA.ck("需求式·护甲：需要集不含该子类→变灰",
              E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 2, "") == true)
        QA.ck("需求式·护甲：集合为空→该维度不生效（恒不变灰）",
              E(S{ Armor={} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 2, "") == false)
        QA.ck("需求式·披风：恒不参与护甲维度（子类不在需要集也放过）",
              E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_CLOAK", 2, "") == false)
        QA.ck("需求式·副手 subID=0 且 HOLDABLE 且不在需要集→变灰",
              E(S{ Armor={["6"]=1} }, D.CLASS_ARMOR, "INVTYPE_HOLDABLE", 0, "") == true)
        QA.ck("需求式·副手 subID=0 且 HOLDABLE 且在需要集→不变灰",
              E(S{ Armor={["0"]=1} }, D.CLASS_ARMOR, "INVTYPE_HOLDABLE", 0, "") == false)
        QA.ck("需求式·副手 subID=0 但非 HOLDABLE（盾）→不因此变灰",
              E(S{ Armor={["6"]=1} }, D.CLASS_ARMOR, "INVTYPE_SHIELD", 0, "") == false)
        -- ③ 词缀
        QA.ck("需求式·词缀：勾中的词命中任一→不变灰",
              E(S{ ShuXing={["力量"]=1, ["敏捷"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "+20 敏捷") == false)
        QA.ck("需求式·词缀：一个勾选词都没命中→变灰",
              E(S{ ShuXing={["力量"]=1, ["敏捷"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "+20 智力") == true)
        QA.ck("需求式·词缀：集合为空→该维度不生效（恒不变灰）",
              E(S{ ShuXing={} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "+20 智力") == false)
        -- Nothave 排除词：命中排除词则该词不算命中
        local oldNh = D.Nothave["力量"]
        D.Nothave["力量"] = { "不可用" }
        QA.ck("需求式·词缀 Nothave：命中排除词则该词不算命中→变灰",
              E(S{ ShuXing={["力量"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "+20 力量（不可用）") == true)
        D.Nothave["力量"] = nil
        QA.ck("需求式·词缀 对照：无排除词时同词命中→不变灰",
              E(S{ ShuXing={["力量"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 1, "+20 力量") == false)
        D.Nothave["力量"] = oldNh
    end)''')
    parse(g12, 'G12 · 需求式语义专项（武器/护甲/披风/副手/词缀/Nothave）')

    # ---------------------------------------------------------------- G13 方案删除 / 上限专项
    # 本轮诉求②：方案可删除。覆盖「删当前之前 → chooseID 前移」「删当前 → nil」
    # 「删最后一个」「删非法 idx 无副作用」「上限 6 AddScheme 返回 nil」「删后腾位可再加」。
    g13 = LE(lua, r'''return QA.run(function()
        local LF = TF_NS.LootFilter
        local function S(n) return { Name=n, Icon="i", Weapon={}, Armor={}, ShuXing={},
            Class={}, BnetAccount={}, Tank={} } end
        -- 删当前选中「之前」的方案 → chooseID 前移 1
        local st = QA.reset({ S("a"), S("b"), S("c"), S("d") }, 3)
        local n0 = #st
        LF.DeleteScheme(2)
        QA.ck("删除：DeleteScheme 后 #store 减 1", #st == n0 - 1, #st)
        QA.ck("删除当前选中之前 → chooseID 前移 1（3→2）", st.chooseID == 2, tostring(st.chooseID))
        QA.ck("删除后原 3 号方案前移到 2 位", st[2].Name == "c", st[2].Name)
        -- 删当前选中方案 → nil
        local st2 = QA.reset({ S("a"), S("b"), S("c") }, 2)
        LF.DeleteScheme(2)
        QA.ck("删除当前选中方案 → chooseID == nil", st2.chooseID == nil, tostring(st2.chooseID))
        QA.ck("删除当前选中方案 → #store 减 1", #st2 == 2, #st2)
        -- 删最后一个方案
        local st3 = QA.reset({ S("a"), S("b"), S("c") }, nil)
        LF.DeleteScheme(3)
        QA.ck("删除最后一个方案 → #store 减 1", #st3 == 2, #st3)
        QA.ck("删除最后一个方案 → 末元素为 b", st3[#st3].Name == "b", st3[#st3].Name)
        -- 删非法 idx 无副作用
        local st4 = QA.reset({ S("a"), S("b") }, 1)
        LF.DeleteScheme(99)
        QA.ck("删除非法 idx(99) 无副作用（#store/chooseID 不变）",
              #st4 == 2 and st4.chooseID == 1, #st4 .. "/" .. tostring(st4.chooseID))
        LF.DeleteScheme(0)
        QA.ck("删除非法 idx(0) 无副作用（#store/chooseID 不变）",
              #st4 == 2 and st4.chooseID == 1, #st4 .. "/" .. tostring(st4.chooseID))
        -- 上限 6：AddScheme 返回 nil
        local st5 = QA.reset({}, nil)
        local ids = {}
        for i = 1, 6 do ids[i] = LF.AddScheme("s" .. i, "Interface\\Icons\\INV_Sword_01") end
        QA.ck("上限 6 内 AddScheme 依次返回 1..6", ids[1] == 1 and ids[6] == 6,
              tostring(ids[1]) .. ".." .. tostring(ids[6]))
        local r = LF.AddScheme("s7", "Interface\\Icons\\INV_Axe_01")
        QA.ck("上限 6：AddScheme 返回 nil 且不写档", r == nil and #st5 == 6,
              tostring(r) .. "/" .. tostring(#st5))
        -- 删除腾位后又能新建
        LF.DeleteScheme(6)
        local r2 = LF.AddScheme("s7b", "Interface\\Icons\\INV_Axe_01")
        QA.ck("删除腾出名额 → AddScheme 又可成功（返回 6）", r2 == 6 and #st5 == 6, tostring(r2))
    end)''')
    parse(g13, 'G13 · 方案删除 / 上限专项')

    # ---------------------------------------------------------------- G14 管理入口可达（静态）
    section('G14 · 管理入口可达（静态源码）')
    lfui_src = open(os.path.join(ADDON, 'Core', 'LootFilterUI.lua'),
                    encoding='utf-8', errors='replace').read().replace('\r\n', '\n')
    lfui_code = '\n'.join(l.split('--')[0] for l in lfui_src.split('\n'))

    # (a) 菜单统一走 ns.hui.ShowMenu（LibUIDropDownMenu 已整体删除，不得残留旧宿主/EasyMenu）
    ck('入口(a)·菜单走 ns.hui.ShowMenu（LibUIDropDownMenu 已整体删除）',
       'ShowMenu' in lfui_code and 'Create_UIDropDownMenu' not in lfui_code
       and 'EasyMenu(' not in lfui_code)
    # (b) 配置面板方案图标注册右键（v4：锚点改为 `local cfg = {` → `UI.cfg = cfg`）
    mcfg = re.search(r'local cfg = \{(.*?)UI\.cfg = cfg', lfui_code, re.S)
    cfg_block = mcfg.group(1) if mcfg else ''
    ck('入口(b)·配置面板方案图标注册 RightButtonUp',
       'RegisterForClicks("LeftButtonUp", "RightButtonUp")' in cfg_block
       and 'SchemeActionMenu(self.scheme)' in cfg_block)
    # (c) 可点「方案设置」入口 + 未选方案分支提示（v4：reset 早于 schemeSet，锚到下个 `local scroll`）
    mset = re.search(r'local schemeSet = NewBtn\([^\n]*\n(.*?)local scroll', lfui_code, re.S)
    set_block = mset.group(1) if mset else ''
    ck('入口(c)·存在可点的「方案设置」按钮', 'NewBtn(popup, L["方案设置"]' in lfui_code)
    ck('入口(c)·方案设置分支：未选方案 → ConfigHint 提示',
       'ConfigHint' in set_block and '请先选择一个方案' in set_block
       and 'GetStore().chooseID' in set_block and 'SchemeActionMenu(id)' in set_block)

    # ---------------------------------------------------------------- G15 v3 语义专项
    g15 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local E = LF.Evaluate
        local function S(over)
            local s = { Name="t", Icon="i", Weapon={}, Armor={}, ShuXing={},
                        Class={}, BnetAccount={}, Tank={} }
            for k, v in pairs(over or {}) do s[k] = v end
            return s
        end
        -- ① key 空间守卫：未列入界面清单的子类永不参与判定（原 bug 的回归闸）
        QA.ck("v3·D.ArmorSet 不含子类 5（小盾/本客户端不存在）", D.ArmorSet[5] == nil,
              tostring(D.ArmorSet[5]))
        QA.ck("v3·未列入 ArmorSet 的子类 5 恒不因护甲维度变灰",
              E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_SHIELD", 5, "") == false)
        QA.ck("v3·对照：已列入 ArmorSet 的子类 2 不在需要集→变灰（守卫非恒真）",
              E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_CHEST", 2, "") == true)
        QA.ck("v3·D.WeaponSet 不含子类 17（长矛）", D.WeaponSet[17] == nil,
              tostring(D.WeaponSet[17]))
        QA.ck("v3·未列入 WeaponSet 的子类 17 恒不因武器维度变灰",
              E(S{ Weapon={["7"]=1} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 17, "") == false)
        QA.ck("v3·对照：已列入 WeaponSet 的子类 8 不在需要集→变灰（守卫非恒真）",
              E(S{ Weapon={["7"]=1} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 8, "") == true)
        -- ② 护甲/武器界面清单（v3 收紧）
        QA.ck("v3·D.ArmorName[5] == nil（小盾子类已删）", D.ArmorName[5] == nil,
              tostring(D.ArmorName[5]))
        local a, w = {}, {}
        for _, v in ipairs(D.ArmorOrder) do a[#a + 1] = tostring(v) end
        for _, v in ipairs(D.WeaponOrder) do w[#w + 1] = tostring(v) end
        QA.ck("v3·D.ArmorOrder = {0,1,2,3,4,6,7,8,9,10}（10 项）",
              table.concat(a, ",") == "0,1,2,3,4,6,7,8,9,10" and #D.ArmorOrder == 10,
              table.concat(a, ","))
        QA.ck("v3·D.WeaponOrder = {0,1,2,3,4,5,6,7,8,10,13,15,16,18,19}（15 项）",
              table.concat(w, ",") == "0,1,2,3,4,5,6,7,8,10,13,15,16,18,19" and #D.WeaponOrder == 15,
              table.concat(w, ","))
        -- ③ 无限服词缀表（本端 ver=16001 ⇒ IsForever）
        local nSX = 0
        for _ in pairs(D.ShuXing) do nSX = nSX + 1 end
        QA.ck("v3·无限服 D.ShuXing = 17 项", nSX == 17, nSX)
        QA.ck("v3·D.ShuXing 含 攻击强度/法术强度/移动速度",
              D.ShuXing["攻击强度"] ~= nil and D.ShuXing["法术强度"] ~= nil
              and D.ShuXing["移动速度"] ~= nil)
        -- ④ 全部预设的 useShuXing 名都能落到 D.ShuXing（0 悬空）
        local total, dangling = 0, 0
        for _, raw in pairs(D.Presets) do
            if type(raw) == "table" then
                for _, p in ipairs(raw) do
                    total = total + 1
                    for _, nm in ipairs(p.useShuXing or {}) do
                        if D.ShuXing[nm] == nil then dangling = dangling + 1 end
                    end
                end
            end
        end
        QA.ck("v3·预设总数 = 33 套", total == 33, total)
        QA.ck("v3·全部预设 useShuXing 词缀名 0 悬空（都落到 D.ShuXing）", dangling == 0, dangling)
        -- ⑤ 盗贼：唯一被改名的职业（潜行者→盗贼）+ 词缀含 力量/攻击强度
        local rogue = D.Presets["ROGUE"]
        QA.ck("v3·ROGUE 预设唯一且名为「盗贼」",
              type(rogue) == "table" and #rogue == 1 and rogue[1].name == "盗贼",
              type(rogue) == "table" and tostring(rogue[1] and rogue[1].name) or "nil")
        local rset = {}
        for _, nm in ipairs((rogue and rogue[1] and rogue[1].useShuXing) or {}) do rset[nm] = true end
        QA.ck("v3·盗贼 useShuXing 同时含「力量」与「攻击强度」",
              rset["力量"] == true and rset["攻击强度"] == true,
              "力量=" .. tostring(rset["力量"]) .. " 攻击强度=" .. tostring(rset["攻击强度"]))
    end)''')
    parse(g15, 'G15 · v3 语义专项（key 空间 / 词缀 / 预设 / 盗贼改名）')

    # ---------------------------------------------------------------- G16 变异自检
    # 对新增断言做「非恒真」校验：临时破坏相关常量/数据 → 断言必须变红 → 还原（仅内存，不写盘）。
    g16 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        local E = LF.Evaluate
        local function S(over)
            local s = { Name="t", Icon="i", Weapon={}, Armor={}, ShuXing={},
                        Class={}, BnetAccount={}, Tank={} }
            for k, v in pairs(over or {}) do s[k] = v end
            return s
        end
        local function trycheck(fn)
            local ok, r = pcall(fn)
            return ok and r or false
        end
        local function flip(tag, apply, revert, check)
            pcall(apply)
            local red = not trycheck(check)
            pcall(revert)
            local green = trycheck(check)
            QA.ck("变异自检·" .. tag .. "（破坏→红，还原→绿）", red and green,
                  "red=" .. tostring(red) .. " green=" .. tostring(green))
        end
        local WANT = "Weapon,Armor,ShuXing,Class,BnetAccount,Tank"
        flip("维度 = 六维", function() table.insert(LF.DIMENSIONS, "MainAttribute") end,
             function() table.remove(LF.DIMENSIONS) end,
             function() return table.concat(LF.DIMENSIONS, ",") == WANT and #LF.DIMENSIONS == 6 end)
        flip("D.MainAttr 已删", function() D.MainAttr = {} end, function() D.MainAttr = nil end,
             function() return D.MainAttr == nil and D.MainAttrOrder == nil end)
        flip("ArmorName[5] 已删", function() D.ArmorName[5] = "小盾" end,
             function() D.ArmorName[5] = nil end, function() return D.ArmorName[5] == nil end)
        flip("key 空间守卫·护甲(5)", function() D.ArmorSet[5] = true end,
             function() D.ArmorSet[5] = nil end,
             function() return E(S{ Armor={["1"]=1} }, D.CLASS_ARMOR, "INVTYPE_SHIELD", 5, "") == false end)
        flip("key 空间守卫·武器(17)", function() D.WeaponSet[17] = true end,
             function() D.WeaponSet[17] = nil end,
             function() return E(S{ Weapon={["7"]=1} }, D.CLASS_WEAPON, "INVTYPE_WEAPON", 17, "") == false end)
        local mv = D.ShuXing["移动速度"]
        flip("词缀含移动速度", function() D.ShuXing["移动速度"] = nil end,
             function() D.ShuXing["移动速度"] = mv end,
             function() return D.ShuXing["移动速度"] ~= nil end)
        local rp = D.Presets["ROGUE"][1]
        local rp_orig = rp.useShuXing
        flip("盗贼 useShuXing 含力量", function() rp.useShuXing = { "攻击强度" } end,
             function() rp.useShuXing = rp_orig end,
             function()
                 for _, nm in ipairs(rp.useShuXing or {}) do if nm == "力量" then return true end end
                 return false
             end)
        local mp = D.Presets["MAGE"][1]
        local mp_orig = mp.useShuXing
        flip("预设词缀 0 悬空", function() mp.useShuXing = { "__不存在词__" } end,
             function() mp.useShuXing = mp_orig end,
             function()
                 for _, raw in pairs(D.Presets) do
                     for _, p in ipairs(raw) do
                         for _, nm in ipairs(p.useShuXing or {}) do
                             if D.ShuXing[nm] == nil then return false end
                         end
                     end
                 end
                 return true
             end)
    end)''')
    parse(g16, 'G16 · 断言的变异自检（证明非恒真；仅内存破坏并还原）')

    # ---------------------------------------------------------------- G17 v4 数据层专项
    g17 = LE(lua, r'''return QA.run(function()
        local LF, D = TF_NS.LootFilter, TF_NS.LootFilterData
        QA.ck("v4·D.ShuXingLabel 存在且 特定法术强度→法术伤害",
              type(D.ShuXingLabel) == "table" and D.ShuXingLabel["特定法术强度"] == "法术伤害",
              tostring(D.ShuXingLabel and D.ShuXingLabel["特定法术强度"]))
        QA.ck("v4·D.FlagLabel 三条新文案（职业限定/保留战网/坦克装备）",
              D.FlagLabel[D.FLAG_CLASS] == "职业限定" and D.FlagLabel[D.FLAG_BNET] == "保留战网"
              and D.FlagLabel[D.FLAG_TANK] == "坦克装备",
              tostring(D.FlagLabel[D.FLAG_CLASS]) .. "/" .. tostring(D.FlagLabel[D.FLAG_BNET])
              .. "/" .. tostring(D.FlagLabel[D.FLAG_TANK]))
        local function lblOf(name)
            for _, k in ipairs(D.KeyList("ShuXing")) do
                if k.key == name then return k.label end
            end
            return nil
        end
        QA.ck("v4·KeyList(ShuXing)：特定法术强度 显示 label=法术伤害（仅显示名缩短）",
              lblOf("特定法术强度") == "法术伤害", tostring(lblOf("特定法术强度")))
        -- key 未改名：33 套预设 useShuXing ∩ D.ShuXing == 原名集合（0 悬空）
        local total, dangling = 0, 0
        for _, raw in pairs(D.Presets) do
            if type(raw) == "table" then
                for _, p in ipairs(raw) do
                    total = total + 1
                    for _, nm in ipairs(p.useShuXing or {}) do
                        if D.ShuXing[nm] == nil then dangling = dangling + 1 end
                    end
                end
            end
        end
        QA.ck("v4·33 套预设 useShuXing 全落到 D.ShuXing 键（0 悬空，key 未随 label 改名）",
              total == 33 and dangling == 0, total .. "/" .. dangling)
        -- 变异自检（证明非恒真；仅内存改并还原）
        local sl = D.ShuXingLabel["特定法术强度"]
        D.ShuXingLabel["特定法术强度"] = nil
        local redL = (lblOf("特定法术强度") ~= "法术伤害")
        D.ShuXingLabel["特定法术强度"] = sl
        QA.ck("变异自检·v4 ShuXingLabel（删映射→label 回原名，破坏→红 还原→绿）",
              redL and lblOf("特定法术强度") == "法术伤害")
        local fl = D.FlagLabel[D.FLAG_TANK]
        D.FlagLabel[D.FLAG_TANK] = "旧文案"
        local redF = (D.FlagLabel[D.FLAG_TANK] ~= "坦克装备")
        D.FlagLabel[D.FLAG_TANK] = fl
        QA.ck("变异自检·v4 FlagLabel（改文案→变红，还原→绿）",
              redF and D.FlagLabel[D.FLAG_TANK] == "坦克装备")
    end)''')
    parse(g17, 'G17 · v4 数据层专项（显示名映射 / 三条新文案 / 词缀键完整）')

    # ---------------------------------------------------------------- G18 v4 UI 运行时行为
    g18 = LE(lua, r'''return QA.run(function()
        local LF, D, UI = TF_NS.LootFilter, TF_NS.LootFilterData, TF_NS.LootFilterUI
        if TF_NS.hui then TF_NS.hui.ReskinToggle = TF_NS.hui.ReskinToggle or function() end end
        local okc = pcall(function() UI:EnsureConfig() end)
        QA.ck("v4·UI:EnsureConfig 可构建（不抛错）", okc and UI.cfg ~= nil,
              tostring(okc) .. "/" .. tostring(UI.cfg ~= nil))
        local cfg = UI.cfg
        if not cfg then return end
        local hdrs = 0
        for _ in pairs(cfg.headers) do hdrs = hdrs + 1 end
        QA.ck("v4·配置面板含 4 个组头，开关池与单元格一一对应",
              hdrs == 4 and #cfg.cells > 0 and #cfg.toggles == #cfg.cells,
              "headers=" .. hdrs .. " cells=" .. #cfg.cells .. " toggles=" .. #cfg.toggles)

        -- 折叠真的改变内容高度（wrap content:SetHeight 记录实参；桩 GetHeight 恒 100 不可用）
        local oSH = cfg.content.SetHeight
        local hrec = -1
        cfg.content.SetHeight = function(self, h) hrec = h; return oSH(self, h) end
        cfg.collapsed = {}
        UI:LayoutConfig()
        local hfull = hrec
        cfg.collapsed["Weapon"] = true
        UI:LayoutConfig()
        local hone = hrec
        for _, g in ipairs({ "Armor", "ShuXing", "Other" }) do cfg.collapsed[g] = true end
        UI:LayoutConfig()
        local hall = hrec
        cfg.content.SetHeight = oSH
        QA.ck("v4·折叠真的降低内容高度（LayoutConfig 非只换箭头）",
              hfull > hone and hone > hall, "full=" .. hfull .. " one=" .. hone .. " all=" .. hall)
        QA.ck("v4·全折叠后内容高度仍 >= 10（不为负 / 不塌成 0）", hall >= 10, hall)
        -- 折叠态下该组开关 Hide；还原后 Show
        cfg.collapsed = {}; cfg.collapsed["Weapon"] = true
        UI:LayoutConfig()
        local anyShown = false
        for _, cell in ipairs(cfg.cells) do
            if cell.group == "Weapon" and cell.tg:IsShown() then anyShown = true end
        end
        QA.ck("v4·折叠态：该组开关全部 Hide（收起后不可见）", not anyShown)
        cfg.collapsed = {}
        UI:LayoutConfig()
        local anyHidden = false
        for _, cell in ipairs(cfg.cells) do
            if cell.group == "Weapon" and not cell.tg:IsShown() then anyHidden = true end
        end
        QA.ck("v4·还原态：该组开关全部 Show", not anyHidden)

        -- v7：面板不再有遮罩（cfg.shield 不存在）→ 打开面板不会拦截主窗鼠标；收起只收面板
        local popup = cfg.popup
        QA.ck("v7·面板无遮罩（cfg.shield 不存在，主窗内容不被拦截）", cfg.shield == nil)
        UI:OpenConfig()
        QA.ck("v7·OpenConfig 后仍未造出遮罩（cfg.shield 仍为 nil）", cfg.shield == nil)
        QA.ck("v7·OpenConfig 后面板显示", popup:IsShown())
        UI:CloseConfig()
        QA.ck("v7·CloseConfig 只收面板（不依赖遮罩）", not popup:IsShown())

        -- v7（Edward 补验）：面板仍可正常开关、自身吞滚轮、且属主窗子级（不抢主窗鼠标的前提下仍可用）
        UI:OpenConfig(); UI:CloseConfig()          -- 先归零
        UI:ToggleConfig()
        local firstShown = popup:IsShown()
        UI:ToggleConfig()
        local secondShown = popup:IsShown()
        QA.ck("v7·ToggleConfig 第一次开 / 第二次关（面板仍可开关，不依赖遮罩）",
              firstShown and not secondShown,
              tostring(firstShown) .. "/" .. tostring(secondShown))
        local scr = rawget(popup, "__scripts")
        QA.ck("v7·面板自身吞滚轮（popup 挂 OnMouseWheel，滚轮不漏到背后副本列表）",
              scr ~= nil and scr["OnMouseWheel"] ~= nil)
        local par = popup:GetParent()
        local host = TF_NS.MainFrame or UIParent
        QA.ck("v7·面板父级 = 主窗（关主窗时随主窗消失，非孤儿悬浮窗）",
              par ~= nil and par == host,
              "hasParent=" .. tostring(par ~= nil) .. " isHost=" .. tostring(par == host))

        -- 互斥单向：OpenConfig 打开过滤面板时先收设置弹窗（ns.CloseSettings 被调用）
        local closeCalled = false
        local rawCS = TF_NS.CloseSettings
        TF_NS.CloseSettings = function() closeCalled = true; if rawCS then rawCS() end end
        local okO = pcall(function() UI:OpenConfig() end)
        TF_NS.CloseSettings = rawCS
        QA.ck("v4·OpenConfig 打开过滤面板时先收设置弹窗（ns.CloseSettings 被调用）",
              okO and closeCalled)
        UI:CloseConfig()

        -- 方案条分页：6 套 → 2 页；边界箭头 EnableMouse(false)；末页空位 Hide
        local S = {}
        for i = 1, 6 do
            S[i] = { Name = "s" .. i, Icon = "Interface\\Icons\\INV_Sword_01",
                     Weapon = {}, Armor = {}, ShuXing = {}, Class = {}, BnetAccount = {}, Tank = {} }
        end
        QA.reset(S, 5)
        local lrec, rrec
        local oLM, oRM = cfg.left.EnableMouse, cfg.right.EnableMouse
        cfg.left.EnableMouse = function(self, v) lrec = v; return oLM(self, v) end
        cfg.right.EnableMouse = function(self, v) rrec = v; return oRM(self, v) end
        cfg.page = 0; UI:RefreshConfig()
        QA.ck("v4·第 1 页 4 枚图标全 Show", cfg.icons[1]:IsShown() and cfg.icons[4]:IsShown())
        QA.ck("v4·边界：第 1 页左箭头 EnableMouse(false)、右箭头 true",
              lrec == false and rrec == true, tostring(lrec) .. "/" .. tostring(rrec))
        cfg.page = 1; UI:RefreshConfig()
        QA.ck("v4·末页仅 2 枚（6 套），第 3/4 空位 Hide（不残留上一页图标/选中框）",
              cfg.icons[1]:IsShown() and cfg.icons[2]:IsShown()
              and (not cfg.icons[3]:IsShown()) and (not cfg.icons[4]:IsShown()))
        QA.ck("v4·边界：末页右箭头 EnableMouse(false)、左箭头 true",
              rrec == false and lrec == true, tostring(lrec) .. "/" .. tostring(rrec))
        QA.ck("v4·CountPages(6 套) == 2", UI:CountPages() == 2, UI:CountPages())
        cfg.left.EnableMouse = oLM; cfg.right.EnableMouse = oRM
    end)''')
    parse(g18, 'G18 · v4/v7 UI 运行时行为（折叠重排 / 面板开关不抢鼠标 / 分页边界）')

    section('结论')
    print('通过 %d / 失败 %d' % (len(PASSED), len(FAILED)))
    for f in FAILED:
        print('  ✗ %s' % f)
    return 0 if not FAILED else 1


if __name__ == '__main__':
    sys.exit(main())

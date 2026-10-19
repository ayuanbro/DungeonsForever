# -*- coding: utf-8 -*-
"""
BGLite 无限模拟器 · 离线执行校验（dry-run harness）

思路：用 lupa 内嵌的真实 Lua 5.1（与 WoW 客户端同版本）加载插件的真实 Lua 文件，
配一套 WoW API 桩，把「加载 → 加满 9 职业 → 导出码往返 → 建界面 → 切页 → 点击 → 命令族」
整条链路实际跑一遍，捕捉任何 Lua 运行期错误。

用法：python tools/talentsim_dryrun.py
"""
import os
import sys

from lupa import lua51

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # _temp
ADDON = r"D:\Game\World of Warcraft\_classic_titan_\Interface\AddOns\TalentsForever"

FILES = [
    ("文案", "Locales/zhCN.lua"),
    ("基础层", "Core/Core.lua"),
    # 注意：Core/Hui.lua 与 Core/MainFrame.lua **不在**本清单里。
    # 本 harness 的 UI 层断言跑在「契约桩」(BG.hui.*) 之上，加载 Hui.lua 真身会把桩覆盖掉。
    # 这两份文件的加载期健壮性（含裸调用泰坦不存在的 API 这类崩溃）由 tf_load_check.py
    # 阶段一/阶段二用同一个 STUB 覆盖 —— 那里也是**故意不定义** IsAddOnLoaded 的地方。
    ("数据-天赋", "Core/Data/Data_Talents.lua"),
    ("数据-法术书", "Core/Data/Data_SpellBook.lua"),
    ("数据-种族传承", "Core/Data/Data_RacesLegacy.lua"),
    ("数据-专精梯队", "Core/Data/Data_SpecTier.lua"),
    ("逻辑层", "Core/Sim.lua"),
    ("传承逻辑", "Core/Legacy.lua"),
    ("组合表逻辑", "Core/ClassRace.lua"),
    ("界面层", "Core/UI.lua"),
]

STUB = r"""
-- ==================== WoW API 桩 ====================
-- GetFrameLevel 不在此表：它按真实累加值返回（见 NewObj / CreateFrame），
-- 否则「某个元素必须画在另一个之上」这类层级问题在桩里恒真，测不出来
local NUMERIC = { GetWidth=1, GetHeight=1, GetStringWidth=1, GetStringHeight=1,
                  GetVerticalScroll=1, GetScale=1, GetEffectiveScale=1,
                  GetNumTalents=1, GetID=1, GetNumRegions=1, GetMinMaxValues=1, GetFrameStrata=1,
                  -- GetAlpha 必须回数字：NineSlice:GetAlpha() 会被 `or 1` 兜底，回假对象会污染 nineAlpha
                  GetAlpha=1 }
local BOOLM   = { IsShown=1, IsVisible=1, IsMouseOver=1, IsEnabled=1, IsDragging=1 }
local STRM    = { GetText=1, GetName=1 }
-- 「取子对象 / 取自身」类 API 必须返回**调用者本身**（桩的兜底分支会现造 NewObj(tostring(k))，
-- 于是 s:GetThumbTexture() 拿到的是一张假 frame 而真身是 function => 后续
-- tinsert(f.__huiRepaints, fn) 变成 tinsert(function) 直接崩）。
-- 这些在任何真实帧上都是「返回自己或自己的一部分」，归到 SELF 表即与客户端同形。
-- ⚠️ GetParent 不在 SELF 里：它有真实语义（沿父链上爬，如 InFrameTree 的 `while f do`），
-- 返回 self 会死循环。见 NewObj 里的单独实现（读 __parent，根处回 nil）。
local SELF    = { GetThumbTexture=1, GetFontString=1, GetNormalTexture=1,
                  GetHighlightTexture=1, GetPushedTexture=1, GetDisabledTexture=1,
                  GetCheckedTexture=1, GetRegions=1, GetChildren=1 }
-- 数据字段白名单：真实帧上这些是「普通 nil / 普通数据」，桩的兜底分支却会把它们现造成
-- function —— 于是 `if bt.bg then bt.bg:SetColorTexture(...)` 索引 function 报错、
-- 存在性判断被骗过。只收**插件确实当数据/存在性读的帧字段名**，别多收：
-- 收进来的名字会被强制回 nil，若插件其实靠桩赋值（桩的 __newindex 是 rawset，正常不冲突），
-- 或断言借它取值，就会误伤。
local DATA_NIL = {
    bg = true,             -- LibHUI 按钮底纹贴图（插件走 if bt.bg then 判存在性）
    outlineFrame = true,   -- 职业按钮选中描边帧（UI 侧显式赋值，未建时须为 nil）
}

local ERRORS = {}
function Push(where, e) ERRORS[#ERRORS+1] = where .. " :: " .. tostring(e) end
function ERRORS_COUNT() return #ERRORS end
function ERRORS_LIST() return ERRORS end

-- 界面构建被 pcall 包住，错误只走 print；这里把关键字捞进 ERRORS，避免「跑过了但其实是崩的」
local RAWPRINT = print
function print(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[#parts+1] = tostring((select(i, ...))) end
    local s = table.concat(parts, " ")
    if s:find("构建出错") or s:find("bad argument") or s:find("attempt to ") then
        ERRORS[#ERRORS+1] = "界面层 :: " .. s
    end
    RAWPRINT(...)
end

-- 控件方法参数校验：颜色传错形态（如整表）在客户端会直接报错，这里同样报错
local function nums(where, ...)
    local n = select("#", ...)
    if n == 0 then error(where .. "：缺少参数", 3) end
    for i = 1, n do
        local v = select(i, ...)
        if type(v) ~= "number" then
            error(string.format("%s：参数 #%d 为 %s（应为 number）", where, i, type(v)), 3)
        end
    end
end
local function optnums(where, ...)
    if select("#", ...) > 0 then nums(where, ...) end
end
-- 参数个数校验：and/or 截断多返回值这类错误，只查类型是查不出来的
local function arity(where, lo, hi, ...)
    local n = select("#", ...)
    if n < lo or n > hi then
        error(string.format("%s：参数个数 %d（应为 %d~%d）", where, n, lo, hi), 3)
    end
end
local CHECKED = {
    SetTextColor           = function(...) arity("SetTextColor", 3, 4, ...) nums("SetTextColor", ...) end,
    SetVertexColor         = function(...) arity("SetVertexColor", 3, 4, ...) nums("SetVertexColor", ...) end,
    SetColorTexture        = function(...) arity("SetColorTexture", 3, 4, ...) nums("SetColorTexture", ...) end,
    SetBackdropColor       = function(...) arity("SetBackdropColor", 3, 4, ...) nums("SetBackdropColor", ...) end,
    SetBackdropBorderColor = function(...) arity("SetBackdropBorderColor", 3, 4, ...) nums("SetBackdropBorderColor", ...) end,
    SetAlpha               = function(...) arity("SetAlpha", 1, 1, ...) nums("SetAlpha", ...) end,
    -- 颜色/文字类参数个数也要查：函数调用非末位参数只取 1 个返回值（Unpack(x), 1 这类写法）
    AddLine                = function(...)
        local n = select("#", ...)
        if n ~= 1 and n ~= 4 and n ~= 5 then
            error(string.format("AddLine：参数个数 %d（应为 1 / 4 / 5）", n), 3)
        end
    end,
    SetSize                = function(w, h) nums("SetSize", w, h) end,
    SetWidth               = function(w) nums("SetWidth", w) end,
    SetHeight              = function(h) nums("SetHeight", h) end,
    SetJustifyH            = function(v) if type(v) ~= "string" then error("SetJustifyH：" .. type(v), 3) end end,
    -- 去饱和：实时天赋页「不能点的节点图标转灰」的唯一判据（桩不记录就永远测不出配色口径）
    SetDesaturated         = function(v) if type(v) ~= "boolean" then error("SetDesaturated：" .. type(v), 3) end end,
    SetPoint               = function(p) if type(p) ~= "string" then error("SetPoint：锚点为 " .. type(p), 3) end end,
    SetBackdrop            = function(t) if type(t) ~= "table" then error("SetBackdrop：" .. type(t), 3) end end,
    SetTexture             = function(t) if t ~= nil and type(t) ~= "string" and type(t) ~= "number" then error("SetTexture：" .. type(t), 3) end end,
    SetFont                = function(font, size)
        if type(font) ~= "string" then error("SetFont：字体为 " .. type(font), 3) end
        if type(size) ~= "number" then error("SetFont：字号为 " .. type(size), 3) end
    end,
    SetText = function(v)
        if v ~= nil and type(v) ~= "string" and type(v) ~= "number" then
            error("SetText：参数为 " .. type(v) .. "（应为 string）", 3)
        end
    end,
}

-- ⚠️ 客户端**不支持**的 widget 脚本名（模拟新端：无限服 1.60 / 11.0+ 的 TooltipDataHandler
-- 把 OnTooltipSetItem / OnTooltipSetSpell / OnTooltipSetUnit 全部移除——无限服源码里这三个名字
-- 零命中，替代机制是 TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, fn)）。
-- 桩的 HookScript 默认对任何脚本名都照单全收，会把「客户端不认这个脚本名」的差异彻底藏住：
-- 2026-09-18 实测 Hui.lua 裸写 tt:HookScript("OnTooltipSetItem", ...) 在无限服报
-- "bad argument #2 to '?'"，且发生在**加载期**（main chunk）→ 中断整个 chunk →
-- 后续文件（含 /tf 命令注册）全不加载 → 表现是「/tf 完全没反应 + 小地图图标不出现」，
-- 而当时离线 harness 与加载检查全绿。故这里显式表达真实差异：HasScript 回 false、HookScript 报错。
local UNSUPPORTED_SCRIPTS = {
    OnTooltipSetItem  = true,
    OnTooltipSetSpell = true,
    OnTooltipSetUnit  = true,
}

local function NewObj(name)
    -- 预置的数据字段：真实帧上这些是 nil 或真实对象，桩的兜底分支会把它们现造成 function
    -- （`if bt.bg then bt.bg:SetColorTexture(...)` 于是索引 function 报错）。
    -- 这里显式给成 nil 对应的真实形态（LibHUI 按钮的底纹贴图）。
    local o = setmetatable({ __name = name, __scripts = {}, __shown = true }, {
        __index = function(t, k)
            -- ⚠️ 插件自定义字段（__xxx，如 __huiRepaints / __roundPieces / __outlineFrame）
            -- ⚠️ 插件自定义字段（__xxx，如 __huiRepaints / __roundPieces）在真实帧上就是普通
            -- nil，**绝不能**现造 function：桩若现造并 rawset 缓存，
            -- `f.__huiRepaints = f.__huiRepaints or {}` 读到的第一个值就是 function
            -- （function 为真，or 兜不住）→ tinsert(function) 当场崩，
            -- 而这类崩溃只会在游戏里出现、离线 harness 反而看不出差别（2026-09-18 实测）。
            -- 客户端 API 名一律不含 "__" 前缀，按此区分是安全的。
            -- ⚠️ 这条只兜「原始表上还没有的键」：桩与 fixture 自己 rawset 过的 __xxx
            -- （BuildRoundBorder 打的 __huiBorderStrip、SetColorTexture 记的 __ct、
            -- SetSize 记的 __w …）走的是原始表、根本到不了这里，故不受影响。
            -- （__level 也在原始表上，供 GetFrameLevel 累加。）
            if type(k) == "string" and k:sub(1, 2) == "__" then return nil end
            -- 数据字段：按真实形态回 nil（见 DATA_NIL 说明）
            if DATA_NIL[k] then return nil end
            local f
            if k == "HasScript" then
                -- 真实帧上「这个 widget 支不支持该脚本」是可查的；新端 tooltip 类脚本已被移除
                f = function(self, ev) return not UNSUPPORTED_SCRIPTS[ev] end
            elseif k == "SetScript" or k == "HookScript" then
                f = function(self, ev, fn)
                    if UNSUPPORTED_SCRIPTS[ev] then
                        error(string.format(
                            "%s：客户端不支持脚本 '%s'（Usage: local success = self:HookScript(scriptTypeName, script [, bindingType])）",
                            k, tostring(ev)), 2)
                    end
                    t.__scripts = t.__scripts or {}; t.__scripts[ev] = fn; return fn
                end
            elseif k == "SetBackdropBorderColor" then
                -- 记录边框色：用于断言「节点视觉是否真的写下去了」
                f = function(self, ...) CHECKED.SetBackdropBorderColor(...); self.__border = { ... }; return self end
            elseif k == "SetColorTexture" then
                -- 记录纯色重染：节点 2px 外框用它着色
                f = function(self, ...) CHECKED.SetColorTexture(...); self.__ct = { ... }; return self end
            elseif k == "SetTexture" then
                -- 记录贴图路径：用于断言「法术书图标是否回退到问号」
                f = function(self, v) self.__tex = v; return self end
            elseif k == "SetText" then
                -- 记录文本：用于断言「右下角点数是否真的写下去了」
                f = function(self, v) CHECKED.SetText(v); self.__text = v; return self end
            elseif k == "SetTextColor" then
                -- 记录文字颜色：用于断言「职业按钮文字是否用了职业色」
                f = function(self, ...) CHECKED.SetTextColor(...); self.__textColor = { ... }; return self end
            elseif k == "SetDesaturated" then
                -- 记录去饱和状态：用于断言「实时天赋页不可点的节点图标是否转灰」
                f = function(self, v) CHECKED.SetDesaturated(v); self.__desaturated = v and true or false; return self end
            elseif k == "SetAtlas" then
                -- 记录 atlas 名：实时天赋页子树标题图标走这个 API
                -- （TraitSubTreeInfo.iconElementID 是 **atlas 字符串**，不是数字图标 ID；
                --   桩不记录的话，把它误当数字去 SetTexture 也照样全绿）。
                f = function(self, v) self.__atlas = v; return self end
            elseif k == "SetGradient" then
                -- 记录渐变参数（方向 + 两端颜色）。★ 注意：项目**已弃用** SetGradient
                -- （子树分隔线改用纯色分段，见 Core/UI.lua 的 PaintFade）——它的两端方向
                -- 在暴雪自己的代码里都自相矛盾。这条记录留着是为了「万一又用上」时能断言，
                -- 而不是在替它背书。
                f = function(self, o, c1, c2) self.__grad = { o, c1, c2 }; return self end
            elseif k == "SetVertexColor" then
                -- 记录染色参数：子树渐变分隔线（纯色分段，alpha 走三角形）的唯一判据。
                -- 不记的话「中间亮两端淡」调成「中间暗两端亮」也全绿。
                f = function(self, ...) CHECKED.SetVertexColor(...); self.__vc = { ... }; return self end
            elseif k == "CreateTexture" or k == "CreateFontString" then
                -- 记子件（真实帧有 GetRegions/GetChildren，桩原本两者都返回自身 → 等于断言不到
                -- 「插件在子帧上画了什么」）。子树标题的图标/树名/点数全挂在标题子帧上，
                -- 没有这层记录就只能断「标题帧存在」，断不到内容。
                f = function(self, ...)
                    local c = NewObj(tostring(k))
                    local list = rawget(self, "__children")
                    if list == nil then
                        list = {}
                        rawset(self, "__children", list)
                    end
                    list[#list + 1] = c
                    return c
                end
            elseif k == "SetPoint" then
                -- 记录最后一次锚点：用于断言「法术书两列的行列位置」
                f = function(self, ...) self.__pts = { ... }; return self end
            elseif k == "SetSize" then
                -- 记录尺寸：用于断言「卡片行的左右留白与卡片间距」（GetWidth 仍是 NUMERIC 的固定值）
                f = function(self, w, h) CHECKED.SetSize(w, h); self.__w, self.__h = w, h; return self end
            elseif k == "SetFont" then
                -- 记录字体三元组：MapUI 钉点名字「选中 16 / 未选 14」动态换字号，
                -- 插件代码走 GetFont() 取回 (path, size, flags) 再 SetFont ——
                -- 桩不记录的话 GetFont 会落到兜底现造 function、返回 table，SetFont 校验当场炸
                f = function(self, font, size, flags)
                    CHECKED.SetFont(font, size)
                    self.__font = { font, size, flags }
                    return self
                end
            elseif k == "GetFont" then
                f = function(self)
                    local rec = rawget(self, "__font")
                    if rec == nil then return "Fonts\\FRIZQT__.TTF", 12, "OUTLINE" end
                    return rec[1], rec[2], rec[3]
                end
            elseif CHECKED[k] then
                local chk = CHECKED[k]
                f = function(self, ...) chk(...) return self end
            elseif k == "Show" then f = function(self) self.__shown = true; return self end
            elseif k == "Hide" then f = function(self) self.__shown = false; return self end
            elseif k == "SetShown" then f = function(self, v) self.__shown = v and true or false; return self end
            elseif k == "IsShown" then f = function(self) return self.__shown end
            -- IsMouseOver 可由用例指定（bt.__mouseOver = true），默认 false；
            -- 用来区分「鼠标还停在节点上」与「鼠标已移开」两种刷新情形
            elseif k == "IsMouseOver" then f = function(self) return rawget(self, "__mouseOver") == true end
            -- rawget：桩的 __index 对未定义字段会现造 function，直接索引会把函数当帧级用
            elseif k == "GetFrameLevel" then f = function(self) return rawget(self, "__level") or 0 end
            elseif k == "SetFrameLevel" then f = function(self, v) self.__level = v; return self end
            -- GetParent 有真实语义：沿父链上爬（InFrameTree 的 `while f do f = f:GetParent()`、
            -- TooltipOwnerIsMine 的 `while f and f ~= UIParent`）。
            -- ⚠️ 必须**能在根处返回 nil**，否则父链无终点、两个循环直接死循环（实测挂死 180s+）。
            -- 客户端语义：UIParent 自身没有父 → nil；其余帧返回建帧时记下的 __parent（可能 nil）。
            elseif k == "GetParent" then
                f = function(self)
                    if self == UIParent then return nil end
                    return rawget(self, "__parent")
                end
            elseif NUMERIC[k] then f = function() return 100 end
            elseif BOOLM[k] then f = function() return false end
            elseif SELF[k] then f = function(self) return self end
            elseif k == "GetText" then f = function(self) return self.__text or "" end
            elseif STRM[k] then f = function() return "" end
            else f = function() return NewObj(tostring(k)) end end
            rawset(t, k, f)
            return f
        end,
        __newindex = function(t, k, v) rawset(t, k, v) end,
    })
    return o
end

-- 子帧默认帧级 = 父帧级 + 1（与客户端一致），供「谁画在谁上面」的断言使用
CreateFrame = function(_, _, parent)
    local o = NewObj("frame")
    o.__parent = parent
    o.__level = (parent and (rawget(parent, "__level") or 0) or 0) + 1
    return o
end
UIParent = NewObj("UIParent")
UIParent.__level = 1
GameTooltip = NewObj("GameTooltip")
-- 暴雪提示框的皮是 NineSlice 子帧（SharedTooltipTemplates.xml 里 parentKey="NineSlice"），
-- 插件换肤要读它的 alpha（NineSlice:GetAlpha()）。桩必须真给一个帧，否则兜底分支会现造
-- function，`tt.NineSlice:GetAlpha()` 变成索引 function 报错（2026-09-18 实测）。
GameTooltip.NineSlice = NewObj("NineSlice")
-- ItemRefTooltip 同样早于插件文件存在（暴雪帧），Hui.lua 建皮时会直接引用
ItemRefTooltip = NewObj("ItemRefTooltip")
ItemRefTooltip.NineSlice = NewObj("NineSlice")
-- ⚠️ 这里**故意不定义** IsAddOnLoaded：泰坦端没有这个全局（2026-09-18 实测 Hui.lua:1689
-- 裸调用 "attempt to call a nil value"，加载期中断整个 chunk）。桩若补上它就等于替插件
-- 兜了底，这类裸调用在离线 harness 里再也暴露不出来。见 tf_load_check.py 阶段一的自检。
-- 记录提示框行文本：用于断言「法术书行提示的是当前技能，而不是上次复用的旧技能」
TOOLTIP_LINES = {}
GameTooltip.AddLine = function(self, txt, ...) TOOLTIP_LINES[#TOOLTIP_LINES + 1] = txt end
-- 右侧列也要登记：节点提示框的「已投入 x / y」这类数值只有右列有，丢了就断言不到范围外刷新
GameTooltip.AddDoubleLine = function(self, a, b, ...)
    TOOLTIP_LINES[#TOOLTIP_LINES + 1] = a
    TOOLTIP_LINES[#TOOLTIP_LINES + 1] = b
end
GameTooltip.ClearLines = function(self) for i = #TOOLTIP_LINES, 1, -1 do TOOLTIP_LINES[i] = nil end end
BiaoGeTooltip = NewObj("tt")
StaticPopupDialogs = {}
StaticPopup_Show = function(name) __lastPopup = name end
SlashCmdList = {}
IsShiftKeyDown = function() return false end
-- CreateColor 是正式/经典各端都有的全局（ColorMixin），实时天赋页的渐变线要用它。
-- ⚠️ 桩里漏了它的话，UI 侧 `if tex.SetGradient and _G.CreateColor` 这层守卫直接短路 →
-- 渐变分支**离线零覆盖**（退化成 SetVertexColor 也不报错）。所以必须给。
-- 只给最小形态：记录四通道 + GetRGBA（插件的唯一用法是把它整个传给 SetGradient）。
CreateColor = function(r, g, b, a)
    local c = { r = r, g = g, b = b, a = a }
    c.GetRGBA = function(self) return self.r, self.g, self.b, self.a end
    return c
end
-- 泰坦客户端只认自己 Spell 表里的法术。数据里的 ID 现已按客户端 DB2 校订过
-- （见 TalentsForever/Core/Data/Data_SpellBook.lua 与 _temp/verify_spellbook_ids.py），
-- 正常情况下客户端都认。下面这批「客户端不认识」的号**只存在于夹具里**（数据中已不再使用），
-- 目的是继续压测「ID 这层走不通 → 按名/数据内同名/宠物条/法术书 逐层兜底」这条链，
-- 免得数据一修好、兜底链就失去覆盖。
local UNKNOWN_SPELL_IDS = {
    [402927] = true, [25980] = true, [15629] = true, [14272] = true, [409526] = true,
    [408343] = true, [437009] = true, [15107] = true, [8166] = true, [704] = true,
    [2970] = true, [460698] = true, [437138] = true,
    -- 34428 = 乘胜追击在数据里的**真实** id（客户端本来是认的）。这里故意标成不认识，
    -- 好让解析链走过「数据内同名 id」这层之后落到最后一道「角色法术书」上，保住那层的用例。
    [34428] = true,
}
local function ClientKnowsSpell(id)
    id = tonumber(id)
    return id ~= nil and not UNKNOWN_SPELL_IDS[id]
end

-- 名称侧同理（泰坦端实测）：客户端按名反查大面积失效——连「反击风暴」这种客户端明明
-- 认识的法术（数据里 id=20230，渲染正常）也按名查不到。这里挑几个名字专门验证
-- 「按名查不到时，能不能靠数据内同名条目的 ID 兜底」。
local UNKNOWN_SPELL_NAMES = {
    ["反击风暴"] = true, ["血性狂暴"] = true, ["防御姿态"] = true, ["乘胜追击"] = true,
    -- ③ 数据内同名贴图层的样本：数据里「先祖的召唤」自带 icon 路径（无 id），
    --    客户端按名不认 → 只能靠「数据内同名条目的贴图路径」这条取到。
    ["先祖的召唤"] = true,
    -- ⑥ 宠物条层的样本：宠物姿态在客户端没有法术行，按名按号都查不到（2026-09-16
    --    游戏内 /tf spellicons 实测 12 条名ID/名贴图全「无」），贴图只有宠物条知道。
    --    留两个给「数据内同名贴图/同名 ID」层，其余全走宠物条层。
    ["攻击型"] = true, ["防御型"] = true, ["被动型"] = true,
    ["跟随"] = true, ["移动到"] = true,
    -- 「停留」= Stay 的游戏内本地化名（数据条目已按游戏名改），客户端也不认这个名
    ["停留"] = true,
    -- 全路走不通的样本：数据里完全不存在这个名字，客户端按名也不认。
    -- 用来验证「七条兜底路全失败时 SpellIcon 返回 nil，界面据此回退问号」这条契约。
    -- （原样本「还击」已在数据修正中补上素材路径，不再经过兜底链，故换成这个虚构名。）
    ["不存在的技能"] = true,
}
local function ClientKnowsName(nm)
    return type(nm) == "string" and nm ~= "" and not UNKNOWN_SPELL_NAMES[nm]
end

GetSpellTexture = function(id)
    if not ClientKnowsSpell(id) then return nil end
    return "Interface\\Icons\\Spell_Nature_Lightning"
end
-- 名称反查：模拟客户端只有一半法术能按名查到 ID（另一半必须走 GetSpellInfo(name) 取图标），
-- 另有一批名字（UNKNOWN_SPELL_NAMES）按名怎么都查不到，与泰坦端实测一致
GetSpellLink = function(name)
    if not ClientKnowsName(name) then return nil end
    if #(tostring(name)) % 2 == 0 then return nil end
    return "|cff71d5ff|Hspell:12345|h[" .. tostring(name) .. "]|h|r"
end
-- 传 ID 与传名字的返回位置不同（ID：castTime 在第 4 位；名字：cost 第 4、castTime 第 7）
GetSpellInfo = function(idOrName)
    if tonumber(idOrName) then
        if not ClientKnowsSpell(idOrName) then return nil end
        return "法术", "", "Interface\\Icons\\Spell_Nature_Lightning", 2500, 0, 0, tonumber(idOrName)
    end
    if not ClientKnowsName(idOrName) then return nil end
    return tostring(idOrName), "", "Interface\\Icons\\Spell_Nature_Lightning", 120, false, 0, 2500, 0, 0
end
GetSpellCooldown = function(id) return 0, 300, 1 end
-- 现代客户端 C_Spell：按标识符（英文名可跨语言）反查法术 ID；按 ID 取 iconID（数字）
C_Spell = {
    GetSpellIDForSpellIdentifier = function(ident)
        if not ClientKnowsName(ident) then return nil end
        return 70000 + (#ident % 5000)
    end,
    GetSpellInfo = function(id)
        if not ClientKnowsSpell(id) then return nil end
        return { iconID = 80000 + (tonumber(id) or 0) % 5000, name = "spell" }
    end,
    -- 按名调这个接口在桩里恒失败（只认数字 ID）；GetSpellInfo(name) 仍会返回贴图，
    -- 所以「按名兜底」在测试里算作一族（按名反查 ID + 按名取贴图），反向验证时整族一起关
    GetSpellTexture = function(id)
        if not ClientKnowsSpell(id) then return nil end
        return "Interface\\Icons\\Spell_Nature_Lightning"
    end,
    -- 法术描述直取（DungeonsForever 技能行第 2 行 = 客户端描述正文，2026-09-30 v3）：
    -- 真客户端按 id 返回说明正文（可含 |c 颜色码）；不认识 → nil。插件侧优先于提示框抓取。
    GetSpellDescription = function(id)
        if not ClientKnowsSpell(id) then return nil end
        return "桩法术描述 " .. tostring(id)
    end,
}
GetSpellPowerCost = function(id) return { { cost = 120, name = "法力值", type = 0 } } end
-- 法术提示框抓取桩（DungeonsForever 地图页技能行第 2 行 = 客户端提示正文，2026-09-30）：
-- SetSpellByID 后按暴雪惯例暴露全局 GameTooltipTextLeft1..N（Left1=名字、Left2=正文），插件按 _G 读。
-- 正文按 id 拼进桩文本：断言既能证明「走了提示框抓取」，又能证明「抓的是当前这条 id」。
GameTooltip.SetSpellByID = function(self, id)
    self:ClearLines()
    if type(id) ~= "number" or not ClientKnowsSpell(id) then
      -- 客户端不认识：行要**置空**（真客户端的行字体串常驻，ClearLines 只清文本不清行 ——
      -- 桩同样留行给空文本，防上一轮法术的正文残留串味）
      self.__tipID = nil
      _G.GameTooltipTextLeft1 = { GetText = function() return "" end }
      _G.GameTooltipTextLeft2 = { GetText = function() return "" end }
      return
    end
    self.__tipID = id
    _G.GameTooltipTextLeft1 = { GetText = function() return "法术" end }
    _G.GameTooltipTextLeft2 = { GetText = function() return "桩法术提示正文 " .. id end }
end
GameTooltip.NumLines = function(self) return self.__tipID and 2 or 0 end
-- 角色法术书（桩）：数据 ID 客户端不认（402927）、按名又查不到的技能（乘胜追击），
-- 只要角色学会了，法术书里就能直接拿到贴图 —— 这是最后一道兜底，这里放一条模拟它可用。
C_SpellBook = {
    GetNumSpellBookSkillLines = function() return 1 end,
    GetSpellBookSkillLineInfo = function(i)
        if i == 1 then return { offset = 0, numSpellBookItems = 1, name = "武器" } end
        return nil
    end,
    GetSpellBookItemName = function(slot) if slot == 1 then return "乘胜追击" end return nil end,
    GetSpellBookItemTexture = function(slot)
        if slot == 1 then return "Interface\\Icons\\Ability_Warrior_VictoryRush" end
        return nil
    end,
}
Enum = { SpellBookSpellBank = { Player = 0 }, TooltipDataType = { Item = 0, Spell = 1, Unit = 2 } }
-- 新端 tooltip 数据回调机制（无限服 1.60 / 11.0+）：替代被移除的 OnTooltipSetItem 等 widget script。
-- 注册进来的回调记在 TOOLTIP_POSTCALLS 上，供加载期契约检查断言「撤皮走了哪条路」。
TOOLTIP_POSTCALLS = {}
TooltipDataProcessor = {
    AllTypes = "ALL",
    AddTooltipPostCall = function(tooltipType, fn)
        TOOLTIP_POSTCALLS[#TOOLTIP_POSTCALLS + 1] = { type = tooltipType, fn = fn }
    end,
}
-- 宠物条（桩）：宠物命令/姿态在客户端没有对应法术行，贴图只有宠物条自己知道。
-- 形态按 2026-09-16 游戏内 /dump GetPetActionInfo(1) 实测：返回 (名, 贴图, isToken, ...)，
-- 命令/姿态类 isToken=1，前两位是**全局常量名**，要 _G[令牌] 解析成真正的本地化名与贴图路径。
NUM_PET_ACTION_SLOTS = 10
local PET_ACTION_STUB = {
    [1] = { "PET_ACTION_ATTACK",  "PET_ATTACK_TEXTURE",  true },
    [2] = { "PET_ACTION_FOLLOW",  "PET_FOLLOW_TEXTURE",  true },
    [3] = { "PET_ACTION_STAY",    "PET_STAY_TEXTURE",    true },
    [4] = { "PET_ACTION_MOVETO",  "PET_MOVETO_TEXTURE",  true },
    [5] = { "PET_ACTION_ASSIST",  "PET_ASSIST_TEXTURE",  true },
    [6] = { "PET_ACTION_DEFEND",  "PET_DEFEND_TEXTURE",  true },
    [7] = { "PET_ACTION_PASSIVE", "PET_PASSIVE_TEXTURE", true },
    -- 宠物技能（如猎人宠物的主动技）isToken=false，直接给本地化名与贴图
    [8] = { "爪击", "Interface\\Icons\\Ability_Druid_Rake", false },
}
for tok, loc in pairs({
    PET_ACTION_ATTACK = "攻击", PET_ACTION_FOLLOW = "跟随", PET_ACTION_STAY = "停留",
    PET_ACTION_MOVETO = "移动到", PET_ACTION_ASSIST = "攻击型", PET_ACTION_DEFEND = "防御型",
    PET_ACTION_PASSIVE = "被动型",
}) do _G[tok] = loc end
for tok, tex in pairs({
    PET_ATTACK_TEXTURE = "Interface\\PetBar\\Pet_Attack",
    PET_FOLLOW_TEXTURE = "Interface\\PetBar\\Pet_Follow",
    PET_STAY_TEXTURE = "Interface\\PetBar\\Pet_Stay",
    PET_MOVETO_TEXTURE = "Interface\\PetBar\\Pet_Moveto",
    PET_ASSIST_TEXTURE = "Interface\\PetBar\\Pet_Assist",
    PET_DEFEND_TEXTURE = "Interface\\PetBar\\Pet_Defend",
    PET_PASSIVE_TEXTURE = "Interface\\PetBar\\Pet_Passive",
}) do _G[tok] = tex end
GetPetActionInfo = function(i)
    local e = PET_ACTION_STUB[i]
    if e then return e[1], e[2], e[3] end
    return nil
end
GetLocale = function() return "zhCN" end
GetBuildInfo = function() return 1, "x", 3, 120005 end
GetTime = function() return 0 end
BIAOGE_TEXT_FONT = "Fonts\\ARKai_T.ttf"
YES, NO = "是", "否"
wipe = function(t) for i = #t, 1, -1 do t[i] = nil end return t end
tinsert = table.insert
format = string.format
strjoin = function(sep, ...) return table.concat({...}, sep) end
strtrim = function(s) return (tostring(s):gsub("^%s+", ""):gsub("%s+$", "")) end
floor, ceil, max, min, abs = math.floor, math.ceil, math.max, math.min, math.abs
strsplit = function(sep, s) local o = {} for w in string.gmatch(s, "([^" .. sep .. "]*)") do o[#o+1] = w end return unpack(o) end
-- t==0 immediate (same contract as df_dungeon_check stub: pump self-continues sync offline)
C_Timer = { NewTicker = function() return {} end, After = function(t, fn) if t == 0 then fn() end end }
UnitClass = function() return "战士", "WARRIOR", 1 end
GetNumTalents = function() return 0 end
debugstack = function() return "stack" end
C_SpecializationInfo = nil -- 默认不可用（模拟真实对比功能取不到数据的分支）

-- 建下拉框：必须**忠实复刻** LibUIDropDownMenu:create_DropDownMenu 的子件布局。
-- 真实库里它会给 f 挂这些子件，而 Hui.lua 的 SkinDropDown 会逐个读来换肤/隐藏：
--   f.Left / f.Middle / f.Right  三段底图（ARTWORK 贴图，原生「角色创建」风）
--   f.Text                       文字（ARTWORK FontString，被重锚 + 换字体换色）
--   f.Icon                       图标（OVERLAY 贴图，默认 Hide）
--   f.Button                     箭头按钮（含 Normal/Pushed/Disabled/Highlight 四贴图）
-- ⚠️ 若这里只回一个裸帧，`dd.Left` / `dd.Text` 会落到 NewObj 的兜底分支 —— 该分支
-- **rawset 一个 function 进对象**，于是 `if tex then tex:Hide() end` 变成「索引 function」
-- 当场报 `attempt to index local 'tex' (a function value)`（Hui.lua:1911 / 1956，2026-09-18 实测）。
-- 这是桩不忠实导致的假报错，不是插件 bug —— 修桩，不要改插件。
-- （`dd.Button` 在真库由 CreateFrame 建，不是本插件给 dd 挂数据字段，故不触 DATA_NIL。）
local function MakeDropDown()
    local f = CreateFrame("Frame")
    f.Left   = f:CreateTexture(nil, "ARTWORK")
    f.Middle = f:CreateTexture(nil, "ARTWORK")
    f.Right  = f:CreateTexture(nil, "ARTWORK")
    f.Text   = f:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
    f.Icon   = f:CreateTexture(nil, "OVERLAY")
    f.Button = CreateFrame("Button", nil, f)
    f.Button.NormalTexture    = f.Button:CreateTexture(nil)
    f.Button.PushedTexture    = f.Button:CreateTexture(nil)
    f.Button.DisabledTexture  = f.Button:CreateTexture(nil)
    f.Button.HighlightTexture = f.Button:CreateTexture(nil)
    return f
end

LibStub = {
    GetLibrary = function(self, name)
        return {
            Create_UIDropDownMenu = MakeDropDown,
            UIDropDownMenu_Initialize = function() end,
            UIDropDownMenu_CreateInfo = function() return {} end,
            UIDropDownMenu_AddButton = function() end,
            UIDropDownMenu_SetWidth = function() end,
            UIDropDownMenu_SetText = function() end,
            UIDropDownMenu_SetAnchor = function() end,
            ToggleDropDownMenu = function() end,
        }
    end,
}
function GetBuildInfo() return "1", "1", "1", 38002 end
SOUNDKIT = { IG_MAINMENU_OPTION_CHECKBOX_ON = 856 }
function PlaySound() end
function hooksecurefunc() end
UISpecialFrames = {}
function GetLocale() return "zhCN" end

BG = {
    IsTitan = true,
    __inits = {},
    huiTheme = "hui",
    hui = {
        ACCENT = {0x46/255, 0xbf/255, 0x72/255},
        FontFlags = function() return "" end,
        AddRepaint = function() end,
        -- 圆角描边桩：与真实实现同形。**顺序必须与真实 BuildRoundBorder 一致**：
        -- 直边条先入表（1~4，带 __huiBorderStrip），四角弧块后入表（5~8）。
        -- 顺序反了会让 pieces[1] 从「直边条」变成「弧角」，
        -- 于是 PaintChipPieces 走 SetVertexColor 而不是 SetColorTexture，
        -- 「描边件颜色」类断言全部恒假（2026-09-18 实测，改 __ 字段守卫后才暴露）。
        BuildRoundBorder = function(f, r, color, owner, layer, rounding, thickness)
            local p = owner or f
            local pieces, covers = {}, {}
            for i = 1, 8 do
                local t = p:CreateTexture(nil, layer or "BORDER")
                t:SetTexture("Interface/AddOns/BGLite/Media/LibHUI/HUIRoundCorner")
                if i <= 4 then t.__huiBorderStrip = true end
                pieces[i] = t
            end
            return pieces, covers
        end,
        RegisterMainAlphaSurface = function() end,
        IsMainUIFrame = function() return false end,
        -- 大卡圆角背景桩：填充角块 + 直边条；withBorder 时另建描边件（MakePageCard 不取返回值）
        BuildRoundedBG = function(f, cr, color, rounding, withBorder, borderThickness)
            local pieces = {}
            for i = 1, 4 do pieces[i] = f:CreateTexture(nil, "BACKGROUND") end
            local border = {}
            if withBorder then
                for i = 1, 8 do border[i] = f:CreateTexture(nil, "BORDER") end
            end
            return pieces, border
        end,
        layer = {
            L0={0.086,0.086,0.086,0.95}, L1={0.169,0.169,0.169,0.95},
            L2={0.212,0.212,0.212,1},    L3={0.251,0.251,0.251,0.95},
            L4={0.290,0.290,0.290,0.95}, L5={0.329,0.329,0.329,0.95},
        },
        CreateSegmentedControl = function(host)
            local c = { buttons = {}, offsets = {} }
            function c:AttachButtons(bts)
                self.list = bts
                local acc = 0
                for _, b in ipairs(bts) do self.offsets[b] = acc; acc = acc + b:GetWidth() end
            end
            function c:SetSelected(bt, animate) self.sel = bt; self.animated = animate end
            function c:ClearSelection() self.sel = nil end
            return c
        end,
    },
    PlaySound = function() end,
    dropDownToggle = function() end,
    CreateButton = function() return NewObj("button") end,
    Init = function(fn) BG.__inits = BG.__inits or {}; BG.__inits[#BG.__inits+1] = fn end,
    MainFrame = NewObj("mainframe"),
    PersonalAssistantMainFrameTabNum = 108,
    ClickTabButton = function() end,
    SelectAssistantSubTab = function() end,
}
BG.TalentSimFrame = NewObj("talentsimframe")

ns = {
    L = setmetatable({}, { __index = function(_, k) return tostring(k) end }),
    LibBG = {
        -- 与 LibStub 侧同款：必须带 Left/Middle/Right/Button（见 MakeDropDown 注释）
        Create_UIDropDownMenu = MakeDropDown,
        UIDropDownMenu_SetWidth = function() end,
        UIDropDownMenu_SetAnchor = function() end,
        UIDropDownMenu_Initialize = function() end,
        UIDropDownMenu_CreateInfo = function() return {} end,
        UIDropDownMenu_AddButton = function() end,
        UIDropDownMenu_SetText = function() end,
        CloseDropDownMenus = function() end,
    },
}
BiaoGe = {}
TalentsForeverDB = {}

BG.hui.SkinButton = function() end
BG.hui.RoundIcon = function(t) t.__round = true end  -- 打标记供断言「图标是否做了圆角」
BG.hui.SetEditBorder = function() end
BG.hui.SkinPopup = function() end
BG.hui.CreateSegmentedControl = function()
    return {
        AttachButtons = function() end,
        SetSelected = function() end,
    }
end

function LoadFile(path, tag)
    local f = io.open(path, "r")
    if not f then error("无法打开 " .. path) end
    local src = f:read("*a")
    f:close()
    local chunk, err = loadstring(src, "@" .. path)
    if not chunk then error(tag .. " 编译失败: " .. tostring(err)) end
    local ok, e = pcall(chunk, "TalentsForever", BG)
    if not ok then error(tag .. " 加载期报错: " .. tostring(e) .. "\n" .. debug.traceback("", 2)) end
    return true
end

local PASS, FAIL = 0, 0
function Check(name, cond, extra)
    if cond then
        PASS = PASS + 1
    else
        FAIL = FAIL + 1
        print(string.format("  [失败] %s%s", name, extra and ("  -> " .. tostring(extra)) or ""))
    end
end
function Try(name, fn, ...)
    local ok, e = pcall(fn, ...)
    if not ok then Check(name, false, e) return false end
    PASS = PASS + 1
    return true
end
function Summary()
    print(string.format("\n断言：通过 %d / 失败 %d", PASS, FAIL))
    if #ERRORS > 0 then
        print(string.format("运行期错误 %d 条：", #ERRORS))
        for i = 1, math.min(#ERRORS, 15) do print("    " .. ERRORS[i]) end
    else
        print("运行期错误 0 条")
    end
    return FAIL == 0 and #ERRORS == 0
end
"""

TEST = r"""
local TS = BG.TalentSim
local U  = BG.TalentSimUI
local ORDER = TS.CLASS_ORDER

print("---------- 一、数据 ----------")
local n_cls, n_tal, n_rem = 0, 0, 0
local n_spell = 0
for _, key in ipairs(ORDER) do
    local c = BG.TalentSimData.classes[key]
    n_cls = n_cls + 1
    for _, tree in ipairs(c.trees) do
        n_tal = n_tal + #tree.talents
        n_rem = n_rem + #tree.removed
    end
    local sb = BG.SpellBookData.classes[key]
    for _, tab in ipairs(sb.tabs) do n_spell = n_spell + #tab.spells end
    n_spell = n_spell + #sb.general
end
print(string.format("  职业 %d / 天赋 %d / 已移除 %d / 法术书条目 %d", n_cls, n_tal, n_rem, n_spell))
Check("职业数 = 9", n_cls == 9, n_cls)
Check("天赋数 = 470", n_tal == 470, n_tal)
Check("已移除条目存在", n_rem > 0, n_rem)
Check("法术书条目 = 403", n_spell == 403, n_spell)

-- 每个节点的描述条数必须等于 max；行列在 1..7 / 1..4
local bad_desc, bad_geo = 0, 0
for _, key in ipairs(ORDER) do
    for _, tree in ipairs(BG.TalentSimData.classes[key].trees) do
        for _, t in ipairs(tree.talents) do
            if #t.desc ~= t.max then bad_desc = bad_desc + 1 end
            if t.row < 1 or t.row > 7 or t.col < 1 or t.col > 4 then bad_geo = bad_geo + 1 end
            if not t.icon or t.icon == "" then bad_geo = bad_geo + 1 end
        end
    end
end
Check("全部节点 desc 条数 == max", bad_desc == 0, bad_desc)
Check("全部节点行列/图标合法", bad_geo == 0, bad_geo)

-- 客户端缺贴图排查：数据里不得再出现 classic_ 前缀名，替代表必须已生效
local dead, fixed = 0, 0
local FIXED_ICONS = {
    spell_holy_sealofprotection = true, ability_hunter_rapidkilling = true,
    spell_nature_spiritwolf = true, ability_dualwield = true,
    spell_shadow_charm = true, spell_fire_volcano = true,
    spell_nature_healingwavelesser = true, ability_warlock_fireandbrimstone = true,
}
local present = {}
local DEADNAMES = {
    classic_spell_holy_blessingofprotection = true, ability_hunter_focusfire = true,
    classic_ability_druid_demoralizingroar = true, ability_rogue_restlessblades = true,
    ability_rogue_dirtydeeds = true, classic_spell_fire_elementaldevastation = true,
    classic_spell_nature_healingway = true, ability_warlock_baneofhavoc = true,
}
for _, key in ipairs(ORDER) do
    for _, tree in ipairs(BG.TalentSimData.classes[key].trees) do
        for _, t in ipairs(tree.talents) do
            if DEADNAMES[t.icon] then dead = dead + 1 end
            if FIXED_ICONS[t.icon] then present[t.icon] = true end
        end
    end
end
for _ in pairs(present) do fixed = fixed + 1 end
Check("无缺失贴图名残留", dead == 0, dead)
Check("8 个替代图标全部落到数据里", fixed == 8, fixed)
for _, key in ipairs(ORDER) do
    for _, tree in ipairs(BG.TalentSimData.classes[key].trees) do
        if tree.icon and tree.icon:sub(1, 8) == "classic_" then dead = dead + 1 end
    end
end
Check("天赋树图标无 classic_ 前缀", dead == 0, dead)

print("\n---------- 二、逻辑层 ----------")
TS.Init(TS)
Check("默认职业 = 战士", TS.GetClassKey(TS) == "WARRIOR", TS.GetClassKey(TS))
Check("默认等级 60", TS.GetLevel(TS) == 60, TS.GetLevel(TS))
Check("点数池 51", TS.GetPool(TS) == 51, TS.GetPool(TS))

-- 层级解锁
TS.ResetAll(TS)
TS.Add(TS, 1, 1, 3)
Check("第 1 行可加点", TS.GetTreeSpent(TS, 1) == 3, TS.GetTreeSpent(TS, 1))
local row2
for i, t in ipairs(TS.GetTrees(TS)[1].talents) do if t.row == 2 then row2 = i break end end
local r = TS.Add(TS, 1, row2, 1)
Check("本系仅 3 点：第 2 行仍锁定", r == false, tostring(r))
TS.Add(TS, 1, 2, 2)
Check("本系 5 点后第 2 行解锁", TS.GateReason(TS, 1, row2) == nil, TS.GateReason(TS, 1, row2))

-- 前置天赋需点满
local pi, preq
for i, t in ipairs(TS.GetTrees(TS)[1].talents) do
    if t.req then pi, preq = i, t.req break end
end
Check("武器树存在前置天赋", pi ~= nil)
if pi then
    TS.ResetAll(TS)
    local target = TS.GetTalent(TS, 1, pi)
    local need = (target.row - 1) * 5
    local ranks = TS.GetRanks(TS)
    -- 在目标行之上直接铺满 need 点（绕过层级门，单独验证前置规则）
    local left = need
    for i, t in ipairs(TS.GetTrees(TS)[1].talents) do
        if left <= 0 then break end
        if t.row < target.row then
            local add = math.min(left, t.max)
            ranks[1][i] = add
            left = left - add
        end
    end
    Check("层级门已铺满", TS.PtsAbove(TS, 1, target.row) >= need, TS.PtsAbove(TS, 1, target.row))
    local pmax = TS.GetTalent(TS, 1, preq).max
    ranks[1][preq] = 0
    Check("前置 0 点时目标锁定", TS.GateReason(TS, 1, pi) ~= nil, TS.GateReason(TS, 1, pi))
    ranks[1][preq] = pmax - 1
    Check("前置差 1 级仍锁定（须点满而非 ≥1 点）", TS.GateReason(TS, 1, pi) ~= nil, TS.GateReason(TS, 1, pi))
    ranks[1][preq] = pmax
    Check("前置点满后放行", TS.GateReason(TS, 1, pi) == nil, TS.GateReason(TS, 1, pi))
    TS.ResetAll(TS)
end

-- 超投回收
TS.ResetAll(TS)
TS.AddMax(TS, 1, 1)
Check("点满后本系 3 点", TS.GetTreeSpent(TS, 1) == 3, TS.GetTreeSpent(TS, 1))
TS.SetLevel(TS, 10)
Check("降到 10 级池 = 1", TS.GetPool(TS) == 1, TS.GetPool(TS))
Check("超投被回收", TS.GetTotalSpent(TS) <= 1, TS.GetTotalSpent(TS))
TS.SetLevel(TS, 60)

-- 导出码
TS.ResetAll(TS)
TS.AddMax(TS, 1, 1)
local code = TS.Encode(TS, true)
print("  导出码样例: " .. code)
Check("导出码含 / 与 -", code:find("/") ~= nil and code:find("-") ~= nil, code)
TS.ResetAll(TS)
local ok, err = TS.Decode(TS, code)
Check("导出码可导入", ok == true, err)
Check("导入后还原 3 点", TS.GetTreeSpent(TS, 1) == 3, TS.GetTreeSpent(TS, 1))
ok = TS.Decode(TS, "garbage")
Check("非法码被拒", ok == false)
ok = TS.Decode(TS, "#warrior/60/000-000-000")
Check("网页格式（带 #）可导入", ok == true)
ok = TS.Decode(TS, "druid/60/1-2-3")
Check("其他职业码可导入", ok == true and TS.GetClassKey(TS) == "DRUID", TS.GetClassKey(TS))

-- 方案
TS.SetClass(TS, "WARRIOR")
TS.SetLevel(TS, 60)
TS.ResetAll(TS)
TS.AddMax(TS, 1, 1)
ok, err = TS.SaveBuild(TS, "测试方案")
Check("保存方案", ok == true, err)
Check("方案列表 1 条", #TS.GetBuilds(TS) == 1, #TS.GetBuilds(TS))
TS.ResetAll(TS)
ok, err = TS.LoadBuild(TS, 1)
Check("载入方案", ok == true, err)
Check("载入后还原 3 点", TS.GetTreeSpent(TS, 1) == 3, TS.GetTreeSpent(TS, 1))
Check("空名保存被拒", TS.SaveBuild(TS, "  ") == false)

-- 对比功能：C_SpecializationInfo 不可用时返回 nil
Check("对比功能不可用时返回 nil", TS.CompareWithPlayer(TS) == nil)

print("\n---------- 三、全职业加满 + 导出码往返 ----------")
for _, key in ipairs(ORDER) do
    Try("职业 " .. key .. " 切职业", TS.SetClass, TS, key)
    local trees = TS.GetTrees(TS)
    Check("职业 " .. key .. " 三棵树", #trees == 3, #trees)
    -- 反复加满（多轮以覆盖前置链逐步解锁的顺序）
    for round = 1, 4 do
        for ti = 1, #trees do
            for i = 1, #trees[ti].talents do
                TS.AddMax(TS, ti, i)
            end
        end
    end
    Check("职业 " .. key .. " 点数不超池", TS.GetTotalSpent(TS) <= TS.GetPool(TS),
        TS.GetTotalSpent(TS) .. "/" .. TS.GetPool(TS))
    local c = TS.Encode(TS, true)
    TS.ResetAll(TS)
    local okk, e = TS.Decode(TS, c)
    Check("职业 " .. key .. " 导出码往返", okk == true, e)
    -- 逐树重置不报错
    for ti = 1, 3 do TS.ResetTree(TS, ti) end
    Check("职业 " .. key .. " 重置后归零", TS.GetTotalSpent(TS) == 0, TS.GetTotalSpent(TS))
end

-- 全部 470 节点状态合法
local bad_state = 0
for _, key in ipairs(ORDER) do
    TS.SetClass(TS, key)
    for ti = 1, 3 do
        for i = 1, #TS.GetTrees(TS)[ti].talents do
            local st = TS.GetStatus(TS, ti, i)
            if st ~= "avail" and st ~= "locked" and st ~= "partial" and st ~= "maxed" then
                bad_state = bad_state + 1
            end
        end
    end
end
Check("470 节点状态取值合法", bad_state == 0, bad_state)

print("\n---------- 四、界面层 ----------")
local inits = BG.__inits or {}
Check("界面注册了 BG.Init 回调", #inits >= 1, #inits)
for i = 1, #inits do
    Try("BG.Init 回调 " .. i, inits[i])
end

local frame = BG.TalentSimFrame
local onshow = frame.__scripts and frame.__scripts.OnShow
Check("子页 OnShow 已绑定", onshow ~= nil)
if onshow then
    Try("OnShow → Build", onshow, frame)
end
Check("界面已构建", U.built == true)

-- 节点视觉必须真正落位（回归：构建路径里若被 U.built 门控吞掉，
-- 图标会停在默认白框 / 无点数 / 无压暗，表现就是「图标全是亮的」）
do
    local n11 = U.nodes[1] and U.nodes[1][1]
    Check("节点已创建（视觉断言前置）", n11 ~= nil)
    if n11 then
        Check("节点外框为 4 条", n11.bars ~= nil and #n11.bars == 4, n11.bars and #n11.bars)
        Check("节点外框已着色", n11.bars and n11.bars[1].__ct ~= nil, n11.bars and n11.bars[1].__ct)
        Check("节点右下角点数已写入", type(n11.rk.__text) == "string" and n11.rk.__text:match("^%d+/%d+$") ~= nil, n11.rk.__text)
    end
    local missing = 0
    for ti = 1, 3 do
        for i = 1, #(U.nodes[ti] or {}) do
            local n = U.nodes[ti][i]
            if not (n.bars and n.bars[1].__ct) then missing = missing + 1 end
            if n.rk.__text == nil then missing = missing + 1 end
        end
    end
    Check("全部节点均有边框色与点数", missing == 0, missing)

    -- 状态配色语义：可加点(含已投未满)=绿 / 已满=金 / 未解锁=压暗
    TS.ResetAll(TS)
    U.UpdateAll(U)
    local availNoGreen, lockedNoDim = 0, 0
    for ti = 1, 3 do
        for i = 1, #(U.nodes[ti] or {}) do
            local n = U.nodes[ti][i]
            local st = TS.GetStatus(TS, ti, i)
            local c = n.bars and n.bars[1].__ct
            if st == "avail" and c and not (c[1] < 0.5 and c[2] > 0.6) then availNoGreen = availNoGreen + 1 end
            if st == "locked" and n.lock.__shown ~= true then lockedNoDim = lockedNoDim + 1 end
        end
    end
    Check("可加点节点为绿色外框", availNoGreen == 0, availNoGreen)
    Check("锁定节点已压暗", lockedNoDim == 0, lockedNoDim)

    TS.AddMax(TS, 1, 1)
    U.UpdateAll(U)
    local maxedNoGold, partialNoGreen = 0, 0
    for ti = 1, 3 do
        for i = 1, #(U.nodes[ti] or {}) do
            local n = U.nodes[ti][i]
            local st = TS.GetStatus(TS, ti, i)
            local c = n.bars and n.bars[1].__ct
            if c then
                if st == "maxed" and not (c[1] > 0.8 and c[2] > 0.6 and c[3] < 0.4) then maxedNoGold = maxedNoGold + 1 end
                if st == "partial" and not (c[1] < 0.5 and c[2] > 0.6) then partialNoGreen = partialNoGreen + 1 end
            end
        end
    end
    Check("已满节点为金色外框", maxedNoGold == 0, maxedNoGold)
    Check("已投未满节点为绿色外框", partialNoGreen == 0, partialNoGreen)

    -- 分享码刷新排在节点循环之后：节点异常不得把它整段吞掉（曾表现为分享码框空白）
    Check("刷新后分享码已写入", U.codeEdit ~= nil and type(U.codeEdit.__text) == "string" and #U.codeEdit.__text > 0,
        U.codeEdit and U.codeEdit.__text)
    TS.ResetAll(TS)
    U.UpdateAll(U)
end

-- 9 职业 UI 刷新
for _, key in ipairs(ORDER) do
    TS.SetClass(TS, key)
    Try("职业 " .. key .. " 重建树", U.RebuildTrees, U)
    Try("职业 " .. key .. " 刷新", U.UpdateAll, U)
end
Check("9 职业 UI 刷新无异常", true)
Check("战士节点数量正确（17+18+19=54）", (function()
    TS.SetClass(TS, "WARRIOR")
    U.RebuildTrees(U)
    local n = 0
    for ti = 1, 3 do n = n + #(U.nodes[ti] or {}) end
    return n == 54
end)())

-- 子页往返
for _, sub in ipairs({ "SpellBook", "Talents", "SpellBook", "Talents" }) do
    Try("切换子页 " .. sub, U.SwitchSub, U, sub)
end
Check("子页往返无异常", true)

-- 两页互斥显示：只 Show 自身不 Hide 对侧，会让先构建的法术书整层压在天赋页上
-- （spellPage 建在 talentPage 之后，层级更高）

-- 场景（冷缓存、首次法术书解析）：模拟泰坦前夕客户端——GetSpellLink / GetSpellInfo
-- 按名查询失效（返回 nil），只有 C_Spell 能按英文名反查 ID。验证新图标逻辑能救场，不回退问号。
do
    local oldLink, oldInfo = GetSpellLink, GetSpellInfo
    GetSpellLink = function() return nil end
    GetSpellInfo = function(id)
        if tonumber(id) then
            return "法术", "", "Interface\\Icons\\Spell_Nature_Lightning", 2500, 0, 0, tonumber(id)
        end
        return nil  -- 按名查询在泰坦失效
    end
    TS.SetClass(TS, "WARRIOR")
    U.SwitchSub(U, "SpellBook")
    local qm2, ic2 = 0, 0
    for i = 1, #U.spellRows do
        local r = U.spellRows[i]
        if r.__shown ~= false and r.icon then
            ic2 = ic2 + 1
            if r.icon.__tex == "Interface\\Icons\\INV_Misc_QuestionMark" then qm2 = qm2 + 1 end
        end
    end
    Check("泰坦按名查失效时 C_Spell 救场：图标无问号", ic2 > 0 and qm2 == 0, ic2 .. " 个图标 / " .. qm2 .. " 个问号")
    GetSpellLink, GetSpellInfo = oldLink, oldInfo  -- 还原，后续测试用正常桩
end

U.SwitchSub(U, "SpellBook")
Check("法术书页：spellPage 已显示", U.spellPage.__shown == true)
Check("法术书页：talentPage 已隐藏", U.talentPage.__shown == false)
U.SwitchSub(U, "Talents")
Check("天赋页：talentPage 已显示", U.talentPage.__shown == true)
Check("天赋页：spellPage 已隐藏", U.spellPage.__shown == false)

-- 种族页：互斥显示 + 列表与详情
U.SwitchSub(U, "Races")
Check("种族页已显示", U.racePage.__shown == true)
Check("种族页：talentPage 已隐藏", U.talentPage.__shown == false)
Check("种族页：spellPage 已隐藏", U.spellPage.__shown == false)
Check("种族页：legacyPage 已隐藏", U.legacyPage.__shown == false)
Check("种族页：tierPage 已隐藏", U.tierPage.__shown == false)
Try("种族页刷新", U.UpdateRaces, U)
Check("种族标题含阵营", U.raceTitle.__text == "部落种族" or U.raceTitle.__text == "联盟种族", U.raceTitle.__text)
local raceRow1 = U.raceRows[1]
Check("种族技能行已创建", raceRow1 ~= nil)
if raceRow1 then
    Check("种族技能行有名称", type(raceRow1.name.__text) == "string" and raceRow1.name.__text ~= "", raceRow1.name.__text)
    Check("种族技能行有描述", type(raceRow1.desc.__text) == "string" and raceRow1.desc.__text ~= "", raceRow1.desc.__text)
    -- 行图标与天赋模拟器页节点同尺寸（观感一致，改一处不得只改另一处）
    local nodeBtR = U.nodes[1] and U.nodes[1][1] and U.nodes[1][1].bt
    Check("种族技能行图标尺寸与天赋页一致",
        raceRow1.iconHolder and nodeBtR and raceRow1.iconHolder.__w == nodeBtR.__w and raceRow1.iconHolder.__h == nodeBtR.__h,
        tostring(raceRow1.iconHolder and raceRow1.iconHolder.__w) .. "/" .. tostring(nodeBtR and nodeBtR.__w))
    Check("种族技能行图标走主题圆角", raceRow1.icon.__round == true, tostring(raceRow1.icon.__round))
    local fn = raceRow1.__scripts and raceRow1.__scripts.OnEnter
    Try("种族技能行 tooltip", fn, raceRow1)
end
local rb2 = U.raceBtns[2]
if rb2 and rb2.__scripts and rb2.__scripts.OnClick then Try("点击第二个种族", rb2.__scripts.OnClick, rb2) end
Check("种族选择已更新", U.raceIdx == 2, U.raceIdx)

-- 职业专属种族技能：仅牧师有数据，亡灵（部落第 2 个）
TS.SetClass(TS, "PRIEST")
U.raceIdx = 2
U.UpdateRaces(U)
local nHdrP = 0
for _, h in ipairs(U.raceHeaders) do if h.__shown then nHdrP = nHdrP + 1 end end
Check("牧师专属种族技能标题出现", nHdrP == 1, nHdrP)
TS.SetClass(TS, "WARRIOR")
U.UpdateRaces(U)
local nHdrW = 0
for _, h in ipairs(U.raceHeaders) do if h.__shown then nHdrW = nHdrW + 1 end end
Check("战士无专属种族技能标题", nHdrW == 0, nHdrW)

-- 阵营切换：索引复位 + 标题刷新
local facBtn = U.factionBtns and U.factionBtns["Alliance"]
if facBtn and facBtn.__scripts and facBtn.__scripts.OnClick then Try("切到联盟", facBtn.__scripts.OnClick, facBtn) end
Check("联盟侧标题刷新", U.raceTitle.__text == "联盟种族", U.raceTitle.__text)
Check("联盟种族索引复位 1", U.raceIdx == 1, U.raceIdx)

-- 职业 × 种族组合总表：数据侧结构 / 星标集合 / 阵营限定 / 界面互斥与跳转
local CR = BG.ClassRace
Check("组合表逻辑层已注册", CR ~= nil)
if CR then
    local crCols, crRows = CR:GetColumns(), CR:GetRows()
    local tidList = {}
    for i, c in ipairs(crCols) do tidList[i] = c.tid end
    Check("组合表：9 列（天裔两条记录合并为一列）", #crCols == 9, #crCols)
    Check("组合表：列序与参考表一致",
        table.concat(tidList, "/") == "HUMAN/DWARF/NIGHTELF/GNOME/ORC/UNDEAD/TAUREN/TROLL/SKYBORNE",
        table.concat(tidList, "/"))
    Check("组合表：9 行且与职业按钮同序",
        #crRows == 9 and crRows[1].key == "WARRIOR" and crRows[9].key == "DRUID", #crRows .. " 行")
    Check("组合表：人类=仅联盟 / 兽人=仅部落 / 天裔=跨阵营",
        crCols[1].faction == "Alliance" and crCols[5].faction == "Horde" and crCols[9].faction == nil,
        tostring(crCols[1].faction) .. "/" .. tostring(crCols[5].faction) .. "/" .. tostring(crCols[9].faction))

    -- 星标逐格核对：参考表为 6 个普通种族新增 + 天裔全部 6 个 = 12
    local WANT = {}
    for _, k in ipairs({ "HUNTER_HUMAN", "MAGE_ORC", "PALADIN_UNDEAD", "PRIEST_GNOME",
                         "SHAMAN_DWARF", "WARLOCK_TROLL", "WARRIOR_SKYBORNE", "HUNTER_SKYBORNE",
                         "MAGE_SKYBORNE", "ROGUE_SKYBORNE", "DRUID_SKYBORNE", "SHAMAN_SKYBORNE" }) do
        WANT[k] = true
    end
    local gotKeys, nNew = {}, 0
    for _, row in ipairs(crRows) do
        for _, col in ipairs(crCols) do
            if CR:GetCell(row.key, col.tid).state == CR.STATE_NEW then
                nNew = nNew + 1
                gotKeys[row.key .. "_" .. col.tid] = true
            end
        end
    end
    local nExtra, nMiss = 0, 0
    for k in pairs(gotKeys) do if not WANT[k] then nExtra = nExtra + 1; print("组合表：多余星标 " .. k) end end
    for k in pairs(WANT) do if not gotKeys[k] then nMiss = nMiss + 1; print("组合表：缺失星标 " .. k) end end
    Check("组合表：星标恰为 12 个且与参考表逐格一致",
        nNew == 12 and nExtra == 0 and nMiss == 0, nNew .. " 个（多 " .. nExtra .. " 缺 " .. nMiss .. "）")

    local stat = CR:GetStats()
    -- 52 = 经典旧世已有 40 + 永恒新增 12。classic 表共 41 条，其中「亡灵猎人」永恒数据里没有，
    -- 该格按不可选留空（不计入统计），故可见的经典旧世格子为 40。
    Check("组合表：可选 52 格 = 经典旧世 40 + 永恒新增 12",
        stat.cells == 52 and stat.classic == 40 and stat.new == 12,
        stat.cells .. " / " .. stat.classic .. " / " .. stat.new)

    -- 负例与经典旧世基线
    Check("组合表：人类不可选德鲁伊", CR:GetCell("DRUID", "HUMAN").state == CR.STATE_NONE)
    Check("组合表：牛头人不可选圣骑士", CR:GetCell("PALADIN", "TAUREN").state == CR.STATE_NONE)
    Check("组合表：牛头人不可选盗贼", CR:GetCell("ROGUE", "TAUREN").state == CR.STATE_NONE)
    Check("组合表：亡灵不可选德鲁伊", CR:GetCell("DRUID", "UNDEAD").state == CR.STATE_NONE)
    -- 经典旧世有、永恒数据里没有的组合：按不可选留空，不得误判成「新增」
    Check("组合表：亡灵猎人（经典旧世有、永恒无）按不可选处理",
        CR:GetCell("HUNTER", "UNDEAD").state == CR.STATE_NONE, CR:GetCell("HUNTER", "UNDEAD").state)
    Check("组合表：暗夜精灵德鲁伊为经典旧世已有", CR:GetCell("DRUID", "NIGHTELF").state == CR.STATE_CLASSIC)
    Check("组合表：人类战士为经典旧世已有", CR:GetCell("WARRIOR", "HUMAN").state == CR.STATE_CLASSIC)

    -- 阵营限定：只有跨阵营列的单边职业会命中
    local lim = CR:GetFactionLimits()
    Check("组合表：阵营限定恰为天裔萨满（部落）+ 天裔法师（联盟）2 条",
        #lim == 2 and lim[1].classKey == "SHAMAN" and lim[1].faction == "Horde"
        and lim[2].classKey == "MAGE" and lim[2].faction == "Alliance", #lim .. " 条")
    Check("组合表：跨阵营列的双边职业不标阵营限定，单边职业标",
        CR:GetCell("WARRIOR", "SKYBORNE").limited == false
        and CR:GetCell("MAGE", "SKYBORNE").limited == true
        and CR:GetCell("MAGE", "SKYBORNE").faction == "Alliance"
        and CR:GetCell("SHAMAN", "SKYBORNE").faction == "Horde")
    Check("组合表：单阵营列的格子不标阵营限定", CR:GetCell("WARRIOR", "HUMAN").limited == false)

    -- 界面侧：两块视图互斥
    Check("组合表：页头有两个视图按钮",
        U.raceModeBtns ~= nil and U.raceModeBtns.detail ~= nil and U.raceModeBtns.table ~= nil)
    Check("组合表：详情视图下总表已建好但隐藏",
        U.raceTable ~= nil and U.raceTable.__shown == false and U.raceDetail.__shown == true,
        tostring(U.raceTable and U.raceTable.__shown) .. "/" .. tostring(U.raceDetail and U.raceDetail.__shown))
    Check("组合表：9×9 格子控件齐备（含标记与阵营角标）",
        #U.raceCells == 9 and #U.raceCells[1] == 9 and U.raceCells[1][1].mark ~= nil,
        (#U.raceCells or 0) .. " 行")
    -- 表头种族名按阵营着色：联盟蓝 / 部落红 / 跨阵营中性
    local function SameRGB(fs, r, g, b)
        local c = fs and fs.__textColor
        if type(c) ~= "table" then return false end
        return math.abs((c[1] or -1) - r) < 0.01 and math.abs((c[2] or -1) - g) < 0.01
            and math.abs((c[3] or -1) - b) < 0.01
    end
    Check("组合表：表头人类（联盟）用联盟蓝",
        SameRGB(U.raceHeadFs and U.raceHeadFs[1], 0.42, 0.66, 1.0),
        U.raceHeadFs and table.concat(U.raceHeadFs[1].__textColor or {}, "/"))
    Check("组合表：表头兽人（部落）用部落红",
        SameRGB(U.raceHeadFs and U.raceHeadFs[5], 0.92, 0.32, 0.28))
    Check("组合表：表头天裔（跨阵营）不用阵营色",
        SameRGB(U.raceHeadFs and U.raceHeadFs[9], 0.88, 0.88, 0.88))

    local tBtn = U.raceModeBtns and U.raceModeBtns.table
    if tBtn and tBtn.__scripts and tBtn.__scripts.OnClick then Try("切到组合总表", tBtn.__scripts.OnClick, tBtn) end
    Check("组合表：已切到总表视图", U.raceView == "table", U.raceView)
    Check("组合表：总表显示 / 详情隐藏",
        U.raceTable.__shown == true and U.raceDetail.__shown == false)
    Check("组合表：标题与页头提示已切换",
        U.raceTitle.__text == "职业与种族组合" and type(U.raceSub.__text) == "string"
        and U.raceSub.__text:find("天裔", 1, true) ~= nil, tostring(U.raceSub.__text))

    -- 状态落到控件上：勾 / 星 / 空 + 阵营角标
    local function CellUI(key, tid)
        for ri, row in ipairs(U.raceTableRows) do
            if row.key == key then
                for ci, col in ipairs(U.raceTableCols) do
                    if col.tid == tid then return U.raceCells[ri][ci] end
                end
            end
        end
    end
    local cWarSky, cWarHuman = CellUI("WARRIOR", "SKYBORNE"), CellUI("WARRIOR", "HUMAN")
    local cDruHuman, cMagSky = CellUI("DRUID", "HUMAN"), CellUI("MAGE", "SKYBORNE")
    Check("组合表：天裔战士格显示金星",
        cWarSky ~= nil and cWarSky.__cell.state == "new" and cWarSky.mark.__shown == true
        and cWarSky.mark.__tex == "Interface\\TargetingFrame\\UI-RaidTargetingIcons",
        cWarSky and tostring(cWarSky.mark.__tex))
    Check("组合表：人类战士格显示勾、且不显示阵营角标",
        cWarHuman ~= nil and cWarHuman.__cell.state == "classic" and cWarHuman.mark.__shown == true
        and cWarHuman.mark.__tex == "Interface\\Buttons\\UI-CheckBox-Check"
        and cWarHuman.tag.__shown == false, cWarHuman and tostring(cWarHuman.mark.__tex))
    Check("组合表：人类德鲁伊格不显示任何标记",
        cDruHuman ~= nil and cDruHuman.__cell.state == "none"
        and cDruHuman.mark.__shown == false and cDruHuman.tag.__shown == false)
    Check("组合表：天裔法师格带「盟」角标",
        cMagSky ~= nil and cMagSky.tag.__shown == true and cMagSky.tag.__text == "盟",
        cMagSky and tostring(cMagSky.tag.__text))

    local fnEnter = cMagSky and cMagSky.__scripts and cMagSky.__scripts.OnEnter
    if Try("组合表格子 tooltip", fnEnter, cMagSky) then
        local tipOk = false
        for _, line in ipairs(TOOLTIP_LINES) do
            if tostring(line):find("法师 · 天裔", 1, true) then tipOk = true end
        end
        Check("组合表：格子 tooltip 含「职业 · 种族」", tipOk, table.concat(TOOLTIP_LINES, " | "))
    end
    TOOLTIP_LINES = {}

    -- 点格跳转：回到详情视图并选中该种族（天裔法师落位到联盟）
    local fnClick = cMagSky and cMagSky.__scripts and cMagSky.__scripts.OnClick
    if fnClick then Try("点天裔法师格", fnClick, cMagSky) end
    U.UpdateRaces(U)
    Check("组合表：点格后回到详情视图", U.raceView == "detail", U.raceView)
    Check("组合表：点格后落在联盟天裔",
        U.raceFaction == "Alliance" and U.raceIdx == CR:FindRaceIndex("Alliance", "SKYBORNE"),
        tostring(U.raceFaction) .. " / " .. tostring(U.raceIdx))
    Check("组合表：点格后标题回到种族详情", U.raceTitle.__text == "联盟种族", U.raceTitle.__text)
    local dBtn = U.raceModeBtns and U.raceModeBtns.detail
    if dBtn and dBtn.__scripts and dBtn.__scripts.OnClick then Try("切回详情按钮", dBtn.__scripts.OnClick, dBtn) end
    Check("组合表：详情按钮切回后详情显示、总表隐藏",
        U.raceView == "detail" and U.raceDetail.__shown == true and U.raceTable.__shown == false)
end

-- 传承福利：数据完整性 + 规则引擎（门槛 / 上限 / 退点保护 / 搜索 / 存档校正）
-- 注意：本测试块里的 ns 是脚本自建的桩表，插件命名空间请用 BG
local LL = BG.Legacy
Check("传承逻辑层已注册", LL ~= nil)
local leg = BG.RaceLegacyData.legacy
local function SameColor(ct, r, g, b)
    if type(ct) ~= "table" then return false end
    return math.abs((ct[1] or -1) - r) < 0.01 and math.abs((ct[2] or -1) - g) < 0.01
        and math.abs((ct[3] or -1) - b) < 0.01
end
local function LegNode(tr, id)
    for _, nd in ipairs(tr.nodes) do
        if nd.id == id then return nd end
    end
end
local function UINode(ui, id)
    for _, nu in ipairs(ui.nodes) do
        if nu.node.id == id then return nu end
    end
end
Check("传承数据：上限 16", leg.cap == 16, leg.cap)
Check("传承数据：三棵树且顺序为 专业→冒险→足智多谋",
    leg.trees[1].name == "专业" and leg.trees[2].name == "冒险" and leg.trees[3].name == "足智多谋",
    tostring(leg.trees[1].name) .. "/" .. tostring(leg.trees[2].name) .. "/" .. tostring(leg.trees[3].name))
local nNode, nLock, nEdge = 0, 0, 0
for _, tr in ipairs(leg.trees) do
    for _, nd in ipairs(tr.nodes) do
        nNode = nNode + 1
        if nd.locked then nLock = nLock + 1 end
    end
    nEdge = nEdge + #tr.edges
end
Check("传承数据：27 个节点（21 真实 + 6 占位）", nNode == 27 and nLock == 6, nNode .. " / " .. nLock)
Check("传承数据：9 条前置连线", nEdge == 9, nEdge)
Check("传承数据：绩效奖金上限修正为 3", (LegNode(leg.trees[1], 110292) or {}).max == 3)
Check("传承数据：补入讨价还价（0/2）", (LegNode(leg.trees[1], 110286) or {}).max == 2)
Check("传承数据：每棵树节点数与连线数齐整",
    #leg.trees[1].nodes == 9 and #leg.trees[2].nodes == 9 and #leg.trees[3].nodes == 9 and #leg.trees[1].edges == 3,
    #leg.trees[1].nodes .. "/" .. #leg.trees[2].nodes .. "/" .. #leg.trees[3].nodes)

local prof, adv = leg.trees[1], leg.trees[2]
local wo, barte, study = LegNode(prof, 110290), LegNode(prof, 110286), LegNode(prof, 110284)
LL:ResetAll()
Check("传承引擎：初始总点数 0", LL:TotalSpent() == 0, LL:TotalSpent())
Check("传承引擎：根节点可加点", LL:BlockedReason(prof, wo) == nil, LL:BlockedReason(prof, wo))
Check("传承引擎：req=5 节点被门槛拦下", LL:BlockedReason(prof, barte) ~= nil, LL:BlockedReason(prof, barte))
Check("传承引擎：占位格状态为 placeholder", LL:GetState(prof, LegNode(prof, 113508)) == "placeholder")
Check("传承引擎：占位格不可加点", LL:SetRank(1, LegNode(prof, 113508), 1) ~= nil)

for i = 1, 5 do LL:SetRank(1, wo, i) end
Check("传承引擎：根节点加满 5 点", LL:GetRank(110290) == 5 and LL:TreeSpent(prof) == 5, LL:GetRank(110290))
Check("传承引擎：加满后 req=5 解锁", LL:BlockedReason(prof, barte) == nil, LL:BlockedReason(prof, barte))
Check("传承引擎：加满态为 max", LL:GetState(prof, wo) == "max", LL:GetState(prof, wo))
Check("传承引擎：req=10 且前置无等级时仍拦", LL:BlockedReason(prof, study) ~= nil, LL:BlockedReason(prof, study))

LL:SetRank(1, barte, 1)
Check("传承引擎：前置 1 点后仍受点数门槛拦", LL:BlockedReason(prof, study) ~= nil, LL:BlockedReason(prof, study))
LL:SetRank(1, LegNode(prof, 110291), 4)
Check("传承引擎：本树 10 点", LL:TreeSpent(prof) == 10, LL:TreeSpent(prof))
Check("传承引擎：req=10 解锁", LL:BlockedReason(prof, study) == nil, LL:BlockedReason(prof, study))
LL:SetRank(1, study, 1)
Check("传承引擎：潜心钻研已投 1 点", LL:GetRank(110284) == 1, LL:GetRank(110284))
local denyBack = LL:SetRank(1, barte, 0)
Check("传承引擎：退掉被依赖的前置被拒", type(denyBack) == "string", denyBack)
Check("传承引擎：被拒后等级未变", LL:GetRank(110286) == 1, LL:GetRank(110286))

LL:ResetAll()
Check("传承引擎：重置后清零", LL:TotalSpent() == 0 and LL:GetRank(110290) == 0)
LL:SetRank(1, wo, 5)
LL:SetRank(1, LegNode(prof, 110291), 5)
LL:SetRank(1, LegNode(prof, 110292), 3)
LL:SetRank(1, LegNode(prof, 110293), 2)
Check("传承引擎：本树已投 15", LL:TreeSpent(prof) == 15, LL:TreeSpent(prof))
local capDeny = LL:SetRank(2, LegNode(adv, 110301), 5)
Check("传承引擎：一次加满超过剩余点数被拒", type(capDeny) == "string", capDeny)
Check("传承引擎：被拒后无副作用", LL:GetRank(110301) == 0, LL:GetRank(110301))
LL:SetRank(2, LegNode(adv, 110301), 1)
Check("传承引擎：总点数用满 16", LL:TotalSpent() == 16 and LL:Remaining() == 0, LL:TotalSpent())
local capDeny2 = LL:SetRank(2, LegNode(adv, 110301), 2)
Check("传承引擎：点数用满后再加被拒", type(capDeny2) == "string", capDeny2)

local matched, total = LL:Search("休息")
Check("传承搜索：命中含「休息」的节点", matched[110301] == true and total >= 1, total)
Check("传承搜索：占位格不参与搜索", select(2, LL:Search("后续内容更新")) == 0)
Check("传承搜索：无关键词时零命中", select(2, LL:Search("")) == 0)

LL:ResetAll()
LL:DB().ranks[999999] = 2
LL:DB().ranks[110284] = 1
LL:Sanitize()
Check("存档校正：剔除未知节点", LL:GetRank(999999) == 0, LL:GetRank(999999))
Check("存档校正：非法状态整表清空", LL:TotalSpent() == 0, LL:TotalSpent())

-- 传承页：互斥显示 + 三张卡 + 节点控件与交互
LL:ResetAll()
U.SwitchSub(U, "Legacy")
Check("传承页已显示", U.legacyPage.__shown == true)
Check("传承页：种族页已隐藏", U.racePage.__shown == false)
Check("传承页：tierPage 已隐藏", U.tierPage.__shown == false)
Check("传承页：talentPage 已隐藏", U.talentPage.__shown == false)
Try("传承页刷新", U.UpdateLegacy, U)
local nCard, nUINode, nUIEdge = 0, 0, 0
for _, ui in ipairs(U.legacyTrees) do
    if ui.card then nCard = nCard + 1 end
    nUINode = nUINode + #ui.nodes
    nUIEdge = nUIEdge + #ui.edges
end
Check("三棵福利树卡片", nCard == 3, nCard)
Check("页面节点控件 27 个", nUINode == 27, nUINode)
Check("页面连线控件 9 条", nUIEdge == 9, nUIEdge)
Check("树头已投点数已写入", type(U.legacyTrees[1].spent.__text) == "string" and U.legacyTrees[1].spent.__text ~= "",
    U.legacyTrees[1].spent.__text)
Check("总点数文案已写入", type(U.legacyPoints.__text) == "string" and U.legacyPoints.__text ~= "", U.legacyPoints.__text)
Check("分档芯片 2 个", #U.legacyTrees[1].chips == 2, #U.legacyTrees[1].chips)

local profUI = U.legacyTrees[1]
local advUI = U.legacyTrees[2]
local uiRoot = UINode(profUI, 110290)
local uiGate = UINode(profUI, 110286)
local uiLock = UINode(profUI, 113508)
Check("节点控件已创建", uiRoot ~= nil and uiGate ~= nil and uiLock ~= nil)
Check("0 级角标为 0/5", uiRoot.pip.__text == "0/5", uiRoot.pip.__text)
Check("可加点节点描边为白", SameColor(uiRoot.bars[1].__ct, 1, 1, 1), tostring(uiRoot.bars[1].__ct and uiRoot.bars[1].__ct[1]))
Check("门槛未满足描边为暗色", SameColor(uiGate.bars[1].__ct, 0.27, 0.27, 0.27))
Check("占位格不显示角标", uiLock.pip.__text == "" and uiLock.pipBg.__shown == false, uiLock.pip.__text)
-- 图标画在节点的子帧上，子帧在父帧贴图之上；角标若用节点自身的贴图承载会被图标整块盖住，
-- 所以角标必须挂在自己的子帧上且帧级高于图标帧
Check("角标帧级高于图标帧",
    uiRoot.pipFrame ~= nil and uiRoot.iconFrame ~= nil
    and uiRoot.pipFrame:GetFrameLevel() > uiRoot.iconFrame:GetFrameLevel())
Check("占位格角标帧级同样高于图标帧",
    uiLock.pipFrame ~= nil and uiLock.iconFrame ~= nil
    and uiLock.pipFrame:GetFrameLevel() > uiLock.iconFrame:GetFrameLevel())
Check("前置连线初始为暗色", SameColor(profUI.edges[1].tex.__ct, 0.27, 0.27, 0.27))

-- 门槛芯片：达标只让描边与文字转主题强调色并亮起外发光，不得用整块色块铺底（会连文字一起盖住）
local bgAccent = BG.hui.ACCENT
local chip5, chip10 = profUI.chips[1].chip, profUI.chips[2].chip
Check("门槛芯片走圆角描边（弧块 + 直边条）", #chip5.border == 8 and #chip5.glow == 8,
    #chip5.border .. " / " .. #chip5.glow)
Check("门槛芯片底色为圆角皮", type(chip5.bg) == "table" and #chip5.bg == 4, type(chip5.bg))
Check("传承树卡片走圆角皮", type(profUI.card.__roundPieces) == "table" and #profUI.card.__roundPieces == 4,
    type(profUI.card.__roundPieces))
Check("未达标芯片文字为灰", SameColor(chip5.text.__textColor, 0.63, 0.63, 0.63),
    tostring(chip5.text.__textColor and chip5.text.__textColor[1]))
Check("未达标芯片描边为灰", SameColor(chip5.border[1].__ct, 0.45, 0.45, 0.45),
    tostring(chip5.border[1].__ct and chip5.border[1].__ct[1]))
Check("未达标芯片不显示外发光", chip5.glow[1].__shown == false)

local click = uiRoot.bt.__scripts and uiRoot.bt.__scripts.OnClick
Check("节点点击脚本存在", click ~= nil)
for i = 1, 5 do
    if click then Try("点节点 " .. i, click, uiRoot.bt, "LeftButton") end
end
Check("左键加点写入引擎", LL:GetRank(110290) == 5, LL:GetRank(110290))
Check("加满后角标 5/5", uiRoot.pip.__text == "5/5", uiRoot.pip.__text)
Check("加满后描边转橙", SameColor(uiRoot.bars[1].__ct, 0xff / 255, 0x80 / 255, 0))
-- 门槛解锁但尚未投入：状态为 can（白描边），绿色只给「已投入未满」
Check("加满后门槛节点解锁转白", SameColor(uiGate.bars[1].__ct, 1, 1, 1), tostring(uiGate.bars[1].__ct and uiGate.bars[1].__ct[1]))
Check("树头点数同步为 5", tostring(profUI.spent.__text):find("5", 1, true) ~= nil, profUI.spent.__text)
Check("达标档芯片文字转主题强调色",
    SameColor(chip5.text.__textColor, bgAccent[1], bgAccent[2], bgAccent[3]),
    tostring(chip5.text.__textColor and chip5.text.__textColor[1]))
Check("达标档芯片描边转主题强调色",
    SameColor(chip5.border[1].__ct, bgAccent[1], bgAccent[2], bgAccent[3]),
    tostring(chip5.border[1].__ct and chip5.border[1].__ct[1]))
Check("未达标档描边为主题色以外的灰",
    not SameColor(chip10.border[1].__ct, bgAccent[1], bgAccent[2], bgAccent[3]),
    tostring(chip10.border[1].__ct and chip10.border[1].__ct[1]))
Check("达标档芯片外发光亮起", chip5.glow[1].__shown == true)
Check("未达标档芯片仍为灰", SameColor(chip10.text.__textColor, 0.63, 0.63, 0.63),
    tostring(chip10.text.__textColor and chip10.text.__textColor[1]))
Check("未达标档仍不显示外发光", chip10.glow[1].__shown == false)
if click then Try("右键退点", click, uiRoot.bt, "RightButton") end
Check("右键退点写入引擎", LL:GetRank(110290) == 4, LL:GetRank(110290))
Check("未满时描边为绿", SameColor(uiRoot.bars[1].__ct, 0x1e / 255, 0xff / 255, 0))
local enter = uiRoot.bt.__scripts and uiRoot.bt.__scripts.OnEnter
if enter then Try("节点提示框", enter, uiRoot.bt) end
local joined = table.concat(TOOLTIP_LINES, " | ")
Check("提示框含节点名", joined:find("加班加点", 1, true) ~= nil, joined)
Check("提示框含等级进度", joined:find("等级", 1, true) ~= nil, joined)
-- 操作说明分两行：Shift 说明必须另起一行，不能与「加点 / 退点」挤在同一行
local opLine, shiftLine
for _, line in ipairs(TOOLTIP_LINES) do
    local s = tostring(line)
    if s:find("左键加点", 1, true) and s:find("右键退点", 1, true) then opLine = s end
    if s:find("Shift 左键点满", 1, true) then shiftLine = s end
end
Check("提示框：加点 / 退点说明单独成行", opLine ~= nil, tostring(opLine))
Check("提示框：Shift 说明另起一行", shiftLine ~= nil and shiftLine ~= opLine, tostring(shiftLine))
Check("提示框：Shift 行不再与加点说明同排",
    shiftLine ~= nil and shiftLine:find("左键加点", 1, true) == nil, tostring(shiftLine))
if uiLock.bt.__scripts and uiLock.bt.__scripts.OnEnter then
    Try("占位格提示框", uiLock.bt.__scripts.OnEnter, uiLock.bt)
end
Check("占位格提示为未公布", table.concat(TOOLTIP_LINES, " | "):find("未公布", 1, true) ~= nil)

-- UI 路径的退点保护：右键退掉被依赖的前置应被拒并记录原因
LL:ResetAll()
LL:SetRank(1, wo, 5)
LL:SetRank(1, LegNode(prof, 110291), 5)
LL:SetRank(1, barte, 1)
LL:SetRank(1, study, 1)
U:UpdateLegacy()
-- OnClick 闭包绑定了各自的节点：必须取目标节点自己的脚本（传别的按钮仍会点到闭包里的那个节点）
local gateClick = uiGate.bt.__scripts and uiGate.bt.__scripts.OnClick
if gateClick then Try("右键退被依赖的前置", gateClick, uiGate.bt, "RightButton") end
Check("UI 右键被拒后等级未变", LL:GetRank(110286) == 1, LL:GetRank(110286))
Check("UI 被拒后记录原因", U.legacyRefusal ~= nil and U.legacyRefusal.id == 110286)

-- 搜索高亮
LL:ResetAll()
U:UpdateLegacy()
local sb = U.legacySearchBox
Check("搜索框已创建", sb ~= nil)
local onChg = sb and sb.__scripts and sb.__scripts.OnTextChanged
Check("搜索输入脚本存在", onChg ~= nil)
if onChg then
    sb:SetText("休息")
    Try("搜索输入", onChg, sb)
    Check("命中节点高亮", UINode(advUI, 110301).hl[1].__shown == true)
    Check("未命中节点无高亮", UINode(profUI, 110290).hl[1].__shown == false)
    Check("命中计数文案已写入", tostring(U.legacySearchInfo.__text):find("命中", 1, true) ~= nil, U.legacySearchInfo.__text)
    sb:SetText("")
    Try("清空搜索", onChg, sb)
    Check("清空后无高亮", UINode(advUI, 110301).hl[1].__shown == false)
end

-- 重置按钮（单树 / 全部）
LL:ResetAll()
LL:SetRank(1, wo, 3)
U:UpdateLegacy()
Check("有投入时重置按钮字色为白", SameColor(profUI.resetFS.__textColor, 1, 1, 1))
local rfn = profUI.reset.__scripts and profUI.reset.__scripts.OnClick
if rfn then Try("重置本树", rfn, profUI.reset) end
Check("单树重置生效", LL:TreeSpent(prof) == 0, LL:TreeSpent(prof))
LL:ResetAll()
LL:SetRank(1, wo, 2)
LL:SetRank(2, LegNode(adv, 110301), 2)
local afn = U.legacyResetAll.__scripts and U.legacyResetAll.__scripts.OnClick
if afn then Try("全部重置按钮", afn, U.legacyResetAll) end
Check("全部重置弹确认框", __lastPopup == "TALENTSFOREVER_LEGACY_RESET_ALL", __lastPopup)
if StaticPopupDialogs["TALENTSFOREVER_LEGACY_RESET_ALL"] then
    StaticPopupDialogs["TALENTSFOREVER_LEGACY_RESET_ALL"].OnAccept()
end
Check("确认后全部清零", LL:TotalSpent() == 0, LL:TotalSpent())
U:UpdateLegacy(U)
Check("清零后界面刷新无异常", U.legacyPoints.__text ~= nil)

-- 连线随前置投入转绿 + 存档落到 SavedVariables（账号共享）
LL:ResetAll()
LL:SetRank(1, LegNode(prof, 110291), 1)
U:UpdateLegacy()
Check("前置有等级后连线转绿", SameColor(profUI.edges[1].tex.__ct, 0x1e / 255, 0xff / 255, 0),
    tostring(profUI.edges[1].tex.__ct and profUI.edges[1].tex.__ct[1]))
Check("存档写入 TalentsForeverDB.legacy.ranks",
    type(TalentsForeverDB.legacy) == "table" and TalentsForeverDB.legacy.ranks[110291] == 1,
    tostring(type(TalentsForeverDB.legacy) == "table" and TalentsForeverDB.legacy.ranks[110291]))
Check("分享码随投入非空", #LL:Encode() > 0, LL:Encode())
LL:ResetAll()
U:UpdateLegacy()
Check("清空后连线回落暗色", SameColor(profUI.edges[1].tex.__ct, 0.27, 0.27, 0.27))
Check("清空后分享码为空", LL:Encode() == "", LL:Encode())

-- 提示框实时刷新：鼠标停在节点上时，点数一变提示框就应就地重建，不必移开再移回
local function tipHas(s)
    for _, line in ipairs(TOOLTIP_LINES) do
        if tostring(line):find(s, 1, true) then return true end
    end
    return false
end
local function tipClear()
    for i = #TOOLTIP_LINES, 1, -1 do TOOLTIP_LINES[i] = nil end
end

U.legacyHover = uiRoot
tipClear()
U:UpdateLegacy()
Check("传承提示框：0 点时就地重建", tipHas("等级 0 / 5"), table.concat(TOOLTIP_LINES, " | "))
LL:SetRank(1, wo, 5)
tipClear()
U:UpdateLegacy()
Check("传承提示框随加点刷新为 5 / 5", tipHas("等级 5 / 5"), table.concat(TOOLTIP_LINES, " | "))
GameTooltip:Hide()
tipClear()
U:UpdateLegacy()
Check("提示框已隐藏时不被刷新重新弹出", #TOOLTIP_LINES == 0, table.concat(TOOLTIP_LINES, " | "))
profUI.nodes[1].bt.__scripts.OnLeave()
Check("移开鼠标后清空 hover 记录", U.legacyHover == nil)
profUI.nodes[1].bt.__scripts.OnEnter()
Check("移入鼠标后记录 hover 节点", U.legacyHover == profUI.nodes[1])
U.legacyHover = nil
LL:ResetAll()
U:UpdateLegacy()

-- 天赋页同一策略：鼠标停在节点上点击加减点，提示框必须当场跟着变（不必移开鼠标再移回）
TS.SetClass(TS, "WARRIOR")
U.RebuildTrees(U)
TS.ResetAll(TS)
local tn = U.nodes[1] and U.nodes[1][1]
if tn then
    local max1 = TS.GetTalent(TS, 1, 1) and TS.GetTalent(TS, 1, 1).max or 0
    local function pts(n) return string.format("%d / %d", n, max1) end
    local enter = tn.bt.__scripts.OnEnter
    local leave = tn.bt.__scripts.OnLeave
    local click = tn.bt.__scripts.OnClick

    GameTooltip:Show()
    enter()
    Check("天赋提示框：0 点显示第 1 级说明", tipHas("等级 1") and tipHas(pts(0)),
        max1 .. " :: " .. table.concat(TOOLTIP_LINES, " | "))
    Check("0 点时不重复展示下一级", not tipHas("下一级："), table.concat(TOOLTIP_LINES, " | "))
    tipClear()
    Try("左键加点", click, tn.bt, "LeftButton")
    Check("加点后提示框就地刷新为 1 / " .. max1, tipHas(pts(1)), table.concat(TOOLTIP_LINES, " | "))
    Check("加点后带出下一级预览", tipHas("下一级："), table.concat(TOOLTIP_LINES, " | "))
    tipClear()
    TS.AddMax(TS, 1, 1)
    U:UpdateAll()
    Check("点满后不再显示下一级预览", tipHas(pts(max1)) and not tipHas("下一级："),
        table.concat(TOOLTIP_LINES, " | "))
    TS.ResetAll(TS)
    Try("回到 1 点", click, tn.bt, "LeftButton")
    tipClear()
    Try("再加到 2 点", click, tn.bt, "LeftButton")
    Check("再加一点后说明跳到第 2 级", tipHas("等级 2") and tipHas(pts(2)),
        table.concat(TOOLTIP_LINES, " | "))
    tipClear()
    Try("右键减点", click, tn.bt, "RightButton")
    Check("减点后提示框回落到 1 / " .. max1, tipHas(pts(1)) and not tipHas("等级 2"),
        table.concat(TOOLTIP_LINES, " | "))

    -- 退点被拒：提示框要当场给出原因（以前只会静默失败）
    TS.ResetAll(TS)
    local n2 = U.nodes[1][2]
    tipClear()
    n2.bt.__scripts.OnEnter()
    tipClear()
    Try("对 0 点天赋右键退点", n2.bt.__scripts.OnClick, n2.bt, "RightButton")
    Check("退点被拒时提示框显示原因", tipHas("尚未投入点数"), table.concat(TOOLTIP_LINES, " | "))
    tipClear()
    Try("左键加点成功", n2.bt.__scripts.OnClick, n2.bt, "LeftButton")
    Check("成功加点后不再显示上次拒绝原因", not tipHas("尚未投入点数"), table.concat(TOOLTIP_LINES, " | "))

    -- 鼠标移开后不得再重建提示框
    TS.ResetAll(TS)
    enter()
    leave()
    tipClear()
    U:UpdateAll()
    Check("移开鼠标后不再重建提示框", #TOOLTIP_LINES == 0, table.concat(TOOLTIP_LINES, " | "))

    -- 客户端点按时可能顺手收起提示框：鼠标没离开就该重新弹回来
    enter()
    tn.bt.__mouseOver = true
    GameTooltip:Hide()
    tipClear()
    U:UpdateAll()
    Check("提示框被收起但鼠标未离开时重新弹出", #TOOLTIP_LINES > 0, table.concat(TOOLTIP_LINES, " | "))
    tn.bt.__mouseOver = nil
    leave()
    GameTooltip:Show()
end
Check("天赋页 hover 记录随 OnLeave 清空", U.hoverNode == nil, tostring(U.hoverNode))
TS.ResetAll(TS)
U:UpdateAll()

-- 职业排行页：三张档位卡 + 专精单元（互斥显示 / 本职业常亮 / 点格跳转）
local ST = BG.SpecTierData
Check("专精梯队数据已加载（三档）", ST ~= nil and #(ST.tiers or {}) == 3, ST and #(ST.tiers or {}))
local stTotal, stMissing = 0, 0
for _, tier in ipairs(ST and ST.tiers or {}) do
    for _, e in ipairs(tier.specs or {}) do
        stTotal = stTotal + 1
        local list = ST.specs[e.class]
        local hit = false
        for _, sp in ipairs(list or {}) do if sp.key == e.spec then hit = true end end
        if not hit then stMissing = stMissing + 1 end
    end
end
Check("梯队条目 22 个", stTotal == 22, stTotal)
Check("梯队条目的职业+专精都能在专精目录里查到", stMissing == 0, stMissing)

U.SwitchSub(U, "SpecTier")
Check("职业排行页已显示", U.tierPage.__shown == true)
Check("职业排行页：传承页已隐藏", U.legacyPage.__shown == false)
Check("职业排行页：天赋页已隐藏", U.talentPage.__shown == false)
Check("职业排行页：种族页已隐藏", U.racePage.__shown == false)
Check("职业排行页：职业按钮行已隐藏", (function()
    for _, bt in pairs(U.classBtns) do if bt.__shown ~= false then return false end end
    return true
end)())

local nTierCard, nSpecCell, nBadge = 0, 0, 0
for _, ui in ipairs(U.tierCards or {}) do
    nTierCard = nTierCard + 1
    nSpecCell = nSpecCell + #ui.cells
    nBadge = nBadge + #(ui.badgeBg or {})
end
Check("三张档位卡", nTierCard == 3, nTierCard)
Check("专精单元 22 个（8 + 9 + 5）", nSpecCell == 22, nSpecCell)
Check("档位徽记底色已建", nBadge > 0, nBadge)
Check("徽记字母为档位键", U.tierCards[1].letter.__text == "S", U.tierCards[1].letter.__text)
Check("页头档位统计已写入",
    type(U.tierNote.__text) == "string" and U.tierNote.__text:find("22", 1, true) ~= nil, U.tierNote.__text)
Check("页头免责声明已写入",
    type(U.tierFine.__text) == "string" and U.tierFine.__text:find("嘉年华", 1, true) ~= nil
    and U.tierFine.__text:find("不代表", 1, true) ~= nil, U.tierFine.__text)

-- 每个单元都必须拿到图标：数据里 class+spec 查不到时图标会落问号兜底
local noIcon, qm, noCatalog = 0, 0, 0
for _, ui in ipairs(U.tierCards) do
    Check("档位卡单元数不超过列数（单行即可容纳）", #ui.cells <= ui.cols, #ui.cells .. "/" .. ui.cols)
    for _, c in ipairs(ui.cells) do
        local t = c.icon.__tex
        if not t or t == "" then noIcon = noIcon + 1 end
        if t == "Interface\\Icons\\INV_Misc_QuestionMark" then qm = qm + 1 end
        if c.specName == "" or c.specEn == "" then noCatalog = noCatalog + 1 end
    end
end
Check("每个专精单元都有图标", noIcon == 0, noIcon)
Check("专精图标无问号兜底", qm == 0, qm)
Check("每个专精单元都解析出全称与英文名", noCatalog == 0, noCatalog)

-- 专精显示名取自梯队图，职业名/职业色走插件自身数据
local c1 = U.tierCards[1].cells[1]
Check("单元1 显示名为梯队图上的专精名", c1.nameFs.__text == "元素萨", c1.nameFs.__text)
Check("单元1 职业名为萨满祭司", c1.classFs.__text == "萨满祭司", c1.classFs.__text)
Check("单元1 专精全称已解析", c1.specName == "元素" and c1.specEn == "Elemental",
    tostring(c1.specName) .. "/" .. tostring(c1.specEn))
Check("单元1 图标取自专精目录",
    c1.icon.__tex == "Interface\\Icons\\spell_nature_lightning", tostring(c1.icon.__tex))

-- 本职业的专精常亮：切职业后当场跟随
TS.SetClass(TS, "SHAMAN")
U:UpdateSpecTier()
local ownN, ownLitWrong, otherLit = 0, 0, 0
for _, ui in ipairs(U.tierCards) do
    for _, c in ipairs(ui.cells) do
        if c.own == true then
            ownN = ownN + 1
            if c.patches[1].__shown ~= true then ownLitWrong = ownLitWrong + 1 end
        elseif c.patches[1].__shown == true then
            otherLit = otherLit + 1
        end
    end
end
Check("本职业（萨满）专精高亮 2 个", ownN == 2, ownN)
Check("高亮单元底色已亮起", ownLitWrong == 0, ownLitWrong)
Check("非本职业单元底色隐藏", otherLit == 0, otherLit)

-- 悬停：底色亮起 + 提示框内容（鼠标移开后非本职业单元必须回落）
tipClear()
c1.__scripts.OnEnter()
Check("悬停单元底色亮起", c1.patches[1].__shown == true)
Check("悬停提示框含专精名", tipHas("元素萨"), table.concat(TOOLTIP_LINES, " | "))
Check("悬停提示框含职业与专精", tipHas("萨满祭司 · 元素"), table.concat(TOOLTIP_LINES, " | "))
Check("悬停提示框含英文名", tipHas("Elemental"), table.concat(TOOLTIP_LINES, " | "))
tipClear()
c1.__scripts.OnLeave()
Check("移开后本职业单元仍常亮", c1.patches[1].__shown == true)
local cB = U.tierCards[3].cells[1]
Check("末尾档首位为鸟德（平衡）", cB.nameFs.__text == "鸟德（平衡）", cB.nameFs.__text)
cB.__scripts.OnEnter()
Check("悬停非本职业单元底色亮起", cB.patches[1].__shown == true)
cB.__scripts.OnLeave()
Check("移开后非本职业单元底色回落", cB.patches[1].__shown == false)

-- 点格跳转：切到天赋页并把职业切到该专精所属职业
U.SwitchSub(U, "SpecTier")
cB.__scripts.OnClick()
Check("点格跳转天赋页", U.talentPage.__shown == true and U.tierPage.__shown == false)
Check("点格跳转后职业切到该专精所属职业", TS.GetClassKey(TS) == "DRUID", TS.GetClassKey(TS))
Check("点格跳转后天赋节点按新职业重建", U.nodeClass == "DRUID", tostring(U.nodeClass))
Check("点格跳转后子页存档为 Talents", TalentsForeverDB.sim.subTab == "Talents", TalentsForeverDB.sim.subTab)

-- 同职业再点一次：不重建也必须能回到天赋页
U.SwitchSub(U, "SpecTier")
cB.__scripts.OnClick()
Check("同职业点格仍能回到天赋页", U.talentPage.__shown == true, tostring(U.talentPage.__shown))

TS.SetClass(TS, "WARRIOR")
U:RebuildTrees()
U:UpdateAll()
U.SwitchSub(U, "SpecTier")
Check("换职业后高亮跟随（战士 2 个输出专精）", (function()
    local n = 0
    for _, ui in ipairs(U.tierCards) do
        for _, c in ipairs(ui.cells) do if c.own == true then n = n + 1 end end
    end
    return n == 2
end)(), "战士专精 2 个")

U.SwitchSub(U, "Talents")
Check("切回天赋页：其余三页全隐藏",
    U.talentPage.__shown == true and U.spellPage.__shown == false
    and U.racePage.__shown == false and U.legacyPage.__shown == false
    and U.tierPage.__shown == false)

-- 法术书：9 职业逐页刷新
for _, key in ipairs(ORDER) do
    TS.SetClass(TS, key)
    U.SwitchSub(U, "SpellBook")
    Try("法术书 " .. key, U.UpdateSpellBook, U)
end
Check("9 职业法术书刷新无异常", true)

-- 切换职业：法术书左侧专精页签必须立即刷新（走真实点击职业按钮的路径）
U.SwitchSub(U, "SpellBook")
TS.SetClass(TS, "WARRIOR")
U.UpdateSpellBook(U)
local tabName1 = U.spellTabs[1] and U.spellTabs[1].__text
local function ClickClass(key)
    local b = U.classBtns[key]
    local fn = b and b.__scripts and b.__scripts.OnClick
    if fn then Try("点击职业按钮 " .. key, fn, b) end
end
ClickClass("MAGE")
local tabName2 = U.spellTabs[1] and U.spellTabs[1].__text
Check("切职业后专精页签立即刷新", tabName1 ~= tabName2,
    tostring(tabName1) .. " -> " .. tostring(tabName2))
Check("切到新职业显示第一页", U.curSpellTab == 1, U.curSpellTab)

-- 记忆上次看的页：法师停在第 2 页 -> 切走 -> 切回应恢复第 2 页
local tab2 = U.spellTabs[2]
local fn2 = tab2 and tab2.__scripts and tab2.__scripts.OnClick
if fn2 then Try("法师切到第 2 页", fn2, tab2) end
Check("法师当前页 = 2", U.curSpellTab == 2, U.curSpellTab)
ClickClass("WARRIOR")
Check("切到战士后为第一页", U.curSpellTab == 1, U.curSpellTab)
ClickClass("MAGE")
Check("切回法师恢复上次第 2 页", U.curSpellTab == 2, U.curSpellTab)

-- 法术书提示框：行是复用的，OnEnter 必须读当前绑定的 row.sp
-- （曾因闭包捕获创建时的 sp，切页后提示的是上个页面的技能）
TS.SetClass(TS, "MAGE")
U.curSpellTab = 1
U.UpdateSpellBook(U)
local r1 = U.spellRows[1]
Check("法术书行已创建", r1 ~= nil)
-- 技能图标与天赋模拟器页的节点图标同尺寸（两页观感一致，改一处不得只改另一处）
local nodeBt = U.nodes[1] and U.nodes[1][1] and U.nodes[1][1].bt
if r1 and r1.iconHolder and nodeBt then
    Check("法术书图标尺寸与天赋页一致", r1.iconHolder.__w == nodeBt.__w,
        tostring(r1.iconHolder.__w) .. "/" .. tostring(nodeBt.__w))
else
    Check("法术书图标尺寸与天赋页一致", false, "缺 iconHolder 或节点")
end
if r1 then
    local name1 = r1.sp and r1.sp.name
    U.curSpellTab = 2
    U.UpdateSpellBook(U)
    Check("法术书行随页重绑技能", r1.sp ~= nil and r1.sp.name ~= name1, r1.sp and r1.sp.name)
    local fn = r1.__scripts and r1.__scripts.OnEnter
    if fn and r1.sp then
        Try("法术书行 tooltip", fn, r1)
        Check("提示框取当前技能而非旧技能", TOOLTIP_LINES[1] == r1.sp.name, TOOLTIP_LINES[1])
    else
        Check("提示框取当前技能而非旧技能", false, "无 OnEnter")
    end
    U.curSpellTab = 1
    U.UpdateSpellBook(U)
end

-- 两列布局：第 1、2 个技能同一行（y 相同），第 3 个换行（y 不同）
if U.spellRows[1] and U.spellRows[2] and U.spellRows[3] then
    local p1, p2, p3 = U.spellRows[1].__pts, U.spellRows[2].__pts, U.spellRows[3].__pts
    Check("法术书两列：前两个同行", p1 and p2 and p1[5] == p2[5],
        tostring(p1 and p1[5]) .. "/" .. tostring(p2 and p2[5]))
    Check("法术书两列：第三个换行", p1 and p3 and p3[5] ~= p1[5],
        tostring(p1 and p1[5]) .. "/" .. tostring(p3 and p3[5]))
end

-- 需求等级必须中文化（数据源原文为英文 "Requires level N"）
local enLv, cnLv = 0, 0
for _, key in ipairs(ORDER) do
    local sb = BG.SpellBookData.classes[key]
    local function scan(list)
        for _, sp in ipairs(list or {}) do
            if sp.reqLv and sp.reqLv ~= "" then
                if sp.reqLv:find("Requires") then enLv = enLv + 1 end
                if sp.reqLv:find("^需要等级 %d+$") then cnLv = cnLv + 1 end
            end
        end
    end
    for _, t in ipairs(sb.tabs) do scan(t.spells) end
    scan(sb.general)
end
Check("法术书需求等级已汉化", enLv == 0 and cnLv > 0, "英文 " .. enLv .. " / 中文 " .. cnLv)

-- 图标：约六成法术无 ID，必须能按名反查到贴图，不能回退问号
TS.SetClass(TS, "WARRIOR")
U.curSpellTab = 1
U.UpdateSpellBook(U)
local qm, ic = 0, 0
for i = 1, #U.spellRows do
    local r = U.spellRows[i]
    if r.__shown ~= false and r.icon then
        ic = ic + 1
        if r.icon.__tex == "Interface\\Icons\\INV_Misc_QuestionMark" then qm = qm + 1 end
    end
end
Check("法术书图标无问号回退", ic > 0 and qm == 0, ic .. " 个图标 / " .. qm .. " 个问号")

-- 兜底链逐层压测（id / 名字都用夹具里「客户端不认识」的号，保证真的会往下掉层）：
-- ① 客户端不认 ID、但按名认得的 —— 靠按名反查 ID
--    名字取一个「数据里根本没有、客户端却认识」的，才能保证前面几层（数据内同名 id / 贴图 /
--    数据自带 id）都拿不到。数据 ID 已按客户端 DB2 校订过，所以不再能拿真实条目来演这一幕。
local probe1 = U.IconOf and U.IconOf({ id = 704, name = "只在客户端存在的技能" })
Check("客户端不认的 ID 时按名兜底取到图标", probe1 ~= nil, tostring(probe1))
-- ② 客户端按名也不认的（泰坦端实测）—— 靠「数据内同名条目自带的 ID」。
--    新增技能条目本身没有 id、只有技能名，这条路是它们唯一能自动取到图标的办法。
local probe2 = U.IconOf and U.IconOf({ name = "反击风暴" })
Check("客户端不认名字时按数据内同名 ID 兜底", probe2 ~= nil, tostring(probe2))
-- ③ ID 与名字客户端都不认（乘胜追击在泰坦端实测就是这条）—— 靠角色法术书里的同名技能
local probe3 = U.IconOf and U.IconOf({ id = 402927, name = "乘胜追击" })
Check("客户端不认 ID 也不认名字时按角色法术书兜底", probe3 ~= nil, tostring(probe3))
-- ④ 客户端按名不认、数据里也没有同名带 id 的条目，但同名条目自带贴图路径
--    （左栏「新增技能」说明行就是这条：只写技能名 + 借同页技能的素材）
local probe4 = U.IconOf and U.IconOf({ name = "先祖的召唤" })
Check("客户端不认名字时按数据内同名贴图兜底", probe4 ~= nil, tostring(probe4))
-- ⑤ 宠物命令/姿态：客户端没有对应法术行，按名按号都查不到，贴图只有宠物条知道。
--    桩按游戏内实测形态给令牌（isToken=1），插件须 _G 解析后才拿得到本地化名与贴图；
--    2026-09-16 用户实测游戏内名字：攻击型/防御型/被动型/跟随/移动到/停留（数据已同步）。
local probe5 = U.IconOf and U.IconOf({ name = "攻击型" })
local probe5b = U.IconOf and U.IconOf({ name = "停留" })
Check("客户端查不到时按宠物条同名条目兜底",
    probe5 == "Interface\\PetBar\\Pet_Assist" and probe5b == "Interface\\PetBar\\Pet_Stay",
    tostring(probe5) .. " / " .. tostring(probe5b))

-- 图标诊断必须一次覆盖全部职业（切一个职业输一次太麻烦），且不依赖「当前职业」
TS.SetClass(TS, "MAGE")
local DIAG = {}
do
    local raw = print
    print = function(...)
        local parts = {}
        for i = 1, select("#", ...) do parts[#parts + 1] = tostring((select(i, ...))) end
        DIAG[#DIAG + 1] = table.concat(parts, " ")
    end
    Try("法术书图标诊断（全职业）", function() U:SpellIconDiag() end)
    print = raw
end
local joined = table.concat(DIAG, "\n")
local lack = {}
for _, key in ipairs(ORDER) do
    local c = BG.SpellBookData.classes[key]
    if c and not joined:find(c.name, 1, true) then lack[#lack + 1] = key end
end
Check("图标诊断一次覆盖全部职业", #lack == 0, "缺 " .. table.concat(lack, ","))
Check("图标诊断不依赖当前职业", joined:find(BG.SpellBookData.classes.WARRIOR.name, 1, true) ~= nil)
-- 诊断必须逐条说清「哪条兜底路走不通」。还击等样本已在数据修正中补上素材（不再经过兜底链），
-- 所以这里改成三条各有针对性的契约断言：
--   ① 七条路全失败 → 解析器返回 nil（界面据此回退问号，宁可显式回退也不要静默空白）
--   ② 诊断表头把七条路都列了出来（列名契约，改列必须同步改断言）
--   ③ 整份数据在当前桩客户端下 0 缺失（数据 ID/图标修正的回归闸门）
Check("所有兜底路都走不通时返回 nil（界面据此回退问号）",
    U.IconOf ~= nil and U.IconOf({ name = "不存在的技能" }) == nil,
    tostring(U.IconOf and U.IconOf({ name = "不存在的技能" })))
Check("图标诊断表头列出七条兜底路",
    joined:find("数据id=条目自带 ID", 1, true) ~= nil
    and joined:find("路径=数据内同名贴图", 1, true) ~= nil
    and joined:find("宠物条=客户端宠物条", 1, true) ~= nil
    and joined:find("书=角色法术书", 1, true) ~= nil,
    joined:find("数据id=[^\n]*") or "未找到表头")
Check("图标诊断全职业 0 缺失（数据修正的回归闸门）",
    joined:find("法术书图标诊断：%d+ 个职业 %d+ 个条目，缺 0") ~= nil,
    joined:find("法术书图标诊断[^\n]*") or "未找到诊断汇总行")

-- 查询探针（/tf spellid）：逐条报告各条客户端路；「按名字查」不得把施法时间当法术 ID
local PROBE = {}
do
    local raw = print
    print = function(...)
        local parts = {}
        for i = 1, select("#", ...) do parts[#parts + 1] = tostring((select(i, ...))) end
        PROBE[#PROBE + 1] = table.concat(parts, " ")
    end
    Try("查询探针（按名）", function() U:SpellIdProbe("冰霜新星") end)
    Try("查询探针（按号）", function() U:SpellIdProbe("20230") end)
    print = raw
end
local pj = table.concat(PROBE, "\n")
local wantId = tostring(70000 + (#"冰霜新星" % 5000))
Check("查询探针报告各条客户端路", pj:find("C_Spell=" .. wantId, 1, true) ~= nil,
    pj:find("查 ID：[^\n]*") or "无输出")
Check("按名查不得把施法时间当 ID", pj:find("GetSpellInfo（仅数字）=无", 1, true) ~= nil)
TS.SetClass(TS, "WARRIOR")
U.curSpellTab = 1
U.UpdateSpellBook(U)

-- 提示框：补充消耗 / 施法时间 / 冷却
local r0 = U.spellRows[1]
if r0 and r0.__scripts and r0.__scripts.OnEnter then
    Try("法术书行 tooltip（数值行）", r0.__scripts.OnEnter, r0)
    local has = {}
    for _, s in ipairs(TOOLTIP_LINES) do has[s] = true end
    Check("提示框含消耗行", has["消耗"] == true)
    Check("提示框含施法时间行", has["施法时间"] == true)
    Check("提示框含冷却行", has["冷却"] == true)
else
    Check("提示框含消耗行", false, "无 OnEnter")
end

U.SwitchSub(U, "Talents")

-- 图例开关：控制「新 / 改 / 移」角标是否显示
TS.SetClass(TS, "WARRIOR")
local function CountTags()
    local n = 0
    for ti = 1, 3 do
        for _, nd in ipairs(U.nodes[ti] or {}) do
            if nd.cls and nd.cls.__shown ~= false then n = n + 1 end
        end
    end
    return n
end
TS.DB(TS).showLegend = true
U.legendOn = true
U.RebuildTrees(U)
U.UpdateAll(U)
local tagOn = CountTags()
TS.DB(TS).showLegend = false
U.legendOn = false
U.UpdateAll(U)
local tagOff = CountTags()
Check("图例开启时显示角标", tagOn > 0, tagOn)
Check("图例关闭时隐藏角标", tagOff == 0, tagOff)
TS.DB(TS).showLegend = true
U.legendOn = true
U.UpdateAll(U)

-- 已移除的两个开关：不应再存在入口
Check("减点模式按钮已移除", U.tgRemove == nil, U.tgRemove)
Check("对比当前天赋按钮已移除", U.tgDiff == nil, U.tgDiff)
Check("图例按钮保留", U.tgLegend ~= nil)

-- 状态角标改为文字：必须与提示框的完整说明区分开（单字）
TS.SetClass(TS, "WARRIOR")
U.RebuildTrees(U)
U.UpdateAll(U)
local tagged, wrongTag = 0, 0
for ti = 1, 3 do
    for i = 1, #(U.nodes[ti] or {}) do
        local n = U.nodes[ti][i]
        local t = TS.GetTalent(TS, ti, i)
        if t and (t.status == "new" or t.status == "changed" or t.status == "moved") then
            tagged = tagged + 1
            local txt = n.cls and n.cls.__text
            -- 角标必须是单字，且与旧的色块贴图无关
            if type(txt) ~= "string" or #txt > 3 then wrongTag = wrongTag + 1 end
        end
    end
end
Check("状态角标为单字文字", tagged > 0 and wrongTag == 0, tagged .. " 个角标 / " .. wrongTag .. " 个异常")

-- 职业按钮：hui 主题下文字用职业色，选中项有描边
local curKey = TS.GetClassKey(TS)
local noBorder, noColor = 0, 0
for key, bt in pairs(U.classBtns) do
    local c = BG.TalentSimData.classes[key]
    local hex = c and c.color or "#e8b84a"
    local cr = tonumber(hex:sub(2, 3), 16) / 255
    local fs = bt:GetFontString()
    local tc = fs.__textColor
    if type(tc) == "table" and math.abs((tc[1] or 0) - cr) > 0.01 then noColor = noColor + 1 end
    if key == curKey then
        if bt.__outlineFrame then
            -- hui：圆角描边整体由一个子帧承载
            if not bt.__outlineFrame.__shown then noBorder = noBorder + 1 end
        else
            local shown = 0
            for _, tex in ipairs(bt.__bars or {}) do if tex.__shown then shown = shown + 1 end end
            if shown ~= 4 then noBorder = noBorder + 1 end
        end
    end
end
Check("职业按钮文字为职业色", noColor == 0, noColor)
Check("选中职业有外框描边", noBorder == 0, noBorder)

-- hui：选中描边必须走圆角（BG.hui.BuildRoundBorder），且选中/未选中互斥
local selBtn = U.classBtns[curKey]
Check("hui 职业按钮有圆角描边帧",
    selBtn ~= nil and selBtn.__outlineFrame ~= nil and selBtn.__outlineFrame ~= false,
    selBtn and selBtn.__outlineFrame)
if selBtn and selBtn.__outlineFrame and selBtn.__outlineFrame ~= false then
    Check("hui 选中职业圆角描边已显示", selBtn.__outlineFrame.__shown == true)
    local other
    for k, b in pairs(U.classBtns) do if k ~= curKey then other = b break end end
    if other and other.__outlineFrame and other.__outlineFrame ~= false then
        Check("hui 未选中职业圆角描边已隐藏", other.__outlineFrame.__shown == false)
    end
end

-- 页头「方案输入框 / 保存 / 删除」三件套右缘必须与职业按钮行末位（德鲁伊）右缘对齐。
-- 锚链：nameEdit TOPLEFT 定 x，save/del 依次锚前一个 RIGHT；职业行末位右缘 = 其 TOPLEFT x + 按钮宽。
do
    local CBW, GAPX = 100, 6
    local NAME_W, ACT_W = 146, 50
    local lastBtn = U.classBtns[ORDER[#ORDER]]
    local ne = U.nameEdit
    if ne and ne.__pts and ne.__pts[4] and lastBtn and lastBtn.__pts and lastBtn.__pts[4] then
        local nameRight = ne.__pts[4] + NAME_W
        local delRight = nameRight + GAPX + ACT_W + GAPX + ACT_W
        local clsRight = lastBtn.__pts[4] + CBW
        Check("页头方案三件套右缘对齐职业行末位",
            math.abs(delRight - clsRight) < 0.01,
            "删除右缘 " .. tostring(delRight) .. " / 职业行末位右缘 " .. tostring(clsRight))
    else
        Check("页头方案三件套右缘对齐职业行末位", false, "缺锚点记录")
    end
end

-- 页头三系点数已移除：同样信息由卡片标题的「n 点」承载，U.counters 必须保持空表（防回退）
Check("页头三系点数已移除", next(U.counters or {}) == nil,
    "counters 条数 " .. tostring(U.counters and #U.counters))

-- 数据来源条目：面板底部并排两条，右起第一条贴面板右下角，wowhead 在其左侧。
-- 两条共用同一个弹窗，展示哪条地址必须由点击的条目决定（先后点两次不可串台）
do
    local sc = U.sourceCredits or {}
    Check("数据来源条目为 2 条", #sc == 2, #sc)
    if #sc == 2 then
        local tfSrc, wowSrc = sc[1], sc[2]
        Check("右侧条目为 talentsforever",
            tfSrc.url == "https://talentsforever.com" and tfSrc.label == "数据来源：talentsforever",
            tostring(tfSrc.label) .. " / " .. tostring(tfSrc.url))
        Check("左侧条目为 wowhead",
            wowSrc.url == "https://www.wowhead.com/forever" and wowSrc.label == "数据来源：wowhead",
            tostring(wowSrc.label) .. " / " .. tostring(wowSrc.url))
        -- 右侧条目贴面板右下角
        local p1 = tfSrc.fs.__pts or {}
        Check("右侧条目贴面板右下角",
            p1[1] == "BOTTOMRIGHT" and p1[2] == U.panel,
            tostring(p1[1]) .. " / " .. tostring(p1[3]))
        -- 左侧条目锚在右侧条目的左缘，偏移必须为负（否则两条重叠在同一处）
        local p2 = wowSrc.fs.__pts or {}
        Check("左侧条目锚在右侧条目左边",
            p2[1] == "RIGHT" and p2[2] == tfSrc.fs and p2[3] == "LEFT"
                and type(p2[4]) == "number" and p2[4] < 0,
            tostring(p2[1]) .. " / " .. tostring(p2[3]) .. " / " .. tostring(p2[4]))
        -- 点击 → 弹窗；弹窗内地址取自被点的那一条
        local function popupTextOf(src)
            src.btn.__scripts.OnClick(src.btn)
            local dlg = StaticPopupDialogs["TalentsForever_SourceURL"]
            if not dlg then return nil, __lastPopup end
            local box = {}
            box.SetText = function(self, v) self.__text = v end
            box.HighlightText = function() end
            box.SetFocus = function() end
            dlg.OnShow({ EditBox = box })
            return box.__text, __lastPopup
        end
        local tfText, tfPopup = popupTextOf(tfSrc)
        local wowText, wowPopup = popupTextOf(wowSrc)
        Check("点 talentsforever 弹窗出对应网址",
            tfPopup == "TalentsForever_SourceURL" and tfText == "https://talentsforever.com",
            tostring(tfText) .. " / " .. tostring(tfPopup))
        Check("点 wowhead 弹窗出对应网址",
            wowPopup == "TalentsForever_SourceURL" and wowText == "https://www.wowhead.com/forever",
            tostring(wowText) .. " / " .. tostring(wowPopup))
        -- 悬停：提示框 + 文字提亮；移开复位
        tipClear()
        wowSrc.btn.__scripts.OnEnter(wowSrc.btn)
        Check("来源条目悬停出提示", TOOLTIP_LINES[1] == "点击复制数据来源网址", tostring(TOOLTIP_LINES[1]))
        Check("来源条目悬停文字提亮", (wowSrc.fs.__textColor[1] or 0) > 0.55, wowSrc.fs.__textColor[1])
        wowSrc.btn.__scripts.OnLeave(wowSrc.btn)
        Check("来源条目移开文字复位",
            math.abs((wowSrc.fs.__textColor[1] or 0) - 0.55) < 0.001, wowSrc.fs.__textColor[1])
    end
end

-- 页内子卡片：四个子页的卡片行一律左右内缩 PAGE_INSET（圆角卡不得顶着面板圆角），
-- 且 hui 下走圆角皮（BuildRoundedBG）。卡片宽由卡内网格定死，内缩量由间距吸收，
-- 故断言「首卡左缘 = 内缩量」+「末卡右缘 = 面板宽 - 内缩量」，并单独查一处卡间距。
do
    local PANEL_W = U.panel.__w
    local INSET, GAP = 12, 12
    Check("面板宽度已记录", PANEL_W == 960, tostring(PANEL_W))
    local function rounded(card)
        return type(card) == "table" and type(card.__roundPieces) == "table" and #card.__roundPieces == 4
    end
    -- 天赋模拟器页：三张树卡（各卡锚在页左上，x 为绝对偏移）
    local t = U.trees or {}
    Check("天赋页三张树卡走圆角皮", rounded(t[1]) and rounded(t[2]) and rounded(t[3]),
        tostring(t[1] and t[1].__roundPieces))
    if t[1] and t[3] then
        local left, right = t[1].__pts[4], t[3].__pts[4] + (t[3].__w or 0)
        Check("天赋页卡片行左右留白一致",
            math.abs(left - INSET) < 0.01 and math.abs(right - (PANEL_W - INSET)) < 0.01,
            string.format("左 %.1f / 右 %.1f（面板宽 %d）", left, right, PANEL_W))
        local gap = t[2].__pts[4] - (t[1].__pts[4] + (t[1].__w or 0))
        Check("天赋页卡片间距为 12", math.abs(gap - GAP) < 0.01, gap)
    end
    -- 法术书 / 种族页：左右两栏（右栏锚在左栏右缘，x 为相对偏移）
    local function twoColCheck(tag, leftCard, rightCard)
        if not (leftCard and rightCard) then
            Check(tag .. "两栏卡片走圆角皮", false, "页面未构建")
            return
        end
        Check(tag .. "两栏卡片走圆角皮", rounded(leftCard) and rounded(rightCard), tostring(leftCard.__roundPieces))
        local l = leftCard.__pts[4]
        local r = leftCard.__pts[4] + (leftCard.__w or 0) + rightCard.__pts[4] + (rightCard.__w or 0)
        Check(tag .. "两栏卡片行左右留白一致",
            math.abs(l - INSET) < 0.01 and math.abs(r - (PANEL_W - INSET)) < 0.01,
            string.format("左 %.1f / 右 %.1f（面板宽 %d）", l, r, PANEL_W))
    end
    twoColCheck("法术书", U.spellLeft, U.spellRight)
    twoColCheck("种族", U.raceLeft, U.raceRight)
    -- 传承福利页：三张树卡（同样锚在页左上）
    local lg = U.legacyTrees or {}
    if lg[1] and lg[#lg] then
        local left = lg[1].card.__pts[4]
        local right = lg[#lg].card.__pts[4] + (lg[#lg].card.__w or 0)
        Check("传承页卡片行左右留白一致",
            math.abs(left - INSET) < 0.01 and math.abs(right - (PANEL_W - INSET)) < 0.01,
            string.format("左 %.1f / 右 %.1f（面板宽 %d）", left, right, PANEL_W))
    end
end

-- 节点点击
TS.SetClass(TS, "WARRIOR")
U.RebuildTrees(U)
local node = U.nodes[1] and U.nodes[1][1]
Check("节点已创建", node ~= nil)
if node then
    local click = node.bt.__scripts and node.bt.__scripts.OnClick
    if click then
        Try("左键加点", click, node.bt, "LeftButton")
        Try("右键减点", click, node.bt, "RightButton")
    end
    local enter = node.bt.__scripts and node.bt.__scripts.OnEnter
    Try("节点 tooltip", enter)
end
Try("全节点 tooltip 构建", function()
    for ti = 1, 3 do
        for i = 1, #U.nodes[ti] do
            TS.ResetAll(TS)
            local n = U.nodes[ti][i]
            local fn = n.bt.__scripts.OnEnter
            if fn then fn(n.bt) end
            TS.AddMax(TS, ti, i)
            if fn then fn(n.bt) end
        end
    end
end)

-- 切换主题：classic 分支也要能建
Try("classic 主题切换后重建", function()
    BG.huiTheme = "classic"
    U.built = false
    U.panel = nil
    U.trees = {}
    U.nodes = {}
    U.lines = {}
    U.counters = {}
    U.classBtns = {}
    U.spellBuilt = false
    U.spellRows = {}
    U.spellTabs = {}
    U:Build()
    U:UpdateAll()
    U:SwitchSub("SpellBook")
    U:SwitchSub("Races")
    U:SwitchSub("Legacy")
    U:SwitchSub("SpecTier")
    U:SwitchSub("Talents")
end)
BG.huiTheme = "hui"
-- 重建路径（面板重造）不得把来源条目累加成 4 条
Check("重建后数据来源条目仍为 2 条", #(U.sourceCredits or {}) == 2, #(U.sourceCredits or {}))

-- 命令族
local cmd = SlashCmdList["TALENTSFOREVER"]
Check("已注册 /tf", cmd ~= nil)
if cmd then
    Try("命令 空", cmd, "")
    Try("命令 dump", cmd, "dump")
    Try("命令 code", cmd, "code")
    Try("命令 reset", cmd, "reset")
    Try("命令 icons", cmd, "icons")
    Try("命令 diag", cmd, "diag")
    Try("命令 未知", cmd, "zzz")
    TS.SetClass(TS, "WARRIOR")
    Try("命令 import", cmd, "import " .. TS.Encode(TS, true))
end

-- 弹窗回调
local dlg = StaticPopupDialogs["TALENTSFOREVER_RESET_ALL"]
Check("重置确认弹窗已注册", dlg ~= nil)
if dlg then Try("弹窗 OnAccept", dlg.OnAccept) end
"""


def main():
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(STUB)

    for tag, rel in FILES:
        path = os.path.join(ADDON, rel.replace("/", os.sep))
        try:
            lua.globals().LoadFile(path, tag)
            print("已加载  %-10s  %s" % (tag, rel))
        except Exception as e:
            print("加载失败  %s：%s" % (tag, e))
            return 1

    print("")
    try:
        lua.execute(TEST)
    except Exception as e:
        print("测试脚本异常：%s" % e)
        return 1

    ok = lua.globals().Summary()
    print("\n结论：" + ("全部通过" if ok else "存在失败项"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

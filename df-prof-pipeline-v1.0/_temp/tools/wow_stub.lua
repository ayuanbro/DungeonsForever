
-- ==================== WoW API 桩 ====================
-- GetFrameLevel 不在此表：它按真实累加值返回（见 NewObj / CreateFrame），
-- 否则「某个元素必须画在另一个之上」这类层级问题在桩里恒真，测不出来
local NUMERIC = { GetWidth=1, GetHeight=1, GetVerticalScroll=1, GetScale=1,
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
    sp = true,             -- 法术书列表行当前绑定的法术（隐藏行 row.sp=nil，读它必须得 nil 而不是现造 function）
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
    SetTexture             = function(t) if t ~= nil and type(t) ~= "string" then error("SetTexture：" .. type(t), 3) end end,
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
            elseif k == "SetTexCoord" then
                f = function(self, ...) self.__tc = { ... }; return self end
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
}
GetSpellPowerCost = function(id) return { { cost = 120, name = "法力值", type = 0 } } end
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
C_Timer = { NewTicker = function() return {} end, After = function() end }
UnitClass = function() return "战士", "WARRIOR", 1 end
GetNumTalents = function() return 0 end
debugstack = function() return "stack" end
C_SpecializationInfo = nil -- 默认不可用（模拟真实对比功能取不到数据的分支）

LibStub = {
    -- LibUIDropDownMenu_BiaoGe 已整库删除（2026-10-17 职业下拉框改走 ns.hui.ShowMenu）。
    -- 忠实返回 nil：若插件里还残留 GetLibrary("BiaoGe-LibUIDropDownMenu-4.0") 的调用，
    -- 这里会立刻炸出来（真客户端同样取不到），而不是被桩悄悄兜住。
    GetLibrary = function() return nil end,
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
        -- 菜单桩（与 Core/Hui.lua 的 ShowMenu 同形）：条目落 owner.__menu，供断言读
        ShowMenu = function(items, opts)
            if opts and opts.owner then opts.owner.__menu = items end
            _G.__MENU_ITEMS = items
        end,
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
        -- 圆角胶囊桩（悬停高亮用）：与真实 BuildCapsule 同形，返回贴图表
        BuildCapsule = function(f, cornerSize, color, inset, sub)
            local pieces = {}
            for i = 1, 9 do pieces[i] = f:CreateTexture(nil, "BACKGROUND", nil, sub or 0) end
            return pieces
        end,
        -- ★ 行卡三态桩：与 Core/Hui.lua 的 HuiCardFX / HuiCardState 同形。
        --   真身逻辑：baseN 决定底色档位（L1/L3 或 L2/L4 或 L3/L5 或 L4/L5），
        --   f.__huiCard 记填充/描边件、f.__hov 记悬停胶囊件；非 hui 主题返回 false，
        --   调用方据此退回旧 SetBackdrop 路径（跨版本兼容分支必须能被断言覆盖）。
        HuiCardFX = function(f, hoverR, baseN)
            if BG.huiTheme ~= "hui" then return false end
            local lv = BG.hui.layer
            local base, hov = lv.L1, lv.L3
            if baseN == 2 then base, hov = lv.L2, lv.L4
            elseif baseN == 3 then base, hov = lv.L3, lv.L5
            elseif baseN == 4 then base, hov = lv.L4, lv.L5 end
            if f.SetBackdropColor then f:SetBackdropColor(0, 0, 0, 0) end
            if f.SetBackdropBorderColor then f:SetBackdropBorderColor(0, 0, 0, 0) end
            local fill, border = BG.hui.BuildRoundedBG(f, 6, base, "both", true, 1)
            for _, t in ipairs(fill or {}) do t:SetVertexColor(base[1], base[2], base[3]) end
            for _, t in ipairs(border or {}) do t:SetVertexColor(0.29, 0.32, 0.39) end
            f.__huiCard = { fill = fill, border = border, baseN = baseN }
            if hoverR and BG.hui.BuildCapsule then
                local hp = BG.hui.BuildCapsule(f, 6, hov, 1, 2)
                for _, t in ipairs(hp) do t:SetVertexColor(hov[1], hov[2], hov[3]); t:Hide() end
                f.__hov = hp
            end
            return true
        end,
        HuiCardState = function(f, st)
            local bp = f.__huiCard
            if not bp then return false end
            local showBase = (st ~= "flat")
            if bp.fill then for _, t in ipairs(bp.fill) do t:SetShown(showBase) end end
            if bp.border then for _, t in ipairs(bp.border) do t:SetShown(showBase) end end
            local hov = (st == "hover")
            if f.__hov then for _, t in ipairs(f.__hov) do t:SetShown(hov) end end
            f.__huiState = st
            return true
        end,
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

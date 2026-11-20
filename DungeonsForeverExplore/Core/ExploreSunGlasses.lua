local ns = _G.DF_NS or {}
local L = ns.L
local Host = ns.ProfHost
if not Host then return end

local DG = Host.DG
local MakeFS = Host.MakeFS
local NewButton = Host.NewButton
local C_GOLD, C_GREY, C_DIM, C_WHITE, C_TEXT = Host.C_GOLD, Host.C_GREY, Host.C_DIM, Host.C_WHITE, Host.C_TEXT
local Unpack = Host.Unpack

local FALLBACK_ICON = "Interface\\Icons\\INV_Misc_QuestionMark"

local function SpellTex(sid)
    local t = C_Spell and C_Spell.GetSpellTexture and C_Spell.GetSpellTexture(sid) or nil
    if type(t) ~= "number" and type(t) ~= "string" then return FALLBACK_ICON end
    return t
end

local function Comma(n)
    local s = tostring(math.floor(n))
    local k
    repeat s, k = s:gsub("^(-?%d+)(%d%d%d)", "%1,%2") until k == 0
    return s
end

local H = ns.hui
local LV = (H and H.layer) or {}
local CL2 = LV.L2 or { 0.09, 0.10, 0.13, 1 }
local CL3 = LV.L3 or { 0.13, 0.14, 0.18, 1 }
local C_OK = { 0.56, 0.85, 0.63 }

local ITEM_POTION, ITEM_BAG, ITEM_PATCH, ITEM_FLANGE = 226856, 226697, 226698, 226699
local ITEM_GLASS, ITEM_COM, ITEM_RUNE = 208424, 276782, 226678
local AREA_TANARIS, AREA_WINTER, AREA_BURNING = 440, 618, 46

local LW = 280
local HEAD_Y, HEAD_H, DIV_GAP = 12, 24, 8
local DET_HEAD = 112
local NOTE_ROW_H, NOTE_TOP, NOTE_BOT = 20, 32, 16
local PAD = 8
local ROW_GAP = 8
local SEC_GAP = 22
local CARD_H = 44
local CARD_GAP = 8

local STEPS = {
    {
        no = ns.SYM.n[1], q = 84135, req = 55, title = L["迷滩机器人"],
        area = AREA_TANARIS, x = 59.2, y = 91.5,
        zone = L["塔纳利斯"], where = L["塔纳利斯 · 天涯海滩"],
        from = { name = L["物件「半埋的机甲」"], area = AREA_TANARIS, x = 59.2, y = 91.5 },
        to = { name = L["物件「半埋的机甲」（同点交掉）"], area = AREA_TANARIS, x = 59.2, y = 91.5 },
        rw = { { ITEM_POTION, L["×1 · 可用 3 次"] } },
        lines = {
            L["到地图最右下角的天涯海滩，点地上「半埋的机甲」和「暗门」各一次：第一次只给一段描述，第二次才接到任务。"],
            L["当场交掉接下一环，同时拿到 1 瓶「制导浮力加速器」，可使用 3 次，加快游速，后面游泳全靠它，不然会疲劳。"],
        },
    },
    {
        no = ns.SYM.n[2], q = 84137, req = 55, title = L["机械罗曼史"],
        area = AREA_TANARIS, x = 59.2, y = 99.6,
        zone = L["塔纳利斯"], where = L["海上钻井平台"],
        from = { name = L["物件「半埋的机甲」（原地接）"], area = AREA_TANARIS, x = 59.2, y = 91.5 },
        to = { name = L["塞巴斯蒂安·尤尔根斯"], area = AREA_TANARIS, x = 59.2, y = 99.6 },
        rw = {},
        lines = {
            L["朝正南方的海岛（灯塔方向）游过去，记住游直线不要停，记住喝刚才的药水，岛边就是钻井平台，上平台顶层，找「塞巴斯蒂安·尤尔根斯」交任务。"],
        },
    },
    {
        no = ns.SYM.n[3], q = 84138, req = 55, title = L["冷淡之谊"],
        area = AREA_WINTER, x = 61.2, y = 37.0,
        zone = L["冬泉谷"], where = L["冬泉谷 · 永望镇"],
        from = { name = L["塞巴斯蒂安·尤尔根斯"], area = AREA_TANARIS, x = 59.2, y = 99.6 },
        to = { name = L["努米"], area = AREA_WINTER, x = 61.2, y = 37.0 },
        rw = {},
        lines = {
            L["飞到永望镇，最大那间屋子的台子上找「努米」，交「冷淡之谊」接「红口袋，蓝受心」。"],
            L["接完就直奔燃烧平原。"],
        },
    },
    {
        no = ns.SYM.n[4], q = 84146, req = 55, title = L["红口袋，蓝受心"],
        area = AREA_BURNING, x = 53.0, y = 24.8,
        zone = L["燃烧平原"], where = L["燃烧平原 · 北面偏僻营地"],
        from = { name = L["努米"], area = AREA_WINTER, x = 61.2, y = 37.0 },
        to = { name = L["物件「大红口袋」"], area = AREA_BURNING, x = 53.0, y = 24.8 },
        rw = { { ITEM_BAG, L["16 格容器"] } },
        lines = {
            L["从燃烧平原 59,29 沿着山坡往北走，到 53.0,24.8 的偏僻营地，点地上的「大红口袋」交任务。"],
            L["交完直接拿到「大红口袋」：16 格容器，只要背包的话，做到这一步就可以收工了。"],
        },
    },
    {
        no = ns.SYM.n[5], q = 84211, req = 58, title = L["偷猎者窝点"],
        area = AREA_BURNING, x = 47.0, y = 27.2,
        zone = L["燃烧平原"], where = L["燃烧平原 · 营地周围"],
        from = { name = L["物件「大红口袋」（原地接）"], area = AREA_BURNING, x = 53.0, y = 24.8 },
        to = { name = L["努米"], area = AREA_WINTER, x = 61.2, y = 37.0 },
        rw = { { ITEM_PATCH, L["×5 · 任务用品"] }, { ITEM_FLANGE, L["×5 · 任务用品"] } },
        lines = {
            L["在营地周围杀「黑石私运商」和「萨弗隆私运者」，各拾取 5 个「垂直复合补片加装器」和「黄铜配制耐热法兰」。"],
        },
    },
    {
        no = ns.SYM.n[6], q = 84212, req = 58, title = L["返程长票"],
        zone = L["冬泉谷"], where = L["永望镇 → 钻井平台"],
        from = { name = L["努米"], area = AREA_WINTER, x = 61.2, y = 37.0 },
        to = { name = L["塞巴斯蒂安·尤尔根斯"], area = AREA_TANARIS, x = 59.2, y = 99.6 },
        rw = {},
        lines = {
            L["回永望镇把「偷猎者窝点」交给「努米」，接「返程长票」。"],
            L["再跑回塔纳利斯南边的钻井平台，把「返程长票」交给「塞巴斯蒂安·尤尔根斯」。"],
        },
    },
    {
        no = ns.SYM.n[7], q = 84213, req = 58, title = L["朝来隙往"],
        zone = L["西部荒野 / 提瑞斯法林地"], where = L["西部荒野 / 提瑞斯法林地"],
        from = { name = L["塞巴斯蒂安·尤尔根斯"], area = AREA_TANARIS, x = 59.2, y = 99.6 },
        to = { name = L["机械臂（落地后召唤）"] },
        rw = { { ITEM_GLASS, L["布甲头部"] }, { ITEM_RUNE, L["交任务拾取"] }, { ITEM_COM, L["占武器栏"] } },
        lines = {
            L["跟着「塞巴斯蒂安·尤尔根斯」上二楼，点他修好的机器传送：联盟落到西部荒野，部落落到提瑞斯法林地。"],
            L["用任务物品召唤「麦田傀儡 V000-A」，打完在旁边的「机械臂」处交任务，拿「太阳眼镜」和「预感与战斗远见」。"],
        },
        boss = true,
    },
}

local PHASES = {
    { p = "P1", sid = 426097, at = L["100% → 95%"], title = L["反篡改护盾"], mech = L["打断掉盾"], target = L["两名打断位"],
      line = L["盾在的时候打不动本体，只打断不输出：每次打断掉 2 层护盾，盾全掉再开打。"],
      todo = L["分好两个打断位轮流上，谁空谁补，盾一掉立刻转火本体。"] },
    { p = "P2", sid = 426084, at = L["95% → 75%"], title = L["巨型防护性铁纹 ×4"], mech = L["护甲减伤拉满"], target = L["坦克 + 减速位"],
      line = L["护甲和减伤拉满，正面打不动，要一边跑一边掉层。"],
      todo = L["坦克风筝、其他人跟上减速（断筋 / 寒冰箭 / 震荡射击），4 层掉完再站定输出。"] },
    { p = "P3", sid = 459592, at = L["75% → 60%"], title = L["收割庄稼"], mech = L["群体旋风斩"], target = L["近战 + 坦克"],
      line = L["群体旋风斩，读条时近战和坦克要撤出近身范围。"],
      todo = L["读条一开始就侧移出 8 码，远程在外面继续打；读完再贴回去。"] },
    { p = "P4", sid = 459293, at = L["60% → 25%"], title = L["抓钩与额外伤害"], mech = L["对坦克约 2000"], target = L["坦克"],
      line = L["对当前坦克有一下约 2000 的抓钩伤害，挫志照旧卡着最后一秒补。"],
      todo = L["轮流缴械降伤害，治疗盯住坦克血线，别在抓钩前后断奶。"] },
    { p = "P5", sid = 427143, at = L["25% → 0%"], title = L["狂暴 · 法术易伤"], mech = L["物理抗性高"], target = L["法系"],
      line = L["狂暴之后物理伤害和斩杀压不动，反而吃法术易伤。"],
      todo = L["法系开爆发收尾，坦克开盾墙硬扛，别再指望物理职业拉平。"] },
}

local TIPS = {
    L["药水 1 瓶、能用 3 次：游泳前确认身上有 buff，游直线。"],
    L["「大红口袋」写着「潜行等级提高 2」，实际是降低 2 级，翻译错了，潜行职业谨慎使用。"],
    L["BOSS 只能 5 人队，开团打不了；也不能拉进暴风城或幽暗城。"],
    L["BOSS 大约 30 分钟重置，团灭不回血可以接着打。"],
    L["前四步 55 级可接，后三步要 58 级，两阵营都能做"],
}

local NOS = { ns.SYM.n[1], ns.SYM.n[2], ns.SYM.n[3], ns.SYM.n[4], ns.SYM.n[5] }


local TOTAL_GROUPS = {
    { head = L["必得 · 第⑦步"], items = { { ITEM_GLASS, L["⑦ 布甲头部"] }, { ITEM_RUNE, L["⑦ 拾取"] }, { ITEM_COM, L["⑦ 占武器栏"] } } },
    { head = L["必得 · 第④步"], items = { { ITEM_BAG, L["④ 16 格容器"] } } },
    { head = L["链中必给"], items = { { ITEM_POTION, L["① 1 瓶 · 3 次"] }, { ITEM_PATCH, L["⑤ ×5"] }, { ITEM_FLANGE, L["⑤ ×5"] } } },
}

local function QState(qid)
    if not qid or type(C_QuestLog) ~= "table" then return 0 end
    if C_QuestLog.IsQuestFlaggedCompleted then
        local ok, done = pcall(C_QuestLog.IsQuestFlaggedCompleted, qid)
        if ok and done then return 2 end
    end
    if C_QuestLog.HasQuest then
        local ok, on = pcall(C_QuestLog.HasQuest, qid)
        if ok and on then return 1 end
    end
    return 0
end

local function QName(qid, fallback)
    if qid and type(C_QuestLog) == "table" and C_QuestLog.GetTitleForQuestID then
        local ok, t = pcall(C_QuestLog.GetTitleForQuestID, qid)
        if ok and type(t) == "string" and t ~= "" then return t end
    end
    if qid and DG.QuestLink then
        local ok, lnk = pcall(DG.QuestLink, qid)
        if ok and type(lnk) == "string" then
            local t = lnk:match("|h%[(.-)%]|h")
            if t and t ~= "" then return t end
        end
    end
    return fallback or "?"
end

local function ItemTex(id)
    local tex = DG.ItemIcon(id)
    if type(tex) == "number" then return tex end
    tex = tostring(tex or "")
    if tex:find("\\", 1, true) then return tex end
    if tex == "" then return FALLBACK_ICON end
    return "Interface\\Icons\\" .. tex
end

local function Build(EG, page)
    if EG.sgFrame then return end
    EG.sgSeg = EG.sgSeg or "step"
    EG.sgMode = EG.sgMode or "detail"

    local GUT = (DG and DG.GUTTER) or 8
    local W = EG.RIGHT_W - GUT * 2
    local RWd = W - LW - ROW_GAP
    local AVAIL = RWd - 2 * PAD
    local COLS = 2
    local COL_W = math.floor((AVAIL - (COLS - 1) * CARD_GAP) / COLS)
    local NOTE_H = NOTE_TOP + #TIPS * NOTE_ROW_H + NOTE_BOT

    local root = CreateFrame("Frame", nil, page)
    root:SetPoint("TOPLEFT", page, "TOPLEFT", EG.X0 + GUT, -EG.TOP_EDGE)
    root:SetPoint("BOTTOMRIGHT", page, "BOTTOMRIGHT", -(EG.EDGE + GUT), EG.EDGE + GUT)
    root:Hide()
    EG.sgFrame = root

    local function Skin(f, base, rad)
        if H and H.SkinPopup then
            H.SkinPopup(f, rad or 8, nil, base)
        elseif f.SetBackdrop then
            f:SetBackdrop({
                bgFile = "Interface\\Buttons\\WHITE8x8",
                edgeFile = "Interface\\Buttons\\WHITE8x8",
                edgeSize = 1,
            })
            f:SetBackdropColor(base[1], base[2], base[3], base[4] or 1)
            f:SetBackdropBorderColor(1, 1, 1, 0.08)
        end
    end

    local title = MakeFS(root, 16, C_WHITE, "LEFT")
    title:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -HEAD_Y - (HEAD_H - 16) / 2)
    title:SetText(L["太阳眼镜"])
    title:SetWordWrap(false)
    local tw = title.GetStringWidth and title:GetStringWidth() or 0
    if type(tw) ~= "number" or tw <= 0 then tw = 64 end

    local segStep = NewButton(root, L["任务步骤"], 88, HEAD_H, 14)
    segStep:SetPoint("TOPLEFT", root, "TOPLEFT", math.floor(tw + 14), -HEAD_Y)
    segStep.__huiKeepTextColor = true
    do
        local f = segStep:GetFontString()
        f:SetJustifyH("CENTER")
    end
    local segBoss = NewButton(root, L["首领机制"], 88, HEAD_H, 14)
    segBoss:SetPoint("TOPLEFT", root, "TOPLEFT", math.floor(tw + 14) + 96, -HEAD_Y)
    segBoss.__huiKeepTextColor = true
    do
        local f = segBoss:GetFontString()
        f:SetJustifyH("CENTER")
    end
    segStep:SetScript("OnClick", function()
        EG.sgSeg = "step"
        EG.sgMode = "detail"
        if EG.sgScroll then EG.sgScroll:SetVerticalScroll(0) end
        ns.ExploreSunGlassesPaint(EG)
        ns.ExploreSunGlassesLayout(EG)
        ns.PlaySound(1)
    end)
    segBoss:SetScript("OnClick", function()
        EG.sgSeg = "boss"
        EG.sgMode = "detail"
        EG.sgPhase = EG.sgPhase or 1
        if EG.sgScroll then EG.sgScroll:SetVerticalScroll(0) end
        ns.ExploreSunGlassesPaint(EG)
        ns.ExploreSunGlassesLayout(EG)
        ns.PlaySound(1)
    end)
    EG.sgSegBtns = { step = segStep, boss = segBoss }

    local rwBtn = CreateFrame("Button", nil, root, "BackdropTemplate")
    rwBtn:SetSize(150, HEAD_H)
    rwBtn:SetPoint("TOPRIGHT", root, "TOPRIGHT", 0, -HEAD_Y)
    rwBtn.__huiKeepTextColor = true
    if H and H.SkinButton then H.SkinButton(rwBtn) end
    local rf = MakeFS(rwBtn, 14, C_GOLD, "CENTER")
    rf:SetAllPoints()
    rf:SetText(L["任务线奖励总览"])
    rf:SetWordWrap(false)
    rwBtn:SetFontString(rf)
    local chev = rwBtn:CreateTexture(nil, "OVERLAY")
    chev:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Common\\BackChevron.tga")
    chev:SetTexCoord(1, 0, 0, 1)
    chev:SetSize(9, 9)
    chev:SetPoint("RIGHT", rwBtn, "RIGHT", -6, 0)
    chev:SetVertexColor(Unpack(C_GOLD))
    rwBtn:SetScript("OnClick", function()
        EG.sgMode = (EG.sgMode == "total") and "detail" or "total"
        if EG.sgTScroll then EG.sgTScroll:SetVerticalScroll(0) end
        if EG.sgScroll then EG.sgScroll:SetVerticalScroll(0) end
        ns.ExploreSunGlassesPaint(EG)
        ns.PlaySound(1)
    end)
    EG.sgRwBtn = rwBtn

    local prog = MakeFS(root, 14, C_GOLD, "RIGHT")
    prog:SetPoint("TOPRIGHT", rwBtn, "TOPLEFT", -8, 0)
    prog:SetWordWrap(false)
    EG.sgProg = prog

    local headRule = root:CreateTexture(nil, "OVERLAY")
    headRule:SetColorTexture(0.11, 0.13, 0.16, 1)
    headRule:SetHeight(1)
    headRule:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -(HEAD_Y + HEAD_H + DIV_GAP))
    headRule:SetPoint("TOPRIGHT", root, "TOPRIGHT", 0, -(HEAD_Y + HEAD_H + DIV_GAP))
    local BODY_Y = HEAD_Y + HEAD_H + DIV_GAP + 1 + DIV_GAP

    local function SpellTip(owner, sid)
        if not owner or not sid or not GameTooltip then return end
        GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
        if GameTooltip.SetSpellByID then
            GameTooltip:SetSpellByID(sid)
        else
            local n = C_Spell and C_Spell.GetSpellInfo and C_Spell.GetSpellInfo(sid)
            local nm = type(n) == "table" and n.name or n
            GameTooltip:ClearLines()
            GameTooltip:AddLine(nm or "?", 1, 1, 1, false)
        end
        GameTooltip:Show()
    end

    local function MakeSpellIcon(par, size)
        local b = CreateFrame("Button", nil, par)
        b:SetSize(size, size)
        local t = b:CreateTexture(nil, "ARTWORK")
        t:SetAllPoints()
        t:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        b.__tex = t
        b:SetScript("OnEnter", function(self)
            if self.__sid then SpellTip(self, self.__sid) end
        end)
        b:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
        b:Hide()
        return b
    end

    local lc = CreateFrame("Frame", nil, root)
    lc:SetPoint("TOPLEFT", root, "TOPLEFT", 0, -BODY_Y)
    lc:SetPoint("BOTTOMRIGHT", root, "BOTTOMRIGHT", -(RWd + ROW_GAP), NOTE_H + ROW_GAP)
    EG.sgLC = lc

    local rows = {}
    for i = 1, #STEPS do
        local r = CreateFrame("Button", nil, lc, "BackdropTemplate")
        r:SetHeight(40)
        if H and H.BuildRoundedBG then
            r:SetBackdropColor(0, 0, 0, 0)
            r:SetBackdropBorderColor(0, 0, 0, 0)
            H.BuildRoundedBG(r, 10, CL2, "both", true, 1)
            r.__huiCard = true
            if H.BuildCapsule then
                r.__hov = H.BuildCapsule(r, 10, LV.L4, 1, 2)
                for _, t in ipairs(r.__hov) do t:Hide() end
            end
        else
            r:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8" })
            r:SetBackdropColor(1, 1, 1, 0.03)
        end
        r.tint = r:CreateTexture(nil, "BORDER")
        r.tint:SetAllPoints()
        r.tint:SetColorTexture(1, 1, 1, 0)

        r.si = MakeSpellIcon(r, 28)
        r.si:SetPoint("LEFT", r, "LEFT", 8, 0)
        r.si:EnableMouse(false)
        r.no = MakeFS(r, 16, C_GOLD, "LEFT")
        r.no:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -6)
        r.no:SetWordWrap(false)
        r.t = MakeFS(r, 16, C_TEXT, "LEFT")
        r.t:SetPoint("TOPLEFT", r, "TOPLEFT", 32, -6)
        r.t:SetPoint("RIGHT", r, "RIGHT", -70, 0)
        r.t:SetWordWrap(false)
        r.p = MakeFS(r, 14, C_GREY, "LEFT")
        r.p:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 32, 6)
        r.p:SetPoint("RIGHT", r, "RIGHT", -70, 0)
        r.p:SetWordWrap(false)
        r.st = MakeFS(r, 14, C_GREY, "RIGHT")
        r.st:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -8, 6)
        r.st:SetWordWrap(false)

        r:SetScript("OnClick", function(self)
            if self.__phase then
                EG.sgSeg = "boss"
                EG.sgPhase = self.__idx
            else
                EG.sgSeg = "step"
                EG.sgSel = self.__idx
            end
            EG.sgMode = "detail"
            if EG.sgScroll then EG.sgScroll:SetVerticalScroll(0) end
            ns.ExploreSunGlassesPaint(EG)
            ns.PlaySound(1)
        end)
        r:SetScript("OnEnter", function(self)
            if self.__hov then for _, t in ipairs(self.__hov) do t:Show() end end
            if self.__phase and self.__sid then SpellTip(self, self.__sid) end
        end)
        r:SetScript("OnLeave", function(self)
            if self.__hov then for _, t in ipairs(self.__hov) do t:Hide() end end
            if self.__phase and GameTooltip then GameTooltip:Hide() end
        end)
        rows[i] = r
    end
    EG.sgRows = rows

    local function MakeBar(sc, ch)
        local track = CreateFrame("Frame", nil, sc, "BackdropTemplate")
        if H and H.BuildCapsule then
            H.BuildCapsule(track, 3, LV.L2)
        else
            track:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                                edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
            track:SetBackdropColor(0, 0, 0, 0.25)
            track:SetBackdropBorderColor(1, 1, 1, 0.08)
        end
        track:SetWidth(7)
        track:SetPoint("TOPRIGHT", sc, "TOPRIGHT", -1, -2)
        track:SetPoint("BOTTOMRIGHT", sc, "BOTTOMRIGHT", -1, 2)
        track:SetFrameLevel((sc:GetFrameLevel() or 0) + 10)
        track:Hide()

        local thumb = CreateFrame("Button", nil, track)
        thumb:SetWidth(5)
        local tp
        if H and H.BuildCapsule then tp = H.BuildCapsule(thumb, 2, LV.L4) end
        thumb:SetPoint("TOP", track, "TOP", 0, -1)
        thumb:SetScript("OnEnter", function()
            if tp then
                local c = LV.L5
                for _, t in ipairs(tp) do t:SetVertexColor(c[1], c[2], c[3]) end
            end
        end)
        thumb:SetScript("OnLeave", function()
            if tp then
                local c = LV.L4
                for _, t in ipairs(tp) do t:SetVertexColor(c[1], c[2], c[3]) end
            end
        end)

        local function update()
            if not sc:IsShown() then track:Hide() return end
            local viewH = sc:GetHeight()
            local contentH = ch:GetHeight()
            if type(viewH) ~= "number" or type(contentH) ~= "number" then track:Hide() return end
            if contentH <= viewH + 2 or viewH <= 0 then track:Hide() return end
            track:Show()
            local trackH = track:GetHeight() - 2
            if type(trackH) ~= "number" or trackH <= 0 then track:Hide() return end
            local maxScroll = contentH - viewH
            local vpos = sc:GetVerticalScroll()
            if type(vpos) ~= "number" then vpos = 0 end
            if vpos > maxScroll then
                pcall(sc.SetVerticalScroll, sc, maxScroll)
                vpos = maxScroll
            end
            if maxScroll <= 0 then maxScroll = 1 end
            local frac = math.min(1, math.max(0, vpos / maxScroll))
            local th = math.max(24, trackH * viewH / contentH)
            thumb:SetHeight(th)
            thumb:ClearAllPoints()
            thumb:SetPoint("TOP", track, "TOP", 0, -1 - frac * (trackH - th))
        end

        sc:SetScript("OnVerticalScroll", function() update() end)
        thumb:SetScript("OnMouseDown", function(self, btn)
            if btn ~= "LeftButton" then return end
            local scale = UIParent and UIParent:GetEffectiveScale() or 1
            if type(scale) ~= "number" or scale <= 0 then scale = 1 end
            local cy0 = select(2, GetCursorPosition()) / scale
            local s0 = sc:GetVerticalScroll()
            if type(s0) ~= "number" then s0 = 0 end
            self:SetScript("OnUpdate", function()
                local cy = select(2, GetCursorPosition()) / scale
                local span = (track:GetHeight() or 0) - (thumb:GetHeight() or 0) - 2
                if span <= 0 then return end
                local maxScroll = (ch:GetHeight() or 0) - (sc:GetHeight() or 0)
                if maxScroll <= 0 then return end
                sc:SetVerticalScroll(math.min(maxScroll, math.max(0, s0 + (cy0 - cy) / span * maxScroll)))
            end)
        end)
        thumb:SetScript("OnMouseUp", function(self)
            self:SetScript("OnUpdate", nil)
            update()
        end)
        thumb:SetScript("OnHide", function(self) self:SetScript("OnUpdate", nil) end)
        return update
    end

    local det = CreateFrame("Frame", nil, root)
    det:SetPoint("TOPLEFT", root, "TOPLEFT", LW + ROW_GAP, -BODY_Y)
    det:SetPoint("BOTTOMRIGHT", root, "BOTTOMRIGHT", 0, NOTE_H + ROW_GAP)
    Skin(det, CL2, 8)
    det:EnableMouseWheel(true)
    EG.sgDet = det

    local dTitle = MakeFS(det, 16, C_WHITE, "LEFT")
    dTitle:SetPoint("TOPLEFT", det, "TOPLEFT", PAD, -8)
    dTitle:SetWordWrap(false)
    EG.sgDTitle = dTitle
    local dIcon = MakeSpellIcon(det, 24)
    dIcon:SetPoint("TOPLEFT", det, "TOPLEFT", PAD, -5)
    EG.sgDIcon = dIcon
    local dTitleBtn = CreateFrame("Button", nil, det)
    dTitleBtn:SetHeight(20)
    dTitleBtn:SetPoint("TOPLEFT", dTitle, "TOPLEFT", -2, 2)
    dTitleBtn:SetScript("OnEnter", function(self)
        if self.__sid then SpellTip(self, self.__sid) end
    end)
    dTitleBtn:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
    dTitleBtn:Hide()
    EG.sgDTitleBtn = dTitleBtn
    local dTag = MakeFS(det, 14, C_GREY, "LEFT")
    dTag:SetPoint("LEFT", dTitle, "RIGHT", 8, 0)
    dTag:SetWordWrap(false)
    EG.sgDTag = dTag

    local function MakePin(par)
        local b = CreateFrame("Button", nil, par, "BackdropTemplate")
        b:SetHeight(24)
        b:SetPushedTextOffset(0, 0)
        local bf = MakeFS(b, 14, C_TEXT, "CENTER")
        b:SetFontString(bf)
        bf:SetText(L["地图"])
        local bw = bf.GetStringWidth and bf:GetStringWidth() or 0
        if type(bw) ~= "number" or bw <= 0 then bw = 28 end
        b:SetWidth(math.floor(PAD + 10.4 + 6 + bw + 7 + 0.5))
        if H and H.SkinButton then H.SkinButton(b) end
        local br = b:CreateTexture(nil, "OVERLAY")
        br:SetSize(10.4, 15)
        br:SetPoint("LEFT", b, "LEFT", PAD, 0)
        br:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Pins\\EntryPin")
        br:SetTexCoord(14 / 64, 50 / 64, 9 / 64, 61 / 64)
        bf:ClearAllPoints()
        bf:SetPoint("LEFT", br, "RIGHT", 6, 0)
        b:SetScript("OnClick", function(self)
            local lc2 = self.__loc
            if lc2 then EG.MarkPoint(lc2[1], lc2[2], lc2[3]) end
            ns.PlaySound(1)
        end)
        b:SetScript("OnEnter", function(self)
            if not GameTooltip then return end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            local lc2 = self.__loc
            if lc2 then GameTooltip:AddLine(format("%.1f, %.1f", lc2[2], lc2[3]), 1, 0.82, 0.24, false) end
            GameTooltip:AddLine(L["点击在世界地图上定位"], 0.8, 0.8, 0.8, true)
            GameTooltip:Show()
        end)
        b:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
        b:Hide()
        return b
    end

    local dCo = MakeFS(det, 14, C_GOLD, "RIGHT")
    dCo:SetPoint("TOPRIGHT", det, "TOPRIGHT", -PAD, -10)
    dCo:SetWordWrap(false)
    EG.sgDCo = dCo

    local head = {}
    for i = 1, 3 do
        local lab = MakeFS(det, 14, C_GREY, "LEFT")
        lab:SetWordWrap(false)
        local val = MakeFS(det, 14, C_TEXT, "LEFT")
        val:SetWordWrap(false)
        head[i] = { lab = lab, val = val }
    end
    head.a = { lab = MakeFS(det, 14, C_GREY, "LEFT"), val = MakeFS(det, 14, C_GOLD, "LEFT"), btn = MakePin(det) }
    head.b = { lab = MakeFS(det, 14, C_GREY, "LEFT"), val = MakeFS(det, 14, C_GOLD, "LEFT"), btn = MakePin(det) }
    head.a.lab:SetWordWrap(false)
    head.a.val:SetWordWrap(false)
    head.b.lab:SetWordWrap(false)
    head.b.val:SetWordWrap(false)
    EG.sgHead = head

    local rs = CreateFrame("ScrollFrame", nil, det)
    if rs.SetClipsChildren then rs:SetClipsChildren(true) end
    rs:EnableMouseWheel(true)
    rs:SetPoint("TOPLEFT", det, "TOPLEFT", 0, -DET_HEAD)
    rs:SetPoint("BOTTOMRIGHT", det, "BOTTOMRIGHT", 0, 0)
    local rc = CreateFrame("Frame", nil, rs)
    rc:SetSize(RWd, 10)
    rs:SetScrollChild(rc)
    EG.sgScroll, EG.sgChild = rs, rc
    local sgb = MakeBar(rs, rc)
    rs:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(rs, rc, delta)
        if sgb then sgb() end
    end)
    det:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(rs, rc, delta)
        if sgb then sgb() end
    end)

    local tot = CreateFrame("Frame", nil, root)
    tot:SetPoint("TOPLEFT", root, "TOPLEFT", LW + ROW_GAP, -BODY_Y)
    tot:SetPoint("BOTTOMRIGHT", root, "BOTTOMRIGHT", 0, NOTE_H + ROW_GAP)
    Skin(tot, CL2, 8)
    tot:EnableMouseWheel(true)
    tot:Hide()
    EG.sgTot = tot

    local tTitle = MakeFS(tot, 16, C_WHITE, "LEFT")
    tTitle:SetPoint("TOPLEFT", tot, "TOPLEFT", PAD, -8)
    tTitle:SetText(L["任务线奖励总览"])
    tTitle:SetWordWrap(false)

    local ts = CreateFrame("ScrollFrame", nil, tot)
    if ts.SetClipsChildren then ts:SetClipsChildren(true) end
    ts:EnableMouseWheel(true)
    ts:SetPoint("TOPLEFT", tot, "TOPLEFT", 0, -32)
    ts:SetPoint("BOTTOMRIGHT", tot, "BOTTOMRIGHT", 0, 0)
    local tc = CreateFrame("Frame", nil, ts)
    tc:SetSize(RWd, 10)
    ts:SetScrollChild(tc)
    EG.sgTScroll, EG.sgTChild = ts, tc
    local tgb = MakeBar(ts, tc)
    ts:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(ts, tc, delta)
        if tgb then tgb() end
    end)
    tot:SetScript("OnMouseWheel", function(_, delta)
        DG.WheelScroll(ts, tc, delta)
        if tgb then tgb() end
    end)
    EG.sgTBar = tgb

    local tHeads = {}
    for i = 1, #TOTAL_GROUPS do
        local f = MakeFS(tc, 16, C_GOLD, "LEFT")
        f:SetText(TOTAL_GROUPS[i].head)
        f:SetWordWrap(false)
        tHeads[i] = f
    end
    EG.sgTHeads = tHeads

    local function MakeCard(parent)
        local c = CreateFrame("Button", nil, parent, "BackdropTemplate")
        c:SetSize(COL_W, CARD_H)
        if H and H.BuildRoundedBG then
            c:SetBackdropColor(0, 0, 0, 0)
            c:SetBackdropBorderColor(0, 0, 0, 0)
            H.BuildRoundedBG(c, 6, CL3, "both", true, 1)
            c.__huiCard = true
            if H.BuildCapsule then
                c.__hov = H.BuildCapsule(c, 6, LV.L4, 1, 2)
                for _, t in ipairs(c.__hov) do t:Hide() end
            end
        else
            c:SetBackdrop({ bgFile = "Interface\\Buttons\\WHITE8x8",
                            edgeFile = "Interface\\Buttons\\WHITE8x8", edgeSize = 1 })
            c:SetBackdropColor(1, 1, 1, 0.05)
            c:SetBackdropBorderColor(1, 1, 1, 0.12)
        end
        c.icon = c:CreateTexture(nil, "ARTWORK")
        c.icon:SetSize(32, 32)
        c.icon:SetTexCoord(0.07, 0.93, 0.07, 0.93)
        if H and H.RoundIcon then H.RoundIcon(c.icon) end
        c.icon:SetPoint("LEFT", c, "LEFT", 6, 0)
        c.nm = MakeFS(c, 14, C_TEXT, "LEFT")
        c.nm:SetPoint("TOPLEFT", c, "TOPLEFT", 46, -6)
        c.nm:SetWidth(COL_W - 52)
        c.nm:SetWordWrap(false)
        c.sb = MakeFS(c, 12, C_GREY, "LEFT")
        c.sb:SetPoint("TOPLEFT", c, "TOPLEFT", 46, -26)
        c.sb:SetWidth(COL_W - 52)
        c.sb:SetWordWrap(false)
        c:SetScript("OnEnter", function(self)
            if self.__hov then for _, t in ipairs(self.__hov) do t:Show() end end
            if self.__id then DG.ShowItemTip(self, { self.__id }) end
        end)
        c:SetScript("OnLeave", function(self)
            if self.__hov then for _, t in ipairs(self.__hov) do t:Hide() end end
            if GameTooltip then GameTooltip:Hide() end
        end)
        c:SetScript("OnClick", function(self, button)
            if DG.ItemShiftClick then DG.ItemShiftClick(self, button) end
        end)
        c:Hide()
        return c
    end

    local cards = {}
    for i = 1, 24 do cards[i] = MakeCard(rc) end
    local tCards = {}
    for i = 1, 14 do tCards[i] = MakeCard(tc) end

    local heads = {}
    for i = 1, 10 do
        local f = MakeFS(rc, 16, C_GOLD, "LEFT")
        f:SetWordWrap(false)
        f:Hide()
        heads[i] = f
    end

    local segs = {}
    for i = 1, 60 do
        local f = MakeFS(rc, 14, C_TEXT, "LEFT")
        f:SetJustifyV("TOP")
        f:Hide()
        segs[i] = f
    end

    local pins = {}
    for i = 1, 8 do
        local b = CreateFrame("Button", nil, rc, "BackdropTemplate")
        b:SetHeight(20)
        b:SetPushedTextOffset(0, 0)
        local bf = MakeFS(b, 12, C_TEXT, "CENTER")
        b:SetFontString(bf)
        bf:SetText(L["地图"])
        local bw = bf.GetStringWidth and bf:GetStringWidth() or 0
        if type(bw) ~= "number" or bw <= 0 then bw = 24 end
        b:SetWidth(math.floor(12 + bw + 4))
        if H and H.SkinButton then H.SkinButton(b) end
        local br = b:CreateTexture(nil, "OVERLAY")
        br:SetSize(7, 10)
        br:SetPoint("LEFT", b, "LEFT", 4, 0)
        br:SetTexture("Interface\\AddOns\\DungeonsForever\\Media\\Pins\\EntryPin")
        br:SetTexCoord(14 / 64, 50 / 64, 9 / 64, 61 / 64)
        bf:ClearAllPoints()
        bf:SetPoint("LEFT", br, "RIGHT", 4, 0)
        b:SetScript("OnClick", function(self)
            local lc2 = self.__loc
            if lc2 then EG.MarkPoint(lc2[1], lc2[2], lc2[3]) end
            ns.PlaySound(1)
        end)
        b:SetScript("OnEnter", function(self)
            if not GameTooltip then return end
            GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            local lc2 = self.__loc
            if lc2 then GameTooltip:AddLine(format("%.1f, %.1f", lc2[2], lc2[3]), 1, 0.82, 0.24, false) end
            GameTooltip:AddLine(L["点击在世界地图上定位"], 0.8, 0.8, 0.8, true)
            GameTooltip:Show()
        end)
        b:SetScript("OnLeave", function() if GameTooltip then GameTooltip:Hide() end end)
        b:Hide()
        pins[i] = b
    end

    local noteRule = root:CreateTexture(nil, "OVERLAY")
    noteRule:SetColorTexture(1, 1, 1, 0.09)
    noteRule:SetHeight(1)
    noteRule:SetPoint("BOTTOMLEFT", root, "BOTTOMLEFT", 0, NOTE_H)
    noteRule:SetPoint("BOTTOMRIGHT", root, "BOTTOMRIGHT", 0, NOTE_H)

    local nHead = MakeFS(root, 16, C_GOLD, "LEFT")
    nHead:SetPoint("BOTTOMLEFT", root, "BOTTOMLEFT", 0, NOTE_H - 8 - 16)
    nHead:SetText(L["注意事项"])
    nHead:SetWordWrap(false)
    local nHint = MakeFS(root, 14, C_GREY, "RIGHT")
    nHint:SetPoint("BOTTOMRIGHT", root, "BOTTOMRIGHT", 0, NOTE_H - 9 - 14)
    nHint:SetText(L["无阵营限制 · 55 / 58 级"])
    nHint:SetWordWrap(false)

    for i = 1, #TIPS do
        local y = NOTE_H - NOTE_TOP - (i - 1) * NOTE_ROW_H - 14
        local n = MakeFS(root, 14, C_GOLD, "LEFT")
        n:SetPoint("BOTTOMLEFT", root, "BOTTOMLEFT", 0, y)
        n:SetText(NOS[i] or "")
        n:SetWordWrap(false)
        local t = MakeFS(root, 14, C_GREY, "LEFT")
        t:SetPoint("BOTTOMLEFT", root, "BOTTOMLEFT", 20, y)
        t:SetWidth(W - 20)
        t:SetWordWrap(false)
        t:SetText(TIPS[i])
    end

    local cursor = 0
    local hi, si, pi, ci = 0, 0, 0, 0

    local function Park()
        for _, f in ipairs(heads) do f:Hide() end
        for _, f in ipairs(segs) do f:Hide() end
        for _, b in ipairs(pins) do b:Hide() end
        for _, c in ipairs(cards) do c:Hide() end
        hi, si, pi, ci = 0, 0, 0, 0
    end

    local function Head(txt)
        hi = hi + 1
        local f = heads[hi]
        if not f then return end
        f:ClearAllPoints()
        f:SetPoint("TOPLEFT", rc, "TOPLEFT", PAD, -cursor)
        f:SetText(txt)
        f:Show()
        cursor = cursor + SEC_GAP
    end

    local function Flow(list, y)
        local n = 0
        for _, it in ipairs(list) do
            ci = ci + 1
            local c = cards[ci]
            if not c then break end
            local id = it[1]
            c.__id = id
            c.icon:SetTexture(ItemTex(id))
            local q = DG.QualOf(id)
            if q and H and H.SetIconRing then H.SetIconRing(c.icon, { DG.QColor(q) }) end
            local nm = DG.ItemName(id)
            if not nm then
                DG.RequestItem(id, true)
                EG.sgNeedNames = true
            end
            c.nm:SetText(nm or "?")
            c.nm:SetTextColor(Unpack(nm and C_TEXT or C_DIM))
            c.sb:SetText(it[2] or "")
            local col = n % COLS
            local row = math.floor(n / COLS)
            c:ClearAllPoints()
            c:SetPoint("TOPLEFT", rc, "TOPLEFT", PAD + col * (COL_W + CARD_GAP), -(y + row * (CARD_H + CARD_GAP)))
            c:Show()
            n = n + 1
        end
        return y + math.ceil(n / COLS) * (CARD_H + CARD_GAP)
    end

    local function Text(text, color, wrap, x, w)
        si = si + 1
        local f = segs[si]
        if not f then return 0 end
        f:ClearAllPoints()
        f:SetPoint("TOPLEFT", rc, "TOPLEFT", x, -cursor)
        if wrap then
            f:SetWidth(math.max(40, AVAIL - (x - PAD)))
            f:SetWordWrap(true)
        else
            f:SetWidth(w or math.max(40, AVAIL - (x - PAD)))
            f:SetWordWrap(false)
        end
        f:SetTextColor(Unpack(color))
        f:SetText(text)
        local h = 20
        if wrap then
            local gh = f.GetStringHeight and f:GetStringHeight() or 0
            if type(gh) == "number" and gh > 0 then h = gh end
        end
        f:Show()
        cursor = cursor + h + 4
        return h
    end

    local function FSW(f)
        local w = f.GetStringWidth and f:GetStringWidth() or 0
        if type(w) ~= "number" or w <= 0 then w = #tostring(f.GetText and f:GetText() or "") * 14 end
        return w
    end

    local function PlaceKV(t, x, y)
        t.lab:ClearAllPoints()
        t.lab:SetPoint("TOPLEFT", det, "TOPLEFT", math.floor(x), -y)
        t.val:ClearAllPoints()
        t.val:SetPoint("LEFT", t.lab, "RIGHT", 2, 0)
    end

    local function LayoutHead()
        local w1 = FSW(head[1].lab) + 2 + FSW(head[1].val)
        local w2 = FSW(head[2].lab) + 2 + FSW(head[2].val)
        local x2 = PAD + w1 + 20
        local x3 = x2 + w2 + 20
        local right = RWd - PAD
        if x3 > right - 80 then x3 = right - 80 end
        if x2 > x3 - 64 then x2 = x3 - 64 end
        PlaceKV(head[1], PAD, 34)
        PlaceKV(head[2], x2, 34)
        PlaceKV(head[3], x3, 34)
        for _, k in ipairs({ "a", "b" }) do
            local t = head[k]
            local y = (k == "a") and 58 or 82
            PlaceKV(t, PAD, y)
            local lw = FSW(t.lab)
            local bw = t.btn and (t.btn:GetWidth() or 60) or 0
            local full = RWd - 2 * PAD - lw - 2
            if t.btn and t.btn:IsShown() then
                t.btn:ClearAllPoints()
                t.btn:SetPoint("TOPRIGHT", det, "TOPRIGHT", -PAD, -(y - 5))
                local useW = full - bw - 10
                if useW < 20 then useW = 20 end
                t.val:SetWidth(useW)
            else
                t.val:SetWidth(full)
            end
        end
    end

    local function PaintStep(i)
        local st = STEPS[i] or STEPS[1]
        local qid = st.q
        EG.sgDIcon:Hide()
        EG.sgDTitleBtn:Hide()
        EG.sgDTitle:ClearAllPoints()
        EG.sgDTitle:SetPoint("TOPLEFT", EG.sgDet, "TOPLEFT", PAD, -8)
        EG.sgDTitle:SetText(QName(qid, st.title))
        EG.sgDTag:SetText(qid and ("#" .. qid) or "")
        EG.sgDCo:SetText("")

        local s = QState(qid)
        local stateTxt, scol = L["未完成"], C_GREY
        if s == 2 then
            stateTxt, scol = L["已完成"], C_OK
        elseif s == 1 then
            stateTxt, scol = L["已接取"], C_GOLD
        end
        head[1].lab:SetText(L["可接等级："])
        head[1].val:SetText(format(L["%d 级可接"], st.req))
        head[1].val:SetTextColor(Unpack(C_TEXT))
        head[2].lab:SetText(L["区域："])
        head[2].val:SetText(st.zone or "")
        head[3].lab:SetText(L["状态："])
        head[3].val:SetText(stateTxt)
        head[3].val:SetTextColor(Unpack(scol))
        for _, k in ipairs({ "a", "b" }) do
            local t = head[k]
            local side = (k == "a") and st.from or st.to
            t.lab:SetText((k == "a") and L["起始："] or L["结束："])
            t.lab:Show()
            t.val:SetText(side.name)
            t.val:Show()
            t.btn.__loc = side.x and { side.area, side.x, side.y } or nil
            t.btn:SetShown(side.x ~= nil)
        end
        LayoutHead()

        cursor = 0
        Park()
        if st.rw and #st.rw > 0 then
            Head(L["本步奖励"])
            cursor = Flow(st.rw, cursor)
            cursor = cursor + 8
        end
        Head(L["收获"])
        local xp = qid and DG.QuestRewardXP and DG.QuestRewardXP(qid) or nil
        if type(xp) == "number" and xp > 0 then
            Text(format(L["%s 经验"], Comma(xp)), C_TEXT, false, PAD)
        else
            Text("—", C_TEXT, false, PAD)
        end
        cursor = cursor + 2
        Head(L["走法"])
        for _, ln in ipairs(st.lines) do Text(ln, C_TEXT, true, PAD) end
        cursor = cursor + 4
        if st.boss then
            Head(L["战斗 · 麦田傀儡 V000-A"])
            for _, ph in ipairs(PHASES) do
                Text(format("|cffffd100%s|r  %s  %s", ph.p, ph.title, ph.at), C_TEXT, false, PAD, AVAIL)
                local y0 = cursor
                Text(ph.todo, C_GREY, true, PAD + 16)
                if cursor <= y0 then cursor = y0 + 20 end
                cursor = cursor + 2
            end
        end
        rc:SetHeight(math.max(cursor + 8, 1))
        if sgb then sgb() end
    end

    local function PaintPhase(i)
        local ph = PHASES[i] or PHASES[1]
        EG.sgDTitle:ClearAllPoints()
        EG.sgDTitle:SetPoint("TOPLEFT", EG.sgDet, "TOPLEFT", PAD + 32, -8)
        EG.sgDTitle:SetText(ph.title)
        EG.sgDIcon.__sid = ph.sid
        EG.sgDIcon.__tex:SetTexture(SpellTex(ph.sid))
        EG.sgDIcon:Show()
        EG.sgDTitleBtn.__sid = ph.sid
        EG.sgDTitleBtn:SetWidth(math.max(24, (EG.sgDTitle:GetStringWidth() or 0) + 4))
        EG.sgDTitleBtn:Show()
        EG.sgDTag:SetText(ph.p)
        EG.sgDCo:SetText(ph.at)

        head[1].lab:SetText(L["阶段："])
        head[1].val:SetText(format(L["%s · 第 %d 阶段"], ph.p, i))
        head[1].val:SetTextColor(Unpack(C_TEXT))
        head[2].lab:SetText(L["血量："])
        head[2].val:SetText(ph.at)
        head[3].lab:SetText(L["机制："])
        head[3].val:SetText(ph.mech)
        head.a.lab:SetText(L["对象："])
        head.a.lab:Show()
        head.a.val:SetText(ph.target)
        head.a.val:SetTextColor(Unpack(C_TEXT))
        head.a.val:Show()
        head.a.btn.__loc = nil
        head.a.btn:Hide()
        head.b.lab:Hide()
        head.b.val:Hide()
        head.b.btn:Hide()
        LayoutHead()

        cursor = 0
        Park()
        Head(L["机制说明"])
        Text(ph.line, C_TEXT, true, PAD)
        cursor = cursor + 4
        Head(L["应对"])
        Text(ph.todo, C_TEXT, true, PAD)
        cursor = cursor + 4
        Head(L["全链要点"])
        Text(L["整场只有两件事不能断：挫志和雷霆。挫志会给他叠一个不能刷新的减攻强 debuff，必须等它跳完的瞬间补上，不然容易直接倒 T。"], C_GREY, true, PAD)
        Text(L["队伍至少 1 坦 1 奶，剩下的位置带法系。坦克穿输出装拿盾就能扛，25% 之后有法术易伤，带个法系会快很多。"], C_GREY, true, PAD)
        rc:SetHeight(math.max(cursor + 8, 1))
        if sgb then sgb() end
    end

    local function PaintTotal()
        ci = 0
        local y = 8
        for gi, g in ipairs(TOTAL_GROUPS) do
            local f = tHeads[gi]
            if f then
                f:ClearAllPoints()
                f:SetPoint("TOPLEFT", tc, "TOPLEFT", PAD, -y)
                f:Show()
            end
            y = y + SEC_GAP
            local n = 0
            for _, it in ipairs(g.items) do
                ci = ci + 1
                local c = tCards[ci]
                if not c then break end
                local iid = it[1]
                c.__id = iid
                c.icon:SetTexture(ItemTex(iid))
                local qq = DG.QualOf(iid)
                if qq and H and H.SetIconRing then H.SetIconRing(c.icon, { DG.QColor(qq) }) end
                local nm2 = DG.ItemName(iid)
                if not nm2 then
                    DG.RequestItem(iid, true)
                    EG.sgNeedNames = true
                end
                c.nm:SetText(nm2 or "?")
                c.nm:SetTextColor(Unpack(nm2 and C_TEXT or C_DIM))
                c.sb:SetText(it[2] or "")
                local col = n % COLS
                local row = math.floor(n / COLS)
                c:ClearAllPoints()
                c:SetPoint("TOPLEFT", tc, "TOPLEFT", PAD + col * (COL_W + CARD_GAP), -(y + row * (CARD_H + CARD_GAP)))
                c:Show()
                n = n + 1
            end
            y = y + math.ceil(n / COLS) * (CARD_H + CARD_GAP) + 4
        end
        for k = ci + 1, #tCards do tCards[k]:Hide() end
        tc:SetHeight(math.max(y + 4, 1))
        if tgb then tgb() end
    end

    function ns.ExploreSunGlassesPaint(EGm)
        local E = EGm or EG
        if not E.sgFrame then return end
        local seg = E.sgSeg or "step"
        local total = (E.sgMode == "total")

        for key, bt in pairs(E.sgSegBtns) do
            local on = (seg == key) and not total
            local fs = bt:GetFontString()
            if fs then fs:SetTextColor(Unpack(on and C_WHITE or C_GREY)) end
        end
        local rfs = E.sgRwBtn:GetFontString()
        if rfs then rfs:SetTextColor(Unpack(total and C_WHITE or C_GOLD)) end

        if seg == "boss" then
            E.sgPhase = E.sgPhase or 1
            for i, r in ipairs(rows) do
                local ph = PHASES[i]
                if ph then
                    r.__phase, r.__idx, r.__sid = true, i, ph.sid
                    r.si.__sid = ph.sid
                    r.si.__tex:SetTexture(SpellTex(ph.sid))
                    r.si:Show()
                    r.no:ClearAllPoints()
                    r.no:SetPoint("TOPLEFT", r, "TOPLEFT", 44, -8)
                    r.no:SetText(ph.p)
                    r.no:SetTextColor(Unpack(C_GOLD))
                    r.t:ClearAllPoints()
                    r.t:SetPoint("LEFT", r.no, "RIGHT", 6, 0)
                    r.t:SetPoint("RIGHT", r, "RIGHT", -70, 0)
                    r.t:SetText(ph.title)
                    r.t:SetTextColor(Unpack(C_TEXT))
                    r.p:ClearAllPoints()
                    r.p:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 44, 8)
                    r.p:SetPoint("RIGHT", r, "RIGHT", -70, 0)
                    r.p:SetText(ph.at)
                    r.p:SetTextColor(Unpack(C_GREY))
                    r.st:ClearAllPoints()
                    r.st:SetPoint("BOTTOMRIGHT", r, "BOTTOMRIGHT", -8, 8)
                    r.st:SetText(ph.mech)
                    r.st:SetTextColor(Unpack(C_DIM))
                    r.tint:SetColorTexture(1, 1, 1, (E.sgPhase == i) and 0.10 or 0)
                    r:Show()
                else
                    r:Hide()
                end
            end
            E.sgProg:SetText(format(L["阶段 %d / %d"], E.sgPhase, #PHASES))
        else
            if not E.sgSel then
                for i, st in ipairs(STEPS) do
                    if QState(st.q) < 2 then E.sgSel = i break end
                end
                E.sgSel = E.sgSel or 1
            end
            local done = 0
            for i, r in ipairs(rows) do
                local st = STEPS[i]
                if st then
                    r.__phase, r.__idx, r.__sid = false, i, nil
                    r.si:Hide()
                    local s = QState(st.q)
                    if s == 2 then done = done + 1 end
                    r.no:ClearAllPoints()
                    r.no:SetPoint("TOPLEFT", r, "TOPLEFT", 8, -6)
                    r.no:SetText(st.no)
                    r.no:SetTextColor(Unpack(C_GOLD))
                    r.t:ClearAllPoints()
                    r.t:SetPoint("TOPLEFT", r, "TOPLEFT", 32, -6)
                    r.t:SetPoint("RIGHT", r, "RIGHT", -70, 0)
                    r.t:SetText(QName(st.q, st.title))
                    r.t:SetTextColor(Unpack(s == 2 and C_DIM or C_TEXT))
                    r.p:ClearAllPoints()
                    r.p:SetPoint("BOTTOMLEFT", r, "BOTTOMLEFT", 32, 6)
                    r.p:SetPoint("RIGHT", r, "RIGHT", -8, 0)
                    r.p:SetText(st.where)
                    r.p:SetTextColor(Unpack(C_GREY))
                    r.st:ClearAllPoints()
                    r.st:SetPoint("TOPRIGHT", r, "TOPRIGHT", -8, -6)
                    r.st:SetText(s == 2 and L["已完成"] or (s == 1 and L["已接取"] or L["未完成"]))
                    r.st:SetTextColor(Unpack(s == 2 and C_OK or (s == 1 and C_GOLD or C_GREY)))
                    r.tint:SetColorTexture(1, 1, 1, (E.sgSel == i) and 0.10 or 0)
                    r:Show()
                end
            end
            E.sgProg:SetText(format(L["进度 %d / %d"], done, #STEPS))
        end

        if total then
            E.sgDet:Hide()
            E.sgTot:Show()
            PaintTotal()
        else
            E.sgTot:Hide()
            E.sgDet:Show()
            if seg == "boss" then
                PaintPhase(E.sgPhase)
            else
                PaintStep(E.sgSel)
            end
        end
        if E.sgNeedNames then E.sgNeedNames = false end
    end

    function ns.ExploreSunGlassesLayout(EGm)
        local E = EGm or EG
        if not E.sgLC then return end
        local h = E.sgLC:GetHeight()
        if type(h) ~= "number" or h <= 100 then h = 411 end
        local seg = E.sgSeg or "step"
        local n = (seg == "boss") and #PHASES or #STEPS
        local rh = (h - (n - 1) * ROW_GAP) / n
        if rh < 34 then rh = 34 end
        for i, r in ipairs(rows) do
            if i <= n then
                r:SetHeight(rh)
                r:ClearAllPoints()
                r:SetPoint("TOPLEFT", lc, "TOPLEFT", 0, -((i - 1) * (rh + ROW_GAP)))
                r:SetPoint("TOPRIGHT", lc, "TOPRIGHT", 0, -((i - 1) * (rh + ROW_GAP)))
            end
        end
        if sgb then sgb() end
        if tgb then tgb() end
    end

    root:SetFrameLevel(math.max(root:GetFrameLevel() or 0, (EG.cardLvl or 0) + 3))
    ns.ExploreSunGlassesPaint(EG)
    ns.ExploreSunGlassesLayout(EG)
end

ns.ExploreSunGlassesBuild = Build

function ns.ExploreSunGlassesRefresh(EG)
    if not (EG and EG.sgFrame and EG.sgFrame:IsShown()) then return end
    if ns.ExploreSunGlassesPaint then ns.ExploreSunGlassesPaint(EG) end
    if ns.ExploreSunGlassesLayout then ns.ExploreSunGlassesLayout(EG) end
end

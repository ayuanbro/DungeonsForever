local addonName, addon = ...

addon.LibHUI = addon.LibHUI or {}

local HUI = addon.LibHUI
local Config = HUI.Config
local Theme = HUI.Theme
local Widgets = HUI.Widgets
local UI = {}

local CreateFrame = CreateFrame
local UIParent = UIParent
local ipairs = ipairs
local pairs = pairs
local type = type
local tonumber = tonumber
local tostring = tostring
local wipe = wipe

HUI.UI = UI

local L = HUI.L

local function DetachRegion(region)
  if not region or not region.Hide then return end

  local live = {}
  local function collect(target)
    if not target then return end
    if target.children then
      for _, child in ipairs(target.children) do live[child] = true end
    end
    if target.GetChildren then
      for _, child in ipairs({ target:GetChildren() }) do live[child] = true end
    end
  end

  collect(region)
  for child in pairs(live) do
    DetachRegion(child)
    child:Hide()
    if child.SetParent then child:SetParent(nil) end
    if child._huiListenerID then
      Theme:OffAccentChanged(child._huiListenerID)
      child._huiListenerID = nil
    end
    if child._huiListenerIDs then
      for _, id in ipairs(child._huiListenerIDs) do
        Theme:OffAccentChanged(id)
      end
      child._huiListenerIDs = nil
    end
    if child._huiActionButtons then
      for _, btn in ipairs(child._huiActionButtons) do
        for i = #Widgets._actionButtons, 1, -1 do
          if Widgets._actionButtons[i] == btn then
            table.remove(Widgets._actionButtons, i)
            break
          end
        end
      end
      child._huiActionButtons = nil
    end
    if child.children then
      wipe(child.children)
    end
    local parent = child.GetParent and child:GetParent()
    if parent and parent.children then
      for i = #parent.children, 1, -1 do
        if parent.children[i] == child then
          table.remove(parent.children, i)
          break
        end
      end
    end
  end
end

local function ClearChildren(frame)
  if not frame then
    return
  end

  DetachRegion(frame)
  if frame.children then
    wipe(frame.children)
  end
end

local function Track(parent, child)
  parent.children = parent.children or {}
  parent.children[#parent.children + 1] = child
  return child
end

local function GetCollapsedMap(app)
  local db = app and app.GetDB and app:GetDB()
  if type(db) ~= "table" then
    return nil
  end
  if type(db.collapsedGroups) ~= "table" then
    db.collapsedGroups = {}
  end
  return db.collapsedGroups
end

local function CollapseKey(control)
  return tostring(control.pageID or "global") .. "|" .. tostring(control.id or "")
end

local function IsHeaderCollapsed(app, control)
  local map = GetCollapsedMap(app)
  if not map then
    return false
  end
  return map[CollapseKey(control)] and true or false
end

local function SetHeaderCollapsed(app, control, value)
  local map = GetCollapsedMap(app)
  if not map then
    return
  end
  local key = CollapseKey(control)
  if value then
    map[key] = true
  else
    map[key] = nil
  end
end

local function DiscardRow(parent, row)
  if not row then
    return
  end
  DetachRegion(row)
  if parent and parent.children then
    for i = #parent.children, 1, -1 do
      if parent.children[i] == row then
        table.remove(parent.children, i)
        break
      end
    end
  end
end

local function FitNavButton(button, minWidth)
  local textWidth = button.text and button.text:GetStringWidth() or 0
  local width = minWidth or 24
  if textWidth and textWidth > 0 then
    width = math.max(width, math.ceil(textWidth + 12))
  end
  button:SetWidth(width)
end

local function CollectListener(row, widget)
  if widget then
    if widget._huiListenerID then
      row._huiListenerIDs = row._huiListenerIDs or {}
      row._huiListenerIDs[#row._huiListenerIDs + 1] = widget._huiListenerID
    end
    if widget._huiListenerIDs then
      row._huiListenerIDs = row._huiListenerIDs or {}
      for _, id in ipairs(widget._huiListenerIDs) do
        row._huiListenerIDs[#row._huiListenerIDs + 1] = id
      end
    end
  end
end

function UI:GetFrame()
  if self.frame then
    return self.frame
  end

  local frame = Widgets:CreatePanel(UIParent, "YYBuffReminderSettingsFrame")
  frame:SetSize(Theme.sizes.frameWidth, Theme.sizes.frameHeight)
  frame:SetPoint("CENTER")
  frame:SetFrameStrata("DIALOG")
  frame:EnableMouse(true)
  frame:SetMovable(true)
  frame:RegisterForDrag("LeftButton")
  frame:SetScript("OnDragStart", frame.StartMoving)
  frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
  frame:SetScript("OnHide", function()
    Widgets:CloseManagedPopups()
  end)
  frame:Hide()

  frame._HUIState = {
    rows = {},
  }

  local sidebarW = Theme.sizes.sidebarWidth or 130
  frame.sidebar = CreateFrame("Frame", nil, frame)
  frame.sidebar:SetPoint("TOPLEFT", frame, "TOPLEFT", 0, 0)
  frame.sidebar:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 0, 0)
  frame.sidebar:SetWidth(sidebarW)
  frame.sidebar.children = {}
  frame.sidebar.bg = frame.sidebar:CreateTexture(nil, "BACKGROUND")
  frame.sidebar.bg:SetColorTexture(0.01, 0.03, 0.05, 0.60)
  frame.sidebar.bg:SetAllPoints()
  frame.sidebar.divider = frame.sidebar:CreateTexture(nil, "ARTWORK")
  frame.sidebar.divider:SetWidth(1)
  frame.sidebar.divider:SetColorTexture(0.25, 0.32, 0.42, 0.80)
  frame.sidebar.divider:SetPoint("TOPRIGHT", frame.sidebar, "TOPRIGHT", 0, 0)
  frame.sidebar.divider:SetPoint("BOTTOMRIGHT", frame.sidebar, "BOTTOMRIGHT", 0, 0)

  frame.logo = frame.sidebar:CreateTexture(nil, "ARTWORK")
  frame.logo:SetSize(36, 36)
  frame.logo:SetPoint("TOP", frame.sidebar, "TOP", 0, -16)
  frame.logo:Hide()

    frame.title = Widgets:CreateText(frame.sidebar, Theme.fonts.heading, "圆圆的Buff提醒", "text")
  frame.title:SetPoint("TOP", frame.logo, "BOTTOM", 0, -6)

  frame.close = Widgets:CreateActionButton(frame, "×", 28, 26, function()
    frame:Hide()
  end)
  frame.close:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -12, -15)

  frame.nav = CreateFrame("Frame", nil, frame.sidebar)
  frame.nav:SetPoint("TOPLEFT", frame.sidebar, "TOPLEFT", 0, -80)
  frame.nav:SetPoint("TOPRIGHT", frame.sidebar, "TOPRIGHT", 0, -80)
  frame.nav:SetPoint("BOTTOMLEFT", frame.sidebar, "BOTTOMLEFT", 0, 50)
  frame.nav:SetPoint("BOTTOMRIGHT", frame.sidebar, "BOTTOMRIGHT", 0, 50)
  frame.nav.children = {}

  frame.subnav = CreateFrame("Frame", nil, frame)
  frame.subnav:SetPoint("TOPLEFT", frame.sidebar, "TOPRIGHT", 18, -18)
  frame.subnav:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -18, -18)
  frame.subnav:SetHeight(28)
  frame.subnav.children = {}

  local contentW = Theme.sizes.frameWidth - sidebarW - 36
  local contentH = Theme.sizes.frameHeight - 58 - 18
  frame.listScroll = Widgets:CreateScrollFrame(frame, contentW, contentH)
  frame.listScroll:SetPoint("TOPLEFT", frame.sidebar, "TOPRIGHT", 18, -58)
  frame.listScroll.children = {}
  frame.list = frame.listScroll.content
  frame.list.children = {}

  self.frame = frame

  Theme:OnAccentChanged(function()
    if self.frame and self.frame:IsShown() then
      local state = self.frame._HUIState
      if state and state.app and state.page then
        self:Render(state.app, state.page.id)
      end
    end
  end)

  return frame
end

function UI:IsPageVisible(page)
  if not page then return false end
  if type(page.visibleWhen) == "function" and not page.visibleWhen(page) then
    return false
  end
  return true
end

function UI:ApplyControlStyles()
  local frame = self.frame
  if not frame then return end
  local state = frame._HUIState
  if not state or not state.controlBgs then return end
  local alpha = addon.db and addon.db.settings and addon.db.settings.controlAlpha or 0.92
  local color = addon.db and addon.db.settings and addon.db.settings.controlBgColor or {0x0a/255, 0x12/255, 0x1c/255}
  for _, bg in ipairs(state.controlBgs) do
    if bg and bg.SetColorTexture then
      bg:SetColorTexture(color[1], color[2], color[3], alpha)
    end
  end
end

local POWER_ICON = "Interface\\AddOns\\YY_BuffReminder\\LibHUI\\Assets\\power"
local function CreatePowerToggle(parent, category, onToggle)
  if type(category.getEnabled) ~= "function" then return nil end
  local pwrBtn = CreateFrame("Button", nil, parent)
  pwrBtn:SetSize(13, 13)
  pwrBtn:SetPoint("RIGHT", parent, "RIGHT", -8, 0)
  pwrBtn:SetFrameLevel(parent:GetFrameLevel() + 10)
  local tex = pwrBtn:CreateTexture(nil, "OVERLAY")
  tex:SetAllPoints()
  tex:SetTexture(POWER_ICON)
  tex:SetTexCoord(1, 0, 1, 0)
  tex:SetDrawLayer("OVERLAY", 7)
  pwrBtn._tex = tex
  pwrBtn._category = category
  local function RefreshPower()
    local enabled = category.getEnabled()
    if enabled then
      tex:SetVertexColor(1, 1, 1, 1)
    else
      tex:SetVertexColor(1, 1, 1, 0.4)
    end
  end
  RefreshPower()
  pwrBtn:SetScript("OnEnter", function(self)
    local enabled = category.getEnabled()
    if enabled then
      tex:SetVertexColor(0.824, 0.212, 0.212, 1)
    else
      tex:SetVertexColor(0.212, 0.824, 0.325, 1)
    end
  end)
  pwrBtn:SetScript("OnLeave", function(self)
    RefreshPower()
  end)
  pwrBtn:SetScript("OnClick", function(self)
    local enabled = category.getEnabled()
    if type(category.setEnabled) == "function" then
      category.setEnabled(not enabled)
    end
    RefreshPower()
    if onToggle then onToggle() end
  end)
  pwrBtn.Refresh = RefreshPower
  return pwrBtn
end

function UI:RenderNav(app, currentPage)
  local frame = self:GetFrame()

  if #app.categoryList <= 1 then
    frame.nav:Hide()
    return
  end
  frame.nav:Show()

  local currentCategoryID = currentPage and currentPage.category
  local navW = frame.nav:GetWidth() or (Theme.sizes.sidebarWidth or 130)
  local btnH = 36
  local gap = 4

  local topCats, bottomCats = {}, {}
  for _, category in ipairs(app.categoryList) do
    if category.sidebarBottom then
      bottomCats[#bottomCats + 1] = category
    else
      topCats[#topCats + 1] = category
    end
  end

  frame.nav._huiNavCache = frame.nav._huiNavCache or {}
  local navCache = frame.nav._huiNavCache
  local fingerprint = tostring(#topCats) .. "|" .. tostring(#bottomCats)
  for _, c in ipairs(topCats) do fingerprint = fingerprint .. ">" .. tostring(c.id) end
  for _, c in ipairs(bottomCats) do fingerprint = fingerprint .. "<" .. tostring(c.id) end
  local structureChanged = (navCache.fingerprint ~= fingerprint)
  if structureChanged then
    ClearChildren(frame.nav)
    frame.nav._huiNavCache = { fingerprint = fingerprint }
    navCache = frame.nav._huiNavCache
  end

  local lastButton
  local navIndex = 0
  local function AcquireNavButton(category, anchorTop)
    navIndex = navIndex + 1
    local buttonKey = "btn" .. navIndex
    local button = navCache[buttonKey]
    if not button then
      button = Track(frame.nav, Widgets:CreateButton(frame.nav, "", navW, btnH, "left"))
      navCache[buttonKey] = button
    end
    if button.text and button.text.SetText then
      button.text:SetText(category.title or category.id)
    end
    if button.SetSelected then
      button:SetSelected(category.id == currentCategoryID)
    end
    button._huiCategoryID = category.id
    button:SetScript("OnClick", function()
      local cat = app.categories[button._huiCategoryID]
      local pages = cat and cat.pages or {}
      for _, page in ipairs(pages) do
        if self:IsPageVisible(page) then
          self:Render(app, page.id)
          return
        end
      end
    end)
    if button._pwrBtn and button._pwrBtn.Hide then
      DetachRegion(button._pwrBtn)
      button._pwrBtn = nil
    end
    local hasPower = type(category.getEnabled) == "function"
    if hasPower then
      local pwrBtn = CreatePowerToggle(button, category, function()
        local state = frame._HUIState
        if state and state.app and state.page then
          self:Render(state.app, state.page.id)
        end
      end)
      if pwrBtn then
        button._pwrBtn = pwrBtn
        if button.text then
          button.text:ClearAllPoints()
          button.text:SetPoint("LEFT", button, "LEFT", 10, 0)
        end
      end
      if not category.getEnabled() then
        button:SetAlpha(0.55)
      else
        button:SetAlpha(1)
      end
    else
      button:SetAlpha(1)
    end
    if anchorTop then
      if lastButton then
        button:SetPoint("TOPLEFT", lastButton, "BOTTOMLEFT", 0, -gap)
        button:SetPoint("TOPRIGHT", lastButton, "BOTTOMRIGHT", 0, -gap)
      else
        button:SetPoint("TOPLEFT", frame.nav, "TOPLEFT", 0, 0)
        button:SetPoint("TOPRIGHT", frame.nav, "TOPRIGHT", 0, 0)
      end
      lastButton = button
    end
    return button
  end

  for _, category in ipairs(topCats) do
    AcquireNavButton(category, true)
  end

  local divider
  if #bottomCats > 0 then
    if structureChanged then
      divider = Track(frame.nav, frame.nav:CreateTexture(nil, "ARTWORK"))
      divider:SetHeight(1)
      divider:SetColorTexture(0.25, 0.32, 0.42, 0.60)
      navCache.divider = divider
    else
      divider = navCache.divider
    end
    if divider then
      divider:SetPoint("TOPLEFT", frame.nav, "BOTTOMLEFT", 16, -btnH * #bottomCats - gap * #bottomCats - 4)
      divider:SetPoint("TOPRIGHT", frame.nav, "BOTTOMRIGHT", -16, -btnH * #bottomCats - gap * #bottomCats - 4)
    end

    local firstBottom = true
    local prevButton
    for index = #bottomCats, 1, -1 do
      local category = bottomCats[index]
      local button = AcquireNavButton(category, false)
      if firstBottom then
        button:SetPoint("BOTTOMLEFT", frame.nav, "BOTTOMLEFT", 0, 0)
        button:SetPoint("BOTTOMRIGHT", frame.nav, "BOTTOMRIGHT", 0, 0)
        firstBottom = false
      else
        button:SetPoint("BOTTOMLEFT", prevButton, "TOPLEFT", 0, gap)
        button:SetPoint("BOTTOMRIGHT", prevButton, "TOPRIGHT", 0, gap)
      end
      prevButton = button
    end
  end

  if not structureChanged then
    for key, btn in pairs(navCache) do
      if type(key) == "string" and key:find("^btn") then
        local idx = tonumber(key:match("btn(%d+)"))
        if idx and idx > navIndex and btn and btn.Hide then
          btn:Hide()
        end
      end
    end
  end
end

function UI:RenderSubNav(app, currentPage)
  local frame = self:GetFrame()

  local currentCategory = currentPage and currentPage.category and app.categories[currentPage.category]
  if not currentCategory then
    frame.subnav:Hide()
    return
  end

  local visiblePages = {}
  for _, page in ipairs(currentCategory.pages) do
    if self:IsPageVisible(page) then
      visiblePages[#visiblePages + 1] = page
    end
  end
  if #visiblePages <= 1 then
    frame.subnav:Hide()
    return
  end
  frame.subnav:Show()

  frame.subnav._huiNavCache = frame.subnav._huiNavCache or {}
  local subCache = frame.subnav._huiNavCache
  local fingerprint = ""
  for _, p in ipairs(visiblePages) do fingerprint = fingerprint .. ">" .. tostring(p.id) end
  local structureChanged = (subCache.fingerprint ~= fingerprint)
  if structureChanged then
    ClearChildren(frame.subnav)
    frame.subnav._huiNavCache = { fingerprint = fingerprint }
    subCache = frame.subnav._huiNavCache
  end

  local lastButton
  for index, page in ipairs(visiblePages) do
    local buttonKey = "btn" .. index
    local button = subCache[buttonKey]
    if not button then
      button = Track(frame.subnav, Widgets:CreateButton(frame.subnav, "", 128, 24))
      subCache[buttonKey] = button
    end
    if button.text and button.text.SetText then
      button.text:SetText(page.title or page.id)
    end
    FitNavButton(button)
    if button.SetSelected then
      button:SetSelected(page.id == currentPage.id)
    end
    button._huiPageID = page.id
    button:SetScript("OnClick", function()
      self:Render(app, button._huiPageID)
    end)
    if lastButton then
      button:SetPoint("LEFT", lastButton, "RIGHT", 8, 0)
    else
      button:SetPoint("LEFT")
    end
    lastButton = button
  end

  if not structureChanged then
    for key, btn in pairs(subCache) do
      if type(key) == "string" and key:find("^btn") then
        local idx = tonumber(key:match("btn(%d+)"))
        if idx and idx > #visiblePages and btn and btn.Hide then
          btn:Hide()
        end
      end
    end
  end
end

function UI:RenderControl(app, parent, control, yOffset, reuseRow)
  local controlType = control.type

  if controlType == "divider" then
    if reuseRow and reuseRow.Hide then reuseRow:Hide() end
    local placeholder = Track(parent, CreateFrame("Frame", nil, parent))
    placeholder:SetHeight(8)
    placeholder:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    placeholder:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)
    local line = placeholder:CreateTexture(nil, "ARTWORK")
    line:SetHeight(1)
    line:SetColorTexture(0x25/255, 0x33/255, 0x42/255, 0.9)
    line:SetPoint("TOPLEFT", placeholder, "TOPLEFT", 0, 0)
    line:SetPoint("TOPRIGHT", placeholder, "TOPRIGHT", 0, 0)
    placeholder.SetSelected = function() end
    return placeholder
  end

  if controlType == "groupheader" then
    if reuseRow and reuseRow.Hide then reuseRow:Hide() end
    local collapsed = IsHeaderCollapsed(app, control)
    local header = Track(parent, Widgets:CreateGroupHeader(parent, control.label or control.text or "", 20, {
      collapsible = control.collapsible ~= false,
      collapsed = collapsed,
      onToggle = function(_, value)
        SetHeaderCollapsed(app, control, value)
        UI:Render(app, control.pageID)
      end,
    }))
    header:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    header:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)
    header.SetSelected = function() end
    return header
  end

  if controlType == "label" then
    if reuseRow and reuseRow.Hide then reuseRow:Hide() end
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)
    row:SetHeight(Theme.sizes.rowHeight)
    local renderedLabels = {}
    if control.labelSegments then
      local previous
      local segmentCount = #control.labelSegments
      for index, segment in ipairs(control.labelSegments) do
        local segmentLabel = Widgets:CreateText(row, Theme.fonts.small, segment.text or "", "muted")
        if previous then
          segmentLabel:SetPoint("LEFT", previous, "RIGHT", segment.offset or 0, 0)
        else
          segmentLabel:SetPoint("LEFT", row, "LEFT", 14, 0)
        end
        segmentLabel:SetJustifyH("LEFT")
        segmentLabel:SetWordWrap(true)
        if index == segmentCount then
          segmentLabel:SetPoint("RIGHT", row, "RIGHT", -14, 0)
        end
        if segment.outline then
          local fontPath, fontSize = segmentLabel:GetFont()
          if fontPath and fontSize then
            segmentLabel:SetFont(fontPath, fontSize, BG.hui.FontFlags("OUTLINE"))
          end
        end
        renderedLabels[#renderedLabels + 1] = segmentLabel
        previous = segmentLabel
      end
    else
      renderedLabels[1] = Widgets:CreateLabel(row, control.label or control.text or "", "muted")
      renderedLabels[1]:SetPoint("LEFT", row, "LEFT", 14, 0)
      renderedLabels[1]:SetPoint("RIGHT", row, "RIGHT", -14, 0)
    end
    local rowHeight = Theme.sizes.rowHeight
    local stringHeight = 0
    for _, renderedLabel in ipairs(renderedLabels) do
      local labelHeight = renderedLabel.GetStringHeight and renderedLabel:GetStringHeight() or 0
      if type(labelHeight) == "number" and labelHeight > stringHeight then
        stringHeight = labelHeight
      end
    end
    if stringHeight > 0 then
      rowHeight = math.max(rowHeight, math.ceil(stringHeight + 6))
    end
    row:SetHeight(rowHeight)
    row._huiRenderedHeight = rowHeight
    row.SetSelected = function() end
    return row
  end

  if controlType == "previewbar" then
    local CAPTION_H = 18
    local PAD_TOP = 6
    local MAX_ICON = 64
    local PAD_BOTTOM = 12
    local ICON_TOP = -(CAPTION_H + PAD_TOP + 2)

    local entries = type(control.getEntries) == "function" and control.getEntries() or {}
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)
    row:SetHeight(CAPTION_H + PAD_TOP + MAX_ICON + PAD_BOTTOM)

    local title = Widgets:CreateText(row, Theme.fonts.small, control.title or "图标预览", "muted")
    title:SetPoint("TOPLEFT", row, "TOPLEFT", 14, -2)

    local data = { row = row, entries = entries, buttons = {}, iconTop = ICON_TOP, maxIcon = MAX_ICON }
    local built = 0
    if #entries > 0 then
      local strip = row:CreateTexture(nil, "BACKGROUND")
      strip:SetColorTexture(0.02, 0.05, 0.09, 0.9)
      data.strip = strip
      data.moreText = Widgets:CreateText(row, Theme.fonts.small, "", "muted")
      data.moreText:SetJustifyH("LEFT")
      data.moreText:SetPoint("LEFT", row, "TOPLEFT", 16, ICON_TOP + 24)

      for index = 1, 24 do
        local entry = entries[index]
        if not entry then break end
        local btn = CreateFrame("Button", nil, row)
        btn:SetSize(1, 1)
        btn.icon = btn:CreateTexture(nil, "ARTWORK")
        btn.icon:SetAllPoints()
        btn.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
        btn.label = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        btn.label:SetPoint("BOTTOMLEFT", btn, "BOTTOMLEFT", 2, 1)
        btn.label:SetJustifyH("LEFT")
        btn.label:SetTextColor(1, 1, 1, 1)
        btn.label:SetShadowColor(0, 0, 0, 1)
        btn.label:SetShadowOffset(1, -1)
        btn.label:Hide()

        btn.count = btn:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
        btn.count:SetJustifyH("RIGHT")
        btn.count:SetTextColor(1, 1, 0.4, 1)
        btn.count:SetShadowColor(0, 0, 0, 1)
        btn.count:SetShadowOffset(1, -1)
        btn.count:Hide()
        if type(control.onToggle) == "function" then
          btn:SetScript("OnClick", function()
            control.onToggle(entry, control)
          end)
          btn:SetScript("OnEnter", function(owner)
            GameTooltip:SetOwner(owner, "ANCHOR_RIGHT")
            GameTooltip:ClearLines()
            GameTooltip:AddLine(entry.label or "", 1, 1, 1)
            if entry.enabled == false then
              GameTooltip:AddLine("已关闭 · 点击启用", 0.7, 0.7, 0.7)
            else
              GameTooltip:AddLine("已开启 · 点击关闭", 0.7, 0.7, 0.7)
            end
            GameTooltip:Show()
          end)
          btn:SetScript("OnLeave", function() GameTooltip:Hide() end)
        end
        data.buttons[#data.buttons + 1] = btn
        built = built + 1
      end
    end
    data.built = built

    local function UpdateVisuals()
      local size = tonumber(control.getIconSize and control.getIconSize()) or 34
      local spacing = tonumber(control.getSpacing and control.getSpacing()) or 4
      local alpha = tonumber(control.getAlpha and control.getAlpha()) or 1
      local showText = not control.getShowText or control.getShowText() ~= false
      local labelSize = tonumber(control.getLabelSize and control.getLabelSize()) or 10
      local labelX = tonumber(control.getLabelX and control.getLabelX()) or 2
      local labelY = tonumber(control.getLabelY and control.getLabelY()) or 1
      local countSize = tonumber(control.getCountSize and control.getCountSize()) or 10
      local countX = tonumber(control.getCountX and control.getCountX()) or 2
      local countY = tonumber(control.getCountY and control.getCountY()) or 1
      local textOutline = control.getTextOutline and control.getTextOutline() or "none"
      local countOutline = control.getCountOutline and control.getCountOutline() or "none"
      local fontFile = GameFontNormalSmall and select(1, GameFontNormalSmall:GetFont()) or STANDARD_TEXT_FONT
      local textFlags = (addon and addon.OutlineToFlags) and addon:OutlineToFlags(textOutline) or ""
      local countFlags = (addon and addon.OutlineToFlags) and addon:OutlineToFlags(countOutline) or ""
      if size < 8 then size = 8 end
      if size > MAX_ICON then size = MAX_ICON end
      if spacing < 0 then spacing = 0 end

      local rowWidth = row:GetWidth() or 552
      local usable = rowWidth - 30
      local per = size + spacing
      local maxCount = per > 0 and math.floor(usable / per) or 0
      if maxCount < 1 then maxCount = 1 end
      local shown = math.min(#data.buttons, maxCount)

      local previous
      for index, btn in ipairs(data.buttons) do
        if index <= shown then
          local entry = data.entries[index]
          btn:SetSize(size, size)
          btn:ClearAllPoints()
          if previous then
            btn:SetPoint("LEFT", previous, "RIGHT", spacing, 0)
          else
            btn:SetPoint("TOPLEFT", row, "TOPLEFT", 16, ICON_TOP)
          end
          btn.icon:SetTexture(entry.icon or (addon.Data and addon.Data.PreviewFallbackIcon))
          if entry.enabled == false then
            btn.icon:SetDesaturated(true)
            btn.icon:SetAlpha(0.35)
          else
            btn.icon:SetDesaturated(false)
            btn.icon:SetAlpha(alpha)
          end
          btn.label:SetFont(fontFile, labelSize, textFlags)
          btn.label:ClearAllPoints()
          btn.label:SetPoint("BOTTOMLEFT", btn, "BOTTOMLEFT", labelX, labelY)
          btn.label:SetShadowColor(0, 0, 0, 1)
          btn.label:SetShadowOffset(1, -1)
          if showText and entry.shortLabel then
            btn.label:SetText(entry.shortLabel)
            btn.label:Show()
          else
            btn.label:Hide()
          end
          btn.count:SetFont(fontFile, countSize, countFlags)
          btn.count:ClearAllPoints()
          btn.count:SetPoint("BOTTOMRIGHT", btn, "BOTTOMRIGHT", -countX, countY)
          btn.count:SetShadowColor(0, 0, 0, 1)
          btn.count:SetShadowOffset(1, -1)
          if entry.hasCount then
            local c = tonumber(entry.count) or 0
            btn.count:SetText(c > 99 and "99+" or tostring(c))
            btn.count:Show()
          else
            btn.count:Hide()
          end
          btn:Show()
          previous = btn
        else
          btn:Hide()
        end
      end

      if data.strip then
        local stripW = shown > 0 and (shown * (size + spacing) - spacing) or 1
        data.strip:ClearAllPoints()
        data.strip:SetPoint("TOPLEFT", row, "TOPLEFT", 15, ICON_TOP + 1)
        data.strip:SetSize(math.max(stripW, 1), MAX_ICON + 2)
        local overflow = math.max(#data.entries - shown, 0)
        if overflow > 0 then
          data.moreText:SetText("+ " .. overflow)
          data.moreText:Show()
          data.moreText:ClearAllPoints()
          if previous then
            data.moreText:SetPoint("LEFT", previous, "RIGHT", 8, math.floor(size / 2) - 8)
          else
            data.moreText:SetPoint("TOPLEFT", row, "TOPLEFT", 16, ICON_TOP + 24)
          end
        else
          data.moreText:Hide()
        end
      end
    end

    control.updateVisuals = UpdateVisuals
    if #entries == 0 then
      row:SetHeight(34)
      local empty = Widgets:CreateText(row, Theme.fonts.small, "当前职业没有可提醒的增益或消耗品", "muted")
      empty:SetPoint("TOPLEFT", row, "TOPLEFT", 14, -2)
    else
      UpdateVisuals()
    end

    row._huiRenderedHeight = row:GetHeight()
    row.SetSelected = function() end
    return row
  end

  function UI:GetImportantDetailPanel()
    local frame = self:GetFrame()
    local state = frame._HUIState
    if state.importantDetail then
      return state.importantDetail
    end
    local panel = CreateFrame("Frame", nil, frame)
    panel:SetPoint("TOPLEFT", frame, "TOPRIGHT", 6, 0)
    panel:SetPoint("BOTTOMLEFT", frame, "BOTTOMRIGHT", 6, 0)
    panel:SetWidth(264)
    panel:SetFrameStrata(frame:GetFrameStrata())
    panel:EnableMouse(true)
    panel:RegisterForDrag("LeftButton")
    panel:SetScript("OnDragStart", function() frame:StartMoving() end)
    panel:SetScript("OnDragStop", function() frame:StopMovingOrSizing() end)
    local bg = panel:CreateTexture(nil, "BACKGROUND")
    bg:SetAllPoints()
    bg:SetColorTexture(0.02, 0.05, 0.09, 0.97)
    local border = CreateFrame("Frame", nil, panel, "BackdropTemplate")
    border:SetAllPoints()
    border:SetBackdrop({ edgeFile = "Interface\\Buttons\\WHITE8X8", edgeSize = 1 })
    local accent = Theme:Color("accent")
    border:SetBackdropBorderColor(accent[1], accent[2], accent[3], 0.7)
    panel.border = border
    panel.icon = panel:CreateTexture(nil, "ARTWORK")
    panel.icon:SetSize(40, 40)
    panel.icon:SetPoint("TOPLEFT", panel, "TOPLEFT", 14, -14)
    panel.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
    panel.title = Widgets:CreateText(panel, Theme.fonts.body, "", "text")
    panel.title:SetPoint("TOPLEFT", panel.icon, "TOPRIGHT", 10, 0)
    panel.title:SetWidth(190)
    panel.title:SetJustifyH("LEFT")
    panel.sub = Widgets:CreateText(panel, Theme.fonts.small, "", "muted")
    panel.sub:SetPoint("BOTTOMLEFT", panel.icon, "BOTTOMRIGHT", 10, 0)
    panel.sub:SetWidth(190)
    panel.sub:SetJustifyH("LEFT")
    panel.close = Widgets:CreateActionButton(panel, "×", 24, 22, function()
      local st = frame._HUIState
      st.importantSelectedSpell = nil
      panel:Hide()
    end)
    panel.close:SetPoint("TOPRIGHT", panel, "TOPRIGHT", -10, -12)
    panel.content = CreateFrame("Frame", nil, panel)
    panel.content:SetPoint("TOPLEFT", panel, "TOPLEFT", 0, -62)
    panel.content:SetPoint("BOTTOMLEFT", panel, "BOTTOMLEFT", 0, 12)
    panel.content:SetWidth(264)
    panel:Hide()
    state.importantDetail = panel
    return panel
  end

  function UI:RefreshImportantDetail(app, control)
    local frame = self:GetFrame()
    local state = frame._HUIState
    local panel = self:GetImportantDetailPanel()
    local spellID = state.importantSelectedSpell
    local entry
    if spellID then
      local entries = type(control.getEntries) == "function" and control.getEntries() or {}
      for _, item in ipairs(entries) do
        if item.spellID == spellID then entry = item; break end
      end
    end
    if not entry then
      panel:Hide()
      return
    end
    panel:Show()
    panel.title:SetText(entry.label or "未知法术")
    panel.sub:SetText("Buff ID: " .. tostring(entry.spellID))
    panel.icon:SetTexture(entry.icon)
    local content = panel.content
    ClearChildren(content)
    local cursorY = 0
    local function AddHeader(text)
      local h = Widgets:CreateText(content, Theme.fonts.small, text, "muted")
      h:SetPoint("TOPLEFT", content, "TOPLEFT", 14, cursorY)
      h:SetWidth(150)
      h:SetJustifyH("LEFT")
      return h
    end
    local function RowGap()
      cursorY = cursorY - 30
    end
    AddHeader("高亮阈值 (秒)\n(0 = 常驻高亮)")
    local thresholdInput = Widgets:CreateInput(content, tostring(entry.thresholdSeconds or 10), function(text)
      local value = tonumber(text)
      if value and type(control.setThreshold) == "function" then control.setThreshold(entry.spellID, value) end
    end)
    thresholdInput:SetSize(96, 22)
    thresholdInput:SetPoint("TOPRIGHT", content, "TOPRIGHT", -14, cursorY)
    CollectListener(content, thresholdInput)
    RowGap()
    AddHeader("生效隐藏")
    local hideToggle = Widgets:CreateToggle(content, entry.hideActive == true, function(checked)
      if type(control.setHideActive) == "function" then control.setHideActive(entry.spellID, checked) end
    end)
    hideToggle:SetPoint("TOPRIGHT", content, "TOPRIGHT", -14, cursorY)
    RowGap()
    AddHeader("未生效隐藏")
    local hideInactiveToggle = Widgets:CreateToggle(content, entry.hideInactive == true, function(checked)
      if type(control.setHideInactive) == "function" then control.setHideInactive(entry.spellID, checked) end
    end)
    hideInactiveToggle:SetPoint("TOPRIGHT", content, "TOPRIGHT", -14, cursorY)
    RowGap()
    AddHeader("仅战斗中显示")
    local combatOnlyToggle = Widgets:CreateToggle(content, entry.combatOnly == true, function(checked)
      if type(control.setCombatOnly) == "function" then control.setCombatOnly(entry.spellID, checked) end
    end)
    combatOnlyToggle:SetPoint("TOPRIGHT", content, "TOPRIGHT", -14, cursorY)
    RowGap()
    local audienceOptions = type(control.getAudienceOptions) == "function" and control.getAudienceOptions() or {}
    AddHeader("受众")
    local audienceDropdown = Widgets:CreateDropdown(content, audienceOptions, entry.audience or "all", function(selected)
      if type(control.setAudience) == "function" then control.setAudience(entry.spellID, selected) end
    end)
    audienceDropdown:SetSize(100, 22)
    audienceDropdown:SetPoint("TOPRIGHT", content, "TOPRIGHT", -14, cursorY)
    CollectListener(content, audienceDropdown)
    RowGap()
    AddHeader("光环类型")
    local auraTypeOptions = type(control.getAuraTypeOptions) == "function" and control.getAuraTypeOptions() or {}
    local auraTypeDropdown = Widgets:CreateDropdown(content, auraTypeOptions, entry.auraType or "buff", function(selected)
      if type(control.setAuraType) == "function" then control.setAuraType(entry.spellID, selected) end
    end)
    auraTypeDropdown:SetSize(100, 22)
    auraTypeDropdown:SetPoint("TOPRIGHT", content, "TOPRIGHT", -14, cursorY)
    CollectListener(content, auraTypeDropdown)
    RowGap()
    AddHeader("单位")
    local unitOptions = type(control.getUnitOptions) == "function" and control.getUnitOptions() or {}
    local unitDropdown = Widgets:CreateDropdown(content, unitOptions, entry.unit or "player", function(selected)
      if type(control.setUnit) == "function" then control.setUnit(entry.spellID, selected) end
    end)
    unitDropdown:SetSize(100, 22)
    unitDropdown:SetPoint("TOPRIGHT", content, "TOPRIGHT", -14, cursorY)
    CollectListener(content, unitDropdown)
  end

  function UI:OpenImportantDetail(app, control, spellID)
    local frame = self:GetFrame()
    frame._HUIState.importantSelectedSpell = spellID
    self:RefreshImportantDetail(app, control)
  end

  function UI:GetImpDragger()
    local frame = self:GetFrame()
    local state = frame._HUIState
    if state.impDragFrame then
      return state.impDragFrame
    end
    local dragger = CreateFrame("Frame", nil, UIParent)
    dragger:SetAllPoints(UIParent)
    dragger:Hide()
    dragger:EnableMouse(true)
    dragger:SetFrameStrata("FULLSCREEN_DIALOG")

    local function ResetStripe(rowFrame)
      if rowFrame and rowFrame._impStripe then
        local sc = rowFrame._impStripe._impBase or { 0.08, 0.16, 0.24, 0.90 }
        rowFrame._impStripe:SetColorTexture(sc[1], sc[2], sc[3], sc[4] or 1)
      end
    end
    local function SetStripe(rowFrame)
      if rowFrame and rowFrame._impStripe then
        local ac = Theme:Color("accent")
        rowFrame._impStripe:SetColorTexture(ac[1], ac[2], ac[3], 0.45)
      end
    end

    dragger:SetScript("OnUpdate", function(self)
      local drag = state.impDrag
      if not drag then self:Hide(); return end
      local cx, cy = GetCursorPosition()
      local uiScale = UIParent:GetEffectiveScale()
      local y = cy / uiScale
      local dx = cx - drag.startX
      local dy = cy - drag.startY
      if not drag.moved then
        if (dx * dx + dy * dy) > 144 then
          drag.moved = true
          local ghost = CreateFrame("Frame", nil, UIParent)
          ghost:SetSize(180, 26)
          ghost:SetFrameStrata("FULLSCREEN_DIALOG")
          ghost.bg = ghost:CreateTexture(nil, "BACKGROUND")
          ghost.bg:SetAllPoints()
          ghost.bg:SetColorTexture(0.10, 0.20, 0.32, 0.92)
          ghost.label = Widgets:CreateText(ghost, Theme.fonts.small, drag.labelText or "", "text")
          ghost.label:SetPoint("LEFT", ghost, "LEFT", 8, 0)
          ghost.label:SetJustifyH("LEFT")
          drag.ghost = ghost
        end
      end
      if drag.moved and drag.ghost then
        drag.ghost:SetPoint("CENTER", UIParent, "BOTTOMLEFT", cx / uiScale, y)
        local target = UI:ImpComputeTargetIndex(state, y)
        if target ~= state.impHighlightIndex then
          if state.impHighlightIndex and state.impRows[state.impHighlightIndex] then
            ResetStripe(state.impRows[state.impHighlightIndex])
          end
          state.impHighlightIndex = target
          if target and state.impRows[target] then
            SetStripe(state.impRows[target])
          end
        end
      end
    end)

    dragger:SetScript("OnMouseUp", function(self, button)
      local drag = state.impDrag
      if not drag then self:Hide(); return end
      state.impDrag = nil
      self:Hide()
      if drag.ghost then drag.ghost:Hide(); drag.ghost = nil end
      if state.impHighlightIndex and state.impRows[state.impHighlightIndex] then
        ResetStripe(state.impRows[state.impHighlightIndex])
      end
      state.impHighlightIndex = nil
      if drag.moved then
        local _, cy = GetCursorPosition()
        local y = cy / UIParent:GetEffectiveScale()
        local target = UI:ImpComputeTargetIndex(state, y)
        if target and target ~= drag.fromIndex then
          if type(drag.control.reorderEntry) == "function" then
            drag.control.reorderEntry(drag.fromIndex, target)
          end
        end
      else
        UI:OpenImportantDetail(drag.app, drag.control, drag.spellID)
      end
    end)

    state.impDragFrame = dragger
    return dragger
  end

  function UI:ImpComputeTargetIndex(state, y)
    if not state.impRows then return nil end
    local best, bestDist = nil, 1e9
    for i, rowFrame in pairs(state.impRows) do
      local top = rowFrame:GetTop()
      local bot = rowFrame:GetBottom()
      if top and bot then
        local center = (top + bot) / 2
        local d = math.abs(center - y)
        if d < bestDist then
          bestDist = d
          best = i
        end
      end
    end
    return best
  end

  if controlType == "importanteditor" then
    local entries = type(control.getEntries) == "function" and control.getEntries() or {}
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)

    local title = Widgets:CreateText(row, Theme.fonts.small, control.title or "重要提醒清单", "muted")
    title:SetPoint("TOPLEFT", row, "TOPLEFT", 14, -2)
    local newInput = Widgets:CreateInput(row, "", function() end)
    newInput:SetSize(92, 22)
    newInput:SetPoint("LEFT", title, "RIGHT", 8, 0)
    CollectListener(row, newInput)
    local addButton = Widgets:CreateActionButton(row, "添加", 46, 22, function()
      local value = newInput:GetText()
      if type(control.addEntry) == "function" then control.addEntry(value) end
    end)
    addButton:SetPoint("LEFT", newInput, "RIGHT", 6, 0)
    newInput.editBox:SetScript("OnEditFocusLost", nil)
    newInput.editBox:SetScript("OnEnterPressed", function(self)
      local value = self:GetText()
      if type(control.addEntry) == "function" then control.addEntry(value) end
      self:ClearFocus()
    end)

    local listTop = -60
    local buffHeader = Widgets:CreateText(row, Theme.fonts.small, "光环信息", "muted")
    buffHeader:SetPoint("TOPLEFT", row, "TOPLEFT", 16, -36)
    buffHeader:SetWidth(200)
    buffHeader:SetJustifyH("LEFT")
    local enabledHeader = Widgets:CreateText(row, Theme.fonts.small, "生效", "muted")
    enabledHeader:SetPoint("TOPLEFT", row, "TOPLEFT", 244, -36)
    local sortHeader = Widgets:CreateText(row, Theme.fonts.small, "排序", "muted")
    sortHeader:SetPoint("TOPRIGHT", row, "TOPRIGHT", -92, -36)
    local actionHeader = Widgets:CreateText(row, Theme.fonts.small, "操作", "muted")
    actionHeader:SetPoint("TOPRIGHT", row, "TOPRIGHT", -12, -36)

    local frame = self:GetFrame()
    local state = frame._HUIState
    state.impRows = {}
    state.impHighlightIndex = nil

    if #entries == 0 then
      local emptyLine = CreateFrame("Frame", nil, row)
      emptyLine:SetPoint("TOPLEFT", row, "TOPLEFT", 0, listTop)
      emptyLine:SetPoint("TOPRIGHT", row, "TOPRIGHT", 0, listTop)
      emptyLine:SetHeight(44)
      local emptyBg = emptyLine:CreateTexture(nil, "BACKGROUND")
      emptyBg:SetAllPoints()
      local emptyColor = Theme:Color("panelSoft")
      emptyBg:SetColorTexture(emptyColor[1], emptyColor[2], emptyColor[3], emptyColor[4] or 1)
      local empty = Widgets:CreateText(row, Theme.fonts.small, "暂无自定义 Buff ID（点击添加或回车新增）", "muted")
      empty:SetPoint("LEFT", emptyLine, "LEFT", 14, 0)
    end

    for index = 1, #entries do
      local item = entries[index]
      local lineTop = listTop - (index - 1) * 48
      local line = CreateFrame("Frame", nil, row)
      line:SetPoint("TOPLEFT", row, "TOPLEFT", 0, lineTop)
      line:SetPoint("TOPRIGHT", row, "TOPRIGHT", 0, lineTop)
      line:SetHeight(44)
      line:EnableMouse(true)
      local selected = (item.spellID == state.importantSelectedSpell)
      local stripeBase = selected and { 0.16, 0.32, 0.46, 0.95 }
        or (index % 2 == 0 and Theme:Color("panelSoft") or Theme:Color("row"))
      local stripe = line:CreateTexture(nil, "BACKGROUND")
      stripe:SetAllPoints()
      stripe:SetColorTexture(stripeBase[1], stripeBase[2], stripeBase[3], stripeBase[4] or 1)
      line._impStripe = stripe
      stripe._impBase = stripeBase

      local icon = line:CreateTexture(nil, "ARTWORK")
      icon:SetSize(22, 22)
      icon:SetPoint("LEFT", line, "LEFT", 14, 0)
      icon:SetTexture(item.icon)
      icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
      local nameText = Widgets:CreateText(line, Theme.fonts.small, item.label .. "\nID:" .. tostring(item.spellID), "text")
      nameText:SetPoint("LEFT", icon, "RIGHT", 8, 0)
      nameText:SetWidth(190)
      nameText:SetJustifyH("LEFT")

      local enabledToggle = Widgets:CreateToggle(line, item.enabled ~= false, function(checked)
        if type(control.setEnabled) == "function" then control.setEnabled(item.spellID, checked) end
      end)
      enabledToggle:SetPoint("LEFT", line, "LEFT", 244, 0)

      local grip = CreateFrame("Frame", nil, line)
      grip:SetSize(12, 16)
      grip:SetPoint("RIGHT", line, "RIGHT", -94, 0)
      grip:EnableMouse(true)
      grip:SetAlpha(0.7)
      grip:SetScript("OnEnter", function(self) self:SetAlpha(1) end)
      grip:SetScript("OnLeave", function(self) self:SetAlpha(0.7) end)
      for r = 0, 1 do
        for c = 0, 2 do
          local dot = grip:CreateTexture(nil, "OVERLAY")
          dot:SetSize(2, 2)
          dot:SetPoint("CENTER", grip, "CENTER", (c - 1) * 5, (r - 0.5) * 5)
          dot:SetColorTexture(0.6, 0.66, 0.72, 0.85)
        end
      end
      grip:SetScript("OnMouseDown", function(self, button)
        if button ~= "LeftButton" then return end
        if not (type(control.reorderEntry) == "function" or type(addon.ReorderImportantSpell) == "function") then return end
        local cx, cy = GetCursorPosition()
        state.impDrag = {
          fromIndex = index,
          startX = cx, startY = cy,
          spellID = item.spellID,
          labelText = item.label,
          app = app, control = control,
          moved = false,
        }
        UI:GetImpDragger():Show()
      end)

      local upButton = Widgets:CreateActionButton(line, "↑", 22, 20, function()
        if type(control.moveEntry) == "function" then control.moveEntry(index, -1) end
      end)
      upButton:SetPoint("RIGHT", line, "RIGHT", -64, 0)
      local downButton = Widgets:CreateActionButton(line, "↓", 22, 20, function()
        if type(control.moveEntry) == "function" then control.moveEntry(index, 1) end
      end)
      downButton:SetPoint("RIGHT", line, "RIGHT", -36, 0)
      local removeButton = Widgets:CreateActionButton(line, "×", 22, 20, function()
        if type(control.removeEntry) == "function" then control.removeEntry(item.spellID) end
      end)
      removeButton:SetPoint("RIGHT", line, "RIGHT", -8, 0)

      line:SetScript("OnMouseDown", function(self, button)
        if button ~= "LeftButton" then return end
        UI:OpenImportantDetail(app, control, item.spellID)
      end)

      state.impRows[index] = line
    end

    row:SetHeight(math.max(64, 60 + math.max(#entries, 1) * 48 + 6))
    row._huiRenderedHeight = row:GetHeight()
    row.SetSelected = function() end

    UI:RefreshImportantDetail(app, control)
    return row
  end

  if controlType == "macroheader" then
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)
    row:SetHeight(Theme.sizes.rowHeight)

    local idHeader = Widgets:CreateText(row, Theme.fonts.small, control.idLabel or "标识", "muted")
    idHeader:SetPoint("LEFT", row, "LEFT", 14, 0)
    idHeader:SetWidth(150)
    idHeader:SetJustifyH("LEFT")

    local iconHeader = Widgets:CreateText(row, Theme.fonts.small, control.iconLabel or "图标", "muted")
    iconHeader:SetPoint("LEFT", idHeader, "RIGHT", 8, 0)
    iconHeader:SetWidth(84)
    iconHeader:SetJustifyH("LEFT")

    local macroHeader = Widgets:CreateText(row, Theme.fonts.small, control.macroLabel or "宏内容", "muted")
    macroHeader:SetPoint("LEFT", iconHeader, "RIGHT", 8, 0)
    macroHeader:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    macroHeader:SetJustifyH("LEFT")

    row.SetSelected = function() end
    row._huiRenderedHeight = Theme.sizes.rowHeight
    return row
  end

  if controlType == "macroedit" then
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)
    row:SetHeight(Theme.sizes.rowHeight)

    local value = app:GetValue(control) or {}
    local idText = Widgets:CreateText(row, Theme.fonts.small, control.idLabel or "", "text")
    idText:SetPoint("LEFT", row, "LEFT", 14, 0)
    idText:SetWidth(150)
    idText:SetJustifyH("LEFT")

    local iconInput = Widgets:CreateInput(row, tostring(value.icon or ""), function(text)
      if type(control.setIcon) == "function" then control.setIcon(text) end
    end)
    iconInput:SetSize(84, 22)
    iconInput:SetPoint("LEFT", idText, "RIGHT", 8, 0)
    if iconInput.editBox then iconInput.editBox:SetJustifyH("LEFT") end
    CollectListener(row, iconInput)
    if iconInput.bg then
      local frame = self:GetFrame()
      frame._HUIState.controlBgs = frame._HUIState.controlBgs or {}
      frame._HUIState.controlBgs[#frame._HUIState.controlBgs + 1] = iconInput.bg
    end

    local macroInput = Widgets:CreateInput(row, tostring(value.macro or ""), function(text)
      if type(control.setMacro) == "function" then control.setMacro(text) end
    end)
    macroInput:SetPoint("LEFT", iconInput, "RIGHT", 8, 0)
    macroInput:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    if macroInput.editBox then macroInput.editBox:SetJustifyH("LEFT") end
    CollectListener(row, macroInput)
    if macroInput.bg then
      local frame = self:GetFrame()
      frame._HUIState.controlBgs = frame._HUIState.controlBgs or {}
      frame._HUIState.controlBgs[#frame._HUIState.controlBgs + 1] = macroInput.bg
    end

    local rowHeight = math.max(Theme.sizes.rowHeight, 28)
    row:SetHeight(rowHeight)
    row._huiRenderedHeight = rowHeight
    row.SetSelected = function() end
    return row
  end

  if controlType == "hekiliMacroEditor" then
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)

    local rows = type(control.getRows) == "function" and control.getRows(control) or {}
    local rowHeight = 28
    local gap = 4
    local headerHeight = 30
    local totalHeight = headerHeight

    local headerAnchor = Track(row, CreateFrame("Frame", nil, row))
    headerAnchor:SetPoint("TOPLEFT", row, "TOPLEFT", 0, 0)
    headerAnchor:SetPoint("TOPRIGHT", row, "TOPRIGHT", 0, 0)
    headerAnchor:SetHeight(headerHeight)

    local idHeader = Widgets:CreateText(headerAnchor, Theme.fonts.heading, control.idLabel or "技能ID", "text")
    idHeader:SetPoint("LEFT", headerAnchor, "LEFT", 14, 0)
    idHeader:SetWidth(170)
    idHeader:SetJustifyH("LEFT")

    local macroHeader = Widgets:CreateText(headerAnchor, Theme.fonts.heading, control.macroLabel or "宏内容", "text")
    macroHeader:SetPoint("LEFT", idHeader, "RIGHT", 8, 0)
    macroHeader:SetPoint("RIGHT", headerAnchor, "RIGHT", -12, 0)
    macroHeader:SetJustifyH("LEFT")

    local headerLine = headerAnchor:CreateTexture(nil, "ARTWORK")
    local headerAccent = Theme:Color("accent")
    headerLine:SetHeight(1)
    headerLine:SetColorTexture(headerAccent[1], headerAccent[2], headerAccent[3], 0.8)
    headerLine:SetPoint("TOPLEFT", headerAnchor, "BOTTOMLEFT", 14, 0)
    headerLine:SetPoint("TOPRIGHT", headerAnchor, "BOTTOMRIGHT", -12, 0)

    local cursor = -headerHeight
    for index, item in ipairs(rows) do
      local line = Track(row, CreateFrame("Frame", nil, row))
      line:SetPoint("TOPLEFT", row, "TOPLEFT", 0, cursor)
      line:SetPoint("TOPRIGHT", row, "TOPRIGHT", 0, cursor)
      line:SetHeight(rowHeight)

      local idInput = Widgets:CreateInput(row, tostring(item and item.ident or ""), function(text)
        if type(control.setIdent) == "function" then control.setIdent(index, text) end
      end)
      idInput:SetSize(170, 22)
      idInput:SetPoint("LEFT", line, "LEFT", 14, 0)
      if idInput.editBox then idInput.editBox:SetJustifyH("LEFT") end
      if idInput.editBox then
        idInput.editBox:SetScript("OnTextChanged", function(input)
          if type(control.setIdent) == "function" then control.setIdent(index, input:GetText()) end
        end)
      end
      CollectListener(row, idInput)
      if idInput.bg then
        local frame = self:GetFrame()
        frame._HUIState.controlBgs = frame._HUIState.controlBgs or {}
        frame._HUIState.controlBgs[#frame._HUIState.controlBgs + 1] = idInput.bg
      end

      local deleteButton = Widgets:CreateActionButton(row, "×", 24, 22, function()
        if type(control.removeRow) == "function" then control.removeRow(index) end
      end)
      deleteButton:SetPoint("RIGHT", line, "RIGHT", -12, 0)

      local macroInput = Widgets:CreateInput(
        row,
        tostring(item and item.macro or ""),
        function(text)
          if type(control.setMacro) == "function" then control.setMacro(index, text) end
        end
      )
      macroInput:SetPoint("LEFT", idInput, "RIGHT", 8, 0)
      macroInput:SetPoint("RIGHT", deleteButton, "LEFT", -8, 0)
      if macroInput.editBox then macroInput.editBox:SetJustifyH("LEFT") end
      if macroInput.editBox then
        macroInput.editBox:SetScript("OnTextChanged", function(input)
          if type(control.setMacro) == "function" then control.setMacro(index, input:GetText()) end
        end)
      end
      CollectListener(row, macroInput)
      if macroInput.bg then
        local frame = self:GetFrame()
        frame._HUIState.controlBgs = frame._HUIState.controlBgs or {}
        frame._HUIState.controlBgs[#frame._HUIState.controlBgs + 1] = macroInput.bg
      end

      cursor = cursor - rowHeight - gap
      totalHeight = totalHeight + rowHeight + gap
    end

    if not control.noAdd then
      local plusRow = Track(row, CreateFrame("Frame", nil, row))
      plusRow:SetPoint("TOPLEFT", row, "TOPLEFT", 0, cursor)
      plusRow:SetPoint("TOPRIGHT", row, "TOPRIGHT", 0, cursor)
      plusRow:SetHeight(24)
      local plusButton = Widgets:CreateActionButton(row, "+", 26, 22, function()
        if type(control.addRow) == "function" then control.addRow() end
      end)
      plusButton:SetPoint("LEFT", plusRow, "LEFT", 14, 0)

      totalHeight = totalHeight + 24 + gap
    end
    row:SetHeight(totalHeight)
    row._huiRenderedHeight = totalHeight
    row.SetSelected = function() end
    return row
  end
  if controlType == "about" then
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)

    local logoW = tonumber(control.logoWidth) or 360
    local logoH = tonumber(control.logoHeight) or 180
    local padTop = 24
    local padBottom = 24
    local gapAfterLogo = 18
    local titleH = 16
    local gapBeforeLines = 14
    local lineH = 16
    local totalHeight = padTop + logoH + gapAfterLogo + titleH + gapBeforeLines + #(control.lines or {}) * lineH + padBottom
    row:SetHeight(totalHeight)

    local logo = row:CreateTexture(nil, "ARTWORK")
    logo:SetTexture(control.logo or "Interface\\AddOns\\YY_BuffReminder\\LibHUI\\Assets\\YY_BuffReminder.tga")
    logo:SetSize(logoW, logoH)
    logo:SetPoint("TOP", row, "TOP", 0, -padTop)

    local title = Widgets:CreateText(row, Theme.fonts.heading, control.title or "", "text")
    title:SetPoint("TOP", logo, "BOTTOM", 0, -gapAfterLogo)
    title:SetPoint("LEFT", row, "LEFT", 14, 0)
    title:SetPoint("RIGHT", row, "RIGHT", -14, 0)
        title:SetJustifyH(control.align or "LEFT")
    local lines = control.lines or {}
    local lastAnchor = title
    for _, line in ipairs(lines) do
      local fs = Widgets:CreateText(row, Theme.fonts.small, line.text or "", "muted")
      fs:SetPoint("TOP", lastAnchor, "BOTTOM", 0, -gapBeforeLines)
      fs:SetPoint("LEFT", row, "LEFT", 14, 0)
      fs:SetPoint("RIGHT", row, "RIGHT", -14, 0)
      fs:SetJustifyH(control.align or "LEFT")
      fs:SetTextColor(line.color[1], line.color[2], line.color[3], 1)
      lastAnchor = fs
    end

    row.SetSelected = function() end
    return row
  end

  if controlType == "changelog" then
    if reuseRow and reuseRow.Hide then reuseRow:Hide() end
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)

    local entries = control.entries or {}
    local padTop = 14
    local padBottom = 14
    local versionHeight = 18
    local gapBeforeLines = 4
    local lineGap = 4
    local entryGap = 16
    local cursorY = -padTop

    for _, entry in ipairs(entries) do
      local version = Widgets:CreateText(row, Theme.fonts.heading, entry.version or "", "text")
      version:SetPoint("TOPLEFT", row, "TOPLEFT", 14, cursorY)
      version:SetPoint("TOPRIGHT", row, "TOPRIGHT", -14, 0)
      version:SetJustifyH("LEFT")
      version:SetWordWrap(true)
      version:SetTextColor(0.95, 0.97, 1, 1)
      cursorY = cursorY - versionHeight - gapBeforeLines
      local bodyLines = entry.lines or {}
      for _, lineText in ipairs(bodyLines) do
        local fs = Widgets:CreateText(row, Theme.fonts.small, lineText, "muted")
        fs:SetPoint("TOPLEFT", row, "TOPLEFT", 28, cursorY)
        fs:SetPoint("TOPRIGHT", row, "TOPRIGHT", -14, 0)
        fs:SetJustifyH("LEFT")
        fs:SetWordWrap(true)
        local lineHeight = fs:GetStringHeight()
        if type(lineHeight) ~= "number" or lineHeight < 16 then lineHeight = 16 end
        cursorY = cursorY - lineHeight - lineGap
      end
      cursorY = cursorY - entryGap
    end

    row:SetHeight(-cursorY + padBottom)
    row._huiRenderedHeight = row:GetHeight()
    row.SetSelected = function() end
    return row
  end
  if controlType == "flagtogglesheader" then
    local row = Track(parent, CreateFrame("Frame", nil, parent))
    row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
    row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)
    row:SetHeight(Theme.sizes.rowHeight)

    local nameHeader = Widgets:CreateText(row, Theme.fonts.small, control.label or "名称", "muted")
    nameHeader:SetPoint("LEFT", row, "LEFT", 14, 0)
    nameHeader:SetWidth(200)
    nameHeader:SetJustifyH("LEFT")

        local flags = control.flagLabels or { "显示", "高亮", "时间" }
    local defaultOffsets = { -38, -98, -158 }
    local offsets = control.flagOffsets or defaultOffsets
    for index = 1, #flags do
      local col = Widgets:CreateText(row, Theme.fonts.small, flags[index], "muted")
      col:SetWidth(52)
      col:SetPoint("RIGHT", row, "RIGHT", (offsets[index] or 0) + 26, 0)
      col:SetJustifyH("CENTER")
    end

    local line = row:CreateTexture(nil, "ARTWORK")
    line:SetHeight(1)
    line:SetColorTexture(0.25, 0.32, 0.42, 0.8)
    line:SetPoint("LEFT", row, "LEFT", 14, 0)
    line:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    line:SetPoint("TOP", row, "BOTTOM", 0, 0)

    row.SetSelected = function() end
    row._huiRenderedHeight = Theme.sizes.rowHeight
    return row
  end

  local row
  if reuseRow and reuseRow._huiRow then
    row = reuseRow
    ClearChildren(row)
    row:SetScript("OnClick", nil)
    row._labels = {}
    row._huiRenderedHeight = nil
  else
    row = Track(parent, Widgets:CreateRow(parent, Theme.sizes.rowHeight))
  end
  row:SetPoint("TOPLEFT", parent, "TOPLEFT", 0, yOffset)
  row:SetPoint("TOPRIGHT", parent, "TOPRIGHT", 0, yOffset)

  local enabledColor = app:IsControlEnabled(control) and "text" or "disabled"
  local label = Widgets:CreateText(row, Theme.fonts.small, control.label or control.id, enabledColor)
  label:SetPoint("LEFT", row, "LEFT", 14, 0)
  label:SetJustifyH("LEFT")

  local segmentLabels
  if control.labelSegments then
    label:SetWidth((label:GetStringWidth() or 0) + 2)
    local previous = label
    segmentLabels = {}
    local segmentCount = #control.labelSegments
    for index, segment in ipairs(control.labelSegments) do
      local segmentLabel = Widgets:CreateText(row, Theme.fonts.small, segment.text or "", enabledColor)
      segmentLabel:SetPoint("LEFT", previous, "RIGHT", segment.offset or 0, 0)
      segmentLabel:SetJustifyH("LEFT")
      segmentLabel:SetWordWrap(true)
      if index == segmentCount then
        segmentLabel:SetPoint("RIGHT", row, "CENTER", -8, 0)
      end
      if segment.outline then
        local fontPath, fontSize = segmentLabel:GetFont()
        if fontPath and fontSize then
          segmentLabel:SetFont(fontPath, fontSize, BG.hui.FontFlags("OUTLINE"))
        end
      end
      segmentLabels[#segmentLabels + 1] = segmentLabel
      previous = segmentLabel
    end
  else
    label:SetPoint("RIGHT", row, "CENTER", -8, 0)
  end

  if segmentLabels then
    local statusHeight = 0
    for _, segmentLabel in ipairs(segmentLabels) do
      local labelHeight = segmentLabel.GetStringHeight and segmentLabel:GetStringHeight() or 0
      if type(labelHeight) == "number" and labelHeight > statusHeight then
        statusHeight = labelHeight
      end
    end
    if statusHeight > Theme.sizes.rowHeight then
      local renderedHeight = math.ceil(statusHeight + 6)
      row:SetHeight(renderedHeight)
      row._huiRenderedHeight = renderedHeight
    end
  end

  row._labels = row._labels or {}
  row._labels[#row._labels + 1] = label
  if segmentLabels then
    for _, segmentLabel in ipairs(segmentLabels) do
      row._labels[#row._labels + 1] = segmentLabel
    end
  end

  local value = app:GetValue(control)

  if controlType == "button" then
    local btn = Widgets:CreateActionButton(row, control.buttonText or control.label or control.id, control.buttonWidth or 100, 22, function()
      if type(control.onClick) == "function" then
        control.onClick(control)
      end
    end)
    btn:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    control.widget = btn
  elseif controlType == "buttongroup" then
    local opts = control.options or {}
    local btns = {}
    local btnW = control.buttonWidth or 56
    local spacing = control.spacing or 6
    local function SelectBtn(v)
      for _, bb in ipairs(btns) do
        bb.selected = (bb._huiValue == v) or nil
        if bb.ApplyState then bb:ApplyState() end
      end
    end
    local last
    for i = #opts, 1, -1 do
      local opt = opts[i]
      local b = Widgets:CreateActionButton(row, opt.label or tostring(opt.value), btnW, 22, function()
        app:SetValue(control, opt.value)
        SelectBtn(opt.value)
      end, { grayInactive = true })
      b._huiValue = opt.value
      if not last then
        last = b
        b:SetPoint("RIGHT", row, "RIGHT", -12, 0)
      else
        b:SetPoint("RIGHT", last, "LEFT", -spacing, 0)
        last = b
      end
      btns[i] = b
    end
    SelectBtn(value)
    control.widgets = btns
    control._huiSelectBtn = SelectBtn
  elseif controlType == "togglerow" then
    local opts = control.options or {}
    local btns = {}
    local spacing = control.spacing or 6
    local function Sync()
      local current = app:GetValue(control) or {}
      for index = 1, #opts do
        local b = btns[index]
        if b then
          b.selected = current[opts[index].key] == true
          if b.ApplyState then b:ApplyState() end
        end
      end
    end
    local last
    for index = #opts, 1, -1 do
      local opt = opts[index]
      local b = Widgets:CreateActionButton(row, opt.label or tostring(opt.key), control.buttonWidth or 68, 22, function()
        if not app:IsControlEnabled(control) then return end
        local nextValue = app:GetValue(control) or {}
        nextValue[opt.key] = not (nextValue[opt.key] == true)
        app:SetValue(control, nextValue)
        Sync()
      end, { grayInactive = true })
      b._huiTogglerowKey = opt.key
      if not last then
        last = b
        b:SetPoint("RIGHT", row, "RIGHT", -12, 0)
      else
        b:SetPoint("RIGHT", last, "LEFT", -spacing, 0)
        last = b
      end
      btns[index] = b
    end
    Sync()
    if last then
      label:ClearAllPoints()
      label:SetPoint("LEFT", row, "LEFT", 14, 0)
      label:SetPoint("RIGHT", last, "LEFT", -8, 0)
    end
    control.widgets = btns
    control._huiTogglerowSync = Sync
  elseif controlType == "toggle" then
    local toggle = Widgets:CreateToggle(row, value, function(checked)
      if not app:IsControlEnabled(control) then return end
      app:SetValue(control, checked)

    end)
    toggle:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    if not app:IsControlEnabled(control) then
      toggle:Disable()
      toggle:SetAlpha(0.5)
    end
  elseif controlType == "flagbuttons" then
        local flagOrder = control.flagOrder or { "time", "highlight", "show" }
    local flagLabels = control.flagLabels or { "时间", "高亮", "显示" }
    local lastBtn
    for index = 1, #flagOrder do
      local flag = flagOrder[index]
      local btn = Widgets:CreateActionButton(row, flagLabels[index] or flag, 52, 22, function()
        if type(control.onFlagClick) == "function" then
          control.onFlagClick(control, flag)
        end
      end)
      if lastBtn then
        btn:SetPoint("RIGHT", lastBtn, "LEFT", -8, 0)
      else
        btn:SetPoint("RIGHT", row, "RIGHT", -12, 0)
      end
      lastBtn = btn
    end
  elseif controlType == "flagtoggles" then
        local flagOrder = control.flagOrder or { "time", "highlight", "show" }
    local lastToggle
    for index = 1, #flagOrder do
      local flag = flagOrder[index]
      local checked = type(value) == "table" and value[flag] == true or false
      local enabled = true
      if type(control.isFlagEnabled) == "function" then
        enabled = control.isFlagEnabled(control, flag) ~= false
      end
      local toggle = Widgets:CreateToggle(row, checked, function(newValue)
        if not enabled then return end
        local nextValue = app:GetValue(control) or {}
        nextValue[flag] = newValue
        app:SetValue(control, nextValue)
      end)
      if lastToggle then
        toggle:SetPoint("RIGHT", lastToggle, "LEFT", -8, 0)
      else
        toggle:SetPoint("RIGHT", row, "RIGHT", -12, 0)
      end
      if not enabled then
        toggle:Disable()
        toggle:SetAlpha(0.5)
      end
      lastToggle = toggle
    end
        if control.dropdownOptions and lastToggle then
      local ddValue = type(control.getDropdownValue) == "function" and control.getDropdownValue() or nil
      local dropdown = Widgets:CreateDropdown(row, control.dropdownOptions, ddValue, function(selected)
        if type(control.setDropdownValue) == "function" then
          control.setDropdownValue(selected)
        end
      end)
      local ddWidth = control.dropdownWidth or 140
      dropdown:SetSize(ddWidth, 22)
      dropdown:SetPoint("RIGHT", lastToggle, "LEFT", -8, 0)
      CollectListener(row, dropdown)
      if dropdown.bg then
        local f = self:GetFrame()
        f._HUIState.controlBgs = f._HUIState.controlBgs or {}
        f._HUIState.controlBgs[#f._HUIState.controlBgs + 1] = dropdown.bg
      end
            label:ClearAllPoints()
      label:SetPoint("LEFT", row, "LEFT", 14, 0)
      label:SetWidth(row:GetWidth() and math.max(80, row:GetWidth() / 2 - ddWidth - 140) or 120)
      label:SetJustifyH("LEFT")
    end
    if control.rightLabel then
      local rightText = Widgets:CreateText(row, Theme.fonts.small, control.rightLabel, enabledColor)
      rightText:SetPoint("RIGHT", row, "RIGHT", -192, 0)
      rightText:SetJustifyH("RIGHT")
      row._labels[#row._labels + 1] = rightText
    end
  elseif controlType == "remarktoggle" then
    local remarkWidth = control.remarkWidth or 64
    local toggle = Widgets:CreateToggle(row, value, function(checked)
      if not app:IsControlEnabled(control) then return end
      app:SetValue(control, checked)
    end)
    toggle:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    if not app:IsControlEnabled(control) then
      toggle:Disable()
      toggle:SetAlpha(0.5)
    end
    local remarkText = ""
    if type(control.getRemark) == "function" then
      remarkText = tostring(control.getRemark() or "")
    end
    local remark = Widgets:CreateInput(row, remarkText, function(text)
      if type(control.setRemark) == "function" then control.setRemark(text) end
    end)
    remark:SetSize(remarkWidth, 22)
    remark:SetPoint("RIGHT", toggle, "LEFT", -8, 0)
    CollectListener(row, remark)
    if remark.bg then
      local f = self:GetFrame()
      f._HUIState.controlBgs = f._HUIState.controlBgs or {}
      f._HUIState.controlBgs[#f._HUIState.controlBgs + 1] = remark.bg
    end
    label:ClearAllPoints()
    label:SetPoint("LEFT", row, "LEFT", 14, 0)
    label:SetPoint("RIGHT", remark, "LEFT", -8, 0)
  elseif controlType == "slider" then
    local function FormatValue(v)
      return control.formatter and control.formatter(v) or tostring(tonumber(v) or v)
    end

    local valueText = row._huiValueText
    if valueText and valueText.SetText then
      valueText:SetParent(row)
      valueText:ClearAllPoints()
      valueText:SetPoint("RIGHT", row, "RIGHT", -12, 0)
      valueText:SetJustifyH("RIGHT")
      valueText:SetText(FormatValue(value))
      valueText:Show()
    else
      valueText = Widgets:CreateText(row, Theme.fonts.small, FormatValue(value), "text")
      valueText:SetPoint("RIGHT", row, "RIGHT", -12, 0)
      valueText:SetJustifyH("RIGHT")
      row._huiValueText = valueText
    end

    local slider = Widgets:CreateSlider(row, value, control.min, control.max, control.step, function(currentValue)
      app:SetValue(control, currentValue)
    end)
    CollectListener(row, slider)
    slider:SetSize(150, 16)
    slider:SetPoint("RIGHT", valueText, "LEFT", -8, 0)

    slider:HookScript("OnValueChanged", function(_, currentValue)
      valueText:SetText("")
      valueText:SetText(FormatValue(currentValue))
    end)
  elseif controlType == "input" then
    local input = Widgets:CreateInput(row, value, function(text)
      app:SetValue(control, text)
    end)
    input:SetSize(180, 22)
    input:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    CollectListener(row, input)
    if input.bg then
      local f = self:GetFrame()
      f._HUIState.controlBgs = f._HUIState.controlBgs or {}
      f._HUIState.controlBgs[#f._HUIState.controlBgs + 1] = input.bg
    end
  elseif controlType == "dropdown" then
    local opts = control.options or {}
    local dropdown = Widgets:CreateDropdown(row, opts, value, function(selected)
      app:SetValue(control, selected)
    end)
    dropdown:SetSize(180, 22)
    dropdown:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    CollectListener(row, dropdown)
    if dropdown.bg then
      local f = self:GetFrame()
      f._HUIState.controlBgs = f._HUIState.controlBgs or {}
      f._HUIState.controlBgs[#f._HUIState.controlBgs + 1] = dropdown.bg
    end
  elseif controlType == "colorpicker" then
    local initColor = value
    if type(initColor) == "string" then
      local hex = initColor:gsub("#", "")
      if hex:match("^%x%x%x%x%x%x$") then
        initColor = {
          tonumber(hex:sub(1,2), 16) / 255,
          tonumber(hex:sub(3,4), 16) / 255,
          tonumber(hex:sub(5,6), 16) / 255,
          1,
        }
      end
    end
    local picker = Widgets:CreateColorPicker(row, initColor, function(c)
      app:SetValue(control, c)
    end)
    picker:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    CollectListener(row, picker)
  elseif controlType == "keybind" then
    local keybind = Widgets:CreateKeybind(row, value, function(key)
      app:SetValue(control, key)
    end)
    keybind:SetSize(180, 22)
    keybind:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    CollectListener(row, keybind)
  elseif controlType == "multidropdown" then
    local opts = control.options or {}
    local multiDropdown = Widgets:CreateMultiDropdown(row, opts, value, function(selected)
      app:SetValue(control, selected)
    end)
    multiDropdown:SetSize(180, 22)
    multiDropdown:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    CollectListener(row, multiDropdown)
  elseif controlType == "iconpicker" then
    local picker = Widgets:CreateIconPicker(row, value, control.icons, function(icon)
      app:SetValue(control, icon)
    end)
    picker:SetPoint("RIGHT", row, "RIGHT", -12, 0)
    CollectListener(row, picker)
  elseif controlType == "reorderlist" then
    local items = control.items or value or {}
    local list = Widgets:CreateReorderList(row, items, function(newOrder)
      app:SetValue(control, newOrder)
    end)
    label:ClearAllPoints()
    label:SetPoint("TOPLEFT", row, "TOPLEFT", 14, -7)
    list:SetPoint("TOPLEFT", row, "TOPLEFT", 0, -(Theme.sizes.rowHeight))
    list:SetPoint("TOPRIGHT", row, "TOPRIGHT", 0, -(Theme.sizes.rowHeight))
    local listHeight = (#items) * 28
    if listHeight <= 0 then listHeight = 28 end
    local renderedHeight = Theme.sizes.rowHeight + listHeight
    row:SetHeight(renderedHeight)
    row._huiRenderedHeight = renderedHeight
    row.SetSelected = function() end
  else
    local valueText = Widgets:CreateText(row, Theme.fonts.small, tostring(value or ""), "muted")
    valueText:SetPoint("RIGHT", row, "RIGHT", -12, 0)
  end

  row:SetScript("OnClick", function(self)
    local frame = UI:GetFrame()
    for _, existingRow in ipairs(frame._HUIState.rows) do
      existingRow:SetSelected(existingRow == self)
    end

  end)

  row._huiRow = true

  local frame = self:GetFrame()
  frame._HUIState.rows[#frame._HUIState.rows + 1] = row

  return row
end

function UI:Render(appOrID, pageID)
  local app = Config:GetAddOn(appOrID)
  if not app then
    return
  end

  local frame = self:GetFrame()
  frame._HUIState.app = app
  frame._HUIState.rows = {}
  frame._HUIState.controlBgs = {}

  local previousPage = frame._HUIState.page
  local previousPageID = previousPage and previousPage.id
  local listScroll = frame.listScroll
  local previousScroll = listScroll and listScroll.scrollFrame and listScroll.scrollFrame:GetVerticalScroll() or 0

  local page = pageID and app.pages[pageID] or app:GetFirstPage()
  if not page then
    return
  end
  if not self:IsPageVisible(page) then
    page = app:GetFirstPage()
  end
  if not page then
    return
  end
  frame._HUIState.page = page

  if page.id ~= "imp_list" then
    local st = frame._HUIState
    if st.importantDetail then st.importantDetail:Hide() end
    st.importantSelectedSpell = nil
    st.impRows = nil
    st.impHighlightIndex = nil
    if st.impDrag then st.impDrag = nil end
    if st.impDragFrame then st.impDragFrame:Hide() end
  end

  if type(page.onSelect) == "function" then
    page.onSelect(page)
  end

  if app.opts.logo then
    frame.logo:SetTexture(app.opts.logo)
    frame.logo:Show()
  else
    frame.logo:Hide()
  end

  Widgets:DestroyManagedPopups()
  self:RenderNav(app, page)
  self:RenderSubNav(app, page)

  local samePage = (page.id == previousPageID)
  local controlRows = frame._HUIState.controlRows
  if not samePage then
    ClearChildren(frame.list)
    frame._HUIState.controlRows = {}
    controlRows = frame._HUIState.controlRows
  end

  local currentCategory = page.category and app.categories[page.category]
  local moduleDisabled = currentCategory
    and type(currentCategory.getEnabled) == "function"
    and not currentCategory.getEnabled()

  if moduleDisabled then
    frame.subnav:Hide()
    local disabledRow = Track(frame.list, CreateFrame("Frame", nil, frame.list))
    disabledRow:SetPoint("TOPLEFT", frame.list, "TOPLEFT", 0, 0)
    disabledRow:SetPoint("TOPRIGHT", frame.list, "TOPRIGHT", 0, 0)
    disabledRow:SetHeight(80)
    local msg = Widgets:CreateText(disabledRow, Theme.fonts.heading,
      currentCategory.title .. " 已关闭", "muted")
    msg:SetPoint("CENTER")
    msg:SetJustifyH("CENTER")
    local hint = Widgets:CreateText(disabledRow, Theme.fonts.small,
      "点击左侧开关按钮可重新启用", "muted")
    hint:SetPoint("TOP", msg, "BOTTOM", 0, -8)
    hint:SetJustifyH("CENTER")
    disabledRow.SetSelected = function() end
    frame.list:SetHeight(frame.listScroll.scrollFrame:GetHeight() or 460)
    frame.listScroll.scrollFrame:SetVerticalScroll(0)
    return
  end

  if samePage then
    for _, oldRow in pairs(controlRows) do
      if oldRow and oldRow.Hide then oldRow:Hide() end
    end
  end

  local yOffset = 0
  local renderedGroups = {}
  local firstRow = true
  local collapsedHeader = nil

  for _, control in ipairs(page.controls) do
    local isCollapsibleHeader = control.type == "groupheader" and control.collapsible ~= false
    if isCollapsibleHeader then
      collapsedHeader = IsHeaderCollapsed(app, control) and control or nil
    end

    if collapsedHeader and not isCollapsibleHeader then
      local hiddenRow = controlRows[control.id]
      if hiddenRow then
        if hiddenRow.Hide then hiddenRow:Hide() end
        DiscardRow(frame.list, hiddenRow)
        controlRows[control.id] = nil
      end
    elseif app:IsControlVisible(control) then
      if control.groupID and not renderedGroups[control.groupID] then
        local group = app.groups[control.groupID]
        if group then
          local groupHeader = controlRows["__group_" .. control.groupID]
          if not groupHeader then
            groupHeader = Track(frame.list, Widgets:CreateGroupHeader(frame.list, group.title or group.id, 20))
            controlRows["__group_" .. control.groupID] = groupHeader
          end
          groupHeader:ClearAllPoints()
          groupHeader:SetPoint("TOPLEFT", frame.list, "TOPLEFT", 0, yOffset)
          groupHeader:SetPoint("TOPRIGHT", frame.list, "TOPRIGHT", 0, yOffset)
          groupHeader:Show()
          yOffset = yOffset - 28
          renderedGroups[control.groupID] = true
        end
      end

      local forceRebuild = control.type == "importanteditor"
        or control.type == "previewbar"
        or control.type == "macroedit"
        or control.type == "macroheader"
        or control.type == "hekiliMacroEditor"
        or control.type == "about"
        or control.type == "changelog"
      local reuseRow = (samePage and not forceRebuild) and controlRows[control.id] or nil
      if forceRebuild and samePage and controlRows[control.id] then
        DetachRegion(controlRows[control.id])
        controlRows[control.id] = nil
      end
      local alwaysReplace = control.type == "groupheader"
        or control.type == "divider"
        or control.type == "label"
      local row = self:RenderControl(app, frame.list, control, yOffset, reuseRow)
      if row and row.Show then row:Show() end
      if not samePage or reuseRow == nil or alwaysReplace then
        controlRows[control.id] = row
      end
      if firstRow then
        row:SetSelected(true)
        firstRow = false
      end
      local renderedHeight = row and row._huiRenderedHeight or Theme.sizes.rowHeight
      yOffset = yOffset - renderedHeight - 4
    end
  end

  if samePage then
    for cid, oldRow in pairs(controlRows) do
      if type(cid) == "string" and cid ~= "" and not cid:find("^__group_") then
        local stillVisible = false
        for _, control in ipairs(page.controls) do
          if control.id == cid and app:IsControlVisible(control) then
            stillVisible = true
            break
          end
        end
        if not stillVisible and oldRow and oldRow.Hide then
          oldRow:Hide()
          controlRows[cid] = nil
        end
      end
    end
  end

  local totalHeight = -yOffset
  frame.list:SetHeight(math.max(totalHeight, frame.listScroll.scrollFrame:GetHeight() or 460))
  if page.id == previousPageID then
    frame.listScroll.scrollFrame:SetVerticalScroll(previousScroll)
  else
    frame.listScroll.scrollFrame:SetVerticalScroll(0)
  end

end

function UI:Open(appOrID, pageID)
  local frame = self:GetFrame()

  self:Render(appOrID, pageID)
  frame:Show()
end

function UI:Toggle(appOrID, pageID)
  local frame = self:GetFrame()
  if frame:IsShown() then
    frame:Hide()
  else
    self:Open(appOrID, pageID)
  end
end

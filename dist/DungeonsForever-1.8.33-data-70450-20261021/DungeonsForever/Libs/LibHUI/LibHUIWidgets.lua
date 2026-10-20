local addonName, addon = ...

addon.LibHUI = addon.LibHUI or {}

local HUI = addon.LibHUI
local Theme = HUI.Theme
local Widgets = {}

local CreateFrame = CreateFrame
local type = type
local tonumber = tonumber
local tostring = tostring

HUI.Widgets = Widgets

local L = HUI.L

local function SetColor(texture, color)
  texture:SetColorTexture(color[1], color[2], color[3], color[4])
end

function Widgets:CreatePanel(parent, name)
  local panel = CreateFrame("Frame", name, parent, "BackdropTemplate")
  local panelColor = Theme:Color("panel")

  panel:SetBackdrop({
    bgFile = "Interface\\Buttons\\WHITE8X8",
    edgeFile = "Interface\\Buttons\\WHITE8X8",
    edgeSize = 1,
  })
  panel:SetBackdropColor(panelColor[1], panelColor[2], panelColor[3], panelColor[4])

  local function ApplyAccent()
    local accent = Theme:Color("accent")
    panel:SetBackdropBorderColor(accent[1] * 0.55, accent[2] * 0.55, accent[3] * 0.55, 0.70)
  end
  ApplyAccent()
  Theme:OnAccentChanged(ApplyAccent)

  local inner = panel:CreateTexture(nil, "BACKGROUND", nil, 1)
  inner:SetColorTexture(0, 0, 0, 0.24)
  inner:SetPoint("TOPLEFT", 1, -1)
  inner:SetPoint("BOTTOMRIGHT", -1, 1)

  panel.inner = inner

  return panel
end

function Widgets:CreateTexture(parent, color)
  local texture = parent:CreateTexture(nil, "BACKGROUND")
  SetColor(texture, color)
  return texture
end

function Widgets:CreateText(parent, template, text, colorName)
  local fontString = parent:CreateFontString(nil, "OVERLAY", template or Theme.fonts.body)
  fontString:SetText(text or "")

  local color = Theme:Color(colorName or "text")
  fontString:SetTextColor(color[1], color[2], color[3], color[4])

  return fontString
end

function Widgets:CreateButton(parent, text, width, height, accentSide)
  local button = CreateFrame("Button", nil, parent)
  button:SetSize(width or 120, height or 28)

  button.bg = self:CreateTexture(button, Theme:Color("button"))
  button.bg:SetAllPoints()

  button.accent = button:CreateTexture(nil, "OVERLAY")
  local verticalAccent = accentSide == "left"
  local function ApplyAccentBar()
    local accent = Theme:Color("accent")
    local active = button.selected or button.hovered
    if button.selected then
      local dark = Theme:Color("accentDark")
      button.accent:SetColorTexture(dark[1], dark[2], dark[3], 1)
    else
      button.accent:SetColorTexture(accent[1], accent[2], accent[3], active and 1 or 0.35)
    end
    if verticalAccent then
      button.accent:SetWidth(active and 4 or 3)
    else
      button.accent:SetHeight(active and 3 or 2)
    end
    button.accent:Show()
  end
  ApplyAccentBar()
  if verticalAccent then
    button.accent:SetPoint("TOPLEFT")
    button.accent:SetPoint("BOTTOMLEFT")
  else
    button.accent:SetPoint("BOTTOMLEFT")
    button.accent:SetPoint("BOTTOMRIGHT")
  end

  button.text = self:CreateText(button, Theme.fonts.body, text, "text")
  button.text:SetPoint("CENTER")

  local function RefreshColors()
    ApplyAccentBar()
    if button.selected then
      SetColor(button.bg, Theme:Color("accent"))
      local textColor = Theme:Color("textDark")
      button.text:SetTextColor(textColor[1], textColor[2], textColor[3], textColor[4] or 1)
      button.text:SetShadowColor(0, 0, 0, 0)
    else
      SetColor(button.bg, Theme:Color("button"))
      local textColor = Theme:Color("text")
      button.text:SetTextColor(textColor[1], textColor[2], textColor[3], textColor[4] or 1)
      button.text:SetShadowColor(0, 0, 0, 1)
      button.text:SetShadowOffset(1, -1)
    end
  end
  button._huiListenerID = Theme:OnAccentChanged(RefreshColors)

  function button:SetSelected(selected)
    self.selected = selected and true or false
    RefreshColors()
  end

  button:SetScript("OnEnter", function(self)
    self.hovered = true
    if not self.selected then
      SetColor(self.bg, Theme:Color("buttonHover"))
    end
    ApplyAccentBar()
  end)
  button:SetScript("OnLeave", function(self)
    self.hovered = false
    if self.selected then
      SetColor(self.bg, Theme:Color("accent"))
    else
      SetColor(self.bg, Theme:Color("button"))
    end
    ApplyAccentBar()
  end)
  button:SetScript("OnMouseDown", function(self)
    SetColor(self.bg, Theme:Color("accent"))
    ApplyAccentBar()
  end)
  button:SetScript("OnMouseUp", function(self)
    if not self.selected then
      SetColor(self.bg, Theme:Color("buttonHover"))
    end
    ApplyAccentBar()
  end)

  button:SetSelected(false)
  return button
end

Widgets._actionButtons = Widgets._actionButtons or {}
function Widgets:RefreshAllButtonStyles()
  for _, btn in ipairs(self._actionButtons) do
    if btn.ApplyState then btn:ApplyState() end
  end
end

function Widgets:CreateActionButton(parent, text, width, height, onClick, options)
  local button = CreateFrame("Button", nil, parent)
  button:SetSize(width or 120, height or 28)

  local normalAsset = Theme:Asset("rowNormal")

  button.bg = button:CreateTexture(nil, "BACKGROUND")
  button.bg:SetAllPoints()

  local function MakeEdge(p1, p2, w, h)
    local e = button:CreateTexture(nil, "BORDER")
    e:SetPoint(p1, button, p1, 0, 0)
    if p2 then e:SetPoint(p2, button, p2, 0, 0) end
    if w then e:SetWidth(w) end
    if h then e:SetHeight(h) end
    return e
  end
  button.borderTop = MakeEdge("TOPLEFT", "TOPRIGHT", nil, 1)
  button.borderBottom = MakeEdge("BOTTOMLEFT", "BOTTOMRIGHT", nil, 1)
  button.borderLeft = MakeEdge("TOPLEFT", "BOTTOMLEFT", 1, nil)
  button.borderRight = MakeEdge("TOPRIGHT", "BOTTOMRIGHT", 1, nil)
  local borders = { button.borderTop, button.borderBottom, button.borderLeft, button.borderRight }

  button.bottomBar = button:CreateTexture(nil, "OVERLAY")
  button.bottomBar:SetPoint("BOTTOMLEFT", button, "BOTTOMLEFT", 0, 0)
  button.bottomBar:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", 0, 0)
  button.bottomBar:SetHeight(2)

  button.leftBar = button:CreateTexture(nil, "OVERLAY")
  button.leftBar:SetPoint("TOPLEFT", button, "TOPLEFT", 0, 0)
  button.leftBar:SetPoint("BOTTOMLEFT", button, "BOTTOMLEFT", 0, 0)
  button.leftBar:SetWidth(3)

  button.topGlow = button:CreateTexture(nil, "OVERLAY")
  button.topGlow:SetPoint("TOPLEFT", button, "TOPLEFT", 0, 0)
  button.topGlow:SetPoint("TOPRIGHT", button, "TOPRIGHT", 0, 0)
  button.topGlow:SetHeight(1)

  button.bottomShadow = button:CreateTexture(nil, "OVERLAY")
  button.bottomShadow:SetPoint("BOTTOMLEFT", button, "BOTTOMLEFT", 0, 0)
  button.bottomShadow:SetPoint("BOTTOMRIGHT", button, "BOTTOMRIGHT", 0, 0)
  button.bottomShadow:SetHeight(1)

  button.text = self:CreateText(button, Theme.fonts.body, text, "text")
  button.text:SetPoint("CENTER")

  local function SetBorder(color, alpha)
    for _, e in ipairs(borders) do
      e:SetColorTexture(color[1], color[2], color[3], alpha or color[4] or 1)
      e:Show()
    end
  end

  local function HideDecor(self)
    for _, e in ipairs(borders) do e:Hide() end
    self.bottomBar:Hide(); self.leftBar:Hide(); self.topGlow:Hide(); self.bottomShadow:Hide()
  end

  local function SetText(self, dark)
    if dark then
      local tc = Theme:Color("textDark")
      self.text:SetTextColor(tc[1], tc[2], tc[3], tc[4] or 1)
      self.text:SetShadowColor(0, 0, 0, 0)
    else
      local tc = Theme:Color("text")
      self.text:SetTextColor(tc[1], tc[2], tc[3], tc[4] or 1)
      self.text:SetShadowColor(0, 0, 0, 1)
      self.text:SetShadowOffset(1, -1)
    end
  end

  local function ApplyState(self)
    local style = (addon.db and addon.db.settings and addon.db.settings.buttonStyle) or "underline"
    local accent = Theme:Color("accent")
    local hovered = self.hovered or self.selected
    HideDecor(self)

        local bgOptions = options and options.bgColor
    if bgOptions then
      local color = hovered and (options.bgHover or options.bgColor) or options.bgColor
      self.bg:SetColorTexture(color[1], color[2], color[3], color[4] or 1)
      SetText(self, false)
      return
    end

    if style == "classic" then
      if hovered then
        self.bg:SetColorTexture(accent[1], accent[2], accent[3], accent[4] or 1)
        SetBorder(accent)
        SetText(self, true)
      else
        if normalAsset then
          self.bg:SetTexture(normalAsset, "CLAMP", "CLAMP")
          self.bg:SetVertexColor(1, 1, 1, 1)
        else
          local color = Theme:Color("button")
          self.bg:SetColorTexture(color[1], color[2], color[3], color[4])
        end
        SetBorder({0x15/255, 0x1f/255, 0x29/255, 1})
        SetText(self, false)
      end

    elseif style == "flat" then
      if hovered then
        self.bg:SetColorTexture(accent[1], accent[2], accent[3], accent[4] or 1)
        SetText(self, true)
      else
        local color = Theme:Color("button")
        self.bg:SetColorTexture(color[1], color[2], color[3], color[4])
        SetText(self, false)
      end

    elseif style == "underline" then
      local color = hovered and Theme:Color("buttonHover") or Theme:Color("button")
      self.bg:SetColorTexture(color[1], color[2], color[3], color[4])
      self.bottomBar:SetColorTexture(accent[1], accent[2], accent[3], hovered and 1.0 or 0.35)
      self.bottomBar:SetHeight(hovered and 3 or 2)
      self.bottomBar:Show()
      SetText(self, false)

    elseif style == "leftbar" then
      local color = hovered and Theme:Color("buttonHover") or Theme:Color("button")
      self.bg:SetColorTexture(color[1], color[2], color[3], color[4])
      self.leftBar:SetColorTexture(accent[1], accent[2], accent[3], hovered and 1.0 or 0.35)
      self.leftBar:Show()
      SetText(self, false)

    elseif style == "pill" then
      if hovered then
        self.bg:SetColorTexture(accent[1], accent[2], accent[3], accent[4] or 1)
        self.topGlow:SetColorTexture(1, 1, 1, 0.15); self.topGlow:Show()
        SetText(self, true)
      else
        local color = Theme:Color("button")
        self.bg:SetColorTexture(color[1], color[2], color[3], color[4])
        self.topGlow:SetColorTexture(1, 1, 1, 0.06); self.topGlow:Show()
        self.bottomShadow:SetColorTexture(0, 0, 0, 0.25); self.bottomShadow:Show()
        SetText(self, false)
      end

    elseif style == "faint" then
      local color = hovered and Theme:Color("buttonHover") or Theme:Color("button")
      self.bg:SetColorTexture(color[1], color[2], color[3], color[4])
      SetBorder(accent, hovered and 0.9 or 0.15)
      SetText(self, false)

    elseif style == "float" then
      if hovered then
        local rh = Theme:Color("buttonHover")
        self.bg:SetColorTexture(rh[1], rh[2], rh[3], rh[4])
        self.topGlow:SetColorTexture(1, 1, 1, 0.12); self.topGlow:Show()
        self.bottomShadow:SetColorTexture(0, 0, 0, 0.40); self.bottomShadow:SetHeight(2); self.bottomShadow:Show()
        SetText(self, false)
      else
        local color = Theme:Color("button")
        self.bg:SetColorTexture(color[1], color[2], color[3], color[4])
        self.topGlow:SetColorTexture(1, 1, 1, 0.08); self.topGlow:Show()
        self.bottomShadow:SetColorTexture(0, 0, 0, 0.30); self.bottomShadow:SetHeight(1); self.bottomShadow:Show()
        SetText(self, false)
      end

    else
      local color = Theme:Color("button")
      self.bg:SetColorTexture(color[1], color[2], color[3], color[4])
      SetText(self, false)
    end

    if options and options.grayInactive and not self.selected and not self.hovered then
      local tc = Theme:Color("muted")
      self.text:SetTextColor(tc[1], tc[2], tc[3], tc[4] or 1)
      self.text:SetShadowColor(0, 0, 0, 1)
      self.text:SetShadowOffset(1, -1)
    end
  end

  button.ApplyState = ApplyState

  button:SetScript("OnEnter", function(self)
    self.hovered = true
    ApplyState(self)
  end)
  button:SetScript("OnLeave", function(self)
    self.hovered = false
    ApplyState(self)
  end)
  button:SetScript("OnClick", function(self)
    if type(onClick) == "function" then
      onClick(self)
    end
  end)

  button._huiListenerID = Theme:OnAccentChanged(function()
    ApplyState(button)
  end)

  function button:SetText(value)
    self.text:SetText(value or "")
  end

  if parent then
    parent._huiActionButtons = parent._huiActionButtons or {}
    parent._huiActionButtons[#parent._huiActionButtons + 1] = button
  end

  Widgets._actionButtons[#Widgets._actionButtons + 1] = button

  ApplyState(button)
  return button
end

function Widgets:CreateGroupHeader(parent, text, height, opts)
  local collapsible = opts and opts.collapsible or false
  local header = CreateFrame(collapsible and "Button" or "Frame", nil, parent)
  header:SetHeight(height or 20)

  local label = (text or ""):upper()

  local box

  if collapsible then
    header:EnableMouse(true)

    local hoverBg = header:CreateTexture(nil, "BACKGROUND")
    hoverBg:SetAllPoints()
    local hoverColor = Theme:Color("rowHover")
    hoverBg:SetColorTexture(hoverColor[1], hoverColor[2], hoverColor[3], 0.35)
    hoverBg:Hide()
    header._huiHoverBg = hoverBg

    box = header:CreateTexture(nil, "ARTWORK")
    box:SetSize(14, 14)
    box:SetPoint("LEFT", header, "LEFT", 4, 0)
    local boxColor = Theme:Color("row")
    box:SetColorTexture(boxColor[1], boxColor[2], boxColor[3], 0.95)

    local boxInner = header:CreateTexture(nil, "ARTWORK")
    boxInner:SetSize(12, 12)
    boxInner:SetPoint("CENTER", box, "CENTER", 0, 0)
    local innerColor = Theme:Color("panel")
    boxInner:SetColorTexture(innerColor[1], innerColor[2], innerColor[3], 0.95)

    local mark = header:CreateFontString(nil, "OVERLAY")
    mark:SetFont(STANDARD_TEXT_FONT or "Fonts\\ARIALN.TTF", 13, BG.hui.FontFlags("OUTLINE"))
    mark:SetPoint("CENTER", box, "CENTER", 0, 0)
    header._huiMark = mark
  end

  header.text = self:CreateText(header, Theme.fonts.small, label, "text")
  if collapsible then
    header.text:SetPoint("LEFT", box, "RIGHT", 6, 0)
  else
    header.text:SetPoint("LEFT", header, "LEFT", 8, 0)
  end
  header.text:SetJustifyH("LEFT")
  header.text:SetTextColor(0x08/255, 0x13/255, 0x24/255, 1)
  header.text:SetShadowColor(0, 0, 0, 0)
  header.text:SetShadowOffset(0, 0)

  header.tag = header:CreateTexture(nil, "BACKGROUND")
  if collapsible then
    header.tag:SetPoint("LEFT", header.text, "LEFT", -6, 0)
  else
    header.tag:SetPoint("LEFT", header, "LEFT", 0, 0)
  end
  header.tag:SetPoint("TOP", header, "TOP", 0, 0)
  header.tag:SetPoint("BOTTOM", header, "BOTTOM", 0, 0)
  header.tag:SetPoint("RIGHT", header.text, "RIGHT", 8, 0)

  header.line = header:CreateTexture(nil, "ARTWORK")
  header.line:SetHeight(1)
  header.line:SetPoint("LEFT", header.tag, "RIGHT", 6, 0)
  header.line:SetPoint("RIGHT", header, "RIGHT", -2, 0)

  local function ApplyAccent()
    local accent = Theme:Color("accent")
    if header._huiCollapsed then
      local muted = Theme:Color("muted")
      header.tag:SetColorTexture(muted[1], muted[2], muted[3], 0.8)
      header.line:SetColorTexture(accent[1], accent[2], accent[3], 0.4)
    else
      header.tag:SetColorTexture(
        accent[1] + (1 - accent[1]) * 0.55,
        accent[2] + (1 - accent[2]) * 0.55,
        accent[3] + (1 - accent[3]) * 0.55,
        0.95)
      header.line:SetColorTexture(accent[1], accent[2], accent[3], 0.9)
    end
    if header._huiMark then
      header._huiMark:SetTextColor(accent[1], accent[2], accent[3], 1)
    end
  end
  ApplyAccent()
  header._huiListenerID = Theme:OnAccentChanged(ApplyAccent)

  function header:SetText(value)
    self.text:SetText((value or ""):upper())
  end

  function header:SetCollapsed(value)
    self._huiCollapsed = value and true or false
    if self._huiMark then
      self._huiMark:SetText(self._huiCollapsed and "+" or "-")
    end
    ApplyAccent()
  end

  if collapsible then
    header:SetCollapsed(opts.collapsed)
    header:SetScript("OnClick", function(self)
      if type(opts.onToggle) == "function" then
        opts.onToggle(self, not self._huiCollapsed)
      end
    end)
    header:SetScript("OnEnter", function(self)
      if self._huiHoverBg then self._huiHoverBg:Show() end
      local tooltip = GameTooltip
      if not tooltip then return end
      tooltip:SetOwner(self, "ANCHOR_RIGHT")
      tooltip:SetText(self._huiCollapsed and "点击展开该分组" or "点击收起该分组", 1, 0.82, 0.1)
      tooltip:Show()
    end)
    header:SetScript("OnLeave", function(self)
      if self._huiHoverBg then self._huiHoverBg:Hide() end
      local tooltip = GameTooltip
      if tooltip and tooltip:GetOwner() == self then tooltip:Hide() end
    end)
  end

  return header
end

function Widgets:CreateRow(parent, height)
  local row = CreateFrame("Button", nil, parent)
  row:SetHeight(height or Theme.sizes.rowHeight)
  row:EnableMouse(true)

  row.bg = row:CreateTexture(nil, "BACKGROUND")
  row.bg:SetAllPoints()
  local _initRowColor = Theme:Color("row")
  row.bg:SetColorTexture(_initRowColor[1], _initRowColor[2], _initRowColor[3], _initRowColor[4] or 1)

  row.borderTop = row:CreateTexture(nil, "BORDER")
  row.borderTop:SetColorTexture(0x15/255, 0x1f/255, 0x29/255, 1)
  row.borderTop:SetPoint("TOPLEFT")
  row.borderTop:SetPoint("TOPRIGHT")
  row.borderTop:SetHeight(1)

  row.borderBottom = row:CreateTexture(nil, "BORDER")
  row.borderBottom:SetColorTexture(0x15/255, 0x1f/255, 0x29/255, 1)
  row.borderBottom:SetPoint("BOTTOMLEFT")
  row.borderBottom:SetPoint("BOTTOMRIGHT")
  row.borderBottom:SetHeight(1)

  row.borderLeft = row:CreateTexture(nil, "BORDER")
  row.borderLeft:SetColorTexture(0x15/255, 0x1f/255, 0x29/255, 1)
  row.borderLeft:SetPoint("TOPLEFT")
  row.borderLeft:SetPoint("BOTTOMLEFT")
  row.borderLeft:SetWidth(1)

  row.borderRight = row:CreateTexture(nil, "BORDER")
  row.borderRight:SetColorTexture(0x15/255, 0x1f/255, 0x29/255, 1)
  row.borderRight:SetPoint("TOPRIGHT")
  row.borderRight:SetPoint("BOTTOMRIGHT")
  row.borderRight:SetWidth(1)

  row.accent = row:CreateTexture(nil, "OVERLAY")
  local accent = Theme:Color("accent")
  row.accent:SetColorTexture(accent[1] * 0.4, accent[2] * 0.4, accent[3] * 0.4, 1)
  row.accent:SetPoint("TOPLEFT")
  row.accent:SetPoint("BOTTOMLEFT")
  row.accent:SetWidth(4)
  row.accent:Hide()

  local function ApplyState(self)
    local accent = Theme:Color("accent")
    local borderColor
    local useDarkText = false
    if self.selected then
      self.bg:SetColorTexture(accent[1], accent[2], accent[3], accent[4] or 1)
      borderColor = accent
      useDarkText = true
    elseif self.hovered then
      local hc = Theme:Color("rowHover")
      self.bg:SetColorTexture(hc[1], hc[2], hc[3], hc[4] or 1)
      borderColor = {0x15/255, 0x1f/255, 0x29/255, 1}
    else
      local rc = Theme:Color("row")
      if self._zebra then
        self.bg:SetColorTexture(rc[1] * 0.65, rc[2] * 0.65, rc[3] * 0.65, rc[4] or 1)
      else
        self.bg:SetColorTexture(rc[1], rc[2], rc[3], rc[4] or 1)
      end
      borderColor = {0x15/255, 0x1f/255, 0x29/255, 1}
    end

    SetColor(self.borderTop, borderColor)
    SetColor(self.borderBottom, borderColor)
    SetColor(self.borderLeft, borderColor)
    SetColor(self.borderRight, borderColor)

    if self._labels then
      local textColor = useDarkText and Theme:Color("textDark") or Theme:Color("text")
      for _, lbl in ipairs(self._labels) do
        lbl:SetTextColor(textColor[1], textColor[2], textColor[3], textColor[4] or 1)
        if useDarkText then
          lbl:SetShadowColor(0, 0, 0, 0)
        else
          lbl:SetShadowColor(0, 0, 0, 1)
          lbl:SetShadowOffset(1, -1)
        end
      end
    end
  end

  row:SetScript("OnEnter", function(self)
    self.hovered = true
    ApplyState(self)
  end)
  row:SetScript("OnLeave", function(self)
    self.hovered = false
    ApplyState(self)
  end)

  function row:SetSelected(selected)
    self.selected = selected and true or false
    self.accent:SetShown(self.selected)
    ApplyState(self)
  end

  row._huiListenerID = Theme:OnAccentChanged(function()
    local updated = Theme:Color("accent")
    row.accent:SetColorTexture(updated[1] * 0.4, updated[2] * 0.4, updated[3] * 0.4, 1)
    ApplyState(row)
  end)

  row:SetSelected(false)
  return row
end

function Widgets:CreateToggle(parent, checked, onChanged)
  local button = CreateFrame("Button", nil, parent)
  button:SetSize(52, 22)

  button.bg = self:CreateTexture(button, Theme:Color("toggleOff"))
  button.bg:SetAllPoints()

  local function MakeEdge() return button:CreateTexture(nil, "BORDER") end
  button.edgeTop = MakeEdge(); button.edgeTop:SetPoint("TOPLEFT"); button.edgeTop:SetPoint("TOPRIGHT"); button.edgeTop:SetHeight(1)
  button.edgeBottom = MakeEdge(); button.edgeBottom:SetPoint("BOTTOMLEFT"); button.edgeBottom:SetPoint("BOTTOMRIGHT"); button.edgeBottom:SetHeight(1)
  button.edgeLeft = MakeEdge(); button.edgeLeft:SetPoint("TOPLEFT"); button.edgeLeft:SetPoint("BOTTOMLEFT"); button.edgeLeft:SetWidth(1)
  button.edgeRight = MakeEdge(); button.edgeRight:SetPoint("TOPRIGHT"); button.edgeRight:SetPoint("BOTTOMRIGHT"); button.edgeRight:SetWidth(1)

  button.thumb = self:CreateTexture(button, Theme:Color("accent"))
  button.thumb:SetDrawLayer("OVERLAY")
  button.thumb:SetSize(18, 18)

  local thumbW, thumbH = 18, 18
  local leftX, rightX = 4, 30
  local animDuration = 0.38

  local function ApplyAccent()
    local accent = Theme:Color("accent")
    local muted = Theme:Color("muted")
    SetColor(button.bg, Theme:Color("toggleOff"))
    if button.checked then
      local edgeColor = { accent[1], accent[2], accent[3], 0.8 }
      for _, e in ipairs({ button.edgeTop, button.edgeBottom, button.edgeLeft, button.edgeRight }) do
        SetColor(e, edgeColor)
      end
      SetColor(button.thumb, accent)
    else
      local edgeColor = { muted[1], muted[2], muted[3], 0.8 }
      for _, e in ipairs({ button.edgeTop, button.edgeBottom, button.edgeLeft, button.edgeRight }) do
        SetColor(e, edgeColor)
      end
      SetColor(button.thumb, muted)
    end
  end

  local function AnimateThumbTo(targetX, endW, endH)
    local startX = button._animX or (button.checked and rightX or leftX)
    local startTime = GetTime()
    button._animX = targetX

    local function easeOutCubic(p)
      return 1 - math.pow(1 - p, 3)
    end

    button:SetScript("OnUpdate", function(self)
      local elapsed = GetTime() - startTime
      local t = math.min(elapsed / animDuration, 1)

      local x = startX + (targetX - startX) * easeOutCubic(t)

      local squash = math.sin(t * math.pi)
      local w = endW * (1 - 0.35 * squash)
      local h = endH * (1 + 0.22 * squash)

      x = math.max(leftX, math.min(rightX, x))
      w = math.min(w, 52 - x - 2)

      self.thumb:ClearAllPoints()
      self.thumb:SetPoint("LEFT", self, "LEFT", x, 0)
      self.thumb:SetSize(w, h)
      if t >= 1 then
        self.thumb:SetSize(endW, endH)
        self:SetScript("OnUpdate", nil)
      end
    end)
  end

  local function SnapToTarget(targetX)
    button._animX = targetX
    button.thumb:ClearAllPoints()
    button.thumb:SetPoint("LEFT", button, "LEFT", targetX, 0)
    button.thumb:SetSize(thumbW, thumbH)
  end

  function button:SetChecked(value, animate)
    self.checked = value and true or false
    local targetX = self.checked and rightX or leftX
    if animate then
      AnimateThumbTo(targetX, thumbW, thumbH)
    else
      SnapToTarget(targetX)
    end
    ApplyAccent()
  end

  button._huiListenerID = Theme:OnAccentChanged(ApplyAccent)

  button.SetValue = button.SetChecked
  function button:GetValue()
    return self.checked
  end

  button:SetScript("OnClick", function(self)
    self:SetChecked(not self.checked, true)
    if type(onChanged) == "function" then
      onChanged(self.checked)
    end
  end)

  button:SetChecked(checked, false)
  return button
end

function Widgets:CreateSlider(parent, value, minValue, maxValue, step, onChanged)
  local slider = CreateFrame("Slider", nil, parent)
  slider:SetOrientation("HORIZONTAL")
  slider:SetMinMaxValues(minValue or 0, maxValue or 100)
  slider:SetValueStep(step or 1)
  slider:SetObeyStepOnDrag(true)
  slider:SetHeight(16)

  slider.track = slider:CreateTexture(nil, "BACKGROUND")
  slider.track:SetHeight(3)
  slider.track:SetPoint("LEFT")
  slider.track:SetPoint("RIGHT")
  slider.track:SetColorTexture(0x20/255, 0x2a/255, 0x36/255, 1)

  slider.fill = slider:CreateTexture(nil, "ARTWORK")
  slider.fill:SetHeight(3)
  slider.fill:SetPoint("LEFT", slider.track, "LEFT", 0, 0)

  local thumbW, thumbH = 12, 22
  slider.thumbTex = slider:CreateTexture(nil, "OVERLAY")
  slider.thumbTex:SetSize(thumbW, thumbH)
  slider:SetThumbTexture(slider.thumbTex)

  slider.thumbCap = slider:CreateTexture(nil, "OVERLAY", nil, 1)
  slider.thumbCap:SetColorTexture(1, 1, 1, 0.55)
  slider.thumbCap:SetSize(thumbW, 2)

  slider.thumbBase = slider:CreateTexture(nil, "OVERLAY", nil, 1)
  slider.thumbBase:SetColorTexture(0, 0, 0, 0.45)
  slider.thumbBase:SetSize(thumbW, 2)

  local function ApplyAccent()
    local accent = Theme:Color("accent")
    local br = accent[1] + (1 - accent[1]) * 0.55
    local bg = accent[2] + (1 - accent[2]) * 0.55
    local bb = accent[3] + (1 - accent[3]) * 0.55
    slider.fill:SetColorTexture(br, bg, bb, 1)
    slider.thumbTex:SetColorTexture(br, bg, bb, 1)
  end
  ApplyAccent()
  slider._huiListenerID = Theme:OnAccentChanged(ApplyAccent)

  local function UpdateFill(self, currentValue)
    local minV, maxV = self:GetMinMaxValues()
    local range = maxV - minV
    local pct = range > 0 and ((currentValue - minV) / range) or 0
    local width = self:GetWidth()
    if width and width > 0 then
      self.fill:SetWidth(math.max(1, width * pct))
      local xOff = pct * (width - thumbW)
      local yTop = -(self:GetHeight() - thumbH) / 2
      self.thumbCap:SetPoint("TOPLEFT", self, "TOPLEFT", xOff, yTop)
      self.thumbBase:SetPoint("BOTTOMLEFT", self, "BOTTOMLEFT", xOff, (self:GetHeight() - thumbH) / 2)
    end
  end

  slider:SetValue(tonumber(value) or minValue or 0)

  slider:SetScript("OnShow", function(self)
    UpdateFill(self, self:GetValue())
  end)
  slider:SetScript("OnSizeChanged", function(self)
    UpdateFill(self, self:GetValue())
  end)
  slider:SetScript("OnValueChanged", function(self, currentValue)
    UpdateFill(self, currentValue)
    if type(onChanged) == "function" then
      onChanged(currentValue)
    end
  end)

  slider:EnableMouseWheel(true)
  slider:SetScript("OnMouseWheel", function(self, delta)
    local minV, maxV = self:GetMinMaxValues()
    local step = self:GetValueStep() or 1
    local newValue = self:GetValue() + delta * step
    newValue = math.floor(newValue / step + 0.5) * step
    newValue = math.max(minV, math.min(maxV, newValue))
    self:SetValue(newValue)
  end)

  return slider
end

local _openDropdown = nil
local _managedPopups = {}

local function RegisterManagedPopup(...)
  local frames = {...}
  for i = 1, #frames do
    local frame = frames[i]
    if frame then
      _managedPopups[#_managedPopups + 1] = frame
    end
  end
end

local function ClearFrameList(list)
  for i = 1, #list do
    local frame = list[i]
    if frame then
      frame:Hide()
      frame:SetParent(nil)
    end
  end
  wipe(list)
end

function Widgets:CloseManagedPopups()
  for i = 1, #_managedPopups do
    local frame = _managedPopups[i]
    if frame and frame.Hide and frame:IsShown() then
      frame:Hide()
    end
  end
  _openDropdown = nil
end

function Widgets:DestroyManagedPopups()
  for i = 1, #_managedPopups do
    local frame = _managedPopups[i]
    if frame then
      frame:Hide()
      frame:SetParent(nil)
    end
  end
  wipe(_managedPopups)
  _openDropdown = nil
end

function Widgets:CreateDropdown(parent, options, currentValue, onChanged)
  local container = CreateFrame("Frame", nil, parent)
  container:SetSize(180, 24)

  container.bg = container:CreateTexture(nil, "BACKGROUND")
  container.bg:SetAllPoints()
  local _cA = (addon.db and addon.db.settings and addon.db.settings.controlAlpha) or 0.92
  local _cC = (addon.db and addon.db.settings and addon.db.settings.controlBgColor) or {0x0a/255, 0x12/255, 0x1c/255}
  container.bg:SetColorTexture(_cC[1], _cC[2], _cC[3], _cA)

  local selectedPreview = container:CreateTexture(nil, "BACKGROUND", nil, 1)
  selectedPreview:SetAllPoints()
  selectedPreview:SetVertexColor(0.55, 0.58, 0.62, 0.78)
  selectedPreview:Hide()

  local function MakeEdge() return container:CreateTexture(nil, "BORDER") end
  local et = MakeEdge(); et:SetPoint("TOPLEFT"); et:SetPoint("TOPRIGHT"); et:SetHeight(1)
  local eb = MakeEdge(); eb:SetPoint("BOTTOMLEFT"); eb:SetPoint("BOTTOMRIGHT"); eb:SetHeight(1)
  local el = MakeEdge(); el:SetPoint("TOPLEFT"); el:SetPoint("BOTTOMLEFT"); el:SetWidth(1)
  local er = MakeEdge(); er:SetPoint("TOPRIGHT"); er:SetPoint("BOTTOMRIGHT"); er:SetWidth(1)
  local edges = {et, eb, el, er}

  local function ApplyBorder(focused)
    local accent = Theme:Color("accent")
    local a = focused and 1 or 0.6
    for _, e in ipairs(edges) do e:SetColorTexture(accent[1], accent[2], accent[3], a) end
  end
  ApplyBorder(false)
  container._huiListenerID = Theme:OnAccentChanged(function() ApplyBorder(container._open) end)

  local displayText = container:CreateFontString(nil, "OVERLAY", Theme.fonts.body)
  displayText:SetPoint("LEFT", container, "LEFT", 8, 0)
  displayText:SetPoint("RIGHT", container, "RIGHT", -22, 0)
  displayText:SetJustifyH("RIGHT")
  displayText:SetTextColor(0.95, 0.96, 0.98, 1)

  local arrowSize = 10
  local arrow = container:CreateTexture(nil, "OVERLAY")
  arrow:SetSize(arrowSize, arrowSize)
  arrow:SetPoint("RIGHT", container, "RIGHT", -7, 0)
  arrow:SetTexture("Interface\\Buttons\\Arrow-Down-Up")
  arrow:SetVertexColor(0.75, 0.78, 0.82, 1)

  local function OptionColor(option)
    local color = option and option.color
    if color and color[1] and color[2] and color[3] then
      return color[1], color[2], color[3], color[4] or 1
    end
    return 0.95, 0.96, 0.98, 1
  end

  local function ApplySelection(option)
    container._value = option and option.value or nil
    displayText:SetText(option and (option.label or option.value) or "")
    displayText:SetTextColor(OptionColor(option))
    if option and option.texture then
      selectedPreview:SetTexture(option.texture)
      selectedPreview:Show()
    else
      selectedPreview:Hide()
    end
  end

  local popup = CreateFrame("Frame", nil, UIParent)
  popup:SetFrameStrata("FULLSCREEN_DIALOG")
  popup:SetClampedToScreen(true)
  popup:SetToplevel(true)
  popup:Hide()
  RegisterManagedPopup(popup)
  popup.bg = popup:CreateTexture(nil, "BACKGROUND")
  popup.bg:SetAllPoints()
  popup.bg:SetColorTexture(0x06/255, 0x0e/255, 0x16/255, 0.98)
  popup.border = CreateFrame("Frame", nil, popup, "BackdropTemplate")
  popup.border:SetAllPoints()
  popup.border:SetBackdrop({edgeFile="Interface\\Buttons\\WHITE8X8", edgeSize=1})
  popup.border:SetBackdropBorderColor(0.3, 0.3, 0.3, 0.8)

  local popupScroll = CreateFrame("ScrollFrame", nil, popup)
  popupScroll:SetPoint("TOPLEFT", popup, "TOPLEFT", 1, -1)
  popupScroll:SetPoint("BOTTOMRIGHT", popup, "BOTTOMRIGHT", -1, 1)
  popupScroll:EnableMouseWheel(true)
  local popupList = CreateFrame("Frame", nil, popupScroll)
  popupScroll:SetScrollChild(popupList)

  local popupTrack = popup:CreateTexture(nil, "BACKGROUND")
  popupTrack:SetWidth(8)
  popupTrack:SetColorTexture(0x0f/255, 0x17/255, 0x21/255, 0.85)
  popupTrack:SetPoint("TOPRIGHT", popup, "TOPRIGHT", -2, -2)
  popupTrack:SetPoint("BOTTOMRIGHT", popup, "BOTTOMRIGHT", -2, 2)
  popupTrack:Hide()

  local popupThumb = CreateFrame("Button", nil, popup)
  popupThumb:SetWidth(8)
  popupThumb:SetPoint("TOP", popupTrack, "TOP", 0, 0)
  popupThumb:Hide()
  local popupThumbTex = popupThumb:CreateTexture(nil, "OVERLAY")
  popupThumbTex:SetAllPoints()
  popupThumbTex:SetColorTexture(0.55, 0.62, 0.70, 0.9)

  local function UpdatePopupThumb()
    local scrollRange = popupScroll:GetVerticalScrollRange() or 0
    local viewHeight = popupScroll:GetHeight() or 1
    if scrollRange <= 0 then
      popupTrack:Hide()
      popupThumb:Hide()
      return
    end
    popupTrack:Show()
    popupThumb:Show()
    local ratio = viewHeight / (viewHeight + scrollRange)
    local thumbHeight = math.max(16, viewHeight * ratio)
    popupThumb:SetHeight(thumbHeight)
    local scrollPos = popupScroll:GetVerticalScroll() or 0
    local scrollPct = scrollRange > 0 and (scrollPos / scrollRange) or 0
    local trackHeight = popupTrack:GetHeight() or viewHeight
    local maxOffset = trackHeight - thumbHeight
    popupThumb:ClearAllPoints()
    popupThumb:SetPoint("TOP", popupTrack, "TOP", 0, -scrollPct * math.max(0, maxOffset))
  end

  popupScroll:SetScript("OnScrollRangeChanged", UpdatePopupThumb)
  popupScroll:SetScript("OnVerticalScroll", UpdatePopupThumb)
  popupScroll:SetScript("OnSizeChanged", UpdatePopupThumb)
  popupList:SetScript("OnSizeChanged", UpdatePopupThumb)
  popupScroll:SetScript("OnMouseWheel", function(scrollFrame, delta)
    local maxScroll = scrollFrame:GetVerticalScrollRange() or 0
    local newScroll = (scrollFrame:GetVerticalScroll() or 0) - delta * 20
    scrollFrame:SetVerticalScroll(math.max(0, math.min(newScroll, maxScroll)))
  end)

  popupThumb:EnableMouse(true)
  popupThumb:SetScript("OnMouseDown", function(thumb)
    thumb.dragging = true
    thumb.startY = select(2, GetCursorPosition()) / UIParent:GetEffectiveScale()
    thumb.startScroll = popupScroll:GetVerticalScroll()
  end)
  popupThumb:SetScript("OnMouseUp", function(thumb)
    thumb.dragging = false
  end)
  popupThumb:SetScript("OnUpdate", function(thumb)
    if not thumb.dragging then return end
    local currentY = select(2, GetCursorPosition()) / UIParent:GetEffectiveScale()
    local deltaY = thumb.startY - currentY
    local trackHeight = popupTrack:GetHeight() or 1
    local thumbHeight = thumb:GetHeight() or 16
    local maxOffset = trackHeight - thumbHeight
    local scrollRange = popupScroll:GetVerticalScrollRange() or 0
    if maxOffset > 0 and scrollRange > 0 then
      local scrollDelta = (deltaY / maxOffset) * scrollRange
      local newScroll = math.max(0, math.min(thumb.startScroll + scrollDelta, scrollRange))
      popupScroll:SetVerticalScroll(newScroll)
    end
  end)

  local function ClosePopup()
    popup:Hide()
    container._open = false
    arrow:SetRotation(0)
    ApplyBorder(false)
    if _openDropdown == container then _openDropdown = nil end
  end

  local function BuildPopup()
    for _, child in ipairs(popup._items or {}) do child:Hide(); child:SetParent(nil) end
    popup._items = {}

    local rowH = 22
    local w = container:GetWidth()
    popup:SetWidth(w)
    if not w or w < 60 then w = 180 end
    local screenH = UIParent:GetHeight() or 768
    local maxListH = math.max(120, screenH - 40)
    local listWidth = w - 2
    local listHeight = #options * rowH
    if listHeight > maxListH and #options > 0 then
        rowH = math.max(14, math.floor(maxListH / #options))
        listHeight = #options * rowH
    end
    popup:SetHeight(listHeight + 2)
    popupScroll:ClearAllPoints()
    popupScroll:SetPoint("TOPLEFT", popup, "TOPLEFT", 1, -1)
    popupScroll:SetPoint("BOTTOMRIGHT", popup, "BOTTOMRIGHT", -1, 1)
    popupScroll:SetSize(listWidth, listHeight)
    popupList:SetSize(listWidth, listHeight)
    popupScroll:SetVerticalScroll(0)

    for i, opt in ipairs(options) do
      local row = CreateFrame("Button", nil, popupList)
      row:SetSize(listWidth, rowH)
      row:SetPoint("TOPLEFT", popupList, "TOPLEFT", 0, -(i-1)*rowH)

      local rowBg = row:CreateTexture(nil, "BACKGROUND")
      rowBg:SetAllPoints()
      rowBg:SetColorTexture(0, 0, 0, 0)

      if opt.texture then
        local preview = row:CreateTexture(nil, "BACKGROUND", nil, 1)
        preview:SetAllPoints()
        preview:SetTexture(opt.texture)
        preview:SetVertexColor(0.58, 0.60, 0.64, 0.82)
      end

      local lbl = row:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
      lbl:SetPoint("LEFT", row, "LEFT", 10, 0)
      lbl:SetPoint("RIGHT", row, "RIGHT", -10, 0)
      lbl:SetJustifyH("RIGHT")
      local colorR, colorG, colorB, colorA = OptionColor(opt)
      lbl:SetTextColor(colorR, colorG, colorB, colorA)
      lbl:SetText(opt.label or opt.value or "")

      if opt.value == container._value and not opt.color then
        lbl:SetTextColor(Theme:Color("accent")[1], Theme:Color("accent")[2], Theme:Color("accent")[3], 1)
      end

      row:SetScript("OnEnter", function()
        rowBg:SetColorTexture(0.10, 0.20, 0.32, 0.85)
      end)
      row:SetScript("OnLeave", function()
        rowBg:SetColorTexture(0, 0, 0, 0)
      end)
      row:SetScript("OnClick", function()
        ApplySelection(opt)
        ClosePopup()
        if type(onChanged) == "function" then onChanged(opt.value) end
      end)

      popup._items[i] = row
    end

    UpdatePopupThumb()
  end

  local function OpenPopup()
    if _openDropdown and _openDropdown ~= container then
      _openDropdown:CloseDropdown()
    end
    BuildPopup()
    local screenH = UIParent:GetHeight() or 0
    local popupH = popup:GetHeight() or 0
    local containerH = container:GetHeight() or 24
    local _, y = container:GetCenter()
    local below = y and (y - containerH / 2 - 2) or 0
    local above = y and (screenH - y - containerH / 2 - 2) or 0
    popup:ClearAllPoints()
    if y and below >= popupH then
      popup:SetPoint("TOPLEFT", container, "BOTTOMLEFT", 0, -2)
    elseif y and above >= popupH then
      popup:SetPoint("BOTTOMLEFT", container, "TOPLEFT", 0, 2)
    elseif below >= above then
      popup:SetPoint("TOPLEFT", container, "BOTTOMLEFT", 0, -2)
    else
      popup:SetPoint("BOTTOMLEFT", container, "TOPLEFT", 0, 2)
    end
    popup:Show()
    container._open = true
    arrow:SetRotation(math.pi)
    ApplyBorder(true)
    _openDropdown = container
  end

  local clickArea = CreateFrame("Button", nil, container)
  clickArea:SetAllPoints()
  clickArea:SetScript("OnClick", function()
    if container._open then ClosePopup() else OpenPopup() end
  end)

  popup:SetScript("OnHide", function()
    container._open = false
    arrow:SetRotation(0)
    ApplyBorder(false)
  end)

  container.CloseDropdown = ClosePopup

  local function SetValue(_, value)
    for _, opt in ipairs(options) do
      if opt.value == value then
        ApplySelection(opt)
        return
      end
    end
    ApplySelection(nil)
  end
  SetValue(nil, currentValue)
  container.SetValue = SetValue
  container.GetValue = function() return container._value end
  container.SetOptions = function(_, newOptions)
    options = newOptions or {}
    if container._open then BuildPopup() end
    SetValue(nil, container._value)
  end

  return container
end

function Widgets:CreateMultiDropdown(parent, options, value, onChanged)

  local selectedValues = value or {}
  if type(selectedValues) ~= "table" then
    selectedValues = {}
  end

  local container = CreateFrame("Frame", nil, parent)
  container:SetSize(180, 24)

  local bg = container:CreateTexture(nil, "BACKGROUND")
  bg:SetAllPoints()
  bg:SetColorTexture(0x0a/255, 0x12/255, 0x1c/255, 0.92)

  local function MakeEdge() return container:CreateTexture(nil, "BORDER") end
  local et = MakeEdge(); et:SetPoint("TOPLEFT"); et:SetPoint("TOPRIGHT"); et:SetHeight(1)
  local eb = MakeEdge(); eb:SetPoint("BOTTOMLEFT"); eb:SetPoint("BOTTOMRIGHT"); eb:SetHeight(1)
  local el = MakeEdge(); el:SetPoint("TOPLEFT"); el:SetPoint("BOTTOMLEFT"); el:SetWidth(1)
  local er = MakeEdge(); er:SetPoint("TOPRIGHT"); er:SetPoint("BOTTOMRIGHT"); er:SetWidth(1)
  local edges = {et, eb, el, er}

  local function ApplyBorder(focused)
    local accent = Theme:Color("accent")
    local a = focused and 1 or 0.6
    for _, e in ipairs(edges) do e:SetColorTexture(accent[1], accent[2], accent[3], a) end
  end
  ApplyBorder(false)
  container._huiListenerID = Theme:OnAccentChanged(function() ApplyBorder(container._open) end)

  local displayText = container:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
  displayText:SetPoint("LEFT", container, "LEFT", 10, 0)
  displayText:SetPoint("RIGHT", container, "RIGHT", -24, 0)
  displayText:SetJustifyH("RIGHT")
  displayText:SetTextColor(0.90, 0.92, 0.95, 1)

  local function UpdateDisplay()
    local count = #selectedValues
    if count == 0 then
      displayText:SetText("|cff666666" .. L.noneSelected .. "|r")
    elseif count == 1 then
      for _, opt in ipairs(options) do
        if opt.value == selectedValues[1] then
          displayText:SetText(opt.label or opt.value)
          return
        end
      end
      displayText:SetText(selectedValues[1])
    else
      displayText:SetText(string.format(L.countSelected, count))
    end
  end

  UpdateDisplay()

  local arrowSize = 8
  local arrow = container:CreateTexture(nil, "OVERLAY")
  arrow:SetSize(arrowSize, arrowSize)
  arrow:SetPoint("RIGHT", container, "RIGHT", -8, 0)
  arrow:SetTexture("Interface\\Buttons\\Arrow-Down-Up")
  arrow:SetVertexColor(0.75, 0.78, 0.82, 1)

  local popup = CreateFrame("Frame", nil, UIParent)
  popup:SetFrameStrata("FULLSCREEN_DIALOG")
  popup:SetSize(200, 200)
  popup:Hide()
  RegisterManagedPopup(popup)

  local popupBg = popup:CreateTexture(nil, "BACKGROUND")
  popupBg:SetAllPoints()
  popupBg:SetColorTexture(0x06/255, 0x0e/255, 0x16/255, 0.98)

  local popupBorder = CreateFrame("Frame", nil, popup, "BackdropTemplate")
  popupBorder:SetAllPoints()
  popupBorder:SetBackdrop({edgeFile="Interface\\Buttons\\WHITE8X8", edgeSize=1})
  local accent = Theme:Color("accent")
  popupBorder:SetBackdropBorderColor(accent[1], accent[2], accent[3], 0.8)

  local scrollChild = CreateFrame("Frame", nil, popup)
  scrollChild:SetPoint("TOPLEFT", 8, -8)
  scrollChild:SetPoint("BOTTOMRIGHT", -8, 8)

  local rowHeight = 24
  local rows = {}

  local function IsSelected(val)
    for _, v in ipairs(selectedValues) do
      if v == val then return true end
    end
    return false
  end

  local function ToggleValue(val)
    local found = false
    for i, v in ipairs(selectedValues) do
      if v == val then
        table.remove(selectedValues, i)
        found = true
        break
      end
    end
    if not found then
      selectedValues[#selectedValues + 1] = val
    end
    UpdateDisplay()
    if type(onChanged) == "function" then
      onChanged(selectedValues)
    end
  end

  local function BuildRows()
    for _, row in ipairs(rows) do row:Hide() end
    wipe(rows)

    for i, opt in ipairs(options) do
      local row = CreateFrame("Button", nil, scrollChild)
      row:SetSize(180, rowHeight)
      row:SetPoint("TOPLEFT", scrollChild, "TOPLEFT", 0, -(i-1) * rowHeight)

      local rowBg = row:CreateTexture(nil, "BACKGROUND")
      rowBg:SetAllPoints()
      rowBg:SetColorTexture(0x0a/255, 0x12/255, 0x1c/255, 0.5)

      local check = self:CreateToggle(row, IsSelected(opt.value), function(checked)
        if checked ~= IsSelected(opt.value) then
          ToggleValue(opt.value)
          for _, r in ipairs(rows) do
            if r.check and r.optValue then
              r.check:SetValue(IsSelected(r.optValue))
            end
          end
        end
      end)
      check:SetPoint("LEFT", row, "LEFT", 6, 0)
      row.check = check
      row.optValue = opt.value

      local label = row:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
      label:SetPoint("LEFT", check, "RIGHT", 8, 0)
      label:SetPoint("RIGHT", row, "RIGHT", -8, 0)
      label:SetJustifyH("RIGHT")
      label:SetText(opt.label or opt.value)
      label:SetTextColor(0.90, 0.92, 0.95, 1)

      row:SetScript("OnEnter", function(self)
        rowBg:SetColorTexture(0x15/255, 0x1d/255, 0x27/255, 0.8)
      end)
      row:SetScript("OnLeave", function(self)
        rowBg:SetColorTexture(0x0a/255, 0x12/255, 0x1c/255, 0.5)
      end)

      row:SetScript("OnClick", function()
        check:SetValue(not check:GetValue())
      end)

      rows[#rows + 1] = row
    end

    scrollChild:SetHeight(#options * rowHeight)
  end

  BuildRows()

  local backdrop = CreateFrame("Frame", nil, UIParent)
  backdrop:SetFrameStrata("FULLSCREEN")
  backdrop:SetAllPoints(UIParent)
  backdrop:EnableMouse(true)
  backdrop:Hide()
  RegisterManagedPopup(backdrop)

  local function ClosePopup()
    popup:Hide()
    backdrop:Hide()
    container._open = false
    arrow:SetRotation(0)
    ApplyBorder(false)
  end

  local function OpenPopup()
    popup:ClearAllPoints()
    local _, py = container:GetCenter()
    if py and py < 220 then
      popup:SetPoint("TOPLEFT", container, "BOTTOMLEFT", 0, -4)
    else
      popup:SetPoint("BOTTOMLEFT", container, "TOPLEFT", 0, 4)
    end
    backdrop:Show()
    popup:Show()
    container._open = true
    arrow:SetRotation(math.pi)
    ApplyBorder(true)
  end

  backdrop:SetScript("OnMouseDown", function()
    ClosePopup()
  end)

  local button = CreateFrame("Button", nil, container)
  button:SetAllPoints()
  button:SetScript("OnClick", function()
    if container._open then ClosePopup() else OpenPopup() end
  end)

  popup:SetScript("OnHide", function()
    container._open = false
    arrow:SetRotation(0)
    ApplyBorder(false)
  end)

  container.SetValue = function(self, v)
    selectedValues = v or {}
    if type(selectedValues) ~= "table" then selectedValues = {} end
    UpdateDisplay()
    for _, row in ipairs(rows) do
      if row.check and row.optValue then
        row.check:SetValue(IsSelected(row.optValue))
      end
    end
  end

  container.GetValue = function(self)
    return selectedValues
  end

  return container
end

function Widgets:CreateDivider(parent)
  local line = parent:CreateTexture(nil, "ARTWORK")
  line:SetHeight(1)
  line:SetColorTexture(0x25/255, 0x33/255, 0x42/255, 0.9)
  return line
end

function Widgets:CreateLabel(parent, text, colorName)
  local label = parent:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
  label:SetText(text or "")
  local color = Theme:Color(colorName or "muted")
  label:SetTextColor(color[1], color[2], color[3], color[4] or 1)
  label:SetJustifyH("LEFT")
  label:SetWordWrap(true)
  return label
end

function Widgets:CreateKeybind(parent, value, onChanged)

  local container = CreateFrame("Button", nil, parent)
  container:SetSize(180, 24)

  local bg = container:CreateTexture(nil, "BACKGROUND")
  bg:SetAllPoints()
  bg:SetColorTexture(0x0a/255, 0x12/255, 0x1c/255, 0.92)

  local function MakeEdge() return container:CreateTexture(nil, "BORDER") end
  local et = MakeEdge(); et:SetPoint("TOPLEFT"); et:SetPoint("TOPRIGHT"); et:SetHeight(1)
  local eb = MakeEdge(); eb:SetPoint("BOTTOMLEFT"); eb:SetPoint("BOTTOMRIGHT"); eb:SetHeight(1)
  local el = MakeEdge(); el:SetPoint("TOPLEFT"); el:SetPoint("BOTTOMLEFT"); el:SetWidth(1)
  local er = MakeEdge(); er:SetPoint("TOPRIGHT"); er:SetPoint("BOTTOMRIGHT"); er:SetWidth(1)
  local edges = {et, eb, el, er}

  local function ApplyBorder(focused)
    local accent = Theme:Color("accent")
    local a = focused and 1 or 0.6
    for _, e in ipairs(edges) do e:SetColorTexture(accent[1], accent[2], accent[3], a) end
  end
  ApplyBorder(false)
  container._huiListenerID = Theme:OnAccentChanged(function() ApplyBorder(container._listening) end)

  local keyText = container:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
  keyText:SetPoint("CENTER")
  keyText:SetTextColor(0.90, 0.92, 0.95, 1)

  local currentValue = value or ""

  local function FormatKey(key)
    if not key or key == "" then
      return "|cff555555" .. L.notBound .. "|r"
    end
    return key
  end

  keyText:SetText(FormatKey(currentValue))

  container._listening = false

  local function StopListening(save)
    container._listening = false
    container:EnableKeyboard(false)
    container:SetScript("OnKeyDown", nil)
    ApplyBorder(false)
    bg:SetColorTexture(0x0a/255, 0x12/255, 0x1c/255, 0.92)
    keyText:SetText(FormatKey(currentValue))
    if save and type(onChanged) == "function" then
      onChanged(currentValue)
    end
  end

  local function StartListening()
    container._listening = true
    container:EnableKeyboard(true)
    ApplyBorder(true)
    bg:SetColorTexture(0x0a/255, 0x18/255, 0x2c/255, 0.96)
    keyText:SetText("|cffffc702" .. L.pressKey .. "|r")

    container:SetScript("OnKeyDown", function(self, key)
      if key == "ESCAPE" then
        StopListening(false)
        return
      end
      if key == "DELETE" or key == "BACKSPACE" then
        currentValue = ""
        StopListening(true)
        return
      end

      if key == "LSHIFT" or key == "RSHIFT" or key == "LCTRL" or key == "RCTRL"
        or key == "LALT" or key == "RALT" or key == "LMETA" or key == "RMETA" then
        return
      end

      local prefix = ""
      if IsShiftKeyDown and IsShiftKeyDown() then prefix = "SHIFT-" .. prefix end
      if IsControlKeyDown and IsControlKeyDown() then prefix = "CTRL-" .. prefix end
      if IsAltKeyDown and IsAltKeyDown() then prefix = "ALT-" .. prefix end

      currentValue = prefix .. key
      StopListening(true)
    end)
  end

  container:SetScript("OnClick", function(self)
    if self._listening then
      StopListening(false)
    else
      StartListening()
    end
  end)

  container:SetScript("OnHide", function()
    if container._listening then StopListening(false) end
  end)

  container.SetValue = function(self, v)
    currentValue = v or ""
    keyText:SetText(FormatKey(currentValue))
  end

  container.GetValue = function(self)
    return currentValue
  end

  return container
end

function Widgets:CreateIconPicker(parent, value, options, onChanged)

  local defaultIcons = {
    "Interface\\Icons\\INV_Misc_QuestionMark",
    "Interface\\Icons\\Spell_Fire_Fireball",
    "Interface\\Icons\\Spell_Frost_Frostbolt",
    "Interface\\Icons\\Spell_Nature_Lightning",
    "Interface\\Icons\\Spell_Holy_PowerWordShield",
    "Interface\\Icons\\Spell_Shadow_ShadowBolt",
    "Interface\\Icons\\Ability_Warrior_Charge",
    "Interface\\Icons\\Ability_Rogue_Vanish",
    "Interface\\Icons\\Ability_Hunter_SteadyShot",
    "Interface\\Icons\\Spell_Druid_Moonfire",
    "Interface\\Icons\\Spell_Arcane_Arcane01",
    "Interface\\Icons\\Spell_Deathknight_UnholyPresence",
  }
  options = options or defaultIcons

  local container = CreateFrame("Frame", nil, parent)
  container:SetSize(72, 24)

  local current = value or ""
  local iconSize = 24

  local iconBtn = CreateFrame("Button", nil, container)
  iconBtn:SetSize(iconSize, iconSize)
  iconBtn:SetPoint("LEFT", 0, 0)

  local iconTex = iconBtn:CreateTexture(nil, "ARTWORK")
  iconTex:SetAllPoints()
  iconTex:SetTexture(current ~= "" and current or "Interface\\Icons\\INV_Misc_QuestionMark")
  iconTex:SetTexCoord(0.08, 0.92, 0.08, 0.92)

  local function MakeEdge(f) return f:CreateTexture(nil, "BORDER") end
  local et = MakeEdge(iconBtn); et:SetPoint("TOPLEFT"); et:SetPoint("TOPRIGHT"); et:SetHeight(1)
  local eb = MakeEdge(iconBtn); eb:SetPoint("BOTTOMLEFT"); eb:SetPoint("BOTTOMRIGHT"); eb:SetHeight(1)
  local el = MakeEdge(iconBtn); el:SetPoint("TOPLEFT"); el:SetPoint("BOTTOMLEFT"); el:SetWidth(1)
  local er = MakeEdge(iconBtn); er:SetPoint("TOPRIGHT"); er:SetPoint("BOTTOMRIGHT"); er:SetWidth(1)
  local btnEdges = {et, eb, el, er}

  local function ApplyBorder(active)
    local accent = Theme:Color("accent")
    local a = active and 1 or 0.5
    for _, e in ipairs(btnEdges) do e:SetColorTexture(accent[1], accent[2], accent[3], a) end
  end
  ApplyBorder(false)
  container._huiListenerID = Theme:OnAccentChanged(function() ApplyBorder(container._open) end)

  local cols, rows = 6, 2
  local cellSize = 32
  local padding = 6
  local popW = cols * cellSize + padding * 2
  local popH = math.ceil(#options / cols) * cellSize + padding * 2

  local popup = CreateFrame("Frame", nil, UIParent)
  popup:SetFrameStrata("FULLSCREEN_DIALOG")
  popup:SetSize(popW, popH)
  popup:Hide()
  RegisterManagedPopup(popup)

  local popBg = popup:CreateTexture(nil, "BACKGROUND")
  popBg:SetAllPoints()
  popBg:SetColorTexture(0x06/255, 0x0e/255, 0x16/255, 0.98)

  local popBorder = CreateFrame("Frame", nil, popup, "BackdropTemplate")
  popBorder:SetAllPoints()
  popBorder:SetBackdrop({edgeFile="Interface\\Buttons\\WHITE8X8", edgeSize=1})
  local accent = Theme:Color("accent")
  popBorder:SetBackdropBorderColor(accent[1], accent[2], accent[3], 0.8)

  local backdrop = CreateFrame("Frame", nil, UIParent)
  backdrop:SetFrameStrata("FULLSCREEN")
  backdrop:SetAllPoints(UIParent)
  backdrop:EnableMouse(true)
  backdrop:Hide()
  RegisterManagedPopup(backdrop)

  local cells = {}

  local function BuildGrid()
    ClearFrameList(cells)

    for i, iconPath in ipairs(options) do
      local col = (i-1) % cols
      local row = math.floor((i-1) / cols)

      local cell = CreateFrame("Button", nil, popup)
      cell:SetSize(cellSize - 2, cellSize - 2)
      cell:SetPoint("TOPLEFT", popup, "TOPLEFT",
        padding + col * cellSize,
        -(padding + row * cellSize))

      local tex = cell:CreateTexture(nil, "ARTWORK")
      tex:SetAllPoints()
      tex:SetTexture(iconPath)
      tex:SetTexCoord(0.08, 0.92, 0.08, 0.92)

      local highlight = cell:CreateTexture(nil, "HIGHLIGHT")
      highlight:SetAllPoints()
      highlight:SetColorTexture(1, 1, 1, 0.25)

      cell:SetScript("OnClick", function()
        current = iconPath
        iconTex:SetTexture(iconPath)
        popup:Hide()
        backdrop:Hide()
        container._open = false
        ApplyBorder(false)
        if type(onChanged) == "function" then onChanged(iconPath) end
      end)

      cell:SetScript("OnEnter", function()
        highlight:SetColorTexture(1, 1, 1, 0.3)
      end)
      cell:SetScript("OnLeave", function()
        highlight:SetColorTexture(1, 1, 1, 0.25)
      end)

      cells[#cells + 1] = cell
    end
    local totalRows = math.ceil(#options / cols)
    popup:SetHeight(totalRows * cellSize + padding * 2)
  end

  BuildGrid()

  local function ClosePopup()
    popup:Hide()
    backdrop:Hide()
    container._open = false
    ApplyBorder(false)
  end

  backdrop:SetScript("OnMouseDown", ClosePopup)

  iconBtn:SetScript("OnClick", function()
    if container._open then
      ClosePopup()
    else
      popup:ClearAllPoints()
      local _, py = iconBtn:GetCenter()
      if py and py < 160 then
        popup:SetPoint("TOPLEFT", iconBtn, "BOTTOMLEFT", 0, -4)
      else
        popup:SetPoint("BOTTOMLEFT", iconBtn, "TOPLEFT", 0, 4)
      end
      backdrop:Show()
      popup:Show()
      container._open = true
      ApplyBorder(true)
    end
  end)

  popup:SetScript("OnHide", function()
    container._open = false
    ApplyBorder(false)
  end)

  container.SetValue = function(self, v)
    current = v or ""
    iconTex:SetTexture(current ~= "" and current or "Interface\\Icons\\INV_Misc_QuestionMark")
  end
  container.GetValue = function(self) return current end

  return container
end

function Widgets:CreateReorderList(parent, items, onChanged)

  local order = {}
  for i, item in ipairs(items) do
    order[i] = item
  end

  local rowH = 28
  local container = CreateFrame("Frame", nil, parent)
  container:SetSize(300, #order * rowH)

  local rowFrames = {}
  local dragItem = nil
  local dragIndex = nil

  local dropIndicator = CreateFrame("Frame", nil, container)
  dropIndicator:SetHeight(2)
  dropIndicator:SetFrameLevel(300)
  dropIndicator:Hide()
  local dropLine = dropIndicator:CreateTexture(nil, "OVERLAY")
  dropLine:SetAllPoints(dropIndicator)
  local dropAccent = Theme:Color("accent")
  dropLine:SetColorTexture(dropAccent[1], dropAccent[2], dropAccent[3], 0.95)

  local function UpdateDropIndicator()
    if not dragItem then
      if dropIndicator:IsShown() then dropIndicator:Hide() end
      return dragIndex
    end
    local _, y = GetCursorPosition()
    local scale = UIParent:GetEffectiveScale()
    local cy = select(2, container:GetCenter())
    local ch = container:GetHeight()
    local relY = (y / scale) - (cy - ch / 2)
    local newIndex = math.min(#order, math.max(1, math.ceil((ch - relY) / rowH)))
    local top = (newIndex > dragIndex) and (newIndex * rowH) or ((newIndex - 1) * rowH)
    dropIndicator:ClearAllPoints()
    dropIndicator:SetPoint("TOPLEFT", container, "TOPLEFT", 0, -top)
    dropIndicator:SetPoint("TOPRIGHT", container, "TOPRIGHT", 0, -top)
    dropIndicator:Show()
    return newIndex
  end

  local function Rebuild()
    ClearFrameList(rowFrames)
    container:SetHeight(#order * rowH)

    for i, item in ipairs(order) do
      local row = CreateFrame("Frame", nil, container)
      row:SetHeight(rowH)
      row:SetPoint("TOPLEFT", container, "TOPLEFT", 0, -(i-1) * rowH)
      row:SetPoint("TOPRIGHT", container, "TOPRIGHT", 0, -(i-1) * rowH)

      local bg = row:CreateTexture(nil, "BACKGROUND")
      bg:SetAllPoints()
      bg:SetColorTexture(0x06/255, 0x0f/255, 0x1a/255, 0.85)

      local handle = CreateFrame("Button", nil, row)
      handle:SetSize(16, rowH)
      handle:SetPoint("LEFT", 4, 0)

      for j = 1, 3 do
        local line = handle:CreateTexture(nil, "ARTWORK")
        line:SetSize(10, 1)
        line:SetPoint("CENTER", 0, (j-2)*5)
        line:SetColorTexture(0.55, 0.60, 0.65, 0.75)
      end

      local accent = Theme:Color("accent")
      local label = row:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
      label:SetPoint("LEFT", handle, "RIGHT", 6, 0)
      label:SetText(item.label or item.id)
      label:SetTextColor(0.90, 0.92, 0.95, 1)

      local rowIndex = i
      local dragLevel
      handle:SetScript("OnMouseDown", function()
        dragIndex = rowIndex
        dragItem = item
        bg:SetColorTexture(accent[1] * 0.3, accent[2] * 0.3, accent[3] * 0.3, 0.95)
        dragLevel = row:GetFrameLevel()
        row:SetFrameLevel(200)
        row:SetMovable(true)
        row:StartMoving()
        container:SetScript("OnUpdate", UpdateDropIndicator)
        UpdateDropIndicator()
      end)
      handle:SetScript("OnMouseUp", function()
        if not dragItem then return end
        row:StopMovingOrSizing()
        row:SetMovable(false)
        row:SetFrameLevel(dragLevel or 0)

        local newIndex = UpdateDropIndicator() or dragIndex
        container:SetScript("OnUpdate", nil)
        dropIndicator:Hide()

        if newIndex ~= dragIndex then
          local moved = table.remove(order, dragIndex)
          table.insert(order, newIndex, moved)
          if type(onChanged) == "function" then onChanged(order) end
        end

        dragItem = nil
        dragIndex = nil
        Rebuild()
      end)

      row:SetScript("OnEnter", function()
        if not dragItem then
          bg:SetColorTexture(0x10/255, 0x1c/255, 0x2c/255, 0.9)
        end
      end)
      row:SetScript("OnLeave", function()
        if not dragItem then
          bg:SetColorTexture(0x06/255, 0x0f/255, 0x1a/255, 0.85)
        end
      end)

      if i > 1 then
        local upBtn = self:CreateActionButton(row, "▲", 20, 20, function()
          local moved = table.remove(order, i)
          table.insert(order, i - 1, moved)
          if type(onChanged) == "function" then onChanged(order) end
          Rebuild()
        end)
        upBtn:SetPoint("RIGHT", row, "RIGHT", -24, 0)
      end

      if i < #order then
        local downBtn = self:CreateActionButton(row, "▼", 20, 20, function()
          local moved = table.remove(order, i)
          table.insert(order, i + 1, moved)
          if type(onChanged) == "function" then onChanged(order) end
          Rebuild()
        end)
        downBtn:SetPoint("RIGHT", row, "RIGHT", -2, 0)
      end

      rowFrames[i] = row
    end
  end

  Rebuild()

  container:SetScript("OnHide", function()
    container:SetScript("OnUpdate", nil)
    dropIndicator:Hide()
    ClearFrameList(rowFrames)
  end)

  container.SetValue = function(self, v)
    order = v or {}
    dropIndicator:Hide()
    Rebuild()
  end
  container.GetValue = function(self) return order end

  return container
end

function Widgets:CreateColorPicker(parent, color, onChanged)
  if type(color) ~= "table" then
    color = { 1, 1, 1, 1 }
  end

  local container = CreateFrame("Frame", nil, parent)
  container:SetSize(24, 24)

  local swatch = CreateFrame("Button", nil, container)
  swatch:SetSize(24, 24)
  swatch:SetPoint("RIGHT", container, "RIGHT", 0, 0)

  local swatchBg = swatch:CreateTexture(nil, "BACKGROUND")
  swatchBg:SetAllPoints()
  swatchBg:SetColorTexture(color[1], color[2], color[3], color[4] or 1)
  container.swatchBg = swatchBg

  local function MakeEdge() return swatch:CreateTexture(nil, "BORDER") end
  local et = MakeEdge(); et:SetPoint("TOPLEFT"); et:SetPoint("TOPRIGHT"); et:SetHeight(1)
  local eb = MakeEdge(); eb:SetPoint("BOTTOMLEFT"); eb:SetPoint("BOTTOMRIGHT"); eb:SetHeight(1)
  local el = MakeEdge(); el:SetPoint("TOPLEFT"); el:SetPoint("BOTTOMLEFT"); el:SetWidth(1)
  local er = MakeEdge(); er:SetPoint("TOPRIGHT"); er:SetPoint("BOTTOMRIGHT"); er:SetWidth(1)
  local edges = {et, eb, el, er}

  local function ApplyBorder(focused)
    local accent = Theme:Color("accent")
    local a = focused and 1 or 0.6
    for _, e in ipairs(edges) do e:SetColorTexture(accent[1], accent[2], accent[3], a) end
  end
  ApplyBorder(false)
  container._huiListenerID = Theme:OnAccentChanged(function() ApplyBorder(container._open) end)

  local hexText = container:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
  hexText:SetPoint("LEFT", swatch, "RIGHT", 8, 0)
  hexText:SetTextColor(0.90, 0.92, 0.95, 1)
  hexText:Hide()

  local function RGBToHex(r, g, b)
    return string.format("#%02x%02x%02x", math.floor(r*255), math.floor(g*255), math.floor(b*255))
  end

  hexText:SetText(RGBToHex(color[1], color[2], color[3]))

  local panel = CreateFrame("Frame", nil, UIParent)
  panel:SetFrameStrata("FULLSCREEN_DIALOG")
  panel:SetSize(240, 160)
  panel:Hide()
  RegisterManagedPopup(panel)

  local panelBg = panel:CreateTexture(nil, "BACKGROUND")
  panelBg:SetAllPoints()
  panelBg:SetColorTexture(0x06/255, 0x0e/255, 0x16/255, 0.98)

  local panelBorder = CreateFrame("Frame", nil, panel, "BackdropTemplate")
  panelBorder:SetAllPoints()
  panelBorder:SetBackdrop({edgeFile="Interface\\Buttons\\WHITE8X8", edgeSize=1})
  local accent = Theme:Color("accent")
  panelBorder:SetBackdropBorderColor(accent[1], accent[2], accent[3], 0.8)

  local function ApplyPanelAccent()
    local a = Theme:Color("accent")
    panelBorder:SetBackdropBorderColor(a[1], a[2], a[3], 0.8)
  end

  local sliders = {}
  local labels = {"R", "G", "B"}
  local currentColor = {color[1], color[2], color[3], color[4] or 1}
  local hexInput

  for i, lbl in ipairs(labels) do
    local label = panel:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
    label:SetPoint("TOPLEFT", panel, "TOPLEFT", 12, -12 - (i-1)*32)
    label:SetText(lbl)
    label:SetTextColor(0.85, 0.87, 0.90, 1)

    local slider = self:CreateSlider(panel, currentColor[i], 0, 1, 0.01, function(val)
      currentColor[i] = val
      swatchBg:SetColorTexture(currentColor[1], currentColor[2], currentColor[3], currentColor[4])
      local hex = RGBToHex(currentColor[1], currentColor[2], currentColor[3])
      hexText:SetText(hex)
      hexInput:SetText(hex)
      if type(onChanged) == "function" then
        onChanged({currentColor[1], currentColor[2], currentColor[3], currentColor[4]})
      end
    end)
    slider:SetSize(160, 16)
    slider:SetPoint("LEFT", label, "RIGHT", 8, 0)
    sliders[i] = slider
  end

  local hexLabel = panel:CreateFontString(nil, "OVERLAY", Theme.fonts.small)
  hexLabel:SetPoint("TOPLEFT", panel, "TOPLEFT", 12, -108)
  hexLabel:SetText("HEX")
  hexLabel:SetTextColor(0.85, 0.87, 0.90, 1)

  hexInput = self:CreateInput(panel, RGBToHex(color[1], color[2], color[3]), function(text)
    local hex = text:gsub("#", "")
    if hex:match("^%x%x%x%x%x%x$") then
      local r = tonumber(hex:sub(1,2), 16) / 255
      local g = tonumber(hex:sub(3,4), 16) / 255
      local b = tonumber(hex:sub(5,6), 16) / 255
      currentColor[1], currentColor[2], currentColor[3] = r, g, b
      swatchBg:SetColorTexture(r, g, b, currentColor[4])
      sliders[1]:SetValue(r)
      sliders[2]:SetValue(g)
      sliders[3]:SetValue(b)
      if type(onChanged) == "function" then
        onChanged({r, g, b, currentColor[4]})
      end
    end
  end)
  hexInput:SetSize(160, 22)
  hexInput:SetPoint("LEFT", hexLabel, "RIGHT", 8, 0)

  local backdrop = CreateFrame("Frame", nil, UIParent)
  backdrop:SetFrameStrata("FULLSCREEN")
  backdrop:SetAllPoints(UIParent)
  backdrop:EnableMouse(true)
  backdrop:Hide()
  RegisterManagedPopup(backdrop)

  local function ClosePanel()
    panel:Hide()
    backdrop:Hide()
    container._open = false
    ApplyBorder(false)
  end

  local function OpenPanel()
    panel:ClearAllPoints()
    local scale = swatch:GetEffectiveScale()
    local uiScale = UIParent:GetEffectiveScale()
    local left = swatch:GetLeft()
    local top = swatch:GetTop()
    local bottom = swatch:GetBottom()
    if left and top and bottom then
      local x = left * scale / uiScale
      local yTop = top * scale / uiScale
      local yBottom = bottom * scale / uiScale
      if yBottom < 180 then
        panel:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", x, yTop + 4)
      else
        panel:SetPoint("TOPLEFT", UIParent, "BOTTOMLEFT", x, yBottom - 4)
      end
    else
      panel:SetPoint("TOPLEFT", swatch, "BOTTOMLEFT", 0, -4)
    end
    backdrop:Show()
    panel:Show()
    container._open = true
    ApplyBorder(true)
  end

  backdrop:SetScript("OnMouseDown", function()
    ClosePanel()
  end)

  swatch:SetScript("OnClick", function()
    if container._open then ClosePanel() else OpenPanel() end
  end)

  panel:SetScript("OnHide", function()
    container._open = false
    ApplyBorder(false)
  end)

  container._huiListenerIDs = container._huiListenerIDs or {}
  container._huiListenerIDs[#container._huiListenerIDs + 1] = Theme:OnAccentChanged(ApplyPanelAccent)

  container.SetValue = function(self, c)
    currentColor = {c[1], c[2], c[3], c[4] or 1}
    swatchBg:SetColorTexture(currentColor[1], currentColor[2], currentColor[3], currentColor[4])
    local hex = RGBToHex(currentColor[1], currentColor[2], currentColor[3])
    hexText:SetText(hex)
    hexInput:SetText(hex)
    for i = 1, 3 do
      sliders[i]:SetValue(currentColor[i])
    end
  end

  container.GetValue = function(self)
    return {currentColor[1], currentColor[2], currentColor[3], currentColor[4]}
  end

  return container
end

function Widgets:CreateScrollFrame(parent, width, height)
  local container = CreateFrame("Frame", nil, parent)
  container:SetSize(width or 400, height or 300)

  local scrollFrame = CreateFrame("ScrollFrame", nil, container)
  scrollFrame:SetPoint("TOPLEFT", 0, 0)
  scrollFrame:SetPoint("BOTTOMRIGHT", -12, 0)
  scrollFrame:EnableMouseWheel(true)
  container.scrollFrame = scrollFrame

  local contentWidth = (width or 400) - 12
  local content = CreateFrame("Frame", nil, scrollFrame)
  content:SetWidth(contentWidth)
  content:SetHeight(1)
  scrollFrame:SetScrollChild(content)
  container.content = content

  local trackBg = container:CreateTexture(nil, "BACKGROUND")
  trackBg:SetWidth(8)
  trackBg:SetColorTexture(0x0f/255, 0x17/255, 0x21/255, 0.85)
  trackBg:SetPoint("TOPRIGHT", container, "TOPRIGHT", -2, -2)
  trackBg:SetPoint("BOTTOMRIGHT", container, "BOTTOMRIGHT", -2, 2)

  local thumb = CreateFrame("Button", nil, container)
  thumb:SetWidth(8)
  thumb:SetPoint("TOP", trackBg, "TOP", 0, 0)

  local thumbTex = thumb:CreateTexture(nil, "OVERLAY")
  thumbTex:SetAllPoints()
  container.thumbTex = thumbTex

  local function ApplyThumbColor()
    local accent = Theme:Color("accent")
    thumbTex:SetColorTexture(accent[1], accent[2], accent[3], 0.9)
  end
  ApplyThumbColor()
  scrollFrame._huiListenerID = Theme:OnAccentChanged(ApplyThumbColor)

  local function UpdateThumb()
    local contentHeight = content:GetHeight() or 1
    local viewHeight = scrollFrame:GetHeight() or 1
    if contentHeight <= viewHeight then
      thumb:Hide()
      return
    end
    thumb:Show()

    local ratio = viewHeight / contentHeight
    local thumbHeight = math.max(20, viewHeight * ratio)
    thumb:SetHeight(thumbHeight)

    local scrollRange = contentHeight - viewHeight
    local scrollPos = scrollFrame:GetVerticalScroll()
    local scrollPct = scrollRange > 0 and (scrollPos / scrollRange) or 0
    local trackHeight = trackBg:GetHeight() or viewHeight
    local maxOffset = trackHeight - thumbHeight
    thumb:ClearAllPoints()
    thumb:SetPoint("TOP", trackBg, "TOP", 0, -scrollPct * maxOffset)
  end

  scrollFrame:SetScript("OnSizeChanged", function(self, w, h)
    content:SetWidth(w)
    UpdateThumb()
  end)

  scrollFrame:SetScript("OnScrollRangeChanged", UpdateThumb)
  scrollFrame:SetScript("OnVerticalScroll", UpdateThumb)
  scrollFrame:SetScript("OnSizeChanged", UpdateThumb)
  content:SetScript("OnSizeChanged", UpdateThumb)

  scrollFrame:SetScript("OnMouseWheel", function(self, delta)
    local current = self:GetVerticalScroll()
    local step = 20
    local newScroll = current - delta * step
    local maxScroll = (content:GetHeight() or 0) - (self:GetHeight() or 0)
    newScroll = math.max(0, math.min(newScroll, maxScroll))
    self:SetVerticalScroll(newScroll)
  end)

  thumb:EnableMouse(true)
  thumb:SetScript("OnMouseDown", function(self)
    self.dragging = true
    self.startY = select(2, GetCursorPosition()) / UIParent:GetEffectiveScale()
    self.startScroll = scrollFrame:GetVerticalScroll()
  end)
  thumb:SetScript("OnMouseUp", function(self)
    self.dragging = false
  end)
  thumb:SetScript("OnUpdate", function(self)
    if not self.dragging then return end
    local currentY = select(2, GetCursorPosition()) / UIParent:GetEffectiveScale()
    local deltaY = self.startY - currentY
    local trackHeight = trackBg:GetHeight() or 1
    local thumbHeight = self:GetHeight() or 20
    local maxOffset = trackHeight - thumbHeight
    local contentHeight = content:GetHeight() or 1
    local viewHeight = scrollFrame:GetHeight() or 1
    local scrollRange = contentHeight - viewHeight
    if maxOffset > 0 and scrollRange > 0 then
      local scrollDelta = (deltaY / maxOffset) * scrollRange
      local newScroll = math.max(0, math.min(self.startScroll + scrollDelta, scrollRange))
      scrollFrame:SetVerticalScroll(newScroll)
    end
  end)

  UpdateThumb()
  return container
end

local focusedEditInput

function Widgets:CreateInput(parent, value, onChanged)
  local container = CreateFrame("Frame", nil, parent)
  container:SetSize(180, 24)

  container.bg = container:CreateTexture(nil, "BACKGROUND")
  container.bg:SetAllPoints()
  local _cA = (addon.db and addon.db.settings and addon.db.settings.controlAlpha) or 0.92
  local _cC = (addon.db and addon.db.settings and addon.db.settings.controlBgColor) or {0x0a/255, 0x12/255, 0x1c/255}
  container.bg:SetColorTexture(_cC[1], _cC[2], _cC[3], _cA)

  local function MakeEdge()
    local t = container:CreateTexture(nil, "BORDER")
    return t
  end
  container.edgeTop = MakeEdge()
  container.edgeTop:SetPoint("TOPLEFT")
  container.edgeTop:SetPoint("TOPRIGHT")
  container.edgeTop:SetHeight(1)

  container.edgeBottom = MakeEdge()
  container.edgeBottom:SetPoint("BOTTOMLEFT")
  container.edgeBottom:SetPoint("BOTTOMRIGHT")
  container.edgeBottom:SetHeight(1)

  container.edgeLeft = MakeEdge()
  container.edgeLeft:SetPoint("TOPLEFT")
  container.edgeLeft:SetPoint("BOTTOMLEFT")
  container.edgeLeft:SetWidth(1)

  container.edgeRight = MakeEdge()
  container.edgeRight:SetPoint("TOPRIGHT")
  container.edgeRight:SetPoint("BOTTOMRIGHT")
  container.edgeRight:SetWidth(1)

  local editBox = CreateFrame("EditBox", nil, container)
  editBox:SetPoint("TOPLEFT", container, "TOPLEFT", 8, -1)
  editBox:SetPoint("BOTTOMRIGHT", container, "BOTTOMRIGHT", -8, 1)
  editBox:SetAutoFocus(false)
  editBox:SetJustifyH("RIGHT")
  editBox:SetFontObject(Theme.fonts.body)
  editBox:SetTextColor(0.95, 0.96, 0.98, 1)
  editBox:SetText(tostring(value or ""))
  editBox:SetCursorPosition(0)
  container.editBox = editBox

  local function ApplyBorder(focused)
    local accent = Theme:Color("accent")
    local a = focused and 1 or 0.6
    local edges = { container.edgeTop, container.edgeBottom, container.edgeLeft, container.edgeRight }
    for _, edge in ipairs(edges) do
      edge:SetColorTexture(accent[1], accent[2], accent[3], a)
    end
  end
  ApplyBorder(false)
  container._huiListenerID = Theme:OnAccentChanged(function()
    ApplyBorder(editBox:HasFocus())
  end)

  editBox:SetScript("OnEditFocusGained", function()
    focusedEditInput = editBox
    ApplyBorder(true)
  end)
  editBox:SetScript("OnEnterPressed", function(self)
    self:ClearFocus()
    if type(onChanged) == "function" then
      onChanged(self:GetText())
    end
  end)
  editBox:SetScript("OnEditFocusLost", function(self)
    if focusedEditInput == self then focusedEditInput = nil end
    ApplyBorder(false)
    if type(onChanged) == "function" then
      onChanged(self:GetText())
    end
  end)

  function container:SetText(text)
    self.editBox:SetText(tostring(text or ""))
    self.editBox:SetCursorPosition(0)
  end
  function container:GetText()
    return self.editBox:GetText()
  end

  return container
end

function Widgets.HasEditingFocus()
  local focused = focusedEditInput
  if not focused then return false end
  local hasFocus = focused.HasFocus and focused:HasFocus() or false
  if not hasFocus then focusedEditInput = nil end
  return hasFocus
end

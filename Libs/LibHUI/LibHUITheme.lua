local addonName, addon = ...

addon.LibHUI = addon.LibHUI or {}

local HUI = addon.LibHUI
local Theme = {}

HUI.Theme = Theme

Theme.colors = {
  background = { 0.01, 0.02, 0.04, 0.94 },
  panel = { 0.02, 0.06, 0.10, 0.88 },
  panelSoft = { 0.04, 0.09, 0.13, 0.82 },
  row = { 0.08, 0.16, 0.24, 0.90 },
  rowHover = { 0.14, 0.26, 0.36, 0.95 },
  button = { 0.15, 0.27, 0.38, 1.00 },
  buttonHover = { 0.24, 0.38, 0.50, 1.00 },
  toggleOff = { 0.20, 0.26, 0.32, 1.00 },
  accent = { 1.00, 0.78, 0.02, 1.00 },
  accentDark = { 0.65, 0.45, 0.00, 1.00 },
  text = { 0.95, 0.96, 0.98, 1.00 },
  textDark = { 0.06, 0.10, 0.18, 1.00 },
  muted = { 0.55, 0.62, 0.70, 1.00 },
  disabled = { 0.28, 0.32, 0.36, 1.00 },
  danger = { 0.90, 0.20, 0.18, 1.00 },
  black = { 0, 0, 0, 1 },
}

Theme.sizes = {
  frameWidth = 720,
  frameHeight = 620,
  headerHeight = 54,
  footerHeight = 42,
  sidebarWidth = 130,
  rowHeight = 28,
  gap = 10,
  inset = 18,
}

Theme.fonts = {
  title = "GameFontNormalHuge",
  heading = "GameFontNormalLarge",
  body = "GameFontNormal",
  small = "GameFontHighlightSmall",
}

local function InitCustomFonts()
  local baseFonts = {
    title = "GameFontNormalHuge",
    heading = "GameFontNormalLarge",
    body = "GameFontNormal",
    small = "GameFontHighlightSmall",
  }
  for name, baseName in pairs(baseFonts) do
    local customName = "YYBuffReminderFont_" .. name
    local font = CreateFont(customName)

    local base = _G[baseName]
    if base then
      font:CopyFontObject(base)
      local fontPath, fontSize = font:GetFont()
      font:SetFont(fontPath, fontSize, "")
    else
      font:SetFont(STANDARD_TEXT_FONT, 14, "")
    end
    Theme.fonts[name] = customName
  end
end
InitCustomFonts()

Theme.assets = {
  rowNormal = "LibHUI_RowNormal",
  rowSelected = "LibHUI_RowSelected",
}

function Theme:GetAssetRoot(app)
  local opts = app and app.opts
  if opts and opts.assetRoot then
    return opts.assetRoot
  end

  return "Interface\\AddOns\\" .. addonName .. "\\LibHUI\\Assets\\"

end

function Theme:Asset(name, app)
  local file = self.assets[name]
  if not file then
    return nil
  end

  return self:GetAssetRoot(app) .. file
end

function Theme:Color(name)
  return self.colors[name] or self.colors.text
end

Theme._accentListeners = Theme._accentListeners or {}
Theme._accentListenerNextID = Theme._accentListenerNextID or 0

function Theme:OnAccentChanged(callback)
  if type(callback) ~= "function" then return end
  self._accentListenerNextID = self._accentListenerNextID + 1
  local id = self._accentListenerNextID
  self._accentListeners[id] = callback
  return id
end

function Theme:OffAccentChanged(id)
  if id then
    self._accentListeners[id] = nil
  end
end

function Theme:SetAccentColor(r, g, b, a)
  a = a or 1
  self.colors.accent = { r, g, b, a }
  local base_r, base_g, base_b = 0.04, 0.10, 0.16
  local mix = 0.30
  self.colors.accentDark = {
    base_r + r * mix,
    base_g + g * mix,
    base_b + b * mix,
    a,
  }

  for _, callback in pairs(self._accentListeners) do
    callback(self.colors.accent)
  end
end

function Theme:SetButtonBgColor(r, g, b, a)
  a = a or 1
  self.colors.row = { r, g, b, a }
  self.colors.button = { r, g, b, a }
  self.colors.rowHover = {
    math.min(r + 0.06, 1),
    math.min(g + 0.10, 1),
    math.min(b + 0.12, 1),
    math.min(a + 0.05, 1),
  }
  self.colors.buttonHover = {
    self.colors.rowHover[1],
    self.colors.rowHover[2],
    self.colors.rowHover[3],
    self.colors.rowHover[4],
  }
  for _, callback in pairs(self._accentListeners) do
    callback(self.colors.accent)
  end
end

function Theme:SetAccentColorHex(hex)
  if type(hex) ~= "string" then
    return
  end
  hex = hex:gsub("#", "")
  if #hex < 6 then
    return
  end
  local r = tonumber(hex:sub(1, 2), 16) / 255
  local g = tonumber(hex:sub(3, 4), 16) / 255
  local b = tonumber(hex:sub(5, 6), 16) / 255
  self:SetAccentColor(r, g, b, 1)
end

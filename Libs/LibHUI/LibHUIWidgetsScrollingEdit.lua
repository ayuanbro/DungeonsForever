local _, addon = ...
local HUI = addon.LibHUI
local Widgets = HUI and HUI.Widgets
local Theme = HUI and HUI.Theme
if not Widgets or not Theme then return end

local CreateFrame = CreateFrame
local select = select
local math_max = math.max
local math_min = math.min

function Widgets.CreateScrollingEditBox(_, parent, width, height)
  local container = CreateFrame("Frame", nil, parent)
  container:SetSize(width or 400, height or 260)

  local scrollFrame = CreateFrame("ScrollFrame", nil, container)
  scrollFrame:SetPoint("TOPLEFT", 0, 0)
  scrollFrame:SetPoint("BOTTOMRIGHT", -12, 0)
  scrollFrame:EnableMouseWheel(true)
  container.scrollFrame = scrollFrame

  local editBox = CreateFrame("EditBox", nil, scrollFrame)
  editBox:SetMultiLine(true)
  editBox:SetAutoFocus(false)
  editBox:SetSize((width or 400) - 12, height or 260)
  editBox:SetFontObject(Theme.fonts.body)
  editBox:SetTextColor(0.95, 0.96, 0.98, 1)
  editBox:SetHighlightColor(0.08, 0.42, 0.78, 0.9)
  scrollFrame:SetScrollChild(editBox)
  editBox.cursorOffset = 0
  editBox.cursorHeight = 0
  container.editBox = editBox

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
    local viewHeight = scrollFrame:GetHeight() or 1
    local scrollRange = scrollFrame:GetVerticalScrollRange() or 0
    if scrollRange <= 0 then
      thumb:Hide()
      return
    end
    thumb:Show()

    local ratio = viewHeight / (viewHeight + scrollRange)
    local thumbHeight = math_max(20, viewHeight * ratio)
    thumb:SetHeight(thumbHeight)

    local scrollPos = scrollFrame:GetVerticalScroll() or 0
    local scrollPct = scrollRange > 0 and (scrollPos / scrollRange) or 0
    local trackHeight = trackBg:GetHeight() or viewHeight
    local maxOffset = trackHeight - thumbHeight
    thumb:ClearAllPoints()
    thumb:SetPoint("TOP", trackBg, "TOP", 0, -scrollPct * maxOffset)
  end

  scrollFrame:SetScript("OnSizeChanged", function(_, w, h)
    editBox:SetSize(w, h)
    UpdateThumb()
  end)
  scrollFrame:SetScript("OnScrollRangeChanged", UpdateThumb)
  scrollFrame:SetScript("OnVerticalScroll", UpdateThumb)

  scrollFrame:SetScript("OnMouseWheel", function(_, delta)
    local step = 20
    local maxScroll = scrollFrame:GetVerticalScrollRange() or 0
    local newScroll = (scrollFrame:GetVerticalScroll() or 0) - delta * step
    newScroll = math_max(0, math_min(newScroll, maxScroll))
    scrollFrame:SetVerticalScroll(newScroll)
  end)

  thumb:EnableMouse(true)
  thumb:SetScript("OnMouseDown", function(button)
    button.dragging = true
    button.startY = select(2, GetCursorPosition()) / UIParent:GetEffectiveScale()
    button.startScroll = scrollFrame:GetVerticalScroll()
  end)
  thumb:SetScript("OnMouseUp", function(button)
    button.dragging = false
  end)
  thumb:SetScript("OnUpdate", function(button)
    if not button.dragging then return end
    local currentY = select(2, GetCursorPosition()) / UIParent:GetEffectiveScale()
    local deltaY = button.startY - currentY
    local trackHeight = trackBg:GetHeight() or 1
    local thumbHeight = button:GetHeight() or 20
    local maxOffset = trackHeight - thumbHeight
    local scrollRange = scrollFrame:GetVerticalScrollRange() or 0
    if maxOffset > 0 and scrollRange > 0 then
      local scrollDelta = (deltaY / maxOffset) * scrollRange
      local newScroll = math_max(0, math_min(button.startScroll + scrollDelta, scrollRange))
      scrollFrame:SetVerticalScroll(newScroll)
    end
  end)

  editBox:SetScript("OnCursorChanged", ScrollingEdit_OnCursorChanged)
  editBox:SetScript("OnTextChanged", function(input)
    ScrollingEdit_OnTextChanged(input, input:GetParent())
    UpdateThumb()
  end)
  editBox:SetScript("OnUpdate", function(input, elapsed)
    ScrollingEdit_OnUpdate(input, elapsed, input:GetParent())
  end)

  UpdateThumb()
  return container
end

local _, addon = ...

addon.LibHUI = addon.LibHUI or {}

local L = {}
addon.LibHUI.L = L

local locale = GetLocale()

if locale == "zhCN" then
  L.noneSelected  = "未选择"
  L.countSelected = "已选择 %d 项"
  L.notBound      = "未绑定"
  L.pressKey      = "请按一个键..."
  L.resetPage     = "重置页面"
  L.reloadUI      = "重载界面"
  L.close         = "关闭"
else
  L.noneSelected  = "None selected"
  L.countSelected = "%d selected"
  L.notBound      = "Not Bound"
  L.pressKey      = "Press a key..."
  L.resetPage     = "Reset Page"
  L.close         = "Close"
end

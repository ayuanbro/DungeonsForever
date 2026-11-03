local addonName, addon = ...

addon.LibHUI = addon.LibHUI or {}

local HUI = addon.LibHUI
local Config = {}

local pairs = pairs
local ipairs = ipairs
local type = type
local tonumber = tonumber
local tinsert = table.insert
local sort = table.sort

HUI.Config = Config
Config.apps = Config.apps or {}

local function SortByOrder(left, right)
  local leftOrder = left and left.order or 1000
  local rightOrder = right and right.order or 1000

  if leftOrder == rightOrder then
    return (left.id or "") < (right.id or "")
  end

  return leftOrder < rightOrder
end

local function NormalizeID(value)
  if type(value) == "string" and value ~= "" then
    return value
  end
end

local AppMixin = {}

function Config:RegisterAddOn(id, opts)
  id = NormalizeID(id) or addonName
  opts = opts or {}

  local app = {
    id = id,
    opts = opts,
    categories = {},
    categoryList = {},
    pages = {},
    pageList = {},
    groups = {},
    controls = {},
    controlList = {},
  }

  for key, value in pairs(AppMixin) do
    app[key] = value
  end

  self.apps[id] = app
  return app
end

function Config:GetAddOn(id)
  if type(id) == "table" then
    return id
  end

  return self.apps[id]
end

function AppMixin:RegisterCategory(data)
  if type(data) ~= "table" then
    return
  end

  local id = NormalizeID(data.id)
  if not id then
    return
  end

  data.pages = data.pages or {}
  self.categories[id] = data
  tinsert(self.categoryList, data)
  sort(self.categoryList, SortByOrder)

  return data
end

function AppMixin:RegisterPage(data)
  if type(data) ~= "table" then
    return
  end

  local id = NormalizeID(data.id)
  if not id then
    return
  end

  data.groups = data.groups or {}
  data.controls = data.controls or {}
  self.pages[id] = data
  tinsert(self.pageList, data)
  sort(self.pageList, SortByOrder)

  local category = data.category and self.categories[data.category]
  if category then
    tinsert(category.pages, data)
    sort(category.pages, SortByOrder)
  end

  return data
end

function AppMixin:RegisterGroup(pageID, data)
  if type(data) ~= "table" then
    return
  end

  local id = NormalizeID(data.id)
  local page = self.pages[pageID]
  if not id or not page then
    return
  end

  data.pageID = pageID
  self.groups[id] = data
  tinsert(page.groups, data)
  sort(page.groups, SortByOrder)

  return data
end

function AppMixin:RegisterControl(pageID, data)
  if type(data) ~= "table" then
    return
  end

  local id = NormalizeID(data.id)
  local page = self.pages[pageID]
  if not id or not page then
    return
  end

  data.pageID = pageID
  data.type = data.type or "label"
  self.controls[id] = data
  tinsert(self.controlList, data)
  tinsert(page.controls, data)
  sort(page.controls, SortByOrder)

  return data
end

function AppMixin:GetDB()
  local db = self.opts and self.opts.db
  if type(db) == "function" then
    return db() or {}
  end

  if type(db) == "table" then
    return db
  end

  return {}
end

function AppMixin:GetValue(control)
  if not control then
    return nil
  end

  if type(control.getValue) == "function" then
    return control.getValue(control)
  end

  local key = control.key
  if key then
    local db = self:GetDB()
    local value = db[key]
    if value ~= nil then
      return value
    end
  end

  return control.default
end

function AppMixin:SetValue(control, value)
  if not control then
    return
  end

  if type(control.setValue) == "function" then
    control.setValue(value, control)
    return
  end

  local key = control.key
  if key then
    local db = self:GetDB()
    db[key] = value
  end
end

function AppMixin:IsControlVisible(control)
  if not control then
    return false
  end

  if type(control.visibleWhen) == "function" and not control.visibleWhen(control) then
    return false
  end

  if type(control.hiddenWhen) == "function" and control.hiddenWhen(control) then
    return false
  end

  return true
end

function AppMixin:IsControlEnabled(control)
  if not control then
    return false
  end

  if type(control.isEnabled) == "function" then
    return control.isEnabled(control) ~= false
  end

  if type(control.parentCheck) == "function" then
    return control.parentCheck(control) ~= false
  end

  return true
end

function AppMixin:GetFirstPage()
  for _, category in ipairs(self.categoryList) do
    if category.pages then
      for _, page in ipairs(category.pages) do
        if not (type(page.visibleWhen) == "function" and not page.visibleWhen(page)) then
          return page
        end
      end
    end
  end

  return self.pageList[1]
end

function AppMixin:ResetControl(control)
  if not control then
    return
  end

  local value = control.default
  if value == nil then
    value = control.dbDefault
  end

  self:SetValue(control, value)
end

local ns = _G.DF_NS or {}

if (type(DF_Locale) ~= "function") or DF_Locale() ~= "enUS" then return end

ns.FactionNpcs = {
  [5396] = { name="Captain Pentigast", map=1443, x=66.7, y=10.9 },
  [5397] = { name="Uthek the Wise", map=1443, x=36.2, y=79.2 },
  [5398] = { name="Warug", map=1443, x=75.0, y=68.2 },
  [5412] = { name="Gurda Wildmane", map=1443, x=56.3, y=59.7 },
  [253096] = { name="Haleya", map=1443, x=69.8, y=78.0 },
  [253097] = { name="Mirda", map=1443, x=70.5, y=70.4 },
  [253136] = { name="Orgrul", map=1443, x=65.4, y=84.2 },
  [253139] = { name="Gorhak", map=1443, x=66.2, y=79.4 },
  [253140] = { name="Morka", map=1443, x=35.7, y=92.2 },
  [253163] = { name="Grolka", map=1443, x=69.8, y=77.9 },
  [253166] = { name="Tarla", map=1443, x=34.5, y=86.9 },
  [253177] = { name="Nerlok", map=1443, x=58.4, y=88.6 },
  [253851] = { name="Hajak", place="Desolace · Valley of Bones" },
  [254040] = { name="Lokren", place="Desolace · Valley of Bones" },
  [254357] = { name="Khan Jehn", map=1443, x=73.8, y=73.9 },
}

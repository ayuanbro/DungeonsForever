# Core/Data 数据结构

本文根据 `dev` 分支当前源码整理，覆盖 `Core/Data` 下的全部 Lua 数据文件，包括语言版本；描述表结构、键、字段、位置数组、关联关系及加载行为，不逐条列出游戏数据。结构以实际定义和 `Core` 中的读取代码为准。

## 范围与读取约定

| 目录 | 文件数 | 用途 |
| --- | ---: | --- |
| `Core/Data/` | 74 | 基础数据，文本主要为简体中文，也包含英文名称与未翻译内容 |
| `Core/Data/enUS/` | 24 | 英文客户端的同名数据或加载函数覆盖 |
| `Core/Data/zhTW/` | 31 | 繁体中文客户端的同名数据或加载函数覆盖 |
| 合计 | 129 | 均为 `.lua` 文件 |

- 数据通过 `local _, ns = ...` 等写法取得插件命名空间，主要导出到 `ns`；全局入口 `_G.DF_NS` 在 `Core/Core.lua` 中指向此命名空间。
- 下文 `T[key] = value` 表示映射，`{Record, ...}` 表示顺序数组，`{a, b, c}` 表示从 **1** 开始的位置数组。`?` 表示可省略或为 `nil`，`...` 表示可重复项。
- `itemID`、`spellID`、`questID`、`npcID`、`displayID` 通常为数字；副本 ID、专业 slug、职业/专精键通常为字符串。显示名不宜替代稳定 ID 作关联键。
- **AreaID 与 UiMapID 不同**：区域 ID 经 `ns.AreaMap` 转为可打开的世界地图 ID。位置数组中的地图类型、坐标顺序以各节为准。
- 地理点和副本标记通常使用 `0–100` 百分比坐标；底图细节使用像素偏移。不能统一按同一种方式解码。
- 阵营存在多套编码：`"A"/"H"`、`"a"/"h"`、数字以及专业表内的代码字典。不能跨表直接套用。
- 稀疏 ID 映射用 `pairs` 或按键访问；顺序数组才适合 `ipairs`。位置数组可能含显式 `nil`/`false`，不要通过 `#record` 判断所有字段是否存在。
- 本目录的数据与 `DungeonsForeverDB` 保存的玩家设置、完成状态、实测商人价格等运行时数据分开；读取模块可能给静态记录添加索引、元表或缓存。

## 加载顺序与语言覆盖

加载入口是 [`DungeonsForever.toc`](../DungeonsForever.toc)，命名空间和客户端条件来自 [`Core/Core.lua`](../Core/Core.lua)。

1. 先加载 `Locales`、依赖库与 `Core/Core.lua`，再按 `.toc` 顺序执行基础数据文件。
2. 在基础文件之后加载 `zhTW` / `enUS` 文件；`.toc` 使用 `[AllowLoadTextLocale ...]`，这些文件也有 `GetLocale()` 守卫。
3. 语言文件通常直接重新赋值整张表，或覆盖 `Ensure*` 函数；不是默认的逐字段合并。`zhTW/Data_ProfItemNames.lua` 显式保留基础表并补回缺失键，是例外。
4. 语言块之后还加载共享补充数据，包括装备职业/任务索引、采矿/钓鱼、专业来源/NPC/物品名/制造索引以及副本任务流程等。因此“同名语言文件已执行”不代表后续不会再修改数据。
5. 大部分 UI 在数据之后加载；`Data_MapDetail.lua` 和 `Data_RouteOvl.lua` 位于 `.toc` 末尾，由需要它们的运行时逻辑读取。

`EnsureGearData`、`EnsureBISData`、`EnsureProfRecipes` 等函数通常在首次调用时构造并缓存大表。仅加载文件不一定已经产生对应数据表，调用方应使用文件提供的 `Ensure*`。语言文件也可能改变构造时机，例如 `enUS/Data_ClassCombat.lua` 直接赋值 `ns.ClassCombat`。

`Data_NPCLoc.lua` 及其语言文件受 `ns.IsTitan` 限制；该标记的实际客户端范围以 `Core/Core.lua` 的 `IsSupportedClient` 为准。`Data_NameOverrides.lua` 只在简体中文环境生效（没有 `GetLocale` 函数时也会执行）。UI 另有 `LoadForeverPages` 等条件，不能把 UI 是否出现与数据文件是否执行视为同一件事。

语言副本的存在只表示存在覆盖数据，不保证所有文本均已翻译，也不保证与基础版本逐条同步。具体覆盖范围见文末文件索引。

## 副本、首领与任务

### Data_Dungeons.lua

导出 `ns.DungeonData = { dungeons = Dungeon[] }`，其中 `dungeons` 是按展示顺序排列的副本数组。`Dungeon` 是命名字段记录：

| 字段 | 类型与含义 |
| --- | --- |
| `id` | `string`，内部副本键，如 `the_deadmines`，用于关联以下各表。 |
| `name`、`nameEn` | 显示名和英文名。 |
| `levelMin`、`levelMax` | 建议等级范围。 |
| `isNew` | 是否为新增副本。 |
| `zone` | 所在区域说明。 |
| `bossCount`、`dropCount` | 静态首领数、掉落数；未知时可以缺省（源码写 `nil`）。 |
| `art` | 美术资源标识。 |
| `bosses` | 当前根文件中的记录均为预留空表；实际首领/掉落由 `DungeonLoot` 等表提供。 |

### Data_DungeonEntry.lua

- `ns.DungeonEntry[dungeonID] = { uiMapID, x, y, mapName }`：副本入口的世界地图点，坐标为百分比。
- `ns.DungeonEntryRoute[dungeonID] = { { uiMapID, x, y, label, mapName }, ... }`：入口外的附加导航点，如楼梯、集合石。
- `DungeonUI` 以入口为第一个点，再追加路线点。并非所有副本都有入口记录，入口表也包含 `onyxias_lair` 等团队副本键。

### Data_DungeonLoot.lua

```lua
ns.DungeonLoot[dungeonID] = {
    { sourceNameEn, sourceName, note, npcIDText, {
        { itemID, dropPercent, isNew },
        -- ...
    } },
    -- ...
}
```

外层是副本到掉落来源数组的映射；一个来源可能是首领，也可能是小怪、箱子等。

- 来源 `[1]` 为英文来源名，也是 `BossPos`、`BossSkills`、`BossModelDisplay` 和攻略 `bosses[].en` 的关联键；`[2]` 为显示名；`[3]` 为补充说明，空字符串表示无说明。
- `[4]` 为字符串形式的 NPC ID；没有对应 NPC 时为 `""`，使用时需要 `tonumber`，不能把它当成总有值的数字。
- `[5]` 为物品数组：`[1]` 物品 ID，`[2]` 百分比掉率（`nil` 表示未知），`[3]` 新增物品标记。
- 物品名、品质、图标等由客户端查询；该表不存完整物品属性。

### Data_DungeonGuide.lua

`ns.DungeonGuide[dungeonID]` 是攻略记录：

- `tagline: string`：副本概述。
- `tips: string[]`：通用提醒。
- `entrance = { A = string | string[], H = string | string[] }`：按阵营区分的到达说明，可以是一段文本或分步数组。
- `trash = { { title, text }, ... }`：小怪类别、机制说明。
- `bosses = { { en, text }, ... }`：按英文首领名关联的打法说明。

字段可按副本缺省；攻略不是首领的主索引，地图通过 `bosses[].en` 查对应说明。

### Data_BossPos.lua

`ns.BossPos[dungeonID][bossNameEn] = { { x, y, floor? }, ... }`。坐标是副本贴图上的百分比，不是世界区域坐标；`floor` 是该副本地图的层索引，缺省为 `1`。同一个首领可有多个刷新点，不能把值简化成单一坐标。

### Data_BossModel.lua

`ns.BossModelDisplay[dungeonID][bossNameEn] = displayID`，值为模型显示 ID，供模型组件 `SetDisplayInfo` 使用；它与 NPC ID 是不同的编号。

### Data_BossSkills.lua

`ns.BossSkills[dungeonID][bossNameEn] = { { fallbackName, fallbackDescription, spellID, iconSlug }, ... }`。

- `[1]`、`[2]` 是名称与描述后备文本；根数据中通常为空字符串。
- `[3]` 在当前数据中为数字法术 ID；消费者同时兼容字符串图标名的旧格式。
- `[4]` 为 `Interface\\Icons\\` 下的图标名后缀。
- `MapUI` 优先通过客户端法术 API 获取本地化名称、图标、说明，再使用记录中的后备值。

### Data_DungeonQuests.lua

导出主任务表与多张补充表；主表使用固定位置的稀疏元组：

```lua
ns.DungeonQuests[dungeonID] = { QuestRow, ... }
```

| 下标 | 类型与含义 |
| --- | --- |
| `[1]` | `number`，任务 ID。 |
| `[2]` | `"A" \| "H" \| nil`，阵营；`nil` 为共用。 |
| `[3]` | 可接等级。 |
| `[4]` | 任务等级后备值，可缺省。 |
| `[5]` | 起始 NPC 或触发来源的显示说明。 |
| `[6]` | 接取地点文本，可包含坐标、区域或物品来源描述。 |
| `[7]` | 前置任务的文字说明。 |
| `[8]` | 副本内接取/触发标记；`DungeonUI` 据此分到 `inside` 组。 |
| `[9]` | 前置列表 `(number \| string)[]`；数值是任务 ID，字符串是没有数值关联的说明。 |
| `[10]` | 奖励物品 ID 数组。 |
| `[11]` | 目标说明后备文本。 |
| `[12]` | 攻略、注意事项。 |
| `[13]` | 难度阈值数组 `{ { playerLevel, colorIndex }, ... }`；颜色编号 `1..5` 为红、橙、黄、绿、灰。 |
| `[14]` | 任务所需物品 ID 数组；不在此保存数量。 |
| `[15]` | 职业限制文字；多职业可用 `/`、`、` 或 `,` 分隔。 |
| `[16]` | 起始 NPC ID。 |
| `[17]` | 起始 NPC 的独立显示名。 |
| `[18]` | 收益记录 `gains`，见下文。 |

`gains = { xp?, money?, rep? }`：`xp` 为经验，`money` 为铜币数；`rep = { { factionID, amount, factionName }, ... }` 为声望奖励。可用客户端信息时，UI 会查询任务名称、等级、目标和奖励，静态值用于补充或回退。

同文件另有：

| 导出 | 结构与用途 |
| --- | --- |
| `ns.DungeonQuestAlias` | `[dungeonID] = questID[]`；为某副本引用已经收录在其他副本中的任务行，当前含奥妮克希亚门任务链。 |
| `ns.DungeonQuestPreExtra` | `[questID] = { previousQuestID?, npc?, lv?, src? }`；`[1]` 为单个前置 ID，命名字段补充 NPC、可接等级、来源说明。 |
| `ns.DungeonQuestPreNote` | `[questID] = string`；解释特殊前置条件。 |
| `ns.DungeonQuestShare` | `[questID] = true`；可分享任务集合。 |
| `ns.EnsureDungeonQuestExtInfo()` | 首次调用建立并缓存 `ns.DungeonQuestExtInfo`，以后返回同一张表。 |

`DungeonQuestExtInfo[questID]` 使用命名字段，补全前置链及未进入主表的任务：

- 基本字段：`lv`（可接等级）、`lvStd`（任务等级）、`nm`（任务名）、`npc`、`npcid`、`side`、`zone`、`cls`。
- 任务内容：`pre: questID[]`、`rew: itemID[]`、`obj: string`、`text: string`、`gains`。
- `si: boolean`：副本内/物品触发等起始方式标记；转换成通用任务行时进入 `[8]`。
- `goals` 为目标数组，当前存在 `{ "i", itemID, count }`（物品）、`{ "c", creatureName, count }`（击杀）、`{ "o", description }`（交互说明）。`DG.ExtQuestRow` 从 `"i"` 目标提取 `[14]`，并可由 `lv/lvStd` 推导 `[13]`。
- 扩展记录的转换结果会附加 `[19] = true` 与 `[20] = obj`，它们是 UI 产生的标记，不是主静态表的基础 18 列。

### Data_DungeonQuestFlow.lua

只在载入时定义 `ns.EnsureDungeonQuestFlow()`；首次调用才分配 `ns.DungeonQuestFlow`，后续返回缓存。

```lua
ns.DungeonQuestFlow[dungeonID] = {
    side = "A",                  -- 可选；也可为 "H"
    sec = { Section, ... },       -- 通用流程
    secA = { Section, ... },      -- 可选，联盟专用流程
    secH = { Section, ... },      -- 可选，部落专用流程
}
-- Section = { hd = "进本前", st = { Step, ... } }
-- Step 是按显示顺序排列的富文本 token 数组：
-- { { t = "找" }, { n = "萨尔", id = 4949 }, { q = "隐藏的敌人", id = 5728 } }
```

`hd` 是阶段标题，`st` 是步骤列表。token 有纯文本 `t`、NPC `n`、任务 `q`、物品 `i` 四种，后三种用 `id` 关联 NPC、任务、物品并提供点击/提示。`secA/secH` 按当前阵营优先选取，通用 `sec` 可受 `side` 限制。

### Data_Route.lua

- `ns.DungeonRoute[dungeonID][floor] = { { from, to, pts, dash? }, ... }`。
- `from`、`to` 为路线段的文字端点；`pts = { { x, y }, ... }` 为副本贴图上的百分比折线点，`dash = true` 表示虚线段。
- `ns.DungeonRouteNote[dungeonID][floor] = { { x, y, text }, ... }` 为同层地图上的文字注释点。
- `floor` 与 `BossPos` 的层索引保持一致；`from/to` 是说明文字，不是需要解析的首领外键。

## 地图、NPC 与任务定位

### Data_AreaMap.lua

导出 `ns.AreaMap[areaID] = uiMapID`，把区域 ID 转为世界地图 ID。探索点、专业 NPC、装备商人等使用区域 ID 的数据可经此表转换；例如区域 `12` 对应地图 `1429`。缺失键表示未收录映射，不应把原值默认为同类型 ID。

### Data_MapPins.lua

导出 `ns.MapPins[dungeonID][kind] = {Pin, ...}`，补充副本入口、任务、楼层通道等标记。`kind` 决定元组结构：

| kind | 元组 | 含义 |
| --- | --- | --- |
| `entrance` | `{x, y, id?, floor?}` | 副本入口；现有记录常以 `nil` 占第 3 项 |
| `quest` | `{x, y, questID, floor?, text?}` | 副本内任务点及提示 |
| `prev` / `next` | `{x, y, floor?, text?, side?}` | 上一层/下一层通道；第 3 项为该标记所在层 |
| `icon` | `{x, y, floor?, text?, side?}` | 文字/交互提示标记 |
| `rare` | `{x, y, npcID, name?, floor?}` | 稀有怪标记 |
| `object` | `{x, y, id?, floor?}` | 物件标记的读取格式 |

`x/y` 为副本地图百分比，缺省楼层为 `1`；通道/提示的 `side` 为 `"A"` 或 `"H"`，缺省表示共用。`Core/MapUI.lua` 的 `ExtraPinsFor` 根据类别读取不同下标，并按楼层、阵营和任务显示开关过滤；不要把所有 Pin 当作同一种元组。

### Data_GravePos.lua

导出 `ns.GravePos[uiMapID] = {x1, y1, side1, x2, y2, side2, ...}`。每 **3** 项一个墓地点，坐标为百分比，`side` 为 `0` 共用、`1` 联盟、`2` 部落。`Core/ExploreMap.lua` 与 `Core/ExploreUI.lua` 按三元组绘制。

### Data_MapDetail.lua

通过局部表 `D` 导出 `ns.MapDetail[uiMapID] = {fileID, dx, dy, width, height, ...}`。每 **5** 项是一张地图细节贴图：纹理文件 ID、左上角水平/垂直像素偏移、宽和高。`dy` 可为负数，直接作为 UI 锚点偏移；这些数值不是地理百分比。`Core/ExploreUI.lua` 在路线地图上叠加这些纹理。

### Data_NPCLoc.lua

导出两张索引，整个文件受 `ns.IsTitan` 守卫控制：

- `ns.NPCLoc[npcID] = {uiMapID, x, y, zoneName?}`：NPC 的代表位置，坐标为百分比。
- `ns.QuestPreNpcID[questID] = npcID`：任务/前置任务对应的 NPC，用于任务链提示及定位回退。

`Core/DungeonUI.lua` 的 `DG.MarkNPC` 读取 NPC 位置，也接受调用方传入的位置覆盖。此表不是 NPC 的全部刷新点集合；专业和装备另有多点数据。

### Data_QuestStartNpc.lua

导出 `ns.DungeonQuestStartNpc[questID] = {npcID, npcName?, uiMapID?, x?, y?}`。收录副本任务起始 NPC，含通过击杀/掉落物触发的任务；名称和位置可能缺失。由 `DG.QuestStartNpc` 读取。

### Data_QuestStartLoc.lua

导出 `ns.DungeonQuestStartLoc[questID] = {npcID?, npcName?, uiMapID?, x?, y?, zoneName?}`。这是按**任务**区分的起始位置补充，允许全 `nil` 的空记录。`DG.StartLoc(qid, npcID)` 仅在地图和坐标齐全且已知 NPC 不冲突时返回位置；同一 NPC 在不同任务中的位置可以不同。

### Data_QuestEndNpc.lua

导出 `ns.DungeonQuestEndNpc[questID] = {npcID?, npcName?, uiMapID?, x?, y?, zoneName?, locationText?}`。第 7 项为可选的交任务位置说明，可能含子区域和坐标文本。由 `DG.QuestEndNpc` 读取，不可与前两种起始位置元组混用。

## 装备与来源索引

### Data_Gear.lua

提供 `ns.EnsureGearData()` 与 `ns.EnsureGearSrc()` 两个独立的缓存构造函数。

`EnsureGearData()` 构造并返回：

```lua
ns.GearData = {
    ver = number,
    cls = { {classID, className}, ... },
    sub = { [classID] = { {subclassID, subclassName}, ... } },
    items = { {itemID, name, pack, icon}, ... },
}
```

`cls/sub` 是物品大类和子类的选项表；物品大类使用 `2` 武器、`4` 护甲。`items` 是顺序数组，并非 `items[itemID]`；`icon` 为图标名称。`pack` 是压缩整数，`Core/GearUI.lua` 的 `ROW_MT` 按以下方式解码：

| 字段 | 解码表达式 | 含义 |
| --- | --- | --- |
| `q` | `pack % 8` | 物品品质 |
| `ilvl` | `floor(pack / 8) % 256` | 物品等级 |
| `req` | `floor(pack / 2048) % 256` | 需要等级 |
| `u` | `floor(pack / 524288) % 32` | 物品子类 |
| `c` | `floor(pack / 16777216) % 2 == 1 and 4 or 2` | 物品大类 |
| `isNew` / `st` | `floor(pack / 33554432) % 2 == 1` | 新物品标记；`st` 为 `"new"` 或空字符串 |
| `s` | `GearSlots[floor(pack / 67108864) % 64 + 1]` | 装备栏位字符串 |

同一个 `EnsureGearData()` 中还构造以下辅助表：

| 导出 | 结构与含义 |
| --- | --- |
| `ns.GearSlots` | 栏位字符串字典数组，第 1 项为空字符串；其余如 `Head`、`Chest`、`One-Hand`、`Trinket` |
| `ns.GearWDLv[itemID]` | `{minLevel, maxLevel}`，世界掉落怪物等级范围 |
| `ns.GearSrcQ[itemID]` | 奖励该物品的代表 `questID` |
| `ns.GearSrcQLv[itemID]` | 奖励任务的可接等级 |
| `ns.GearQuestMap[questID]` | `{uiMapID, x, y}`，任务起始地图点 |
| `ns.GearQuestRace[questID]` | `"a"` 联盟或 `"h"` 部落；缺失键没有额外阵营限制信息 |

`EnsureGearSrc()` 独立构造并返回 `ns.GearSrc[itemID] = sourceText`。文本通常是 `"来源类别|地点或说明"`，也存在没有 `|` 的单段文本；它是展示信息，不是结构化来源关系表。装备 UI 还从副本掉落表建立来源索引，BIS 逻辑会读取 `EnsureGearSrc()` 的结果。

### Data_GearCls.lua

- `ns.GearCls[itemID] = classMask`：装备职业限制位掩码。消费者 `Core/BisUI.lua` 使用战士 `1`、圣骑士 `2`、猎人 `4`、潜行者 `8`、牧师 `16`、死亡骑士 `32`、萨满 `64`、法师 `128`、术士 `256`、武僧 `512`、德鲁伊 `1024`，以 `bit.band` 判断；缺失键不施加此项过滤。
- `ns.GearUni[itemID] = true`：唯一物品集合，用于 BIS 自动选装时避免重复选择。

### Data_GearVendors.lua

`ns.EnsureGearVendors()` 首次构造两张表并返回 `ns.GearVendors`：

```lua
ns.GearVendors[itemID] = {
    {npcID, areaID?, side?, englishName, localizedName?}, ...
}
ns.GearVendorSpawns[npcID] = {
    {areaID, uiMapID?, x?, y?}, ...
}
```

一个物品可有多个商人，一个商人可有多个刷新位置；`side` 为小写 `"a"/"h"` 或缺省。`GearUI.GearVendorEnts` 先筛玩家阵营，再优先选与商人条目 `areaID` 匹配且有 UiMapID 的位置，最后回退到其他位置。第 5 项名称优先于第 4 项。没有坐标或空刷新点数组均可能出现。

### Data_GearRareSpawns.lua

导出 `ns.GearRareSpawns[itemID] = { {npcID, uiMapID, areaID, x, y, name}, ... }`。这是按物品索引的稀有来源刷新点，一个物品可指向多个位置。注意这里地图顺序是 **UiMapID 在 AreaID 前**，与 `GearVendorSpawns` 相反。

### Data_GearQuestStart.lua

导出 `ns.GearQuestStart[questID] = {npcID, uiMapID?, x?, y?}`。提供装备奖励任务的起始 NPC 与地图点，供 BIS 来源交互等读取。与 `DungeonQuestStartNpc` 的第 2 项含义不同。

### Data_GearQuestChain.lua

- `ns.GearQuestChain = {Chain, ...}`；`Chain = {Stage, ...}`；`Stage = {questID, ...}`。链、阶段均有序，同阶段可有多个任务。UI 以 `questID → chainIndex` 建立缓存并按阶段展开，数据本身未另设 AND/OR 条件字段。
- `ns.GearQuestLoc2[questID] = {uiMapID, x, y, minLevel?}`：任务链中间步骤的位置/可接等级补充。装备 UI 优先读取 `GearQuestMap`，没有位置时再读取本表。

### Data_GearQuestReward.lua

导出 `ns.GearRewardQ[itemID] = questID`，为任务奖励反查补充。`Core/TipLines.lua` 与 `Core/BisUI.lua` 会联合 `GearSrcQ` 查询；每个物品在这张表中最多保留一个任务 ID，不代表该物品只有一个获得途径。

## 职业、天赋与 BIS

本组职业索引通常使用大写职业标识（如 `WARRIOR`、`DRUID`）；BIS 的 `slug` 则为小写。专精 key 是各数据表自己的约定，不能只凭名称直接互换，例如职业指南的 `ret` 与 PvP 套装的 `retri`。

### Data_BIS.lua

导出 `ns.EnsureBISData()`；第一次调用构造并返回 `ns.BIS`，后续调用复用已有表。

```lua
BIS = {
    updated = string,
    default = number,                         -- 默认等级档，当前为 30
    levels = { [level] = { updated = string, classes = Class[] } },
    classes = Class[],                        -- 与 levels[default].classes 指向同一表
}
Class = { slug = string, specs = Spec[] }
Spec = {
    id = string, tspec = string, label = string, key = string,
    slots = { [slotKey] = { AllianceItem, HordeItem } },
    rows = { [slotKey] = Candidate[] },
    enchs = Enchant[],
}
AllianceItem = { itemID, quality, enchantText? }
Candidate = { item = number, q = number, side = "a"|"h"|nil, src = Source }
Enchant = { slot = string, item = number?, lvl = number?, eff = string, name = string?, note = string? }
```

- `levels` 当前包含 20、30 两档；`id` 是预设类别（如 `pve`、`pvp`、`tank`），`tspec` 是职业专精，`label` 是显示名，`key` 是预设标识。
- `slots[slotKey][1]` 为联盟、`[2]` 为部落；各元组 `[1]` 是物品 ID、`[2]` 是品质、`[3]` 是可选附魔说明。槽位采用 `head`、`finger2`、`trinket2`、`main-hand`、`two-hand`、`shield` 等字符串。
- `rows` 是候选物品列表，允许空数组；`q` 在候选记录中表示品质，在 `src.q` 中表示任务 ID（源数据为字符串，可用 `tonumber` 转换）。
- `Source.t` 当前为 `quest`、`boss`、`craft`、`rare`、`books`、`other`；公共说明字段为 `note?`。任务来源带 `q?`；首领来源带 `dung?`、`boss?`、`rate?`；制造来源带 `prof?`（英文专业 key）、`lvl?`（技能等级）。`rate` 是显示文本，不能直接当数值概率。
- `enchs.item` 可能缺省（只有附魔名）；`lvl` 为专业技能要求。主要由 `Core/BisUI.lua` 消费，并结合装备目录补全物品资料。

### Data_ClassTier.lua

直接导出 `ns.ClassTier`：

- `meta = { patch, level, updated }`：适用版本、等级范围和更新时间。
- `specs[class] = { { key, name, nameEn, icon }, ... }`：该职业有序专精定义。
- `pages[] = { key, intro, tiers, factors, notes }`：排行页面；当前页面 key 为 `dps`、`tank`、`healer`。
- `tiers[] = { key, specs = { { class, spec }, ... } }`：等级档（如 `S` 到 `D`），其中 `spec` 引用 `specs[class][].key`。
- `factors[] = { factorName, explanation }`：位置数组 `[1]` 是评价因素名、`[2]` 是说明；`notes` 为字符串数组。

由 `Core/TierUI.lua` 读取；`icon` 是游戏图标路径。

### Data_ClassGuide.lua

导出懒加载函数 `ns.EnsureClassGuide()`，结果缓存在 `ns.ClassGuide`：

```lua
ClassGuide = {
    meta = { patch = string, level = number, updated = string },
    specs = { [class] = { [specKey] = {
        updated = string,
        sections = { { key = string, flow = FlowNode[] }, ... },
    } } },
}
```

章节 key 包括 `changes`、`viability`、`sw`、`beginner`、`systems`、`races`、`prof`、`stats`、`rotation`。`flow` 保留内容顺序，每个节点为 `{ t, v }`：

| `t` | `v` 的结构 |
| --- | --- |
| `p`、`h4` | 段落或小标题字符串 |
| `good`、`bad` | 优点或缺点字符串数组 |
| `tb` | 表格行数组；每行是字符串位置数组，第一格为标签，其余格为正文 |
| `ul` | `{ term = string, text = string }[]` |
| `races` | `{ race = string, side = faction, mark = string }[]`（`faction` 为 `alliance/horde`）；当前 `mark` 为 `tick` 或 `star` |

正文包含 `|s法术ID|` 等客户端内联标记，由 `Core/TierUI.lua` 解析和呈现。缺少某个职业/专精/章节时，不能假定自动继承其他专精内容。

### Data_ClassCombat.lua

基础文件导出 `ns.EnsureClassCombat()`，第一次调用构造 `ns.ClassCombat`：

- `meta = { patch, level, ranks }`，其中 `ranks = "game-client"` 表示法术等级信息由客户端确认。
- `spells[class][] = { spellNameKey, unlockLevel, rank1SpellID, rank2SpellID, ... }`：`[1]` 是法术检索 key（多为英文，也存在中文），`[2]` 是解锁等级提示（可为 0），`[3..n]` 为各等级/版本法术 ID。消费者从后向前寻找已学会的 ID，基础图标回退到 `[3]`。
- `rotation[class][specKey] = { note?, st = RotationEntry[], aoe = RotationEntry[] }`：单体与多目标优先级列表；记录为 `{ spell = spellNameKey, note = string? }`，`spell` 引用本职业 `spells` 的 `[1]`。
- `macros[class][] = { level, name, legacy?, body, what, explain }`：建议等级、宏名、旧宏名、宏模板、用途、逐行解释字符串数组。`body` 中的 `{SpellNameKey}` 由 `Core/ClassCombatUI.lua` 替换为客户端当前技能名；`legacy` 可为 `nil`。

英文覆盖文件 `enUS/Data_ClassCombat.lua` 直接构造 `ns.ClassCombat`，没有重新定义 `EnsureClassCombat`；繁体覆盖仍采用懒加载函数。这是本组本地化文件的实际加载行为差异。

### Data_ClassQuest.lua

同一文件包含三个对外数据入口：

1. `ns.ClassQuestChains[class] = Chain[]`：立即构造的职业任务链。
2. `ns.EnsureClassQuestInfo()`：懒加载、缓存并返回 `ns.ClassQuestInfo[questID]`。
3. `ns.ClassQuestItemName[itemID] = string`：任务奖励物品的中文名称回退表。

```lua
Chain = {
    t = string, key = string, steps = Step[],
    group = string?, races = number[]?, faction = "A"|"H"|nil,
    note = string?, after = number?, afterAny = number[]?,
    extra = boolean?, cat = string?, minLevel = number?,
    anyOrder = number[]?, choice = number[]?,
}
Step = questID | questID[]
QuestInfo = {
    n = string, cn = string?, l = number, r = number,
    f = "A"|"H"|nil, races = number[]?,
    s = Point[]?, e = Point?, items = number[]?, spells = number[]?, note = string?,
}
Point = { npcOrObjectID, name, zoneName, x, y, uiMapID }
```

- `t` 是链标题；`steps` 的顺序表示阶段，嵌套数组保存同阶段的多个任务/分支。`anyOrder` 和 `choice` 保存阶段下标；`after`/`afterAny` 保存前置任务 ID；`group` 关联同目标的地域/种族版本。`cat` 当前为 `endgame`；`extra` 表示额外支线。这些是源数据元信息；当前 `ClassQuestUI` 会递归展开 `steps` 展示，并未逐项执行上述全部元信息。
- `races` 是游戏种族 ID 数组，包含无限服自定义的 95、96。`l` 是任务等级，`r` 是可接等级；`n` 是原始任务名，`cn` 是中文名；`f` 缺省表示未限定阵营。
- 接取点 `s` 可有多个；当前数据的交付点 `e` 是单个元组，消费者兼容嵌套点数组并取第一个。点位 `x/y` 为 0–100 百分比；`0,0` 表示没有有效坐标，不能据此生成精确导航。第一个 ID 也可能是物件/容器，不应一律视为可对话 NPC。
- `items` 和 `spells` 分别是奖励物品 ID、奖励法术 ID 数组；由 `Core/ClassQuestUI.lua` 消费。

### Data_TalentTrees.lua

直接导出 `ns.TalentTrees[class] = { key, name, color, trees }`：

- `key` 为小写职业标识；`name` 为职业显示名；`color` 为 `#rrggbb` 字符串。
- `trees[] = { name, nameEn, icon, nodes }`：有序天赋树，顺序是天赋方案中树下标的依据。
- `nodes[] = { n, max, row, col, icon, passive, req?, status, desc }`：天赋名、最高等级、网格行列、图标名、是否被动、可选前置节点下标、变更状态、逐等级说明字符串数组。
- `req` 引用同一棵树 `nodes` 的 1 基下标；`status` 当前为 `same`、`changed`、`moved`、`new`。`desc[rank]` 是对应等级说明。

`Core/TalentTabUI.lua` 根据该表绘制节点与前置连线；调整节点顺序必须同时检查 `req` 和 `Data_TalentPlans.lua` 的引用。

### Data_TalentPlans.lua

直接导出 `ns.TalentPlans[class] = Plan[]`，方案为：

```lua
Plan = {
    name = string?, level = number,
    pts = { tree1Points, tree2Points, tree3Points },
    alloc = { [treeIndex] = { [nodeIndex] = rank } },
    seq = { { treeIndex, nodeIndex }, ... }?,
}
```

`alloc` 是稀疏的节点分配映射，树与节点下标引用 `TalentTrees[class].trees[treeIndex].nodes[nodeIndex]`；缺省节点表示未加点。`seq` 的每条元组表示投入一点的顺序，同一节点可重复出现。`name` 缺省时 UI 显示自动编号名称；`pts` 是各树点数摘要，实际分配和顺序分别存于 `alloc`、`seq`。

## 团本与 PvP 套装、军衔

### Data_RaidSets.lua

直接导出 `ns.RaidSetData = { updated, raid, total, pieces, batches, sets }`：

- `updated`、`raid` 为更新时间和团本名；`total`、`pieces` 是摘要信息，不能替代每套 `#ids`（专属套装实际件数并不一致）。
- `batches[] = { key, label, count, revealed? }`：批次定义，目前为 `t1`、`exclusive`。
- `sets[] = { class, id?, role?, spec?, armor?, batch, revealed?, name, ids, bonuses?, marks? }`。
- `class` 是大写职业标识；专属套装可为空字符串。`id` 为套装 ID；`role` 当前为 `dps`、`tank`、`heal`；`spec`、`armor` 为显示文本；`batch` 引用批次 key。
- `ids` 为有序物品 ID 数组；`bonuses[pieceCount] = string` 以激活套装效果所需件数索引；`marks[pieceCount] = { st, where?, note? }` 对相应效果补充变更标记，`st` 当前为 `baseline`、`same`、`changed`、`moved`、`new`。
- `revealed = false` 是尚未公开/待补全标记；消费者将缺省值视为已公开。`Core/RaidUI.lua` 根据实际 `ids` 生成物品卡片。

### Data_PvPRanks.lua

直接导出 `ns.PvPRankData`，包含：

| 字段 | 结构与含义 |
| --- | --- |
| `updated` | 更新时间字符串 |
| `marks[]` | `{ id, slot, rank }`：套装兑换印记物品 ID、部位 key、解锁军衔 |
| `ranks[rank]` | `{ pts, cum, week, a, h, s }`：本级点数、累计点数、最早解锁周、联盟奖励物品 ID 数组、部落奖励物品 ID 数组、双方共用奖励物品 ID 数组 |
| `caps[week]` | `{ rank, cum, inc }`：该周可达军衔、累计点数上限、当周增加量 |
| `battlefields[]` | `{ key, minLevel, maxLevel, size, cta }`：战场 key、等级范围、单方人数、战斗召唤轮换编号 |

当前军衔下标为 1–14，周上限为第 1–10 周，战场 key 为 `spear`、`ab`、`wsg`、`av`；`cta = 0` 是无轮换编号的记录。

### Data_PvPSets.lua

直接导出 `ns.PvPSetData = { updated, sets, spear, battle }`：

- `sets[] = { class, spec, blue = { A = itemID[], H = itemID[] }, epic = { A = itemID[], H = itemID[] } }`：职业/专精的蓝色与史诗品质套装，阵营 key 使用大写 `A/H`。
- `spec` 当前包括 `all`、`holy`、`retri`、`shadow`、`holydisc`、`enhance`、`resto`、`ele`、`feral`、`balance`。
- `spear[standingKey] = { A = itemID[], H = itemID[] }`：暗矛群岛声望奖励。
- `battle[battlefieldKey][standingKey] = { A = itemID[], H = itemID[] }`：其他战场奖励，当前仅包含 `ab`。声望 key 为 `friendly`、`honored`、`revered`、`exalted`。

套装与奖励均仅保存物品 ID，名称、图标和详情由客户端查询；由 `Core/PvPUI.lua` 消费。

### Data_PvPHonor.lua

直接导出 `ns.PvPHonorData = { updated, rankChangeFactor, cpFloor, cpCeiling, honorRatio, honorIncrements, milestones }`：

- `cpFloor[rank]`、`cpCeiling[rank]`：军衔积分区间的下限和上限，当前各 14 项。
- `honorRatio[rank]`、`honorIncrements[rank]`：荣誉与积分的换算系数及荣誉阈值，当前各 14 项。
- `rankChangeFactor[index]`：跨军衔积分增益系数序列，当前 15 项；消费者以目标军衔相关下标读取，不能强行裁成与其他数组等长。
- `milestones[rank] = number[]`：达到该军衔时供计算器显示的荣誉里程碑候选，当前有 2–14 的键。

`Core/PvPUI.lua` 使用这些数值估算荣誉收益和军衔进度；它与 `PvPRankData` 的赛季点数/周上限是两组不同的数据。

## 声望与拾取过滤

### Data_Factions.lua

直接导出有序数组 `ns.FactionsData`，每行 `{ id, name, side, group, desc, start, races?, rewards? }`：

- `id` 为声望阵营 ID，`name/desc` 为名称与说明；`side` 为 `alliance`、`horde`、`neutral`。
- `group` 当前为 `alliance`、`allianceForces`、`horde`、`hordeForces`、`cartel`、`other`、`prof`，用于显示分组。
- `start` 是默认初始声望数值，可为负数；`races[] = { raceOrFactionDescription, startingReputation }` 保存特定种族/阵营的起始值说明，第一项为显示文本，不是种族 ID。
- `rewards[standingKey] = itemID[]`，档位键包括 `neutral`、`friendly`、`honored`、`revered`、`exalted`；未配置的档位可以缺省。

`Core/FactionUI.lua` 优先采用客户端可取得的声望名称、描述和当前值，缺失时使用本表。英文覆盖中仍存在未翻译说明和不准确的名称文本，字段结构不等于翻译质量保证。

### Data_FactionQM.lua

直接导出 `ns.FactionQM[factionID] = { npcID, uiMapID, x, y }`：`[1]` 是军需官 NPC ID，`[2]` 是地图 ID，`[3]/[4]` 是 0–100 坐标。`factionID` 关联 `FactionsData[].id`；并非每个声望都有军需官记录。`Core/FactionUI.lua` 使用坐标创建导航点时会除以 100。

### Data_LootFilter.lua

导出 `ns.LootFilterData`（文件内简称 `D`）。它包含定义、运行时生成的索引/匹配式和预设，不是单一物品清单：

| 字段 | 结构 |
| --- | --- |
| `CLASS_WEAPON`、`CLASS_ARMOR`、`CLASS_QUEST`、`CLASS_QUEST_ALT` | 物品分类常量，分别为 2、4、12、9 |
| `DEFAULT_ICON` | 默认图标路径 |
| `FLAG_CLASS`、`FLAG_BNET`、`FLAG_TANK` | 职业限制、战网绑定、坦克过滤的字符串 key |
| `FlagLabel[flag]`、`ShuXingLabel[attributeName]` | UI 显示名映射 |
| `WeaponName[subclassID]`、`ArmorName[subclassID]` | 武器/护甲子类 ID 到名称映射；ID 含 0，不能用 `ipairs` 遍历完整映射 |
| `WeaponOrder`、`ArmorOrder` | 可展示子类的有序 ID 数组 |
| `WeaponIdByName[name]`、`ArmorIdByName[name]` | 根据展示顺序生成的名称到子类 ID 反向索引 |
| `WeaponSet[subclassID]`、`ArmorSet[subclassID]` | 展示子类集合，值为 `true` |
| `ClassUsable[class]` | `{ weapon = string[], armor = string[] }` 职业可用类型 |
| `ShuXing[attributeName]`、`ShuXingOrder` | 属性名到 Lua pattern 的映射及显示顺序 |
| `Nothave[attributeName]` | 该属性匹配时应排除的触发文本数组 |
| `TankKeywords` | 坦克属性匹配式数组 |
| `ClassPrefix`、`BnetBound`、`ExcludeLine` | 职业限制行前缀、绑定文本数组、应排除的提示行文本数组 |
| `PresetIcon[presetKey]` | 职业/角色预设图标路径映射 |
| `RoleShuXing[roleKey]` | 内部角色属性组合字符串数组（如 `t0`、`dps0`、`fx0`、`n0`） |
| `Presets[class][]` | `{ icon, name, useWeapon, useArmor, useShuXing, Tank }`；四个选择字段分别为武器名、护甲名、属性名、过滤 flag 的数组 |

加载时依据 `ns.IsForever` 和客户端 `_G` 本地化提示文本生成属性匹配式；预设的 `useShuXing` 会过滤掉当前没有匹配式的属性。`toPattern(string)` 转义 Lua pattern 特殊字符，并把空白转换为捕获片段；`KeyList(dim)` 根据 `Weapon/Armor/ShuXing/Class/BnetAccount/Tank` 返回 `{ key, label }[]`，其中武器/护甲 ID 会转为字符串 key。

`Core/LootFilter.lua`、`Core/LootFilterUI.lua` 使用上述索引和预设。繁体覆盖不仅翻译标签，也更换了部分作为索引的中文字符串，因此使用时应从同一份 `D` 取 key；本目录没有英文覆盖版的 `Data_LootFilter.lua`。

## 专业、配方与供应

专业数据以 `professionSlug` 关联，例如 `alchemy`、`blacksmithing`、`enchanting`、`engineering`、`leatherworking`、`tailoring`、`mining`、`herbalism`、`skinning`、`cooking`、`fishing`、`first-aid`、`poisons`、`comprehension`、`camping`。这些是稳定键，显示名另存。下面的数组下标均从 1 开始。

### Data_Professions.lua

导出 `ns.ProfData = { build, updated, order, perks, pro }`。

| 路径 | 结构与含义 |
| --- | --- |
| `build` / `updated` | 来源客户端版本、资料更新日期字符串；属于静态资料元数据 |
| `order` | 专业 slug 的显示顺序数组 |
| `perks[perkSlug]` | `{名称, 图标, 英文分类, 最高等级, 各等级说明[], 摘要, 来源标记, 待确认说明[]}` |
| `pro[professionSlug]` | 单个专业的概览记录 |

`pro` 记录包含 `name`、`icon`、`kind`（`primary` / `secondary` / `system`）、`section`、`guide`、`summary`、`status`；以及可选的 `title`、`description`、`recipes`、`sub`、`kinds`（配方类型名 → 数量）。概览计数与配方明细分别维护，不能把概览计数当作运行时扫描结果。

复杂字段：

- `cert = {认证物品ID, 名称, 图标, 所需技能, 解锁称号}`。
- `miles[] = {里程碑名称, 所需技能, 奖励点数}`。
- `camp[] = {物品ID, 名称, 图标, 所需技能, 总说明, 增益说明, 作用说明, 替代设施名, 互斥增益名, 容量文本, 材料[], 图纸信息}`；材料为 `{itemID, quantity}`，图纸信息为 `{formulaItemID, 附加数值}`，当前消费逻辑仅使用图纸 ID。
- `perks[]` 引用顶层 `perks` 的 slug。`tips[]`、`verify[]`、`unknowns[]` 均为文本数组。
- `racials[] = {种族特性slug, 英文名称, 说明}`；`bonuses[] = {名称, 图标, 类型, 说明}`。
- `steps_title`、`steps_note` 为过程说明标题/备注；`steps[] = {步骤标题, 说明}`。这里的 `steps` 是展示文本，区别于 `ProfLeveling.steps` 的数值路线。
- 钓鱼的 `ranks[] = {阶级名称, 技能上限文本, 学习方式说明, 可选书籍itemID}`。
- `fishing` 内分 `spells`、`lures`、`food`、`items`、`titles`；每组记录统一为 `{ID, 备用名称, 图标, 说明, 分类/副标题, 所需技能, 技能加成, 持续分钟, 角色等级, 学会后解锁标记, 新增标记, 可作钓具标记, 需求文本[]}`。ID 的类型由组别决定：法术、物品或称号。

### Data_ProfRecipes.lua

导出 `ns.ProfRecipeKeys`（专业 slug 数组）、`ns.ProfRecipes`（按 slug 索引的配方分区）和 `ns.EnsureProfRecipes(keys?)`。

该文件将每个专业保存为私有构造函数，通过 `ProfRecipes` 的 `__index` 首次访问时实例化并缓存。直接 `pairs(ns.ProfRecipes)` 只能看到已实例化的专业；完整遍历应使用 `ProfRecipeKeys`，或先调用 `EnsureProfRecipes()`。

普通专业分区结构：

```lua
ProfRecipes[slug] = {
    word = "Recipe", -- 配方类型标签
    counts = { items = ..., total = ..., sourced = ..., unreadable = ... },
    groups = { { groupKey, displayName, icon, count }, ... },
    rows = { recipeRow, ... },
}
```

`counts` 是资料生成时的统计（配方物品数、总记录数、有来源数、未能读取数），不是学习状态。普通 `recipeRow` 各位置：

| 下标 | 含义 |
| --- | --- |
| 1–4 | 制造法术ID、产物itemID、单次产量、`groups` 的分类键 |
| 5–6 | 装备/等级等副标题、效果说明 |
| 7–10 | 学习技能、变黄技能、变绿技能、变灰技能 |
| 11 | 新增/改版标记 |
| 12 | 材料数组 `{{itemID, quantity}, ...}` |
| 13 | 可选图纸信息 `{formulaItemID, 原始附加数值}`；当前核心消费逻辑按第 1 项关联来源和购买信息 |
| 14 | 可选来源记录 `{skill, read, vendors[], drops[]}` |
| 15 | 改版前材料数组 |
| 16–17 | 套装名称、护甲类型文本 |

来源记录中，`skill` 是来源所标技能，`read` 是读取状态/来源标记（可见 `wowhead`、`classic`、空字符串；采矿补充还使用 `forever`、`unknown`）。`vendors[]` 记录可含 `name`、`zone`、`cost`（显示文本）、`skill`、`id`，合并后还可有 `area`、`side`、`price`、`cur`、`amt`、`stock`；`drops[]` 可含 `npc`、`zone`、`chance`、`lv={min,max}`、`id`，合并后可有 `area`。缺字段、空数组和 `nil` 均实际存在。

附魔分区另有三套元组，不能套用普通行下标：

- `enchants[] = {原名称, 显示名称, 附魔部位, 效果, 学习技能, 黄, 绿, 灰, 材料[], 来源记录, 新增标记, 原始标记, 适用条目[], spellID, 可选关联物品ID}`。适用条目在 UI 中读取其第 3 项说明；第 12 项在当前展示代码中未使用。
- `crafted[] = {spellID, 产物itemID, 产量, 学习技能, 黄, 绿, 灰, 材料[], 图纸itemID字符串或空串, 新增标记}`。绿技能可能为 `nil`，展示代码可按黄/灰中点补算。
- `favor[] = {交出物品ID, 所需技能, 商人青睐数量, 换得物品名称, 换得物品ID}`。

`ProfSourceMerge.Fill(row)` 会按图纸 ID 从 `ProfSources` 合并商人/掉落信息到普通行的 `[14]`，并加入 `__srcDone` 防止重复合并。运行时技能/材料/可用性修正由专业模块处理，静态行不是实时客户端状态。

### Data_ProfLeveling.lua

导出 `ns.ProfLeveling[professionSlug]`。各专业仅提供适用字段：

| 字段 | 结构与含义 |
| --- | --- |
| `steps[]` | `{起始技能, 目标技能, spellID, 预计制作次数}` |
| `shopping[]` | `{itemID, 预计总需求量}` |
| `sold[]` | 可向商人购买的材料 itemID 数组 |
| `parts[]` | 中间制作品 itemID 数组 |
| `quest[]` | 通过任务途径学习的配方法术 ID 数组；不是 questID |
| `learn[]` | 学习来源判断使用的配方法术 ID 数组 |
| `rinfo[spellID]` | `{learn, yellow, green, grey, mats={{itemID, quantity},...}, makes=itemID或nil, trainer=boolean}`，补充尤其是附魔路线的配方信息 |
| `rods[]` | `{内部记录ID, 附魔棒itemID}`；当前运行时代码未读取该字段 |
| `camps.a` / `.h` | `{营地组织名称, 区域备用名称, 营地名, x, y, areaID}` |
| `vendor.a` / `.h` | `{名称, npcID, 职能, 图标, x, y, areaID}` |

`x/y` 是 0–100 百分比坐标；`areaID` 须经 `AreaMap` 转换成 UI 地图 ID。路线是静态参考，当前专业模块也能按客户端数据、价格和库存生成路线。

### Data_ProfMining.lua

采矿补充文件，执行时增补 `ns.ProfRecipes.mining`、`ns.ProfLeveling.mining`、`ns.ProfRecipeMeta[spellID]`，并确保 `ProfRecipeKeys` 含 `mining`。

`ProfRecipes.mining` 使用普通配方分区和 14 项配方行，分类为 `Smelting`。`ProfRecipeMeta[spellID] = {profession="mining", station, tools={}, availabilityUnknown?}`；`station` 为 `forge`、`blackForge`、`moltenFoundry`，`availabilityUnknown=true` 表示来源/可用性尚不确定。

采矿路线除普通步骤外，还可含 `{起始技能, 目标技能, 0, 0, checkpoint=true, profession="mining", reason="gather"}`，表示该区间需要采集，不能把法术 ID 0 当作制造配方。

### Data_ProfGathering.lua

导出 `ns.ProfGathering`，不同专业的元组不同：

- `mining[]` / `herbalism[] = {产物itemID数组, 所需技能, 区域分布[]}`；区域分布条目为 `{areaID, 资料中的节点数量}`。
- `skinning[] = {{怪物最低等级, 最高等级}, 产物itemID数组, 区域分布[]}`；此处分布数量表示可剥皮对象资料数量，不是掉率。
- `fishing[] = {areaID, 原始水域技能档位, 原始最低技能值}`；第三项可为负数，当前区域展示/兜底路线主要使用前两项。新的推荐技能与不脱钩阈值见 `ProfFishingRoutes`，不能混用两者阈值。

### Data_ProfFishingRoutes.lua

导出 `ns.ProfFishingRoutes = {fish, fishingSteps}`。

- `fish[itemID] = {a=水域记录数组, rate?, pool?, night?, season?}`；`rate` 是 0–1 捕获比例参考，`pool` 表示鱼群、`night` 表示夜间、`season` 表示季节限制。
- 水域记录为 `{zoneID=areaID, minSkill, noGetaway, note?}`；`minSkill` 是最低钓鱼技能，`noGetaway` 是含鱼竿/鱼饵/装备加成的不脱钩技能。
- `fishingSteps[] = {from, to, areas=水域记录数组, fishIDs=itemID数组, note}`，提供钓鱼自身的升级分段。

多个鱼种和路线步骤共享本文件构造的水域数组；这些是参考位置/门槛，没有精确坐标时只打开区域地图。

### Data_ProfTrainers.lua

导出惰性加载函数 `ns.EnsureProfTrainers()`；首次调用构造并返回 `ns.ProfTrainers[professionSlug] = {ranks, list}`。

- `ranks[] = {en, zh, tw, cap, sk?, lv?}`：三种语言的等级名、技能上限、进阶所需技能、角色等级。
- `list[] = {rng, fac, map, x, y, en, zh, tw, loc_en, loc_zh, loc_tw}`：可教技能区间文本、阵营、UI 地图 ID、百分比坐标、三语 NPC 名、三语位置说明。当前基础文件的 `fac` 值为 `A` / `H`。

同一 NPC 可因教授区间/阵营而重复出现，`list` 不是以 npcID 为键的唯一 NPC 表。

### Data_ProfVendors.lua

导出 `ns.ProfVendors[npcID] = {areaID, uiMapID, x, y}`。用于专业商人地图标记，坐标为 0–100；与 `ProfVendorNames`、`ProfVendorSide` 按 npcID 关联。

### Data_ProfVendorNames.lua

导出 `ns.ProfVendorNames[npcID] = 名称字符串`。用于补齐来源/供应记录中未直接保存的商人名称。

### Data_ProfVendorSide.lua

导出 `ns.ProfVendorSide[npcID] = "a" | "h" | "n"`，分别为联盟、部落、中立。此表使用小写，与供应扁平数组的数字阵营码、训练师的 `A/H` 不同。

### Data_ProfDropNpcs.lua

导出 `ns.ProfDropNpcs[英文NPC名称] = {本地化名称, uiMapID?, x?, y?}`。名称是字符串键，坐标缺失时可只有名称；配方内旧式 `drops[].npc`、商人备用名称可据此取得显示名与位置。

### Data_ProfDropNames.lua

导出 `ns.ProfDropNames[npcID] = 本地化名称`。与按英文名称键索引的 `ProfDropNpcs` 互补，尤其用于 `ProfSources.d[].id` 的名称兜底。

### Data_ProfNPCLocs.lua

导出 `ns.ProfNPCLocsMeta = {schemaVersion, source, npcCount}` 和惰性加载函数 `ns.EnsureProfNPCLocs()`。

构造 `ns.ProfNPCLocs[npcID] = {{areaID占位, uiMapID, x, y}, ...}`，一个 NPC 可有多个位置；本文件第一项当前为 `0` 占位，实际地图标记读取第 2–4 项。坐标为百分比，消费者通常取位置列表第一项作为兜底。

### Data_ProfItemNames.lua

导出 `ns.ProfItemNames[itemID] = 名称字符串`。这是客户端物品信息不可用时的名称兜底表，不是完整物品数据库。

### Data_ProfSources.lua

导出 `ns.ProfSourcesMeta = {schemaVersion, source, itemCount, vendorRows, dropRows, dropCap}`，惰性加载函数 `ns.EnsureProfSources()`。首次调用同时构造 `ProfSources` 与 `ProfZoneText`：

```lua
ProfSources[itemID] = {
    v = { {id=npcID, name=..., area=areaID, side="a"/"h"/"n",
           price=铜币价格, stock=库存, cur=代币ID, amt=代币数量}, ... },
    d = { {npc=名称, id=npcID, pct=掉落概率, area=areaID}, ... },
}
ProfZoneText[areaID] = 区域名称
```

`v` / `d` 和内部字段均可缺省。`stock=-1` 表示不限量；`cur/amt` 用于非金币购买。`pct` 通过现有 UI 的兼容规则展示：`0 < pct <= 1` 时乘以 100，否则按百分数处理；不要默认所有历史 `chance/pct` 记录都使用同一种单位。`dropCap` 表示收录掉落条目的上限，不表示全量掉落来源。

### Data_ProfMakeSrc.lua

导出 `ns.ProfMakeSrc[产物itemID] = 图纸itemID`。当直接查产物没有商人/掉落资料时，专业 UI 可再查该图纸在 `ProfSources` 中的来源。

### Data_ProfCraftIndex.lua

公开接口是 `ns.ProfCraftSlugOf(itemID) -> professionSlug | nil`。文件内部用 `S` 保存专业 slug 数组、`M[itemID]` 保存 `S` 的下标，二者均为私有表。用于轻量判断物品属于哪个制造专业，不需要实例化完整配方。输入非数字或未收录时返回 `nil`。

### Data_ProfMaterialSupply.lua

导出 `ns.ProfMaterialSupplyMeta` 和惰性加载函数 `ns.EnsureProfMaterialSupply()`。

元数据包括 `schemaVersion=2`、`gameFlavor`、`fingerprint`、`verifiedAt`、`scope`、`complete`、`offerCount`、`itemCount`。当前 `complete=false`，表示已发现/人工登记的常规供应子集。

`ns.ProfMaterialSupply[itemID]` 是按 **5 个数一组**串接的扁平数组：

```text
npcID, priceCopper, bundleQuantity, sideCode, rawTag, ...
```

`priceCopper` 是该批次价格，`bundleQuantity` 是每批件数，单件价格须相除；`sideCode=1/2/3` 分别为联盟/部落/中立。第 5 项是原始标记码，当前 `ProfSupply` 不读取或定义其语义；不应将其解释成 areaID。`ProfSupply.BuildList` 将本表转为 `unlimited=true` 的常规材料供应记录，因此库存和地图不在该 5 项元组中。

当前 `ProfessionUI.VendorOffersOf` 仍有按 8 项读取本表的旧逻辑，而 `ProfSupply` 按 schemaVersion 2 使用 5 项。阅读或扩展数据时以本文件和 `ProfSupply` 的 5 项布局为准；8 项布局属于下一个配方报价表。

### Data_ProfFormulaOffers.lua

导出 `ns.ProfFormulaOffersMeta`（`schemaVersion`、`source` 和物品/报价/金币/代币/不限量/限量计数）及惰性加载函数 `ns.EnsureProfFormulaOffers()`。

`ns.ProfFormulaOffers[配方物品ID]` 是按 **8 个数一组**串接的数组：

```text
npcID, copperCost, stock, sideCode, areaID, bundleQuantity, currencyID, currencyAmount, ...
```

`stock=-1` 表示不限量，`0` 表示当前不可购买，非负数表示限量库存。`sideCode=1/2/3` 表示联盟/部落/中立，`0` 未指定。代币 ID/数量为 `0` 时表示没有该项代币消耗。`ProfSupply.FormulaList` 用于金币报价，`DisplayList` 还保留代币报价；它们会把扁平数组解码为命名字段记录。

### Data_ProfFormulaQuests.lua

在 `ns.ProfFormulaMeta` 中增补按图纸 itemID 索引的任务来源：

```lua
ProfFormulaMeta[itemID] = {
    source = {questOnly=true, quests={{id=questID, name=任务名}}, url=来源URL}
}
```

注意键是配方物品 ID，`quests[].id` 才是任务 ID；它区别于 `ProfLeveling.quest[]` 的法术 ID。

### Data_ProfTools.lua

导出 `ns.ProfTools = {revision, [professionSlug]=工具记录数组}`。工具记录为 `{spell, item, minSkill, bindOnPickup?}`，分别是制作法术、工具物品、最低技能、拾取绑定标记，用于制造前置条件/采购计划。

### Data_ProfSpecializations.lua

导出 `ns.ProfSpecializationsMeta = {schemaVersion, revision, source, fpr, entries, gates, trainer, item, pending, src}`，以及 `ns.ProfSpecializations[spellID] = {flags, specializationAbilityID?}`。

`flags` 按位组合：`1` 表示训练师教授，`2` 表示图纸/物品教授，`4` 表示含待确认来源。第二项是所需专业专精能力法术 ID，缺失视为无专精限制。`ProfGates` 负责解码与玩家已学专精对比；数据中存在待确认标记时不能将来源视作完全核实。

### Data_ProfSpecializationQuests.lua

导出：

- `ns.ProfSpecializationQuestMeta = {schemaVersion, revision, sourceBuild, sourceCommit, sourceURL, correctionURL}`。
- `ns.ProfSpecializationAbilities[专精能力spellID] = professionSlug`。
- `ns.ProfSpecializationQuests[choice] = 专精任务定义`，当前 `choice` 为 `goblin` / `gnomish`。

任务定义字段为 `id`、`choice`、`profession`、`abilityID`、`minSkill`、`minLevel`、`questID?`、`questName`、`prerequisiteQuestIDs?`、`inputs={{itemID, quantity},...}`、`npcID?`、`npcName?`、`zone?`、`mapID?`、`x?`、`y?`、`factions?`。`mapID` 是 UI 地图 ID，`x/y` 为百分比。

需要按阵营选不同任务时，使用 `variants.A` / `variants.H`，其内部可覆盖 `questID`、`prerequisiteQuestIDs` 和 NPC/位置字段。`factions={A=true,H=true}` 为可用阵营集合。

### 专业本地化文件

`enUS` 与 `zhTW` 都提供 `Data_Professions.lua`、`Data_ProfRecipes.lua`、`Data_ProfLeveling.lua`、`Data_ProfTrainers.lua`；`zhTW` 另提供 `Data_ProfVendorNames.lua`、`Data_ProfDropNpcs.lua`、`Data_ProfItemNames.lua`。这些文件有语言检查，结构沿用同名基础表，主要替换显示文本和整表构造。

`zhTW/Data_ProfTrainers.lua` 重新定义惰性构造函数；`enUS/Data_ProfTrainers.lua` 直接建立 `ProfTrainers`，之后基础 `EnsureProfTrainers()` 的早退分支会复用它。`zhTW/Data_ProfItemNames.lua` 先建立繁体表，再补入基础表中缺失的键。采矿等共用补充文件在语言文件之后加载，因此继续增补最终语言版本的表。

## 探索、导航与补给

### Data_Explore.lua

核心书籍表为按序号索引的 `ns.ExploreBooks`：

```lua
ExploreBooks[index] = {
    itemID, areaID, x, y, hint, side?, alternateLocations?, route?,
}
-- alternateLocations = { { areaID, x, y, hint? }, ... }
-- route = { { areaID, x, y }, ... }
```

这里的 `areaID` 是区域编号，需经项目地图映射转换，不能直接视作 `uiMapID`；坐标为百分比。`[6]` 是可选阵营信息，当前 UI 的领地标签另按区域表推导；`[7]` 是同一本书的其他拾取位置；`[8]` 是洞口、上山起点到目标等分段坐标。备选地点仍属于同一物品，不应重复计算收集进度。

同文件包含以下表：

| 导出 | 结构与用途 |
| --- | --- |
| `ns.ExploreBookQuests` | `[bookItemID] = questID`；对应每本书交付任务，用于判断完成状态。 |
| `ns.ExploreBookSet` | `[bookItemID] = setID`；当前档位为 `1 / 35 / 45 / 60`。 |
| `ns.ExploreZoneLv` | `[areaID] = string`；区域等级范围或主城标记。 |
| `ns.ExploreRecIDs` | `[bookItemID] = true`；推荐书籍集合。 |
| `ns.ExploreUnverIDs` | `[bookItemID] = true`；位置未验证集合。 |
| `ns.ExploreBookMeta` | `{ updated, quest10, quest20, quest25 }`；更新时间和三个阶段的任务名。 |
| `ns.ExploreBookRewards` | 有序奖励记录数组：`{ at, req, questID, quest, items?, choices? }`；`at` 是书籍数量门槛，`req` 是可接等级，`items = { A = itemID, H = itemID }`，`choices = itemID[]`。 |
| `ns.ExploreHowTo` | `{ title, intro, detail, steps = { { t, d }, ... } }`；说明标题、引言、补充说明、操作步骤。 |
| `ns.ExploreMageBonus` | `{ prof, ability, reagent, title, desc = string[] }`；研究专业名、技能名、材料物品 ID 和法师说明。 |

### Data_ExplorePets.lua

导出 `ns.ExplorePets` 与 `ns.ExplorePetMeta = { updated }`。宠物记录与下述玩具、旗帜共用获取攻略结构：

| 下标/字段 | 类型与含义 |
| --- | --- |
| `[1]` | 获得宠物/玩具的物品 ID。 |
| `[2]` | 图标名后备值，不包含 `Interface\\Icons\\` 前缀。 |
| `[3]` | `"A" \| "H" \| nil`，阵营限制。 |
| `[4]` | `"party" / "solo" / "easy"`，获取难度/组队提示。 |
| `[5]` | `areaID`。 |
| `[6]`、`[7]` | 百分比坐标；`false` 表示没有固定坐标，UI 只显示区域。 |
| `[8]` | 获取来源摘要。 |
| `[9]` | 步骤数组，基本元素为 `{ t = text, m = marks?, q = questID? }`。 |
| `[10]` | 可选摘要链接数组，用于给 `[8]` 中的名称/坐标加交互。 |
| `__display` | 宠物模型显示 ID，供收藏界面预览。 |

`marks` 支持 `{ label, areaID, x, y }` 的地图链接及 `{ label, "item", itemID }` 的物品提示链接。没有固定坐标时同样允许用 `false` 保持元组位置。步骤的 `q` 配合文本 `#q` 占位符，运行时换成客户端任务名。

### Data_ExploreToys.lua

`ns.ExploreToys` 使用 `ExplorePets` 的相同 10 槽攻略结构；当前包含火炬获取步骤及摘要位置链接。`ns.ExploreToyMeta = { updated }` 记录更新时间。

### Data_ExploreBanner.lua

`ns.ExploreBanner` 同样采用上述获取攻略元组。其 `[9]` 的步骤还支持：`{ h = sectionTitle }`（分节标题）、`num`（自定义步骤编号）和 `n = true`（灰色备注）。`m` 可同时关联地图点与回响物品。

### Data_ExploreRoutes.lua

`ns.ExploreRoutes = { h = RouteTarget[], a = RouteTarget[] }`，这里是小写阵营键。每个目标为：

```lua
{
    name = targetName,
    mapID = uiMapID,
    fp = flightPointDescription,
    time = estimatedTimeText,        -- 可选
    dst = { uiMapID, x, y },
    ovl = { overlayName, ... },       -- 可选，关联 ns.RouteOvl
    races = {
        { race = raceName, time = optionalTime, steps = {
            { t = title, k = kind, d = description,
              x = optionalX, y = optionalY,
              m = { uiMapID, x, y } },
        } },
    },
}
```

`k` 当前使用 `die`（死亡）、`grave`（复活）、`fp`（飞行点）、`travel`（移动）、`item`（中转）。`races` 是按种族分支的路线，不是种族 ID 映射；可有 `race = "其他"`。步骤坐标 `x/y` 用于地图上的动作点，`m` 为显式导航点/所在地图，均可缺省；种族分支的 `time` 优先于目标 `time`。

### Data_RouteOvl.lua

`ns.RouteOvl[overlayName] = { uiMapID, texturePath, textureWidth, textureHeight, contentWidth, contentHeight }`。

`texturePath` 为贴图资源路径；`[3..4]` 为贴图尺寸，`[5..6]` 为有效内容尺寸，UI 以 `contentWidth/textureWidth` 与 `contentHeight/textureHeight` 裁切 UV。名称可由 `ExploreRoutes[].ovl` 引用，地图也会展示同 `uiMapID` 的覆盖图。

### Data_Plunder.lua

`ns.PlunderData = { goods = { { id, band, cat, mats }, ... } }`。

- `id`：待装填补给物品 ID；`band`：UI 标记的物品等级档位（当前 `10 / 25 / 40 / 50`）。
- `cat`：`ingot / herb / leather / enchant / potion / food / bandage / device / gear / other / mismatch`；最后一个表示数据不一致项。
- `mats = { { itemID, quantity }, ... }`：装填所需材料；专业 UI 用拍卖行快照计算总成本。数据本身不保存实时价格。

### Data_Crates.lua

`ns.CratesData` 含两个有序数组：

- `crates = { { id, tier, level, favor?, opts }, ... }`：`id` 为补给箱物品 ID，`tier` 为 `1..4`（学徒、熟练、专家、工匠），`level` 为等级要求，`favor` 为青睐奖励，缺省时 UI 标为未验证。`opts = { { itemID, quantity }, ... }` 是可选装填方案，UI 比较各方案成本，不把所有方案材料相加。
- `writs = { { quest, target, qty, rep, level, item }, ... }`：`quest` 为物资单任务 ID，`target` 为要交付的物品 ID，`qty` 为交付数量，`rep` 为声望奖励，`level` 为等级要求，`item` 为物资单物品 ID。它们都不是 NPC ID；UI 会比较直接购买目标物品和自行制作的成本。

以上 18 个文件中，`Data_Dungeons.lua`、`Data_DungeonEntry.lua`、`Data_DungeonGuide.lua`、`Data_DungeonLoot.lua`、`Data_DungeonQuests.lua` 以及 5 个 `Data_Explore*.lua` 文件有 `enUS/`、`zhTW/` 同名版本，导出结构相同。语言文件经 locale 守卫后整表覆盖，不能据目录名假设文字已经全部翻译；当前 `enUS/Data_Explore.lua` 仍保留多段中文。其余 8 个文件没有这两种语言副本。

## 收藏与基础商人价格

### Data_CollectionMounts.lua

导出 `ns.CollectionMounts = {Mount, ...}` 和 `ns.CollectionMountMeta = {updated = "YYYY-MM-DD"}`。Mount 同时包含位置字段和命名字段：

```lua
Mount = {
    id, kind, icon?, sourceGroup, description, displayID?, cameraScale?,
    npcs = { {npcID, name}, ... },
    riding = number?,
    speed = number?,
    teach = {rawValue1, rawValue2?},
}
```

`kind` 为 `"spell"` 或 `"item"`，决定第 1 项属于哪种 ID；第 6 项为模型 display ID，第 7 项为镜头缩放（读取时缺省 `1`）。`sourceGroup` 包括 `job`、`store`、`legacy`、`bmah`、`rep`、`drop`、`unknown`。`riding` 使用 `75/150` 等骑术要求，`speed` 为速度加成百分比数值。

`npcs` 把说明中的商人名与 NPC ID 关联，供点击定位。`teach` 保存形如 `{40, 2000000}` 或 `{60}` 的原始数值元组，文件没有为两项提供独立类型定义；当前 `CollectionUI` 仅通过 `teach` 是否存在显示学习物品卡，不读取其内部数值。坐骑显示名主要通过游戏物品/法术 API 查询，缺失时使用 `NameOverrides` 等回退。

### Data_CollectionPets.lua

导出 `ns.CollectionPets = {Pet, ...}`；其基础位置布局与 `ExplorePets` 相同：

| 下标/字段 | 含义 |
| --- | --- |
| `[1]` | 宠物物品 ID |
| `[2]` | 回退图标名 |
| `[3]` | `"A"` / `"H"`，`nil` 为双阵营 |
| `[4]` | 来源/难度键，如 `craft`、`vendor`、`drop`、`quest`、`store`、`unknown` |
| `[5]`, `[6]`, `[7]` | `areaID, x, y`；无定位时可为 `false` |
| `[8]` | 来源简述 |
| `[9]` | 步骤数组：字符串或 `{t = text, m = { {label, areaID, x?, y?}, ... }}` |
| `__display` | 模型 display ID；消费者兼容旧 `[11]` |
| `__cam` | 可选镜头缩放；消费者兼容旧 `[12]`，缺省 `1` |
| `cost` | 可选价格：铜币数字，或 `{amount, "c"/"i", currencyOrItemID, fallbackIcon?}` |

`m` 中的 label 对应步骤文本里的可点击片段，`areaID` 经地图映射后定位；`cost[2] == "c"` 表示货币，`"i"` 表示物品兑换。记录可在固定字段之间穿插命名字段，不会改变位置下标。

`Core/CollectionUI.lua` 的 `CG.Pets()` 先加入 `ExplorePets`，再加入 `CollectionPets`，以 `[1]` 物品 ID 去重，同 ID 优先保留探索记录。

### Data_NameOverrides.lua

导出 `ns.NameOverrides = {spell = {[spellID] = name}, item = {[itemID] = name}}`，提供收藏坐骑/宠物的简体中文显示名修正。该文件受简体中文守卫控制；消费者根据物品/法术 API 返回情况决定使用时机，不会修改原 ID。

### Data_VendorPrices.lua

导出 `ns.VendorPriceSeed[itemID] = priceCopper`，表示基础商人单价的静态种子。`Core/VendorPriceDB.lua` 在没有其他符合条件的报价且上下文不要求实测价时，将其转换为 `source="seed"`、`quantity=1`、`bundleSize=1`、`priceBasis="catalogue"` 的报价。它不包含商人位置、库存或玩家折扣观测，实际购买条件应结合专业供应与运行时商人记录判断。

## 文件与语言版本索引

下表列出全部基础文件、导出入口及实际存在的语言副本。语言列的链接指向对应文件；`—` 表示没有同名语言副本，通常继续使用基础数据。表内包含延迟构造函数的导出名，数据表本身可能需要首次调用后才存在。

| 基础文件 | 导出入口 | enUS | zhTW |
| --- | --- | --- | --- |
| [Data_AreaMap.lua](../Core/Data/Data_AreaMap.lua) | `AreaMap` | — | — |
| [Data_BIS.lua](../Core/Data/Data_BIS.lua) | `BIS`、`EnsureBISData` | [有](../Core/Data/enUS/Data_BIS.lua) | [有](../Core/Data/zhTW/Data_BIS.lua) |
| [Data_BossModel.lua](../Core/Data/Data_BossModel.lua) | `BossModelDisplay` | — | — |
| [Data_BossPos.lua](../Core/Data/Data_BossPos.lua) | `BossPos` | — | — |
| [Data_BossSkills.lua](../Core/Data/Data_BossSkills.lua) | `BossSkills` | — | — |
| [Data_ClassCombat.lua](../Core/Data/Data_ClassCombat.lua) | `ClassCombat`、`EnsureClassCombat` | [有](../Core/Data/enUS/Data_ClassCombat.lua) | [有](../Core/Data/zhTW/Data_ClassCombat.lua) |
| [Data_ClassGuide.lua](../Core/Data/Data_ClassGuide.lua) | `ClassGuide`、`EnsureClassGuide` | [有](../Core/Data/enUS/Data_ClassGuide.lua) | [有](../Core/Data/zhTW/Data_ClassGuide.lua) |
| [Data_ClassQuest.lua](../Core/Data/Data_ClassQuest.lua) | `ClassQuestChains`、`ClassQuestInfo`、`ClassQuestItemName`、`EnsureClassQuestInfo` | — | — |
| [Data_ClassTier.lua](../Core/Data/Data_ClassTier.lua) | `ClassTier` | [有](../Core/Data/enUS/Data_ClassTier.lua) | [有](../Core/Data/zhTW/Data_ClassTier.lua) |
| [Data_CollectionMounts.lua](../Core/Data/Data_CollectionMounts.lua) | `CollectionMountMeta`、`CollectionMounts` | — | [有](../Core/Data/zhTW/Data_CollectionMounts.lua) |
| [Data_CollectionPets.lua](../Core/Data/Data_CollectionPets.lua) | `CollectionPets` | [有](../Core/Data/enUS/Data_CollectionPets.lua) | [有](../Core/Data/zhTW/Data_CollectionPets.lua) |
| [Data_Crates.lua](../Core/Data/Data_Crates.lua) | `CratesData` | — | — |
| [Data_DungeonEntry.lua](../Core/Data/Data_DungeonEntry.lua) | `DungeonEntry`、`DungeonEntryRoute` | [有](../Core/Data/enUS/Data_DungeonEntry.lua) | [有](../Core/Data/zhTW/Data_DungeonEntry.lua) |
| [Data_DungeonGuide.lua](../Core/Data/Data_DungeonGuide.lua) | `DungeonGuide` | [有](../Core/Data/enUS/Data_DungeonGuide.lua) | [有](../Core/Data/zhTW/Data_DungeonGuide.lua) |
| [Data_DungeonLoot.lua](../Core/Data/Data_DungeonLoot.lua) | `DungeonLoot` | [有](../Core/Data/enUS/Data_DungeonLoot.lua) | [有](../Core/Data/zhTW/Data_DungeonLoot.lua) |
| [Data_DungeonQuestFlow.lua](../Core/Data/Data_DungeonQuestFlow.lua) | `DungeonQuestFlow`、`EnsureDungeonQuestFlow` | — | — |
| [Data_DungeonQuests.lua](../Core/Data/Data_DungeonQuests.lua) | `DungeonQuestAlias`、`DungeonQuestExtInfo`、`DungeonQuestPreExtra`、`DungeonQuestPreNote`、`DungeonQuests`、`DungeonQuestShare`、`EnsureDungeonQuestExtInfo` | [有](../Core/Data/enUS/Data_DungeonQuests.lua) | [有](../Core/Data/zhTW/Data_DungeonQuests.lua) |
| [Data_Dungeons.lua](../Core/Data/Data_Dungeons.lua) | `DungeonData` | [有](../Core/Data/enUS/Data_Dungeons.lua) | [有](../Core/Data/zhTW/Data_Dungeons.lua) |
| [Data_Explore.lua](../Core/Data/Data_Explore.lua) | `ExploreBookMeta`、`ExploreBookQuests`、`ExploreBookRewards`、`ExploreBooks`、`ExploreBookSet`、`ExploreHowTo`、`ExploreMageBonus`、`ExploreRecIDs`、`ExploreUnverIDs`、`ExploreZoneLv` | [有](../Core/Data/enUS/Data_Explore.lua) | [有](../Core/Data/zhTW/Data_Explore.lua) |
| [Data_ExploreBanner.lua](../Core/Data/Data_ExploreBanner.lua) | `ExploreBanner` | [有](../Core/Data/enUS/Data_ExploreBanner.lua) | [有](../Core/Data/zhTW/Data_ExploreBanner.lua) |
| [Data_ExplorePets.lua](../Core/Data/Data_ExplorePets.lua) | `ExplorePetMeta`、`ExplorePets` | [有](../Core/Data/enUS/Data_ExplorePets.lua) | [有](../Core/Data/zhTW/Data_ExplorePets.lua) |
| [Data_ExploreRoutes.lua](../Core/Data/Data_ExploreRoutes.lua) | `ExploreRoutes` | [有](../Core/Data/enUS/Data_ExploreRoutes.lua) | [有](../Core/Data/zhTW/Data_ExploreRoutes.lua) |
| [Data_ExploreToys.lua](../Core/Data/Data_ExploreToys.lua) | `ExploreToyMeta`、`ExploreToys` | [有](../Core/Data/enUS/Data_ExploreToys.lua) | [有](../Core/Data/zhTW/Data_ExploreToys.lua) |
| [Data_FactionQM.lua](../Core/Data/Data_FactionQM.lua) | `FactionQM` | — | — |
| [Data_Factions.lua](../Core/Data/Data_Factions.lua) | `FactionsData` | [有](../Core/Data/enUS/Data_Factions.lua) | [有](../Core/Data/zhTW/Data_Factions.lua) |
| [Data_Gear.lua](../Core/Data/Data_Gear.lua) | `EnsureGearData`、`EnsureGearSrc`、`GearData`、`GearQuestMap`、`GearQuestRace`、`GearSlots`、`GearSrc`、`GearSrcQ`、`GearSrcQLv`、`GearWDLv` | [有](../Core/Data/enUS/Data_Gear.lua) | [有](../Core/Data/zhTW/Data_Gear.lua) |
| [Data_GearCls.lua](../Core/Data/Data_GearCls.lua) | `GearCls`、`GearUni` | — | — |
| [Data_GearQuestChain.lua](../Core/Data/Data_GearQuestChain.lua) | `GearQuestChain`、`GearQuestLoc2` | — | — |
| [Data_GearQuestReward.lua](../Core/Data/Data_GearQuestReward.lua) | `GearRewardQ` | — | — |
| [Data_GearQuestStart.lua](../Core/Data/Data_GearQuestStart.lua) | `GearQuestStart` | — | — |
| [Data_GearRareSpawns.lua](../Core/Data/Data_GearRareSpawns.lua) | `GearRareSpawns` | — | [有](../Core/Data/zhTW/Data_GearRareSpawns.lua) |
| [Data_GearVendors.lua](../Core/Data/Data_GearVendors.lua) | `EnsureGearVendors`、`GearVendors`、`GearVendorSpawns` | — | [有](../Core/Data/zhTW/Data_GearVendors.lua) |
| [Data_GravePos.lua](../Core/Data/Data_GravePos.lua) | `GravePos` | — | — |
| [Data_LootFilter.lua](../Core/Data/Data_LootFilter.lua) | `LootFilterData` | — | [有](../Core/Data/zhTW/Data_LootFilter.lua) |
| [Data_MapDetail.lua](../Core/Data/Data_MapDetail.lua) | `MapDetail` | — | — |
| [Data_MapPins.lua](../Core/Data/Data_MapPins.lua) | `MapPins` | [有](../Core/Data/enUS/Data_MapPins.lua) | [有](../Core/Data/zhTW/Data_MapPins.lua) |
| [Data_NameOverrides.lua](../Core/Data/Data_NameOverrides.lua) | `NameOverrides` | — | — |
| [Data_NPCLoc.lua](../Core/Data/Data_NPCLoc.lua) | `NPCLoc`、`QuestPreNpcID` | [有](../Core/Data/enUS/Data_NPCLoc.lua) | [有](../Core/Data/zhTW/Data_NPCLoc.lua) |
| [Data_Plunder.lua](../Core/Data/Data_Plunder.lua) | `PlunderData` | — | — |
| [Data_ProfCraftIndex.lua](../Core/Data/Data_ProfCraftIndex.lua) | `ProfCraftSlugOf` | — | — |
| [Data_ProfDropNames.lua](../Core/Data/Data_ProfDropNames.lua) | `ProfDropNames` | — | — |
| [Data_ProfDropNpcs.lua](../Core/Data/Data_ProfDropNpcs.lua) | `ProfDropNpcs` | — | [有](../Core/Data/zhTW/Data_ProfDropNpcs.lua) |
| [Data_Professions.lua](../Core/Data/Data_Professions.lua) | `ProfData` | [有](../Core/Data/enUS/Data_Professions.lua) | [有](../Core/Data/zhTW/Data_Professions.lua) |
| [Data_ProfFishingRoutes.lua](../Core/Data/Data_ProfFishingRoutes.lua) | `ProfFishingRoutes` | — | — |
| [Data_ProfFormulaOffers.lua](../Core/Data/Data_ProfFormulaOffers.lua) | `EnsureProfFormulaOffers`、`ProfFormulaOffers`、`ProfFormulaOffersMeta` | — | — |
| [Data_ProfFormulaQuests.lua](../Core/Data/Data_ProfFormulaQuests.lua) | `ProfFormulaMeta` | — | — |
| [Data_ProfGathering.lua](../Core/Data/Data_ProfGathering.lua) | `ProfGathering` | — | — |
| [Data_ProfItemNames.lua](../Core/Data/Data_ProfItemNames.lua) | `ProfItemNames` | — | [有](../Core/Data/zhTW/Data_ProfItemNames.lua) |
| [Data_ProfLeveling.lua](../Core/Data/Data_ProfLeveling.lua) | `ProfLeveling` | [有](../Core/Data/enUS/Data_ProfLeveling.lua) | [有](../Core/Data/zhTW/Data_ProfLeveling.lua) |
| [Data_ProfMakeSrc.lua](../Core/Data/Data_ProfMakeSrc.lua) | `ProfMakeSrc` | — | — |
| [Data_ProfMaterialSupply.lua](../Core/Data/Data_ProfMaterialSupply.lua) | `EnsureProfMaterialSupply`、`ProfMaterialSupply`、`ProfMaterialSupplyMeta` | — | — |
| [Data_ProfMining.lua](../Core/Data/Data_ProfMining.lua) | `ProfLeveling`、`ProfRecipeKeys`、`ProfRecipeMeta`、`ProfRecipes` | — | — |
| [Data_ProfNPCLocs.lua](../Core/Data/Data_ProfNPCLocs.lua) | `EnsureProfNPCLocs`、`ProfNPCLocs`、`ProfNPCLocsMeta` | — | — |
| [Data_ProfRecipes.lua](../Core/Data/Data_ProfRecipes.lua) | `EnsureProfRecipes`、`ProfRecipeKeys`、`ProfRecipes` | [有](../Core/Data/enUS/Data_ProfRecipes.lua) | [有](../Core/Data/zhTW/Data_ProfRecipes.lua) |
| [Data_ProfSources.lua](../Core/Data/Data_ProfSources.lua) | `EnsureProfSources`、`ProfSources`、`ProfSourcesMeta`、`ProfZoneText` | — | — |
| [Data_ProfSpecializationQuests.lua](../Core/Data/Data_ProfSpecializationQuests.lua) | `ProfSpecializationAbilities`、`ProfSpecializationQuestMeta`、`ProfSpecializationQuests` | — | — |
| [Data_ProfSpecializations.lua](../Core/Data/Data_ProfSpecializations.lua) | `ProfSpecializations`、`ProfSpecializationsMeta` | — | — |
| [Data_ProfTools.lua](../Core/Data/Data_ProfTools.lua) | `ProfTools` | — | — |
| [Data_ProfTrainers.lua](../Core/Data/Data_ProfTrainers.lua) | `EnsureProfTrainers`、`ProfTrainers` | [有](../Core/Data/enUS/Data_ProfTrainers.lua) | [有](../Core/Data/zhTW/Data_ProfTrainers.lua) |
| [Data_ProfVendorNames.lua](../Core/Data/Data_ProfVendorNames.lua) | `ProfVendorNames` | — | [有](../Core/Data/zhTW/Data_ProfVendorNames.lua) |
| [Data_ProfVendors.lua](../Core/Data/Data_ProfVendors.lua) | `ProfVendors` | — | — |
| [Data_ProfVendorSide.lua](../Core/Data/Data_ProfVendorSide.lua) | `ProfVendorSide` | — | — |
| [Data_PvPHonor.lua](../Core/Data/Data_PvPHonor.lua) | `PvPHonorData` | — | — |
| [Data_PvPRanks.lua](../Core/Data/Data_PvPRanks.lua) | `PvPRankData` | — | — |
| [Data_PvPSets.lua](../Core/Data/Data_PvPSets.lua) | `PvPSetData` | — | — |
| [Data_QuestEndNpc.lua](../Core/Data/Data_QuestEndNpc.lua) | `DungeonQuestEndNpc` | — | — |
| [Data_QuestStartLoc.lua](../Core/Data/Data_QuestStartLoc.lua) | `DungeonQuestStartLoc` | — | — |
| [Data_QuestStartNpc.lua](../Core/Data/Data_QuestStartNpc.lua) | `DungeonQuestStartNpc` | — | — |
| [Data_RaidSets.lua](../Core/Data/Data_RaidSets.lua) | `RaidSetData` | [有](../Core/Data/enUS/Data_RaidSets.lua) | [有](../Core/Data/zhTW/Data_RaidSets.lua) |
| [Data_Route.lua](../Core/Data/Data_Route.lua) | `DungeonRoute`、`DungeonRouteNote` | — | — |
| [Data_RouteOvl.lua](../Core/Data/Data_RouteOvl.lua) | `RouteOvl` | — | — |
| [Data_TalentPlans.lua](../Core/Data/Data_TalentPlans.lua) | `TalentPlans` | — | — |
| [Data_TalentTrees.lua](../Core/Data/Data_TalentTrees.lua) | `TalentTrees` | — | — |
| [Data_VendorPrices.lua](../Core/Data/Data_VendorPrices.lua) | `VendorPriceSeed` | — | — |

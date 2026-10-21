# DungeonsForever 架构与修改导航

核对日期：2026-10-21。依据当前下载仓库合并后的源码；当前 TOC 版本为 1.8.36。合并来源及取舍见 `MERGE_NOTES.md`。
本文记录实际实现，后续功能变更后应重新核对相应部分。

## 1. 项目边界

- 原生 WoW Lua 插件，单窗口手册，固定 HUI 外观；无前端框架、服务端或独立构建流程。
- 当前目录是内层 Git 仓库，分支 `codex/merge-installed-1.8.28`；以下载版 1.8.20 为基础迁入安装版 1.8.28。专业统一入口在 `df-data-pipeline/_temp/fc_update.py`，默认检查，`--apply` 经完整三语校验后事务发布正式 `Core/Data`；旧 `df-prof-pipeline-v1.0/` 留档停用。`tests/` 包含 Lua 5.1 模拟测试与基准脚本，见 `tests/README.md`。
- 所有源码、脚本、测试及数据修改只允许在 `C:\Users\yewei\Downloads\DungeonsForever\DungeonsForever`。游戏安装目录中的插件副本只能只读核对，禁止编辑、生成、部署或清理；当前会话的默认工作目录不能视为写入授权。
- 顶层目录：`Core/` 业务与界面，`Core/Data/` 数据，`Locales/` 文案，`Libs/` 内嵌库，`Media/` 图片与地图等资源。
- 当前共 30 个 Core 顶层 Lua 文件；数据文件共 124 个：基础 52 个、enUS 36 个、zhTW 36 个。
- 版本显示从 `DungeonsForever.toc` 的 `## Version` 读取，不应在各页面重复写死。`addon_version.txt` 当前值为 `655404`，用途未确认，不作为插件显示版本。

## 2. 加载顺序与共享命名空间

没有 require/module loader。WoW 按 TOC/XML 顺序执行文件，各文件使用 `local _, ns = ...` 共享同一个表。`_G.DF_NS` 供调试访问。

实际加载链：

```text
DungeonsForever.toc
  → Locales/zhCN.lua → 按语言加载 zhTW/enUS 文案
  → Libs/embeds.xml
      → LibStub / CallbackHandler / LibDataBroker / UTF8
      → Core/Bridge.lua → LibHUI → LibDBIcon
  → Core/Core.lua → Core/Hui.lua
  → 基础 Data_*（包含 Route、QuestStartNpc/Loc、QuestEndNpc、ClassCombat、ClassQuest）
  → 按语言加载 zhTW/enUS 数据覆盖
  → Data_ProfItems / Data_ProfMaterialSupply / Data_ProfFormulaQuests / Data_ProfMining / Data_ProfFishingRoutes（语言覆盖之后的独立扩展）
  → LootFilter.lua → DungeonUI.lua
  → PvPUI / FactionUI / MapUI / LootFilterUI / RaidUI
  → ProfEconomy → ProfRecovery → ProfFishing → ProfRouteSolver → ProfRouteAuto → ProfExecution
  → ProfessionUI → AuctionatorBridge → ProfFollow → ProfItemPrices
  → ExploreUI → ExploreMap → CollectionUI → BisUI → TierUI
  → ClassCombatUI → ClassQuestUI → GearUI
  → MainFrame.lua → QuickBar.lua
```

- `Bridge.lua` 经 XML 加载，并不直接列在 TOC 中；必须先于 LibHUI，把 `addon.db` 指向 `DungeonsForeverDB.libHUI`，在 ADDON_LOADED 后重接存档引用。
- `Core.lua` 的 `ns.Init(fn)` 收集初始化回调；自身 ADDON_LOADED 后通过 `C_Timer.After(0, ...)` 顺序执行，并逐个 `xpcall` 隔离错误。
- 文件执行时注册模块和函数；初始化回调执行时，排在 TOC 后面的 MainFrame 等对象已经建立。因此不能把回调内的访问随意搬到文件顶层。
- 新增模块时检查加载先后，特别是文件顶层捕获的 `local Host = ns.ProfHost`、数据引用或其他模块引用。

## 3. 客户端条件

以 `Core.lua` 中 `GetBuildInfo()` 第四返回值为准：

| 标记 | 当前判定 | 作用 |
| --- | --- | --- |
| `ns.IsTitan` | `[16000,17000)`、`[38000,40000)` 或 `[120000,130000)` | 历史命名，实际为支持客户端标记，不是单指 Titan |
| `ns.IsForever` | `[16000,17000)` | 无限服标记 |
| `ns.IsRetail` | `[120000,130000)` | 正式服标记 |
| `ns.LoadForeverPages` | IsForever 或 IsRetail | 专业、探索、藏品、声望、BIS、指南、PvP、装备库页面准入 |

TOC 的 Interface 声明范围更广，不代表所有声明客户端都能通过业务运行时门禁。
部分模块注释写“只对无限服加载”，实际使用的是 `LoadForeverPages`，应读代码判定。
`MainFrame.lua` 的斜杠页面直达仍使用 `IsForever` 限制扩展页，与 UI 的 `LoadForeverPages` 不完全一致；这里只记录差异，未修改。

## 4. 窗口、路由与公共宿主

- `MainFrame.lua` 创建 1000×708 主窗，公开 `ns.MainFrame` 和兼容别名 `ns.TalentSimFrame`，负责拖动、位置/缩放、设置弹窗、关于页、小地图入口及斜杠命令。
- `DungeonUI.lua` 是架构中心，不只是副本页：
  - `ns.DungeonUI`（局部 U）：页面状态、容器、主标签、构建与路由。
  - `ns.DungeonModule`（局部 DG）：副本逻辑，以及物品/任务读取、地图定位、控件辅助、加载调度等公共能力。
  - `ns.ProfHost`：导出 U、DG、MakeFS、NewButton、描边/提示工具、颜色和内容尺寸；许多页面都依赖它，名称虽为 ProfHost，实际用途不限于专业。
- `U:Build()` 建立主页面容器并恢复选中页；`U:EnsureBuilt(key)` 按页触发模块构建；`U:SwitchSub(key)` 处理客户端门禁、保存选中页、显隐、构建和 Open/Refresh。
- 页面模块通常提供点调用 `Module.Build(page)`、`Module.Open()`、`Module.Refresh()`；U 自身使用冒号调用。不要因名字相似而混用点/冒号。
- 对外入口：`ns.Open()`、`ns.Toggle()`、`ns.OpenPage(key)`、`ns.ShowDungeonDetail(id)`；小地图和快捷栏复用这些入口。
- 常用命令 `/df`、`/fbsc`、本地化 `/副本手册`。直达别名包括 fb/tb/zy/ts/hp/wm/bis/zn；当前别名表没有 PvP/Gear 直达项。

## 5. 页面与支撑模块

| 功能 | 主要实现 / 导出 | 关联数据或协作点 |
| --- | --- | --- |
| 副本列表、掉落、任务、攻略 | DungeonUI / DungeonModule | DungeonData、DungeonLoot、DungeonQuests、DungeonGuide；稳定副本 id 贯穿各表 |
| 副本地图、首领详情、世界任务钉 | MapUI / MapModule | BossPos、BossModelDisplay、BossSkills、MapPins、AreaMap、NPCLoc、DungeonEntry；依赖 ProfHost.U/DG |
| 团本时间线、列表、套装 | RaidUI / RaidModule | 文件内排期表、RaidSetData；团本详情复用副本详情能力 |
| 专业总览、配方、采集、升级 | ProfessionUI / ProfModule | ProfData、ProfRecipes、ProfLeveling、ProfGathering、训练师/商人、CratesData/PlunderData |
| 专业客户端输入与规则 | ProfEconomy | 角色/专业/配方/库存/学费读取、配方规范化、排除草稿与角色存档 |
| 最终产物估值与成本归属 | ProfRecovery | 售价/手续费及可信数量快照、最终剩余产物收入、递归归属成本与净支出 |
| 整数采购及路线搜索 | ProfRouteSolver | 共享库存账本、材料制购组合、另一专业制材/联合升级、分帧搜索 |
| 自动专业升级路线门面 | ProfRouteAuto | 旧方案兼容；最省钱异步快照、缓存、发布通知、停止/继续 |
| 制作执行及持久记录 | ProfExecution | 冻结执行计划、分段技能与材料义务、真实次数/产出、重算余量、按需补料 |
| 专业跟随 HUD、购物清单 | ProfFollow | ProfModule、ProfRouteAuto、材料背包状态；AuctionBridge 导出清单 |
| 物品采购报价 | ProfItemPrices | 普通材料先检查独立不限量供货证据，再比较货架整组价与 AH；图纸独立读取原 NPC 报价、库存和来源 |
| 拍卖行清单桥接 | AuctionatorBridge / AuctionBridge | 调用 Auctionator API；不可用时提供可复制导入串 |
| 探索及相关收集活动 | ExploreUI / ExploreModule | ExploreBooks、奖励、宠物、玩具、旗帜等数据 |
| 探索地图路线及追踪 | ExploreMap | 由 ExploreModule 驱动；世界地图钉/线池、路线、追踪条、航点 |
| 坐骑、宠物藏品 | CollectionUI / CollectionModule | CollectionMounts/Pets、NameOverrides；模型与 NPC 定位 |
| 声望与军需官 | FactionUI / FactionModule | FactionsData、FactionQM |
| BIS 配装与方案 | BisUI / BisModule | BIS、装备目录、附魔/制皮配方；存在跨页面数据依赖 |
| 职业排行、专精指南 | TierUI / TierModule | ClassTier、ClassGuide；文字攻略含原 rotation 正文；另有循环/宏/职业任务模式 |
| 输出循环、宏 | ClassCombatUI / ClassCombatUI | ClassCombat；由 TierUI 驱动，独立于原文字攻略 |
| 职业任务 | ClassQuestUI / ClassQuestUI | ClassQuest、任务起终点和 NPC 资料；共享任务/物品异步刷新 |
| PvP 军衔、周进度、声望、套装 | PvPUI / PvPModule | PvPRankData、PvPHonorData、PvPSetData |
| 装备库、属性筛选、心愿单 | GearUI / GearModule | GearData、商人/稀有来源、任务与套装数据；BuildCatalog 构建索引 |
| 掉落装备过滤 | LootFilter + LootFilterUI | Data_LootFilter → 判定引擎 → 配置 UI；ShouldGrey/Apply 等用于显示过滤 |
| 主窗右侧快捷栏 | QuickBar | 推荐副本、专业、探索入口；读取 QuickCfg，与设置/过滤弹窗联动位置 |

## 6. 数据、语言与客户端异步信息

- `Locales/zhCN.lua` 先建立 `ns.L`，缺词返回键本身；键通常是简中文案。zhTW/enUS 再按客户端语言覆盖。
- `ns.DL` 用于数据文本翻译。`Core/Data/` 为基础数据，`Core/Data/enUS`、`zhTW` 在其后按语言加载，覆盖同名 ns 表或初始化函数；并非所有基础文件都有两种语言副本。
- 副本以稳定字符串 id 串联各表，物品/任务/技能/NPC 主要以数字 ID 关联；掉落、配方等大量表采用位置字段数组，修改前必须读文件头的字段定义。
- 大数据并非全部立即建表：`EnsureGearData()`、`EnsureBISData()`、`EnsureClassGuide()` 是惰性入口；`ProfRecipes` 通过元表按专业首次取值建表，`ProfRecipeKeys` 列出键，`EnsureProfRecipes(keys)` 可选择预热。
- 遍历惰性 ProfRecipes 时注意：`pairs()` 只见已经实例化的条目，不能代替 ProfRecipeKeys 或 EnsureProfRecipes。
- 掉落/配方中的物品显示通常优先客户端名称、图标、品质、描述；不同数据集仍可能含静态名称/来源/覆盖项，不能笼统假设全部只存 ID。
- DG.RequestItem → 客户端请求/Item 续接 → 事件回调 → RefreshItemCards；监听器只处理本插件请求过的 ID。任务同样依赖任务数据与任务状态事件补刷新。
- 不能将首次 API 返回 nil 当作永久无数据，也不能在每个全局物品事件中重扫全部页面。
- 专业六表由 `df-data-pipeline/_temp/fc_update.py` 统一生成及三语发布。维护输入保留当前新增、修正、来源、顺序与省略规则，不从旧Lua回捞；原文与维护冲突或已有记录丢失时整批阻止发布。未接管的数据/业务代码/语言文件保持原样。其余历史工具和输入仍在综合包，不默认执行旧同步或部署脚本。
- 2026-10-21已按用户确认离线发布70450：正式三语专业总表和规范JSON为1.60.1.70450/2026-10-16，毒药与理解仍保留70338真实来源；客户端根价数据保留，材料采购资格以独立供货表为准。安装包直接取发布后正式文件，验收见 `df-data-pipeline/PUBLISH_70450.md`。
- 客户端及商人/NPC五份CSV默认从流水线自己的 `_temp/_fc/inputs/` 只读快照输入，来源和SHA-256单列记录；统一入口不导入、调用或监控 `scripts/` 的生产代码，也不启动wow.tools.local。各脚本输入见 `df-data-pipeline/SCRIPT_INPUTS.md`，旧包249份原件与功能核对见 `LEGACY_PARITY.md`。`--stage-dir/--package-zip`可保留验证后的新批次并直接生成安装ZIP，正式`Core/Data`和成功指针保持不动。
- 图纸商人采集优先读取 Wowhead `sold-by` Listview 的内嵌 JSON，隐藏页签也能提取通货、数量、阵营及完整金币价；HTML 表格作为兼容入口。当前商人角色读取 `vendors-soldby-json-20261021.csv` 修复快照，原五份 CSV 保留原字节与修改时间；输入清单和同目录审计记录逐页哈希、原记录修正及新增商人行。兑换价格独立保留 `currency_kind/id/amount`；材料供货证据与价格另走独立材料链，不修改图纸输入。
- 1.8.36：附魔来源缺 `formulaID` 时，`ProfItemPrices.GetFormulaItemID` 仅复用当前客户端 build 的明确且唯一教学关系；多图纸歧义或版本不匹配不猜测。维护输入移除 26 条错误删除附魔法术 ID 的操作，三语配方经生成器重建，每份仅恢复这 26 个字段。169 条附魔中 163 条有法术 ID、108 条有唯一图纸关联，其余缺项保留；恢复/启示的通货报价不转换为金币采购资格。
- 配方学习来源统一由 `ProfEconomy.LearningSource` 读取明确训练师证据（客户端正观察、规范化来源或 `ProfSpecializations.routes` 的 `trainerObserved=true`），训练师优先于关联图纸。普通、附魔、crafted、升级来源与采购共用此规则；保留原始图纸但不强制购买，专精/明确不可用/用户排除仍独立限制。学习规则指纹升级到 2，旧路线等待手动重算；来源各层输入与缺口见 `df-data-pipeline/SCRIPT_INPUTS.md`。
- 图纸商人名字优先已有本地化，缺译名时保留规范原名，确实无名才用 NPC 编号；旧保存记录的编号可由其原名恢复，不重复追加相同原文。提示、选择框及采购来源采用同一名字回退；默认随当前角色阵营过滤明确异方，中立与未知保留，阵营未知不改写为中立。
- `scripts/export_buyprice/export-item-buy-prices.ps1` 在 Windows PowerShell 5.1 下调用本机 wow.tools.local，下载并验证匹配当前 Forever build 的最新 Hotfix，串行导出三语 ItemSparse，并只读取一次 Item。输出 `output/item-buy-prices.csv`（enUS/zhTW/zhCN 名称、原始基础组价、组数、零价/缺价和版本）及 `output/item.csv`（Item 全字段，供 `scripts/gen_vendors.py` 按 ClassID/SubclassID 筛配方）。导出器不生成 Lua；连同下述图纸学习条件 CSV，三份输出全部验证后共同发布，失败回滚旧输出。`df-data-pipeline/_temp/fc_prof_items.py` 再合并商人、NPC 和客户端价格三表，生成固定 19 列的 `DataProfItems.csv`，并由同一 CSV 内容生成 schema 2 的 `Data_ProfItems.lua`；`--from-csv` 可单独重建物品 Lua。独立底层脚本默认仍输出工具样例；统一入口将本轮物品、商人、专精及三语同批发布正式目录。旧试验导入脚本和三份 `Data_VendorPrices.lua` 已移除。
- 材料购买资格与基础价格分开：固定19列 CSV 和 schema 2 继续完整保留客户端根 `cost_copper`、`VendorStackCount` 及图纸 NPC 报价，但根价不证明任何供货资格。材料链按维护的少量耗材种子发现常规供应商，再按 NPC 抓整张货架；只有明确不限量、纯金币、无未满足条件且阵营可购买的供货记录进入独立 `Data_ProfMaterialSupply.lua`。正常在线运行刷新 NPC、货架与价格；失败 NPC 本轮降级，不沿用历史资格，离线重放保留原状态与核验时间。维护与运行说明见 `df-data-pipeline/MATERIAL_VENDORS.md`。

- 专业学习专精数据独立生成：价格导出器另输出 `recipe-item-specializations.csv`，仅把图纸物品的 `RequiredAbility` 沿明确教学关系关联至配方法术。`_temp/fc_prof_specializations.py` 合并图纸与 Wowhead Forever 的训练师证据，写入 `_temp/_fc/data/trainer-recipe-specializations.csv` 和 `Data_ProfSpecializations.lua`；`fc_update.py` 已接入该步骤，正式插件输出命令见管线 README。正式 TOC 在经济模块前加载 `Core/Data/Data_ProfSpecializations.lua` 与独立任务配置 `Data_ProfSpecializationQuests.lua`。`ns.ProfSpecializations[spellID]` 保留独立学习途径与来源，缺证据为 `pending`，不同途径不自动合为统一限制。目标客户端 build 与网页来源版本分开记录；跨来源 patch/build 的旧证据保留但不作为目标版本的已确认要求。网页抓取采用缓存、串行间隔、跨进程互斥和持久冷却，在线失败不发布最终产物。
- `ProfEconomy` 统一读取实际已学专精、角色工程选择及配方学习资格。优先 `C_SpellBook.IsSpellKnown`，成功的 false 与接口缺失/异常分开；任务历史不能证明当前能力。已学配方免重复检查学习门槛，制作仍服从客户端可用状态。明确限制按具体学习途径判断，缺字段途径不能绕过其他已确认要求；普通未知配方继续参与，不增加待确认标签。
- 工程选择默认不开启，已有能力自动可用。选择分支且目标至少 200 时，求解状态增加入门任务、已解锁能力和完成标记；低目标不提高。任务消费与升级共用库存、AH 数量、NPC 整包和图纸账本，递归任务制材限于工程。最省钱同时比较交付时机和升级；其他自动模式保留升级评分，在首个门槛节点优化任务采购。固定攻略过滤不可用配方并保留缺口提示。已交任务物品从可售产物及续接库存中扣除。
- 执行段 `kind="specialization_quest"` 保存任务、NPC、交付物及产出分配。HUD 等待实际能力确认；正常解锁只推进计划，不清空制作记录。选择、规则版本及数据指纹变更使旧协程、冻结计划、补料和购物导入等待手动重算。只有工程作为升级目标时安排任务，辅助工程以及其他专业仅用角色已具备的专精。
- 专精的重复更新入口为 `_temp/fc_refresh_specializations.py`，也可由 `fc_update.py --specializations-only` 调用。默认检查，`--apply`才发布；在线和离线都只读已有客户端三CSV与九表DB2快照，核实Item原文、ItemSparse价格/名称/组数、RequiredAbility、ID覆盖及Build/Hotfix/内容哈希，不再调用外部导出器。在线只刷新网页。准备结果仅含训练师CSV、Lua、三个审计及schema2成功状态；客户端CSV作为inputs记录，绝不覆盖。原schema1状态仍可按哈希迁移。审计动态比较前后未关联集合，不固定物品数；书籍子类不直接排除，wuxianwow目录匹配不充当教学或专精证据。网页和外部目录默认复用七天有效缓存，检查或失败运行可保留缓存与日志，但不替换正式产物。

## 7. 存档

唯一 TOC SavedVariables 是 `DungeonsForeverDB`，没有单独的 SavedVariablesPerCharacter。`ns.DB()` 返回根表并保证 ui 存在。

主要分区：`ui`（窗口/缩放/小地图/quick）、`libHUI`、`dungeon`、`raid`、`prof`、`explore`、`bis`、`tier`、`factions`、`gear`、`wishlist`、`vendorPrices`；诊断信息也存根表。

- 不能把所有状态都当角色级：大量 UI 偏好与方案直接存在共享表中。
- 副本任务的 `dungeon.dungeonQSide` 显式保存 `all/A/H`；旧缺失值按角色阵营和当前任务计数选择默认。`dungeon.mapQuestPins` 缺失时默认关闭，已保存的 true/false 保持原值。列表与总览共用阵营筛选，任务控制栏为两排以容纳五个按钮及开关。
- 装备过滤显式分角色：`ui.lootFilter[服务器][角色]`，有版本校验和默认方案。
- 专业跟随状态：`prof.follow[角色名-服务器名]`；部分购物清单偏好仍为共享设置。
- 专业经济规则及客户端观测：`prof.economy[角色名-服务器名]`，包含按目标专业保存的排除规则、按客户端 build 隔离的配方与可用目录观测。1.8.18 不再读取学费、工具或初始库存；排除草稿在内存中，点击重算才提交。
- 旧根表 `profVendorOffers`、`vendorPrices` 的历史商人报价不再读取或写入，也不再创建；无需清除整个角色存档。`ProfItemPrices` 不订阅商人窗口事件，不读取 Auctionator 的商人价格缓存；AH 行情与数量观测仍按既有规则保存。
- 新字段沿用缺失补默认/已有版本迁移逻辑，不应为新增开关重置整个存档。

## 8. 分帧构建、渲染与预热

- `ns.IdleJobs`：普通/紧急两队列，通过 OnUpdate 驱动；普通任务战斗中暂停；当前队列预算普通 6ms、紧急 12ms。任务返回 true 才结束，否则进入后续帧继续；错误任务被丢弃。
- `DG.Loader` / Gate / PushStep / RunSteps / `ns.PhasedStart`：构建队列与协程，带进度闸门。省电/标准/激进基础预算 2/4/8ms，当前实现会自适应调整 cap，不能视为严格固定上限。
- `ns.PaintJob`：已有页面的协程分帧重绘，按 key 和 generation 管理；默认 4ms，可替换/取消旧任务。页面有 built/building/queued 或对应状态与帧池，修改时保留生命周期约束。
- `U:SchedulePrebuild()` 当前直接 return，不能依据相邻注释认定它会预建全部页面。
- 但 `Core.lua` 登录后另有预热：根据快捷栏页签显隐，装载装备数据、目录及图标/文字/物品信息，预热专业配方；随后尝试 U:Build()。其他页面批量 EnsureBuilt 受 `DungeonsForeverDB.dfPrebuild` 开关控制。实际是按需构建与登录预热并存。
- `MainFrame.lua` 首次 Open 还有 RevealStart 渐进显示，与数据预热/PhasedStart 是不同机制。
- 关闭主窗会做 tooltip/hover 清理与分步 GC。`ns.ReleasePages()` 是显式页面清理入口，不等于 WoW 提供帧销毁，也不代表关闭窗口自动卸载页面。

## 9. 修改导航与核验边界

- 改页面视觉：对应 UI 文件 + Hui.lua；保留 ProfHost 尺寸、锚点、遮罩层级及池化复用关系。公共外观经 `ns.hui` 适配层，避免各页直接改 LibHUI。
- 改页面准入/新增页面：同步检查 Core 标记、TOC 顺序、U 的 Build/EnsureBuilt/SwitchSub/UpdateActiveSub/页签定义、QuickCfg/QuickBar、命令别名及清理入口。
- 改物品/任务/地图数据：核对稳定 ID、位置数组格式、基础和语言覆盖、异步到货后的刷新。
- 改专业路线：分别核对计算层 ProfRouteAuto、专业页、ProfFollow 和 AuctionBridge；材料价格、商人购买价、产物卖店收益是不同含义。
- 已确认诊断入口包括 `/dfdiag`、`/dfspeed`、`/dfgate`、`/dfmem`，专业还有 `/dfprofperf`、`/dfprofrows`、`/dfprofgate`。性能日志包括 openPerf、memProbe/memMarks 等；仅在定位相关问题时启用。
- 自动测试会核对全部 TOC 引用、Libs XML 引用和 Lua 5.1 语法。原文件备份在 `.implementation-backup/20261017-professions/`，不被 TOC 加载。
- 2026-10-17 已完成专业经济功能的代码与离线验证；游戏内 API、UI 和帧时间仍待实机核验，不能将模拟测试表述为游戏内验证。

## 10. 专业经济功能的当前约定

### 客户端数据优先

- 用户 2026-10-17 修正：客户端能读到的值优先；接口缺失、未学专业或尚未返回时，配方材料和产量默认回退已有资料，不能把整页锁为待读取。`ProfEconomy.ResolveRecipe/Normalize` 逐字段合并并记录 `materialSource/outputSource/toolSource/dataSource`；页面、固定路线和自动路线使用同一规则。已有资料也缺失、客户端确认产量不确定时，仍明确标记，不能猜测。
- `ProfEconomy` 优先读取现代 `GetRecipeSchematic`，按能力回落旧 `C_TradeSkillUI` 和全局 TradeSkill/Craft 接口。其他玩家的链接/公会专业界面不能覆盖本角色观测。训练师面板仅用于确认配方可学与技能要求，不再读取费用，不能代替专业书获取所有未学专业配方。
- 2026-10-18 路线显示修正：不完整原理图按字段继续查询旧客户端接口，再回退已有 Wowhead 数据；空值、零数量占位和不匹配的配方 ID 不能覆盖有效资料。已有升级攻略 `rinfo` 提供技能阈值补充，解决附魔起步配方目录 20 与攻略 1 的冲突；实际客户端学习等级仍优先。目录中新配方无需仅因缺图纸物品 ID 而拒绝规划；客户端明确不可用、未确认开放元数据、冷却和自定义排除仍保留。
- 旧商人采购资料和采价入口继续禁用。普通材料的 `GetOffers/GetPrice` 只接受 `ProfMaterialSupply` 中有来源、核验时间和证据哈希的有效不限量报价，并过滤角色阵营与显式 NPC 访问拒绝；根基础价不会在运行时自行生成采购资格。材料输出保持匿名，不展示 NPC 身份或地图。图纸 `GetFormulaOffers` 继续从原 `ProfItems.offers[npc_id]` 获取报价。任务来源和地图定位均不补价；不读取商人窗口、历史商人报价存档或 Auctionator 商人缓存。
- 材料报价由生成器优先采用货架纯金币整组价与同源组数；金额缺失时，仅在纯金币、不限量资格已经确认且组数不冲突时采用客户端基础组价及组数。未知、限量、混合兑换及未确认条件不作为普通材料采购；数值必须是有限非负整数，组数为正整数。图纸仍按原层 `cost_copper`、根 `VendorStackCount`、通货和库存规则独立处理，`maxStock` 不冒充当前现货。
- 拍卖行价格、缓存、数量及导入功能保留。普通材料比较 AH 支出与已证实供货的整组支出，图纸比较 AH 和原明确 NPC 支出；某一层缺价不阻止 AH。完全无价时继续尝试本专业制材，不当作免费；产物卖店收益仍由客户端 API 独立获取。网页材料报价属于带来源时间的参考，不臆算角色声望折扣。
- `RA.StampVendorQuotes/ValidateVendorQuotes` 统一保护路线、冻结执行采购视图、补料及购物清单旧回调。指纹包含原图纸数据与独立材料供货/价格的语义指纹；变化后旧采购视图等待手动重算，历史制作事实保留。纯 AH 候选也须重新比较新的合法供货集合。补料重新捕获当前输入，不采用持久化执行选项中的旧 `snapshot`。
- 固定 HUD 按当前段剩余次数调用同一个 `SummarizeSteps`，保留同物品 NPC/AH 的独立采购行，只导入实际 AH 数量；不再以旧 `ProfLeveling.sold` 标记采购来源。限量/未知库存的 NPC 图纸与可靠 AH 图纸均作为搜索候选，不能只因前者便宜而丢掉完整可执行的 AH 路线。
- 配方目录来自生成的 Wowhead/经典资料，并非客户端扫描的完整清单。未核验记录标记为参考；稳定的现代完整专业目录（包含未学记录、匹配本角色当前专业）可证明该专业中某个目录记录不可用，此时隐藏并禁止自动制作。空列表、接口 nil、旧版仅已学列表不证明不存在；观测按客户端 build 隔离。
- 采矿原始法术效果数量与创建物品目录曾有差异；默认使用创建物品目录数量（铜 1、青铜 2），客户端读取后覆盖，保留原差异来源。已验证的随机产量范围以 `outputMin/outputMax` 保存，整数账本按最小值 `count=outputMin` 计算；旧记录只有随机标记但没有范围时，回退已有资料产量并标记 `outputBasis=reference`。真正缺失或明确冲突的产量仍不猜测。
- `/dfprofapi` 输出当前 build、接口是否存在及实际读取成功/空结果/错误次数，保存于角色经济状态 `apiReport`。Forever 接口声明及实机验证边界见 `tests/FOREVER_API.md`。

### 计算与结果

- 最新成本规则：默认开启回血模式，仅最省钱以材料及必要图纸采购支出减去最终制作余量预计收入为目标，同净支出优先较低采购支出；关闭后恢复采购支出目标。其他自动方案、固定攻略及纯钓鱼保留原选择目标，同时展示预计回血。每个方案从空材料账本开始，不读取或扣除角色背包、银行；仍不计训练师学费、专业升阶学费和工具要求。只复用本方案生成的中间产物与采购余量；父配方立即预留材料，避免嵌套制材重复消耗。采购资金单列，未到账收入不抵扣采购数量或采购支出。
- 1.8.24 图纸层：`E.FindRecipe/FormulaFor/CollectFormulas` 统一查询固定攻略、全部自动方案及制材依赖的图纸。已学配方与训练师直学免购；其他必要图纸按物品 ID 收费一次，`formulaPaid` 进入搜索状态。图纸昂贵时可以改选冲级配方或购买中间产物；逐步成本模式也考虑尚未支付的图纸费用。
- 自动计算拒绝无可靠图纸购买报价的未学配方，包括仅任务来源且无 AH 报价的图纸；已学豁免。固定攻略保留来源与受阻提示。不能将空商人列表、`read=classic/wowhead` 或数字技能要求当作任务来源；`Data_ProfFormulaQuests` 独立保存可追溯任务来源，不参与 NPC 采购定价。
- 1.8.34：`ProfRecovery.Capture` 冻结产物 NPC 卖价（有效零与未加载分开）、交易限制、AH 报价、数量证据及手续费。拍卖每件净价先向下取整到铜；仅当比 NPC 卖价高超过 100 铜，且两天内完整、排除本人的客户端结果至少 40 件时采用。按全部最终剩余制作产物估值，不以 40 件封顶；统一标明“假设全部成交”。无法估值的产物保留路线并提示缺失，不捏造无物品制作的收入。
- 手续费可手动覆盖 0–100%；自动来源优先可靠客户端观察，缺失时读取已安装 Auctionator 的 `Constants.AfterAHCut` 并标参考。Forever 接口声明未提供手续费读取接口，不把押金接口当手续费；手续费未知时仅估 NPC 收入。按首轮全部成交，不预扣未知流拍损失，不计退回押金收入。
- `ProfRecovery.Apply` 按真实制作时序重放采购与制作来源，只有最终未消耗的制作产物可产生收入；无法消费的辅助专业余量与续接种子单独保留。递归成本经实际消耗传入下游，同批供多个配方按数量分摊；图纸费仅一次，整包采购余料保留归属。`productionCost/transferredCost/attributedCostExact/attributedCost/recoveryTotal/netTotal` 为步骤经济账，`cost` 仍是原采购归属。精确分摊后累计处理铜币尾差，两个步骤列表的归属成本均与采购总额相等。
- 补料的合成需求不显示为虚构制作步骤，但以 `consumedDemands` 在经济重放中消费一次；只给超出交付需求的自然余量估值。`demandAttribution/demandNonCraftCost` 分别记录交付成本与直接采购交付的成本，后者不虚构制作归属行。
- 新结果保存 `recoveryRevision=1/recoverySnapshot/purchaseTotal/recoveryTotal/netTotal/saleOutputs`，搜索额外保存 `initialNetTotal/bestNetTotal/netSavings`，不把净支出降低冒充采购额节省。缺失售价或手续费不作完整回血模型最优证明。
- 回血设置、报价、绑定及数量可信度变化仅标记快照过期，手动重算后应用。旧缓存不补盖回血优化标记，历史制作记录保持冻结。`RA.FixedSummary` 为固定攻略页面、购物清单及 HUD 保存同一角色报价快照，固定重算只刷新参考账目，不启动自动配方优化。普通补料数量变更仍可用无缓存的 `SummarizeSteps` 重新汇总。
- `ProfItemPrices.GetFormulaOffers` 只返回新表中的显式 NPC 记录；无有效金币成本时 `priceUsable=false`，不得用配方来源中的旧商人记录补价或补供货。`maxStock` 仅是刷新上限，不能假装当前现货；不读取商人实时库存。图纸来源、任务和已有 NPC 坐标仍可单独显示，不因此取得购买资格。
- 配方页来源改为独立的“图纸.掉落 / 图纸.商人”标签，同图纸双来源并列；行与提示框不再展示资料出处，仍保留缺资料和不可用提示。图纸行情、商人阵营/地区及购买成本在悬停时读取。`GetFormulaDisplayOffers` 单独合并目录与原始 NPC 的显示记录，含特殊通货和缺价来源，不进入金币采购；通货名称/图标优先客户端接口，缺数据时保留 ID 并在下次悬停重试。来源热区随行池清理，原地图点击及商人选择框复用。
- NPC 所属组织独立保存在 `Data_ProfItems.lua` 的 `ns.ProfVendorFactions`，与 `side` 的A/H/N访问限制分开。`ProfItemPrices.GetNPCFaction` 优先客户端阵营名称API，再回退静态三语名；报价携带 `npcFactionID/npcFactionName`，图纸提示优先显示所属名字，缺失则沿用A/H/N或未知。`fc_prof_items.py` / 统一 `fc_update.py` 的 `--vendor-factions-json` 覆盖默认 `_fc/inputs/vendors/npc-factions.json`，同时验证 `faction-sources/` 冻结证据，不改固定19列CSV、价格、库存或坐标。
- 全商人所属管线见 [`scripts/VENDOR_FACTIONS.md`](scripts/VENDOR_FACTIONS.md)：`update_vendor_factions.py` 从商人CSV动态发现全部NPC，`--offline`从随仓库保存的完整原始快照确定性重放，`--collect`刷新过期/缺失证据，`--install-input`只事务安装JSON/审计/快照，生成Lua另走专业流水线。2026-10-21为289名商人、242名ID及三语名、47名未知，0缺payload/冲突/采集错误。旧两NPC日期快照仅作历史。缺`react`不补中立，不由商品声望推所属；WoWDBDefs仅定义结构，70450名称解码不等于具备NPC关联。输入哈希/目标集合/ID冲突失败时保留旧结果，原五CSV和采购条件不变。
- 图纸区同时列 AH/NPC 单价、推荐采购支出、固定不限量/限量刷新/性质未知、所属配方及来源定位；地图复用配方页商人/掉落 NPC 工具，未知坐标明确标记。HUD 与导入也包含所选 AH 图纸，NPC、已学及不可购图纸不导入。图纸不混入材料库存；一次性费用归入首次使用步骤。
- 材料可以购买、自制或混用，按整数批次和购买组数计算；灰色配方可以制材但不涨点。冷却配方排除，尚未确认的转化冷却不当作无冷却。
- 1.8.25 数量约束：`E.Capture` 保存 `auctionSupply[物品ID]={quantity,complete,observedAt,...}`。只接受实际读到的非负整数；无记录为未知，不能当作零。`ahUsed` 与技能、余量、图纸付款一同进入搜索状态，材料、递归制材、不同冲级配方及图纸共用有限拍卖数量；合批补购也不能突破。某配方的瓶颈材料耗尽后改用其他候选，或比较 NPC/自制补齐；绿色配方不足一个期望技能点时保留概率进度，由另一配方继续。图纸采购可选择较贵 NPC 来源，保留稀缺 AH 物品供后续制材。
- 其他自动评分模式保持各自优先级，在存在有限数量观察时按实际整数制作逐次扣减共享采购额度并切换候选。固定攻略保留原步骤，仅在购物清单标明需求超过已读取数量；不能把固定参考当作已经满足货源限制的方案。`E.SummarizeAuctionSupply` 统一材料及图纸的 `availableCount/supplyObserved/supplyComplete`，结果记录未知物品种数及数量模型版本；数量未知不抹去已知价格和可见路线。
- 1.8.27 数量持久化：`AuctionBridge.GetAuctionSupply(id,true)` 从本插件 `DungeonsForeverDB.auctionSupply` v2 返回最近观测，Unix 时间戳、递增修订号、市场和扫描批次跨重载保存；不再五分钟失效，打开拍卖行只清瞬时查询/明细状态。按客户端 Interface 与 Auctionator 的服务器/阵营市场键划分，排除本人拍卖的记录再按角色 GUID 隔离；每个作用域仅保留最近一条。完整市场扫描只另存 ID 集合和完成标记，缺失物品的零数量可跨重载恢复，新单物品记录凭修订号覆盖。
- 当前 Auctionator `Database:SetPrice` 用 `hooksecurefunc` 后置监听，仅接受普通物品 ID 键和有效数量；价格单独保存观测时间，只有价格的更新不改数量及其时间。`ProcessScan` 后置标记异步扫描批次，同批且含本人原始数量匹配时优先客户端过滤结果；安装版每批重叠边界的重复写入仍属于该批次，后续购买报告的新数量可以覆盖。接口缺失保留客户端采集与存档；`SupplyStatus` 和 `/dfauction` 报告兼容状态及最近错误。不修改 Auctionator 文件/数据库，不主动请求搜索。
- 传统搜索逐页汇总，现代接口按存在性读取，仅一口价且排除本人；不完整零记录不覆盖旧观察。不能确认扫描范围及本人拍卖的 `SetPrice` 数量标为 `auctionator-update` 汇总估计，仍参与数量预算但不展示已验证/模型最优结论。全扫读取及存档各按每批最多 150 条分帧，最后才建立缺失零标记；取消 serial 防止旧任务继续发布。单物品超大分组不在观察器重复同步求和，无对应客户端数据时先采用明确标记的不完整估计。
- `GetAuctionSupplyHistory` 只读 Auctionator 历史日最高数量作显示参考，从不进入预算。没有最近观察时保持未知、按价格估算并提示去拍卖师完整扫描；两天以上只显示数据较旧，不删除或禁用。价格和数量分别显示观测时间，页面及 HUD 共用材料/图纸快照；原单位报价模型不承诺全部数量能按最低单价买到。
- 新观察只标记现有路线需手动更新，不因切页重算；初始化/重载的就绪通知不算行情变化。结果数量模型 v2 冻结所有相关候选物品的输入身份，恢复时仅在实际证据变化后标记过期；旧 v1 运行时计时证据清为未知并保留路线。手动重算以新数量替换输入，页面、HUD 与 AH 导入共用所选采购记录。
- 1.8.28 查询关联修正：`AUCTION_HOUSE_SHOW` 不清除同事件中 Auctionator/系统较早监听器刚发起的查询；关闭时重置瞬时查询/明细，持久记录不清除。否则正常结果和完整空查询均可能因 `legacyQuery` 被抹去而读不到数量。数量未知提示列出实际 AH 材料/图纸的前三种缺失名称并去重，不把 NPC 物品或已知零量列入。`/dfauction [物品ID…]` 增加本插件版本、查询监听/活动状态、当前市场记录数、最近接收时间及逐物品结果；不发起额外查询。
- 新发布路线 `vendorQuoteRevision=4`，并记录 `ProfItemsMeta.sources.csv.sha256` 作为报价数据指纹。旧 NPC 报价或相关数据变化要求手动重新计算；原纯 AH 路线仍可查看，新 NPC 候选改变比较结果时标记需更新，不自动搜索。历史和冻结执行记录不被替换。旧数量模型无法从 Auctionator 历史日最高量补出最近数量，更新 Lua 后须 `/reload` 再实际搜索或扫描。
- 2026-10-18 用户缺价规则：没有有效拍卖行或 NPC 报价的材料，必须由目标本专业实际制作；递归展开所有原料，最终必须落到有价采购或本方案已实际制作的本专业产物。无法闭合的材料链使该冲级候选失效，改选其他配方；不生成待报价采购、不把未知价当零。另一专业制材仅对有有效采购报价的材料参与比较；联合升级顺带产生的无价物品保留为余量，不可绕过本专业制作和学习等级检查。`inv/unusable` 区分总余量与可消费库存，合批、状态去重及依赖图遵循同一来源规则。
- 另一主专业默认仅提供当前能制作的材料；`autoSecondaryLeveling` 默认关闭，开启后允许为制材补足技能并计费，最高 300。
- 1.8.23：未学目标开启联合升级时，必须明确选择另一个主专业，不默认沿用角色原有两个主专业。`E.PartnerCandidates/RouteContext/GetRoutePartner/SetRoutePartner` 统一候选、校验和按角色/服务器/目标专业保存的选择；可选已学或未学主专业，不能选目标本身。`secondaryProfession` 写入计算输入，未学目标的材料依赖仅限目标与所选伙伴；已学伙伴使用实际技能，未学伙伴从 1/75 开始模拟，联合升级关闭时仅使用目标专业。未学专业逐专业忽略 `learnedOnly`，已学专业仍受该选项约束，保存的全局开关不变。
- `RA.Get/Compute/Recalculate` 缺选择时返回 `selection_required/secondaryRequired`，不启动搜索；`S.Compute` 也独立防御。改变配对或遇到旧三专业缓存时返回 `recalculate_required/pairingChanged`，清空可执行步骤和采购清单，等待手动重算。缓存签名包含目标已学状态与伙伴，结果保存 `professionPolicy=1/targetUnlearned/secondaryProfession`；取消不匹配的旧协程时同步清除无任务的 searching 缓存，旧任务不得再发布。HUD、旧方案模式和旧购物回调同样检查待选择/待重算及配对身份，不回退固定路线执行。
- `RA.Get/Start` 首次没有结果时调度计算，随后按角色、专业和设置读取内存及 `prof.routeCache[角色-服务器]` 保存的完整快照。切页、重开、真实技能和价格变化不自动重算，普通 `RA.Invalidate` 只清报价缓存并标记旧方案过期。手动 `RA.Recalculate` 替换旧任务，防止旧协程覆盖新结果。持久缓存/路线模型版本 3，旧版本冷启动重算一次；无解结果也保存。设置变化先显示旧方案及提示，重新计算后应用。
- 1.8.22 对旧版没有任何步骤的失败缓存自动修复一次：`emptyResultRevision=2`；旧 `pricePending/referenceRoute/mats[].unpriced` 最省钱结果也重算一次。已有有价路线、明确停止的任务和本版真实无解结果继续保存，不因切页重新计算。
- `RA.Cancel` 可停止；`RA.OnPlanChanged(fn)` 发布 `(slug, result)`，界面和 HUD 共用 `RA.OptionsFor`。旧 `Continue` 仅为兼容保留，界面已移除继续入口，终态任务不能被复活。
- 重算和配对失效会立即释放旧求解协程及输入/搜索状态，排队旧回调只返回结束，不能再发布；终态计算发布后同样解除引用。停止仍保留兼容继续所需的状态，但不再占用后续帧计算。重新计算后的执行计划及 HUD 只在计算终态自动冻结，避免锁住首个临时前段；玩家明确绑定的执行事实仍保持不变。未开启联合升级时，旧专业身份/规则不兼容使用独立提示，不误报搭配专业变化。
- 工程任务首个可行路线与普通升级一样先构建一套共享采购账本，后续搜索仍比较完整制购组合；不会在首次交付前枚举所有采购拆分。预搜索超时保留最远有效前段的真实阻断原因。达到目标与证明最优分开显示，终态搜索信息不能盖住执行前段的实际等级；完整路线的限量图纸/未完整扫描采购仍明确提示。
- v2 结果包含 `steps/executionSteps/actions/dependencyGraph/mats/formulas`、来源与费用、`revision/status/feasible/completeCost/optimal`。`ahTotal + vendorTotal = matTotal + formulasTotal = total`；另有 `formulaAHTotal/formulaVendorTotal/formulaComplete`。仍无学费和工具费用。`formulaRevision=1` 使旧版不计图纸的结果自动更新一次，新结果继续缓存。
- 无法立即完成全目标时保留可执行前段：`partial=true/plannedTo/targetReached=false`，金额和购物清单仅属于前段，后续限制单列。`steps[].recipe` 保存本次规范化配方快照，避免页面/HUD 重读变化中的输入。跳过候选的失败原因按类别压缩，不能淹没路线；图纸过滤不是用户自定义排除。
- 先快速构建可行方案，再比较递归制购组合并搜索。采购成本模式沿用材料价值势函数和已发生成本剪枝；回血模式停用不能证明安全的采购成本剪枝及下界，状态键保留全部影响出售的产物数量。仅制作升级和后续材料必需批次，不因盈利继续生产。预算耗尽保留当前最好方案，不作最优证明。
- 每得到第一个或再推进约 15 点的有效前段即发布；首轮直接采购种子同时递归补齐本专业无价材料，按物品/需求缓存估价并优先找到可执行制作链。之后的制购组合预搜索只占约 250ms CPU，避免耗尽 5 秒却仍显示零状态。循环路径的失败估价不跨路径缓存。
- 1.8.30 保留搜索的真实制作时序，仅合并相邻同配方。发布前向重放与反向用途检查删除零期望收益且产物无人使用的步骤，并裁剪采购、保持 NPC 整包与有限货源约束。保留小数涨点收益，清理后重新验证用途排除。`steps` 仍按配方汇总，`executionSteps` 可出现同配方多个独立 `segmentID`，带 `goalSkill/expectedGain/requiredOutputs/materialMinCrafts/allocations`；两种列表不能共享可变配额表。
- `S.ProcureMany(snapshot,demands,opts)` 共用材料、整包余量及 AH 数量账本，为补料展开递归制作；`Procure` 为单物品兼容入口。只有明确的 `executionInventory` 可作为本路线制作余量输入，普通背包或 `snapshot.inventory` 继续忽略。
- `ProfExecution` 在角色 `prof.execution[角色键]` 下保存逐专业活动计划映射及历史执行记录。`planID` 持久标识计算批次，执行快照冻结后不因搜索 revision、开关 HUD、切页或重载清空；后台新方案只提示。成功施法次数不受预计次数截断，实际产出由制作结果或本地化制造消息关联并去重，未确认产出与最低保证量分别保存。
- 冻结计划的 `searchState` 独立更新后台任务状态、已比较数量与当前候选费用，路线内容及制作记录不被替换；重载后不自动恢复搜索。1.8.36 增加 `searchTermination/searchCpuMs/searchCpuLimitMs`，明确区分 CPU 时限、状态上限及搜索穷尽，结束后不再称“后台当前”。达到节点上限但最后一个状态恰好已处理完时仍可确认穷尽；预算截止不宣称最优。
- 1.8.36 升级工具栏分为页面导航和操作两组。路线、购物、补料、记录、配方排除为互斥页签，用金色下划线表示选中；重算、补料计算、HUD、导入为操作，回血/纯钓鱼用独立开关状态。HUD/导入只在操作行占位，宽度不足逐行换行；排除页单栏且不显示购物导入。配方名称和副行都有明确列宽与截断预算，完整附魔描述保留提示。购物掉落行显示去重地区，缺精确坐标时标“精确坐标未收录”，不因已知地区而伪造 NPC 点位。
- 步骤同时检查实际技能与后续材料数量义务；技能达标但材料不足继续制作，实际多产可满足后续配额且不得重复分配。正常分配的消耗仍算完成生产义务，额外制作占用未来配额则要求补足；按真实制作顺序重放并在本次进度未变化时复用内存结果。HUD 追加需求不自动采购；点击计算补料才生成独立清单和费用，并校验计算期间进度是否变化。补做段插在当前消费者前，连续补料保留此前尚未使用的追加预算，原费用不改写。
- 手动重算归档旧记录，从真实技能及已确认未消耗的本路线中间产物继续；复用量以随身数量为上限，不读取银行或抵扣普通旧材料。旧 v2 路线缺执行契约时保留参考并要求手动重算；历史实际产量不能从技能等级反推。固定/旧评分路线的纯升级步骤可通过执行适配器记录。
- 普通 IdleJobs 每片约 2ms，累计 CPU 预算 5 秒；达到预算自动结束本轮并保留最好方案。`expanded/initialTotal/improvements/savings/searchComplete/budgetLimited` 提供真实比较状态数和节省金额，不能把没有变化当作已经更省。
- 搜索穷尽且资料完整才显示模型内最优；预算截止、循环处理或联合升级分组搜索不作最优证明。`optimal` 保留价格/期望与观察上限模型的内部证明，界面还要求 `supplyComplete~=false`，数量未知或扫描不完整时不展示最优结论。真实客户端资料覆盖并非穷尽证明，默认显示当前找到的最低材料支出。协作式预算不能抢占单次 API/GC，不能承诺每一帧严格小于 2ms。

### 采矿、自定义与执行

- 1.8.26：烹饪升级页新增独立“纯钓鱼”模式，`prof.cookingRoute=fishing/standard` 保留其他专业的全局自动模式和评分方案。`ProfFishing.Compute` 通过 `ProfRouteAuto` 的 `scheme=fishing` 发布 v2 快照，使用同一角色缓存、目标、排除规则、图纸采购及 HUD；与普通最省钱路线的缓存不会互相回退。没有 AH 插件也能预览，不要求选择联合升级的主专业；未学烹饪忽略仅已学过滤，已学烹饪仍遵守。
- `Data_ProfFishingRoutes` 在语言覆盖之后加载：1–225 采用用户指定 Forever 指南的四个鱼配方（7751/7753/7755/20916），制作次数按当前起点、目标和共享涨点模型计算，参考用量不直接当作所有目标的数量。225–300 默认斑点黄尾鱼（18238），现有 Forever 阈值为 225/265/285/305；无季节或时段限制，指南对应海岸可钓率约 40%，鱼类门槛 205/300。失效/变灰时才按低门槛、高钓获率和涨点率选择其他合规鱼配方。时间/季节受限鱼不自动选取，白鳞鲑鱼门槛冲突显式提示并保守使用 330/425。
- 纯钓鱼模式只接受已核验可钓鱼类；非鱼配料只使用独立不限量材料供货报价，不把普通根价当作 NPC 资格。客户端实际配方材料改为肉类或未知来源时不能沿用旧鱼材料冒充。鱼类放在 `fishMaterials`，来源为 `fishing`，不进入采购金额、AH 数量账本及导入。它们是待钓需求，不代表已有材料；主优化器没有新增任意免费采集来源。`steps[].fishing/fishingAreas` 显示每配方鱼类及内陆/海岸区域、最低钓鱼/不脱钩技能，区域点击打开地图，没坐标时不造航点。
- 配料读取 `Data_ProfMaterialSupply` 的有效报价，食谱沿用独立 NPC/AH 图纸报价，钓鱼文件不内置商人货架。必要图纸按物品计费一次，已学免购，缺价任务或 NPC 图纸不能免费使用。鱼的时间成本不折算金币。225 之后需先解锁大师级烹饪，蚌肉大餐的非鱼任务材料单独提示，不属于这条制作路线的鱼材料或采购成本。
- 钓鱼升级路线改用同一指南的优先区域：出生地内陆水域、主城、尘泥沼泽内陆/海岸、塔纳利斯热砂港，保留原完整区域目录供浏览。不再声称每次下竿必涨点，也不要求达到阶段点就换区；显示实际技能定位与有效技能门槛，可留低级水域升级。位置与钓获概率是 Classic 指南参考，不冒充 Forever 实测。地理参考见 `tests/data/fishing-routes-audit.md`，新采购通路规则见 `tests/data/vendor-offers-audit.md`，两者不互相补出供货关系。

- 采矿配方页有 15 条熔炼目录记录；采集页保留。熔炼参考路线包含 140–155、185–300 实地采矿阶段，奥金属于炼金，不能列作采矿熔炼。
- 自动采矿只在配方本身没有涨点覆盖的区间插入采矿检查点；缺价、未加载或被排除的配方不会被偷偷替换成零价采矿。检查点不预支矿石产物，不计矿工锄、升阶或其他工具费用。
- 排除键为 `专业:法术ID`，按角色及目标专业保存：`ban` 禁止一切制作但可购买产物；`level` 禁止主动冲级但允许按下游材料需求制作，并计入预计涨点。是否仅用已学配方由独立设置控制。`autoBuyLimitedFormulas` 默认关闭，仅禁用明确限量 NPC 的图纸采购来源；有可用 AH 报价且已读数量非零（或数量未知）仍可入选，已学/明确训练师/不限量商人不受影响。自动、递归制材、其他评分、纯钓鱼和固定汇总共用该政策；固定攻略保留参考步骤并标未取得图纸，不伪造购买。政策快照及设置变化要求手动重算，取消旧任务，保留制作事实与历史。
- 路线右键排除、管理排除、单项/全部恢复均先改草稿，重新计算后应用。无解或客户端数据未齐时不回退到违反限制的固定路线。
- 页面有步骤时优先显示步骤；拒绝候选的诊断不能冒充所选路线的错误，后续真正阻断由 `blockingDiagnostics` 单列。无初始完整方案时不显示“节省 0”统计。
- 2026-10-18：同一专业/法术的升级与制材数量合成一个真实制作批次，按材料就绪和学习等级安排步骤，重新模拟整批的涨点。允许超过单纯冲级所需数量以供后续消耗；必要时购买中间材料修复合批依赖，费用计入。合批后未达目标的候选不作为完整路线发布；依赖修复或合批冲突不宣称模型最优。
- 页面五列为“步骤、等级范围、配方、制作次数、成本”，按执行序号排列。`role=level/material/both` 根据真实技能收益及后续是否消耗产物生成“升级 / 中间产物 / 升级&中间产物”。`steps` 和 `executionSteps` 共享真实合批顺序，不能只压缩显示而保留多次执行。
- 采购记录 `owner` 指向直接消耗该材料的配方，步骤成本为其新增采购合计；中间产物费用在制作该材料的步骤列一次，后续步骤不重复计费。所有步骤成本之和与采购总额一致。
- 已选择的合格 NPC 材料保留购买来源标签，不导入 Auctionator，也不展示具体材料商人。材料采购比较 AH 和有证据的整组买入；两者都无法报价时，自动路线必须用本专业制作补齐，否则舍弃相关候选，固定攻略明确显示缺价。页面、HUD 和导入使用同一采购来源字段；图纸商人明细与材料计价分别处理。
- HUD 按成功制作次数跟踪批次，采矿检查点等待实际技能；购物清单使用方案选定的完整采购数量，不扣已有物品。只有玩家点击实际制作按钮前检查背包材料，不参与路线成本。
- Auctionator 通过 OptionalDeps 优先加载；`AuctionBridge.Status` 区分缺失、停用、初始化中、就绪。API 函数存在但价格库未初始化时禁止查询/负缓存；延迟登录回调及公开数据库更新回调使价格和路线失效。就绪但缺报价不能显示未安装。

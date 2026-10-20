# DungeonsForever 架构与修改导航

核对日期：2026-10-20。依据当前下载仓库合并后的源码；当前 TOC 版本为 1.8.31。合并来源及取舍见 `MERGE_NOTES.md`。
本文记录实际实现，后续功能变更后应重新核对相应部分。

## 1. 项目边界

- 原生 WoW Lua 插件，单窗口手册，固定 HUI 外观；无前端框架、服务端或独立构建流程。
- 当前目录是内层 Git 仓库，分支 `codex/merge-installed-1.8.28`；以下载版 1.8.20 为基础迁入安装版 1.8.28。专业数据工具在 `df-prof-pipeline-v1.0/`，其脚本和样例生成目录独立于正式插件数据。`tests/` 包含 Lua 5.1 模拟测试与基准脚本，见 `tests/README.md`。
- 所有源码、脚本、测试及数据修改只允许在 `C:\Users\yewei\Downloads\DungeonsForever\DungeonsForever`。游戏安装目录中的插件副本只能只读核对，禁止编辑、生成、部署或清理；当前会话的默认工作目录不能视为写入授权。
- 顶层目录：`Core/` 业务与界面，`Core/Data/` 数据，`Locales/` 文案，`Libs/` 内嵌库，`Media/` 图片与地图等资源。
- 当前共 29 个 Core 顶层 Lua 文件；数据文件共 121 个：基础 49 个、enUS 36 个、zhTW 36 个。
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
  → Data_ProfVendorOffers / Data_ProfFormulaSources / Data_ProfMining / Data_ProfFishingRoutes（语言覆盖之后的独立扩展）
  → LootFilter.lua → DungeonUI.lua
  → PvPUI / FactionUI / MapUI / LootFilterUI / RaidUI
  → ProfEconomy → ProfFishing → ProfRouteSolver → ProfRouteAuto → ProfExecution
  → ProfessionUI → AuctionatorBridge → ProfFollow → VendorPriceDB
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
| 整数采购及路线搜索 | ProfRouteSolver | 共享库存账本、材料制购组合、另一专业制材/联合升级、分帧搜索 |
| 自动专业升级路线门面 | ProfRouteAuto | 旧方案兼容；最省钱异步快照、缓存、发布通知、停止/继续 |
| 制作执行及持久记录 | ProfExecution | 冻结执行计划、分段技能与材料义务、真实次数/产出、重算余量、按需补料 |
| 专业跟随 HUD、购物清单 | ProfFollow | ProfModule、ProfRouteAuto、材料背包状态；AuctionBridge 导出清单 |
| NPC 供货资料查询 | VendorPriceDB | 只读 NPC 货架、购买组数与访问条件；购买价格数据已移除，缺价保持未知，待重新设计 |
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
- 多份数据曾由 `_temp` 脚本生成。专业 `fc_gen.py` 等工具已完整保存在 `df-prof-pipeline-v1.0/_temp/`，工具内 `Core/Data/` 为独立样例输出，不能直接覆盖正式资料。装备等其他生成脚本仍未提供。更新前核对输出位置、三语覆盖和手工扩展；此次合并未运行生成。
- `scripts/export_buyprice/export-item-buy-prices.ps1` 在 Windows PowerShell 5.1 下调用本机 wow.tools.local，下载并验证匹配当前 Forever build 的最新 Hotfix，串行导出三语 ItemSparse，并只读取一次 Item。输出 `output/item-buy-prices.csv`（enUS/zhTW/zhCN 名称、原始基础组价、组数、零价/缺价和版本）及 `output/item.csv`（Item 全字段，供 `scripts/gen_vendors.py` 按 ClassID/SubclassID 筛配方）。导出器不生成或导入 Lua；连同图纸学习条件 CSV，三份输出全部验证后共同发布，失败回滚旧输出。旧试验导入脚本、缺失生成文件的 TOC 引用及三份无消费者的 `Data_VendorPrices.lua` 已移除。内置 NPC 采购资料仍由 `Data_ProfVendorOffers` 和 `Data_ProfFormulaSources` 提供。

- 专业学习专精数据独立生成：价格导出器另输出 `recipe-item-specializations.csv`，仅把图纸物品的 `RequiredAbility` 沿明确教学关系关联至配方法术。`_temp/fc_prof_specializations.py` 合并图纸与 Wowhead Forever 的训练师证据，写入 `_temp/_fc/data/trainer-recipe-specializations.csv` 和管线包 `Core/Data/Data_ProfSpecializations.lua`；`fc_update.py` 已接入该步骤。`ns.ProfSpecializations[spellID]` 保留独立学习途径与来源，缺证据为 `pending`，不同途径不自动合为统一限制。目标客户端 build 与网页来源版本分开记录；跨来源 patch/build 的旧证据保留但不作为目标版本的已确认要求。网页抓取采用缓存、串行间隔、跨进程互斥和持久冷却，在线失败不发布两份最终产物。这份 Lua 目前仅为管线数据，没有接入正式插件 TOC、UI 或求解器。
- 专精的重复更新入口为 `_temp/fc_refresh_specializations.py`，也可由 `fc_update.py --specializations-only` 调用。默认检查，`--apply` 才发布；在线模式通过导出器可选 `-LearningSnapshotPath` 保留九张 DB2 表和 Build／Hotfix／内容哈希，按内容归档并记录成功快照指针。冻结输入后生成三个客户端 CSV、训练师 CSV、Lua 及三个审计文件，校验通过才同批发布，失败补偿回滚；无变化的正式文件不改写。离线模式复核已发布快照哈希。审计动态比较前后未关联集合，不固定物品数；书籍子类不直接排除，wuxianwow 目录匹配不充当教学或专精证据。网页和外部目录默认复用七天有效缓存，检查或失败运行可保留缓存与日志，但不替换正式产物。

## 7. 存档

唯一 TOC SavedVariables 是 `DungeonsForeverDB`，没有单独的 SavedVariablesPerCharacter。`ns.DB()` 返回根表并保证 ui 存在。

主要分区：`ui`（窗口/缩放/小地图/quick）、`libHUI`、`dungeon`、`raid`、`prof`、`explore`、`bis`、`tier`、`factions`、`gear`、`wishlist`、`vendorPrices`；诊断信息也存根表。

- 不能把所有状态都当角色级：大量 UI 偏好与方案直接存在共享表中。
- 副本任务的 `dungeon.dungeonQSide` 显式保存 `all/A/H`；旧缺失值按角色阵营和当前任务计数选择默认。`dungeon.mapQuestPins` 缺失时默认关闭，已保存的 true/false 保持原值。列表与总览共用阵营筛选，任务控制栏为两排以容纳五个按钮及开关。
- 装备过滤显式分角色：`ui.lootFilter[服务器][角色]`，有版本校验和默认方案。
- 专业跟随状态：`prof.follow[角色名-服务器名]`；部分购物清单偏好仍为共享设置。
- 专业经济规则及客户端观测：`prof.economy[角色名-服务器名]`，包含按目标专业保存的排除规则、按客户端 build 隔离的配方与可用目录观测。1.8.18 不再读取学费、工具或初始库存；排除草稿在内存中，点击重算才提交。
- 旧根表 `profVendorOffers`、`vendorPrices` 的历史商人报价不再读取或写入，也不再创建；无需清除整个角色存档。`VendorPriceDB` 不订阅商人窗口事件，不读取 Auctionator 的商人价格缓存；AH 行情与数量观测仍按既有规则保存。
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
- 用户 2026-10-20 最新要求：删除旧 NPC 购买价格，所有物品的购买价格方法由用户重新设计。`Data_ProfVendorOffers`、`Data_ProfFormulaSources` 和 `Data_ProfFishingRoutes` 的货架仅保存 NPC/物品/组数/库存性质/位置/来源，无购买金额、报价认证或估价字段；任务来源及钓鱼资料保留。`GetOffers/GetPrice` 在当前真实数据上分别返回空表/nil，图纸接口仍返回无价来源元数据。没有玩家商人采价、旧价格存档、Auctionator 商人缓存或 CSV 自动导入补齐。缺价提示“NPC购买价格尚未配置”，不当作零价。
- 拍卖行价格、价格缓存、数量及导入功能完整保留；产物卖给 NPC 的收益仍通过客户端 API 获取。通用采购/整数搜索接口可用人工报价做离线验证，但当前未接入新的 NPC 购买价格来源。供货的阵营、等级、任务、声望、专业及访问条件仍过滤；召唤 Bot 需要明确可访问状态。旧 NPC 报价路线需手动重算，纯 AH 路线与制作执行记录继续保留。
- 配方目录来自生成的 Wowhead/经典资料，并非客户端扫描的完整清单。未核验记录标记为参考；稳定的现代完整专业目录（包含未学记录、匹配本角色当前专业）可证明该专业中某个目录记录不可用，此时隐藏并禁止自动制作。空列表、接口 nil、旧版仅已学列表不证明不存在；观测按客户端 build 隔离。
- 采矿原始法术效果数量与创建物品目录曾有差异；默认使用创建物品目录数量（铜 1、青铜 2），客户端读取后覆盖，保留原差异来源。已验证的随机产量范围以 `outputMin/outputMax` 保存，整数账本按最小值 `count=outputMin` 计算；旧记录只有随机标记但没有范围时，回退已有资料产量并标记 `outputBasis=reference`。真正缺失或明确冲突的产量仍不猜测。
- `/dfprofapi` 输出当前 build、接口是否存在及实际读取成功/空结果/错误次数，保存于角色经济状态 `apiReport`。Forever 接口声明及实机验证边界见 `tests/FOREVER_API.md`。

### 计算与结果

- 最新成本规则：材料和必要图纸采购支出进入目标函数。每个方案从空材料账本开始，不读取或扣除角色背包、银行；仍不计训练师学费、专业升阶学费和工具要求。只复用本方案生成的中间产物与采购余量；父配方立即预留材料，避免嵌套制材重复消耗。剩余产物收入单列，不抵扣采购支出。
- 1.8.24 图纸层：`E.FindRecipe/FormulaFor/CollectFormulas` 统一查询固定攻略、全部自动方案及制材依赖的图纸。已学配方与训练师直学免购；其他必要图纸按物品 ID 收费一次，`formulaPaid` 进入搜索状态。图纸昂贵时可以改选冲级配方或购买中间产物；逐步成本模式也考虑尚未支付的图纸费用。
- 自动计算拒绝无可靠图纸购买报价的未学配方，包括仅任务来源且无 AH 报价的图纸；已学豁免。固定攻略保留来源与受阻提示。不能将空商人列表、`read=classic/wowhead` 或数字技能要求当作任务来源；`Data_ProfFormulaSources` 保存可追溯的任务及 NPC 来源，无价格。
- `VendorPriceDB.GetFormulaOffers` 保留固定/限量图纸的来源与购买条件，即使无价格也不能丢失 NPC 定位；当前所有内置图纸均无 NPC 报价，不会形成免费采购。`maxStock` 仅是刷新上限，不能假装当前现货；不读取商人实时库存。通用接口的定价能力留待新的购买价格设计接入。
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
- 新发布路线 `vendorQuoteRevision=3`；包含旧 NPC 采购金额的缓存要求手动重新计算，不再将已删除价格发布为当前报价。历史执行记录保留，纯 AH 路线仍可恢复，不自动搜索。旧数量模型无法从 Auctionator 历史日最高量补出最近数量，更新 Lua 后须 `/reload` 再实际搜索或扫描。
- 2026-10-18 用户缺价规则：没有有效拍卖行或 NPC 报价的材料，必须由目标本专业实际制作；递归展开所有原料，最终必须落到有价采购或本方案已实际制作的本专业产物。无法闭合的材料链使该冲级候选失效，改选其他配方；不生成待报价采购、不把未知价当零。另一专业制材仅对有有效采购报价的材料参与比较；联合升级顺带产生的无价物品保留为余量，不可绕过本专业制作和学习等级检查。`inv/unusable` 区分总余量与可消费库存，合批、状态去重及依赖图遵循同一来源规则。
- 另一主专业默认仅提供当前能制作的材料；`autoSecondaryLeveling` 默认关闭，开启后允许为制材补足技能并计费，最高 300。
- 1.8.23：未学目标开启联合升级时，必须明确选择另一个主专业，不默认沿用角色原有两个主专业。`E.PartnerCandidates/RouteContext/GetRoutePartner/SetRoutePartner` 统一候选、校验和按角色/服务器/目标专业保存的选择；可选已学或未学主专业，不能选目标本身。`secondaryProfession` 写入计算输入，未学目标的材料依赖仅限目标与所选伙伴；已学伙伴使用实际技能，未学伙伴从 1/75 开始模拟，联合升级关闭时仅使用目标专业。未学专业逐专业忽略 `learnedOnly`，已学专业仍受该选项约束，保存的全局开关不变。
- `RA.Get/Compute/Recalculate` 缺选择时返回 `selection_required/secondaryRequired`，不启动搜索；`S.Compute` 也独立防御。改变配对或遇到旧三专业缓存时返回 `recalculate_required/pairingChanged`，清空可执行步骤和采购清单，等待手动重算。缓存签名包含目标已学状态与伙伴，结果保存 `professionPolicy=1/targetUnlearned/secondaryProfession`；取消不匹配的旧协程时同步清除无任务的 searching 缓存，旧任务不得再发布。HUD、旧方案模式和旧购物回调同样检查待选择/待重算及配对身份，不回退固定路线执行。
- `RA.Get/Start` 首次没有结果时调度计算，随后按角色、专业和设置读取内存及 `prof.routeCache[角色-服务器]` 保存的完整快照。切页、重开、真实技能和价格变化不自动重算，普通 `RA.Invalidate` 只清报价缓存并标记旧方案过期。手动 `RA.Recalculate` 替换旧任务，防止旧协程覆盖新结果。持久缓存/路线模型版本 3，旧版本冷启动重算一次；无解结果也保存。设置变化先显示旧方案及提示，重新计算后应用。
- 1.8.22 对旧版没有任何步骤的失败缓存自动修复一次：`emptyResultRevision=2`；旧 `pricePending/referenceRoute/mats[].unpriced` 最省钱结果也重算一次。已有有价路线、明确停止的任务和本版真实无解结果继续保存，不因切页重新计算。
- `RA.Cancel` 可停止；`RA.OnPlanChanged(fn)` 发布 `(slug, result)`，界面和 HUD 共用 `RA.OptionsFor`。旧 `Continue` 仅为兼容保留，界面已移除继续入口，终态任务不能被复活。
- v2 结果包含 `steps/executionSteps/actions/dependencyGraph/mats/formulas`、来源与费用、`revision/status/feasible/completeCost/optimal`。`ahTotal + vendorTotal = matTotal + formulasTotal = total`；另有 `formulaAHTotal/formulaVendorTotal/formulaComplete`。仍无学费和工具费用。`formulaRevision=1` 使旧版不计图纸的结果自动更新一次，新结果继续缓存。
- 无法立即完成全目标时保留可执行前段：`partial=true/plannedTo/targetReached=false`，金额和购物清单仅属于前段，后续限制单列。`steps[].recipe` 保存本次规范化配方快照，避免页面/HUD 重读变化中的输入。跳过候选的失败原因按类别压缩，不能淹没路线；图纸过滤不是用户自定义排除。
- 先快速构建可行方案，再比较递归制购组合并执行 A* 搜索。材料价值势函数提供保守剩余费用下界，仅在完整状态应用；材料预留过程只按已发生费用剪枝。状态去重忽略不会再消耗的成品数量，保留可复用材料、技能与概率余量；同价优先较少配方切换。
- 每得到第一个或再推进约 15 点的有效前段即发布；首轮直接采购种子同时递归补齐本专业无价材料，按物品/需求缓存估价并优先找到可执行制作链。之后的制购组合预搜索只占约 250ms CPU，避免耗尽 5 秒却仍显示零状态。循环路径的失败估价不跨路径缓存。
- 1.8.30 保留搜索的真实制作时序，仅合并相邻同配方。发布前向重放与反向用途检查删除零期望收益且产物无人使用的步骤，并裁剪采购、保持 NPC 整包与有限货源约束。保留小数涨点收益，清理后重新验证用途排除。`steps` 仍按配方汇总，`executionSteps` 可出现同配方多个独立 `segmentID`，带 `goalSkill/expectedGain/requiredOutputs/materialMinCrafts/allocations`；两种列表不能共享可变配额表。
- `S.ProcureMany(snapshot,demands,opts)` 共用材料、整包余量及 AH 数量账本，为补料展开递归制作；`Procure` 为单物品兼容入口。只有明确的 `executionInventory` 可作为本路线制作余量输入，普通背包或 `snapshot.inventory` 继续忽略。
- `ProfExecution` 在角色 `prof.execution[角色键]` 下保存逐专业活动计划映射及历史执行记录。`planID` 持久标识计算批次，执行快照冻结后不因搜索 revision、开关 HUD、切页或重载清空；后台新方案只提示。成功施法次数不受预计次数截断，实际产出由制作结果或本地化制造消息关联并去重，未确认产出与最低保证量分别保存。
- 1.8.31 将冻结计划的 `searchState` 独立更新为后台任务的状态、已比较数量与当前候选费用；页面状态、费用说明和停止按钮共用它，路线内容及制作记录不被替换。重载后没有活动任务时不得把旧 `searching` 当作仍在优化，也不因打开已保存执行计划自动启动搜索。升级工具栏先预留可见 HUD/导入入口，再将动作按钮换行；列表位置包含全部工具行。
- 步骤同时检查实际技能与后续材料数量义务；技能达标但材料不足继续制作，实际多产可满足后续配额且不得重复分配。正常分配的消耗仍算完成生产义务，额外制作占用未来配额则要求补足；按真实制作顺序重放并在本次进度未变化时复用内存结果。HUD 追加需求不自动采购；点击计算补料才生成独立清单和费用，并校验计算期间进度是否变化。补做段插在当前消费者前，连续补料保留此前尚未使用的追加预算，原费用不改写。
- 手动重算归档旧记录，从真实技能及已确认未消耗的本路线中间产物继续；复用量以随身数量为上限，不读取银行或抵扣普通旧材料。旧 v2 路线缺执行契约时保留参考并要求手动重算；历史实际产量不能从技能等级反推。固定/旧评分路线的纯升级步骤可通过执行适配器记录。
- 普通 IdleJobs 每片约 2ms，累计 CPU 预算 5 秒；达到预算自动结束本轮并保留最好方案。`expanded/initialTotal/improvements/savings/searchComplete/budgetLimited` 提供真实比较状态数和节省金额，不能把没有变化当作已经更省。
- 搜索穷尽且资料完整才显示模型内最优；预算截止、循环处理或联合升级分组搜索不作最优证明。`optimal` 保留价格/期望与观察上限模型的内部证明，界面还要求 `supplyComplete~=false`，数量未知或扫描不完整时不展示最优结论。真实客户端资料覆盖并非穷尽证明，默认显示当前找到的最低材料支出。协作式预算不能抢占单次 API/GC，不能承诺每一帧严格小于 2ms。

### 采矿、自定义与执行

- 1.8.26：烹饪升级页新增独立“纯钓鱼”模式，`prof.cookingRoute=fishing/standard` 保留其他专业的全局自动模式和评分方案。`ProfFishing.Compute` 通过 `ProfRouteAuto` 的 `scheme=fishing` 发布 v2 快照，使用同一角色缓存、目标、排除规则、图纸采购及 HUD；与普通最省钱路线的缓存不会互相回退。没有 AH 插件也能预览，不要求选择联合升级的主专业；未学烹饪忽略仅已学过滤，已学烹饪仍遵守。
- `Data_ProfFishingRoutes` 在语言覆盖之后加载：1–225 采用用户指定 Forever 指南的四个鱼配方（7751/7753/7755/20916），制作次数按当前起点、目标和共享涨点模型计算，参考用量不直接当作所有目标的数量。225–300 默认斑点黄尾鱼（18238），现有 Forever 阈值为 225/265/285/305；无季节或时段限制，指南对应海岸可钓率约 40%，鱼类门槛 205/300。失效/变灰时才按低门槛、高钓获率和涨点率选择其他合规鱼配方。时间/季节受限鱼不自动选取，白鳞鲑鱼门槛冲突显式提示并保守使用 330/425。
- 纯钓鱼模式只接受已核验可钓鱼类和有效不限量、纯金币 NPC 材料；客户端实际配方材料改为肉类或未知来源时不能沿用旧鱼材料冒充。鱼类放在 `fishMaterials`，来源为 `fishing`，不进入采购金额、AH 数量账本及导入。它们是待钓需求，不代表已有材料；主优化器没有新增任意免费采集来源。`steps[].fishing/fishingAreas` 显示每配方鱼类及内陆/海岸区域、最低钓鱼/不脱钩技能，区域点击打开地图，没坐标时不造航点。
- NPC 配料的购买价当前未配置；必要图纸有有效 AH 报价时仍按物品计费一次，已学免购，缺价任务或 NPC 图纸不能当免费使用。常用鱼食谱的货架只保存 `ProfFormulaOffers` 来源/阵营/库存性质/位置，不含购买价格。鱼的时间成本不折算金币。225 之后需先解锁大师级烹饪，蚌肉大餐的非鱼任务材料单独提示，不属于这条制作路线的鱼材料或采购成本。
- 钓鱼升级路线改用同一指南的优先区域：出生地内陆水域、主城、尘泥沼泽内陆/海岸、塔纳利斯热砂港，保留原完整区域目录供浏览。不再声称每次下竿必涨点，也不要求达到阶段点就换区；显示实际技能定位与有效技能门槛，可留低级水域升级。位置与钓获概率是 Classic 指南参考，不冒充 Forever 实测。依据及 NPC 逐项报价见 `tests/data/fishing-routes-audit.md`。

- 采矿配方页有 15 条熔炼目录记录；采集页保留。熔炼参考路线包含 140–155、185–300 实地采矿阶段，奥金属于炼金，不能列作采矿熔炼。
- 自动采矿只在配方本身没有涨点覆盖的区间插入采矿检查点；缺价、未加载或被排除的配方不会被偷偷替换成零价采矿。检查点不预支矿石产物，不计矿工锄、升阶或其他工具费用。
- 排除键为 `专业:法术ID`，按角色及目标专业保存：`ban` 禁止一切制作但可购买产物；`level` 禁止主动冲级但允许按下游材料需求制作，并计入预计涨点。已删除需图纸配方的额外过滤设置；是否仅用已学配方仍由独立设置控制。
- 路线右键排除、管理排除、单项/全部恢复均先改草稿，重新计算后应用。无解或客户端数据未齐时不回退到违反限制的固定路线。
- 页面有步骤时优先显示步骤；拒绝候选的诊断不能冒充所选路线的错误，后续真正阻断由 `blockingDiagnostics` 单列。无初始完整方案时不显示“节省 0”统计。
- 2026-10-18：同一专业/法术的升级与制材数量合成一个真实制作批次，按材料就绪和学习等级安排步骤，重新模拟整批的涨点。允许超过单纯冲级所需数量以供后续消耗；必要时购买中间材料修复合批依赖，费用计入。合批后未达目标的候选不作为完整路线发布；依赖修复或合批冲突不宣称模型最优。
- 页面五列为“步骤、等级范围、配方、制作次数、成本”，按执行序号排列。`role=level/material/both` 根据真实技能收益及后续是否消耗产物生成“升级 / 中间产物 / 升级&中间产物”。`steps` 和 `executionSteps` 共享真实合批顺序，不能只压缩显示而保留多次执行。
- 采购记录 `owner` 指向直接消耗该材料的配方，步骤成本为其新增采购合计；中间产物费用在制作该材料的步骤列一次，后续步骤不重复计费。所有步骤成本之和与采购总额一致。
- 已确认 NPC 直售的材料仍保留来源标签，不导入 Auctionator；当前 NPC 购买价格全部未知，不用旧参考价或拍卖价冒充 NPC 买价。自动路线必须用本专业制作补齐无法报价的材料，否则舍弃相关候选；固定攻略明确显示缺价。页面、HUD 和导入使用同一来源字段，购买价格的新方法由用户另行设计。
- HUD 按成功制作次数跟踪批次，采矿检查点等待实际技能；购物清单使用方案选定的完整采购数量，不扣已有物品。只有玩家点击实际制作按钮前检查背包材料，不参与路线成本。
- Auctionator 通过 OptionalDeps 优先加载；`AuctionBridge.Status` 区分缺失、停用、初始化中、就绪。API 函数存在但价格库未初始化时禁止查询/负缓存；延迟登录回调及公开数据库更新回调使价格和路线失效。就绪但缺报价不能显示未安装。

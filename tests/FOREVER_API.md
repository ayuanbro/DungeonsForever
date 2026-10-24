# Forever API 核对与复测

2026-10-19，修复版本 1.8.28。以下区分源码接口声明、离线模拟和当前游戏中的实际返回，不能互相代替。

2026-10-20 最新更新：NPC 采购只使用 schema 2 的 `Data_ProfItems.lua`，旧 `Data_ProfVendorOffers.lua`、`Data_ProfFormulaSources.lua` 及钓鱼旧货架已彻底删除，不再读取旧条件、商人事件、历史买价或 Auctionator 商人缓存。任务来源独立迁入 `Data_ProfFormulaQuests.lua`，坐标继续独立显示；两者均不建立供货或购买价格。源码、脚本、数据和测试仅在 `C:\Users\yewei\Downloads\DungeonsForever\DungeonsForever` Git checkout 修改，游戏安装目录只读，不部署。专业配方 API、AH 行情与数量、卖店收益接口保留。本轮二次复审后 587 项 Lua 5.1 离线测试通过，实际游戏尚未验证。

| 范围 | 已核对证据 | 使用方式与边界 |
|---|---|---|
| `C_TradeSkillUI.GetRecipeSchematic`、`GetRecipeOutputItemData`、`GetRecipeRequirements` | [暴雪 UI 源码的 forever 分支接口声明](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/TradeSkillUIDocumentation.lua)；[Forever 配方表单调用](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_ProfessionsTemplates/Blizzard_ProfessionsRecipeSchematicForm.lua) | 现代接口优先。声明存在不保证任意未学专业或未打开面板时都有数据。 |
| 目录、已学状态及旧 TradeSkill/Craft API | 运行时按函数存在性与实际返回判断 | 只有当前专业完整、稳定且含未学记录的目录才证明配方不存在。旧列表或空值不证明不存在。 |
| 专精能力 | [Forever SpellBook 接口声明](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/SpellBookDocumentation.lua)；`C_SpellBook.IsSpellKnown` 优先，兼容 `IsSpellKnown`、`IsPlayerSpell`、`C_Spell.IsSpellKnown` | 成功 false 是未学，缺失/异常是未知；未登录时不采信 false。历史任务完成不能证明当前仍有专精；已学配方也不能反推整个分支。 |
| 工程入门任务 | [Questie Forever 固定提交](https://github.com/Questie/QuestieDB/blob/af56aeef176b2b7534be683907c276c52beabb6d/data/Forever/foreverQuestDB.lua#L1984-L1989) | 地精 3639 / NPC 8126；侏儒联盟 3641 / NPC 7944、部落 3643 / NPC 7406。角色 30、工程 200；前置接取/对话仅提示，不虚构费用。客户端实际能力与任务进度优先，任务历史不直接解锁。 |
| 任务进度 | [Forever QuestLog 接口声明](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/QuestLogDocumentation.lua)；`IsOnQuest`、`ReadyForTurnIn`、`IsQuestFlaggedCompleted`、`IsQuestDisabledForSession` | 存在且成功返回布尔值才采信，缺失/异常保留未知。已接取和可交仅用于辅助提示；当前明确不可用则阻断。仍以实际专精能力确认节点完成，不由任务进度生成能力。 |
| 训练师服务 | 运行时安全检查和服务身份读取 | 对话只确认可学习配方及技能要求，不读取学费，也不会加载未学专业的全部原理图。 |
| NPC 采购数据 | 本地三表合并为 19 列 `DataProfItems.csv`，同一 CSV 内容生成 schema 2 的 `Data_ProfItems.lua` | 只使用显式物品/NPC 记录的有限非负整数 `cost_copper` 与正整数 `VendorStackCount`，按整组计费；任一 `currency_kind/currency_id/currency_amount` 非空（包括 `0`）均拒绝金币采购，不从 `cost_text` 推价。`stock=-1` 用于不限量材料，正数限量仅作为图纸刷新上限，零库存不可购；无 NPC 根成本不建立供货。数据检查不证明游戏内可买到。 |
| Auctionator | 本机安装版 v341，TOC 包含 Interface 16001/camelot；`Source/Initialize/Main.lua`、`Source/Variables/Main.lua`、`Source/API/v1` | 公开 API 的第一个参数是调用者 ID。价格数据库于 PLAYER_LOGIN 初始化；函数先出现不等于数据库已就绪。未修改 Auctionator 文件。 |
| Auctionator 新数量与历史 | 本机 v341 的 `Source/Database/Mixin.lua`、`Source_LegacyAH/Search/GroupResultsForDB.lua` 与 `Tabs/DataProviders/BuyAuctions.lua` | 没有公开数量 getter。安全后置监听当前对象 `SetPrice(dbKey,price,available)`，`ProcessScan` 标记异步批次；普通物品键的最新数量存入本插件，不写 Auctionator。没有 available 的价格更新不刷新数量；范围/本人拍卖未知时显示汇总估计。`GetPriceHistory` 的 available 是日最高量，只作参考；`GetItemCount` 是记录种数，不是销售数量。 |
| 传统拍卖行实时数量 | 本机 v341 的 `Source_LegacyAH/AH/Mixins/Scan.lua`、`AH/Wrappers.lua`、`Constants/Main.lua` | 被动观察 `QueryAuctionItems` 和 `AUCTION_ITEM_LIST_UPDATE`，读取 `GetNumAuctionItems("list")` 与 `GetAuctionItemInfo`（数量第 3、整组一口价第 10、卖家第 14、物品 ID 第 17 返回值）；不主动请求扫描。按实际返回页汇总，缺页不标为完整；自己的拍卖及没有一口价的条目不计入可购量。 |
| 现代拍卖行实时数量 | [Forever 分支 AuctionHouse 接口声明](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/AuctionHouseDocumentation.lua)；本机 `Source_ModernAH/AH/Mixins/SearchScan.lua` | 仅在对应函数存在时响应 `ITEM_SEARCH_RESULTS_UPDATED` / `COMMODITY_SEARCH_RESULTS_UPDATED`，读取 `GetNum*SearchResults`、`Get*SearchResultInfo` 与 `HasFull*SearchResults`。商品数量减去 `numOwnerItems`；物品排除本人及账号自有拍卖；装备子类型搜索只视为部分结果。接口声明不证明当前角色会走现代拍卖行分支。 |

未学专业继续使用已有配方材料、产量和来源，实际客户端字段优先。NPC 金币报价只来自新表；缺失不当作零，不用历史金额、根成本、卖店收益或 AH 报价冒充 NPC 买价。新表阵营与调用者显式 NPC 访问拒绝仍生效，旧声望、职业、任务、等级和召唤条件不再回退。AH 不受 NPC 是否有 `cost_copper` 限制；材料及图纸比较 AH 支出与 NPC 整包支出，NPC 无有效报价时仍可选择 AH。已学配方免购图纸的规则保留。

## 当前游戏内检查

1.8.28 修复 `AUCTION_HOUSE_SHOW` 监听顺序：其他插件在同事件较早发起的搜索不能被清除；关闭时才清理瞬时查询状态，持久数量不变。普通和空查询的事件顺序均有离线复现与回归。`/dfauction [物品ID…]` 新增本插件版本、查询监听状态、已存记录数和最近数量时间，区分旧运行版本、尚未收到数量及市场分区；不会主动扫描。使用新 Lua 文件须先 `/reload`，旧价格历史无法还原最近数量。

只有新表显式 `offers[npc_id]` 能建立 NPC 供货关系；粗线等物品若仅有根成本而没有 NPC 行，仍不能从旧货架或位置表补出商人。打开商人不读取或改变价格。新路线保存 `vendorQuoteRevision=4` 与 `ProfItemsMeta.sources.csv.sha256`；旧报价或 CSV 内容变化提示手动重算，保留冻结执行记录，纯 AH 方案仍可查看。

纯钓鱼烹饪路线仍使用同一专业 API、参考鱼种分布及地理资料。旧食谱货架已删除，配料和食谱只使用新表采购数据；无报价的未学食谱不会变成免费。离线模拟与生成表核对均不能代替实机购买和制作验证。

图纸报价接口只读取新表显式 NPC 行；无有效金币成本时保留不可定价状态，特殊货币或物品兑换不能成为金币采购。`maxStock` 仅为刷新上限，不是当前现货。任务和配方来源文本仍可单独显示，不能为 NPC 报价补金额或供货关系。价格出处保留 `client/wowhead`，不伪造价格核验日期。

拍卖数量被动接收并独立保存至 `DungeonsForeverDB.auctionSupply` v2，采用 Unix 时间与持久修订号；按客户端 Interface、Auctionator 市场键分区，排除本人数据再按角色保存。正常关闭、重载及重开拍卖行均保留最近数量；超过两天提示旧数据但继续参与预算。没有观察时数量未知并提示去拍卖师完整扫描；历史日最高量仅参考，购物清单目标量不作为货源。完整空搜索只对确认身份的物品给出零，不完整零不覆盖原观察；完整市场标记可确认未出现物品为零，后续记录凭修订号覆盖。沿用 Auctionator 的市场划分，不能声称额外识别了其未区分的中立市场。

全扫临时注销其他列表事件时，经公开数据库更新回调读取仍在客户端的结果；同一 getAll 已完成采集后，后续仅价格通知不能重新标记旧数量时间。读取、元数据写入和完成集合均按每批最多 150 条发布，最后才确认全扫缺失零；新查询取消旧批次。安全后置监听不会改变 Auctionator 原方法的参数/返回值，接口异常隔离并保留客户端/已存记录后备，使用 `/dfauction` 查看状态及最近错误。新观察只使路线待更新，重载就绪通知不自动使未变路线过期或重算。

安装版 v341 的普通扫描封装从索引 1 读取，而 `FullScan/Mixins/Frame.lua` 的 `ProcessBatch` 从索引 0 开始。适配器对 getAll 结果安全探测索引 0 和 count：只有 0 有效且 count 无效时读取 `0..count-1`，否则读取 `1..count`，避免客户端把 0 作为第一条别名时重复第一条、遗漏最后一条；不把其中某种索引约定写死为 Forever 的实测行为。全量结果直接复用分批构造的记录，不再同步复制或排序全部拍卖；货架明细顺序保持客户端观察顺序。

数量适配器在运行时保留逐条整组数量/一口价/单位价，但存档仅保留紧凑汇总及全扫 ID 集合。当前价格沿用原单位报价，未逐档优化实际售价和整组组合；价格与数量分别显示时间，保存数量不保证下单时现货。重复边界写入、跨重载与购买更新路径通过离线模拟；真实扫描、购买后的刷新和跨拍卖行行为仍待游戏内复测。

1. `/reload` 后打开插件。Auctionator 可显示初始化中或缺少有效价格，但已安装时不应误报未安装。
2. 未学习采矿时查看配方，材料应直接显示，来源是参考资料；与训练师对话只更新实际读取到的服务。
3. 打开已学专业的系统专业面板，再输入 `/dfprofapi`。报告区分 `available/unavailable` 与 `data/empty/errors`，并保存到角色状态。完整目录核验后，已确认不存在的参考配方从普通列表和自动路线移除。
4. 重算最省钱路线，先看可用步骤。后续受阻时显示已计算终点及合并后的原因，购物清单只包含当前已计算部分。
5. 价格/配方变化仅标记已存方案过期，切页、重开和重载都不自动重算；点击“重新计算”更新报价和方案。确认五列表格的三个用途标签、合批制作数量、NPC/AH 采购来源及导入过滤。
6. 核对新表显式 NPC 的纯金币金额和整组数量：材料仅接受 `stock=-1`，图纸限量只显示刷新上限，`cost_text` 或任一兑换字段不能冒充铜币。只有根成本的物品不产生 NPC 来源；缺 NPC 金币价仍可选择 AH。打开商人前后不新增买价，旧文件和来源文本不能补价；完全缺价才尝试实际制材或报告受阻。revision 4 或 CSV 指纹变化提示手动重算，AH 行情和数量及冻结执行记录不被替换。
7. 不打开专业面板时，配方材料、产量等字段继续回退已有资料。重算升级路线时，缺少拍卖行及有效 NPC 报价的材料必须由目标本专业制作，并递归计入有价原料成本；无法制作的无价原料应使该冲级候选被替代，没有替代时保留可用前段并说明受阻。不能生成待报价采购，也不能用另一专业顺带产物绕过规则。检查附魔从 1 点起步、工程随机产量手雷、早期可用前段、合批顺序和自定义排除。旧版空白失败及待报价结果自动修复一次，有效有价缓存继续保留。
8. 查看未学专业并开启联合升级时，先选择一个搭配主专业；未选择时不计算，也不显示旧三专业缓存。选已学搭配应使用实际技能，未学搭配从 1 开始。更换搭配后点击重新计算；HUD 和导入必须等待同一配对的结果。开启“仅使用已学习的配方”不能阻止未学目标/未学搭配预览，已学搭配仍遵守过滤；重载后保留选择。只学急救或只有第二个主专业槽有值时，专业识别不能遗漏或误判为未学。

历史离线重放曾读取本机保存的 1.60.1:70374 配方观察和 2667 条 Auctionator 保存报价，工程 60→225（24 个步骤）与附魔 1→225（12 个步骤）均生成全程有价路线。该重放使用指定技能场景，不证明当前角色实时技能、接口返回和实机帧时间；当前代码已移除 Auctionator 商人价格接口，保留 AH 行情接口。

本轮数据切换及二次采购复审的 587 项 Lua 5.1 离线回归通过，详见 `tests/README.md`；包括三语 135 个真实专业/入口小目标、旧冻结/补料/回调门禁、限量图纸 AH 候选与有限 AH 混合采购。这些测试和源码核对仅提供模拟证据。未操作运行中的游戏进行购买、制作、训练或拍卖行扫描，实际返回仍以 `/dfprofapi` 和上述检查为准。

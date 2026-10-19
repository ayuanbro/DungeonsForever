# Forever API 核对与复测

2026-10-19，修复版本 1.8.28。以下区分源码接口声明、离线模拟和当前游戏中的实际返回，不能互相代替。

| 范围 | 已核对证据 | 使用方式与边界 |
|---|---|---|
| `C_TradeSkillUI.GetRecipeSchematic`、`GetRecipeOutputItemData`、`GetRecipeRequirements` | [暴雪 UI 源码的 forever 分支接口声明](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/TradeSkillUIDocumentation.lua)；[Forever 配方表单调用](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_ProfessionsTemplates/Blizzard_ProfessionsRecipeSchematicForm.lua) | 现代接口优先。声明存在不保证任意未学专业或未打开面板时都有数据。 |
| 目录、已学状态及旧 TradeSkill/Craft API | 运行时按函数存在性与实际返回判断 | 只有当前专业完整、稳定且含未学记录的目录才证明配方不存在。旧列表或空值不证明不存在。 |
| 训练师服务 | 运行时安全检查和服务身份读取 | 对话只确认可学习配方及技能要求，不读取学费，也不会加载未学专业的全部原理图。 |
| Auctionator | 本机安装版 v341，TOC 包含 Interface 16001/camelot；`Source/Initialize/Main.lua`、`Source/Variables/Main.lua`、`Source/API/v1` | 公开 API 的第一个参数是调用者 ID。价格数据库于 PLAYER_LOGIN 初始化；函数先出现不等于数据库已就绪。未修改 Auctionator 文件。 |
| Auctionator 新数量与历史 | 本机 v341 的 `Source/Database/Mixin.lua`、`Source_LegacyAH/Search/GroupResultsForDB.lua` 与 `Tabs/DataProviders/BuyAuctions.lua` | 没有公开数量 getter。安全后置监听当前对象 `SetPrice(dbKey,price,available)`，`ProcessScan` 标记异步批次；普通物品键的最新数量存入本插件，不写 Auctionator。没有 available 的价格更新不刷新数量；范围/本人拍卖未知时显示汇总估计。`GetPriceHistory` 的 available 是日最高量，只作参考；`GetItemCount` 是记录种数，不是销售数量。 |
| 传统拍卖行实时数量 | 本机 v341 的 `Source_LegacyAH/AH/Mixins/Scan.lua`、`AH/Wrappers.lua`、`Constants/Main.lua` | 被动观察 `QueryAuctionItems` 和 `AUCTION_ITEM_LIST_UPDATE`，读取 `GetNumAuctionItems("list")` 与 `GetAuctionItemInfo`（数量第 3、整组一口价第 10、卖家第 14、物品 ID 第 17 返回值）；不主动请求扫描。按实际返回页汇总，缺页不标为完整；自己的拍卖及没有一口价的条目不计入可购量。 |
| 现代拍卖行实时数量 | [Forever 分支 AuctionHouse 接口声明](https://github.com/Gethe/wow-ui-source/blob/forever/Interface/AddOns/Blizzard_APIDocumentationGenerated/AuctionHouseDocumentation.lua)；本机 `Source_ModernAH/AH/Mixins/SearchScan.lua` | 仅在对应函数存在时响应 `ITEM_SEARCH_RESULTS_UPDATED` / `COMMODITY_SEARCH_RESULTS_UPDATED`，读取 `GetNum*SearchResults`、`Get*SearchResultInfo` 与 `HasFull*SearchResults`。商品数量减去 `numOwnerItems`；物品排除本人及账号自有拍卖；装备子类型搜索只视为部分结果。接口声明不证明当前角色会走现代拍卖行分支。 |

未学专业默认显示已有参考材料、产量和来源；实际客户端值逐字段覆盖。参考记录标明未核验，不能宣称目录中每条都在当前 Forever 版本开放。商人材料优先采用当前角色有效 API 报价；读不到时允许已核验的 Wowhead Forever NPC 整包参考价格，明确标注来源及声望差异。已核验参考价不是实测，也不是未知价；两者均缺失时仍标记缺价。仍不计已有库存、学习费用和工具要求；1.8.24 按最新要求重新计入必要图纸采购。

## 当前游戏内检查

1.8.28 修复 `AUCTION_HOUSE_SHOW` 监听顺序：其他插件在同事件较早发起的搜索不能被清除；关闭时才清理瞬时查询状态，持久数量不变。普通和空查询的事件顺序均有离线复现与回归。`/dfauction [物品ID…]` 新增本插件版本、查询监听状态、已存记录数和最近数量时间，区分旧运行版本、尚未收到数量及市场分区；不会主动扫描。使用新 Lua 文件须先 `/reload`，旧价格历史无法还原最近数量。

商人实测缺失时先使用已核验固定报价，再考虑没有 NPC/折扣归属的缓存估价；粗线等固定材料无需先访问商人。实际 API 报价仍优先，限量/特殊货币/不可购的拒绝证据仍阻止参考回退。旧快照仅迁移错误的“待读取”诊断，提示重算，不改写原采购金额。

纯钓鱼烹饪路线仍逐字段使用同一专业 API 观察；材料、产量、可用性和已学状态不另设固定替代。钓鱼区域与钓获概率没有假定存在可查询的客户端鱼种分布 API，采用用户指定 Classic 指南参考并明确标记，不能声称已经在 Forever 验证。新增食谱 NPC 组价来自实际读取的 Forever 商人页面，当前角色 API 实测优先。该模式不将待钓鱼量注入普通最省钱优化器库存。详见 [核验记录](data/fishing-routes-audit.md)。

图纸采购新增独立商人读取：保存纯金币购买组价、实际库存及是否可购买，允许有限量图纸报价；材料采购接口仍拒绝限量供应。已学配方状态沿用客户端读取。参考价格不冒充 API 实测，刷新上限不冒充当前库存。

拍卖数量被动接收并独立保存至 `DungeonsForeverDB.auctionSupply` v2，采用 Unix 时间与持久修订号；按客户端 Interface、Auctionator 市场键分区，排除本人数据再按角色保存。正常关闭、重载及重开拍卖行均保留最近数量；超过两天提示旧数据但继续参与预算。没有观察时数量未知并提示去拍卖师完整扫描；历史日最高量仅参考，购物清单目标量不作为货源。完整空搜索只对确认身份的物品给出零，不完整零不覆盖原观察；完整市场标记可确认未出现物品为零，后续记录凭修订号覆盖。沿用 Auctionator 的市场划分，不能声称额外识别了其未区分的中立市场。

全扫临时注销其他列表事件时，经公开数据库更新回调读取仍在客户端的结果；同一 getAll 已完成采集后，后续仅价格通知不能重新标记旧数量时间。读取、元数据写入和完成集合均按每批最多 150 条发布，最后才确认全扫缺失零；新查询取消旧批次。安全后置监听不会改变 Auctionator 原方法的参数/返回值，接口异常隔离并保留客户端/已存记录后备，使用 `/dfauction` 查看状态及最近错误。新观察只使路线待更新，重载就绪通知不自动使未变路线过期或重算。

安装版 v341 的普通扫描封装从索引 1 读取，而 `FullScan/Mixins/Frame.lua` 的 `ProcessBatch` 从索引 0 开始。适配器对 getAll 结果安全探测索引 0 和 count：只有 0 有效且 count 无效时读取 `0..count-1`，否则读取 `1..count`，避免客户端把 0 作为第一条别名时重复第一条、遗漏最后一条；不把其中某种索引约定写死为 Forever 的实测行为。全量结果直接复用分批构造的记录，不再同步复制或排序全部拍卖；货架明细顺序保持客户端观察顺序。

数量适配器在运行时保留逐条整组数量/一口价/单位价，但存档仅保留紧凑汇总及全扫 ID 集合。当前价格沿用原单位报价，未逐档优化实际售价和整组组合；价格与数量分别显示时间，保存数量不保证下单时现货。重复边界写入、跨重载与购买更新路径通过离线模拟；真实扫描、购买后的刷新和跨拍卖行行为仍待游戏内复测。

1. `/reload` 后打开插件。Auctionator 可显示初始化中或缺少有效价格，但已安装时不应误报未安装。
2. 未学习采矿时查看配方，材料应直接显示，来源是参考资料；与训练师对话只更新实际读取到的服务。
3. 打开已学专业的系统专业面板，再输入 `/dfprofapi`。报告区分 `available/unavailable` 与 `data/empty/errors`，并保存到角色状态。完整目录核验后，已确认不存在的参考配方从普通列表和自动路线移除。
4. 重算最省钱路线，先看可用步骤。后续受阻时显示已计算终点及合并后的原因，购物清单只包含当前已计算部分。
5. 价格/配方变化仅标记已存方案过期，切页、重开和重载都不自动重算；点击“重新计算”更新报价和方案。确认五列表格的三个用途标签、合批制作数量、NPC/AH 采购来源及导入过滤。
6. 未访问材料商人时重算一次，已核验不限量材料应使用参考整包金额并显示 Wowhead 提示。访问商人后手动重算，应优先使用实测组价（含声望折扣）。确认 API 没返回价格但已返回限量/特殊货币/不可购时，不能使用同 NPC 参考价。固定攻略购物清单也应按整包取整、标记 NPC 和参考来源。
7. 不打开专业面板时，配方材料、产量等字段继续回退已有资料。重算升级路线时，缺少拍卖行及有效 NPC 报价的材料必须由目标本专业制作，并递归计入有价原料成本；无法制作的无价原料应使该冲级候选被替代，没有替代时保留可用前段并说明受阻。不能生成待报价采购，也不能用另一专业顺带产物绕过规则。检查附魔从 1 点起步、工程随机产量手雷、早期可用前段、合批顺序和自定义排除。旧版空白失败及待报价结果自动修复一次，有效有价缓存继续保留。
8. 查看未学专业并开启联合升级时，先选择一个搭配主专业；未选择时不计算，也不显示旧三专业缓存。选已学搭配应使用实际技能，未学搭配从 1 开始。更换搭配后点击重新计算；HUD 和导入必须等待同一配对的结果。开启“仅使用已学习的配方”不能阻止未学目标/未学搭配预览，已学搭配仍遵守过滤；重载后保留选择。只学急救或只有第二个主专业槽有值时，专业识别不能遗漏或误判为未学。

本次读取本机保存的 1.60.1:70374 配方观察和 2667 条 Auctionator 保存报价做只读离线重放，工程 60→225（24 个步骤）与附魔 1→225（12 个步骤）均生成全程有价路线，没有待报价采购。该重放使用指定技能场景，不证明当前角色实时技能、接口返回和实机帧时间。安装版 Auctionator v341 的商人单位价入口是 `GetVendorPriceByItemID(callerID,itemID)`，已修正调用并保留旧命名兼容；仍须可靠供应和已实测购买组数。

本次执行了 Lua 5.1 离线回归和源码核对；未操作运行中的游戏进行制作、训练或拍卖行扫描，因此这些实际返回仍以 `/dfprofapi` 和上述检查为准。

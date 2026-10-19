# Forever 商人材料目录核验

核验日期：2026-10-18。按用户本次修正，客户端没有商人价格时，允许已核验的稳定资料报价参与路线计算。`GetOffers` 优先本角色有效商人 API 报价；缺失时可使用带同 NPC 实测组数的 Auctionator 商人缓存估算，最后使用本表的 Wowhead Forever 参考报价。显式 `requireObservedPrice=true` 仍只返回实测。旧 `vendorPrices` 和 `VendorPriceSeed` 无法证明 NPC、库存和购买批量，不作为兜底。

当前目录含 **14 个商人货架、202 条不限量供应记录、94 种物品**，包括制作材料、工具和已经逐项确认不限量的图纸。202 条均已补齐该 NPC 的参考整包铜币金额和购买数量，其中常驻商人 139 条、召唤 Bot 63 条。工具和图纸不因此重新计入材料成本。NPC 名称与地图坐标是参考定位；客户端实际读到的名称、购买条件、库存数量和价格优先。

完整研究证据在 [vendor-price-reference.json](vendor-price-reference.json)：包含 14 个 NPC 页面读到的 236 条原始不限量记录及 52 条限量排除记录。原始货架可能还有运行目录没有采用的商品；价格证据不等于当前角色已满足配方学习条件。运行目录的 202 条报价已逐条与该 JSON 对照。

| NPC | 来源 | 核验重点 |
| --- | --- | --- |
| Lorelae Wintersong 12022 | [Forever 货架](https://www.wowhead.com/forever/npc=12022/lorelae-wintersong) | 中立通用材料；盐、煤、线、染料、香料、瓶类、工具；三种限量图纸排除。 |
| Xizk Goodstitch 2670 | [Forever 货架](https://www.wowhead.com/forever/npc=2670/xizk-goodstitch) | 中立线与染料；新材料包图纸不限量；旧斗篷和兜帽图纸限量。 |
| Maria Lumere 1313 | [Forever 货架](https://www.wowhead.com/forever/npc=1313/maria-lumere) | 四种瓶均每次购买 5 个；八种草药及暗影之力图纸为限量。 |
| Elynna 4168 | [Forever 货架](https://www.wowhead.com/forever/npc=4168/elynna) | 联盟线与染料、新材料包图纸；旧限量图纸排除。Invoker 两项开放状态没有确认，未导入。 |
| Herble Baubbletump 3133 | [Forever 货架](https://www.wowhead.com/forever/npc=3133/herble-baubbletump) | 助熔剂、煤、枪托、墨水、羊皮纸与工具；火药、铜管、铜调节器、青铜管、青铜框架、发条式同步协调陀螺仪和银触媒为限量。 |
| Jangdor Swiftstrider 7854 | [Forever 货架](https://www.wowhead.com/forever/npc=7854/jangdor-swiftstrider) | 部落制皮线、染料、盐及新护甲片图纸；五项限量图纸排除。 |
| Tilli Thistlefuzz 5158 | [Forever 货架](https://www.wowhead.com/forever/npc=5158/tilli-thistlefuzz) | 联盟木材、铜棒、魔法微粒与油图纸；奇异之尘、次级魔法精华和两张旧图纸限量。 |
| Kithas 3346 | [Forever 货架](https://www.wowhead.com/forever/npc=3346/kithas) | 部落附魔货架；魔法微粒不限量，奇异之尘、次级魔法精华和三张旧图纸限量。 |
| Alchemist Pestlezugg 5594 | [Forever 货架](https://www.wowhead.com/forever/npc=5594/alchemist-pestlezugg) | 中立四种瓶和炼金石、铁转金、奥金图纸；自然防护与秘银转真银图纸限量。图纸有供应不代表带冷却配方能进入路线。 |
| Innkeeper Skindle 6807 | [Forever 货架](https://www.wowhead.com/forever/npc=6807/innkeeper-skindle) | 水、牛奶、饮料为不限量 5 个一组；六种生鱼限量。 |
| Nixxrax Fillamug 2832 | [矮人烈酒 Sold by](https://www.wowhead.com/forever/item=2596/skin-of-dwarven-stout) | 明确显示库存 ∞、购买数量 1。 |
| Sly Garrett 2622 | [Forever 货架](https://www.wowhead.com/forever/npc=2622/sly-garrett) | 中立毒药材料、瓶、盗贼工具和闪光粉，全货架不限量。 |
| Reagent Bot 242498 | [Forever 货架](https://www.wowhead.com/forever/npc=242498/reagent-bot) | 两页共 65 项；火药两项限量，其余 63 项不限量；包括面粉 10284、厚实原木 272941、厨师刀 273636、元素助熔剂和新图纸。它是召唤 NPC，目录记录 `summoned=true`，不假设玩家已经能召唤或购买。 |
| Krinkle Goodsteel 5411 | [元素助熔剂 Sold by](https://www.wowhead.com/forever/item=18567/elemental-flux) | 中立常驻替代供应；明确显示库存 ∞、购买数量 1。 |

NPC 货架的 `data-type="number"` 表示每次购买数量（缺省单件）；`data-type="quantity"` 的括号表示限量库存。Cost 列中的金币、银币和铜币合并成一次购买的整包铜币金额，不是物品 Sell Price，也不能再乘一次包内数量。商品页面 Sold by 表的“Stock ∞”用于进一步确认。没有把图标上的数量与限量库存混用。

例如 [Maria 的空瓶](https://www.wowhead.com/forever/npc=1313/maria-lumere) 报价为 18 铜/5 件，[Lorelae](https://www.wowhead.com/forever/npc=12022/lorelae-wintersong) 为 20 铜/5 件；[空瓶 Sold by](https://www.wowhead.com/forever/item=3371/empty-vial) 可交叉核对购买数量。不同 NPC 页面报告的价格可能含不同折扣，不统一解释为未折扣基础价，也不再按声望推算一次折扣。需求 6 件时，18 铜/5 件的采购费用为 36 铜，购买 10 件，余量在本方案内复用。

另外检查了 [Mister Graphed 263384](https://www.wowhead.com/forever/npc=263384/mister-graphed)；其当前货架是 Gift of Galloping，不能作为制作材料供应商导入。

## 覆盖范围及缺口

对当前 `Data_ProfRecipes.lua` 的材料字段做去重，得到 482 种材料。与旧 `VendorPriceSeed` 相交的 41 种材料全部已有可追溯的不限量供应来源；新目录覆盖其中 48 种材料，并额外记录工具、图纸与新的 Forever 材料。其余 434 种材料的商人供应关系没有逐项证明不存在。

此计数仅是当前完整配方数据文件的审计，不包括后来由客户端新增读取的配方或独立采矿扩展，不是全游戏目录完整性证明。未知商人来源或缺少可靠报价时，不能据此宣称全局最优；参考报价产生的金额属于该报价模型，不等于已经读取当前角色折扣。

参考报价有 `reference=true/priceVerified=true/estimated=true/priceBasis="wowhead-reference"` 和核验日期、来源 URL，正常进入整组采购费用，购物清单及总额卡明确标注参考来源及声望差异。普通跨角色缓存估算仍标记费用不完整，不能混为已核验参考。API 实测优先，即使其价格高于参考或有效报价为零；声望档位变化使旧实测失效后可使用参考价，重新读取实测后再优先实测。旧 `vendorPrices` 存档原样保留；新扫描另存 `profVendorOffers`，记录 NPC、角色、声望快照、库存性质、价格、数量、来源与时间。

限量、特殊货币、扩展消耗或不可购买的当前角色观测阻止该 NPC 的资料兜底，即使当次 API 没返回价格也保留这些拒绝证据。阵营、声望敌对及已知访问条件仍过滤。召唤 Bot 不因有静态报价就假设可用，需要本角色购买观测或明确可访问证据。仍无报价的已知 NPC 材料保留缺价状态，不能改用拍卖行价或当作免费。NPC 采购不导入 Auctionator。

已保存的方案不会因加入参考价格自动重算；更新插件并 `/reload` 后，点击“重新计算”一次应用新报价。

## 离线验证

`tests/test_prof_vendor.py` 使用 Lua 5.1 模拟环境覆盖旧 7 返回值、当前 10 返回值和结构化商人 API，检查不限量、库存为零、特殊货币、整组数量、可购买性、旧缓存隔离、角色隔离、声望变化及重载、参考价兜底、实测优先、缺价拒绝证据、全部参考组价与证据一致、召唤可用性、无 Auctionator 采购、失效通知和目录中的限量排除。固定与自动路线均测试采购整组数量及来源一致性。尚未在实际游戏商人窗口中验证。

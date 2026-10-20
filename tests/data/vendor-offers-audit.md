# NPC 采购新表通路核对

文档更新日期：2026-10-20。本文说明当前源码和生成数据的采购规则，不是游戏内购买核验记录。旧手工货架及其价格/供货 JSON 已删除，不能作为报价、供应关系或购买条件的后备。

## 唯一采购输入

`Core/ProfItemPrices.lua` 只从正式插件的 `Core/Data/Data_ProfItems.lua` 读取 schema 2 数据：物品根保存 `VendorStackCount` 等公共字段，`offers[npc_id]` 保存显式 NPC 记录和 `cost_copper`。金额来源按 `price_source` 保留 `client/wowhead`；不添加价格核验日期或沿用旧货架的认证字段。

生成流程在 `df-prof-pipeline-v1.0/_temp/fc_prof_items.py`：合并商人、NPC 和客户端价格三表，生成固定 19 列 `DataProfItems.csv`，再用同一份序列化 CSV 内容生成 Lua。`--from-csv` 可只重建物品 Lua。工具包内输出和正式插件数据是独立目录；所有修改限于 Downloads Git checkout，不部署到游戏安装目录。

旧 `Data_ProfVendorOffers.lua`、`Data_ProfFormulaSources.lua` 和钓鱼文件末尾的旧货架已经删除。运行时不读取旧 catalog、商人事件、玩家历史买价或 Auctionator 商人缓存。

## 报价与供货规则

- NPC 金币金额必须是有限非负整数 `cost_copper`；`VendorStackCount` 必须是正整数。金额是不可拆分的整组购买价，不再乘除一次组数。
- 任一 `currency_kind/currency_id/currency_amount` 非空，包括数字 `0`，都不能进入金币采购；`cost_text` 不解析成铜币。物品兑换和特殊货币不能变成零金币商品。
- 只有显式 NPC 行能建立供货关系。物品根有成本但 `offers={}` 时不产生供应商，也不从旧记录或位置表补出 NPC。
- `stock=-1` 才能提供不限量材料。正数限量仅在图纸接口表示刷新上限 `maxStock`，不是当前现货；`stock=0` 不可购，未知库存不能标为不限量。
- 新表阵营和调用者显式的 `npcAccess[npc_id]=false` 生效。已删除的旧等级、声望、任务、职业和召唤条件不会回退到新报价。
- 无金额或无有效组数的图纸记录可保留来源显示，但 `priceUsable=false`。坐标只用于地图，任务信息单独由 `Data_ProfFormulaQuests.lua` 提供，均不赋予采购资格。

## 整组比较与缓存

AH 行情和数量功能保留，不受 NPC 是否存在 `cost_copper` 限制。材料及必要图纸比较实际 AH 采购支出和 NPC 整组支出；NPC 无效或只有兑换来源时仍可走 AH，完全缺价才尝试本专业制材或改选配方。

例如一条模拟 NPC 报价为 37 铜/4 件，需求 6 件且 AH 为 20 铜/件时，购买 8 件支付 74 铜，余下 2 件可在本方案复用。若 AH 为 10 铜/件，则 NPC 买 4 件、AH 补 2 件合计 57 铜，比纯 NPC 的 74 铜和纯 AH 的 60 铜都低。固定攻略和自动路线均支持这种组合，逐步费用合计与采购金额一致。此例是算法输入，不是任何真实 NPC 的现行价格。

路线保存 `vendorQuoteRevision=4` 和 `ProfItemsMeta.sources.csv.sha256`。报价模型或 CSV 内容变化提示手动重算，旧纯 AH 方案仍可查看；不会因为打开页面或商人而重新采价、自动重算或改写冻结执行记录。

## 核对范围

离线回归应覆盖新表金额唯一来源、兑换字段拒绝、阵营/访问拒绝、限量与未知库存、无 NPC 根成本、AH 回退与整组比较、数量余量、来源显示和报价指纹迁移。相关测试位于 `tests/test_prof_item_prices.py` 及专业路线、图纸和流水线测试中。

本轮完整回归结论另见 `tests/README.md`，本文不声明全套通过。游戏内商人可购买性、服务器现货、实机制作和界面仍待验证；静态记录不证明当前角色已经买到商品。

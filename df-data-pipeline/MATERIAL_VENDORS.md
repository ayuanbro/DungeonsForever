# 常规材料商人、货架与购买资格

普通材料只有取得常规供应商、明确不限量、纯金币及阵营可购买证据，才能进入 NPC 与 AH 的比较。客户端物品基础购买价不证明出售资格；图纸继续使用原独立供货与采购逻辑。

## 更新

从仓库根运行以下命令。所有输出、缓存、浏览器资料和日志只能位于本仓库；不写游戏目录，不启动客户端导出服务或调用独立 `scripts/` 生产程序。

```powershell
# 在线检查：刷新种子、维护的NPC目录、所有启用NPC的货架和价格，暂不发布
python -B df-data-pipeline/_temp/fc_update.py --materials-only

# 在线更新：经校验后将材料快照与正式Lua作为同一事务发布
python -B df-data-pipeline/_temp/fc_update.py --materials-only --apply

# 完全离线：重放已保存快照，保留原来的核验时间与失败/停用状态
python -B df-data-pipeline/_temp/fc_update.py --materials-only --offline
```

完整 `fc_update.py` 在线运行默认包含材料更新，`--offline` 则重放材料快照。现有 `--from-csv` 仅重建物品价格/图纸数据，不会从价格CSV推导材料资格。首次没有快照时不能离线构造资格。

网络 provider 可通过 `--material-provider http`、`chrome` 或 `auto` 选择。浏览器 provider 使用仓库内独立资料目录；依赖版本列于 `requirements.txt`，并需要本机 Chrome 或 Edge。Windows 默认使用普通浏览器模式并将窗口放在屏幕外；`--material-headless` 可显式使用无头模式，`--material-channel msedge` 可选 Edge。本轮正常浏览器采集成功，无头模式收到403。抓取被拦截、超时或页面不完整时会报告失败，不能把失败页面当空货架或沿用上一轮资格。

## 维护目录

配置位于 `_temp/_fc/maintenance/material-vendors.json`。`seedItemIDs` 只用于发现 NPC，不授予种子物品任何购买资格；默认包含线、瓶、染料、助熔剂、盐、调料、枪托和铜棒。先刷新种子的 Sold by，再按 NPC 读取完整 `sells` 货架，而不是逐物品扫描全部客户端物品。

`npcs` 以字符串 NPC ID 为键。添加已知材料商人时加入该ID的配置对象；停用时设 `enabled: false` 并填写 `reason`。自动发现不会覆盖手工排除。确有来源证据但页面称号无法识别时，可填写允许的 `role` 与证据 `reason`；角色覆盖不豁免库存、阵营、通货、价格或购买条件检查。

标准类型为 `profession_supply`、`trade_supply`、`reagent_supply`、`general_goods`、`cooking_supply`、`fishing_supply`。未知类型只保留为候选，不生成采购资格。角色名称映射按配置维护，新增映射也不直接授予货架中限量或特殊兑换物品资格。

规范快照位于 `_temp/_fc/data/material-vendors.json`，维护 NPC 目录、发现来源、本轮状态、货架、历史证据引用、核验时间和生成资格。不要手工修改规范快照；修正应写入维护配置后重新运行。

自动发现覆盖种子能关联到的供应商。仅出售全新独有物品的 NPC，需要补充种子或手工登记；目录不声称覆盖全部 Forever 商人。已知 NPC 本轮未再次出现在发现结果中，不自动删除，仍刷新其货架。

## 价格与失败规则

- 成功解析的完整 NPC 货架才替换该 NPC 的旧货架；明确完整的空列表可以撤销旧供货，缺少列表、页面截断和验证页属于失败。
- 每件货物独立检查不限量、纯金币、当前阵营和购买条件。限量、库存未知、兑换或特殊条件未确认的材料不参与普通 NPC 采购。
- 阵营按每一侧的明确友好反应独立确定；例如联盟友好、部落未知，只建立联盟采购资格，不将部落补成友好或敌对。
- 优先采用 NPC 货架中的现金金额与同源购买组数。现金类型已证实但金额缺失时，仅在客户端基础组价、组数有效且与货架不冲突时补价；未知成本类型不能补成金币。
- 网页价格保留来源与时间，属于参考报价，不推算声望折扣。不同来源的金额与组数不能拼接；后续采购按整组数量和余量比较 AH。
- 更新按用户选择部分发布。失败 NPC 保留目录和失败原因，但其历史货架本轮不提供资格；同一材料仍可由其他成功的合法供应商证明。
- 原始网页按内容哈希保存在 `_temp/_fc/cache/material-vendors/`，用于审计与排错。规范快照保留证据引用，离线重放失败快照不会重新采用缓存中的旧成功资格。
- 离线重解析会校验引用的原始网页哈希；需要备份或迁移离线证据时，同时保留规范快照与该缓存的原始网页。缺少原文或哈希不一致会明确失败，不生成没有可重现证据的新表。
- 报告记录发现/成功/失败数量、资格增减、价格变化和未覆盖材料。结构校验、输入并发变动或发布失败会阻止本轮事务，不发布不一致的快照与Lua。

生成的 `Core/Data/Data_ProfMaterialSupply.lua` 独立于 `Data_ProfItems.lua`。插件仅从有效供货表生成匿名材料报价；材料页面和HUD不展示具体NPC。供货或价格语义指纹变化后，旧采购视图要求手动重新计算，历史制作记录保留。

## 验收

执行 `python -B tests/run_tests.py`。实际存档与AH报价的只读重放入口为 `python -B tests/replay_prof_target225.py`；地精任务另用 `--profession engineering --start 60 --choice goblin`。重放包括完整采购量、不抵扣原有背包库存，不能把离线结果当作游戏内现货、声望折扣、布局或帧耗时证明。

本轮采集覆盖、路线与修复包验收结果记录于仓库 `tests/README.md`。

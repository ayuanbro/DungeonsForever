# 专业数据保留与差异记录

当前实现保留 dev 的原始 `Core/Data` 文件、表结构和数据数量，只融合专业路线的计算、客户端读取、执行及提示逻辑。modularization 中有而 dev 缺少的配方、字段和学习条件没有接入运行时；本文件不表示专业数据已经补齐。

工作基线为 dev 的 `942a0ca1ae6478dabad4b0885f7abf4011338cc2`，参考为 modularization 的 `ec184e0d83f9d027e518b95eb0b2545699c5aeea`。参考目录及原始 DB2／网页快照标记为 `1.60.1.70532`，dev 原资料标记为 `1.60.1.70338`。不同版本的源码证据不能直接替代当前客户端确认。

## 当前加载和数据边界

- 原有 `Data_ProfRecipes.lua`、`Data_ProfLeveling.lua`、`Data_ProfMining.lua`、采集、工具、专精及三语数据保持原样。没有新增专业 Data 文件，也没有通过运行时补充层追加配方或改写这些表。
- 仍由主 `DungeonsForever.toc` 加载 `Core`，保留 dev 按专业延迟展开的方式、页面／HUD 入口及 `DungeonsForeverDB` 保存入口。没有引入模块版 Catalog、ModuleAPI 或独立专业插件。
- 静态配方采用 dev 的 `rows > ProfLeveling.rinfo > crafted/enchants` 优先级，明确的客户端观察可校正原有可识别配方。客户端扫描不等于自动收录所有新发现配方。
- `ProfLearning.lua` 保留通用学习条件算法，但不加载 modularization 的静态学习条件投影。它只能判断原有资料或显式输入的条件，无法凭空得知 dev 没有记录的种族、职业、任务和替代学习路线。
- 配方覆盖保持未确认。求解得到可行结果不表示候选完整或全局最优，不能用现有配方数量证明与参考分支功能相同。

## 已融合的逻辑

| 环节 | 当前行为 | 数据限制 |
| --- | --- | --- |
| 输入 | 读取实际材料、产量、可用性、已学事实和训练师观察；失败或不完整读取不会证明配方不存在。 | 主要校正 dev 已有配方，参考分支独有的配方和资格未自动接入。 |
| 搜索 | 比较采购批量、递归制材、图纸、有限供货和产物复用，区分预算截止与可行结果。 | 材料、产物、产量或阈值缺失时，逻辑不能生成真实配方。 |
| 条件 | 自动和固定步骤共用当前可获得的可用性、工具、专精与学习检查；冷却未知不当作无限制作。 | 未加载的复杂学习条件仍是资料覆盖缺口，不能宣称已经逐条约束。 |
| 执行 | 保存冻结计划、制作事实、确认产出、材料用途、补料和续算。 | 原有攻略的预计次数和购物清单不等于实际制作回执。 |
| 晋级与导航 | 使用 dev 训练师／教材／任务资料和角色实际技能上限提供提示；采集导航不产生材料。 | 缺失的任务细节、节点对应关系或角色上限不会由求解器模拟补造。 |

具体实现及专业边界见[逐专业审计](profession-route-per-profession-audit.md)。

## 缺少数据的实际影响

急救保留 dev 自动规划入口和原固定攻略，但攻略涉及的制作技能缺少完整配方记录，不能据此承诺自动规划、购物汇总或执行已经可用。参考资料中可以提取固定路线所需材料、产物和黄／绿／灰阈值；其中六个学习门槛仍有来源歧义。这些资料全部单列，没有补进 Data。

其他制作专业的参考分支新增候选、已有配方缺失图纸及冲突字段也未接入。它们有些可以扩大候选覆盖，有些会影响未学配方的资格、一次性图纸成本或产量计算；是否必要取决于实际选择的路线。未知值和冲突不能因来源版本较新而自动覆盖 dev。

人可读清单见[dev 专业数据缺口](profession-dev-data-gaps.md)。完整字段和证据见：

- [配方参考差异](profession-data-reference-differences.json)：双方原字段、可供人工审查的 `candidateFields`、冲突及未知项；元数据明确标记 `appliedToRuntime=false`。
- [学习条件缺口](profession-learning-condition-gaps.json)：dev 已有配方缺少的参考学习门禁与来源。
- [未确认资料](profession-data-unconfirmed.md)及[对应 JSON](profession-data-unconfirmed.json)：参考资料的逐配方未知／冲突清单。
- 原证据清单：[制作 A](../validation/data/prof_crafting_a_candidates.json)、[制作 B](../validation/data/prof_crafting_b_candidates.json)、[急救](../validation/data/prof_first_aid_candidates.json)。

这些 Markdown／JSON 文件不在 TOC 中，不参与候选收集，也不修改运行时 Data。原证据清单的 `acceptedFields` 在文档导出中称为 `candidateFields`，表示字段有参考来源、可以继续审查，不表示已采用、已导入或当前客户端已确认。

## 来源复现与验证边界

[export_prof_reference_differences.py](../validation/export_prof_reference_differences.py) 和 [export_prof_learning_condition_gaps.py](../validation/export_prof_learning_condition_gaps.py) 仅导出文档参考 JSON。来源提交、版本、来源文件及 SHA256 保留在证据中；它们不生成运行时专业数据。

离线验证使用实际 dev 数据、Lua 5.1 及三语加载，检查原始 Data 未变、原有配方解析优先级、求解、门禁、执行及页面入口。可从仓库根目录运行：

```powershell
python -m unittest discover -s validation -p 'test_prof_*.py' -q
```

本次最终 182 项回归通过，173 个 Core Lua 文件通过 Lua 5.1 编译。保护检查逐个核对 129 个原 Data 文件的内容与路径，并确认 TOC 数据加载项及语言条件与原 dev 一致；两个仅写文档的导出器均可用 `--check` 逐字复现。测试中的显式条件或客户端观察替身只能验证算法，曾使用补充候选执行的离线用例不作为当前原生加载路径的完成证据。

尚需真实客户端验证技能面板、学习条件、专精任务、共享冷却、商人库存、实际制作和产量、HUD 绘制及跨登录事件。源码、DB2 和网页快照一致不等于游戏中已经确认。

# 同版本资料复用与补充数据交付（2026-10-30）

> 这是规则3阶段记录。后续各专业自动习得、通货来源和规则4生成物见[来源修正记录](source-origins-2026-10-30.md)，当前缺口数量与验证以新记录为准。

本次全部离线完成，使用已关闭的 Wago `wowf` 数据包 `1.60.1.70685`，不重新采集，也不依赖旧 Lua 生成物补缺。已更新独立的 [Data_ProfLearningSources.lua](../../../Core/Data/Data_ProfLearningSources.lua)。

## 新抓与复用统计

| 项目 | 条数 |
| --- | ---: |
| 本轮实际新请求 newlyRequested / attempted | 7480 |
| 同版本 verified 复用 reused | 1234 |
| 新请求或有效复用 covered | 8714 |
| 未新请求且未有效复用 uncovered | 16 |
| 全部目标 targetCount | 8730 |
| 有效网页 verified（含复用） | 8193 |

复用记录仍保留原始 `webRunID`、URL、采集时间、SHA-256。复用登记校验同一原始包的 build/config、DB2、网页字节和解析结果，不把旧记录改成本轮请求。

`notAttempted=1250` 继续准确表示本轮未发送请求的数量，其中1234条已复用，16条保留缺口。因此 `requestCoverageComplete=false`；有效复用不伪造本轮全量请求完成。`sourceCoverageComplete=false`，数据仍按部分资料交付。

## 缺口逐项清单

- [来源缺口 CSV](source-gaps-2026-10-30.csv)：537条，包含来源地址、实体ID、HTTP状态、错误和原批次；`notNewlyRequestedAndNotReused=True` 标出剩余16条。
- [技能资料缺口 CSV](learning-gaps-2026-10-30.csv)：2153条，按专业、技能ID、缺失原因和路径状态列出。
- [完整审计](../../../.pipeline-runtime/prof-learning-generation-20261030/learning-audit.json)：含所有规范化事实、教材、训练师、商人、任务和条件。
- [复用证据与未覆盖项](../../../.pipeline-runtime/prof-learning-generation-20261030/reuse-and-source-gaps.json)：1234条复用证据及16条旧失败记录。

537条网页缺口分为278条 sourceMissing、255条 parseError、4条 sourceBlocked。当前剩余 parseError 均为 matching recipe record missing，已没有 malformed listview JSON。404不证明游戏内删除；缺少配方条目的页面也不能凭空补出制作或学习路径。

| 剩余16条旧失败记录 | 技能ID |
| --- | --- |
| HTTP404 / sourceMissing | 2330、2337、3447、6619、7181、11457、17556、22434 |
| matching recipe record missing | 2577、2578、2579、3413、7732、13262、18248、18260 |

受阻的4条为技能1216024、1217189、1252251、1252252，均保留HTTP403证据。

“2153条带资料缺口的记录”不等于2153条配方全部不能使用：某条教材获取资料缺失时，独立确认的训练师路径、已有明确来源或已学配方仍按现有逻辑判断；所有学习路径均无法确认的未学配方继续排除自动路线。获取条件未知不记为免费、保证可得的库存。

## 生成与原生数据边界

补充文件为规则3，包含2540条专业技能参考记录、2226条已确认学习路径。参考记录不会新增到 dev 原生配方数组。急救未加入补充资料；原生急救、数值和数据结构不变。

原始129个 Data Lua 文件逐字节哈希未变，TOC原有条目、顺序、语言条件及延迟加载方式未变。本次只更新已有独立补充文件，没有新增加载项或模块框架，保留 `ns.Init`、事件注册与 `DungeonsForeverDB` 接入方式。现有未提交的功能修改未被重置。

完整审计保留37261条掉落NPC关系引用；它们不确认教材获取资格，也不构成保证库存。补充文件把完整名单留在离线包，仅携带 `dropSourceCount`、`dropDetailsOffline`。不提供 `acquisition.drops` 覆盖 dev 原有掉落视图。教材关系、学习条件、训练师ID、任务条件、商人报价和非拍卖限制均保留。

嵌套条件与来源结构通过内部共享编码、共享结构模板、连续字符串池及小整数编码压缩；仍提供原有 Get / ForProfession / Each / Materialize 查询接口，数据按需解码。Lua文件129083字节，无游戏内联网或JSON解析。

本专业学习技能门槛审计发现196处差异，涉及177条原生配方，继续采用 dev 数值优先规则。[数值冲突审计](../../../.pipeline-runtime/prof-learning-generation-20261030/native-conflicts.json) 保留来源值及 dev 值；其范围仅为本专业学习技能门槛，不声称穷尽全部数值字段。

## 验证结果

- 127项流水线、编解码、学习路径、UI与冻结计划检查通过，无跳过。
- 37项原生配方、急救、学习资格、路线计划和master后端回归通过。
- Lua5.1逐项对比2540条生成记录的全部公开字段，与当前来源事实的运行时投影一致；确认Forever限定、不添加原生配方、无急救。
- 将原始归档和流水线源码复制到Linux临时目录，禁用 socket.connect 后重建；Lua和完整审计均逐字节一致。重建约11.16秒，无GUI，无旧Lua输入。
- zhCN / zhTW / enUS全TOC选定加载检查通过：新增冷启动内存最高250.49 KiB，单专业最高511.67 KiB，全部专业最高1382.03 KiB；分别低于256 / 512 / 2048 KiB。
- 本次数据更新前后使用相同原生Data与功能代码，炼金、锻造、制皮分别覆盖已学／未学场景，每场景交替150次暖态 Capture。六个场景p95回退均不超过10%，最大4.44%。共享主机测量存在调度噪声，不把耗时下降当作普遍性能提升。

以上内存检查在GC后强引用原生配方对应的记录与路径视图，不包含所有离线证据或全部历史计划。耗时比较仅覆盖 target=75 的 Capture，不包含完整求解、UI或初次加载。本次没有新增后台任务；没有在真实客户端证明全部既有回调严格不超过2ms，也没有进行游戏内学习／采购验收。

[机器验证汇总](acceptance-2026-10-30.json)；[可携带原始归档](../../../.pipeline-runtime/prof-learning-full-20261029.reused-20261030.zip)。

## 重复执行

```sh
python -m data_pipeline.professions reuse-verified --raw .pipeline-runtime/prof-learning-full-20261029 --report .pipeline-runtime/prof-learning-generation-20261030/reuse-and-source-gaps.json
python -m data_pipeline.professions status --raw .pipeline-runtime/prof-learning-full-20261029
python -m data_pipeline.professions build --raw .pipeline-runtime/prof-learning-full-20261029 --output Core/Data/Data_ProfLearningSources.lua --report .pipeline-runtime/prof-learning-generation-20261030/learning-audit.json
python -m data_pipeline.professions check --raw .pipeline-runtime/prof-learning-full-20261029.reused-20261030.zip --output Core/Data/Data_ProfLearningSources.lua --report .pipeline-runtime/prof-learning-generation-20261030/learning-audit.json
python -m data_pipeline.professions.gap_reports --audit .pipeline-runtime/prof-learning-generation-20261030/learning-audit.json --reuse-report .pipeline-runtime/prof-learning-generation-20261030/reuse-and-source-gaps.json --source-output data_pipeline/professions/reports/source-gaps-2026-10-30.csv --learning-output data_pipeline/professions/reports/learning-gaps-2026-10-30.csv
```

重复登记复用只更新采集审计元数据，不改变规范化事实指纹；重建归档前不要把修改过的目录清单与旧ZIP当作同一份原始包。在线传输效率对照本次未运行。

## 后续专项：掉落图纸通过拍卖行学习

检查结论：现有逻辑不会仅因图纸是掉落来源而排除其拍卖购买路径。本次只增加回归检查，未修改生产逻辑、原生Data或独立补充文件。

使用实际生成记录 `alchemy:3230 → item:2553`（200条掉落NPC来源引用、教材获取状态unknown、学习条件confirmed），注入25000铜的模拟有效报价和1份可用拍卖供给。学习资格通过，选择AH路径，图纸费用25000铜；8次制作的收集计费仍只购买1份图纸。该价格是测试输入，不是实时市场价格。

合成路线同时验证快速、精确及固定路线：技能1升4，材料每次7铜，图纸501铜，结果总价522铜，图纸只计1份。部分掉落／任务奖励来源资料不足不会单独关闭AH路径，任务奖励的获取条件未被误当作全局学习条件；实际声望学习条件不满足仍会拒绝。

本次专项执行8项Lua5.1检查全部通过：新增真实生成样本、部分来源、精确／固定路线、快速路线4项；另检查学习条件未知、图纸不可交易、拍卖数量耗尽、明确禁用拍卖购买4项边界。用例位于 `tests/test_runtime_learning.py` 和 `tests/test_learning_ui_execution.py`。这些结果证明离线路径与计费行为，不代替游戏内实际购买验收。

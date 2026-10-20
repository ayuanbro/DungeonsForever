# 旧专业包功能和数据覆盖核对

核对日期：2026-10-21。唯一维护实现为本目录；`df-prof-pipeline-v1.0` 保持留档停用，不转发执行。当前核对以旧包原件SHA-256、活动实现接口和回归测试为依据，不用“脚本同名”代替功能核对。

## 功能对应

| 旧专业包功能 | 综合包维护实现 | 保留方式/变化 |
| --- | --- | --- |
| 单入口、检查/发布、离线、路径与刷新参数 | `fc_update.py` → `fc_pipeline.py` | 默认检查，正式发布单锁/单事务；新增独立候选保留与安装ZIP生成 |
| 14页抓取、离线缓存与RSC解析 | `fc_fetch.py`、`fc_parse.py` | 串行抓取、失败检查、全部旧原始输入及HTML独立留存 |
| 区域名转AreaID | `fc_zones.py`及本包AreaTable/Questie资料 | 无游戏目录工具回退；既有60条映射保留 |
| 字段/顶层键审计、Lua发射复检 | `fc_fields.py`及统一最终校验 | 关键Lua依赖缺失时失败，保留完整字段/材料/阈值/来源检查 |
| 汉化词表对账/人工追加/批次辅助 | `fc_i18n.py`、`_fc/i18n/zh.json` | 原词表归档；本次增补2条缺译 |
| 专业基础5表生成 | `fc_gen.py`、`fc_maintenance.py` | 扩为含训练师的6表；保留既有人工增补、毒药/理解、阈值、来源、省略和顺序规则 |
| 物品CSV合并、三语原名、金币/兑换成本、库存条件 | `fc_prof_items.py` | 外部CSV只读；不使用背包库存扣减、不恢复旧报价表；同轮商人资料参与合并 |
| NPC坐标合并、独立19列CSV重建 | `fc_prof_items.py --from-csv`及普通合并模式 | 明确保留两种模式及稀疏Lua字段处理 |
| 专精学习途径、图纸+训练师、confirmed/pending/conflict | `fc_prof_specializations.py` | 原证据与版本独立保留，缺证据不猜测无限制 |
| Wowhead缓存、robots、限频与冷却 | `fc_specialization_fetch.py` | 规范缓存和冷却状态已迁入；不会绕过拒绝/冷却 |
| 外部配方目录与条件请求 | `fc_recipe_catalog_fetch.py` | 校验目录hash及出处，不虚构精确build |
| DB2教学链、未映射分类与旧基线对账 | `fc_recipe_item_audit.py` | 快照版本/热修复/9表hash严格检查，保留resolved/removed等区别 |
| 已验证网页物品教学证据审计 | `fc_recipe_item_web_audit.py` | 使用可用规范缓存，不把列表命中当教学关系 |
| 专精独立更新及准备/发布能力 | `fc_refresh_specializations.py` | `prepare_batch`只准备5派生产物及状态，不提前发布；CSV改为只读inputs，兼容旧schema1状态 |
| 去注释工具 | `strip_comments.py`、`strip_lua_comments.py` | 两份原工具均保留；修复检查模式改文件问题，不通配处理本链以外数据 |
| 自动调用外部客户端导出器 | 已按本次用户要求移除 | 不依赖或启动 `scripts/` 程序/wow.tools.local；保留读取、绑定、校验其已生成CSV及DB2证据的能力 |
| 英文/繁体生成 | `fc_locales.py`及语言包装脚本 | 新增6表×2语言，稳定身份+源文hash保留人工译文，BIS按职业/专精识别 |

本次唯一获准的现有配方删除是 `spell=1251750 / item=250952`：用户选择跟随最新网页移除，授权范围在维护记录中精确限定。急救运行分片和非附魔favor继续沿用既有人工省略规则，原始数据仍保留为证据，不能用旧样例覆盖这些维护决定。

## 数据完整性清单

`_temp/_fc/maintenance/legacy-coverage.json` 逐文件记录旧相对路径、字节数、SHA-256及本包独立保存位置，共 **249份非字节码原件**：

- 69份脚本、输入、样例、说明等保存在 `archive/df-prof-pipeline-v1.0/`，旧可执行脚本及Lua样例以 `.txt` 结尾归档，避免成为另一个活动实现。
- 180份HTML、DB2、网页规范缓存、冷却及历史运行材料保存在 `_temp/_fc/cache/migration-archive/df-prof-pipeline-v1.0/`，按原SHA-256留存，缓存按既有规则不进入Git或安装ZIP。
- 9份 `__pycache__/*.pyc` 是可重建的解释器字节码，明确排除；它们不是独立功能或源数据。

所有原始JSON、旧DataProfItems/训练师CSV、原审计结果、词表、区域数据、Questie、干跑工具、原Lua样例、旧入口原件及缓存均有独立哈希保存。活动输入/输出可继续演进，不会使旧快照记录丢失；日常运行不依赖旧目录或归档副本。

活动数据的来源还包括当前仓库正式70338维护基线、此次70450网页和用户此前生成的5份CSV；本次不会让旧包70245样例回退覆盖它们。

## 可重复验证

```powershell
python -B df-data-pipeline/_temp/fc_legacy_audit.py
python -B df-data-pipeline/_temp/fc_legacy_audit.py --without-caches
python -B tests/run_tests.py
```

第一条在当前有缓存的工作区核对249份原件，第二条只核对69份随源码归档的原件，两者都不读取旧包目录。详细结果写 `_temp/_fc/reports/legacy-coverage.json`。新机器若没有迁入忽略的缓存，需要先取得对应缓存；不能把跳过缓存的检查说成全部249份通过。

完整执行链还会核对当前记录保留、规范输入/CSV哈希、三语言按TOC加载、惰性配方、材料/技能/来源/坐标及扩展，以及所有未接管运行文件的字节保留。

每个活动脚本的外部输入位置见 [SCRIPT_INPUTS.md](SCRIPT_INPUTS.md)。

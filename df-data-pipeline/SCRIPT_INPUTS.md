# 专业流水线脚本与外部输入清单

核对日期：2026-10-21。本文覆盖统一专业链、旧专业包全部17个Python脚本及新增支持脚本。综合包中职业任务、副本、装备等历史生成器不接入本链，它们的固定路径引用由 `fc_path_audit.py` 单独列为历史工具，不应批量执行。

## 路径约定

- 仓库根 `R = C:\Users\yewei\Downloads\DungeonsForever\DungeonsForever`。
- 流水线根 `P = R\df-data-pipeline`；脚本根 `T = P\_temp`。
- 下表均按这些根目录定位，与启动工作目录无关。显式相对路径参数则相对于调用目录。
- 所有输出、缓存、暂存、日志和ZIP只能在当前仓库。输入文件是只读的；不会启动游戏、wow.tools.local、PowerShell导出器或 `scripts/` 中的程序。

## 外部生产的CSV：默认已保存为流水线自有快照

下列五个默认输入按原字节从此前CSV导入，清单与完整SHA-256在 `T\_fc\inputs\manifest.json`。`originalFile` 只是迁移来源记录，运行时不会去该位置找脚本、刷新或回退输入。

| 文件及实际默认读取位置 | 此前生产位置（只作来源说明） | 用途 | 显式覆盖参数 |
| --- | --- | --- | --- |
| `T\_fc\inputs\client\item-buy-prices.csv` | `R\scripts\export_buyprice\output\item-buy-prices.csv` | 三语物品原名、基础购买价、组数、Build/HotfixBuild | `--prices-csv` |
| `T\_fc\inputs\client\item.csv` | `R\scripts\export_buyprice\output\item.csv` | 原始Item分类、ID集合及关联审计 | `--item-csv` |
| `T\_fc\inputs\client\recipe-item-specializations.csv` | `R\scripts\export_buyprice\output\recipe-item-specializations.csv` | 物品教学链、RequiredAbility、版本证据 | `--recipe-items-csv` |
| `T\_fc\inputs\vendors\vendors.csv` | `R\scripts\out\vendors.csv` | NPC供货、原成本、库存、阵营与条件 | `--vendors-csv` |
| `T\_fc\inputs\vendors\npcs.csv` | `R\scripts\out\npcs.csv` | NPC名称、区域、坐标 | `--npcs-csv` |

如果以后外部工具生成新CSV，可明确传入那份CSV。生产程序的存在、参数和运行状态都不是本流水线依赖。客户端三CSV必须属于同一已验证DB2批次；不能仅凭相同Build把不同热修复数据混合使用。

普通材料采购只采用客户端 CSV 的有效基础整组价与组数，不要求商人记录。生成器为每个客户端物品保留独立无 NPC 的报价行，使固定19列 DataProfItems.csv 可以完整重建根价格。材料根报价与图纸 NPC 报价分开：图纸仍严格要求显式商人记录，并保留阵营、库存性质、兑换条件和具体来源；普通材料报价不会建立图纸供货资格。

## 各脚本实际读取的文件

表中“缓存”均为仓库内文件，不是游戏目录。上游来源是证据属性，不代表运行时要连接旧导出服务。

| 脚本 | 读取位置和文件 | 外部访问/补充说明 |
| --- | --- | --- |
| `fc_update.py` | 本包 `fc_pipeline.py` | 唯一统一入口，默认检查，`--apply`才发布 |
| `fc_pipeline.py` | 上述5份CSV；`T\_fc\data\*.json`；`T\_fc\i18n\*.json`；`T\_fc\maintenance\`下维护输入；当前 `R\Core\Data`、`R\Locales`、TOC作为保留及加载校验基线 | 只调本包Python步骤；无 `scripts/` 程序调用。`--offline`禁止网页请求 |
| `fc_pipeline_paths.py` | 无额外文件；根据脚本目录计算CSV默认路径 | 统一路径常量，不探测游戏/旧专业包/外部工具 |
| `fc_pipeline_common.py` | 当前Python可导入的 `lupa.lua51`（统一入口优先预载 `R\.pipeline-runtime\lib`）；待验证Lua/输入/输出；仓库锁与发布备份 | Lua 5.1必须可用。导入失败时仍有可选只读回退 `C:\Users\yewei\AppData\Local\Temp\df-lua-runtime`，不在该处安装或写文件。锁为 `T\_fc\cache\.pipeline-state\update.lock` |
| `fc_fetch.py` | `T\_fc\cache\professions.html`、`professions_<slug>.html`、`_meta.json` | 在线串行请求 `https://foreverchanges.pro/professions`及13个子页；离线只读缓存 |
| `fc_parse.py` | 同一组14个HTML | 解析为 `index.json`、`prof_*.json`、`item_ids.json`；统一入口写本轮暂存，不直接改正式输入 |
| `fc_zones.py` | 当前归一化index/prof JSON；`T\_fc\cache\areatable_classic.csv` | 缺缓存且在线时读取wago AreaTable；离线缺表明确失败。代理可用 `DF_PIPELINE_PROXY` 配置 |
| `fc_fields.py` | 本轮归一化JSON；生成器字段声明；`T\tools\tf_dryrun.py`、`wow_stub.lua` | 统一链使用 `--strict --source-only`，最后另做真实Lua/三语发射校验；不跳过缺失关键依赖 |
| `fc_i18n.py` | 本轮归一化JSON、`T\_fc\i18n\zh.json`；`--add/--batch`时另读取人工提供的词表内容/批次文件 | `--audit`只对账，缺译不自动联网翻译 |
| `fc_gen.py` | `index.json`、`prof_*.json`、`enchant_ids.json`、`vendor_loc.json`、可选 `vendor_side.json`、`drop_loc.json`、`zone_ids.json`、`zone_zh.json`；`zh.json`；`T\questie\questie_forever.json`；`T\_wago_AreaTable_zh.csv`；专业维护输入 | 支持文件优先取冻结暂存目录，否则取本包默认路径；无游戏/旧专业目录回退 |
| `fc_maintenance.py` | `T\_fc\maintenance\professions.json`及其版本化维护记录/源文件 | 三方冲突检查、人工新增、阈值/来源修订、字段及分片省略、顺序与计数；一次性迁移参数 `--migrate-from` 才读取显式旧Lua目录 |
| `fc_prof_items.py` | `vendors.csv`、`npcs.csv`、`item-buy-prices.csv`；本轮生成的Data_ProfVendors.lua | 在内存合并，统一链使用同轮商人数据，并单独保留客户端物品基础整组价格；`--from-csv`只读指定19列DataProfItems.csv，跳过三表合并 |
| `fc_refresh_specializations.py` | 客户端3份CSV；有效专业目录；训练师旧CSV；专精current指针/显式DB2目录；网页缓存 | 在线只刷新独立网页证据；客户端3份CSV与DB2在线/离线均为只读输入。训练师CSV是本轮派生产物，`--apply`才同批发布 |
| `fc_prof_specializations.py` | 图纸CSV、训练师CSV、`prof_*.json`、`enchant_ids.json`及Wowhead规范缓存 | 合并学习途径/证据；缺证据保留pending，不把0当无限制 |
| `fc_specialization_fetch.py` | `T\_fc\cache\specializations\wowhead-forever\<URL哈希>.json`；`.network-state`锁、请求时钟、冷却 | 在线低频请求Wowhead Forever专业页及所需法术页；尊重缓存、robots与冷却，离线不请求 |
| `fc_recipe_catalog_fetch.py` | `T\_fc\cache\specializations\wuxianwow\recipes.json`、`source.json`；独立请求时钟/冷却 | 在线条件请求 `https://wuxianwow.com/data/recipes.json`及其robots；不能据此虚构精确build |
| `fc_recipe_item_audit.py` | 客户端3份CSV、DB2 manifest和表、可选旧图纸CSV基线、可选外部配方目录JSON | 只读关联与未映射分类审计，无网络；省略DB2路径时从本包已验证current选择 |
| `fc_recipe_item_web_audit.py` | 图纸CSV、DB2快照、已有Wowhead规范缓存 | 只审计可用网页证据，不自行发起抓取 |
| `fc_locales.py` | 本轮6份基础Lua、`T\_fc\maintenance\locales.json`及语言审计记录；既有6份各语言Lua作为格式基线 | 以稳定身份与源文哈希复用人工译文；原文不匹配阻止生成；只处理6份专业表 |
| `gen_enus_data.py` | `--source-root`中6份基础专业Lua和人工语言维护输入 | 独立enUS包装入口，不通配处理共享/非专业文件 |
| `gen_zhtw_data.py` | 同上，另读取OpenCC配置 | 独立zhTW包装入口 |
| `gen_zhtw.py` | `R\.pipeline-runtime\lib`中的OpenCC，调用方传入文本 | 繁体转换辅助；缺OpenCC明确失败 |
| `strip_comments.py` | 调用方传入Lua/样式文件 | 保留的去注释辅助；检查模式不改文件，不作为独立发布入口 |
| `strip_lua_comments.py` | 命令行明确指定的Lua/目录；无参默认扫描 `P\Core` 与 `P\Locales` | 旧专业包去注释工具已完整保留，默认dry-run，`--apply`才写入；不接入统一链 |
| `fc_package.py` | `R\DungeonsForever.toc`递归XML引用、`LICENSE`、Media资源以及本轮验证后的20份专业Lua | 只生成安装ZIP；原运行文件按原字节收入，其余工具/缓存/报告不打包 |
| `fc_path_audit.py` | 两流水线、相关工具、测试与说明中的脚本文本 | 静态读取路径，区分活动/历史/归档/外部支持工具；不会执行它们 |
| `fc_legacy_audit.py` | `T\_fc\maintenance\legacy-coverage.json`指向的本包归档及缓存 | 不读取旧专业包目录；按原SHA-256验证249份历史原件，`--without-caches`可只验随源码保存的69份 |

## 必须保留的DB2证据目录

默认选择 `T\_fc\cache\specializations\current.json` 记录的快照；也可传 `--db2-dir <仓库内目录>`。目前已有：

`T\_fc\cache\specializations\db2\1.60.1.70450\d5c044674353ac14192bd8fe21cf6aa6a310c91e4e0b6c2bd9d9f9cc8ac9a85c\`

该目录包含 `manifest.json` 和9份表：`item.csv`、`itemsparse.csv`、`itemeffect.csv`、`itemxitemeffect.csv`、`spelleffect.csv`、`spelllearnspell.csv`、`skilllineability.csv`、`skillline.csv`、`spellname.csv`。manifest里的旧本地HTTP URL仅记录当时导出来源，运行时不会请求这些URL。

检查会核实manifest/各表SHA-256、版本/热修复身份、Item原文字节、CSV ID覆盖、价格/enUS名称/组数/状态以及RequiredAbility。缺少这组证据时明确失败，不会启动外部导出工具补齐，也不会静默跳过关联审计。

目标生成批次70450不等于所有历史证据都在70450重新核验。毒药、理解专业的人工分片在 `supplemental_catalog_sources` 中明确保留70338来源与冻结维护文件哈希，有效catalog继续输出70338及`source_provenance`；未知来源版本留空。

## 保留生成与只打包

在仓库根运行，选择不存在的暂存/ZIP路径：

```powershell
python -B df-data-pipeline/_temp/fc_update.py --check --offline `
  --stage-dir .pipeline-runtime/review/validated-batch `
  --package-zip dist/DungeonsForever-1.8.33-data-70450-preview.zip
```

去掉 `--offline` 时只允许网页联网更新，CSV与DB2仍是只读现成输入。`--stage-dir`保留规范JSON、有效目录、CSV、审计与20份Lua候选及输入哈希；ZIP使用这些新Lua，其他运行模块保持原字节。两者都不能与 `--apply` 合用。

普通完整检查不加 `--stage-dir/--package-zip` 时只产生仓库内缓存、暂存和报告。规范JSON、派生CSV、Lua及成功指针要等明确执行 `--apply` 才事务发布；外部生产的5份输入CSV始终只读，发布也不覆盖它们。

## 旧专业包覆盖核对

详见 [LEGACY_PARITY.md](LEGACY_PARITY.md)。249份非字节码原件已按SHA-256独立保存到本包（69份源码/数据/说明归档、180份缓存历史），9份可重建pyc明确排除。日常流水线不读取旧包或这些历史副本；旧入口仍退出并提示统一入口。

旧包中“自动启动外部服务导出客户端CSV”的编排已按本次要求移除，读取与校验已生成CSV的功能、物品/商人/专精/网页证据及审计功能均保留。其他综合包模块保持原实现与入口，未接入本次专业链。

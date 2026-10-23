# 专业流水线脚本与外部输入清单

核对日期：2026-10-23。本文覆盖统一专业链及现用支持脚本。旧专业包和重复归档已删除，历史迁移来源可从 Git 查询。综合包中职业任务、副本、装备等历史生成器不接入本链，它们的固定路径引用由 `fc_path_audit.py` 单独列为历史工具，不应批量执行。

## 路径约定

- 仓库根 `R = C:\Users\yewei\Downloads\DungeonsForever\DungeonsForever`。
- 流水线根 `P = R\df-data-pipeline`；脚本根 `T = P\_temp`。
- 下表均按这些根目录定位，与启动工作目录无关。显式相对路径参数则相对于调用目录。
- 所有输出、缓存、暂存、日志和ZIP只能在当前仓库。输入文件是只读的；不会启动游戏、wow.tools.local、PowerShell导出器或 `scripts/` 中的程序。
- 工具运行样例不再跟踪。`python -B df-data-pipeline/prepare_workspace.py` 从仓库根的正式运行文件创建工具工作副本，任一目标已存在则拒绝覆盖；它不修复历史生成器的固定 D 盘路径或外部依赖。

## 外部生产的CSV：默认已保存为流水线自有快照

当前使用五个CSV输入角色及独立的 NPC 所属组织 JSON，清单与完整SHA-256在 `T\_fc\inputs\manifest.json`。最初导入的五份CSV保留原字节与修改时间；商人供货默认改为独立版本的修复快照。`originalFile` 只是迁移来源记录，运行时不会去该位置找脚本、刷新或回退输入。

| 文件及实际默认读取位置 | 此前生产位置（只作来源说明） | 用途 | 显式覆盖参数 |
| --- | --- | --- | --- |
| `T\_fc\inputs\client\item-buy-prices.csv` | `R\scripts\export_buyprice\output\item-buy-prices.csv` | 三语物品原名、基础购买价、组数、Build/HotfixBuild | `--prices-csv` |
| `T\_fc\inputs\client\item.csv` | `R\scripts\export_buyprice\output\item.csv` | 原始Item分类、ID集合及关联审计 | `--item-csv` |
| `T\_fc\inputs\client\recipe-item-specializations.csv` | `R\scripts\export_buyprice\output\recipe-item-specializations.csv` | 物品教学链、RequiredAbility、版本证据 | `--recipe-items-csv` |
| `T\_fc\inputs\vendors\vendors-soldby-json-20261021.csv` | 原 `vendors.csv` 及仓库内已缓存的 Wowhead sold-by 结构化数据 | NPC供货、原成本、库存、阵营与条件 | `--vendors-csv` |
| `T\_fc\inputs\vendors\npcs.csv` | `R\scripts\out\npcs.csv` | NPC名称、区域、坐标 | `--npcs-csv` |
| `T\_fc\inputs\vendors\npc-factions.json` | `scripts/update_vendor_factions.py` 对商人CSV全部NPC统一采集/重放 | NPC所属组织ID、三语名称与来源；独立于A/H/N | `--vendor-factions-json` |
| `T\_fc\inputs\vendors\faction-sources\` | 同入口冻结的完整原始NPC payload、客户端CSV/DB2及manifest、既有语言目录 | 随仓库保存的离线证据；逐文件哈希校验 | 生产入口 `--snapshot-dir`；生成器按JSON的 `sourceBundle` 定位 |

如果以后外部工具生成新CSV，可明确传入那份CSV。生产程序的存在、参数和运行状态都不是本流水线依赖。客户端三CSV必须属于同一已验证DB2批次；不能仅凭相同Build把不同热修复数据混合使用。

`vendors-soldby-json-20261021.csv` 重放现有图纸页面缓存中的 sold-by JSON，补回隐藏表格遗漏的供货记录、完整金币成本和通货条件；逐项修复及缓存源哈希保存在同目录的快照审计中。原 `vendors/vendors.csv` 和其余四份导入CSV继续作为只读历史证据，未改写。此修复只运行 `fc_prof_items.py` 合并现有商人、NPC与客户端价格输入，不发布完整目录或其他数据批次。

普通材料采购必须先取得独立的常规材料商人不限量、纯金币、可访问证据。新增材料链维护种子、NPC目录和完整货架，优先使用货架整组价及组数，缺金额时只在证据与组数均满足条件时回退客户端基础组价；不能仅凭根价判断可购买。固定19列 DataProfItems.csv 和原图纸采购输入保持不变；材料的配置、快照、失败降级、独立Lua与更新命令见 [MATERIAL_VENDORS.md](MATERIAL_VENDORS.md)。

## 各脚本实际读取的文件

表中“缓存”均为仓库内文件，不是游戏目录。上游来源是证据属性，不代表运行时要连接旧导出服务。

| 脚本 | 读取位置和文件 | 外部访问/补充说明 |
| --- | --- | --- |
| `P\prepare_workspace.py` | 仓库根现有正式运行文件 | 仅创建工具所需工作副本；目标已存在则拒绝，不覆盖正式数据 |
| `fc_update.py` | 本包 `fc_pipeline.py` | 唯一统一入口，默认检查，`--apply`才发布 |
| `fc_pipeline.py` | 上述5份CSV及NPC所属组织JSON；`T\_fc\data\*.json`；`T\_fc\i18n\*.json`；`T\_fc\maintenance\`下维护输入；当前 `R\Core\Data`、`R\Locales`、TOC作为保留及加载校验基线 | 只调本包Python步骤；无 `scripts/` 程序调用。`--offline`禁止网页请求 |
| `fc_pipeline_paths.py` | 无额外文件；根据脚本目录计算CSV默认路径 | 统一路径常量，不探测游戏/旧专业包/外部工具 |
| `fc_pipeline_common.py` | 当前Python可导入的 `lupa.lua51`（统一入口优先预载 `R\.pipeline-runtime\lib`）；待验证Lua/输入/输出；仓库锁与发布备份 | Lua 5.1必须可用。导入失败时仍有可选只读回退 `C:\Users\yewei\AppData\Local\Temp\df-lua-runtime`，不在该处安装或写文件。锁为 `T\_fc\cache\.pipeline-state\update.lock` |
| `fc_fetch.py` | `T\_fc\cache\professions.html`、`professions_<slug>.html`、`_meta.json` | 在线串行请求 `https://foreverchanges.pro/professions`及13个子页；离线只读缓存 |
| `fc_parse.py` | 同一组14个HTML | 解析为 `index.json`、`prof_*.json`、`item_ids.json`；统一入口写本轮暂存，不直接改正式输入 |
| `fc_zones.py` | 当前归一化index/prof JSON；`T\_fc\cache\areatable_classic.csv` | 缺缓存且在线时读取wago AreaTable；离线缺表明确失败。代理可用 `DF_PIPELINE_PROXY` 配置 |
| `fc_fields.py` | 本轮归一化JSON；生成器字段声明；`T\tools\tf_dryrun.py`、`wow_stub.lua` | 统一链使用 `--strict --source-only`，最后另做真实Lua/三语发射校验；不跳过缺失关键依赖 |
| `fc_i18n.py` | 本轮归一化JSON、`T\_fc\i18n\zh.json`；`--add/--batch`时另读取人工提供的词表内容/批次文件 | `--audit`只对账，缺译不自动联网翻译 |
| `fc_gen.py` | `index.json`、`prof_*.json`、`enchant_ids.json`、`vendor_loc.json`、可选 `vendor_side.json`、`drop_loc.json`、`zone_ids.json`、`zone_zh.json`；`zh.json`；`T\questie\questie_forever.json`；`T\_wago_AreaTable_zh.csv`；专业维护输入 | 支持文件优先取冻结暂存目录，否则取本包默认路径；无游戏/旧专业目录回退 |
| `fc_maintenance.py` | `T\_fc\maintenance\professions.json`及其版本化维护记录/源文件 | 三方冲突检查、人工新增、阈值/来源修订、字段及分片省略、顺序与计数；一次性迁移参数 `--migrate-from` 才读取显式旧Lua目录 |
| `fc_prof_items.py` | `vendors.csv`、`npcs.csv`、`item-buy-prices.csv`、默认NPC所属组织JSON；本轮生成的Data_ProfVendors.lua | 在内存合并，统一链使用同轮商人数据，并单独保留客户端物品基础整组价格；`--from-csv`只读指定19列DataProfItems.csv，跳过三表合并，所属JSON仍独立读取并生成 `ns.ProfVendorFactions` |
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
| `fc_package.py` | `R\DungeonsForever.toc`递归XML引用、`LICENSE`、Media资源以及完整专业批次验证后的21份专业Lua | 只生成安装ZIP；原运行文件按原字节收入，其余工具/缓存/报告不打包 |
| `fc_path_audit.py` | 当前流水线、相关工具、测试与说明中的脚本文本 | 静态读取路径，区分活动/历史/外部支持工具；不会执行它们 |

## 配方学习途径与图纸出处如何取得

制作产物、制作法术、教授法术的图纸物品是三种不同身份。目录中存在 `formula` 只能说明关联了一张图纸；客户端教学链只能证明该物品可以教授该法术，两者都不能证明必须购买图纸，也不能排除训练师教授。

| 信息 | 原始证据与处理方式 | 当前使用位置 |
| --- | --- | --- |
| 配方目录、图纸ID及部分掉落/商人文字 | `fc_fetch.py` 缓存 `foreverchanges.pro/professions` 及各专业子页；`fc_parse.py` 读取 RSC 中的 `formula`、`source.drops/vendors` | 主配方 `Data_ProfRecipes.lua` |
| 训练师教授 | `fc_specialization_fetch.py` 读取 Wowhead Forever 技能页配方的 `source` 含 `6`；部分情况补查法术页 `taught-by-npc` | `Data_ProfSpecializations.lua` 的训练途径及 `trainerObserved` |
| 图纸掉落/商人缺口 | `fc_gen.py` 按图纸ID查询保存的 QuestieDB-Forever `item_npcDrops/item_vendors`，只补缺失，不覆盖已有数据；没有掉率或价格时不补造 | 主配方 `source.drops/vendors` |
| 图纸商人报价、通货、阵营、库存 | 独立 `scripts/gen_vendors.py` 采集 Wowhead 图纸物品页 Sold by JSON；统一入口只读已导入的版本化商人 CSV 与 NPC CSV | `fc_prof_items.py` 生成 `Data_ProfItems.lua` 的 NPC 报价；显示与金币采购接口分开 |
| NPC所属组织 | 独立 `scripts/update_vendor_factions.py` 自动遍历商人CSV全部NPC，合并明确tooltip所属与客户端精确ID/名称；统一入口只读已安装的JSON及完整证据快照 | `Data_ProfItems.lua` 中 `ns.ProfVendorFactions`；显示所属，不改变A/H/N访问判定 |
| 图纸教学关系和学习专精要求 | 独立客户端导出器根据 Item → ItemXItemEffect → ItemEffect 等明确教学链生成图纸 CSV；`RequiredAbility` 与教学来源分别记录 | `fc_prof_specializations.py` 合并为独立学习途径 |
| 任务图纸 | `Data_ProfFormulaQuests.lua` 的九项明确任务配置，运行时合并；不是完整任务目录 | 图纸任务来源与采购限制 |
| NPC 名称、区域、坐标 | 目录资料、保存的 Questie/NPC 定位输入及 `npcs.csv`；客户端与已核验语言资料用于显示回退 | 优先本地化名字，缺译名显示已有原名，确实无名才显示 NPC 编号；缺坐标不补造 |
| 人工来源修订 | `_fc/maintenance/professions.json` 及版本化维护输入，经三方冲突核对后保留新增、修正、顺序和省略规则 | 主配方与语言发布 |
| 辅助配方目录 | `fc_recipe_catalog_fetch.py` 缓存 `wuxianwow.com/data/recipes.json`，用于交叉核对、关联及未映射审计 | 辅助证据；不凭名称或目录命中推定训练师、唯一图纸途径或精确 Build |
| 当前角色实际观测 | 客户端训练师接口的正观察保存为 `ProfRecipeRuntime[spell].trainerObserved`；已学、暂未加载及明确不可用分别处理 | 运行时解析及可用性检查 |

当前 `ProfEconomy.LearningSource` 统一使用正证据：明确观察到训练师教授时，界面按训练师显示，采购不再强制购买关联图纸。训练师途径中专精条件仍为 `pending` 不会抹掉 `trainerObserved=true`；专精要求、客户端明确不可用及用户排除继续独立检查。原始图纸ID与出处不删除，仍可审计。

无图纸字段不等于已有训练师证据；来源为空可能只是未记录。旧界面对无图纸条目的训练师兜底不能作为采集证据，`ProfLeveling.learn` 名单也不能据此推定训练师。来源覆盖并不完整，缺失训练师 NPC 名单、掉率、坐标、通货名称或精确来源 Build 时均不能补造。

图纸/产物拍卖行情另由 Auctionator 集成读取，用于价格显示和采购比较；它不建立训练师教授或图纸掉落关系。

图纸商人默认按 `UnitFactionGroup("player")` 的当前角色阵营过滤；明确异方专属的商人被隐藏，中立与阵营未知者保留。阵营未知仍显示未知，不当作已经证实中立；显式角色/访问上下文可进一步限制显示或采购。缺译名与阵营缺失是独立字段，名字回退不改变原价格、通货、库存或阵营。

NPC所属组织的可重现操作见 [`scripts/VENDOR_FACTIONS.md`](../scripts/VENDOR_FACTIONS.md)。干净检出在仓库根执行 `python -B scripts/update_vendor_factions.py --offline`，不依赖浏览器、本机缓存或旧 `.pipeline-runtime`。联网更新使用 `--collect --proxy= --client-dir scripts/out/npc-faction-client`；加 `--install-input` 只事务安装 JSON、审计和证据，Lua仍经正常 `fc_prof_items.py` / `fc_update.py --apply` 发布。更新商人CSV后重新采集会自动包含新增NPC；离线目标集合不匹配或证据哈希/ID冲突明确失败，保持旧结果。

2026-10-21 全量覆盖289名商人，242名有ID及三语名，47名无明确所属；缺payload、冲突和采集错误均为0。完整 `faction-sources/` 原始字节及manifest随仓库保存。默认不再使用只含Gorhak/Molkar的 `npc-factions-20261021.json` 或一次性脚本；它们仅作历史记录。SoldBy缺 `react` 不补中立，商品声望要求不反推NPC所属；固定19列CSV、价格、库存、坐标、`side`和原五份CSV不变。WoWDBDefs只说明结构，70450名称解码不证明存在NPC关联；运行时客户端阵营名称API仍优先。

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

去掉 `--offline` 时只允许网页联网更新，CSV与DB2仍是只读现成输入。完整专业检查的 `--stage-dir` 保留规范JSON、有效目录、CSV、审计与21份Lua候选及输入哈希；ZIP使用这些新Lua，其他运行模块保持原字节。两者都不能与 `--apply` 合用。

普通完整检查不加 `--stage-dir/--package-zip` 时只产生仓库内缓存、暂存和报告。规范JSON、派生CSV、Lua及成功指针要等明确执行 `--apply` 才事务发布；外部生产的5份输入CSV始终只读，发布也不覆盖它们。

## 工作副本与派生 CSV

`DataProfItems.csv` 是可重建的合并结果，不再随 Git 保存。首次需要时在仓库根依次执行：

```powershell
python -B df-data-pipeline/prepare_workspace.py
python -B df-data-pipeline/_temp/fc_prof_items.py
python -B df-data-pipeline/_temp/fc_update.py --from-csv df-data-pipeline/_temp/_fc/data/DataProfItems.csv --check
```

第一步仅创建不存在的工具工作副本；已有工作副本时省略该步。第二步从冻结输入生成合并 CSV，并更新 `P\Core\Data` 下的物品与商人样例；第三步只检查物品 Lua，三步均不改 `R\Core\Data`。原始客户端与商人 CSV、维护 JSON、训练师证据及规范输入仍是需要保留的来源，不能按派生 CSV 一并删除。

旧专业包、迁移归档及一次性迁移核对工具已移除，过去的原件核对结果仅属历史验收。当前读取与校验已生成客户端 CSV、物品/商人/专精/网页证据及审计功能均保留；外部自动导出服务仍不由统一入口启动。

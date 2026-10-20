# 统一专业数据流水线

唯一维护入口为 `_temp/fc_update.py`，以当前仓库定位输入和正式 `Core/Data`，不依赖启动目录。
`df-prof-pipeline-v1.0` 已留档停用，不是默认输入或缓存来源。
各脚本要读取的位置和文件见 [SCRIPT_INPUTS.md](SCRIPT_INPUTS.md)，旧专业包功能及249份原件的覆盖核对见 [LEGACY_PARITY.md](LEGACY_PARITY.md)。
人工维护的记录、字段差异和新增项前后位置见 [MANUAL_MAINTENANCE.md](MANUAL_MAINTENANCE.md)。
2026-10-21已将70450数据发布到当前仓库，使用当前1.8.33代码及材料价格规则；发布验收与最新安装包见 [PUBLISH_70450.md](PUBLISH_70450.md)。此前仅检查的记录保留在 [CSV_CHECK_REPORT.md](CSV_CHECK_REPORT.md)。

## 使用

从仓库根目录运行：

```powershell
python -B df-data-pipeline/_temp/fc_update.py --check --offline
python -B df-data-pipeline/_temp/fc_update.py --apply --offline
python -B df-data-pipeline/_temp/fc_update.py --specializations-only --check --offline
python -B df-data-pipeline/_temp/fc_update.py --from-csv df-data-pipeline/_temp/_fc/data/DataProfItems.csv --check
```

不带模式参数默认为检查；`--apply` 才发布。`--offline` 禁止网页、DB2 和热修复网络请求，缺缓存或成功快照就失败，不能偷偷改为联网。
也可使用 `df-data-pipeline/run.bat` 传入相同参数。路径参数相对于调用目录；未指定参数的默认路径始终根据脚本定位。

客户端与商人/NPC的五份旧CSV已按原字节导入 `_temp/_fc/inputs/`，路径常量集中在 `fc_pipeline_paths.py`；来源哈希在 `inputs/manifest.json`。默认运行不再依赖 `scripts/` 目录，不导入、监控或调用其中的程序，也不会启动 wow.tools.local。显式CSV参数仍可读取外部工具生成在仓库内的CSV。

只生成经校验的新批次与安装ZIP，不发布正式数据：

```powershell
python -B df-data-pipeline/_temp/fc_update.py --check --offline `
  --stage-dir .pipeline-runtime/review/validated-batch `
  --package-zip dist/DungeonsForever-1.8.33-data-70450-preview.zip
```

两个目标都必须不存在。ZIP将本轮20份专业Lua覆盖进安装包，其余运行文件保持原字节；工具、报告及缓存不打包。`--stage-dir/--package-zip`不能与`--apply`合用，不改游戏安装目录。

依赖是 Python 3.10+、`lupa.lua51` 和 OpenCC。可将 `requirements.txt` 安装到仓库忽略目录 `.pipeline-runtime/lib`；统一入口自动加载该目录。不同 Python 版本应安装对应的 Lupa wheel，不共用不匹配的二进制模块。

```powershell
$env:PIP_CACHE_DIR = "$PWD/.pipeline-runtime/pip-cache"
$env:TEMP = "$PWD/.pipeline-runtime/tmp"
$env:TMP = $env:TEMP
python -B -m pip install --target .pipeline-runtime/lib -r df-data-pipeline/requirements.txt
python -B tests/run_tests.py
```

安装前创建上述仓库内临时目录。关键依赖缺失时退出，Lua 发射校验不会被跳过。

## 生成链与发布范围

冻结输入 → 网页抓取或离线重放 → 解析/区域映射/字段和文案审计 → 当前专业维护修订 → 基础数据 → 客户端与专精审计 → 物品 CSV/购买资料及商人定位 → zhTW/enUS → Lua/完整记录/TOC 校验 → 一次事务发布。

- 基础六份：Professions、ProfRecipes、ProfLeveling、ProfGathering、ProfVendors、ProfTrainers。
- 同步生成这六份的 zhTW 和 enUS 副本，保留语言守卫及现有人工翻译。
- Items、Specializations 是共享文件，不作通用翻译。物品表保持三语原名、固定19列CSV与schema 2；专精继续保留学习途径、未知状态、目标与来源版本、网页冷却和审计。
- 现有任务、采矿、钓鱼扩展及所有未接管文件不覆盖、不删除，不更改业务模块、UI文案、TOC顺序或存档。
- 规范化输入、有效证据目录、合并CSV、审计、共享数据和三语Lua同批发布。仅数据确实改变才替换，重复运行不因生成时间更新文件。

`--specializations-only` 保留独立专精更新范围。`--from-csv` 只重建物品Lua，不重写CSV、商人、专业或语言数据。原输入/刷新/版本/缓存选项由 `--help` 列出；所有写入位置必须在当前仓库。

## 当前数据与维护输入

当前正式专业总表与规范JSON均为70450（网页资料日期2026-10-16），保留70338基线中的新增、修订与显式省略规则；旧70245输入另在版本化冻结模型中保留，用于精确旧批次重放。`_temp/_fc/maintenance/professions.json` 将维护差异保存为稳定身份的原值/修订值/来源，涵盖配方、附魔、毒药与理解、阈值、来源、顺序及手工训练师/区域输入。日常生成不读取旧Lua回捞手工段。

2026-10-21新增revision2接通最新网页70450（站点日期2026-10-16），10项维护冲突经逐项rebase处理；revision1只对精确旧输入使用归档词表继续复现70338。64项已被上游追平的人工字段仍保留第三值守卫。炼金配方1251750/250952按用户确认跟随上游删除，授权记录精确限定；其余人工增补、阈值、来源、省略及相对顺序保留，计数按实际记录重算。版本化源文件与审计在 `_fc/maintenance/source/rebase-2-70450/`。用户确认发布后，已通过统一入口离线事务写入正式目录。

`locales.json` 保存专业人工译文、原文哈希和历史源文版本。附魔以原始名称识别，BIS按职业/专精识别，避免名单移位套错译文。本轮补齐2项新增缺译、审订7处源文的14份英繁译文；既有29项缺译仍单独报告。其他原文变化继续阻止生成，已有记录缺失也会阻止发布，唯一例外是维护文件记录的精确用户批准删除。

`_fc/data/catalog/` 是同批发布的有效专精证据目录：保留原始证据目录，追加维护后的新增配方与明确ID证据；UI省略不删除原始证据。无ID卷轴保持未确认。
人工毒药/理解分片继续标记真实70338来源并绑定冻结维护文件哈希，不随本轮目标70450重标；未知来源版本留空。

历史 wx/补丁资料仅作为迁移来源；一次性维护提取工具在 `fc_maintenance.py`，不应作为日常更新步骤。重新迁移会改变保留基线，必须检查差异及测试。

## 缓存、事务与路径

- 单一仓库锁串行更新；先生成到仓库内暂存区，最终复核全部输入与目标哈希再发布。冲突和任何步骤失败不发布正式批次。
- 发布失败补偿回滚；恢复材料保留在 `.implementation-backup/pipeline-publish-*`，回滚失败信息会给出该目录。不会清理或部署到游戏安装目录。
- 检查/失败运行可更新忽略的页面缓存、不可变DB2快照、冷却和报告，不发布规范输入/CSV/Lua/成功指针。
- `fc_path_audit.py` 只读扫描固定路径引用，报告 `_fc/reports/path-audit.json`，区分活动链、历史工具、停用专业包和支持脚本；不执行历史同步/部署工具。
- 正式输出、日志、缓存、DB2归档和链接解析后的目标全部限制仓库。拒绝覆盖非受管业务代码、维护输入及不同产物路径碰撞。

在线模式只刷新网页，客户端三CSV和DB2仍复用同一已验证快照，不调用外部导出器。可用 `--db2-dir` 指定仓库内快照，否则按已有current及内容哈希选择；缺少或混批在请求网页前失败。已移除 `--tool-directory`、`--base-url`、`--powershell`。网页代理可用 `DF_PIPELINE_PROXY` 设置。

```powershell
python -B df-data-pipeline/_temp/fc_update.py --check
python -B df-data-pipeline/_temp/fc_path_audit.py
python -B df-data-pipeline/_temp/fc_legacy_audit.py
```

## 其他数据工具

本次统一只接管专业六表与对应三语。职业任务、副本路线、装备、BIS、职业指南等工具和输入仍保留，索引见 `INDEX.md`。这些历史工具可能含旧路径或依赖，不属于统一入口，勿将历史 `sync_beta.py`、`mk_df_*` 或全目录语言通配生成串回当前流程。旧说明保存在 `HISTORICAL_README.md`。

## 首次迁移验收（历史）

2026-10-21：完整842项测试通过，无跳过，含真实打包、事务回滚/恢复、锁与链接边界。统一入口在不同中文/空格工作目录成功离线发布，重复发布零变更且mtime不变；136份未接管运行文件哈希不变。独立专精与CSV检查通过。验收记录在仓库忽略目录 `.implementation-backup/20261021-unified-pipeline/acceptance.json`，本轮未联网刷新、未写游戏安装目录。

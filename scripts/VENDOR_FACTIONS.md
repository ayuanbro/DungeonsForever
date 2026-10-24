# 全商人所属阵营更新

`update_vendor_factions.py` 从默认 `df-data-pipeline/_temp/_fc/inputs/vendors/vendors-soldby-json-20261021.csv` 自动提取全部不同 `npc_id`，合并明确的 NPC tooltip 所属与客户端 Faction 证据。没有 NPC ID 白名单，也不按角色联盟/部落筛掉采集目标。所属声望阵营与商人 A/H/N 访问限制是两个字段。

默认商人路径读取统一配置 `fc_pipeline_paths.CSV_INPUTS`，刷新器不重复固定某一版CSV；更换商人输入角色后，默认目标集合随配置更新，也可传 `--vendors-csv`。

## 干净检出离线重放

在仓库根执行，使用 Python 标准库，不需要浏览器、服务或本机旧缓存：

```powershell
python -B scripts/update_vendor_factions.py --offline
```

默认读取已纳入版本管理的 `df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/`，输出 `scripts/out/vendor-factions/npc-factions.json`、`audit.json` 及证据副本。省略模式参数也采用离线重放。相同冻结输入产生相同 JSON、审计及复制文件字节；运行目录不影响默认路径，显式相对参数则相对于调用目录。

快照含原始 `vendors.csv`、每名 NPC 的原始 Nether JSON、客户端 CSV/原始DB2/manifest，以及按确认 Faction ID 使用的语言目录。外层 manifest 校验每个文件的 SHA-256/长度，客户端子 manifest 再校验客户端所有声明文件；目标 NPC 集合必须与当前商人CSV一致。离线时不会缺缓存转联网，也不依赖旧 `.pipeline-runtime`。

## 在线刷新与安装输入

先用[独立客户端导出器](export_npc_factions/README.md)生成仓库内 `scripts/out/npc-faction-client/`。该目录应含 `factions.csv`、`npc-factions.csv`、原始证据和 manifest；原始 Faction DB2 解码只有名称，没有 NPC 关联，允许只有表头的关联CSV。

```powershell
python -B scripts/update_vendor_factions.py --collect --proxy= --client-dir scripts/out/npc-faction-client --install-input
```

`--collect` 获取当前商人CSV全部NPC的缺失/过期原始payload，默认缓存期限7天；`--refresh`强制刷新，`--max-age 0`不按年龄失效。`--proxy=`明确直连；需要本地代理时给出有效地址，工具不会偷偷切换代理。新NPC进入商人CSV后，下次采集自动包含；本入口不重新抓取物品SoldBy或修改供货CSV。

`--capture-cache`可冻结已有缓存而完全禁止HTTP；缺失记录进入覆盖审计，错误记录阻止替换成功结果。存在无法由客户端关联补齐的缺失payload时，`--install-input`拒绝替换正式输入，避免不完整缓存抹去已有所属；有效payload明确未提供所属则保留未知。`--cache-dir`、`--client-dir`、`--snapshot-dir`、`--output-dir`和`--vendors-csv`均可明确指定，但必须位于当前仓库。`--locales enUS,zhCN,zhTW`可另采语言payload；默认英文，确认ID后可使用客户端名称和已有语言目录。

`--install-input`只事务安装以下 JSON、审计与冻结快照，并更新输入manifest；不会写游戏目录、生成Lua、改价格或坐标：

- `df-data-pipeline/_temp/_fc/inputs/vendors/npc-factions.json`
- `df-data-pipeline/_temp/_fc/inputs/vendors/npc-factions-audit.json`
- `df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/`

原始五份CSV和固定19列 `DataProfItems.csv`保持不变。解析/ID冲突、采集错误、输入并发变化或安装失败时保留上次成功JSON；冲突或采集错误另写审计。成功输出及安装使用同一发布事务。旧 `npc-factions-20261021.json` 的两NPC快照仅作历史证据，不再是默认输入；旧 `.pipeline-runtime/vendor-factions-20261021/collect_and_publish.py` 也不是更新入口。

## 生成插件数据

正常专业流水线默认读取新JSON及其完整证据快照。合并 CSV 和工具样例不再跟踪；首次使用 `--from-csv` 时先准备工具工作副本并从冻结的三份 CSV 生成合并结果：

```powershell
python -B df-data-pipeline/prepare_workspace.py
python -B df-data-pipeline/_temp/fc_prof_items.py
```

准备脚本将正式 `Core/Data` 复制到工具包；目标目录已存在则拒绝，已有工作副本时省略准备命令。接着可只重建工具工作副本中的物品 Lua：

```powershell
python -B df-data-pipeline/_temp/fc_prof_items.py --from-csv df-data-pipeline/_temp/_fc/data/DataProfItems.csv --dry-run
python -B df-data-pipeline/_temp/fc_prof_items.py --from-csv df-data-pipeline/_temp/_fc/data/DataProfItems.csv
```

上述命令默认只写工具包中的样例和派生 CSV，不改仓库根的正式 `Core/Data`。统一检查与发布继续使用 `fc_update.py --offline` / `fc_update.py --offline --apply`。两入口均支持 `--vendor-factions-json <仓库内JSON>`覆盖默认输入。`ns.ProfVendorFactions`是独立元数据，不向报价CSV增加列，也不把所属变成供货、声望门槛或中立访问资格。

## 当前覆盖与证据边界

2026-10-21的输入含1,658条供货行、859件物品、289名不同商人；289份英文payload均有效。242名得到明确Faction ID及enUS/zhCN/zhTW名称，47名无明确所属，缺payload、冲突、采集错误均为0。两次从不同工作目录离线重放，299个输出文件同字节。这是当前快照覆盖，不保证未来新增NPC均有数据。

原始客户端 Faction 解码提供253条可读英文名称；名称与ID只能按精确匹配关联，语言目录只按已确认ID补名，运行时客户端名称API仍优先。WoWDBDefs提供结构定义，不提供NPC数据；当前70450名称解码没有可用目标NPC关联，不能凭空补出。

Gorhak253139所属93、Molkar253140所属92可由通用tooltip解析和客户端精确名称对照重新得到，不需要专门ID分支。Pexmit、Dala Fairmaw、Repair Bot、Qujo仍无明确所属。SoldBy缺`react`不等于中立；NPC名字、称号、怪物类型、商品声望条件都不能替代明确所属证据。未知和冲突在审计中保留，绝不补造中立。

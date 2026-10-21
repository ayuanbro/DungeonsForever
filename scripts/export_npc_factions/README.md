# NPC 所属阵营独立导出

这套工具只提供客户端 NPC **所属声望阵营**证据，与 `gen_vendors.py` 和正式专业生成入口分离。不会生成 Lua、推断联盟/部落/中立、改商人价格或启动 wow.tools.local。所有输出必须留在当前 Git 仓库；输出目录必须不存在，已有快照不覆盖。

## 已解包 Faction 名称

从已有原始 DB2 读取全部可读 Faction 名称，包含复制记录，不含 NPC 关联：

```powershell
python -B scripts/export_npc_factions/decode_faction_names.py `
  --input .pipeline-runtime/wow.tools.local/dbcs/1.60.1.70450/dbfilesclient/faction.db2 `
  --output-dir scripts/out/npc-faction-client `
  --build 1.60.1.70450
```

`--input`、`--output-dir` 相对当前工作目录。解码器只接受已核对的 WDC5 Faction 表 `06F624D7`、布局 `6D443C38`、非稀疏外置 ID 和未压缩首列名称偏移；其他布局直接报错。读取所有可读行及 copy ID，不含任何特定 NPC 或 Faction ID 名单；无法解密的 section 与未能解析的复制关系记入 manifest。

输出 `factions.csv`、只有表头的 `npc-factions.csv`、原始 DB2 副本和 `manifest.json`。名称只写实际语言对应的列，其余留空。DB2 locale mask 精确为 `1/16/32` 时分别确认 enUS/zhCN/zhTW；这与 CASC root 的 locale bit 位置不同。

这里的 `--build` 是外部提供的版本标签，只核对 DB2 `schemaString` 的版本族；原始 WDC5 不携带完整 build 号，不能据此称该 build 已完整验证。此入口只读取 **base DB2**，没有应用 Hotfix、没有 NPC 关联，也不代表完成了一次客户端数据更新。2026-10-21 当前 70450 原始 Faction 实读为 enUS，253 条（252 原始 ID 加1条复制 ID），中文列为空。

## 已运行 WTL 服务

Windows PowerShell 5.1，无 Python 依赖。相对路径以本脚本目录为基准；从任意工作目录调用建议传绝对路径：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/export_npc_factions/export-npc-factions.ps1 `
  -Build 1.60.1.70450 `
  -BaseUrl http://127.0.0.1:5000 `
  -NpcCsvPath C:\path\to\repository\scripts\out\npcs.csv `
  -HotfixCachePath C:\path\to\repository\.pipeline-runtime\wow.tools.local\caches\DBCache.bin `
  -OutputDirectory C:\path\to\repository\scripts\out\npc-factions-new
```

`BaseUrl` 仅接受 loopback HTTP origin。操作者应先在 WTL 加载正确客户端及对应 Hotfix；脚本不启动服务、不下载、不重载缓存。不应用 Hotfix 的明确检查场景用 `-WithoutHotfixes`，与 `-HotfixCachePath` 二选一。

脚本先后两次检查 `casc/buildname`，必须精确等于 `-Build`，并检测 `dbc/header/{table}?build=...` 的必需字段和外键。所有 CSV 串行经 `dbc/export/?name=...&build=...&useHotfixes=...&newLinesInStrings=true&locale=...` 取得。

需要的字段：

| 表 | 字段 |
| --- | --- |
| CreatureDifficulty | ID、CreatureID、FactionTemplateID |
| FactionTemplate | ID、Faction（外键 Faction::ID） |
| Faction | ID、Name_lang |

Faction 分别读取 enUS/zhCN/zhTW CSV，并保存同语言 `dbc/export/db2?tableName=faction&fullBuild=...&locale=...` 原始响应。只有其 DB2 locale mask 精确符合语言，才将该语言的 CSV 名称写入输出。WTL 磁盘回退可能忽略请求语言；这时原始 CSV 仍保留供审计，未证实名称列为空，不能把英文副本冒充中文。API/必需字段不支持、类型非法或重复原始 ID 时整批失败，不发布目标目录。

提供 Hotfix 时验证缓存的 `XFTH` 标记、内嵌 build 与目标一致，复制原字节并记录 SHA256，同时请求 `useHotfixes=true`。当前 WTL API 不提供“此确切缓存 SHA 已应用”的证明，因此 manifest 明确 `serverAttested=false`；保留的是指定缓存身份与请求证据，不把它说成服务器完成了独立的应用证明。不要在导出期间切换客户端、语言或重载缓存。

## CSV 契约与缺口

- `factions.csv`：`ID,Name_enUS,Name_zhCN,Name_zhTW`，只填实际证实的语言。
- `npc-factions.csv`：`npc_id,faction_id,status,faction_template_ids,creature_difficulty_ids`，每 NPC 一行，ID 列表去重后按数值排序，以分号连接。
- `report.json`：逐 NPC 候选关联记录、缺口及冲突，三语验证状态和计数。
- `manifest.json`：版本与 Hotfix 证据、请求 URL、原始 CSV/表头/DB2，`files:{relative:{sha256,bytes}}` 覆盖所有 raw 与派生 CSV/report（不含 manifest 自身）。

同 NPC 多条 CreatureDifficulty 都解析到同一正 Faction ID 且存在 Faction 记录，才是 `resolved`；不同模板可以指向同一 Faction。模板缺失为 `missing-template`，Faction 记录缺失为 `missing-faction`，不同 Faction 或正值与零值并存为 `conflict`。没有观察到 CreatureDifficulty、只有零模板/零 Faction 时为 `no-faction`。所有未解决状态的 `faction_id` 为空，原始链仍在 report 中。`no-faction` 是这批输入未提供所属阵营，不证明服务器 NPC 没有阵营。部分已解析、部分链缺失时也不擅自选择已知分支。

`-NpcCsvPath` 可读取 `npc_id`、`NPCID` 或 `ID` 列，用于完整报告目标 NPC 中未覆盖的记录。省略时处理 CreatureDifficulty 中所有 NPC；没有行则只输出表头。它不筛选 NPC 名称、职业或特定 ID。

## 冻结重放

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/export_npc_factions/export-npc-factions.ps1 `
  -Build 1.60.1.70450 `
  -InputSnapshotPath C:\path\to\repository\scripts\out\npc-factions-new `
  -OutputDirectory C:\path\to\repository\scripts\out\npc-factions-replayed
```

离线模式不发 HTTP。读取本 PS1 产生的 manifest，校验文件 SHA/字节数、表头、外键、build、Hotfix 与语言证据，重放相同 NPC 目标集；CSV 内容可逐字节比较。原始 DB2 名称解码器的局部输入缺少两张关联表，不能充当 PS1 的完整关联快照。

```powershell
python -B tests/test_npc_faction_export.py
```

测试使用内存模拟 HTTP 服务、冻结 CSV 和紧凑 WDC5，覆盖多模板同阵营、缺失、冲突、零值、跨语言回退、CSV 引号/换行、重放/篡改、版本与 Hotfix 身份，另有真实本地 DB2 导出记录。它们不证明游戏内实时数据或客户端 API 行为。

格式依据：[WoWDBDefs Faction](https://github.com/wowdev/WoWDBDefs/blob/master/definitions/Faction.dbd)、[CreatureDifficulty](https://github.com/wowdev/WoWDBDefs/blob/master/definitions/CreatureDifficulty.dbd)、[WTL ExportController](https://github.com/Marlamin/wow.tools.local/blob/main/Controllers/DBC/ExportController.cs)、[DBCD WDC5Reader](https://github.com/wowdev/DBCD/blob/master/DBCD.IO/Readers/WDC5Reader.cs)。DB2 locale 与 CASC 位掩码差异参考 [TrinityCore Common.h](https://github.com/TrinityCore/TrinityCore/blob/master/src/common/Common.h) 和 [DB2FileLoader](https://github.com/TrinityCore/TrinityCore/blob/master/src/common/DataStores/DB2FileLoader.cpp)。

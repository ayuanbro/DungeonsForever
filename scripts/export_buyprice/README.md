# Forever 物品、三语基础购买价及图纸学习要求 CSV 导出

从仓库根目录运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\export_buyprice\export-item-buy-prices.ps1"
```

从其他目录启动时使用脚本绝对路径。兼容 Windows PowerShell 5.1，无需安装 Python。默认使用 `C:\Users\yewei\Downloads\Release-win-x64\wow.tools.local.exe` 和 `http://127.0.0.1:5000`：服务已启动则复用，未启动则隐藏启动；结束时只关闭本次启动的进程。

## 输出

文件写入脚本旁的 `output/`，均使用 UTF-8 BOM：

| 文件 | 内容 |
| --- | --- |
| `item.csv` | 当前 Item 表的完整字段与记录，包括 `ID`、`ClassID`、`SubclassID`；保持工具返回的原始列，供上层 `gen_vendors.py` 筛选配方物品 |
| `item-buy-prices.csv` | 合并 enUS、zhTW、zhCN 名称及 ItemSparse 的原始基础购买价、组数、状态和版本 |
| `recipe-item-specializations.csv` | 仅 `Item.ClassID=9` 图纸的物品 ID、实际所教配方 spellID、图纸 `RequiredAbility`、学习路径和来源版本 |

三语价格表字段：

```text
ItemID,Name_enUS,Name_zhTW,Name_zhCN,BuyPriceCopper,VendorStackCount,PriceStatus,Build,HotfixBuild
```

`BuyPriceCopper` 保留数据库整组购买价，不除以 `VendorStackCount`。`PriceStatus` 区分 `priced`、`zero`、`missing_item_sparse`；缺少数据的数值留空。缺少某种语言名称时留空，不用英文替换。价格为零不表示免费，基础价也不证明任何 NPC 实际出售、无限量供应或角色折扣。

图纸表字段：

```text
RecipeItemID,RecipeSpellID,RequiredAbility,Status,Reason,LearningPath,Build,HotfixBuild,Source
```

脚本读取 `ItemXItemEffect.ItemID → ItemEffectID`，也兼容 `ItemEffect.ParentItemID` 布局。`TriggerType=6` 可直接给出所教 spell；其他使用 spell 只沿明确的 `SpellEffect.Effect=36` 且 `EffectTriggerSpell>0`、或 `SpellLearnSpell.SpellID → LearnSpellID` 追踪。`LearningPath` 保留表名、记录 ID、字段和值，同一目标的多条路径用 ` | ` 分隔。

目标通常须属于 `SkillLineAbility` 中的专业或 `SkillLine.ParentSkillLineID` 的子专业，并排除技能等级效果 44/118。这些字段仅验证目标是否属于专业配方范围，工程学 `SkillLine=202`、子专业或分类本身不能证明地精/侏儒专精；通用学习法术（如 402265）不会作为配方输出。只记录图纸的 `ItemSparse.RequiredAbility`，不把成品的穿戴/使用要求传播给配方，也不按名称猜测。

少数明确教学目标缺少 `SkillLineAbility`。这时仅在图纸 `ItemSparse.RequiredSkill` 属于专业父/子系，且目标存在创建物品效果 `24`（`EffectItemType>0`）或附魔效果 `53/54`（`EffectMiscValue[0]>0`），并且没有技能等级效果或任何非专业 SkillLine 记录时，补充所教配方 ID。`LearningPath` 同时记录 RequiredSkill 和具体 SpellEffect 记录证据。相关可选字段缺失时不补；制作效果、tradeskill 属性或物品分类单独都不够。`SubclassID=0` 书籍同样按明确教学和专业证据判断，不直接排除。`TriggerType=1` 等非学习触发仍须有明确学习链，不能因目标是制作法术便视为教学。

`Status=confirmed` 表示图纸有唯一、明确的学习目标且 `RequiredAbility>0`，证明的是这条图纸学习途径的前置 spell 要求。`pending` 表示“待确认”：`RequiredAbility=0` 原样保留，缺少字段或记录则留空；都不表示通用。未解析到目标时 `RecipeSpellID` 留空；多个目标分别保留候选行并标记 `ambiguous_recipe_spells`；循环、断链和遍历上限也保留原因。图纸途径不能证明训练师的学习条件，训练师证据由 pipeline 的独立生成器处理。

脚本只输出 CSV，不生成 Lua，不导入插件或写入游戏安装目录。插件中的旧 NPC 购买价格已删除，当前仅保留供货/位置/库存性质等非价格资料，等待重新设计购买价格方法；商人窗口不采价，Auctionator 的 AH 行情与数量继续保留。

## 数据校验与运行规则

每次读取本机当前加载的 Forever build，下载最新 `classic_beta` Hotfix，并核验本次新缓存的文件头、版本及 SHA-256。下载失败、没有新缓存、损坏或 build 不匹配时停止，不使用旧缓存冒充成功。

重载 Hotfix 后只导出一次 Item，再依次读取 enUS、zhTW、zhCN 的 ItemSparse，以及 enUS 的 ItemEffect、ItemXItemEffect、SpellEffect、SpellLearnSpell、SkillLineAbility、SkillLine。所有请求串行，显式指定 build、locale 与 `useHotfixes=true`；三语价格、组数以及图纸 RequiredAbility/RequiredSkill 必须一致。缺少必需表或链接字段时停止；有效的只有表头的学习表可以为空。

三个输出都验证成功且版本/缓存未变才发布；后续文件发布失败时回滚之前的文件，保留旧输出。单文件替换为原子操作，三个文件之间使用补偿回滚。回滚若被操作系统阻止，会报错并保留备份供恢复。三个输出路径不得互为大小写别名、目录链接别名或硬链接；输出 mutex 同时保护路径和已有文件标识。

导出期间避免在 wow.tools.local 页面切换版本或手动重载缓存。不同缓存按 Hotfix PushID 合并，下载文件不等同于完全独立的数据库快照。控制台和 `output/logs/` 记录版本、缓存哈希、行数及名称缺失数量。输出和日志不进入 Git；同一服务或输出文件的并发导出会被阻止。

## 参数

所有相对路径均相对于脚本目录，不受当前工作目录影响：

```powershell
.\scripts\export_buyprice\export-item-buy-prices.ps1 `
  -ToolDirectory 'C:\Users\yewei\Downloads\Release-win-x64' `
  -BaseUrl 'http://127.0.0.1:5000' `
  -OutputPath 'output\item-buy-prices.csv' `
  -ItemOutputPath 'output\item.csv' `
  -RecipeItemOutputPath 'output\recipe-item-specializations.csv' `
  -StartupTimeoutSec 180 `
  -RequestTimeoutSec 300
```

后续商人数据工具示例：

```powershell
python scripts/gen_vendors.py --item-db2 scripts/export_buyprice/output/item.csv --plan
```

## 可重复运行的学习数据快照

可选参数 `-LearningSnapshotPath` 指定本次快照的精确目录，例如由上层更新入口传入临时 `stage/db2`。默认不开启快照，保持上述三个输出和原有请求数量。启用时复用已经读取的 Item、enUS ItemSparse 和六张学习表原文，只额外读取一次同 build/hotfix 的 enUS SpellName：

```powershell
.\scripts\export_buyprice\export-item-buy-prices.ps1 `
  -LearningSnapshotPath 'output\staging\run-20261021\db2'
```

目录中生成 `item.csv`、`itemsparse.csv`、`itemeffect.csv`、`itemxitemeffect.csv`、`spelleffect.csv`、`spelllearnspell.csv`、`skilllineability.csv`、`skillline.csv`、`spellname.csv` 和 `manifest.json`。CSV 保留工具原文，统一 UTF-8 BOM；JSON 使用 UTF-8 无 BOM。manifest 包含 `schemaVersion=1`、`build`、`hotfixBuild`、`hotfixSHA256`、`useHotfixes=true`、UTC `fetchedAt`，以及 `tables.<小写表名>.{url,sha256,rows}`。每个表的 SHA-256 对应实际落盘字节，行数不包含表头。

快照目录必须不存在或为空，禁止覆写旧快照；它不能与任一 CSV 输出相同、包含 CSV 输出或处在 CSV 文件路径之下，目录链接别名也会解析后校验。快照写入与输出有同一轮版本/缓存检查，并在三个 CSV 发布前完成；写入失败会清理本次创建的快照文件并保留旧 CSV。manifest 最后写入。若后续 CSV 发布失败，三个 CSV 仍按原规则回滚，已经完整写出的快照可能留在临时目录，由上层更新入口处理失败清理。成功返回对象中的 `LearningSnapshotPath` 是绝对路径，未开启时为 null。

快照归档、最终产物成批发布及定期执行由上层更新入口安排；再次运行时为快照指定新的空目录。

## 离线回归

测试使用模拟 HTTP 服务及临时目录，Python 仅为开发测试依赖：

```powershell
python -m unittest discover -s tests -p 'test_item_price_export.py' -v
```

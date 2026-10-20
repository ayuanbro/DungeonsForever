# 未关联图纸核查：1.60.1.70450

核查日期：2026-10-21（Asia/Tokyo）。以原导出的 931 条空 RecipeSpellID 记录为固定基线。
原 CSV SHA-256：`45bf2a896a46687645631c81e85e43743a31a600106624ca58e5a6c759488cf7`。

这是首次补齐的历史说明。现在的 `recipe-item-link-audit.csv`、两个审计 JSON
由统一更新入口按最新快照维护，不再固定为原来的 931 项；最近一次运行核查当前 925 项。
后续数量及证据以这些生成文件和 `cache/specializations/runs/last-run.json` 为准。

## 补齐结果

补齐 6 个图纸物品对应的 5 个不同配方 SpellID，剩余 925 项仍未建立专业配方映射。

| 图纸 ItemID | 所教 SpellID | RequiredSkill | 目标效果 |
|---|---|---|---|
| 2404 | 2156 | 165 制皮 | Effect 24，成品 2305 |
| 2405 | 2157 | 165 制皮 | Effect 24，成品 2306 |
| 6222 | 7451 | 333 附魔 | Effect 54，附魔 64 |
| 6343 | 7451 | 333 附魔 | Effect 54，附魔 64 |
| 8547 | 10844 | 129 急救 | Effect 24，成品 8546 |
| 274491 | 1294289 | 165 制皮 | Effect 24，成品 274490 |

这 6 项均有明确的 ItemEffect 教学目标，缺的是目标的 SkillLineAbility 记录。
补充规则联合使用图纸 ItemSparse.RequiredSkill 与目标 SpellEffect，完整关系保留在
导出 CSV 的 LearningPath 中。RequiredAbility 均为 0，因此专精状态仍为 pending，
不能据此断定没有专精要求。上述关系也不证明物品当前可获得。

## 剩余 925 项

| 审计分类 | 数量 | 含义 |
|---|---:|---|
| other_skill_line | 684 | 明确教学目标的 SkillLineAbility 位于其他技能系 |
| multiple_targets | 2 | 多个明确目标，均位于其他技能系 |
| profession_rank | 6 | 教学链含专业等级学习效果 |
| missing_spell_record | 122 | 目标在当前 SpellName 与 SpellEffect 中均缺失 |
| missing_skill_line | 44 | 目标存在，但没有足够的专业归属证据 |
| no_teaching_relation | 67 | 没有明确的学习触发或教学边 |

SubclassID=0 只表示书籍。原 931 项中有 891 项属于该子类，没有按子类排除它们。
其他技能系也不一概等同于职业法术；逐目标 SkillLineID 见 CSV 的 TargetClassifications。
缺失技能关联不等于已废弃、不可能获取或没有专精要求。

## 外部数据核对

- [wuxianwow recipes.json](https://wuxianwow.com/data/recipes.json)：2,594 条记录的
  id / spell / skill 全部匹配当前 SkillLineAbility 的 ID / Spell / SkillLine。
  products 是成品，未发现图纸教学关联字段、专精字段或完整 Build。
  与本次候选相交的是 21302 / 25347（毒药技能系 40）和 251426 / 1252323；
  这些相交结果没有新增教学证据。
- 复用了 12 个 Wowhead 技能页和 18 个法术页缓存。recipe-items 命中 7 个候选物品，
  但没有所教 SpellID。缓存中 6 条明确 taught-by-item 关系均已存在于原导出。
- 只额外请求了 [物品 251426](https://www.wowhead.com/forever/item%3D251426/plans-prefects-waistguard)
  一页，使用原抓取器的 robots、互斥、限流和缓存机制。该页没有明确 teaches 法术列表；
  spellModifiers 中的 1252323 不表示教学，DB2 对应 TriggerType=1，也未补成学习关系。

外部来源没有补齐新增映射。网页完整 Build 保持未知，不以本地 Build 代填。
`recipe-item-web-link-audit.json` 保留网页 URL、时间、内容哈希及核查证据。
`recipe-item-link-audit-summary.json` 保留 DB2 表清单、哈希和外部目录核对结果。

## 重放

以后重复更新或离线重放使用统一入口：

```powershell
python df-prof-pipeline-v1.0/_temp/fc_update.py --specializations-only --apply
python df-prof-pipeline-v1.0/_temp/fc_update.py --specializations-only --apply --offline
```

仅重放本文的原 931 项基线时，从仓库根目录运行以下命令。
它使用保存的本地快照，不发起网络请求，结果另存为报告，避免替换当前审计：

```powershell
python df-prof-pipeline-v1.0/_temp/fc_recipe_item_audit.py `
  --baseline-csv df-prof-pipeline-v1.0/_temp/_fc/cache/specializations/db2/1.60.1.70450/recipe-items-before.csv `
  --db2-dir df-prof-pipeline-v1.0/_temp/_fc/cache/specializations/db2/1.60.1.70450 `
  --recipe-catalog-json df-prof-pipeline-v1.0/_temp/_fc/cache/specializations/wuxianwow/recipes.json `
  --output-csv df-prof-pipeline-v1.0/_temp/_fc/reports/recipe-items-original-931.csv `
  --summary-json df-prof-pipeline-v1.0/_temp/_fc/reports/recipe-items-original-931-summary.json
```

上述历史重放还需要当次导出的 Item／价格／图纸 CSV；如果它们已更新至其他 Build，
应通过 `--item-csv`、`--prices-csv`、`--recipe-items-csv` 指向保留的当次文件。
缓存按仓库规则忽略；正式审计 CSV/JSON 和此报告保留。缓存缺失时，审计脚本明确报错，
不会自动抓取、填造证据或覆盖已有产物。

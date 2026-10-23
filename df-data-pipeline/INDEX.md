# 数据表索引：每张表是谁生成的、数据从哪来

专业统一入口与外部输入见 [SCRIPT_INPUTS.md](SCRIPT_INPUTS.md)，70450候选安装包的检查结果见 [CSV_CHECK_REPORT.md](CSV_CHECK_REPORT.md)。
70450正式发布与最新安装包见 [PUBLISH_70450.md](PUBLISH_70450.md)。
人工维护记录及新增相对位置见 [MANUAL_MAINTENANCE.md](MANUAL_MAINTENANCE.md)。

下表记录工具包历史样例所覆盖的数据来源。正式插件数据位于仓库根 `Core/Data/`；工具包不再保存48份运行样例，需工作副本时在仓库根运行 `python -B df-data-pipeline/prepare_workspace.py`，任一目标已存在则拒绝覆盖。**生成数据应修改生成器或维护输入后重建，不应直接修改产物。**

- 「单一生成器」= 跑这一个脚本就能整表重建
- 「多脚本增量维护」= 没有已验证的一键重建入口；表内列出的历史批次说明来源，不能作为自动更新顺序。
- 已完成的补丁和修复脚本已清理，历史原件可从 Git 查询。准备工作副本不修复旧脚本的固定 D 盘路径，任何历史工具都应先核对路径和输入。
- 源代号见 `HISTORICAL_README.md` 的「四类数据源」。

---

## 一、副本结构

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_Dungeons.lua` | 多脚本增量维护（`_apply_excav.py` / `gen_dungeon_entry.py` 等） | 手工整理 + CLIENT 副本 id |
| `Data_DungeonEntry.lua` | `gen_dungeon_entry.py` | CLIENT 地图坐标 + 手工校准 |
| `Data_MapPins.lua` | `fc_pins.py`（含 `_route_qicons.py` / `_route_write_pins.py` 分支） | 手工标注 + 路线编辑器导出 |
| `Data_Route.lua` | `gen_route_lua.py` | 手工画线（`_route_plan/tune.html`）+ `Data_Route` 原始段 |
| `Data_AreaMap.lua` | `gen_area_map.py` | WAGO 的 AreaTable + CLIENT |

## 二、首领

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_BossModel.lua` | `gen_boss_model.py` | WOWHEAD NPC 模型 id |
| `Data_BossPos.lua` | `gen_boss_pos.py` | WOWHEAD 地图坐标 + 手工校准 |
| `Data_BossSkills.lua` | `gen_boss_skills.py` | WOWHEAD 法术 id + 自写说明 |

## 三、掉落 / 装备

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_DungeonLoot.lua` | 多脚本增量维护（`_df_wh_align.py` / `_fc_loot_apply_1007.py` …） | WOWHEAD 掉落表 |
| `Data_Gear.lua` | `gen_gear_src.py` → `gen_gear_pack.py` / `gen_gear_scrape.py` | FOREVERCHANGES + WOWHEAD |
| `Data_GearVendors.lua` | `gen_gear_vendors.py` | CLIENT 商人 NPC + 手工 |
| `Data_GearRareSpawns.lua` | `gen_gear_rare.py` | CLIENT 稀有刷新点 |
| `Data_RaidSets.lua` | `gen_raidsets.py` | FOREVERCHANGES 套装 |
| `Data_BIS.lua` | `fc_bis.py` | FOREVERCHANGES |
| `Data_ProfItems.lua` | `fc_prof_items.py`，统一入口同批发布 | 商人/NPC/客户端CSV；替代已停用旧商人报价表 |
| `Data_Plunder.lua` | `gen_plunder_data.py` | CLIENT 掠夺品 |
| `Data_Crates.lua` | `gen_crates_data.py` | CLIENT 箱子 |
| `Data_LootFilter.lua` | 多脚本增量维护 | 手工规则（分类/品质/职业） |

## 四、任务

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_DungeonQuests.lua` | 多脚本增量维护（`_wh_qend_batch.py` / `fc_quest_gap_classify.py` …） | WOWHEAD 任务 + CLIENT |
| `Data_QuestStartNpc.lua` | `gen_quest_start_npc.py` | CLIENT 任务给予者 |
| `Data_QuestStartLoc.lua` | `gen_quest_start_loc.py` | CLIENT NPC 坐标 |
| `Data_QuestEndNpc.lua` | `gen_quest_end_npc.py` | CLIENT NPC 坐标 |
| `Data_ClassQuest.lua` | `gen_class_quest.py` | CLIENT(ClassQuestsForever) + WOWHEAD 评论 |
| `Data_FactionQM.lua` | `gen_faction_qm.py` | CLIENT 阵营军需官 |

## 五、职业 / 配装

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_ClassGuide.lua` | `fc_guide.py` | FOREVERCHANGES |
| `Data_ClassCombat.lua` | `gen_class_combat.py` | CLIENT 法术书 + 手工循环 |
| `Data_ClassTier.lua` | `fc_tier.py` | FOREVERCHANGES |

## 六、专业（当前受管链）

统一入口 `_temp/fc_update.py`；当前维护输入、输出、语言及事务说明见 `README.md`。每个活动脚本的文件输入见 [SCRIPT_INPUTS.md](SCRIPT_INPUTS.md)。五份CSV默认读取本包`_temp/_fc/inputs/`，不调用外部生产脚本。当前六表由 `fc_gen.py` 合并版本化维护规则生成；下表的来源辅助脚本说明数据来历，不是统一入口之外的必跑步骤。

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_Professions.lua` | `fc_gen.py`（总控 `fc_update.py`） | FOREVERCHANGES |
| `Data_ProfRecipes.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfLeveling.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfGathering.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfVendors.lua` | `fc_gen.py` + 同轮 `fc_prof_items.py` | 维护规则、FOREVERCHANGES、冻结 NPC CSV |
| `Data_ProfTrainers.lua` | `fc_gen.py` + 版本化训练师维护输入 | CLIENT 训练师 NPC 的已保存来源 |
| `Data_ProfSpecializations.lua` | `fc_refresh_specializations.py` 准备后统一发布 | DB2图纸、有效配方目录、训练师网页及审计 |
| `Data_ProfMaterialSupply.lua` | `fc_material_vendors.py`，统一入口同批发布 | 独立材料商人供货证据与货架价格 |
| 专业六表 zhTW/enUS | `fc_locales.py` | 同轮基础数据、术语表及人工语言维护输入 |

## 七、收藏 / 探索 / PvP / 杂项

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_CollectionMounts.lua` | `_gen_mounts_apply.py` / `_gen_mounts_npcs_apply.py` | CLIENT + 手工 |
| `Data_CollectionPets.lua` | `_build_collection_pets.py` | CLIENT + 手工 |
| `Data_Explore.lua` | `explore_gen.py` | CLIENT + 手工坐标 |
| `Data_ExploreBanner.lua` | `enus_data_banner.py` | 手工 |
| `Data_ExplorePets.lua` | 多脚本增量维护 | 手工 |
| `Data_ExploreToys.lua` | `enus_data_toys.py` | 手工 |
| `Data_PvPSets.lua` | `gen_pvp_data.py` | FOREVERCHANGES + CLIENT |
| `Data_PvPRanks.lua` | `gen_pvp_data.py` | FOREVERCHANGES |
| `Data_PvPHonor.lua` | `gen_pvp_honor.py` | FOREVERCHANGES + 手工系数 |
| `Data_Factions.lua` | `gen_factions_data.py` | CLIENT 阵营表 |
| `Data_NPCLoc.lua` | 多脚本增量维护（`_apply_npcloc_1016b.py` …） | CLIENT NPC 坐标 |
| `Data_NameOverrides.lua` | `clean_comments_20261010.py`（一次性清洗） | 手工覆盖 |

> `Data_SpellBook` 是扫描脚本 `gen_spells_from_book.py` 的中间产物，不单独成表。

---

## 脚本分类与清理边界

2026-10-23移除141份已完成的 `patch_*`、31份已完成的 `fix_*` 和157份日志；`patch_mut_main_fix.py` 仍被工具引用而保留。旧专业包及重复归档从当前树移除，源文件历史仍由 Git 保存。

| 类别 | 当前使用方式 |
| --- | --- |
| 统一专业链 | 只按 `README.md`、`SCRIPT_INPUTS.md` 的入口运行 |
| `gen_*`、`_cq_*`、`_route_*`、抓取及构建工具 | 根据上表定位；先核对输入、输出、固定路径和外部依赖 |
| `_apply_*`、`_fix_*`、探针及历史校验工具 | 不属于日常自动链；名称不保证只读，执行前检查代码 |
| `strip_*` | 检查其模式和目标；不能把写入模式用于正式数据的手工修订 |

当前跟踪名单可运行 `git ls-files df-data-pipeline/_temp` 查看；历史目录文件总数不再作为完整性契约。

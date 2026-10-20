# 数据表索引：每张表是谁生成的、数据从哪来

`Core/Data/` 下 46 张表全部由 `_temp/` 里的 Python 生成或维护，**禁止手改**。

- 「单一生成器」= 跑这一个脚本就能整表重建
- 「多脚本增量维护」= 没有一键重建，靠一串 `_apply_*` / `patch_*` 逐批改；重跑要按时间顺序挑
- 源代号见 README 的「四类数据源」

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
| `Data_ProfVendorOffers.lua` | 已核验的静态商人货架资料 | 仅 NPC/物品/不限量/购买组数及访问条件，无购买价格；旧价格种子与静态金额已移除，价格方法待重新设计 |
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

## 六、专业

| 数据表 | 生成脚本 | 数据源 |
|---|---|---|
| `Data_Professions.lua` | `fc_gen.py`（总控 `fc_update.py`） | FOREVERCHANGES |
| `Data_ProfRecipes.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfLeveling.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfGathering.lua` | `fc_gen.py` | FOREVERCHANGES |
| `Data_ProfVendors.lua` | `fc_vendors.py` → `fc_gen.py` | FOREVERCHANGES + CLIENT |
| `Data_ProfTrainers.lua` | `gen_prof_trainers.py` + 4 个 `prof_trainer_*.py` 注入 | CLIENT 训练师 NPC |

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

## 脚本分类（1165 个）

| 前缀 | 数量 | 用途 | 要不要跑 |
|---|---|---|---|
| `gen_*` | 51 | 各表的正式生成器 | ✅ 主链路 |
| `fc_*` | 25 | 专业页流水线（抓 → 解析 → 审计 → 生成） | ✅ 主链路 |
| `_cq_*` | 14 | 职业任务的中文化与评论抓取 | ✅ 主链路 |
| `_route_*` | 20+ | 副本路线：抓点、分阵营、生成 Lua、调参页 | ✅ 主链路 |
| `_wh_*` / `_df_wh_*` | 30+ | 窝窝头抓取与对齐 | ✅ 按需 |
| `clean_*` / `explore_gen` / `_build_*` | 20+ | 一次性清洗与构建 | ⚠️ 重跑会覆盖 |
| `patch_*` | 142 | 历史补丁（改 UI、改数据、修某批 id） | ❌ 一次性，已完成 |
| `_apply_*` | 50+ | 把某一批抓取结果写进表 | ⚠️ 按时间顺序 |
| `_fix_*` / `_bak_*` | 200+ | 修复脚本与备份快照 | ❌ 别跑 |
| `qa_*` / `probe_*` / `_check*` | 120+ | 校验与探针，只读 | ✅ 只读安全 |
| `strip_*` | 4 | 去注释 / 格式检查 | ✅ 收尾用 |

完整名单：`_temp/` 下直接按前缀 `ls`。

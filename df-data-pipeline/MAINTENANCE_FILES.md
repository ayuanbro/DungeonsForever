# 数据流水线维护文件清单

核对日期：2026-10-23。这里集中列出清理后 `df-data-pipeline/` 内保留的全部版本控制路径，包括当前入口、依赖、人工输入和离线来源。根目录正式插件、`scripts/` 的独立生产器、测试及资源继续按各自目录维护；它们不在本清单范围内。每个路径只列一次。

更新模块与入口对应关系见 [INDEX.md](INDEX.md)，专业执行参数和输入契约见 [SCRIPT_INPUTS.md](SCRIPT_INPUTS.md)。本清单不是批量执行顺序。保留的来源辅助脚本可能仍有固定 D 盘路径、代理设置或外部原始输入，运行前要核对；不能把“保留”理解为所有旧工具已经迁移或端到端验证。

## 跟踪边界

- 跟踪正式插件产物及其生成器、手工坐标/路线/翻译/训练师映射、版本化规则、冻结来源和当前入口必需的离线输入。文件位于 `_temp`，或名称含 `raw`、`draft`、`cache`，都不构成删除依据。
- 不跟踪运行日志、抓取探测、临时诊断、历史 UI 样页、已完成补丁与迁移、旧部署器及可以用现有输入重建的中间输出。历史原件从 Git 查询；重新生成的工作文件由 `.gitignore` 排除。
- 工具工作副本用仓库根的 `python -B df-data-pipeline/prepare_workspace.py` 按需创建；已有目标目录时拒绝覆盖。正式运行文件仍须跟踪，发布安装包直接使用正式文件。
- 专业 `_fc/inputs` 的冻结客户端/网页证据和 `_fc/data` 的有效目录不是普通下载缓存。当前统一检查、分支更新和离线重放会读取这些文件；本次保留，不以“以后还可以抓到”为由删除。

## 保留输入的关键理由

- `_bosspos_*`、`_stormwind_npc_coords*`、`_npcloc_sw_override.json`、路线 JSON 包含人工标注或校准；重建还需要原始地图、截图或外部来源，不能丢弃。
- `_cq_*`、`_wh_translate_zh.json`、`_trainers_*` 等包含维护译文、映射或当前采集选择。训练师 `_trainers_zone_zh.json` 虽为英文列表，其重建依赖未跟踪的 Questie 原目录，仍保留为必要输入。
- `_cg_parsed.json`、`_macro_data.json`、`_rot_data.json` 等是当前入口读取的离线批次，原始网页并非全部随仓库保存。`_cg_norm.json` 保留旧英文对齐基线：当前重建会改变优势/劣势分组，且旧批次仍有未逐项确认的独有英文，不能按成功退出即认定完全可复现。
- `_fc_hidden_items.html` 保留为隐藏物品解析器的冻结网页输入；其来源为 `https://foreverchanges.pro/zh-cn/hidden-items`，当前没有专用保留抓取器。

## 已移除中间文件的恢复顺序

从仓库根准备工具工作副本后，可运行 `python -B df-data-pipeline/_temp/_df_wh_export_zh.py` 重建 `_wh_translate_src.json`。它只导出英文待翻译清单；人工译文在保留的 `_wh_translate_zh.json`。本次离线重建保留全部旧正文，只随当前掉落名单增加 Stockade 的 Dextren Ward，已有中文按副本和首领键匹配。

副本网页缓存先在 `df-data-pipeline/_temp/` 运行 `python -B _fc_dg_fetch_all.py`，成功后运行 `python -B _fc_dg_parse.py <slug>`；单副本技能解析为 `python -B _fc_fights_parse.py <slug>`。抓取器需要 `curl_cffi` 和符合本机环境的代理配置。比较报表按 `fc_dungeon_compare2.py` → `fc_quest_side_verify.py` → `fc_side_cross.py` 顺序重新生成，先核对脚本工作目录和源输入。重新抓取只取得当前来源，不能保证重现历史网站字节。

`_trainers_zone_zh2.json` 原内容为空。保留选择清单和 `_trainers_zone_ids.json` 后，`prof_trainer_zone_search.py` 在结果缺失时自动从空映射开始抓取；审阅后把有效译文合并进维护的 `_trainers_zone_full.json`。`zone_fetch` 只输出网页文字，不会自动合并译文。

## 完整路径

共 686 个路径；以下路径均相对仓库根。

### 包入口、文档、忽略规则与职业任务原始样本（14）

```text
df-data-pipeline/CSV_CHECK_REPORT.md
df-data-pipeline/INDEX.md
df-data-pipeline/MAINTENANCE_FILES.md
df-data-pipeline/MANUAL_MAINTENANCE.md
df-data-pipeline/MATERIAL_VENDORS.md
df-data-pipeline/PUBLISH_70450.md
df-data-pipeline/README.md
df-data-pipeline/SCRIPT_INPUTS.md
df-data-pipeline/_temp/.gitignore
df-data-pipeline/prepare_workspace.py
df-data-pipeline/requirements.txt
df-data-pipeline/run.bat
df-data-pipeline/samples/ClassQuestsForever/Chains.lua
df-data-pipeline/samples/ClassQuestsForever/Quests.lua
```

### 专业生成、语言与维护工具（59）

```text
df-data-pipeline/_temp/enus_data.py
df-data-pipeline/_temp/enus_data_banner.py
df-data-pipeline/_temp/enus_data_guide19.py
df-data-pipeline/_temp/enus_data_names.py
df-data-pipeline/_temp/enus_data_names2.py
df-data-pipeline/_temp/enus_data_names3.py
df-data-pipeline/_temp/enus_data_names_hand.py
df-data-pipeline/_temp/enus_data_onyxia.py
df-data-pipeline/_temp/enus_data_prof.py
df-data-pipeline/_temp/enus_data_prose.py
df-data-pipeline/_temp/enus_data_quests.py
df-data-pipeline/_temp/enus_data_quests2.py
df-data-pipeline/_temp/enus_data_raidsets.py
df-data-pipeline/_temp/enus_data_resid.py
df-data-pipeline/_temp/enus_data_tier.py
df-data-pipeline/_temp/enus_data_toys.py
df-data-pipeline/_temp/enus_data_whguide.py
df-data-pipeline/_temp/fc_enchant_ids.py
df-data-pipeline/_temp/fc_fetch.py
df-data-pipeline/_temp/fc_fields.py
df-data-pipeline/_temp/fc_gen.py
df-data-pipeline/_temp/fc_i18n.py
df-data-pipeline/_temp/fc_locales.py
df-data-pipeline/_temp/fc_maintenance.py
df-data-pipeline/_temp/fc_material_coverage.py
df-data-pipeline/_temp/fc_material_vendors.py
df-data-pipeline/_temp/fc_package.py
df-data-pipeline/_temp/fc_parse.py
df-data-pipeline/_temp/fc_path_audit.py
df-data-pipeline/_temp/fc_pipeline.py
df-data-pipeline/_temp/fc_pipeline_common.py
df-data-pipeline/_temp/fc_pipeline_paths.py
df-data-pipeline/_temp/fc_prof_items.py
df-data-pipeline/_temp/fc_prof_specializations.py
df-data-pipeline/_temp/fc_recipe_catalog_fetch.py
df-data-pipeline/_temp/fc_recipe_item_audit.py
df-data-pipeline/_temp/fc_recipe_item_web_audit.py
df-data-pipeline/_temp/fc_refresh_specializations.py
df-data-pipeline/_temp/fc_specialization_fetch.py
df-data-pipeline/_temp/fc_update.py
df-data-pipeline/_temp/fc_vendor_side.py
df-data-pipeline/_temp/fc_vendors.py
df-data-pipeline/_temp/fc_vendors_resolve.py
df-data-pipeline/_temp/fc_zh_sync.py
df-data-pipeline/_temp/fc_zones.py
df-data-pipeline/_temp/gen_enus_data.py
df-data-pipeline/_temp/gen_prof_trainers.py
df-data-pipeline/_temp/gen_zhtw.py
df-data-pipeline/_temp/gen_zhtw_data.py
df-data-pipeline/_temp/prof_trainer_loc_inject.py
df-data-pipeline/_temp/prof_trainer_npcid.py
df-data-pipeline/_temp/prof_trainer_zh_fetch.py
df-data-pipeline/_temp/prof_trainer_zh_inject.py
df-data-pipeline/_temp/prof_trainer_zone_fetch.py
df-data-pipeline/_temp/prof_trainer_zone_ids.py
df-data-pipeline/_temp/prof_trainer_zone_search.py
df-data-pipeline/_temp/prof_trainer_zone_zh.py
df-data-pipeline/_temp/strip_comments.py
df-data-pipeline/_temp/tools/tf_dryrun.py
```

### 独立 Lua 辅助工具（1）

```text
df-data-pipeline/_temp/strip_lua_comments.py
```

### 副本路线与地图脚本（14）

```text
df-data-pipeline/_temp/_map_inventory.py
df-data-pipeline/_temp/_map_tga.py
df-data-pipeline/_temp/_route_bake_maps.py
df-data-pipeline/_temp/_route_build_all.py
df-data-pipeline/_temp/_route_faction.py
df-data-pipeline/_temp/_route_make_tune.py
df-data-pipeline/_temp/_route_paths.py
df-data-pipeline/_temp/_route_qicons.py
df-data-pipeline/_temp/_route_serve.py
df-data-pipeline/_temp/_route_write_pins.py
df-data-pipeline/_temp/fc_pins.py
df-data-pipeline/_temp/gen_area_map.py
df-data-pipeline/_temp/gen_dungeon_entry.py
df-data-pipeline/_temp/gen_route_lua.py
```

### 首领与副本攻略脚本（17）

```text
df-data-pipeline/_temp/_df_pin_floors2.py
df-data-pipeline/_temp/_df_pin_refetch.py
df-data-pipeline/_temp/_df_skill_scrape.py
df-data-pipeline/_temp/_df_wh_align.py
df-data-pipeline/_temp/_df_wh_export_zh.py
df-data-pipeline/_temp/_df_wh_guide_gen.py
df-data-pipeline/_temp/_df_wh_guide_parse.py
df-data-pipeline/_temp/_df_wh_guide_scrape.py
df-data-pipeline/_temp/_df_wh_names2.py
df-data-pipeline/_temp/_df_wh_spell_desc.py
df-data-pipeline/_temp/_df_wh_spell_icons.py
df-data-pipeline/_temp/_df_wh_spell_names.py
df-data-pipeline/_temp/_gen_guide19.py
df-data-pipeline/_temp/gen_boss_model.py
df-data-pipeline/_temp/gen_boss_pos.py
df-data-pipeline/_temp/gen_boss_skills.py
df-data-pipeline/_temp/lootified_bosspos.py
```

### 掉落、装备与BIS脚本（13）

```text
df-data-pipeline/_temp/_fc_loot_apply_1007b.py
df-data-pipeline/_temp/_gqf_fetch_coords.py
df-data-pipeline/_temp/_gqf_fetch_names.py
df-data-pipeline/_temp/fc_bis.py
df-data-pipeline/_temp/fc_bis_zh.py
df-data-pipeline/_temp/fc_dungeon_compare2.py
df-data-pipeline/_temp/gen_gear_pack.py
df-data-pipeline/_temp/gen_gear_rare.py
df-data-pipeline/_temp/gen_gear_scrape.py
df-data-pipeline/_temp/gen_gear_src.py
df-data-pipeline/_temp/gen_gear_vendors.py
df-data-pipeline/_temp/gen_qlv_from_quests.py
df-data-pipeline/_temp/gen_raidsets.py
```

### 任务脚本（22）

```text
df-data-pipeline/_temp/_cq_comments_fetch.py
df-data-pipeline/_temp/_cq_comments_prep.py
df-data-pipeline/_temp/_cq_fetch_names.py
df-data-pipeline/_temp/_cq_forever_fetch.py
df-data-pipeline/_temp/_cq_item_zh.py
df-data-pipeline/_temp/_cq_npc_zh.py
df-data-pipeline/_temp/_cq_qname_wx.py
df-data-pipeline/_temp/_cq_qname_zh2.py
df-data-pipeline/_temp/_cq_wxdb2.py
df-data-pipeline/_temp/_wh_parse_1007.py
df-data-pipeline/_temp/_wh_q_comments_all_fetch.py
df-data-pipeline/_temp/_wh_qb_fetch.py
df-data-pipeline/_temp/_wh_qend_batch.py
df-data-pipeline/_temp/fc_quest_gap_classify.py
df-data-pipeline/_temp/fc_quest_side_verify.py
df-data-pipeline/_temp/fc_side_cross.py
df-data-pipeline/_temp/gen_class_quest.py
df-data-pipeline/_temp/gen_ext_info.py
df-data-pipeline/_temp/gen_quest_end_npc.py
df-data-pipeline/_temp/gen_quest_share.py
df-data-pipeline/_temp/gen_quest_start_loc.py
df-data-pipeline/_temp/gen_quest_start_npc.py
```

### 职业与战斗脚本（12）

```text
df-data-pipeline/_temp/_cg_fetch_all.py
df-data-pipeline/_temp/_cg_norm_dump.py
df-data-pipeline/_temp/_cg_parse_guide.py
df-data-pipeline/_temp/_macro_parse.py
df-data-pipeline/_temp/_rot_parse.py
df-data-pipeline/_temp/fc_guide.py
df-data-pipeline/_temp/fc_tier.py
df-data-pipeline/_temp/gen_class_combat.py
df-data-pipeline/_temp/gen_macro_doc.py
df-data-pipeline/_temp/gen_rot_doc.py
df-data-pipeline/_temp/gen_rot_wowhead.py
df-data-pipeline/_temp/gen_spells_from_book.py
```

### 声望、PvP、箱子脚本（8）

```text
df-data-pipeline/_temp/fac_wowhead_sweep.py
df-data-pipeline/_temp/gen_crates_data.py
df-data-pipeline/_temp/gen_faction_qm.py
df-data-pipeline/_temp/gen_factions_data.py
df-data-pipeline/_temp/gen_plunder_data.py
df-data-pipeline/_temp/gen_pvp_data.py
df-data-pipeline/_temp/gen_pvp_honor.py
df-data-pipeline/_temp/gen_pvp_parse.py
```

### 收藏与探索脚本（14）

```text
df-data-pipeline/_temp/_build_pets_src.py
df-data-pipeline/_temp/_pets_fetch.py
df-data-pipeline/_temp/_pets_parse.py
df-data-pipeline/_temp/_pets_pins.py
df-data-pipeline/_temp/_wh_mount_pages_parse.py
df-data-pipeline/_temp/_wh_mounts_items.py
df-data-pipeline/_temp/_wh_mounts_parse.py
df-data-pipeline/_temp/_wh_pet_display.py
df-data-pipeline/_temp/explore_crosscheck.py
df-data-pipeline/_temp/explore_fetch.py
df-data-pipeline/_temp/explore_gen.py
df-data-pipeline/_temp/explore_parse.py
df-data-pipeline/_temp/explore_resolve.py
df-data-pipeline/_temp/explore_wowhead_verify.py
```

### 独立来源采集脚本（8）

```text
df-data-pipeline/_temp/_build_collection_pets.py
df-data-pipeline/_temp/_fc_dg_fetch_all.py
df-data-pipeline/_temp/_fc_dg_parse.py
df-data-pipeline/_temp/_fc_fights_parse.py
df-data-pipeline/_temp/_fc_hidden_parse.py
df-data-pipeline/_temp/_fetch_wh_wotlk_npcloc.py
df-data-pipeline/_temp/_ov_fetch.py
df-data-pipeline/_temp/_ov_parse.py
```

### 独立数据组装入口（2）

```text
df-data-pipeline/_temp/_gen_mounts_apply.py
df-data-pipeline/_temp/_gen_mounts_npcs_apply.py
```

### 语言生成器与维护词表（4）

```text
df-data-pipeline/_temp/enus_cjk_audit.py
df-data-pipeline/_temp/enus_fetch_names.py
df-data-pipeline/_temp/enus_gap_all.py
df-data-pipeline/_temp/gen_enus.py
```

### 资源生成器（15）

```text
df-data-pipeline/_temp/_gen_route_dot.py
df-data-pipeline/_temp/_gen_route_icons.py
df-data-pipeline/_temp/_gen_settings_icon.py
df-data-pipeline/_temp/_gen_state_icons2.py
df-data-pipeline/_temp/gen_check_glyphs.py
df-data-pipeline/_temp/gen_crate_nav_icon.py
df-data-pipeline/_temp/gen_entry_icons.py
df-data-pipeline/_temp/gen_faction_icons.py
df-data-pipeline/_temp/gen_line_arc_tga.py
df-data-pipeline/_temp/gen_my_mark.py
df-data-pipeline/_temp/gen_pvp_rank_arrow.py
df-data-pipeline/_temp/gen_quest_pin_icons.py
df-data-pipeline/_temp/gen_sort_icon.py
df-data-pipeline/_temp/gen_vfade.py
df-data-pipeline/_temp/gen_warn_icon.py
```

### 共享执行依赖（10）

```text
df-data-pipeline/_temp/_cg_fetch.py
df-data-pipeline/_temp/_fc_compare.py
df-data-pipeline/_temp/_route_gen.py
df-data-pipeline/_temp/cc_mac.py
df-data-pipeline/_temp/cc_mac2.py
df-data-pipeline/_temp/cc_rot.py
df-data-pipeline/_temp/cc_rot_wow.py
df-data-pipeline/_temp/cc_spells.py
df-data-pipeline/_temp/rot_zh_notes.py
df-data-pipeline/_temp/tools/wow_stub.lua
```

### 路线编辑器、手工路线与地图索引（31）

```text
df-data-pipeline/_temp/_map_inv.json
df-data-pipeline/_temp/_route_override.json
df-data-pipeline/_temp/_route_plan/data/blackfathom_deeps.json
df-data-pipeline/_temp/_route_plan/data/blackrock_depths.json
df-data-pipeline/_temp/_route_plan/data/dire_maul_east.json
df-data-pipeline/_temp/_route_plan/data/dire_maul_north.json
df-data-pipeline/_temp/_route_plan/data/dire_maul_west.json
df-data-pipeline/_temp/_route_plan/data/gnomeregan.json
df-data-pipeline/_temp/_route_plan/data/index.json
df-data-pipeline/_temp/_route_plan/data/lower_blackrock_spire.json
df-data-pipeline/_temp/_route_plan/data/maraudon.json
df-data-pipeline/_temp/_route_plan/data/ragefire_chasm.json
df-data-pipeline/_temp/_route_plan/data/razorfen_downs.json
df-data-pipeline/_temp/_route_plan/data/razorfen_kraul.json
df-data-pipeline/_temp/_route_plan/data/scholomance.json
df-data-pipeline/_temp/_route_plan/data/shadowfang_keep.json
df-data-pipeline/_temp/_route_plan/data/sm_armory.json
df-data-pipeline/_temp/_route_plan/data/sm_cathedral.json
df-data-pipeline/_temp/_route_plan/data/sm_graveyard.json
df-data-pipeline/_temp/_route_plan/data/sm_library.json
df-data-pipeline/_temp/_route_plan/data/stratholme_main.json
df-data-pipeline/_temp/_route_plan/data/sunken_temple.json
df-data-pipeline/_temp/_route_plan/data/the_deadmines.json
df-data-pipeline/_temp/_route_plan/data/the_stockade.json
df-data-pipeline/_temp/_route_plan/data/uldaman.json
df-data-pipeline/_temp/_route_plan/data/wailing_caverns.json
df-data-pipeline/_temp/_route_plan/data/zul_farrak.json
df-data-pipeline/_temp/_route_plan/tune.html
df-data-pipeline/_temp/_route_qi_hide.json
df-data-pipeline/_temp/_route_qicon_override.json
df-data-pipeline/_temp/_wc_routes_raw.json
```

### 首领及NPC位置、模型与手工校准（10）

```text
df-data-pipeline/_temp/_boss_skills_raw.json
df-data-pipeline/_temp/_bossmodel_lootified.json
df-data-pipeline/_temp/_bosspos_draft.json
df-data-pipeline/_temp/_bosspos_floors.json
df-data-pipeline/_temp/_bosspos_floors_all.json
df-data-pipeline/_temp/_bosspos_lootified.json
df-data-pipeline/_temp/_bosspos_manual.json
df-data-pipeline/_temp/_npcloc_sw_override.json
df-data-pipeline/_temp/_stormwind_npc_coords.csv
df-data-pipeline/_temp/_stormwind_npc_coords_v2.csv
```

### 任务来源、坐标与人工译文（18）

```text
df-data-pipeline/_temp/_cq_item_zh.json
df-data-pipeline/_temp/_cq_names.json
df-data-pipeline/_temp/_cq_notes.json
df-data-pipeline/_temp/_cq_npc_manual.json
df-data-pipeline/_temp/_cq_npc_zh.json
df-data-pipeline/_temp/_cq_qname_zh.json
df-data-pipeline/_temp/_cq_quest_ids.json
df-data-pipeline/_temp/_cq_title_zh.json
df-data-pipeline/_temp/_cq_zone_map.json
df-data-pipeline/_temp/_cq_zone_zh.json
df-data-pipeline/_temp/_gqf_applied.json
df-data-pipeline/_temp/_gqf_name_cache.json
df-data-pipeline/_temp/_gqf_quest_coords.json
df-data-pipeline/_temp/_q_notes_map.json
df-data-pipeline/_temp/_qsn_needwow.json
df-data-pipeline/_temp/_qsn_wow_loc.json
df-data-pipeline/_temp/_wh_qend_raw.json
df-data-pipeline/_temp/questie/questie_forever.json
```

### 训练师名单、地名与人工映射（5）

```text
df-data-pipeline/_temp/_trainers_npcid.json
df-data-pipeline/_temp/_trainers_zh.json
df-data-pipeline/_temp/_trainers_zone_full.json
df-data-pipeline/_temp/_trainers_zone_ids.json
df-data-pipeline/_temp/_trainers_zone_zh.json
```

### 职业与副本攻略原文、译文和对齐基线（11）

```text
df-data-pipeline/_temp/_batch19_bosslists.json
df-data-pipeline/_temp/_cg_norm.json
df-data-pipeline/_temp/_cg_parsed.json
df-data-pipeline/_temp/_macro_data.json
df-data-pipeline/_temp/_rot_data.json
df-data-pipeline/_temp/_wh_guide_raw.json
df-data-pipeline/_temp/_wh_npc_names.json
df-data-pipeline/_temp/_wh_spell_desc.json
df-data-pipeline/_temp/_wh_spell_icons.json
df-data-pipeline/_temp/_wh_spell_names.json
df-data-pipeline/_temp/_wh_translate_zh.json
```

### 藏品来源及坐骑离线输入（6）

```text
df-data-pipeline/_temp/_companions_names.json
df-data-pipeline/_temp/_wh_mount_fixups.json
df-data-pipeline/_temp/_wh_mount_item_pages.json
df-data-pipeline/_temp/_wh_mount_npcloc.json
df-data-pipeline/_temp/_wh_mount_npcs.json
df-data-pipeline/_temp/_wh_mounts_items.json
```

### 客户端与网站冻结来源（10）

```text
df-data-pipeline/_temp/_fc_hidden_items.html
df-data-pipeline/_temp/_plunder_src.json
df-data-pipeline/_temp/_pvp_site_data.json
df-data-pipeline/_temp/_wago_AreaTable_en.csv
df-data-pipeline/_temp/_wago_AreaTable_zh.csv
df-data-pipeline/_temp/_wuxian_fac.json
df-data-pipeline/_temp/_wx_categories.json
df-data-pipeline/_temp/_wx_manifest.json
df-data-pipeline/_temp/_wx_quests.json
df-data-pipeline/_temp/_wx_recipes.json
```

### 其他当前选择清单与人工输入（6）

```text
df-data-pipeline/_temp/_ext_notes.json
df-data-pipeline/_temp/_ext_pre_ids.json
df-data-pipeline/_temp/_fc_rare_zh.json
df-data-pipeline/_temp/_fc_slugs.txt
df-data-pipeline/_temp/_lootify_zh_names.json
df-data-pipeline/_temp/_rare_zh_cache.json
```

### 专业人工维护规则与迁移基线（29）

```text
df-data-pipeline/_temp/_fc/maintenance/locales-audit-70450-v2.json
df-data-pipeline/_temp/_fc/maintenance/locales.json
df-data-pipeline/_temp/_fc/maintenance/material-vendors.json
df-data-pipeline/_temp/_fc/maintenance/professions.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/audit.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/incoming-input-model.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/_wago_AreaTable_zh.csv
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/drop_loc.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/enchant_ids.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/index.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/item_ids.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_alchemy.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_blacksmithing.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_cooking.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_enchanting.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_engineering.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_first-aid.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_fishing.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_herbalism.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_leatherworking.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_mining.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_skinning.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/prof_tailoring.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/vendor_loc.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/zh.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/zone_ids.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/normalized/zone_zh.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/previous-input-model.json
df-data-pipeline/_temp/_fc/maintenance/source/rebase-2-70450/revision-1-manifest.json
```

### 专业人工语言输入（1）

```text
df-data-pipeline/_temp/_fc/i18n/zh.json
```

### 专业有效目录、离线批次与审计（38）

```text
df-data-pipeline/_temp/_fc/data/catalog/enchant_ids.json
df-data-pipeline/_temp/_fc/data/catalog/prof_alchemy.json
df-data-pipeline/_temp/_fc/data/catalog/prof_blacksmithing.json
df-data-pipeline/_temp/_fc/data/catalog/prof_comprehension.json
df-data-pipeline/_temp/_fc/data/catalog/prof_cooking.json
df-data-pipeline/_temp/_fc/data/catalog/prof_enchanting.json
df-data-pipeline/_temp/_fc/data/catalog/prof_engineering.json
df-data-pipeline/_temp/_fc/data/catalog/prof_first-aid.json
df-data-pipeline/_temp/_fc/data/catalog/prof_fishing.json
df-data-pipeline/_temp/_fc/data/catalog/prof_herbalism.json
df-data-pipeline/_temp/_fc/data/catalog/prof_leatherworking.json
df-data-pipeline/_temp/_fc/data/catalog/prof_mining.json
df-data-pipeline/_temp/_fc/data/catalog/prof_poisons.json
df-data-pipeline/_temp/_fc/data/catalog/prof_skinning.json
df-data-pipeline/_temp/_fc/data/catalog/prof_tailoring.json
df-data-pipeline/_temp/_fc/data/drop_loc.json
df-data-pipeline/_temp/_fc/data/enchant_ids.json
df-data-pipeline/_temp/_fc/data/explore_books.json
df-data-pipeline/_temp/_fc/data/explore_resolved.json
df-data-pipeline/_temp/_fc/data/index.json
df-data-pipeline/_temp/_fc/data/item_ids.json
df-data-pipeline/_temp/_fc/data/material-vendors.json
df-data-pipeline/_temp/_fc/data/prof_alchemy.json
df-data-pipeline/_temp/_fc/data/prof_blacksmithing.json
df-data-pipeline/_temp/_fc/data/prof_cooking.json
df-data-pipeline/_temp/_fc/data/prof_enchanting.json
df-data-pipeline/_temp/_fc/data/prof_engineering.json
df-data-pipeline/_temp/_fc/data/prof_first-aid.json
df-data-pipeline/_temp/_fc/data/prof_fishing.json
df-data-pipeline/_temp/_fc/data/prof_herbalism.json
df-data-pipeline/_temp/_fc/data/prof_leatherworking.json
df-data-pipeline/_temp/_fc/data/prof_mining.json
df-data-pipeline/_temp/_fc/data/prof_skinning.json
df-data-pipeline/_temp/_fc/data/prof_tailoring.json
df-data-pipeline/_temp/_fc/data/trainer-recipe-specializations.csv
df-data-pipeline/_temp/_fc/data/vendor_loc.json
df-data-pipeline/_temp/_fc/data/zone_ids.json
df-data-pipeline/_temp/_fc/data/zone_zh.json
```

### 专业冻结输入及来源证据（308）

```text
df-data-pipeline/_temp/_fc/inputs/client/item-buy-prices.csv
df-data-pipeline/_temp/_fc/inputs/client/item.csv
df-data-pipeline/_temp/_fc/inputs/client/recipe-item-specializations.csv
df-data-pipeline/_temp/_fc/inputs/manifest.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/client/factions.csv
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/client/manifest.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/client/npc-factions.csv
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/client/raw/faction_enUS.db2
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/locales/zhCN.lua
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/locales/zhTW.lua
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/manifest.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/10118.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/10856.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/10857.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/11185.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/11187.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/11189.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/11278.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1146.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1148.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1149.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/11536.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/11557.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/11874.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12022.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12033.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12043.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12245.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12246.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1250.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12941.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12942.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12943.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12944.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12956.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12957.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12958.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12959.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/12962.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1304.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1313.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1318.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/13278.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/13420.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/13429.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/13432.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/13433.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/13435.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1347.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/13476.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/14371.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1454.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/14637.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1465.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1471.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/14738.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1474.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/14921.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/15176.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/15179.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/15419.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/15471.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1669.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1672.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1684.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/1685.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/17068.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/17070.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2118.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/213077.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/214070.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/214096.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/214098.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/214099.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/214101.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/216672.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/216902.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/217689.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/222261.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/227853.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2380.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2381.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2383.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2393.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2394.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2397.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/240604.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/242498.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2480.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2481.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/248196.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/248197.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/248198.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/248199.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2482.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/248200.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/248201.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/248202.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2483.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/251905.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/251973.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/251991.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/251997.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/252083.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/252380.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/253139.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/253140.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/254151.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/254695.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/255894.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/255895.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/256629.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/256729.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/256730.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/256731.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/256732.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/256733.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/256734.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/256735.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/257004.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/257006.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/257020.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/258306.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/258415.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/258463.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/258466.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/258548.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/258568.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/258572.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/259860.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/259962.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/260487.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/260565.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/260566.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/260570.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/261313.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2626.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/264078.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/264797.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2663.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2664.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2668.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2669.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/266901.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2670.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/267000.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2672.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2679.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2682.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2683.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2684.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2685.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2687.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2688.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2697.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2698.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2699.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/270780.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/272646.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/277945.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2803.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2805.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2806.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2810.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2812.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2814.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2816.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2819.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2821.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2838.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2843.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2846.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/2848.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3005.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3012.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3027.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3029.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3081.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3085.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3091.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3096.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3134.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3178.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/32287.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3333.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3335.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3346.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3348.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3356.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3364.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3366.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/340.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3400.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3413.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3482.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3485.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3489.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3490.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3495.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3497.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3499.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3522.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3537.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3550.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3556.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3683.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3881.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3954.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3955.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3956.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3958.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/3960.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4083.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4086.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4168.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4186.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4189.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4200.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4223.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4225.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4226.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4228.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4229.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4265.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4305.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4307.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4553.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4561.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4574.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4577.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4589.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4610.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4617.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4782.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4877.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4878.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4879.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/4897.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5128.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5154.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5158.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5160.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5162.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5175.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5178.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5411.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5483.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5494.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5512.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5565.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5594.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5695.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5748.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5757.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5758.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5783.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5940.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5942.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/5944.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/6567.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/6568.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/6574.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/6576.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/66.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/6730.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/6731.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/6777.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/6779.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/734.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/7733.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/777.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/7852.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/7854.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/7940.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/7947.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8125.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8131.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8137.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8139.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8145.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8150.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8157.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8158.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8160.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8161.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8176.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8177.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8178.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8307.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/843.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8508.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8678.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8679.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8681.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/8878.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/9179.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/9499.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/9544.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/9636.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/nether/989.json
df-data-pipeline/_temp/_fc/inputs/vendors/faction-sources/vendors.csv
df-data-pipeline/_temp/_fc/inputs/vendors/npc-factions-20261021.json
df-data-pipeline/_temp/_fc/inputs/vendors/npc-factions-audit.json
df-data-pipeline/_temp/_fc/inputs/vendors/npc-factions.json
df-data-pipeline/_temp/_fc/inputs/vendors/npcs.csv
df-data-pipeline/_temp/_fc/inputs/vendors/soldby-json-20261021-audit.json
df-data-pipeline/_temp/_fc/inputs/vendors/vendors-soldby-json-20261021.csv
df-data-pipeline/_temp/_fc/inputs/vendors/vendors.csv
```

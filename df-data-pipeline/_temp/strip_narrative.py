# -*- coding: utf-8 -*-
"""叙事类注释清理·第二批（方案 A：叙事全删、留骨架）。
- 删：决策叙事 / 阶段史 / 源项目模块提及（拍卖/出价/角色总览/装备库/OptionsHUI 等）。
- 留：生成物标记、表字段结构说明、技术坑注（机制描述压缩后保留）。
- 受检替换：每条 old 必须精确命中 expected 次（默认 1），否则 sys.exit。
- 行尾：DungeonUI.lua / Hui.lua = CRLF，其余 = LF。
"""
import sys, io

FILES_CRLF = {'Core/DungeonUI.lua', 'Core/Hui.lua'}

# (file, old, new[, expected])
EDITS = [
    # ───────────── DungeonUI.lua ─────────────
    ('Core/DungeonUI.lua',
     '-- ⚠️ 本文件由 _temp/port_dungeonsforever.py 生成，改注释或结构都要改脚本；手改会被覆盖。\n--    几何值一律原值：改一个像素整页位移。\n',
     '-- ⚠️ 几何值一律原值：改一个像素整页位移。\n'),
    ('Core/DungeonUI.lua',
     '-- 注：列表页原先按「等级分段」分组（13–19 / 20–29 …）的 BANDS 配色表已随卡片墙改版删除，\n-- 现在列表按「可达性」分三组（现在可以进入 / 推荐 / 还需升级），配色见 DG.BuildList。\n',
     '-- 列表按「可达性」分三组（现在可以进入 / 推荐 / 还需升级），配色见 DG.BuildList。\n'),
    ('Core/DungeonUI.lua',
     '    -- 原先的「副本」大标题 + 「按等级排 13–60 级 · …」说明行都是冗余（顶部标签页已表明身份），\n'
     '    -- 合并成一行后比原来少一行，正文自然上移 38px（原先 BODY_Y = 130）。\n'
     '    -- 子页签行紧跟在顶部胶囊行之下。实测面板纵向坐标（截图逐像素量得）：\n'
     '    --   胶囊本体原是 y = 0~-20（ROW_SUB=0、BTN_H=20），hui 轨道上下各外扩 2px → +2~-22，\n'
     '    --   选中滑块高 22、底边约 y = -22；\n'
     '    --   ★ 胶囊行整体上移 DG.CAPSULE_LIFT(=10) → 整行约 +12~-12。\n'
     '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距由原约 8px 变成约 18px。\n',
     '    -- 子页签行紧跟在顶部胶囊行之下（hui 轨道上下各外扩 2px；胶囊行整体上移 DG.CAPSULE_LIFT=10）。\n'
     '    -- 故 SUBTAB_Y = ROW_CLASS(30) 仍在胶囊下方，间距约 18px。\n'),
    ('Core/DungeonUI.lua',
     '    -- 原先写 ROW_CLASS + 32（= 62）会在标签栏与子页签之间空出 39px 死区。\n',
     '    -- ⚠️ 不要写 ROW_CLASS + 32：会在标签栏与子页签之间空出 39px 死区。\n'),
    ('Core/DungeonUI.lua',
     '-- 数据来自 Core/Data/Data_DungeonLoot.lua（ns.DungeonLoot[副本 id]），由\n-- _temp/gen_dungeon_loot.py 生成（逐条对账见 _temp/verify_dungeon_loot.py）。\n',
     '-- 数据来自 Core/Data/Data_DungeonLoot.lua（ns.DungeonLoot[副本 id]）。\n'),
    ('Core/DungeonUI.lua',
     '--    物品自身的名字 / 品质 / 部位 / 图标一律**只从客户端取**（\n'
     '--    外部口径不准（例：6465「水蛇法袍」判 2 绿而游戏内 3 蓝，全库 444 件不一致）；\n'
     '--    客户端拿不到就明说「暂时没有客户端数据」，宁缺毋滥）。\n',
     '--    物品自身的名字 / 品质 / 部位 / 图标一律**只从客户端取**（外部口径不准）；\n'
     '--    客户端拿不到就明说「暂时没有客户端数据」，宁缺毋滥。\n'),
    ('Core/DungeonUI.lua',
     '-- ★★ 外部物品资料已**整体弃用**（外部口径不准，宁缺毋滥）。\n'
     '--    原来这里有个 `DG.TipOf`，读 Core/Data/Data_DungeonTips.lua（414 KB 外部 tooltip 文本）\n'
     '--    逐行渲染。现已删除该函数，数据文件也从 TOC 卸下并移出插件目录 ——\n'
     '--    物品的一切属性只从客户端取，客户端没有就显示「暂时没有客户端数据」。\n',
     '-- ★★ 物品的一切属性只从客户端取（外部物品资料已整体弃用，宁缺毋滥），\n'
     '--    客户端没有就显示「暂时没有客户端数据」。\n'),
    ('Core/DungeonUI.lua',
     '-- ★★ 实机事故：原实现只走 C_Item.RequestLoadItemDataByID，\n'
     '--    该 API 在本端不存在时退到「裸调 GetItemInfo」—— 而现代端裸调 GetItemInfo\n'
     '--    **不会**触发加载。于是请求根本发不出去：`/tf qual` 实测 1807 件**到货 0 件**，\n'
     '--    卡片只能一直停在外部口径（现象就是「插件里绿色、游戏里蓝色」）。\n'
     '--    现改为**三路齐发**（各自幂等、成本可忽略，任一路可用即生效）：\n',
     '-- ★★ 坑：只走 C_Item.RequestLoadItemDataByID 不够——本端没有该 API 时裸调 GetItemInfo\n'
     '--    **不会**触发加载（实测一批 itemID 到货 0 件）。现走**三路齐发**（各自幂等，任一路可用即生效）：\n'),
    ('Core/DungeonUI.lua',
     '地图标记（2026-09-22）：', '地图标记：'),
    ('Core/DungeonUI.lua',
     '副本入口标记（2026-09-24）：', '副本入口标记：'),

    # ───────────── ProfessionUI.lua ─────────────
    ('Core/ProfessionUI.lua',
     '-- ── 全部专业总览：三列导航宫格（方案 B）──',
     '-- ── 全部专业总览：三列导航宫格 ──'),
    ('Core/ProfessionUI.lua',
     '    -- 全部专业总览的三列导航宫格（方案 B）：同一套「行池外小部件」先例，',
     '    -- 全部专业总览的三列导航宫格：同一套「行池外小部件」先例，'),
    ('Core/ProfessionUI.lua',
     '    -- 职业加成对照总表（方案 A）：同一套「行池外小部件」先例，wantBonusTable 举手时',
     '    -- 职业加成对照总表：同一套「行池外小部件」先例，wantBonusTable 举手时'),
    ('Core/ProfessionUI.lua',
     '-------------------- 营地页 · 职业加成（全专业对照总表 · 方案 A）--------------------',
     '-------------------- 营地页 · 职业加成（全专业对照总表）--------------------'),
    ('Core/ProfessionUI.lua',
     '-- 「全部 → 总览」的正文（方案 B）：三列卡片 × 四个分组。',
     '-- 「全部 → 总览」的正文：三列卡片 × 四个分组。'),
    ('Core/ProfessionUI.lua',
     '    -- ── 全部专业总览：三列导航宫格（方案 B，帧一次建全，渲染期只摆位）──',
     '    -- ── 全部专业总览：三列导航宫格（帧一次建全，渲染期只摆位）──'),
    ('Core/ProfessionUI.lua',
     '    -- ── 营地：职业加成对照总表（方案 A，帧一次建全，渲染期只摆位）──',
     '    -- ── 营地：职业加成对照总表（帧一次建全，渲染期只摆位）──'),
    ('Core/ProfessionUI.lua',
     '        -- ★ 方案 B：下面整块换成「三列导航宫格」（PD.BuildIndexGrid，\n'
     '        --   渲染期由 PD.PaintRows 末尾按 wantIndexGrid 摆位）。原「营地对照表在左列…」\n'
     '        --   的指路文案挪进宫格尾部的灰字备注，这里不再重复。\n',
     '        -- ★ 下面整块换成「三列导航宫格」（PD.BuildIndexGrid，\n'
     '        --   渲染期由 PD.PaintRows 末尾按 wantIndexGrid 摆位）。\n'),
    ('Core/ProfessionUI.lua',
     '    -- ── 方案 B：左右双栏 + 段落卡 ──',
     '    -- ── 左右双栏 + 段落卡 ──'),
    ('Core/ProfessionUI.lua',
     '    PD.wantIndexGrid = false     -- 全部专业总览的三列导航宫格（方案 B）',
     '    PD.wantIndexGrid = false     -- 全部专业总览的三列导航宫格'),
    ('Core/ProfessionUI.lua',
     '    PD.wantBonusTable = false    -- 职业加成对照总表（方案 A）',
     '    PD.wantBonusTable = false    -- 职业加成对照总表'),
    ('Core/ProfessionUI.lua',
     '-- ★ 这一块原先整个没画（数据在、UI 不取）。它是「拿商人青睐换配方」的入口，\n'
     '--   对练级的人比单看配方更直接，故补成一档独立分类。\n'
     '-- ★ 这一档的货币译名统一叫「商人青睐」（数据侧注释与本行右侧同改）。\n',
     '-- ★ 「拿商人青睐换配方」的入口，对练级的人比单看配方更直接，独立成一档分类。\n'
     '-- ★ 这一档的货币译名统一叫「商人青睐」。\n'),
    ('Core/ProfessionUI.lua',
     '        -- ★ 总览重设计（方案 B）：专业详情走左右双栏\n'
     '        --   （左「是什么」= 简介 + 认证与称号 + 共同变化 + 营地三档；\n'
     '        --     右「数字速览」+ 里程碑），**每个内容块一张段落卡**（sec 编号 → PD.secCards）。\n'
     '        --   「全部专业」首页 方案 B：统计行之下换成三列导航宫格\n'
     '        --   （PD.BuildIndexGrid 一次建全，此处只举手，摆位在 PaintRows 末尾）。\n'
     '        --   ★ 营地三档放左栏收尾（原 span 通栏在左栏下方留出整片空白，实机被否）；\n',
     '        -- ★ 总览：专业详情走左右双栏\n'
     '        --   （左「是什么」= 简介 + 认证与称号 + 共同变化 + 营地三档；\n'
     '        --     右「数字速览」+ 里程碑），**每个内容块一张段落卡**（sec 编号 → PD.secCards）。\n'
     '        --   「全部专业」首页：统计行之下换成三列导航宫格\n'
     '        --   （PD.BuildIndexGrid 一次建全，此处只举手，摆位在 PaintRows 末尾）。\n'
     '        --   ★ 营地三档放左栏收尾；\n'),

    # ───────────── ExploreUI.lua ─────────────
    ('Core/ExploreUI.lua',
     '    -- ── 行内胶囊徽章（方案 A）：阵营/等级/推荐/待确认四枚小胶囊，',
     '    -- ── 行内胶囊徽章：阵营/等级/推荐/待确认四枚小胶囊，'),
    ('Core/ExploreUI.lua',
     '-- ── 行内胶囊徽章渲染（方案 A）：链式锚接（上一枚可见接其右 4px，',
     '-- ── 行内胶囊徽章渲染：链式锚接（上一枚可见接其右 4px，'),
    ('Core/ExploreUI.lua',
     '    -- ── 胶囊徽章链（方案 A）：极细 1px 描边、推荐无星；',
     '    -- ── 胶囊徽章链：极细 1px 描边、推荐无星；'),
    ('Core/ExploreUI.lua',
     '    -- ★ 方案 A：listCard = 右列**大底卡**——顶边抬到进度文本上方',
     '    -- ★ listCard = 右列**大底卡**——顶边抬到进度文本上方'),
    ('Core/ExploreUI.lua',
     '    -- listCard（右列大底卡）**常驻**：清单/奖励两态都当底板（方案 A）',
     '    -- listCard（右列大底卡）**常驻**：清单/奖励两态都当底板'),
    ('Core/ExploreUI.lua',
     '    -- ── 进度条（PROG 行整行宽，方案 C 形式）：无边框细条 + 金色填充 + 门槛刻度上下出头 ──',
     '    -- ── 进度条（PROG 行整行宽）：无边框细条 + 金色填充 + 门槛刻度上下出头 ──'),
    ('Core/ExploreUI.lua',
     '    -- ★ 方案 A：右列大底卡——从进度条上方整列包到页底，',
     '    -- ★ 右列大底卡——从进度条上方整列包到页底，'),

    # ───────────── Hui.lua ─────────────
    ('Core/Hui.lua',
     '    -- 危险动作红（MakeDangerButton 常底，同 OptionsHUI.lua 重置配置底色）',
     '    -- 危险动作红（MakeDangerButton 常底）'),
    ('Core/Hui.lua',
     '    -- ===== 主题色板（WorkBuddy 主题搬入；方案 B：借色相，亮度沿用骨架）=====',
     '    -- ===== 主题色板（借色相，亮度沿用骨架）====='),
    ('Core/Hui.lua',
     '    -- 层色快照缓存：窗口独立主题色的持续消费方（出价卡呼吸/常态/显灰驱动等）按 key',
     '    -- 层色快照缓存：窗口独立主题色的持续消费方按 key'),
    ('Core/Hui.lua',
     '        -- 切换前 accent 顶点色 RGB（供重染 SetTextColor(accent) 创建的文字，如个人buff滑条数值、设置页强调字）',
     '        -- 切换前 accent 顶点色 RGB（供重染 SetTextColor(accent) 创建的文字）'),
    ('Core/Hui.lua',
     '    -- scope=窗口作用域（auction/roleOverview），可传多个帧树根（如出价看板主窗与预览容器\n'
     '    -- 是两棵互不相连的树，须同轮重染）；作用域主题为 classic 时无需处理。\n',
     '    -- scope=窗口作用域，可传多个帧树根（互不相连的树须同轮重染）；作用域主题为 classic 时无需处理。\n'),
    ('Core/Hui.lua',
     '    -- 切主题时统一重设文本/字色，免 RL、免开关界面。用法\n'
     '    -- ns.hui.SetThemeText(fs, function() return "|cff" .. ns.hui.TextHex("00FF00", "accent") .. L["心愿"] .. RR end)\n',
     '    -- 切主题时统一重设文本/字色，免 RL、免开关界面。\n'),
    ('Core/Hui.lua',
     '    -- 主题文字热切换（自动、覆盖全）：遍历所有已登记顶层帧（主表 + 设置窗 + OptionsHUI 窗等）整棵 UI 树',
     '    -- 主题文字热切换（自动、覆盖全）：遍历所有已登记顶层帧整棵 UI 树'),
    ('Core/Hui.lua',
     '    -- (b) 顶点色 SetTextColor(accent) 的文字（个人buff滑条数值、设置页选中项/强调字等）。',
     '    -- (b) 顶点色 SetTextColor(accent) 的文字。'),
    ('Core/Hui.lua',
     '    -- ⚠️ 必须是「4 角 + 上下边条 + 全宽中条」的完整结构（同 OptionsHUI.lua BuildCapsule）',
     '    -- ⚠️ 必须是「4 角 + 上下边条 + 全宽中条」的完整结构'),
    ('Core/Hui.lua',
     ' end -- ：角色总览双卡分层需要', ' end', 2),
    ('Core/Hui.lua',
     '        -- 自动主界面透明度联动：BuildRoundedBG 的 frame 为 ns.MainFrame 自身或其后代时\n'
     '        -- （记录本子页卡/心愿卡/拍卖卡/装备库卡等主界面卡片原语），自动注册随设置页\n',
     '        -- 自动主界面透明度联动：BuildRoundedBG 的 frame 为 ns.MainFrame 自身或其后代时\n'
     '        -- （主界面卡片原语），自动注册随设置页\n'),
    ('Core/Hui.lua',
     '    -- 覆盖面与经典 UpdateAlpha 对齐：主面板 L0 皮 + 拍卖记录/装备过期抽屉底；',
     '    -- 覆盖面与经典 UpdateAlpha 对齐：主面板 L0 皮 + 各抽屉底；'),
    ('Core/Hui.lua',
     '    -- 子控件随主界面透明度联动。独立窗口/浮窗/看板（RoleOverview / 监控浮窗 / 拍卖WA 看板 /\n'
     '    -- PA 等挂在 UIParent 下）天然不命中，不受主界面透明度影响\n',
     '    -- 子控件随主界面透明度联动。独立窗口/浮窗/看板（挂在 UIParent 下）天然不命中，不受主界面透明度影响\n'),
    ('Core/Hui.lua',
     '    -- 皮未创建时无注册项，静默跳过，创建时按存档值取新透明度（角色总览 UpdateFBCDAlpha 同款）。',
     '    -- 皮未创建时无注册项，静默跳过，创建时按存档值取新透明度。'),
    ('Core/Hui.lua',
     '    -- 阶段 3 批①第⑥步：自建弹窗/面板统一 hui 皮（参照 Trade/Mail 详情弹窗定稿）',
     '    -- 自建弹窗/面板统一 hui 皮'),
    ('Core/Hui.lua',
     '        -- noBorder：跳过 1px 细描边——自绘主界面同款 2px 蓝外框的窗\n'
     '        -- （角色总览主窗）必须传 true，防「细白边+粗蓝框」双框（主窗 L0 蓝框不加描边同款铁律）。\n',
     '        -- noBorder：跳过 1px 细描边——自绘主界面同款 2px 蓝外框的窗必须传 true，\n'
     '        -- 防「细白边+粗蓝框」双框。\n'),
    ('Core/Hui.lua',
     '        -- 描边贴图表挂到帧上（阶段3尾巴）：调用方需要语义状态染色时复用（如记账预览窗\n'
     '        -- 超上限红/可交易绿、出价框 关注蓝/心愿绿）；重申默认色见 repaintBorder，动态染色见\n'
     '        -- Trade.lua / AuctionWA SetFrameColor。covers（粗框角部内盘）不入此表——随皮底色不随描边色\n',
     '        -- 描边贴图表挂到帧上：调用方需要语义状态染色时复用；重申默认色见 repaintBorder。\n'
     '        -- covers（粗框角部内盘）不入此表——随皮底色不随描边色\n'),
    ('Core/Hui.lua',
     '        -- 各皮令牌 alpha 不变）——装备库/预设价格/记录本/团长助手等弹窗族面板全覆盖；\n'
     '        -- 独立窗口（角色总览自带 roleOverviewAlpha、拍卖WA看板、团队BUFF监控浮窗自带\n'
     '        -- 背景透明度）显式传 noAlpha=true 排除。注册须在 repaintFill/OnShow 之后（重申\n',
     '        -- 各皮令牌 alpha 不变）——各弹窗族面板全覆盖；\n'
     '        -- 独立窗口（自带背景透明度）显式传 noAlpha=true 排除。注册须在 repaintFill/OnShow 之后（重申\n'),
    ('Core/Hui.lua',
     '    -- （L_DropDownList4..20）的换肤 hook 静默不装（与 OptionsHUI SkinMenus 同款坑）',
     '    -- （L_DropDownList4..20）的换肤 hook 静默不装'),
    ('Core/Hui.lua',
     '    -- 阶段 3 批①第 2 步：页签内容区 L1 面板（#2b2b2b、8px 圆角）。',
     '    -- 页签内容区 L1 面板（#2b2b2b、8px 圆角）。'),
    ('Core/Hui.lua',
     '    -- 阶段 3 批①第 3 步：BOSS/功能区块卡片（默认 L2 #363636、6px 圆角）。',
     '    -- BOSS/功能区块卡片（默认 L2 #363636、6px 圆角）。'),
    ('Core/Hui.lua',
     '    -- ===== 文字令牌（阶段 3 批③·装备库文字适配；UI重构方案 2.2 节四级文字色）=====',
     '    -- ===== 文字令牌（四级文字色）====='),
    ('Core/Hui.lua',
     '    ns.hui.CARD_BORDER = C_CARD_BORDER -- 卡片描边默认色（阶段3尾巴导出：描边状态染色后还原用）',
     '    ns.hui.CARD_BORDER = C_CARD_BORDER -- 卡片描边默认色（描边状态染色后还原用）'),
    ('Core/Hui.lua',
     '    -- 出价框分项字体描边（设置-现代风格设置-字体描边）的跨模块取值桥：出价框与自动拍卖记录的\n'
     '    -- 「装等」「装绑」角标共用同一组分项开关（存档键 bidOutlineLevel / bidOutlineBind）。\n',
     '    -- 分项字体描边的跨模块取值桥：「装等」「装绑」角标共用同一组分项开关\n'
     '    -- （存档键 bidOutlineLevel / bidOutlineBind）。\n'),
    ('Core/Hui.lua',
     '    -- 物品数量文字的字体 flags（记录本 → 交易记录/邮件记录 各自的「物品数量描边」设置项控制）。\n'
     '    -- 两个模块各有独立存档键：\n'
     '    --   ns.options.tradeItemCountOutline（交易记录）默认 1\n'
     '    --   ns.options.mailItemCountOutline （邮件记录）默认 1\n',
     '    -- 物品数量文字的字体 flags（调用方各自的「物品数量描边」设置项控制）。\n'
     '    -- 两个存档键各有独立开关：\n'
     '    --   ns.options.tradeItemCountOutline 默认 1\n'
     '    --   ns.options.mailItemCountOutline  默认 1\n'),
    ('Core/Hui.lua',
     '    -- 全局 GameTooltip 换肤（阶段 3 ①方案第七节 #9：L1 底 + #3A3A3A 细边、圆角 8）。',
     '    -- 全局 GameTooltip 换肤：L1 底 + #3A3A3A 细边、圆角 8。'),
    ('Core/Hui.lua',
     '    -- 动作按钮换肤（阶段 3 ①主界面族）：暗灰圆角底 + 灰圆角描边 + 白字（去 OUTLINE），悬停只变边框为主题绿。',
     '    -- 动作按钮换肤：暗灰圆角底 + 灰圆角描边 + 白字（去 OUTLINE），悬停只变边框为主题绿。'),
    ('Core/Hui.lua',
     '    -- 红底必须倒圆角（同描边半径 6，方块底会从圆角描边四角露出，同 OptionsHUI.lua MakeDanger 教训）',
     '    -- ⚠️ 红底必须倒圆角（同描边半径 6）：方块底会从圆角描边四角露出'),
    ('Core/Hui.lua',
     '    -- 主题绿主行动按钮（拍卖记录多选「开始拍卖/取消选择」）',
     '    -- 主题绿主行动按钮'),
    ('Core/Hui.lua',
     '    -- 复选框 → iOS 式开关（阶段 3）：36×20 胶囊轨，关=灰轨+黑钮左 / 开=绿轨+黑钮右（单点实现）。',
     '    -- 复选框 → iOS 式开关：36×20 胶囊轨，关=灰轨+黑钮左 / 开=绿轨+黑钮右（单点实现）。'),
    ('Core/Hui.lua',
     '    -- 经 ns.hui 适配层统一出口，所有模块（工资抹零/拍卖记录类型/自动生成账单等）统一调用；主题守卫由调用方处理。',
     '    -- 经 ns.hui 适配层统一出口，所有模块统一调用；主题守卫由调用方处理。'),
    ('Core/Hui.lua',
     '    -- 数值滑块换肤（阶段 3 ②团长助手族 / 设置页共用，单点实现）：圆形把手(HUICircle) + 灰余轨 + 绿已选段',
     '    -- 数值滑块换肤（设置页共用，单点实现）：圆形把手(HUICircle) + 灰余轨 + 绿已选段'),
]


def main():
    data = {}
    for item in EDITS:
        f, old, new = item[0], item[1], item[2]
        exp = item[3] if len(item) > 3 else 1
        if f not in data:
            raw = open(f, 'rb').read().decode('utf-8')
            crlf = '\r\n' in raw
            data[f] = [raw.replace('\r\n', '\n') if crlf else raw, crlf]
        txt = data[f][0]
        n = txt.count(old)
        if n != exp:
            sys.exit('FAIL %s: 命中 %d 次（期望 %d）：%r' % (f, n, exp, old[:60]))
        data[f][0] = txt.replace(old, new)

    for f, (txt, crlf) in data.items():
        if crlf:
            txt = txt.replace('\n', '\r\n')
        open(f, 'wb').write(txt.encode('utf-8'))
        print('OK', f, 'CRLF' if crlf else 'LF')


if __name__ == '__main__':
    main()

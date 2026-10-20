# -*- coding: utf-8 -*-
"""生成 DungeonsForever/Locales/zhTW.lua（繁体客户端文案 · 生成物）。

链路（2026-09-25 本地化方案第 3 步）：
  1. 按加载序扫 Core/*.lua 里所有 L["…"] 的键（键 = 简体文案）；
  2. 先过 TW 术语词表（简体词 → 台湾惯用词，直出繁体，避开 opencc 只管字形不管用语）；
  3. 其余过 opencc s2t 做简→繁；
  4. 转换前后相同的条目跳过（zhTW 客户端下 zhCN.lua 已早退，未覆盖键由 __index
     回退键名本身，简体键=繁体值时无需登记）。

人工校对发现错译 → 修 GLOSSARY（或加例外表）后重跑本脚本，禁止手改 zhTW.lua。

用法：python gen_zhtw.py
"""
import os
import re
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
DF = os.path.dirname(HERE)
DST = os.path.join(DF, 'Locales', 'zhTW.lua')

# 与 DungeonsForever.toc 的 Core 加载序一致（首见顺序 = 输出顺序）
SCAN_FILES = [
    'Core/DungeonUI.lua',
    # 2026-10-08 补缺口：PvP 军衔页 / 专业升级 HUD 也在用 L["…"]，原先漏扫
    'Core/PvPUI.lua',
    'Core/FactionUI.lua',
    'Core/MapUI.lua',
    'Core/ProfessionUI.lua',
    'Core/ProfRouteAuto.lua',   # 2026-10-08 新增：专业升级自动路线（拍卖行价格）
    'Core/AuctionatorBridge.lua',   # 2026-10-08 新增：Auctionator 桥接（购物清单一键导入）
    'Core/ProfFollow.lua',
    'Core/ExploreUI.lua',
    'Core/ExploreMap.lua',
    'Core/CollectionUI.lua',   # 2026-10-08 补缺口：藏品页 L 键原先漏扫（来源：/ 等 %d 处）
    'Core/BisUI.lua',
    'Core/RaidUI.lua',
    'Core/GearUI.lua',
    'Core/MainFrame.lua',
    'Core/Hui.lua',
    'Core/Core.lua',
    # 2026-09-30 补缺口：这四件也在用 L["…"]，原先漏扫 ⇒ 重跑会误删它们的键
    'Core/LootFilter.lua',
    'Core/LootFilterUI.lua',
    'Core/TierUI.lua',
    'Core/ClassCombatUI.lua',
    'Core/ClassQuestUI.lua',
    'Core/QuickBar.lua',
]

KEY = re.compile(r'L\["([^"]+)"\]')

# TW 用语词表（简体词 → 台湾惯用繁体词；先于 opencc 整词替换）。
# 校对发现的错译都回填到这里 —— 本脚本是繁体文案的唯一源头。
GLOSSARY = {
    '服务器': '伺服器',
    '界面': '介面',
    '设置': '設定',
    '默认': '預設',
    '鼠标': '滑鼠',
    '数据': '資料',
    '信息': '資訊',
    '消息': '訊息',
    '支持': '支援',
    '网络': '網路',
    '缓存': '快取',
    '内存': '記憶體',
    '保存': '儲存',
    '加载': '載入',
    '搜索': '搜尋',
    'BOSS': '首領',  # zhTW 惯用「首領」；只影响大写 BOSS 的键（如 " · BOSS %d"）
}

cc = None
GLOSS_RE = re.compile('|'.join(re.escape(k) for k in sorted(GLOSSARY, key=len, reverse=True)))


def require_opencc():
    global cc
    if cc is None:
        try:
            from opencc import OpenCC
        except ImportError as exc:
            raise RuntimeError('OpenCC is required for zhTW conversion; install opencc-python-reimplemented') from exc
        cc = OpenCC('s2t')
    return cc


def to_tw(s):
    s = GLOSS_RE.sub(lambda m: GLOSSARY[m.group(0)], s)
    # opencc 会把「为」转成异体「爲」；台湾惯用「為」，统一替换
    # opencc 同样会把「群」转成异体「羣」（QQ群 等）；台湾惯用「群」，统一替换
    return require_opencc().convert(s).replace('爲', '為').replace('羣', '群')


def main():
    keys = []
    seen = set()
    for rel in SCAN_FILES:
        path = os.path.join(DF, rel)
        if not os.path.exists(path):
            sys.exit('扫描清单里的文件不存在：%s' % rel)
        src = open(path, 'rb').read().decode('utf-8')
        for k in KEY.findall(src):
            if k not in seen:
                seen.add(k)
                keys.append((rel, k))

    entries = []
    skipped = 0
    for rel, k in keys:
        v = to_tw(k)
        if v == k:
            skipped += 1
            continue
        entries.append((k, v))

    head = '''local _, ns = ...
if (GetLocale() ~= "zhTW") then return end
local L = ns.L'''
    body = '\n'.join('L["%s"] = "%s"' % (k, v) for k, v in entries)
    out = head + '\n\n' + body + '\n'
    open(DST, 'wb').write(out.encode('utf-8'))
    print('扫描 %d 个键；繁体≠简体登记 %d 条；转换恒等跳过 %d 条（走键名回退）'
          % (len(keys), len(entries), skipped))


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
# 乌尔之书 / 乔丹铁锤 对调（用户实机第三次标位定案）：
#   乔丹铁锤 6895 = 第 1 层 (37.3,53.8)（庭院铁匠铺）
#   乌尔之书 6283 = 第 6 层 (47.2,79.3)（阿鲁高档）
import io


def rd(p):
    return io.open(p, encoding='utf-8', newline='').read()


def wr(p, s):
    io.open(p, 'w', encoding='utf-8', newline='').write(s)


def rep1(src, old, new, tag):
    n = src.count(old)
    assert n == 1, '%s: hit %d' % (tag, n)
    return src.replace(old, new, 1)


# ---------- 1) 生成器 ----------
p = 'fc_pins.py'
s = rd(p)
s = rep1(s, """#     实机（用户两张截图标位）核准：
#       (37.3,53.8) = 乌尔之书 6283（第 1 层，原 BossPos 把乔丹铁锤摆这里当 boss，已删）
#       (47.2,79.3) = 乔丹铁锤 6895（第 6 层）
#   ⇒ 干脆按坐标登记，不再信 slug。
OBJ_BY_COORD = {
    37.3: (6283, None),
    47.2: (6895, 6),
}""", """#     实机（用户实机查验定案，2026-10-04 第三轮对调）：
#       (37.3,53.8) = 乔丹铁锤 6895（第 1 层庭院铁匠铺；曾误摆 BossPos 当 boss，已删）
#       (47.2,79.3) = 乌尔之书 6283（第 6 层阿鲁高档）
#   ⇒ 干脆按坐标登记，不再信 slug。
OBJ_BY_COORD = {
    37.3: (6895, None),
    47.2: (6283, 6),
}""", 'fc OBJ')
wr(p, s)
print('fc_pins.py 对调完成')

# ---------- 2) 动态断言：数据抽查 ----------
p = 'df_dungeon_check.py'
s = rd(p)
s = rep1(s, """      ck("★★ 图钉扩展数据抽查：影牙 2 物品钉 = 乌尔之书 6283@第1层(37.3,53.8) + 乔丹铁锤 6895@第6层(47.2,79.3)"
         .. "（fc slug 与坐标交叉，实机两轮标位核准）/ 监狱 / 死矿 / 侏儒 = 0（稀有已并入 BossPos）/ 洛丹伦 2",
         #(_MM.ExtraPinsFor("shadowfang_keep", nil) or {}) == 2
         and (_MM.ExtraPinsFor("shadowfang_keep", 1) or {})[1].id == 6283
         and (_MM.ExtraPinsFor("shadowfang_keep", 6) or {})[1].id == 6895""",
"""      ck("★★ 图钉扩展数据抽查：影牙 2 物品钉 = 乔丹铁锤 6895@第1层(37.3,53.8) + 乌尔之书 6283@第6层(47.2,79.3)"
         .. "（fc slug 与坐标交叉，实机三轮标位定案）/ 监狱 / 死矿 / 侏儒 = 0（稀有已并入 BossPos）/ 洛丹伦 2",
         #(_MM.ExtraPinsFor("shadowfang_keep", nil) or {}) == 2
         and (_MM.ExtraPinsFor("shadowfang_keep", 1) or {})[1].id == 6895
         and (_MM.ExtraPinsFor("shadowfang_keep", 6) or {})[1].id == 6283""", 'dyn spot')

# ---------- 3) 动态断言：影牙第 1 层 / 第 6 层 ----------
s = rep1(s, """        local _book1 = false
        for _i = 1, _M.MAX_PINS do
          if _fs.pinBtns[_i].__shown and _fs.pinBtns[_i].__kind == "object"
             and _fs.pinBtns[_i].__p and _fs.pinBtns[_i].__p.id == 6283 then _book1 = true end
        end
        ck("★★ 影牙第 1 层（庭院）只画本层钉点：4 点 = 3 boss（雷希戈尔/影马/斯普林瓦尔）"
           .. " + 乌尔之书（物品钉 6283@(37.3,53.8)，用户标位）—— 乔丹铁锤非 boss 已从 BossPos 删除（2026-10-04）",
           _c1 == 4 and _e1 == "Rethilgore" and _book1, _c1 .. "/" .. tostring(_e1))""",
"""        local _book1 = false
        for _i = 1, _M.MAX_PINS do
          if _fs.pinBtns[_i].__shown and _fs.pinBtns[_i].__kind == "object"
             and _fs.pinBtns[_i].__p and _fs.pinBtns[_i].__p.id == 6895 then _book1 = true end
        end
        ck("★★ 影牙第 1 层（庭院）只画本层钉点：4 点 = 3 boss（雷希戈尔/影马/斯普林瓦尔）"
           .. " + 乔丹铁锤（物品钉 6895@(37.3,53.8)，庭院铁匠铺）—— 乔丹铁锤非 boss 已从 BossPos 删除（2026-10-04）",
           _c1 == 4 and _e1 == "Rethilgore" and _book1, _c1 .. "/" .. tostring(_e1))""", 'dyn f1')

s = rep1(s, """            if _fs.pinBtns[_i].__kind == "object" and _fs.pinBtns[_i].__p
               and _fs.pinBtns[_i].__p.id == 6895 then _book6 = true end
          end
        end
        ck("★★ 切到第 6 层（阿鲁高的房间）→ 芬鲁斯/狼王南杜斯/大法师阿鲁高 + 乔丹铁锤（物品钉 6895，实为该层物件）4 点，阿鲁高在列",
           _c6 == 4 and _has6 and _book6, _c6)""",
"""            if _fs.pinBtns[_i].__kind == "object" and _fs.pinBtns[_i].__p
               and _fs.pinBtns[_i].__p.id == 6283 then _book6 = true end
          end
        end
        ck("★★ 切到第 6 层（阿鲁高的房间）→ 芬鲁斯/狼王南杜斯/大法师阿鲁高 + 乌尔之书（物品钉 6283，阿鲁高档）4 点，阿鲁高在列",
           _c6 == 4 and _has6 and _book6, _c6)""", 'dyn f6')

# ---------- 4) 静态断言：Data_MapPins 抽查 ----------
s = rep1(s, """ck('★★ ㊲b Data_MapPins：3 个副本登记 + 关键 ID 抽查（任务 96395/98423/95250、'
   '乌尔之书 6283@第1层、乔丹铁锤 6895@第6层）+ 稀有/假 ID 必须已清（6228/3586/3872）',""",
"""ck('★★ ㊲b Data_MapPins：3 个副本登记 + 关键 ID 抽查（任务 96395/98423/95250、'
   '乔丹铁锤 6895@第1层、乌尔之书 6283@第6层）+ 稀有/假 ID 必须已清（6228/3586/3872）',""", 'static head')
s = rep1(s, """   and '{ 37.3, 53.8, 6283 }' in _pins_src
   and '{ 47.2, 79.3, 6895, 6 }' in _pins_src)""",
"""   and '{ 37.3, 53.8, 6895 }' in _pins_src
   and '{ 47.2, 79.3, 6283, 6 }' in _pins_src)""", 'static ids')
wr(p, s)
print('df_dungeon_check.py 三段断言对调完成')

# -*- coding: utf-8 -*-
# 终验（2026-10-09 配方搜索 + 列宽）：我的改动全部在场 + 源/副本 md5 对账
import hashlib

s = open(r'D:\workspace\DungeonsForever\Core\ProfessionUI.lua', 'rb').read()
b = open(r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever\Core\ProfessionUI.lua',
         'rb').read()

marks = [
    'PD.RECIPE_NAME_MIN, PD.RECIPE_NAME_MAX = 118',
    'function PD.SearchReserve',
    'function PD.SearchHit',
    'function PD.SearchFilter',
    'function PD.FitRecipeCols',
    'PD.searchBox = sb',
    'local list = PD.SearchFilter(PD.RecipeList())',
    '没有名称或材料匹配',
    'PD.RIGHT_W - ((row == 0) and PD.SearchReserve() or 0)',
    'PD.searchQ = nil',
]
sc = s.decode('utf-8')
bad = [m for m in marks if m not in sc]
print('改动在场检查：', '全部 10 处 OK' if not bad else ('缺失 %r' % bad))
print('md5 源  =', hashlib.md5(s).hexdigest())
print('md5 副本=', hashlib.md5(b).hexdigest())
print('一致' if s == b else '不一致!')

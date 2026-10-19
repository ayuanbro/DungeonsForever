# -*- coding: utf-8 -*-
"""Data_ProfRecipes 分片化守卫。

防止「重跑生成器把分片结构静默冲回 monolithic」：
  1) 静态：三份文件（基线 + enUS/zhTW 覆盖层）必须含分片骨架与 9 个分片；
  2) 行为：基线文件在离线 Lua 里加载后，必须「未取用=未构建」，
     且 ns.EnsureProfRecipes({...}) 只构建指定分片。

用法：python qa_prof_split.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lupa import lua51  # noqa: E402

ADDON = (os.environ.get('DF_ADDON_ROOT')
         or r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever')
RELS = [
    'Core/Data/Data_ProfRecipes.lua',
    'Core/Data/enUS/Data_ProfRecipes.lua',
    'Core/Data/zhTW/Data_ProfRecipes.lua',
]
KEYS = ['alchemy', 'blacksmithing', 'enchanting', 'engineering',
        'leatherworking', 'tailoring', 'cooking', 'poisons', 'comprehension']
MARKS = ['local PARTS = {}', 'local KEYS = {}', 'local HAND = {',
         'ns.ProfRecipeKeys = KEYS',
         'ns.ProfRecipes = setmetatable({}, {',
         '__index = function(t, k)', 'PARTS[k] = nil',
         'ns.EnsureProfRecipes = function(keys)']

FAILED = []
PASSED = []


def ck(name, ok, extra=None):
    (PASSED if ok else FAILED).append(name)
    print('  [%s] %s%s' % ('OK ' if ok else 'FAIL', name,
                           '' if extra is None else '  [%s]' % extra))
    return ok


def read(rel):
    with open(os.path.join(ADDON, rel), encoding='utf-8', errors='replace') as f:
        return f.read().replace('\r\n', '\n')


def static_pass():
    print('=' * 72)
    print('静态：三份文件的分片骨架')
    print('=' * 72)
    for rel in RELS:
        try:
            src = read(rel)
        except OSError as e:
            ck('%s 可读' % rel, False, e)
            continue
        miss = [m for m in MARKS if m not in src]
        ck('%s 含全部分片骨架（%d 项）' % (rel, len(MARKS)), not miss, ','.join(miss))
        n = src.count('= function() return {')
        ck('%s 分片数 = 9' % rel, n == 9, n)
        absent = [k for k in KEYS if ('PARTS["%s"] = function() return {' % k) not in src]
        ck('%s 9 个专业键齐全' % rel, not absent, ','.join(absent))
        ck('%s 已无 monolithic 顶层表（ns.ProfRecipes = {）' % rel,
           '\nns.ProfRecipes = {\n' not in src)


def behavior_pass():
    print('=' * 72)
    print('行为：惰性构建（基线文件离线加载）')
    print('=' * 72)
    src = read(RELS[0])
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    lua.globals()['NS'] = lua.table()
    lua.globals()['SRC'] = src
    try:
        lua.execute('local f = assert(loadstring(SRC, "@Data_ProfRecipes.lua")) f(nil, NS)')
    except Exception as e:
        ck('基线文件离线加载', False, str(e)[:200])
        return
    ck('基线文件离线加载', True)

    got = str(lua.eval('table.concat(NS.ProfRecipeKeys, ",")'))
    ck('ProfRecipeKeys 清单 = 9 项且顺序一致', got == ','.join(KEYS), got[:60])

    lazy = lua.eval('rawget(NS.ProfRecipes, "alchemy") == nil'
                    ' and rawget(NS.ProfRecipes, "enchanting") == nil'
                    ' and rawget(NS.ProfRecipes, "leatherworking") == nil')
    ck('★ 加载后未取用分片全部未构建（惰性成立）', lazy is True or lazy == 1,
       str(lazy))

    only = lua.eval('NS.EnsureProfRecipes({ "enchanting", "leatherworking" }) ~= nil'
                    ' and rawget(NS.ProfRecipes, "enchanting") ~= nil'
                    ' and rawget(NS.ProfRecipes, "leatherworking") ~= nil'
                    ' and rawget(NS.ProfRecipes, "alchemy") == nil'
                    ' and rawget(NS.ProfRecipes, "tailoring") == nil')
    ck('★ 指定分片预热只构建那两片（alchemy/tailoring 仍懒）', only is True or only == 1,
       str(only))

    data = lua.eval('type(NS.ProfRecipes.enchanting.enchants) == "table"'
                    ' and #NS.ProfRecipes.enchanting.enchants > 0')
    ck('★ enchanting.enchants 可取且非空（Bis 附魔依赖）', data is True or data == 1,
       str(data))

    lw = lua.eval('type(NS.ProfRecipes.leatherworking.rows) == "table"'
                  ' and #NS.ProfRecipes.leatherworking.rows > 0')
    ck('★ leatherworking.rows 可取且非空（制皮护甲片依赖）', lw is True or lw == 1,
       str(lw))

    full = lua.eval('(function() local t = NS.EnsureProfRecipes() local n = 0'
                    ' for i = 1, #NS.ProfRecipeKeys do'
                    ' if rawget(t, NS.ProfRecipeKeys[i]) ~= nil then n = n + 1 end end'
                    ' return n end)()')
    ck('不带参调 EnsureProfRecipes() = 全量 9 片（向后兼容）', full == 9, full)


def main():
    static_pass()
    behavior_pass()
    print('=' * 72)
    print('结论')
    print('=' * 72)
    print('通过 %d / 失败 %d' % (len(PASSED), len(FAILED)))
    for n in FAILED:
        print('  ✗ ' + n)
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())

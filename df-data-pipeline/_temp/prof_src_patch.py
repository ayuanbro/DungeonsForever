# -*- coding: utf-8 -*-
"""配方来源补丁（QuestieDB 第 4 源）—— 独立于 fc_gen.py 全量重生成（其缓存旧，
重跑会冲掉并行会话的新数据），本脚本只对 Data_ProfRecipes.lua 的 source 字段做
setdefault 式补全：formula 图纸物品 → item npcDrops / vendors → source。

幂等可重跑：已有 drops/vendors 的配方不覆盖。
"""
import json
import os
import re
import sys

from lupa import lua51

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
QJ = json.load(open(os.path.join(HERE, 'questie', 'questie_forever.json'),
                    encoding='utf-8'))
NDROPS = QJ.get('item_npcDrops') or {}
NVEND = QJ.get('item_vendors') or {}
NINFO = QJ.get('npc_info') or {}

AZZ = {}
_p = os.path.join(HERE, '_wago_AreaTable_zh.csv')
if os.path.exists(_p):
    for ln in open(_p, encoding='utf-8'):
        parts = ln.split(',')
        if len(parts) > 2 and parts[0].isdigit():
            AZZ[int(parts[0])] = parts[2].strip()

LUA_KEYWORDS = {'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for',
                'function', 'if', 'in', 'local', 'nil', 'not', 'or', 'repeat',
                'return', 'then', 'true', 'until', 'while'}
IDENT = re.compile(r'^[A-Za-z_]\w*$')


def lit(v):
    if v is None:
        return 'nil'
    if v is True:
        return 'true'
    if v is False:
        return 'false'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return repr(v)
    if isinstance(v, str):
        out = []
        for ch in v:
            if ch == '\\':
                out.append('\\\\')
            elif ch == '"':
                out.append('\\"')
            elif ord(ch) < 32:
                out.append(' ')
            else:
                out.append(ch)
        return '"' + ''.join(out) + '"'
    if isinstance(v, list):
        if not v:
            return '{}'
        return '{ ' + ', '.join(lit(x) for x in v) + ' }'
    if isinstance(v, dict):
        if not v:
            return '{}'
        parts = []
        for k, val in v.items():
            kk = k if (IDENT.match(str(k)) and k not in LUA_KEYWORDS) else '["%s"]' % k
            parts.append('%s=%s' % (kk, lit(val)))
        return '{ ' + ', '.join(parts) + ' }'
    sys.exit('prof_src_patch: 无法序列化的类型 %r' % type(v))


_RT = lua51.LuaRuntime()
LTABLE = type(_RT.table())


def to_py(v):
    if isinstance(v, LTABLE):
        n = len(v)
        if n > 0:
            return [to_py(v[i]) for i in range(1, n + 1)]
        d = {}
        for k, val in v.items():
            d[str(k)] = to_py(val)
        return d
    return v


def patch_row(rec, stat):
    f = rec[12] if len(rec) > 12 else None
    fid = f[0] if isinstance(f, list) and f else None
    if not fid:
        return
    src = rec[13] if len(rec) > 13 else None
    if not isinstance(src, dict):
        src = {}
    if not src.get('drops'):
        ids = NDROPS.get(str(fid)) or []
        if ids:
            src['drops'] = [{
                'npc': (NINFO.get(str(i)) or ['#' + str(i)])[0],
                'zone': AZZ.get(NINFO.get(str(i), [None]*4)[3], '') if NINFO.get(str(i)) else '',
                'chance': None,
                'lv': [x for x in (NINFO.get(str(i)) or [None, None])[1:3] if x is not None],
                'id': int(i),
            } for i in ids]
            stat['d'] += 1
    if not src.get('vendors'):
        ids = NVEND.get(str(fid)) or []
        if ids:
            src['vendors'] = [{
                'name': (NINFO.get(str(i)) or ['#' + str(i)])[0],
                'zone': AZZ.get(NINFO.get(str(i), [None]*4)[3], '') if NINFO.get(str(i)) else '',
                'cost': '',
                'skill': None,
                'id': int(i),
            } for i in ids]
            stat['v'] += 1
    rec[13] = src


def load_lua(path):
    rt = lua51.LuaRuntime()
    head = open(path, encoding='utf-8').read(2048)
    loc = re.search(r"[~]=\s*[\"'](\w+)[\"']\s*(?:then|and)", head)
    want = loc.group(1) if loc else 'zhCN'
    rt.execute('function GetLocale() return "%s" end; ns = {}' % want)
    code = open(path, encoding='utf-8').read()
    code = code.replace('local _, ns = ...', 'local _, ns = nil, _G["ns"]')
    rt.execute(code)
    if rt.globals().ns.EnsureProfRecipes is None:
        raise SystemExit('prof_src_patch: %s 加载后 EnsureProfRecipes 为 nil' % path)
    rt.execute('ns.EnsureProfRecipes()')
    return rt, rt.globals().ns.ProfRecipes


def prof_key_order(txt):
    return re.findall(r'^    \["(\w+)"\] = \{', txt, re.M)


def rebuild(txt, proftab, stat):
    keys = prof_key_order(txt)
    i = txt.index('ns.ProfRecipes = {\n') + len('ns.ProfRecipes = {\n')
    head = txt[:i]
    out = [head]
    for pk in keys:
        prof = proftab[pk]
        p = to_py(prof)
        out.append('    ["%s"] = {\n' % pk)
        out.append('        word = %s,\n' % lit(p.get('word')))
        out.append('        counts = %s,\n' % lit(p.get('counts') or {}))
        g = p.get('groups') or []
        if g:
            out.append('        groups = {\n')
            for it in g:
                out.append('            %s,\n' % lit(it))
            out.append('        },\n')
        else:
            out.append('        groups = {},\n')
        rows = p.get('rows') or []
        out.append('        rows = {\n')
        for rec in rows:
            patch_row(rec, stat)
            out.append('            %s,\n' % lit(rec))
        out.append('        },\n')
        out.append('    },\n')
    out.append('}\nreturn ns.ProfRecipes\nend\n')
    return ''.join(out)


def main():
    targets = [
        'Core/Data/Data_ProfRecipes.lua',
        'Core/Data/zhTW/Data_ProfRecipes.lua',
        'Core/Data/enUS/Data_ProfRecipes.lua',
    ]
    for rel in targets:
        path = os.path.join(ROOT, rel)
        raw0 = open(path, 'rb').read()
        crlf = b'\r\n' in raw0
        txt = raw0.decode('utf-8').replace('\r\n', '\n')
        rt, proftab = load_lua(path)
        stat = {'d': 0, 'v': 0}
        body = rebuild(txt, proftab, stat)
        raw = body.encode('utf-8')
        if crlf and not raw.endswith(b'\r\n\r\n'):
            raw = raw[:-1].replace(b'\n', b'\r\n') + b'\r\n'
        open(path, 'wb').write(raw)
        print('%s: 掉落 +%d 商人 +%d' % (rel, stat['d'], stat['v']))
    return 0


if __name__ == '__main__':
    sys.exit(main())

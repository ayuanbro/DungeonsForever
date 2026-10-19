# -*- coding: utf-8 -*-
# 2026-10-10 五轮：|T...|t 图标序列被 TextW/Fit 逐字节量宽 → 路线页次数列宽爆炸、右半内容被挤出
# Hui.lua = CRLF。
import sys

P = 'Core/Hui.lua'

OLD = (
    'function ns.hui.TextW(text, fs)\r\n'
    '    if type(text) ~= "string" then return 0 end\r\n'
    '    local w, i, n = 0, 1, #text\r\n'
    '    while i <= n do\r\n'
    '        local _, step, k = HCharStep(text, i)\r\n'
    '        w = w + k * fs\r\n'
    '        i = i + step\r\n'
    '    end\r\n'
    '    return w\r\n'
    'end\r\n'
    '\r\n'
    'function ns.hui.Fit(text, fs, width)\r\n'
    '    if type(text) ~= "string" then return "" end\r\n'
    '    if ns.hui.TextW(text, fs) <= width then return text end\r\n'
    '    local out, w, i, n = "", 0, 1, #text\r\n'
    '    while i <= n do\r\n'
    '        local ch, step, k = HCharStep(text, i)\r\n'
    '        local cw = k * fs\r\n'
    '        if w + cw > width - fs then break end\r\n'
    '        out = out .. ch\r\n'
    '        w = w + cw\r\n'
    '        i = i + step\r\n'
    '    end\r\n'
    '    return out .. "…"\r\n'
    'end\r\n'
)

NEW = (
    '-- |T...|t 贴图序列（币种图标等）的 token 化：整块按「1 个字宽 + 2px」计，\r\n'
    '-- 绝不能逐字节量宽/截断（markup 有 40+ 字节，会让列宽爆炸、把右半内容挤出面板）。\r\n'
    'local function HTokenize(text)\r\n'
    '    local toks, pos = {}, 1\r\n'
    '    while true do\r\n'
    '        local s, e = string.find(text, "|T.-|t", pos)\r\n'
    '        if not s then\r\n'
    '            if pos <= #text then toks[#toks + 1] = { t = string.sub(text, pos) } end\r\n'
    '            break\r\n'
    '        end\r\n'
    '        if s > pos then toks[#toks + 1] = { t = string.sub(text, pos, s - 1) } end\r\n'
    '        toks[#toks + 1] = { t = string.sub(text, s, e), icon = true }\r\n'
    '        pos = e + 1\r\n'
    '    end\r\n'
    '    return toks\r\n'
    'end\r\n'
    '\r\n'
    'function ns.hui.TextW(text, fs)\r\n'
    '    if type(text) ~= "string" then return 0 end\r\n'
    '    local w = 0\r\n'
    '    for _, tk in ipairs(HTokenize(text)) do\r\n'
    '        if tk.icon then\r\n'
    '            w = w + fs + 2\r\n'
    '        else\r\n'
    '            local i, n = 1, #tk.t\r\n'
    '            while i <= n do\r\n'
    '                local _, step, k = HCharStep(tk.t, i)\r\n'
    '                w = w + k * fs\r\n'
    '                i = i + step\r\n'
    '            end\r\n'
    '        end\r\n'
    '    end\r\n'
    '    return w\r\n'
    'end\r\n'
    '\r\n'
    'function ns.hui.Fit(text, fs, width)\r\n'
    '    if type(text) ~= "string" then return "" end\r\n'
    '    if ns.hui.TextW(text, fs) <= width then return text end\r\n'
    '    local out, w = "", 0\r\n'
    '    for _, tk in ipairs(HTokenize(text)) do\r\n'
    '        if tk.icon then\r\n'
    '            local cw = fs + 2\r\n'
    '            if w + cw > width - fs then break end\r\n'
    '            out = out .. tk.t\r\n'
    '            w = w + cw\r\n'
    '        else\r\n'
    '            local i, n = 1, #tk.t\r\n'
    '            local stop = false\r\n'
    '            while i <= n do\r\n'
    '                local ch, step, k = HCharStep(tk.t, i)\r\n'
    '                local cw = k * fs\r\n'
    '                if w + cw > width - fs then stop = true break end\r\n'
    '                out = out .. ch\r\n'
    '                w = w + cw\r\n'
    '                i = i + step\r\n'
    '            end\r\n'
    '            if stop then break end\r\n'
    '        end\r\n'
    '    end\r\n'
    '    return out .. "…"\r\n'
    'end\r\n'
)


def check():
    data = open(P, 'rb').read().decode('utf-8')
    c = data.count(OLD)
    print('anchor count =', c)
    return c == 1


def apply():
    if not check():
        sys.exit('anchor check failed, abort')
    data = open(P, 'rb').read().decode('utf-8')
    data = data.replace(OLD, NEW, 1)
    open(P, 'wb').write(data.encode('utf-8'))
    d = open(P, 'rb').read()
    print('applied; CRLF:', d.count(b'\r\n'), 'bare LF:', d.count(b'\n') - d.count(b'\r\n'))


if __name__ == '__main__':
    if '--check' in sys.argv:
        check()
    else:
        apply()

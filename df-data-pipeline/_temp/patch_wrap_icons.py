# -*- coding: utf-8 -*-
# 2026-10-10 四轮：PD.Wrap 折行器把 |T...|t 币种图标序列剁碎 → 图标 token 原子化
P = 'Core/ProfessionUI.lua'

OLD = '''PD.Wrap = function(text, fs, width)\r
    local out = {}\r
    if type(text) ~= "string" or text == "" or not width then return out end\r
    local i, n = 1, #text\r
    local line, w = "", 0\r
    while i <= n do\r
        local ch, step, k = CharStep(text, i)\r
        local cw = k * fs\r
        if w + cw > width and line ~= "" then\r
            out[#out + 1] = line\r
            line, w = "", 0\r
        end\r
        line = line .. ch\r
        w = w + cw\r
        i = i + step\r
    end\r
    if line ~= "" then out[#out + 1] = line end\r
    return out\r
end\r
'''

NEW = '''PD.Wrap = function(text, fs, width)\r
    local out = {}\r
    if type(text) ~= "string" or text == "" or not width then return out end\r
    -- |T...|t 贴图序列按整块处理（2026-10-10 币种图标）：不许从中间折行剁开，\r
    -- 宽度按「一个字号 + 2px 余量」估算；其余文本仍按 CharStep 逐字符走。\r
    local toks, pos = {}, 1\r
    while true do\r
        local s, e = string.find(text, "|T.-|t", pos)\r
        if not s then\r
            toks[#toks + 1] = { t = string.sub(text, pos) }\r
            break\r
        end\r
        if s > pos then toks[#toks + 1] = { t = string.sub(text, pos, s - 1) } end\r
        toks[#toks + 1] = { t = string.sub(text, s, e), icon = true }\r
        pos = e + 1\r
    end\r
    local line, w = "", 0\r
    for _, tk in ipairs(toks) do\r
        if tk.icon then\r
            local cw = fs + 2\r
            if w + cw > width and line ~= "" then\r
                out[#out + 1] = line\r
                line, w = "", 0\r
            end\r
            line, w = line .. tk.t, w + cw\r
        else\r
            local i, n = 1, #tk.t\r
            while i <= n do\r
                local ch, step, k = CharStep(tk.t, i)\r
                local cw = k * fs\r
                if w + cw > width and line ~= "" then\r
                    out[#out + 1] = line\r
                    line, w = "", 0\r
                end\r
                line = line .. ch\r
                w = w + cw\r
                i = i + step\r
            end\r
        end\r
    end\r
    if line ~= "" then out[#out + 1] = line end\r
    return out\r
end\r
'''

import sys


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

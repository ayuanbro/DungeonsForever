# -*- coding: utf-8 -*-
"""解析 fc 站副本页 RSC 载荷 → floors/pins 完整版（支持嵌套）"""
import re, json, sys

# RSC 载荷里 JSON 是转义形态；把 \\" 还原成 " 后用平衡扫描抽 floors 数组
def unescape(seg):
    return seg.replace('\\\\', '\x00').replace('\\"', '"').replace('\x00', '\\')

def extract_floors(h):
    """找 'floors':[' 开头，做括号平衡扫描取完整数组"""
    out = []
    for m in re.finditer(r'\\"floors\\":\[', h):
        i = m.end()  # 指向 [ 后
        depth = 1
        j = i
        instr = False
        esc = False
        while j < len(h) and depth > 0:
            c = h[j]
            if esc:
                esc = False
            elif c == '\\\\':
                esc = True
            elif c == '"':
                instr = not instr
            elif not instr:
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
            j += 1
        out.append(h[i:j - 1])
    return out

def parse_pins(floor_json):
    """floor_json: 已反转义的楼层 JSON 文本（pins 数组段）"""
    pins = []
    for m in re.finditer(r'\{"x":([\d.]+),"y":([\d.]+),"boss":"([^"]*)","face":(\d+),"faceKind":"([^"]*)","label":(?:"([^"]*)"|\$undefined)', floor_json):
        x, y, b, face, kind, label = m.groups()
        pins.append(dict(x=float(x), y=float(y), boss=b, face=int(face), kind=kind, label=label or ''))
    name_m = re.search(r'"src":"([^"]*)"', floor_json)
    nm = re.findall(r'"name":"([^"]*)"', floor_json)
    return (name_m.group(1) if name_m else '?'), [n for n in nm if n and not n.startswith('/')], pins

if __name__ == '__main__':
    for slug in sys.argv[1:]:
        h = open('_fc_dg_%s.html' % slug, encoding='utf-8').read()
        print('##', slug)
        floors = extract_floors(h)
        if not floors:
            print('  (no floors block)')
        for f in floors:
            fj = unescape(f)
            src, names, pins = parse_pins(fj)
            print('  floor %s names=%s' % (src, names))
            for p in pins:
                print('    pin %.1f,%.1f %s face=%s kind=%s' % (p['x'], p['y'], p['label'] or p['boss'], p['face'], p['kind']))

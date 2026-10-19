# -*- coding: utf-8 -*-
"""QA(严过关) 独立扫描 v2：中英夹杂（大小写无关白名单）。"""
import io, os, re

DF = r'D:\workspace\DungeonsForever'

# 通用缩写 / 品牌 —— 大小写无关
ALLOW_RAW = '''pvp pve aoe dps dot hot boss beta tbc wotlk gcd ttk meta
wow rpg xp hp mp ap ui id tier bis
raidbots discord wowhead youtube twitch simc wcl
solo mob mobs add addon buff debuff proc dps
pre dungeon raid tank healer dps raidbots
ph www com cn net org
alpha rift rift
'''
ALLOW = set(w.strip().lower() for w in ALLOW_RAW.split() if w.strip())
# 罗马数字 & 单字母
ROMAN = re.compile(r'^[IVXLCivxlc]+$')

CJK = re.compile(r'[\u4e00-\u9fff]')
LATIN = re.compile(r"(?<![A-Za-z])([A-Za-z][A-Za-z0-9'\-]{1,})(?![A-Za-z])")

def extract_strings(t):
    out=[]; i=0; n=len(t)
    while i<n:
        c=t[i]
        if c=='"':
            j=i+1; buf=[]
            while j<n:
                ch=t[j]
                if ch=='\\': buf.append(t[j:j+2]); j+=2; continue
                if ch=='"': break
                buf.append(ch); j+=1
            out.append(''.join(buf)); i=j+1
        else: i+=1
    return out

def bad_tokens(s2):
    bad=set()
    for tk in LATIN.findall(s2):
        low=tk.lower()
        if low in ALLOW: continue
        if tk.isdigit(): continue
        if ROMAN.match(tk): continue
        # 单字母缩写（S/A 等）
        if len(tk)==1: continue
        bad.add(tk)
    return bad

def scan(path,label):
    t=io.open(path,encoding='utf-8',errors='replace').read()
    hits=[]
    for s in extract_strings(t):
        s2=re.sub(r'\|s\d+\|',' ',s)
        if not CJK.search(s2): continue
        b=bad_tokens(s2)
        if b: hits.append((s,sorted(b)))
    print('='*78); print('[%s] %s' % (label, os.path.relpath(path,DF)))
    print('  命中元素=%d' % len(hits))
    for s,b in hits[:60]:
        print('    - %s | %s' % (','.join(b), s[:190]))
    return len(hits)

tot=0
for f in [os.path.join(DF,'Core','Data','Data_ClassGuide.lua'),
          os.path.join(DF,'Core','Data','zhTW','Data_ClassGuide.lua')]:
    tot+=scan(f,'zh 产物')
print('>>> 合计命中 = %d' % tot)

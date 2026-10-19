# -*- coding: utf-8 -*-
import sys, io, json, re
sys.path.insert(0, '_temp')
import fc_guide as F

data = json.load(io.open('_temp/_cg_parsed.json', encoding='utf-8'))
verpat = re.compile(r'Forever|永恒|永久|永恆')

en_fallback_hits = 0
for key in F.KEYS:
    rec = data.get(key)
    if not rec:
        continue
    cn = F.load_trans(key)
    for sec in rec['sections']:
        en_flow = F.normalize_flow(sec['flow'], sec['key'])
        cn_flow = None
        if cn:
            cs = F.find_cn_sec(cn, sec['key'])
            if cs:
                cf = cs.get('flow', [])
                if sec['key'] == 'sw':
                    cf = F.resync_sw_cn(en_flow, cf, key)
                cn_flow = cf
        for i, en in enumerate(en_flow):
            prov = 'EN'
            if cn_flow and i < len(cn_flow) and cn_flow[i].get('t') == en['t']:
                prov = 'CN'
            entext = json.dumps(en['v'], ensure_ascii=False)
            if prov == 'EN' and verpat.search(entext):
                en_fallback_hits += 1
                print('EN-FALLBACK ver-term: %s|%s|%d  %s' % (key, sec['key'], i, entext[:140]))
print('TOTAL EN-fallback elements carrying version terms:', en_fallback_hits)

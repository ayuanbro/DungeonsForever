# -*- coding: utf-8 -*-
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from curl_cffi import requests as cr
PROXY='http://127.0.0.1:7897'
H={'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
   'Accept-Language':'en-US,en;q=0.9','Upgrade-Insecure-Requests':'1'}
for imp in ['chrome110','chrome124','chrome131','safari17_0','firefox133']:
    try:
        s=cr.Session(impersonate=imp, proxies={'http':PROXY,'https':PROXY}, headers=H)
        r=s.get('https://www.wowhead.com/classic/guide/classes/rogue/dps-macros', timeout=45)
        print(imp, r.status_code, len(r.text))
        if r.status_code!=200:
            print('   body:', repr(r.text[:300]))
        else:
            open('_temp/_mprobe_rogue.html','w',encoding='utf-8').write(r.text)
            print('   SAVED')
            break
    except Exception as e:
        print(imp, 'ERR', str(e)[:100])
    time.sleep(2)

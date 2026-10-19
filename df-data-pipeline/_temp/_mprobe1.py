# -*- coding: utf-8 -*-
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from curl_cffi import requests as cr
PROXY='http://127.0.0.1:7897'
H={'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
   'Accept-Language':'zh-CN,zh;q=0.9,en;q=0.8','Upgrade-Insecure-Requests':'1',
   'Referer':'https://www.wowhead.com/classic/'}
s=cr.Session(impersonate='chrome110', proxies={'http':PROXY,'https':PROXY}, headers=H)
for u in ['https://www.wowhead.com/classic/guide/classes/rogue/dps-macros',
          'https://www.wowhead.com/forever/cn/guide/classes/rogue/dps-macros',
          'https://www.wowhead.com/forever/guide/classes/rogue/dps-macros']:
    try:
        r=s.get(u, timeout=45)
        print(r.status_code, len(r.text), u)
        if r.status_code==200 and len(r.text)>20000:
            open('_temp/_mprobe_rogue.html','w',encoding='utf-8').write(r.text)
            print('  saved')
    except Exception as e:
        print('ERR', u, str(e)[:80])
    time.sleep(1.5)

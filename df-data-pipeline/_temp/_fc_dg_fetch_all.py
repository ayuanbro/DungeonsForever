# -*- coding: utf-8 -*-
"""抓取 fc 站全部 35 本副本页（串行、慢速）"""
from curl_cffi import requests
import time, sys

PROXIES = {'http': 'http://127.0.0.1:7897', 'https': 'http://127.0.0.1:7897'}
H = {'Referer': 'https://foreverchanges.pro/zh-cn/dungeons'}

SLUGS = [
    'ragefire-chasm', 'wailing-caverns', 'the-deadmines', 'shadowfang-keep',
    'blackfathom-deeps', 'the-stockade', 'gnomeregan', 'razorfen-kraul',
    'razorfen-downs', 'scarlet-monastery-graveyard', 'scarlet-monastery-library',
    'scarlet-monastery-armory', 'scarlet-monastery-cathedral', 'zulfarrak',
    'maraudon', 'sunken-temple', 'uldaman', 'blackrock-depths',
    'lower-blackrock-spire', 'upper-blackrock-spire', 'scholomance',
    'stratholme-main-gate', 'stratholme-service-gate', 'dire-maul-east',
    'dire-maul-west', 'dire-maul-north', 'excavation-site', 'city-of-dalaran',
    'hall-of-thanes', 'ruins-of-lordaeron', 'blackmaw-hold', 'alcaz-prison',
    'kroldok-stronghold', 'shapers-terrace', 'the-drowned-city',
]

only = sys.argv[1:] if len(sys.argv) > 1 else None
ok = fail = 0
for slug in SLUGS:
    if only and slug not in only:
        continue
    dst = '_fc_dg_%s.html' % slug
    try:
        r = requests.get('https://foreverchanges.pro/zh-cn/dungeons/%s' % slug,
                         headers=H, proxies=PROXIES, impersonate='chrome110', timeout=40)
        if r.status_code == 200 and len(r.text) > 20000:
            open(dst, 'w', encoding='utf-8').write(r.text)
            ok += 1
            print('ok  %-28s %d' % (slug, len(r.text)))
        else:
            fail += 1
            print('FAIL %-28s HTTP %s len %d' % (slug, r.status_code, len(r.text)))
    except Exception as e:
        fail += 1
        print('ERR  %-28s %s' % (slug, str(e)[:80]))
    time.sleep(1.2)
print('done ok=%d fail=%d' % (ok, fail))

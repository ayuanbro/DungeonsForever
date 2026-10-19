# -*- coding: utf-8 -*-
for p in [r'D:\workspace\DungeonsForever\Core\ProfessionUI.lua',
          r'D:\Game\World of Warcraft\_classic_beta_\Interface\AddOns\DungeonsForever\Core\ProfessionUI.lua']:
    d = open(p, 'rb').read()
    print(len(d), 'crlf=', d.count(b'\r\n'), 'lf=', d.count(b'\n'), p)

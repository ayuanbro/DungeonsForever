import re
for f in ['_bis_warrior.html', '_bis_rogue.html']:
    h = open(f, encoding='utf-8').read()
    for m in re.finditer(r'<a href="(/zh-cn/item/\d+)">([^<]+)</a>', h):
        print(f, m.group(1), '|', m.group(2))
    # rares / library 文本
    for m in list(re.finditer(r'<a href="/zh-cn/rares">([^<]+)</a>', h))[:3]:
        print(f, 'rares |', m.group(1))
    for m in list(re.finditer(r'<a href="/zh-cn/library-books">([^<]+)</a>', h))[:3]:
        print(f, 'books |', m.group(1))
    # quest 链接文本
    for m in list(re.finditer(r'<a href="https://www\.wowhead\.com/forever/zh-cn/quest=(\d+)"[^>]*>([^<]+)</a>', h))[:3]:
        print(f, 'quest', m.group(1), '|', m.group(2))
    # professions 链接文本
    for m in list(re.finditer(r'<a href="/zh-cn/professions/([a-z-]+)(#[^"]*)?">([^<]+)</a>', h))[:6]:
        print(f, 'prof', m.group(1), '|', m.group(3))

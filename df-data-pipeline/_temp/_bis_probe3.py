import re
h = open('_bis_warrior.html', encoding='utf-8').read()
# dungeons 链接的显示文本
for m in re.finditer(r'<a href="(/zh-cn/dungeons/[a-z0-9-]+)">([^<]+)</a>', h):
    print(m.group(1), '|', m.group(2))
print('---- quest link text ----')
for m in list(re.finditer(r'<a href="(https://www\.wowhead\.com/forever/zh-cn/quest=\d+)"[^>]*>([^<]+)</a>', h))[:4]:
    print(m.group(1), '|', m.group(2))
print('---- item link text ----')
for m in list(re.finditer(r'<a data-tip="\d+" class="bis-name q\d" href="/zh-cn/item/\d+">[^<]*</a><[^>]*><p><a href="(/zh-cn/item/\d+)">([^<]+)</a>', h))[:4]:
    print(m.group(1), '|', m.group(2))
print('---- slot ids in order ----')
print(re.findall(r'<section class="bis-slot" id="slot-([a-z0-9]+)">', h))
print('---- doll cell hrefs in order ----')
print(re.findall(r'<a class="bis-cell" href="#slot-([a-z0-9]+)">', h))
print('---- cols ----')
print(re.findall(r'<div class="bis-col">', h))

import re
h = open('_bis_warrior.html', encoding='utf-8').read()
# 武器区
for pat in ['mainhand', 'offhand', 'bis-weap', '武器', '主手']:
    idx = [m.start() for m in re.finditer(pat, h)]
    print(pat, len(idx), idx[:5])
i = h.find('mainhand')
print(h[i-600:i+900].replace('\n',' ') if i>0 else 'none')
print()
# dungeons 链接原文
k = h.find('/zh-cn/dungeons/the-deadmines')
print('DUNG LINK:', h[k-300:k+500].replace('\n',' '))

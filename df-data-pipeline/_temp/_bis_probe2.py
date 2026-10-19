import re
h = open('_bis_warrior.html', encoding='utf-8').read()
# side 切换控件
for pat in ['bis-side', 'side-switch', 'data-side', '部落', 'Horde']:
    idx = [m.start() for m in re.finditer(re.escape(pat), h)]
    print(pat, len(idx))
i = h.find('data-side')
if i > 0:
    print(h[i-500:i+500].replace('\n',' '))
# 顶栏区域（按钮前面）
j = h.find('>角色<')
print('TOPBAR:', h[j-1200:j+200].replace('\n',' '))

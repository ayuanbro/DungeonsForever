# -*- coding: utf-8 -*-
import io, os
DF = r'D:\workspace\DungeonsForever'
files = [
 'Core/BisUI.lua','Core/Bridge.lua','Core/Core.lua','Core/DungeonUI.lua','Core/ExploreUI.lua',
 'Core/Hui.lua','Core/LootFilter.lua','Core/LootFilterUI.lua','Core/MainFrame.lua',
 'Core/ProfessionUI.lua','Core/RaidUI.lua','Core/TierUI.lua',
 'Core/Data/Data_BIS.lua','Core/Data/Data_ClassGuide.lua','Core/Data/Data_ClassTier.lua',
 'Core/Data/Data_DungeonEntry.lua','Core/Data/Data_DungeonGuide.lua','Core/Data/Data_DungeonLoot.lua',
 'Core/Data/Data_DungeonQuests.lua','Core/Data/Data_Dungeons.lua','Core/Data/Data_Explore.lua',
 'Core/Data/Data_LootFilter.lua','Core/Data/Data_NPCLoc.lua','Core/Data/Data_Professions.lua',
 'Core/Data/enUS/Data_LootFilter.lua','Locales/enUS.lua','Locales/zhCN.lua','Locales/zhTW.lua',
]
L=[]
for f in files:
    p=os.path.join(DF,f)
    head=[]
    with io.open(p,encoding='utf-8',errors='replace') as fh:
        for line in fh:
            s=line.rstrip('\n')
            if s.strip()=='' or s.strip().startswith('--'):
                head.append(s)
            else:
                break
    L.append('='*74)
    L.append(f)
    L.append('-'*74)
    L.extend(head[:12])
io.open(os.path.join(DF,'_temp','_qa2_heads.txt'),'w',encoding='utf-8',newline='\n').write('\n'.join(L)+'\n')
print('ok')

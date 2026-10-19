import json, io
d = json.load(io.open('_temp/_cq_zone_map.json', encoding='utf-8'))
ids = sorted(set(d.values()))
lines = ['local ids = {' + ','.join(str(i) for i in ids) + '}',
         'local out = {}',
         'for i = 1, #ids do',
         '  local ok, info = pcall(C_Map.GetMapInfo, ids[i])',
         '  if ok and type(info) == "table" then',
         '    out[#out+1] = ids[i] .. "|" .. tostring(info.name) .. "|parent=" .. tostring(info.parentMapID) .. "|t=" .. tostring(info.mapType)',
         '  else',
         '    out[#out+1] = ids[i] .. "|nil"',
         '  end',
         'end',
         'return table.concat(out, "\\n")']
io.open('_temp/_cq_zonechk.lua', 'w', encoding='utf-8', newline='\n').write('\n'.join(lines))
print(len(ids))

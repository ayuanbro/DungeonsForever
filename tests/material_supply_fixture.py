"""Explicit evidence fixtures for material purchasing tests, never root-price inference."""

MATERIAL_FIXTURE = r'''
ns.ProfMaterialSupply={}
ns.ProfMaterialSupplyMeta={schemaVersion=1,fingerprint='supply-a'}
function material(item,values,npcID)
  local row={eligible=true,stockState='unlimited',costKind='gold',access='unconditional',
    role='profession_supply',side='n',price=37,quantity=4,priceSource='client_base_bundle',
    sourceURL='https://www.wowhead.com/forever/npc=7',verifiedAt='2026-10-21T00:00:00Z',
    evidenceHash='fixture-positive-supply-evidence'}
  for key,value in pairs(values or {})do row[key]=value end
  ns.ProfMaterialSupply[item]=ns.ProfMaterialSupply[item] or {offers={}}
  ns.ProfMaterialSupply[item].offers[npcID or 7]=row
  return row
end
'''

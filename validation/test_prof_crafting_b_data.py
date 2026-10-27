"""Field-by-field source inventory for the remaining dev profession data.

Use --write-candidates to regenerate the review inventory. Normal test discovery
only reads it. This inventory does not treat a newer source build as approval to
replace conflicting dev facts or declare a profession playable.
"""
from __future__ import annotations
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys
import unittest

try:
    from validation.export_prof_learning_condition_gaps import runtime, git_source, plain, PINNED_REF, CATALOG, trim_conditions
except ModuleNotFoundError:
    from export_prof_learning_condition_gaps import runtime, git_source, plain, PINNED_REF, CATALOG, trim_conditions

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'validation'/'data'/'prof_crafting_b_candidates.json'
SCOPE=('blacksmithing','leatherworking','tailoring','cooking','mining','herbalism','skinning','fishing','poisons','comprehension','camping')
CORE_FIELDS=('item','count','outputMin','outputMax','mats','learn','yellow','green','grey','formula')
MODES={**{p:'automatic_crafting'for p in ('blacksmithing','leatherworking','tailoring','cooking')},
       'mining':'gather_navigation_and_fixed_smelt_reference','herbalism':'gather_navigation',
       'skinning':'gather_navigation','fishing':'gather_navigation','poisons':'fixed_route',
       'comprehension':'reference_without_leveling_route','camping':'reference_without_leveling_route'}


@lru_cache(maxsize=1)
def upstream():
    lua=runtime();lua.execute('ns={}')
    for path in ('AddOns/DungeonsForever/Framework/CatalogCodec.lua',CATALOG,
                 'AddOns/DungeonsForever_RecipeData/Domain/ProfCatalog.lua',
                 'AddOns/DungeonsForever_Maps/Data/Data_MapCatalog.lua',
                 'AddOns/DungeonsForever_Maps/Domain/Catalog.lua'):
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)",git_source(path))
    lua.execute("ns.SharedCatalogs={Get=function(_,name)if name=='MapCatalog'then return ns.MapCatalog end end}")
    return lua


@lru_cache(maxsize=1)
def dev_records():
    lua=runtime();lua.execute("ns={};function GetLocale()return 'zhCN'end")
    for name in ('Data_Professions','Data_ProfRecipes','Data_ProfLeveling','Data_ProfGathering','Data_ProfMining'):
        path=ROOT/'Core'/'Data'/(name+'.lua')
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)",path.read_text(encoding='utf-8-sig'))
    records=plain(lua.execute(r"""
      local records={}
      local function add(out,raw,kind,profession)
        local spell=kind=='enchants'and raw[14]or(raw.spell or raw[1])
        if type(spell)~='number'or spell<=0 or out[spell]then return end
        local r={profession=profession,spell=spell,sourceKind=kind}
        if kind=='rinfo'then
          r.item,r.count,r.mats=raw.item or raw.makes,raw.count,raw.mats
          r.learn,r.yellow,r.green,r.grey=raw.learn,raw.yellow,raw.green,raw.grey
          r.formula=raw.formula or raw.formulaID
        elseif kind=='enchants'then
          r.item,r.count,r.mats=raw[15],1,raw[9]
          r.learn,r.yellow,r.green,r.grey=raw[5],raw[6],raw[7],raw[8]
          r.formula=raw[10]and raw[10].formulaID
        elseif kind=='crafted'then
          r.item,r.count,r.mats=raw[2],raw[3],raw[8]
          r.learn,r.yellow,r.green,r.grey=raw[4],raw[5],raw[6],raw[7]
          r.formula=tonumber(raw[9])
        else
          r.item,r.count,r.mats=raw[2],raw[3],raw[12]
          r.learn,r.yellow,r.green,r.grey=raw[7],raw[8],raw[9],raw[10]
          r.formula=type(raw[13])=='table'and raw[13][1]or nil
        end
        if not r.item and r.count==nil then r.count=0 end
        if r.count==nil then r.count=1 end
        r.yellow=r.yellow or r.learn
        if r.green==nil then
          r.green=r.yellow and r.grey and(r.yellow+r.grey)/2 or r.yellow
          r.greenDerived=r.green~=nil or nil
        end
        r.outputMin,r.outputMax=r.count,r.count
        local mats={}
        for _,m in ipairs(r.mats or{})do mats[#mats+1]={itemID=m[1],quantity=m[2]}end
        if r.mats~=nil then r.mats=mats end
        out[spell]=r
      end
      for _,profession in ipairs(ns.ProfData.order or{})do
        local out={};records[profession]=out
        local group=ns.ProfRecipes[profession]
        for _,row in ipairs(group and group.rows or{})do add(out,row,'rows',profession)end
        local guide=ns.ProfLeveling[profession]
        for spell,row in pairs(guide and guide.rinfo or{})do
          local clone={};for k,v in pairs(row)do clone[k]=v end;clone.spell=spell
          add(out,clone,'rinfo',profession)
        end
        for _,kind in ipairs({'crafted','enchants'})do
          for _,row in ipairs(group and group[kind]or{})do add(out,row,kind,profession)end
        end
      end
      return records
    """))
    return lua,records


def normalized_materials(value):
    if value is None:
        return None
    if isinstance(value,dict) and not value:
        return []
    total={}
    for row in value:
        item=row.get('itemID');quantity=row.get('quantity')
        if not isinstance(item,(int,float)) or not isinstance(quantity,(int,float)):
            return value
        total[int(item)]=total.get(int(item),0)+quantity
    return [{'itemID':item,'quantity':quantity}for item,quantity in sorted(total.items())]


def fields(record):
    result={key:record.get(key)for key in CORE_FIELDS}
    result['mats']=normalized_materials(result['mats'])
    return result


def qualification(spell):
    lua=upstream()
    routes=plain(lua.execute('return ns.ProfCatalog.GetLearningRoutes(...)',spell))
    requirement=plain(lua.execute("return ns.ProfCatalog.GetExtension('recipe_requirements',...)",spell))
    keep={'kind','status','conditionsKnown','verified','teachingItemID','trainerTaught','trainerObserved'}
    unique={}
    for original in routes if isinstance(routes,list)else[]:
        row={key:value for key,value in original.items()if key in keep}
        row['conditions']=trim_conditions(original.get('conditions'))
        token=json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(',',':'))
        unique.setdefault(token,row)
    result={}
    if unique:result['routes']=list(unique.values())
    if requirement:
        conditions=trim_conditions(requirement.get('conditions'))
        if conditions:result['requirements']={'conditions':conditions}
    return result


def missing_production_fields(record):
    unknown=[]
    for key in ('learn','yellow','green','grey'):
        if not isinstance(record.get(key),(int,float)):
            unknown.append(key)
    mats=record.get('mats')
    if not isinstance(mats,list)or not mats:
        unknown.append('mats')
    elif any(not isinstance(row.get('itemID'),(int,float))or row['itemID']<=0
             or not isinstance(row.get('quantity'),(int,float))or row['quantity']<=0 for row in mats):
        unknown.append('mats')
    if record.get('item') is not None:
        if not isinstance(record.get('count'),(int,float))or record['count']<=0:
            unknown.append('count')
    elif record.get('kind')!='enchant':
        unknown.append('item/output')
    return unknown



def gathering_reference_entries():
    lua=upstream();devlua,_=dev_records();out=[]
    for profession in ('mining','herbalism','skinning'):
        world=plain(lua.execute("return ns.ProfCatalog.GetWorld('gathering',...)",profession))or{}
        legacy=plain(devlua.execute('return ns.ProfGathering[...]',profession))
        for node in world.get('nodes',[]):
            identity_type='object'if node.get('objectID')is not None else'npc'if node.get('npcID')is not None else'unknown'
            identity=node.get('objectID',node.get('npcID'))
            fields={key:value for key,value in node.items()if key in('objectID','npcID','itemIDs','requiredSkill','requiredSkillVerified','skillThresholds','locations','locationText','yields')}
            if fields.get('locations')=={}:fields['locations']=[]
            unknown=[{'field':'devIdentityLink','reason':'dev aggregates item/skill or creature-level bands; item overlap is not an object/NPC identity proof'}]
            if not fields.get('locations'):unknown.append({'field':'locations','reason':'source supplies no identified map coordinates or area list for this node'})
            if fields.get('requiredSkill')is None:unknown.append({'field':'requiredSkill','reason':'source does not supply a verified node skill threshold'})
            if not fields.get('skillThresholds'):unknown.append({'field':'skillThresholds','reason':'source does not supply a complete node color range'})
            rows=[]
            items=set(node.get('itemIDs')or[])
            for index,row in enumerate(legacy if isinstance(legacy,list)else[],1):
                legacy_items=row[1]if profession=='skinning'else row[0]
                if any(item in items for item in legacy_items):rows.append(index)
            out.append({'profession':profession,'identityType':identity_type,'identity':identity,
                'status':'separate_source_reference','action':'add_separate_reference_only_if_supported',
                'fields':fields,'acceptedFields':fields,'conflicts':{},'unknownFields':unknown,
                'evidence':{'sourceCommit':PINNED_REF,'sourcePath':CATALOG,'record':"ProfCatalog.GetWorld('gathering',profession).nodes",
                    'devPath':'Core/Data/Data_ProfGathering.lua','devItemOverlapRows':rows,
                    'linkPolicy':'candidate overlap only; do not replace a dev aggregate band or fabricate a skill cap',
                    'yieldSemantics':'observed sample frequencies; not guaranteed per-harvest production'}})
    world=plain(lua.execute("return ns.ProfCatalog.GetWorld('fishing','all')"))or{}
    for key,fish in sorted((world.get('fish')or{}).items(),key=lambda pair:int(pair[0])):
        fields={k:v for k,v in fish.items()if k in('itemID','areas','pool','pools','requiredSkill','requiredBase','requiredNoGetaway','inland','coastal')}
        unknown=[{'field':'devIdentityLink','reason':'dev generic area thresholds and source fish/area observations have different grains; retain both as references'}]
        out.append({'profession':'fishing','identityType':'fish_item','identity':int(key),
            'status':'separate_source_reference','action':'add_separate_reference_only_if_supported',
            'fields':fields,'acceptedFields':fields,'conflicts':{},'unknownFields':unknown,
            'evidence':{'sourceCommit':PINNED_REF,'sourcePath':CATALOG,'record':"ProfCatalog.GetWorld('fishing','all').fish[itemID]",
                'devPath':'Core/Data/Data_ProfGathering.lua','linkPolicy':'no free inventory or assumed harvest quantity',
                'yieldSemantics':'observed catch frequencies; not guaranteed catch probability or guaranteed future output'}})
    return out


def compile_candidates():
    lua=upstream();devlua,dev=dev_records()
    metadata=plain(lua.execute('return ns.ProfCatalog.GetMetadata()'))
    scope=[];entries=[];matching=[]
    for profession in SCOPE:
        source=plain(lua.execute("local out={};for row in ns.ProfCatalog.IterRecipes(...)do out[row.spell]=row end;return out",profession))
        baseline=dev.get(profession,{})
        static_state=plain(devlua.execute("""
          local p=...;local lv=ns.ProfLeveling[p]
          local gathering=ns.ProfGathering and ns.ProfGathering[p]
          local pro=ns.ProfData.pro[p]
          local placeholders={};local group=ns.ProfRecipes[p]
          for _,row in ipairs(group and group.rows or{})do
            if type(row[1])~='number'or row[1]<=0 then placeholders[#placeholders+1]=row[1]or'unknown'end
          end
          return {placeholderRecipeIDs=placeholders,hasFixedSteps=lv and type(lv.steps)=='table'and #lv.steps>0 or false,
            hasGatheringReference=gathering~=nil,hasProfessionDescription=pro~=nil}
        """,profession))
        scope_unknown=[]
        if static_state.get('placeholderRecipeIDs'):
            scope_unknown.append({'field':'recipeIdentity','reason':'dev contains placeholder/nonpositive spell IDs; they are not canonical crafting recipes'})
        if not source:scope_unknown.append({'field':'modularRecipeAssociation','reason':'no explicit recipe membership in this pinned source; description/camp entries are not a new leveling algorithm'})
        if MODES[profession]=='reference_without_leveling_route':
            scope_unknown.append({'field':'levelingRouteAndSkillCap','reason':'no supported upgrade route/cap is established here; retain current description and reference data'})
        if profession in('mining','herbalism','skinning','fishing'):
            scope_unknown.extend([{'field':'devNodeCrosswalk','reason':'node identities and dev aggregate bands are not interchangeable'},
                {'field':'guaranteedHarvest','reason':'observed drop/catch frequency does not establish future production quantity'}])
        if profession=='poisons':
            scope_unknown.append({'field':'sourceLearnAndGreenThresholds','reason':'most source poison recipes omit learn/green; keep accepted dev fixed-route thresholds and list missing source facts'})
        scope.append({'profession':profession,'runtimeMode':MODES[profession],**static_state,
                      'sourceAssociation':'explicit_profession_membership'if source else'no_modular_recipe_membership',
                      'unknownFields':scope_unknown,
                      'dataPolicy':'retain dev values on conflict; no fabricated recipes, gathering production, leveling algorithm or skill cap'})
        for spell in sorted(set(source)|set(baseline)):
            original=source.get(spell)
            previous=baseline.get(spell)
            incoming=fields(original)if original else{}
            accepted=fields(previous)if previous else{}
            conflict={};available=[];unknown=[]
            if original and previous:
                for key in CORE_FIELDS:
                    new,old=incoming.get(key),accepted.get(key)
                    if new is not None and old is not None and new!=old:
                        conflict[key]={'dev':old,'modularization':new,'resolution':'retain_dev_pending_live_confirmation',
                            'alternatives':[{'value':old,'source':'dev','status':'existing_reference'},
                                            {'value':new,'source':'modularization','commit':PINNED_REF,'build':metadata.get('build'),'status':'source_reference'}]}
                    elif old is None and new is not None:
                        available.append(key)
                    elif new is None:
                        unknown.append({'field':key,'side':'modularization','reason':'not supplied by the named record; do not infer zero'})
            elif original:
                available=[key for key in CORE_FIELDS if incoming.get(key)is not None]
            if original:
                source_unknown=missing_production_fields({**original,**incoming})
                unknown.extend({'field':key,'side':'modularization','reason':'required production fact is missing or invalid'}for key in source_unknown)
                outputs=original.get('outputs')or[]
                if isinstance(outputs,list)and len(outputs)>1:
                    unknown.append({'field':'outputs','side':'runtime','reason':'multiple physical outputs are not represented by the current single-item solver contract'})
                q=qualification(spell)
            else:
                source_unknown=[];q={}
            if not original:
                status='dev_only'
            elif not previous:
                status='missing_in_dev'if not source_unknown else'reference_only'
            elif conflict:
                status='conflict'
            elif available:
                status='fill_missing_fields'
            elif source_unknown:
                status='reference_only'
            else:
                status='matching'
            if MODES[profession]in('gather_navigation','reference_without_leveling_route'):
                action='reference_only'
            elif status in('matching','dev_only','reference_only'):
                action='retain_dev_or_reference_only'
            elif conflict:
                action='review_conflicts_before_field_projection'
            else:
                action='candidate_for_explicit_source_reference_projection'
            dev_evidence=None
            if previous:
                kind=previous['sourceKind']
                dev_evidence={'sourceKind':kind,'path':'Core/Data/Data_ProfLeveling.lua'if kind=='rinfo'else'Core/Data/Data_ProfRecipes.lua',
                              'fields':accepted,'precedence':'rows > rinfo > crafted/enchants'}
                if previous.get('greenDerived'):
                    dev_evidence['derivedFields']={'green':'current dev Normalize midpoint of yellow and grey'}
            # A catalogue profession/rank/quest spell is not a production recipe.
            # Positive item, quantity and reagent evidence distinguishes a craft;
            # missing learning thresholds may remain inactive until client read.
            item=incoming.get('item');count=incoming.get('count');mats=incoming.get('mats')
            output_evidence=isinstance(item,(int,float)) and item>0
            reagent_evidence=isinstance(mats,list) and bool(mats) and all(
                isinstance(m.get('itemID'),(int,float)) and m['itemID']>0
                and isinstance(m.get('quantity'),(int,float)) and m['quantity']>0 for m in mats)
            craft_evidence=bool(original and (output_evidence or reagent_evidence))
            candidate_fields={key:incoming[key] for key in (available if previous else CORE_FIELDS)
                if incoming.get(key)is not None and key not in conflict}
            accepted={}
            if craft_evidence:
                for key,value in candidate_fields.items():
                    if key=='mats':
                        if reagent_evidence:accepted[key]=value
                    elif key in('item','formula','count','outputMin','outputMax'):
                        if isinstance(value,(int,float))and value>0 and value==int(value):accepted[key]=value
                    elif isinstance(value,(int,float))and value>=0:
                        accepted[key]=value
            production_kind=('craft'if output_evidence and reagent_evidence else'craft_reference_incomplete')if craft_evidence else'profession_rank_or_nonproduction_ability'
            merged={**(previous or {}),**(dev_evidence['fields']if dev_evidence else{}),**accepted}
            requires_observation=bool(original and (missing_production_fields(merged) or not craft_evidence
                or any(u['field']=='outputs' and u['side']=='runtime'for u in unknown)))
            if previous and not accepted:requires_observation=False
            if original and not craft_evidence and not previous:status='reference_only'
            if status=='matching':
                matching.append({'profession':profession,'spell':int(spell),
                    'fieldsSHA256':hashlib.sha256(json.dumps(incoming,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()})
                continue
            entry={'profession':profession,'spell':int(spell),'fields':incoming,'acceptedFields':accepted,
                   'status':status,'action':action,'recipeType':production_kind,'requiresClientObservation':requires_observation,
                   'canGainSkillInSourceModel':bool(original and isinstance(incoming.get('learn'),(int,float))
                       and isinstance(incoming.get('grey'),(int,float))and incoming['grey']>incoming['learn']),
                   'availableFields':available,'conflicts':conflict,'unknownFields':unknown,
                   'evidence':{'dev':dev_evidence,'modularization':{'commit':PINNED_REF,'build':metadata.get('build'),
                       'path':CATALOG,'record':'ProfCatalog.GetRecipe(spell,profession)','kind':original.get('kind')if original else None,
                       'association':'explicit_profession_membership'if original else'absent_in_this_profession_membership',
                       'qualification':q,'liveClientVerified':False}}}
            entries.append(entry)
    rawpaths=('Core/Data/Data_Professions.lua','Core/Data/Data_ProfRecipes.lua','Core/Data/Data_ProfLeveling.lua',
              'Core/Data/Data_ProfGathering.lua','Core/Data/Data_ProfMining.lua')
    return {'schemaVersion':1,'purpose':'field-level review inventory; status is not proof of gameplay availability',
            'source':{'commit':PINNED_REF,'build':metadata.get('build'),'path':CATALOG,
                      'sha256':hashlib.sha256(git_source(CATALOG).encode('utf-8')).hexdigest(),
                      'learningFingerprint':metadata.get('learningFingerprint'),
                      'dependencyFiles':[{'path':path,'sha256':hashlib.sha256(git_source(path).encode('utf-8')).hexdigest()}
                          for path in('AddOns/DungeonsForever_Maps/Data/Data_MapCatalog.lua','AddOns/DungeonsForever_Maps/Domain/Catalog.lua')]},
            'baseline':{'commit':'942a0ca1ae6478dabad4b0885f7abf4011338cc2','build':devlua.execute('return ns.ProfData.build'),
                        'sourceFiles':[{ 'path':path,'sha256':hashlib.sha256((ROOT/path).read_bytes()).hexdigest()}for path in rawpaths],
                        'normalization':'current dev named contract with rows > rinfo > crafted/enchants; no live runtime overrides'},
            'policies':['Different source versions are explicit; a newer build does not resolve contradictory facts.',
                        'Missing acquisition conditions stay unknown; use the learning-condition evidence and real client observations.',
                        'Four gathering professions retain navigation/fixed-smelt policy; profession/rank spells are not zero-material production.',
                        'No skill cap or leveling route is invented for comprehension/camping.'],
            'professions':scope,'entries':entries,'matching':matching,'referenceEntries':gathering_reference_entries()}


@lru_cache(maxsize=1)
def inventory():
    return json.loads(OUTPUT.read_text(encoding='utf-8'))


class CraftingBDataInventoryTests(unittest.TestCase):
    def test_pinned_source_and_each_baseline_file_are_traceable(self):
        data=inventory()
        self.assertEqual(data['source']['commit'],PINNED_REF)
        self.assertEqual(data['source']['sha256'],hashlib.sha256(git_source(CATALOG).encode('utf-8')).hexdigest())
        self.assertEqual(data['source']['build'],'1.60.1.70532')
        self.assertEqual(data['baseline']['build'],'1.60.1.70338')
        for record in data['baseline']['sourceFiles']:
            self.assertEqual(record['sha256'],hashlib.sha256((ROOT/record['path']).read_bytes()).hexdigest())

    def test_every_explicit_dev_and_mod_recipe_identity_has_a_field_review(self):
        data=inventory();actual={(r['profession'],r['spell'])for r in data['entries']+data['matching']}
        self.assertEqual(len(actual),len(data['entries'])+len(data['matching']),'duplicate profession/spell reviews')
        self.assertTrue(all(spell>0 for profession,spell in actual),'placeholder spell IDs are not recipes')
        _,dev=dev_records();lua=upstream();expected=set()
        for profession in SCOPE:
            expected.update((profession,int(spell))for spell in dev.get(profession,{}))
            ids=plain(lua.execute('local ids={};for r in ns.ProfCatalog.IterRecipes(...)do ids[r.spell]=true end;return ids',profession))
            expected.update((profession,int(spell))for spell in ids)
        self.assertEqual(actual,expected)

    def test_starting_threshold_conflicts_are_explicit_and_do_not_request_overwrite(self):
        rows={(r['profession'],r['spell']):r for r in inventory()['entries']}
        for profession,spell,upstream_learn in (('blacksmithing',2660,15),('leatherworking',2152,30),('tailoring',2963,25)):
            with self.subTest(profession=profession):
                row=rows[(profession,spell)]
                self.assertEqual(row['status'],'conflict')
                self.assertEqual(row['conflicts']['learn']['dev'],1)
                self.assertEqual(row['conflicts']['learn']['modularization'],upstream_learn)
                self.assertEqual(row['conflicts']['learn']['resolution'],'retain_dev_pending_live_confirmation')
                self.assertNotEqual(row['action'],'candidate_for_explicit_source_reference_projection')

    def test_candidates_have_exact_named_material_and_output_evidence(self):
        for row in inventory()['entries']:
            if not row['fields']:
                continue
            source=plain(upstream().execute('return ns.ProfCatalog.GetRecipe(...)',row['spell'],row['profession']))
            self.assertIsNotNone(source)
            self.assertEqual(row['fields'],fields(source))
            self.assertFalse(row['evidence']['modularization']['liveClientVerified'])

    def test_unknown_and_noncraft_records_never_request_an_unconditional_import(self):
        for row in inventory()['entries']:
            required=[u for u in row['unknownFields']if u['reason']=='required production fact is missing or invalid']
            if required and row['evidence']['dev']is None:
                self.assertEqual(row['status'],'reference_only')
                self.assertTrue(row['requiresClientObservation'])
            for field,value in row['acceptedFields'].items():
                self.assertNotIn(field,row['conflicts'])
                self.assertIsNotNone(value)
                if field=='mats':
                    self.assertTrue(value,'unknown/empty reagent list must not become free production')
                    for mat in value:self.assertGreater(mat['itemID'],0);self.assertGreater(mat['quantity'],0)
                if field in('item','formula','count','outputMin','outputMax'):
                    self.assertGreater(value,0,'zero sentinel is not an accepted production fact')
            if row['recipeType']=='profession_rank_or_nonproduction_ability':
                self.assertFalse(row['acceptedFields'])
        for p in inventory()['professions']:
            if p['profession']in('herbalism','skinning','fishing','comprehension','camping'):
                for row in inventory()['entries']:
                    if row['profession']==p['profession']:self.assertEqual(row['action'],'reference_only')

    def test_new_recipe_qualification_is_not_silently_discarded(self):
        for row in inventory()['entries']:
            if row['status']!='missing_in_dev':continue
            self.assertEqual(row['evidence']['modularization']['qualification'],qualification(row['spell']))
            self.assertEqual(row['evidence']['modularization']['association'],'explicit_profession_membership')

    def test_gathering_reference_nodes_remain_separate_from_crafting_and_dev_aggregate_bands(self):
        for row in inventory()['referenceEntries']:
            self.assertNotIn('spell',row)
            self.assertEqual(row['status'],'separate_source_reference')
            self.assertEqual(row['action'],'add_separate_reference_only_if_supported')
            self.assertTrue(any(u['field']=='devIdentityLink'for u in row['unknownFields']))
            self.assertNotIn('crafts',row['fields'])
            if row['identityType']in('object','npc'):
                self.assertEqual(row['fields'][row['identityType']+'ID'],row['identity'])
            if row['profession']=='skinning'and not row['fields'].get('locations'):
                self.assertTrue(any(u['field']=='locations'for u in row['unknownFields']))

    def test_projection_inventory_is_deterministically_reproducible(self):
        self.assertEqual(inventory(),compile_candidates())


if __name__=='__main__':
    if '--write-candidates'in sys.argv:
        data=compile_candidates();OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Wrote',OUTPUT)
        for scope in SCOPE:
            rows=[r for r in data['entries']if r['profession']==scope]
            statuses={status:sum(r['status']==status for r in rows)for status in sorted({r['status']for r in rows})}
            statuses['matching']=sum(r['profession']==scope for r in data['matching'])
            print(scope,statuses)
    else:
        unittest.main()

"""Export field differences and uncertainty reports without writing addon Data.

Reviewed fields remain documentation only. The original dev tuples are read
without applying supplements. All output paths are restricted to docs/.
--check never writes files or contacts the network.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from export_prof_learning_condition_gaps import ROOT, runtime, plain

INPUTS=("prof_crafting_a_candidates.json","prof_crafting_b_candidates.json","prof_first_aid_candidates.json")
ALLOWED={"item","count","outputMin","outputMax","mats","learn","yellow","green","grey","formula","category","cooldown","cooldownVerificationRequired"}
REQUIRED=("mats","count","learn","yellow","green","grey")
PROF_NAMES={"alchemy":"炼金","blacksmithing":"锻造","enchanting":"附魔","engineering":"工程","leatherworking":"制皮",
    "tailoring":"裁缝","cooking":"烹饪","first-aid":"急救","poisons":"制毒","mining":"采矿","herbalism":"采药",
    "skinning":"剥皮","fishing":"钓鱼","comprehension":"理解","camping":"露营"}


def digest(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")


def baseline():
    lua=runtime()
    lua.execute("ns={};GetLocale=function()return 'zhCN'end")
    for name in ("Data_Professions","Data_ProfRecipes","Data_ProfLeveling","Data_ProfMining"):
        lua.execute("assert(loadstring(...))('DF',ns)",(ROOT/"Core/Data"/(name+".lua")).read_text(encoding="utf-8-sig"))
    return plain(lua.execute('''
      local out,unidentified={},{}
      for _,slug in ipairs(ns.ProfData.order)do
        local by={};out[slug]=by;local group=ns.ProfRecipes[slug]
        local function put(spell,r,kind,index,name)
          if type(spell)=='number'and spell>0 then
            if not by[spell]then by[spell]=r end
          else
            unidentified[#unidentified+1]={profession=slug,spell=spell,kind=kind,rowIndex=index,
              item=r.item,name=name,reason='missing or placeholder spell identity; no canonical recipe is fabricated'}
          end
        end
        for i,r in ipairs(group and group.rows or {})do
          put(r[1],{item=r[2],count=r[3],learn=r[7],yellow=r[8],green=r[9],grey=r[10],mats=r[12],formula=type(r[13])=='table'and r[13][1]or nil},'rows',i)
        end
        for spell,r in pairs(ns.ProfLeveling[slug]and ns.ProfLeveling[slug].rinfo or {})do
          put(spell,{item=r.makes,count=r.count,learn=r.learn,yellow=r.yellow,green=r.green,grey=r.grey,mats=r.mats,formula=r.formula or r.formulaID})
        end
        for i,r in ipairs(group and group.crafted or {})do
          put(r[1],{item=r[2],count=r[3],learn=r[4],yellow=r[5],green=r[6],grey=r[7],mats=r[8],formula=r[9]},'crafted',i)
        end
        for i,r in ipairs(group and group.enchants or {})do
          put(r[14],{item=r[15],count=1,learn=r[5],yellow=r[6],green=r[7],grey=r[8],mats=r[9]},'enchants',i,r[1])
        end
      end
      return {recipes=out,unidentified=unidentified}
    '''))


def normalize_fields(accepted):
    fields={k:v for k,v in accepted.items()if k in ALLOWED and v is not None}
    if "mats"in fields:
        normalized=[]
        for row in fields["mats"]:
            item=row.get("itemID",row.get("id",row.get("item")))if isinstance(row,dict)else row[0]
            quantity=row.get("quantity",row.get("count"))if isinstance(row,dict)else row[1]
            if not isinstance(item,int)or item<=0 or not isinstance(quantity,(int,float))or quantity<=0:
                raise ValueError(f"Unusable accepted material: {row!r}")
            normalized.append([item,quantity])
        fields["mats"]=sorted(normalized)
    if "category"in fields and str(fields["category"]).isdigit():fields.pop("category")
    return fields


def unknown_names(record):
    values=record.get("unknownFields",record.get("unresolvedFields",[]))
    if isinstance(values,dict):return sorted(values)
    return sorted({v if isinstance(v,str)else str(v.get("field"))for v in values})


def render():
    baseline_data=baseline();native=baseline_data['recipes'];groups={};uncertain=[];source_hashes={};counts=Counter();refs=[];profession_unknowns=[];differences=[]
    for filename in INPUTS:
        path=ROOT/"validation/data"/filename
        data=path.read_bytes();source_hashes[filename]=digest(data);manifest=json.loads(data)
        records=manifest.get("records",manifest.get("entries",[]))
        for original in records:
            slug=original.get("profession",manifest.get("profession"));spell=original.get("spell")
            if not slug or not isinstance(spell,int)or spell<=0:continue
            old=native.get(slug,{}).get(spell)
            accepted=normalize_fields(original.get("acceptedFields",{}))
            unknown=unknown_names(original);conflicts=original.get("conflicts",{})
            entry={"profession":slug,"spell":spell,"sourceFile":"validation/data/"+filename,
                "sourceStatus":original.get("status","reference"),"unknownFields":unknown,"conflicts":conflicts}
            # A rank, passive, or scroll without crafting facts is not a new
            # leveling recipe. Confirmed fragments still remain in the report.
            physical=bool(accepted.get("mats"))and ((isinstance(accepted.get("item"),int)and accepted["item"]>0
                and ("count"not in accepted or accepted["count"]>0))
                or slug=="enchanting"and accepted.get("count")==0)
            add=old is None and physical and original.get("status")!="non_crafting"
            differences.append(dict(entry,devFields=old,referenceFields=original.get("fields",original.get("modularization")),
                candidateFields=accepted,missingInDev=old is None,appliedToRuntime=False))
            if add and accepted.get("cooldown")is None:
                if "cooldown"not in unknown:unknown.append("cooldown")
                entry["runtimeUnknowns"]=[{"field":"cooldown","reason":"no explicit current-client cooldown result; base duration zero is insufficient",
                    "resolution":"positive cooldown or an explicit hasCooldown=false observation with cooldownVerified"}]
            if unknown or conflicts or original.get("status")in ("reference_only","dev_only"):
                entry["retainedDevFields"]=old or None
                entry["referenceFields"]=original.get("fields",original.get("modularization"))
                entry["unknownDetails"]=original.get("unknownFields",original.get("unresolvedFields",[]))
                uncertain.append(entry)
            if not accepted or old is None and not add:
                counts["referenceOnly"]=counts["referenceOnly"]+1;continue
            missing=[]
            if old is None:
                # This is only a report of missing reference facts, not a
                # runtime seed or a proposal to alter the generated tuple.
                for field in REQUIRED:
                    if field not in accepted and field not in missing:missing.append(field)
            out={"candidateFields":accepted,"missingRecipeInDev":add,"requiredUnknownFields":sorted(missing),
                 "sourceStatus":"reference_confirmed" if filename=="prof_first_aid_candidates.json" else "source_reference",
                 "evidenceID":slug+":"+str(spell)}
            if old is None:
                out["cooldownUnverified"]=accepted.get("cooldown")is None
                if original.get("requiresClientObservation")or original.get("action")=="reference_only":out["requiresClientObservation"]=True
            groups.setdefault(slug,{})[spell]=out
            counts["missingRecipeCandidates"if add else "existingRecordsWithCandidateFields"]+=1
            counts["reviewedFieldsWithEvidence"]+=len(accepted)
            if missing:counts["incompleteRecipeCandidates"]+=1
        refs.extend(manifest.get("referenceEntries",[]))
        for profession in manifest.get("professions",[]):
            if profession.get("unknownFields"):
                profession_unknowns.append(dict(profession,sourceFile="validation/data/"+filename))
    fingerprint=digest(encoded(groups))
    meta={"revision":1,"fingerprint":fingerprint,"sourceCommit":"ec184e0d83f9d027e518b95eb0b2545699c5aeea",
          "sourceBuild":"1.60.1.70532","devReferenceBuild":"1.60.1.70338","inputsSHA256":source_hashes,
          "appliedToRuntime":False,"policy":"documentation only; do not alter generated dev Data, runtime recipe tuples or static lazy loaders"}
    uncertain.sort(key=lambda r:(r["profession"],r["spell"]))
    report={"schemaVersion":1,"metadata":meta,"summary":dict(counts),"unconfirmed":uncertain,
            "professionUnknowns":profession_unknowns,"unidentifiedDevRows":baseline_data['unidentified'],"unmatchedWorldReferences":refs}
    md=["# 专业参考资料中的未确认项","", "本文件仅列示参考差异，不加载到插件，也不改写 dev Data。所有候选字段均尚未导入。", "",
        "来源参考版本为 `1.60.1.70532`，dev 原资料标记为 `1.60.1.70338`。参考来源有据不等于当前客户端已确认。", "",
        "字段说明：`learn` 学习技能门槛，`yellow/green/grey` 黄／绿／灰技能门槛，`mats` 材料，`item` 产物，`count` 每次产量，`formula` 教学图纸，`cooldown` 制作冷却。", "",
        "急救等 dev 原本缺少的配方仍是数据缺口；客户端观察也不会擅自追加静态配方。完整必要缺口见 [dev 数据缺口](profession-dev-data-gaps.md)。", "",
        "完整候选证据见 `validation/data/prof_*_candidates.json`；本表保留每个有未知或冲突的配方编号。", "",
        "| 专业 | 配方编号 | 未知字段 | 冲突字段 | 证据文件 |","| --- | --- | --- | --- | --- |"]
    for r in uncertain:
        cf=r["conflicts"]
        fields=list(cf)if isinstance(cf,dict)else [v.get("field","?")for v in cf]
        md.append("| "+PROF_NAMES.get(r["profession"],r["profession"])+" | "+str(r["spell"])+" | "+", ".join(r["unknownFields"])+" | "+", ".join(fields)+" | "+Path(r["sourceFile"]).name+" |")
    md.extend(["", "## 专业与采集资料的未确认项", "",
        "| 专业 | 未确认项 |", "| --- | --- |"])
    for profession in profession_unknowns:
        fields=", ".join(field["field"] for field in profession["unknownFields"])
        md.append("| "+PROF_NAMES.get(profession["profession"],profession["profession"])+" | "+fields+" |")
    md.extend(["", "理解中的 `spell=0` 仍为占位，不能当作真实配方；露营没有已确认的独立升级路线和技能上限。", "",
        "原 dev 中缺少有效技能编号的记录也未据名称猜测：", "",
        "| 专业 | 原表位置 | 物品／名称 |", "| --- | --- | --- |"])
    for row in baseline_data['unidentified']:
        md.append("| "+PROF_NAMES.get(row['profession'],row['profession'])+" | "+row['kind']+"["+str(row['rowIndex'])+"] | "+str(row.get('item',row.get('name','?')))+" |")
    md.extend(["",
        "采集节点无法与旧聚合参考逐一对应的记录，另保留在 JSON 的 `unmatchedWorldReferences` 中；没有据此伪造采集产量或技能上限。", "",
        "[结构化清单](profession-data-unconfirmed.json)包含双方字段值、未知原因和来源定位。实际客户端已学、训练师或配方观察可用于后续确认。",""])
    reference_report={"metadata":meta,"summary":dict(counts),"referenceDifferences":differences,"candidateGroups":groups}
    return {ROOT/"docs/profession-data-reference-differences.json":json.dumps(reference_report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
            ROOT/"docs/profession-data-unconfirmed.json":json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
            ROOT/"docs/profession-data-unconfirmed.md":"\n".join(md)},counts


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--check",action="store_true");args=parser.parse_args()
    outputs,counts=render()
    for path,text in outputs.items():
        if path.resolve().parent!=(ROOT/"docs").resolve():raise ValueError('Report output must remain in docs/')
        if args.check:
            if not path.exists()or path.read_text(encoding="utf-8")!=text:raise SystemExit(f"Generated data differs: {path}")
        else:path.write_text(text,encoding="utf-8",newline="\n")
    print("Reference reports "+("reproduce exactly"if args.check else "written")+": "+json.dumps(dict(counts),sort_keys=True))


if __name__=="__main__":main()

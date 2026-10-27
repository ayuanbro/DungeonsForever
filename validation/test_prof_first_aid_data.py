"""Frozen first-aid candidates retain field provenance and unresolved facts."""
from pathlib import Path
import hashlib
import json
import subprocess
import unittest

from test_prof_solver_fusion import LuaRuntime, ROOT

DATA=ROOT/"validation"/"data"/"prof_first_aid_candidates.json"


def lua_named(value):
    if not hasattr(value,"items"):
        return value
    keys=list(value.keys())
    if not keys:
        return []
    if set(keys)==set(range(1,len(keys)+1)):
        return [lua_named(value[index])for index in range(1,len(keys)+1)]
    return {str(key):lua_named(item)for key,item in value.items()}


class FirstAidCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATA.read_text(encoding="utf-8"))
        cls.by_spell={row["spell"]:row for row in cls.data["records"]}

    def test_fixed_route_spells_are_all_present_with_confirmed_materials_and_outputs(self):
        self.assertEqual(len(self.by_spell),40)
        self.assertEqual(len(self.data["referenceSteps"]),16)
        expected={3275,3276,3277,3278,7928,7929,10840,10841,18629,18630,1244431,1244432,1244433,1259342}
        self.assertEqual(set(self.data["referenceSpells"]),expected)
        self.assertEqual({step[2]for step in self.data["referenceSteps"]},expected)
        for spell in expected:
            accepted=self.by_spell[spell]["acceptedFields"]
            self.assertTrue(accepted["mats"],spell)
            for field in ("item","count","outputMin","outputMax","yellow","green","grey"):
                self.assertIn(field,accepted,spell)
            self.assertEqual(self.by_spell[spell]["profession"],"first-aid")

    def test_forever_healing_potions_are_not_filled_from_generic_alchemy(self):
        expected={
            1244431:[(3371,1),(2678,1),(2447,1)],
            1244432:[(3371,1),(2678,2),(2450,1)],
            1244433:[(3372,1),(2692,1),(2453,1)],
        }
        for spell,materials in expected.items():
            actual=self.by_spell[spell]["acceptedFields"]["mats"]
            self.assertEqual([(m["itemID"],m["quantity"])for m in actual],materials)

    def test_forever_simple_poultice_yield_and_materials_are_explicit(self):
        accepted=self.by_spell[1259342]["acceptedFields"]
        self.assertEqual(accepted["item"],255716)
        self.assertEqual((accepted["count"],accepted["outputMin"],accepted["outputMax"]),(3,3,3))
        self.assertEqual([(m["itemID"],m["quantity"])for m in accepted["mats"]],[(3174,1),(2678,1),(2723,1)])

    def test_zero_orange_vs_learning_values_are_not_silently_resolved(self):
        unresolved={3275,7929,10840,10841,18629,18630}
        actual=set(self.data["summary"]["fixedUnknownLearn"])
        self.assertEqual(actual,unresolved)
        for spell in unresolved:
            row=self.by_spell[spell]
            self.assertNotIn("learn",row["acceptedFields"])
            alternatives=row["unknownFields"]["learn"]["alternatives"]
            self.assertGreater(len({a.get("value")for a in alternatives}),1)
            self.assertTrue(any(a["source"]=="snapshot:3034 colors[0]"for a in alternatives))
        self.assertEqual(self.by_spell[3275]["fields"]["learn"],30)
        self.assertEqual(self.by_spell[1244431]["acceptedFields"]["learn"],1)

    def test_acquisition_item_is_separate_from_unresolved_probability_start(self):
        for spell,item,skill in ((7929,16112,180),(10840,16113,210)):
            accepted=self.by_spell[spell]["acceptedFields"]
            self.assertEqual(accepted["formula"],item)
            route=next(r for r in accepted["learningRoutes"]if r["kind"]=="item")
            self.assertTrue(route["teachingValidated"])
            self.assertTrue(any(c["kind"]=="skill"and c["value"]==skill for c in route["conditions"]))
            self.assertNotIn("learn",accepted)

    def test_unknown_learning_conditions_and_cooldowns_are_explicit(self):
        for spell in self.data["referenceSpells"]:
            row=self.by_spell[spell]
            self.assertNotIn("cooldown",row["acceptedFields"])
            self.assertIn("cooldown",row["unknownFields"])
        self.assertEqual(set(self.data["summary"]["fixedUnknownLearningRoutes"]),{3275,10841,18629,18630})
        self.assertIn("learningRequirements",self.by_spell[1244431]["unknownFields"])

    def test_all_accepted_materials_and_outputs_have_matching_original_rows(self):
        for row in self.data["records"]:
            accepted=row["acceptedFields"]
            if "mats"in accepted:
                evidence=next(e for e in row["evidence"]if e["kind"]=="materials")
                self.assertEqual(evidence["source"],"snapshot:30")
                self.assertEqual(evidence["rows"][0]["materials"],accepted["mats"])
                self.assertEqual(int(evidence["rows"][0]["SpellID"]),row["spell"])
            if "item"in accepted:
                evidence=next(e for e in row["evidence"]if e["kind"]=="outputs")
                self.assertEqual(evidence["source"],"snapshot:20")
                self.assertEqual(int(evidence["rows"][0]["EffectItemType"]),accepted["item"])
                self.assertEqual(float(evidence["rows"][0]["EffectBasePointsF"]),accepted["count"])

    def test_raw_snapshot_hashes_are_revalidated_when_local_evidence_is_present(self):
        present=0
        for source in self.data["sources"].values():
            self.assertTrue(source["rawHashVerified"])
            path=ROOT/source["rawPath"]
            if not path.exists():
                continue
            present+=1
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),source["sha256"])
        if present==0:
            self.skipTest("local immutable raw capture cache is not installed")
        self.assertEqual(present,len(self.data["sources"]))

    def test_fixed_catalogue_is_decoded_and_every_record_matches(self):
        lua=LuaRuntime(unpack_returned_tuples=True)
        lua.execute('ns={};GetLocale=function()return "enUS"end;GetBuildInfo=function()return "1.60.1",70532 end')
        load=lua.eval("function(source)assert(loadstring(source))('DungeonsForever',ns)end")
        for source in self.data["catalogSources"]:
            raw=subprocess.check_output(["git","show",self.data["catalogRef"]+":"+source["path"]],cwd=ROOT)
            self.assertEqual(hashlib.sha256(raw).hexdigest(),source["sha256"])
            load(raw.decode("utf-8-sig"))
        lua.execute('rows={};for r in ns.ProfCatalog.IterRecipes("first-aid")do rows[#rows+1]=r end')
        decoded={r["spell"]:r for r in lua_named(lua.globals().rows)}
        self.assertEqual(set(decoded),set(self.by_spell))
        for spell,row in self.by_spell.items():
            for key,value in row["fields"].items():
                if key=="learningRoutes":
                    continue
                self.assertEqual(decoded[spell].get(key),value,(spell,key))
            self.assertTrue(row["supplementaryDatabaseFieldsMatchCatalog"])

    def test_build_and_runtime_limits_are_visible(self):
        self.assertEqual(self.data["evidenceBuild"],"1.60.1.70532")
        self.assertEqual(self.data["devReferenceBuild"],"1.60.1.70338")
        self.assertNotEqual(self.data["evidenceBuild"],self.data["devReferenceBuild"])
        self.assertTrue(any(r["status"]=="non_crafting"for r in self.data["records"]))
        self.assertTrue(all(r["status"]!="confirmed_current_game"for r in self.data["records"]))


if __name__=="__main__":
    unittest.main()

"""Coverage is a factual report and cannot grant purchasing eligibility."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'df-data-pipeline/_temp'))
from fc_material_coverage import reagent_coverage
from fc_pipeline_common import PipelineError, sha


class MaterialVendorCoverage(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / '.pipeline-runtime/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def catalog(self, slug, rows):
        path = self.folder / ('prof_' + slug + '.json')
        path.write_text(json.dumps({'rows': rows}), encoding='utf-8')
        return path

    def test_faction_specific_evidence_and_static225_scope(self):
        path = self.catalog('alchemy', [
            {'learn': 1, 'reagents': [[3371, 1], [2447, 2]]},
            {'learn': 224, 'reagents': [[3371, 2], [2320, 1]]},
            {'learn': 225, 'reagents': [[999, 1]]}])
        self.catalog('cooking', [{'learn': 1, 'reagents': [[2678, 1]]}])
        offers = {3371: {'offers': {7: {'side': 'a'}}}, 2678: {'offers': {9: {'side': 'n'}}}}
        report, inputs = reagent_coverage(self.folder, offers)
        low = report['fiveProfessionsBelow225']
        self.assertEqual(low['materialCount'], 3)
        self.assertEqual(low['qualifiedForAnyFaction'], 1)
        self.assertEqual(low['withoutConfirmedNpcSupply'], [2320, 2447])
        self.assertEqual(low['hordeWithoutConfirmedNpcSupply'], [2320, 2447, 3371])
        self.assertEqual(report['allProfessions']['materialCount'], 5)
        self.assertEqual(inputs[0]['sha256'], sha(path.read_bytes()))
        self.assertEqual(offers[3371]['offers'][7], {'side': 'a'})

    def test_empty_qualified_set_reports_ah_materials_without_inventing_sellers(self):
        self.catalog('engineering', [{'learn': 1, 'reagents': [[2840, 1], [2589, 1]]}])
        report, _ = reagent_coverage(self.folder, {})
        self.assertEqual(report['fiveProfessionsBelow225']['withoutConfirmedNpcSupply'], [2589, 2840])
        self.assertEqual(report['allProfessions']['qualifiedForAnyFaction'], 0)

    def test_malformed_reagent_or_absent_catalog_cannot_claim_coverage(self):
        with self.assertRaises(PipelineError):
            reagent_coverage(self.folder, {})
        self.catalog('tailoring', [{'learn': 1, 'reagents': [[True, 3]]}])
        with self.assertRaises(PipelineError):
            reagent_coverage(self.folder, {})

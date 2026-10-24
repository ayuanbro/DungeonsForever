"""Material base-price generation stays within the existing unified pipeline."""
import json
from pathlib import Path
import unittest
from unittest import mock
import test_prof_items_integration as integration

class MaterialPricePipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture=integration.UnifiedIntegrationTests('test_check_runs_every_step_and_does_not_publish')
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)

    def test_full_entry_has_only_original_five_csv_inputs_and_no_supplier_side_channel(self):
        options=integration.pipeline.parser().parse_args([])
        self.assertFalse(hasattr(options,'material_suppliers'))
        self.assertEqual(len(integration.pipeline.CSV_INPUTS),5)
        frozen={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in integration.pipeline.CSV_INPUTS.values()}
        self.assertEqual(self.fixture.invoke('--check'),0)
        self.assertEqual({p:(p.read_bytes(),p.stat().st_mtime_ns) for p in frozen},frozen)
        self.assertEqual(self.fixture.marker.read_bytes(),b'old marker')

    @unittest.skipUnless(integration.pipeline.os.name=='nt','Windows directory handle retry')
    def test_retained_preview_retries_transient_windows_directory_handle(self):
        preview=self.fixture.root/'.pipeline-runtime/material-price-preview'
        rename=Path.rename;sleep=integration.pipeline.time.sleep;attempts=[]
        def locked(path,target):
            if path.name.startswith('.preview-') and target==preview:
                attempts.append(path)
                if len(attempts)<3:raise PermissionError(5,'transient scanner handle')
            return rename(path,target)
        with mock.patch.object(Path,'rename',locked),mock.patch.object(integration.pipeline.time,'sleep',wraps=sleep) as delay:
            result=self.fixture.invoke('--check','--stage-dir',str(preview))
        self.assertEqual(result,0);self.assertGreaterEqual(len(attempts),3)
        self.assertLessEqual(len(attempts),5);self.assertEqual(delay.call_count,len(attempts)-1)
        manifest=json.loads((preview/'preview-manifest.json').read_bytes())
        self.assertEqual(manifest['status'],'validated-preview')
        self.assertFalse(any('material-suppliers' in key for key in manifest['inputs']))

if __name__=='__main__':unittest.main()

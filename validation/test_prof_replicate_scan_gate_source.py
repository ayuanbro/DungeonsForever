"""Static regression checks for replicate-mode settings and route gates."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ReplicateModeGateSourceTests(unittest.TestCase):
    def test_mode_revision_and_successful_scan_serial_are_bound(self):
        bridge=(ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig')
        for item in ('function AB.ObserveReplicateMode()',
                     'function AB.ReplicateScanReady()',
                     'function AB.HookReplicateModeSetting()',
                     'state.generation=state.generation+1',
                     'mode.scanSerial=mode.scanSerial+1',
                     'rg=scan.modeGeneration,rs=scan.scanSerial',
                     'batch.rg~=state.generation or batch.rs~=state.scanSerial'):
            self.assertIn(item,bridge)
    def test_all_live_entry_points_gate_recalculation(self):
        route=(ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig')
        self.assertEqual(route.count('local blocked=replicatePrerequisite(slug,opts)'),3)
        self.assertIn('job.searchTermination="replicate_scan_required"',route)
    def test_three_locales_define_messages(self):
        for locale in ('zhCN','zhTW','enUS'):
            text=(ROOT/'Locales'/f'{locale}.lua').read_text(encoding='utf-8-sig')
            for word in ('replicateModeUnknown',): pass
            self.assertIn('L["无法确认 Auctionator 扫描模式，请检查是否开启备用扫描模式。"]',text)
if __name__=='__main__': unittest.main()

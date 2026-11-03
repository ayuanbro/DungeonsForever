"""Static regression checks for replicate-mode settings and route gates."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ReplicateModeGateSourceTests(unittest.TestCase):
    def test_import_generation_and_persisted_snapshot_are_separate(self):
        bridge=(ROOT/'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig')
        for item in ('function AB.ObserveReplicateMode()',
                     'function AB.ReplicateScanReady()',
                     'function AB.HookReplicateModeSetting()',
                     'state.generation=state.generation+1',
                     'mode.scanSerial=mode.scanSerial+1',
                     'ScanDB().auctionFullScan=fullBatch',
                     'mode.generation~=scan.modeGeneration or mode.scanSerial~=scan.scanSerial'):
            self.assertIn(item,bridge)
    def test_scan_notice_gates_recalculation(self):
        route=(ROOT/'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig')
        self.assertIn('replicatePrerequisite',route)
        self.assertIn('replicate_scan_required',route)
    def test_three_locales_define_messages(self):
        for locale in ('zhCN','zhTW','enUS'):
            text=(ROOT/'Locales'/f'{locale}.lua').read_text(encoding='utf-8-sig')
            self.assertIn('L["请使用 Auctionator 完整扫描一次拍卖行，再重新计算路线。"]',text)
if __name__=='__main__': unittest.main()

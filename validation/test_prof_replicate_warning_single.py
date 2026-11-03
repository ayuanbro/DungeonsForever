"""Regression: a failed replicate-scan prerequisite appears once on the page."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class SingleReplicateWarning(unittest.TestCase):
    def test_body_warning_is_not_repeated_by_plan_status(self):
        code = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        body = code.split('function PD.RowsLeveling(rows)', 1)[1].split('function PD.', 1)[0]
        self.assertIn('local scanWarning=PD.ReplicateScanWarning()', body)
        self.assertIn('PushText(rows,scanWarning,12,{0.98,0.55,0.4},1)', body)
        self.assertIn('if statusText ~= scanWarning then', body)
        self.assertNotIn('PushText(rows, PD.PlanStatusText(res)', body)

    def test_cost_tile_does_not_add_same_warning_a_second_time(self):
        code = (ROOT / 'Core/ProfessionUI.lua').read_text(encoding='utf-8-sig')
        tile = code.split('function PD.PaintLvTiles()', 1)[1].split('function PD.', 1)[0]
        self.assertIn('scanBlocked', tile)
        self.assertNotIn('无法重新计算', tile)
        self.assertNotIn('costLines[#costLines+1]={scanWarning', tile)

    def test_inventory_verification_and_route_gate_both_remain(self):
        bridge = (ROOT / 'Core/AuctionatorBridge.lua').read_text(encoding='utf-8-sig')
        plans = (ROOT / 'Core/ProfRoutePlans.lua').read_text(encoding='utf-8-sig')
        self.assertIn('function AB.ReplicateScanReady()', bridge)
        self.assertIn('function AB.HookReplicateModeSetting()', bridge)
        self.assertIn('replicatePrerequisite', plans)

if __name__ == '__main__':
    unittest.main()

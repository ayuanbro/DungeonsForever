"""Client material base prices remain independent of formula NPC quotations."""
import csv
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'df-data-pipeline/_temp'))
import fc_prof_items as items
import fc_pipeline_common as common

class MaterialPriceLayers(unittest.TestCase):
    def price(self, item=100, **extra):
        row=dict.fromkeys(items.PRICE_FIELDS,'')
        row.update(ItemID=str(item),Name_enUS='Item',Name_zhCN='物品',Name_zhTW='物品',
                   BuyPriceCopper='12345',VendorStackCount='5',PriceStatus='priced',
                   Build='1.60.1.70450',HotfixBuild='70450')
        row.update(extra);return row

    def vendor(self, **extra):
        row=dict.fromkeys(items.VENDOR_FIELDS,'')
        row.update(item_id='100',npc_id='7',name_en='Formula seller',zone_id='12',side='a',stock='1')
        row.update(extra);return row

    def build(self,vendors,prices):
        fields,rows,stats=items.merge_rows(items.VENDOR_FIELDS,vendors,prices)
        content=items.csv_bytes(fields,rows)
        rebuilt=items.items_csv_rows(content)
        ns=common.load_namespace([('items.lua',items.build_items(rebuilt,{}).encode())])
        self.assertEqual(fields,items.CSV_FIELDS)
        return rows,ns['ProfItems'],stats

    def test_client_base_quote_survives_different_npc_discount(self):
        rows,data,_=self.build([self.vendor(cost_copper='9000',cost_text='90s')],[self.price()])
        self.assertEqual(len(rows),2)
        self.assertEqual(data[100]['cost_copper'],12345)
        self.assertEqual(data[100]['price_source'],'client')
        self.assertEqual(data[100]['VendorStackCount'],5)
        self.assertEqual(data[100]['offers'][7]['cost_copper'],9000)
        self.assertEqual(data[100]['offers'][7]['stock'],1)

    def test_barter_formula_offer_cannot_replace_client_material_quote(self):
        _,data,_=self.build([self.vendor(currency_kind='currency',currency_id='99',currency_amount='3')],[self.price()])
        self.assertEqual(data[100]['cost_copper'],12345)
        self.assertEqual(data[100]['offers'][7]['currency_id'],99)
        self.assertNotIn('cost_copper',data[100]['offers'][7])

    def test_material_without_any_npc_still_has_client_base_quote(self):
        rows,data,_=self.build([], [self.price()])
        self.assertEqual(len(rows),1)
        self.assertEqual(data[100]['cost_copper'],12345)
        self.assertEqual(data[100]['offers'],{})

    def test_zero_missing_or_invalid_status_never_becomes_free_root_quote(self):
        for extra in ({'BuyPriceCopper':'0','PriceStatus':'zero'},
                      {'BuyPriceCopper':'','PriceStatus':'missing_item_sparse'},
                      {'BuyPriceCopper':'12345','PriceStatus':'conflict'}):
            with self.subTest(extra=extra):
                _,data,_=self.build([], [self.price(**extra)])
                self.assertNotIn('cost_copper',data[100])
                self.assertNotIn('price_source',data[100])

    def test_fixed_nineteen_columns_reconstruct_both_price_layers_exactly(self):
        vendors=[self.vendor(cost_copper='7',cost_text='7c')]
        fields,rows,_=items.merge_rows(items.VENDOR_FIELDS,vendors,[self.price()])
        first=items.build_items(rows,{'generatedAt':'fixed'})
        second=items.build_items(items.items_csv_rows(items.csv_bytes(fields,rows)),{'generatedAt':'fixed'})
        self.assertEqual(first,second)
        self.assertEqual(len(fields),19)

    def test_original_vendor_rows_remain_distinct_from_one_root_row_per_item(self):
        _,data,stats=self.build([self.vendor(),self.vendor(npc_id='8')],[self.price(),self.price(101)])
        self.assertEqual(set(data[100]['offers']),{7,8})
        self.assertEqual(data[101]['offers'],{})
        self.assertEqual(stats['vendorRows'],2)
        self.assertEqual(stats['clientPriceRows'],2)

if __name__=='__main__':unittest.main()

"""Read-only CSV input locations owned by the standalone profession pipeline.

External producers are independent. Import their CSV files explicitly; the
pipeline never imports, watches, or invokes their implementation scripts.
"""
from fc_pipeline_common import HERE

INPUTS = HERE / '_fc/inputs'
CLIENT_INPUTS = INPUTS / 'client'
VENDOR_INPUTS = INPUTS / 'vendors'
CSV_INPUTS = {
    'prices_csv': CLIENT_INPUTS / 'item-buy-prices.csv',
    'item_csv': CLIENT_INPUTS / 'item.csv',
    'recipe_items_csv': CLIENT_INPUTS / 'recipe-item-specializations.csv',
    'vendors_csv': VENDOR_INPUTS / 'vendors-soldby-json-20261021.csv',
    'npcs_csv': VENDOR_INPUTS / 'npcs.csv',
}

"""
Delete Hidden Listings and Relist with Clean Data
Best approach for fixing policy violations
"""

import json
import requests
import logging
import sys
from pathlib import Path
from token_manager import get_token_manager
from ebay_auth import auth_manager
from config import settings

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Get active account
active_account = settings.active_account
account_name = f"Account {active_account}" + (" (Primary)" if active_account == 1 else " (Secondary)")
token_manager = get_token_manager(active_account)

if not token_manager.load_tokens():
    print(f"ERROR: No OAuth token found for {account_name}!")
    print(f"Please run: python authorize_account.py {active_account}")
    exit(1)

print("\n" + "="*70)
print("DELETE HIDDEN LISTINGS (Policy Violations)")
print(f"Active Account: {account_name}")
print("="*70)

# Load the products file
products_file = Path("processed/amazon-products-2026-01-05T05-55-06.json")

if not products_file.exists():
    print(f"\nERROR: File not found: {products_file}")
    exit(1)

with open(products_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

products = data.get('products', [])
total = len(products)

print(f"\nLoaded {total} products from {products_file.name}")
print("\nThis script will:")
print("1. Delete existing offers")
print("2. Delete inventory items")
print("3. You can then relist with complete_listing_flow_llm.py")

# Ensure authenticated
if not token_manager.is_authenticated():
    print("ERROR: Not authenticated")
    exit(1)

access_token = auth_manager.access_token

# eBay API endpoints
INVENTORY_BASE = "https://api.ebay.com/sell/inventory/v1"

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Content-Language": "en-US"
}

# Counters
deleted_offers = 0
deleted_inventory = 0
not_found = 0

print(f"\n{'='*70}")
print("STARTING DELETION")
print(f"{'='*70}\n")

for idx, amazon_product in enumerate(products, 1):
    asin = amazon_product.get('asin', 'Unknown')
    title = amazon_product.get('title', 'Unknown')[:50]

    print(f"\n[{idx}/{total}] Processing ASIN: {asin}")
    print(f"  Title: {title}...")

    sku = asin

    try:
        # Step 1: Get and delete offers
        print(f"  → Checking for offers...")

        offers_url = f"{INVENTORY_BASE}/offer"
        offers_params = {"sku": sku}

        offers_response = requests.get(
            offers_url,
            headers=headers,
            params=offers_params,
            timeout=30
        )

        if offers_response.status_code == 200:
            offers_data = offers_response.json()
            offers = offers_data.get('offers', [])

            if offers:
                for offer in offers:
                    offer_id = offer.get('offerId')
                    listing_id = offer.get('listingId')

                    print(f"  → Deleting offer {offer_id} (listing: {listing_id})...")

                    delete_offer_url = f"{INVENTORY_BASE}/offer/{offer_id}"
                    delete_response = requests.delete(
                        delete_offer_url,
                        headers=headers,
                        timeout=30
                    )

                    if delete_response.status_code == 204:
                        print(f"  ✓ Offer deleted successfully")
                        deleted_offers += 1
                    else:
                        print(f"  ✗ Failed to delete offer: {delete_response.status_code}")
                        print(f"    {delete_response.text[:200]}")
            else:
                print(f"  ⚠ No offers found")

        # Step 2: Delete inventory item
        print(f"  → Deleting inventory item (SKU: {sku})...")

        delete_inv_url = f"{INVENTORY_BASE}/inventory_item/{sku}"
        delete_inv_response = requests.delete(
            delete_inv_url,
            headers=headers,
            timeout=30
        )

        if delete_inv_response.status_code == 204:
            print(f"  ✓ Inventory item deleted successfully")
            deleted_inventory += 1
        elif delete_inv_response.status_code == 404:
            print(f"  ⚠ Inventory item not found")
            not_found += 1
        else:
            print(f"  ✗ Failed to delete inventory item: {delete_inv_response.status_code}")
            print(f"    {delete_inv_response.text[:200]}")

    except Exception as e:
        print(f"  ✗ Error: {str(e)}")

# Summary
print(f"\n{'='*70}")
print("DELETION COMPLETE")
print(f"{'='*70}")
print(f"\nResults:")
print(f"  ✓ Offers Deleted: {deleted_offers}")
print(f"  ✓ Inventory Items Deleted: {deleted_inventory}")
print(f"  ⚠ Not Found: {not_found}")
print(f"  Total: {total}")

print(f"\n{'='*70}")
print("NEXT STEPS:")
print(f"{'='*70}")
print("\nTo relist:")
print(f"\n  python complete_listing_flow_llm.py")
print()

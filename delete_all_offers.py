"""
Delete all unpublished offers
"""
import requests
import json
from token_manager import token_manager
from ebay_auth import auth_manager
from config import settings

# Load tokens
if not token_manager.load_tokens():
    print("ERROR: No OAuth token found!")
    exit(1)

headers = {
    "Authorization": f"Bearer {auth_manager.access_token}",
    "Content-Type": "application/json",
    "Content-Language": "en-US"
}

print("="*70)
print("Delete All Unpublished Offers")
print("="*70)

# Get all inventory items
inv_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/inventory_item"
response = requests.get(inv_url, headers=headers, params={'limit': 50})

if response.status_code != 200:
    print(f"Error getting inventory items: {response.text}")
    exit(1)

inventory_items = response.json().get('inventoryItems', [])
print(f"\nFound {len(inventory_items)} inventory items")

offers_to_delete = []

# Get all offers
for inv_item in inventory_items:
    sku = inv_item.get('sku')

    # Get offers for this SKU
    offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
    response = requests.get(offer_url, headers=headers, params={'sku': sku})

    if response.status_code == 200:
        offers = response.json().get('offers', [])

        for offer in offers:
            if offer.get('status') == 'UNPUBLISHED':
                offers_to_delete.append({
                    'offerId': offer.get('offerId'),
                    'sku': sku
                })

print(f"\nFound {len(offers_to_delete)} unpublished offers to delete\n")

if offers_to_delete:
    print("Offers to be deleted:")
    for item in offers_to_delete:
        print(f"  - Offer ID: {item['offerId']} (SKU: {item['sku']})")

    print("\nDeleting offers...")
    deleted = 0
    failed = 0

    for item in offers_to_delete:
        offer_id = item['offerId']
        sku = item['sku']

        print(f"\nDeleting offer {offer_id} (SKU: {sku})...")

        delete_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}"
        response = requests.delete(delete_url, headers=headers)

        if response.status_code == 204:
            print(f"  [OK] Deleted successfully")
            deleted += 1
        else:
            print(f"  [FAILED] Delete failed: {response.status_code}")
            try:
                print(f"     Error: {response.text}")
            except:
                pass
            failed += 1

    print("\n" + "="*70)
    print(f"Summary: {deleted} deleted, {failed} failed")
    print("="*70)
else:
    print("\nNo unpublished offers found.")

print("\n" + "="*70)

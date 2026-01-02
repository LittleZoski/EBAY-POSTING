"""
Complete diagnostic: Check inventory items, offers, and attempt individual publishing
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
    "Content-Type": "application/json"
}

print("="*70)
print("eBay Listing Diagnostic Tool")
print("="*70)
print(f"Environment: {settings.ebay_environment}")
print(f"API Base URL: {settings.ebay_api_base_url}")

# Step 1: Check inventory items
print("\n" + "="*70)
print("Step 1: Checking Inventory Items")
print("="*70)

inv_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/inventory_item"
response = requests.get(inv_url, headers=headers, params={'limit': 20})

print(f"Status Code: {response.status_code}")

inventory_items = []
if response.status_code == 200:
    data = response.json()
    inventory_items = data.get('inventoryItems', [])
    print(f"Found {len(inventory_items)} inventory items")

    for item in inventory_items[:5]:  # Show first 5
        sku = item.get('sku')
        title = item.get('product', {}).get('title', 'N/A')
        print(f"  - {sku}: {title[:50]}")
else:
    print(f"Error: {response.text}")
    exit(1)

# Step 2: For each inventory item, check if offer exists
print("\n" + "="*70)
print("Step 2: Checking Offers for Each Inventory Item")
print("="*70)

offers_to_publish = []

for item in inventory_items:
    sku = item.get('sku')

    # Get offers for this SKU
    offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
    response = requests.get(offer_url, headers=headers, params={'sku': sku})

    if response.status_code == 200:
        data = response.json()
        offers = data.get('offers', [])

        if offers:
            for offer in offers:
                offer_id = offer.get('offerId')
                status = offer.get('status')
                print(f"\n  SKU: {sku}")
                print(f"    Offer ID: {offer_id}")
                print(f"    Status: {status}")

                if status == 'UNPUBLISHED':
                    offers_to_publish.append({'sku': sku, 'offerId': offer_id})
        else:
            print(f"\n  SKU: {sku} - No offers found")
    else:
        print(f"\n  SKU: {sku} - Error checking offers: {response.status_code}")

# Step 3: Attempt to publish unpublished offers one by one
if offers_to_publish:
    print("\n" + "="*70)
    print(f"Step 3: Publishing {len(offers_to_publish)} Unpublished Offers")
    print("="*70)

    for offer_data in offers_to_publish:
        sku = offer_data['sku']
        offer_id = offer_data['offerId']

        print(f"\nAttempting to publish: {sku} (Offer ID: {offer_id})")

        publish_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}/publish"
        response = requests.post(publish_url, headers=headers)

        print(f"  Status Code: {response.status_code}")

        if response.status_code in [200, 201]:
            result = response.json()
            listing_id = result.get('listingId')
            print(f"  ✅ SUCCESS! Published listing")
            print(f"     Listing ID: {listing_id}")
            print(f"     View at: https://www.ebay.com/itm/{listing_id}")
        else:
            print(f"  ❌ FAILED")
            try:
                error_data = response.json()
                print(f"     Error: {json.dumps(error_data, indent=2)}")
            except:
                print(f"     Error: {response.text}")
else:
    print("\n✅ No unpublished offers found. All offers may already be published!")
    print("\nCheck your active listings at:")
    print("https://www.ebay.com/sh/lst/active")

print("\n" + "="*70)

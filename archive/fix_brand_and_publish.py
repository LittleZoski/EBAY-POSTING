"""
Fix Brand aspect for all inventory items and publish offers
"""
import requests
import json
import re
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

def extract_brand_from_title(title):
    """Extract brand name from product title"""
    # Common brand patterns
    brands = ["eos", "STANLEY", "OEAK", "Owala", "PULIDIKI"]

    title_lower = title.lower()
    for brand in brands:
        if brand.lower() in title_lower:
            return brand

    # Try to extract first word if it looks like a brand (all caps or capitalized)
    words = title.split()
    if words:
        first_word = words[0]
        if first_word.isupper() or (first_word[0].isupper() and len(first_word) > 2):
            return first_word

    return "Generic"

print("="*70)
print("Fix Brand Aspect and Publish Offers")
print("="*70)

# Get all inventory items
inv_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/inventory_item"
response = requests.get(inv_url, headers=headers, params={'limit': 50})

if response.status_code != 200:
    print(f"Error getting inventory items: {response.text}")
    exit(1)

inventory_items = response.json().get('inventoryItems', [])
print(f"\nFound {len(inventory_items)} inventory items\n")

updated_skus = []

for inv_item in inventory_items:
    sku = inv_item.get('sku')
    product = inv_item.get('product', {})
    title = product.get('title', '')
    aspects = product.get('aspects', {})
    current_brand = aspects.get('Brand', [''])[0]

    if current_brand == "Unbranded":
        # Extract real brand
        real_brand = extract_brand_from_title(title)
        print(f"{sku}:")
        print(f"  Title: {title[:60]}...")
        print(f"  Current Brand: {current_brand}")
        print(f"  New Brand: {real_brand}")

        # Update the aspect
        aspects['Brand'] = [real_brand]
        product['aspects'] = aspects

        # Update inventory item
        update_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/inventory_item/{sku}"

        # Prepare update payload
        update_data = {
            "product": product,
            "condition": inv_item.get('condition'),
            "conditionDescription": inv_item.get('conditionDescription'),
            "availability": inv_item.get('availability')
        }

        response = requests.put(update_url, headers=headers, json=update_data)

        if response.status_code in [200, 204]:
            print(f"  [OK] Updated successfully\n")
            updated_skus.append(sku)
        else:
            print(f"  [FAILED] Update failed: {response.status_code}")
            print(f"     Error: {response.text}\n")
    else:
        print(f"{sku}: Brand already set to '{current_brand}' (skipping)\n")

# Now try to publish all offers for updated SKUs
if updated_skus:
    print("="*70)
    print(f"Publishing Offers for {len(updated_skus)} Updated Items")
    print("="*70)

    for sku in updated_skus:
        # Get offers for this SKU
        offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
        response = requests.get(offer_url, headers=headers, params={'sku': sku})

        if response.status_code != 200:
            continue

        offers = response.json().get('offers', [])

        for offer in offers:
            if offer.get('status') == 'UNPUBLISHED':
                offer_id = offer.get('offerId')

                print(f"\nPublishing offer {offer_id} for {sku}...")

                publish_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}/publish"
                response = requests.post(publish_url, headers=headers)

                if response.status_code in [200, 201]:
                    result = response.json()
                    listing_id = result.get('listingId')
                    print(f"  [SUCCESS] Published listing!")
                    print(f"     Listing ID: {listing_id}")
                    print(f"     View at: https://www.ebay.com/itm/{listing_id}")
                else:
                    print(f"  [FAILED] {response.status_code}")
                    try:
                        error_data = response.json()
                        print(f"     Error: {json.dumps(error_data, indent=2)}")
                    except:
                        print(f"     Error: {response.text}")

print("\n" + "="*70)
print("Done!")
print("="*70)

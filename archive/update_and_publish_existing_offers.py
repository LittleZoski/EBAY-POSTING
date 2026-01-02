"""
Update existing offers with valid leaf category from cache and publish them
"""
import requests
import json
from token_manager import token_manager
from ebay_auth import auth_manager
from config import settings
from product_mapper import product_mapper
from category_cache import CategoryCache

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
print("Update Existing Offers with Valid Leaf Category")
print("="*70)

# Initialize category cache
cache = CategoryCache()
cache.initialize()

# Pick a safe test category - using simple, common categories at level 2
# These are broad, commonly-used categories less likely to have special requirements
test_categories = [
    "360",     # Art Prints > Art (Level 2) - minimal requirements
    "28009",   # Art Posters > Art (Level 2) - minimal requirements
    "182073",  # Vintage Cell Phones > Cell Phones & Accessories (Level 2) - requires Model
    "139973",  # Video Games > Video Games & Consoles > Video Games (Level 2) - requires Platform
    "261186",  # Books > Books & Magazines > Books (Level 2) - requires Book Title
]
selected_category = None

print("\nFinding valid leaf category for testing:")
for cat_id in test_categories:
    cat = cache.get_category(cat_id)
    if cat and cat['leaf']:
        selected_category = cat_id
        print(f"  [OK] Selected category {cat_id}: {cat['name']}")
        print(f"       Path: {cache.get_category_path(cat_id)}")
        print(f"       Leaf: {cat['leaf']}")
        break
    else:
        print(f"  [SKIP] Category {cat_id} not valid")

if not selected_category:
    print("ERROR: Could not find a valid test category!")
    exit(1)

print(f"\nWill update offers to use category: {selected_category}")
print("="*70)

# Get all inventory items
inv_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/inventory_item"
response = requests.get(inv_url, headers=headers, params={'limit': 50})

if response.status_code != 200:
    print(f"Error getting inventory items: {response.text}")
    exit(1)

inventory_items = response.json().get('inventoryItems', [])
print(f"\nFound {len(inventory_items)} inventory items")

# For each inventory item, get its offers and update them
updated_offers = []

for inv_item in inventory_items:
    sku = inv_item.get('sku')
    product = inv_item.get('product', {})

    # Get offers for this SKU
    offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
    response = requests.get(offer_url, headers=headers, params={'sku': sku})

    if response.status_code != 200:
        print(f"Error getting offers for {sku}: {response.text}")
        continue

    offers = response.json().get('offers', [])

    for offer in offers:
        if offer.get('status') == 'UNPUBLISHED':
            offer_id = offer.get('offerId')

            print(f"\n{sku}: Updating offer {offer_id}...")

            # Check current category
            current_cat = offer.get('categoryId', 'unknown')
            print(f"  Current category: {current_cat}")

            cat_info = cache.get_category(current_cat)
            if cat_info:
                print(f"  Category name: {cat_info['name']}")
                print(f"  Is leaf: {cat_info['leaf']}")

            # Build listingDescription from product data
            title = product.get('title', '')
            description = product.get('description', '')
            images = product.get('imageUrls', [])

            # Extract bullet points from description if available
            bullet_points = []
            if description:
                lines = description.split('\n')
                bullet_points = [line.strip('• ').strip() for line in lines if line.strip().startswith('•')]

            listing_description = product_mapper._build_html_description({
                "title": title,
                "description": description,
                "bulletPoints": bullet_points[:10],
                "images": images
            })

            # Update the offer
            update_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}"

            # Get current offer data
            current_offer = offer

            # Add listingDescription to the offer
            current_offer['listingDescription'] = listing_description

            # Update to valid leaf category
            current_offer['categoryId'] = selected_category
            print(f"  Changing category to: {selected_category}")

            # Remove read-only fields
            fields_to_remove = ['offerId', 'status', 'listing']
            for field in fields_to_remove:
                current_offer.pop(field, None)

            response = requests.put(update_url, headers=headers, json=current_offer)

            print(f"  Update response: {response.status_code}")

            if response.status_code in [200, 204]:
                print(f"  [OK] Updated successfully")

                # Verify the update by fetching the offer again
                verify_response = requests.get(update_url, headers=headers)
                if verify_response.status_code == 200:
                    updated_offer_data = verify_response.json()
                    print(f"  Verified category is now: {updated_offer_data.get('categoryId')}")

                updated_offers.append(offer_id)
            else:
                print(f"  [FAILED] Update failed: {response.status_code}")
                print(f"     Error: {response.text}")

# Now try to publish all updated offers
if updated_offers:
    print("\n" + "="*70)
    print(f"Publishing {len(updated_offers)} Updated Offers")
    print("="*70)

    for offer_id in updated_offers:
        print(f"\nPublishing offer {offer_id}...")

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

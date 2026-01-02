"""
Complete end-to-end flow: JSON -> Inventory Item -> Offer -> Published Listing
"""

import json
import requests
from pathlib import Path
from token_manager import token_manager
from ebay_auth import auth_manager
from product_mapper import product_mapper

# Load tokens
if not token_manager.load_tokens():
    print("ERROR: No OAuth token found!")
    exit(1)

# Load business policies
with open("business_policies_config.json", "r") as f:
    config = json.load(f)

payment_policy_id = config["payment_policy_id"]
return_policy_id = config["return_policy_id"]
fulfillment_policy_id = config["fulfillment_policy_id"]
category_id = config["default_category_id"]

print("\n" + "="*70)
print("Complete eBay Listing Flow (with Price Multiplier)")
print("="*70)

# Load Amazon products from Downloads folder
json_file = Path("C:/Users/31243/Downloads/test-amazon-product.json")

if not json_file.exists():
    print(f"\nERROR: {json_file} not found!")
    exit(1)

with open(json_file, "r") as f:
    amazon_products = json.load(f)

print(f"\nLoaded {len(amazon_products)} products from {json_file.name}")

headers = {
    "Authorization": f"Bearer {auth_manager.access_token}",
    "Content-Type": "application/json",
    "Content-Language": "en-US"
}

# STEP 1: Create/verify merchant location exists
print("\n" + "="*70)
print("[Step 1] Ensuring merchant location exists...")
print("="*70)

location_key = "us_warehouse"
location_url = f"https://api.ebay.com/sell/inventory/v1/location/{location_key}"

# Try to get existing location
response = requests.get(location_url, headers=headers)

if response.status_code == 404:
    # Create location
    print(f"\nCreating merchant location '{location_key}'...")
    location_data = {
        "location": {
            "address": {
                "addressLine1": "123 Business St",
                "city": "New York",
                "stateOrProvince": "NY",
                "postalCode": "10001",
                "country": "US"
            }
        },
        "locationTypes": ["WAREHOUSE"],
        "name": "US Warehouse",
        "merchantLocationStatus": "ENABLED"
    }

    response = requests.post(location_url, headers=headers, json=location_data)
    if response.status_code in [200, 201, 204]:
        print(f"  SUCCESS: Created location '{location_key}'")
    else:
        print(f"  ERROR: {response.text}")
        exit(1)
else:
    print(f"  Location '{location_key}' already exists")

# STEP 2: Create inventory items
print("\n" + "="*70)
print("[Step 2] Creating inventory items with US location...")
print("="*70)

skus_created = []

for product in amazon_products:
    asin = product["asin"]
    sku = f"AMZN-{asin}"
    multiplier = product.get("price_multiplier", 2.0)

    print(f"\nProcessing {sku}...")
    print(f"  Price multiplier: {multiplier}x")

    # Parse price
    amazon_price = product_mapper.parse_price(product["price"])
    ebay_price = product_mapper.calculate_ebay_price(amazon_price, multiplier=multiplier)

    print(f"  Amazon price: ${amazon_price:.2f}")
    print(f"  eBay price: ${ebay_price:.2f}")

    # Create inventory item with US location
    inventory_item = {
        "sku": sku,
        "locale": "en_US",
        "product": {
            "title": product["title"][:80],  # eBay 80 char limit
            "description": product["description"],
            "imageUrls": product["images"],
            "aspects": {
                "Brand": [product.get("specifications", {}).get("Brand", "Unbranded")],
                "MPN": [asin],
                "Condition": ["New"]
            }
        },
        "condition": "NEW",
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 10,
                "availabilityDistributions": [
                    {
                        "merchantLocationKey": location_key,
                        "quantity": 10
                    }
                ]
            }
        }
    }

    # Create or update inventory item
    inv_url = f"https://api.ebay.com/sell/inventory/v1/inventory_item/{sku}"
    response = requests.put(inv_url, headers=headers, json=inventory_item)

    if response.status_code in [200, 201, 204]:
        print(f"  SUCCESS: Inventory item created")
        skus_created.append((sku, ebay_price))
    else:
        print(f"  ERROR: {response.text}")

# STEP 3: Create offers
print("\n" + "="*70)
print("[Step 3] Creating offers with business policies...")
print("="*70)

offer_ids_created = []

for sku, price in skus_created:
    print(f"\nCreating offer for {sku}...")

    offer = {
        "sku": sku,
        "marketplaceId": "EBAY_US",
        "format": "FIXED_PRICE",
        "availableQuantity": 10,
        "categoryId": category_id,
        "listingPolicies": {
            "paymentPolicyId": payment_policy_id,
            "returnPolicyId": return_policy_id,
            "fulfillmentPolicyId": fulfillment_policy_id
        },
        "pricingSummary": {
            "price": {
                "value": str(price),
                "currency": "USD"
            }
        },
        "merchantLocationKey": location_key
    }

    offer_url = "https://api.ebay.com/sell/inventory/v1/offer"
    response = requests.post(offer_url, headers=headers, json=offer)

    if response.status_code in [200, 201]:
        offer_id = response.json().get("offerId")
        print(f"  SUCCESS: Offer created (ID: {offer_id})")
        offer_ids_created.append(offer_id)
    else:
        print(f"  ERROR: {response.text}")

# STEP 4: Publish offers
print("\n" + "="*70)
print("[Step 4] Publishing offers to create live listings...")
print("="*70)

listing_ids = []

for offer_id in offer_ids_created:
    print(f"\nPublishing offer {offer_id}...")

    publish_url = f"https://api.ebay.com/sell/inventory/v1/offer/{offer_id}/publish"
    response = requests.post(publish_url, headers=headers)

    if response.status_code in [200, 201]:
        listing_id = response.json().get("listingId")
        print(f"  SUCCESS: Published! Listing ID: {listing_id}")
        listing_ids.append(listing_id)
    else:
        print(f"  ERROR: {response.text}")

# SUMMARY
print("\n" + "="*70)
print("FINAL SUMMARY")
print("="*70)

print(f"\nProducts processed: {len(amazon_products)}")
print(f"Inventory items created: {len(skus_created)}")
print(f"Offers created: {len(offer_ids_created)}")
print(f"Listings published: {len(listing_ids)}")

if listing_ids:
    print("\n SUCCESS! Your listings are now LIVE on eBay!")
    print("\nView your active listings at:")
    print("https://www.ebay.com/sh/lst/active")

    print("\nPublished listings:")
    for listing_id in listing_ids:
        print(f"  - https://www.ebay.com/itm/{listing_id}")

print("\n" + "="*70)

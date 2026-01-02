"""
Complete end-to-end flow with LLM-powered category selection
Flow: JSON -> LLM Category Selection -> Inventory Item -> Offer (with requirements) -> Published Listing
"""

import json
import requests
import logging
import sys
from pathlib import Path
from token_manager import token_manager
from ebay_auth import auth_manager
from product_mapper import product_mapper
from llm_category_selector import LLMCategorySelector
from config import settings

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

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

print("\n" + "="*70)
print("Complete eBay Listing Flow with LLM Category Selection")
print("="*70)

# Initialize LLM category selector
print("\nInitializing LLM category selector...")
try:
    category_selector = LLMCategorySelector()
    print(f"  [OK] Category cache loaded: {len(category_selector.cache.categories)} categories")
except Exception as e:
    print(f"  [ERROR] Failed to initialize LLM selector: {str(e)}")
    print("  Make sure ANTHROPIC_API_KEY is set in .env file")
    exit(1)

# Load Amazon products from processed folder (most recent file)
processed_folder = Path(settings.processed_folder)
# Filter out _results files, only get original product files
json_files = [f for f in processed_folder.glob("amazon-products-*.json") if "_results" not in f.name]

if not json_files:
    print(f"\nERROR: No product files found in {processed_folder}")
    exit(1)

# Get most recent file
json_file = max(json_files, key=lambda p: p.stat().st_mtime)

with open(json_file, "r", encoding='utf-8') as f:
    data = json.load(f)

products = data.get('products', [])
print(f"\nLoaded {len(products)} products from {json_file.name}")

headers = {
    "Authorization": f"Bearer {auth_manager.access_token}",
    "Content-Type": "application/json",
    "Content-Language": "en-US"
}

# STEP 0: Ensure merchant location exists
print("\n" + "="*70)
print("[Step 0] Ensuring merchant location exists...")
print("="*70)

location_key = "us_warehouse"
location_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/location/{location_key}"

response = requests.get(location_url, headers=headers)

if response.status_code == 404:
    print(f"\nCreating merchant location '{location_key}'...")
    location_data = {
        "location": {
            "address": {
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
        print(f"  [OK] Created location '{location_key}'")
    else:
        print(f"  [ERROR] {response.text}")
        exit(1)
else:
    print(f"  [OK] Location '{location_key}' already exists")

# Process each product
results = []

for idx, product in enumerate(products, 1):
    print("\n" + "="*70)
    print(f"Processing Product {idx}/{len(products)}")
    print("="*70)

    asin = product["asin"]
    sku = f"AMZN-{asin}"
    title = product["title"]
    description = product.get("description", "")
    bullet_points = product.get("bulletPoints", [])
    specifications = product.get("specifications", {})
    images = product.get("images", [])

    print(f"\nProduct: {title[:60]}...")
    print(f"SKU: {sku}")

    # STEP 1: LLM selects category
    print("\n[Step 1] LLM Category Selection...")
    try:
        category_id, category_name, confidence = category_selector.select_category(
            title, description, bullet_points
        )
        print(f"  [OK] Selected: {category_name} (ID: {category_id})")
        print(f"  Confidence: {confidence:.2f}")
    except Exception as e:
        print(f"  [ERROR] Category selection failed: {str(e)}")
        continue

    # STEP 2: Get category requirements
    print("\n[Step 2] Fetching category requirements...")
    try:
        requirements = category_selector.get_category_requirements(category_id)
        required_count = len(requirements.get('required', []))
        print(f"  [OK] Found {required_count} required aspects")

        if required_count > 0:
            print(f"  Required aspects:")
            for aspect in requirements['required']:
                print(f"    - {aspect['name']} ({aspect['mode']}, {aspect['cardinality']})")
    except Exception as e:
        print(f"  [WARNING] Could not fetch requirements: {str(e)}")
        requirements = {'required': [], 'recommended': [], 'optional': []}

    # STEP 3: LLM fills required aspects
    filled_aspects = {}
    if requirements.get('required'):
        print("\n[Step 3] LLM filling required aspects...")
        try:
            product_data = {
                'title': title,
                'description': description,
                'bulletPoints': bullet_points,
                'specifications': specifications
            }
            filled_aspects = category_selector.fill_category_requirements(product_data, requirements)
            print(f"  [OK] Filled {len(filled_aspects)} aspects")
            for name, value in filled_aspects.items():
                print(f"    - {name}: {value}")
        except Exception as e:
            print(f"  [WARNING] Could not fill aspects: {str(e)}")
            filled_aspects = {}

    # STEP 4: Calculate price
    print("\n[Step 4] Calculating pricing...")
    amazon_price = product_mapper.parse_price(product.get("price", "$0.00"))
    multiplier = product.get("price_multiplier", 2.0)
    ebay_price = product_mapper.calculate_ebay_price(amazon_price, multiplier=multiplier)
    print(f"  Amazon: ${amazon_price:.2f} -> eBay: ${ebay_price:.2f} ({multiplier}x)")

    # STEP 5: Create inventory item
    print("\n[Step 5] Creating inventory item...")

    # Build aspects (Brand, MPN, Condition, + category-specific)
    aspects = {
        "Brand": [product_mapper.extract_brand(title, description)],
        "MPN": [asin],
        "Condition": ["New"]
    }

    # Add filled category-specific aspects
    for aspect_name, aspect_value in filled_aspects.items():
        if isinstance(aspect_value, list):
            aspects[aspect_name] = aspect_value
        else:
            aspects[aspect_name] = [aspect_value]

    inventory_item = {
        "sku": sku,
        "locale": "en_US",
        "product": {
            "title": title[:80],
            "description": description,
            "imageUrls": images[:12],  # eBay limit
            "aspects": aspects
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

    inv_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/inventory_item/{sku}"
    response = requests.put(inv_url, headers=headers, json=inventory_item)

    if response.status_code in [200, 201, 204]:
        print(f"  [OK] Inventory item created")
    else:
        print(f"  [ERROR] {response.text}")
        results.append({'sku': sku, 'status': 'failed', 'stage': 'inventory', 'error': response.text})
        continue

    # STEP 6: Build listing description HTML
    print("\n[Step 6] Building listing description...")
    listing_description = product_mapper._build_html_description({
        "title": title,
        "description": description,
        "bulletPoints": bullet_points,
        "images": images
    })

    # STEP 7: Create offer
    print("\n[Step 7] Creating offer...")

    offer = {
        "sku": sku,
        "marketplaceId": "EBAY_US",
        "format": "FIXED_PRICE",
        "availableQuantity": 10,
        "categoryId": category_id,
        "listingDescription": listing_description,
        "listingPolicies": {
            "paymentPolicyId": payment_policy_id,
            "returnPolicyId": return_policy_id,
            "fulfillmentPolicyId": fulfillment_policy_id
        },
        "pricingSummary": {
            "price": {
                "value": str(ebay_price),
                "currency": "USD"
            }
        },
        "merchantLocationKey": location_key
    }

    offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
    response = requests.post(offer_url, headers=headers, json=offer)

    if response.status_code in [200, 201]:
        offer_id = response.json().get("offerId")
        print(f"  [OK] Offer created (ID: {offer_id})")
    else:
        print(f"  [ERROR] {response.text}")
        results.append({'sku': sku, 'status': 'failed', 'stage': 'offer', 'error': response.text})
        continue

    # STEP 8: Publish offer
    print("\n[Step 8] Publishing offer...")

    publish_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}/publish"
    response = requests.post(publish_url, headers=headers)

    if response.status_code in [200, 201]:
        listing_id = response.json().get("listingId")
        print(f"  [SUCCESS] Published! Listing ID: {listing_id}")
        print(f"  View at: https://www.ebay.com/itm/{listing_id}")

        results.append({
            'sku': sku,
            'status': 'success',
            'category_id': category_id,
            'category_name': category_name,
            'offer_id': offer_id,
            'listing_id': listing_id
        })
    else:
        error_data = response.text
        print(f"  [ERROR] Publish failed: {error_data}")
        results.append({
            'sku': sku,
            'status': 'failed',
            'stage': 'publish',
            'error': error_data,
            'category_id': category_id,
            'offer_id': offer_id
        })

# FINAL SUMMARY
print("\n" + "="*70)
print("FINAL SUMMARY")
print("="*70)

successful = [r for r in results if r['status'] == 'success']
failed = [r for r in results if r['status'] == 'failed']

print(f"\nTotal products processed: {len(products)}")
print(f"Successfully published: {len(successful)}")
print(f"Failed: {len(failed)}")

if successful:
    print("\n[SUCCESS] Published listings:")
    for result in successful:
        print(f"  - {result['sku']}: {result['category_name']} (ID: {result['category_id']})")
        print(f"    https://www.ebay.com/itm/{result['listing_id']}")

if failed:
    print("\n[FAILED] Failed listings:")
    for result in failed:
        print(f"  - {result['sku']}: Failed at {result.get('stage', 'unknown')}")
        if 'category_id' in result:
            print(f"    Category: {result.get('category_id')}")

print("\nView all active listings at:")
print("https://www.ebay.com/sh/lst/active")

print("\n" + "="*70)

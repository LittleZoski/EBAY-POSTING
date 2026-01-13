"""
Complete end-to-end flow with LLM-powered category selection
Flow: JSON -> LLM Category Selection -> Inventory Item -> Offer (with requirements) -> Published Listing
"""

import json
import requests
import logging
import sys
from pathlib import Path
from token_manager import get_token_manager
from ebay_auth import auth_manager
from product_mapper import product_mapper
from semantic_category_selector import SemanticCategorySelector
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

# Get active account and token manager
active_account = settings.active_account
account_name = f"Account {active_account}" + (" (Primary)" if active_account == 1 else " (Secondary)")
token_manager = get_token_manager(active_account)

# Load tokens for active account
if not token_manager.load_tokens():
    print(f"ERROR: No OAuth token found for {account_name}!")
    print(f"Please run: python authorize_account.py {active_account}")
    exit(1)

# Load business policies for active account
policies = settings.get_business_policies()
payment_policy_id = policies["payment_policy_id"]
return_policy_id = policies["return_policy_id"]
fulfillment_policy_id = policies["fulfillment_policy_id"]

print("\n" + "="*70)
print("Complete eBay Listing Flow with LLM Category Selection")
print(f"Active Account: {account_name}")
print("="*70)

# Initialize semantic category selector (Vector DB + LLM hybrid)
print("\nInitializing semantic category selector (Vector DB)...")
try:
    category_selector = SemanticCategorySelector()
    print(f"  [OK] Vector DB loaded with semantic search enabled")
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
    sku = asin
    title = product["title"]
    description = product.get("description", "")
    bullet_points = product.get("bulletPoints", [])
    specifications = product.get("specifications", {})
    raw_images = product.get("images", [])

    # Filter out unwanted images (UI elements, functional icons, high-res variants, etc.)
    images = []
    for img_url in raw_images:
        # AGGRESSIVE: Skip ANY images with AC_SL pattern (e.g., _AC_SL1000_, _AC_SL1500_)
        if "_AC_SL" in img_url or "AC_SL" in img_url:
            continue
        # Skip UI elements from /images/G/ directory (Amazon UI assets, icons, buttons)
        if "/images/G/" in img_url or "/G/01/" in img_url:
            continue
        # Skip play button overlay images (video thumbnails)
        if "PKplay-button" in img_url or "play-icon" in img_url or "play_button" in img_url:
            continue
        # Skip 360-degree view icons and interactive elements
        if "360_icon" in img_url or "360-icon" in img_url or "imageBlock" in img_url:
            continue
        # Skip transparent pixel placeholders
        if "transparent-pixel" in img_url or "transparent_pixel" in img_url:
            continue
        images.append(img_url)

    print(f"  Filtered images: {len(raw_images)} -> {len(images)}")

    # If description is empty, create one from bullet points
    if not description or description.strip() == "":
        if bullet_points:
            description = "\n\n".join(bullet_points)
        else:
            description = title  # Last resort: use title

    print(f"\nProduct: {title[:60]}...")
    print(f"SKU: {sku}")

    # STEP 1: LLM optimizes title, extracts brand AND selects category (single call for efficiency!)
    print("\n[Step 1] LLM Title Optimization + Brand Extraction + Category Selection...")
    try:
        optimized_title, brand, category_id, category_name, confidence = category_selector.optimize_title_and_select_category(
            title, description, bullet_points, specifications
        )
        print(f"  [OK] Original: {title[:60]}...")
        print(f"  [OK] Optimized ({len(optimized_title)} chars): {optimized_title}")
        print(f"  [OK] Brand: {brand}")
        print(f"  [OK] Category: {category_name} (ID: {category_id})")
        print(f"  Confidence: {confidence:.2f}")

        # Use optimized title and extracted brand for the listing
        title = optimized_title
    except Exception as e:
        print(f"  [ERROR] Optimization failed: {str(e)}")
        # Fallback: truncate title if needed
        if len(title) > 80:
            title = title[:77] + "..."
            print(f"  [FALLBACK] Truncated title to: {title}")
        # Fallback brand
        brand = "Generic"
        print(f"  [FALLBACK] Using brand: {brand}")
        continue

    # STEP 2: Get category requirements
    print("\n[Step 2] Fetching category requirements...")
    try:
        requirements = category_selector.get_category_requirements(category_id)
        required_count = len(requirements.get('required', []))
        recommended_count = len(requirements.get('recommended', []))
        print(f"  [OK] Found {required_count} required, {recommended_count} recommended aspects")

        if required_count > 0:
            print(f"  Required aspects:")
            for aspect in requirements['required']:
                print(f"    - {aspect['name']} ({aspect['mode']}, {aspect['cardinality']})")

        if recommended_count > 0:
            print(f"  Recommended aspects (will enhance listing visibility):")
            for aspect in requirements['recommended'][:5]:  # Show first 5
                print(f"    - {aspect['name']} ({aspect['mode']}, {aspect['cardinality']})")
            if recommended_count > 5:
                print(f"    ... and {recommended_count - 5} more")
    except Exception as e:
        print(f"  [WARNING] Could not fetch requirements: {str(e)}")
        requirements = {'required': [], 'recommended': [], 'optional': []}

    # STEP 3: LLM fills required + recommended aspects (in single call)
    filled_aspects = {}
    if requirements.get('required') or requirements.get('recommended'):
        print("\n[Step 3] LLM filling required + recommended aspects...")
        try:
            product_data = {
                'title': title,
                'description': description,
                'bulletPoints': bullet_points,
                'specifications': specifications
            }
            # Enhanced call: include_recommended=True to fill both required and recommended in one LLM call
            filled_aspects = category_selector.fill_category_requirements(
                product_data,
                requirements,
                include_recommended=True
            )
            print(f"  [OK] Filled {len(filled_aspects)} aspects total")
            for name, value in filled_aspects.items():
                print(f"    - {name}: {value}")
        except Exception as e:
            print(f"  [WARNING] Could not fill aspects: {str(e)}")
            filled_aspects = {}

    # STEP 4: Calculate price (using tiered pricing strategy + delivery fee)
    print("\n[Step 4] Calculating pricing...")
    amazon_price = product_mapper.parse_price(product.get("price", "$0.00"))
    delivery_fee = product_mapper.parse_price(product.get("deliveryFee", "$0.00"))

    # Get optional price_multiplier override from product data
    # If not provided, calculate_ebay_price will use tiered pricing
    multiplier = product.get("price_multiplier", None)
    ebay_price = product_mapper.calculate_ebay_price(amazon_price, delivery_fee=delivery_fee, multiplier=multiplier)

    # Show which multiplier was used and cost breakdown
    total_amazon_cost = amazon_price + delivery_fee
    if delivery_fee > 0:
        print(f"  Amazon Product: ${amazon_price:.2f}")
        print(f"  Amazon Delivery: ${delivery_fee:.2f}")
        print(f"  Total Amazon Cost: ${total_amazon_cost:.2f}")
    else:
        print(f"  Amazon Cost: ${amazon_price:.2f} (no delivery fee)")

    if multiplier is not None:
        print(f"  eBay Price: ${ebay_price:.2f} (Override: {multiplier}x)")
    else:
        actual_multiplier = product_mapper.get_tiered_multiplier(total_amazon_cost)
        print(f"  eBay Price: ${ebay_price:.2f} (Tiered: {actual_multiplier}x)")

    # STEP 5: Create inventory item
    print("\n[Step 5] Creating inventory item...")

    # Build aspects (Brand, MPN, Condition, + category-specific)
    # Brand was extracted by LLM in Step 1 for cost efficiency
    aspects = {
        "Brand": [brand],
        "MPN": [asin],
        "Condition": ["New"]
    }

    # Add filled category-specific aspects
    # CRITICAL: Don't overwrite Brand/MPN/Condition that we already set above
    # The LLM might return these as required aspects, but we've already handled them
    protected_aspects = {"Brand", "MPN", "Condition"}

    for aspect_name, aspect_value in filled_aspects.items():
        # Skip if this aspect is already set (Brand, MPN, Condition)
        if aspect_name in protected_aspects:
            print(f"  [SKIP] Aspect '{aspect_name}' already set, not overwriting")
            continue

        # Skip if value is None or empty
        if aspect_value is None or (isinstance(aspect_value, str) and not aspect_value.strip()):
            print(f"  [SKIP] Aspect '{aspect_name}' has empty value from LLM")
            continue

        if isinstance(aspect_value, list):
            aspects[aspect_name] = aspect_value
        else:
            aspects[aspect_name] = [aspect_value]

    # Extract package weight from specifications
    package_weight = None
    weight_str = specifications.get("Item Weight", "")

    # Try to parse weight (e.g., "1.96 pounds", "12.3 ounces")
    if weight_str:
        import re
        match = re.search(r'([\d.]+)\s*(pound|lb|ounce|oz)', weight_str.lower())
        if match:
            weight_value = float(match.group(1))
            weight_unit = match.group(2)

            # Convert to pounds if needed
            if 'oz' in weight_unit or 'ounce' in weight_unit:
                weight_value = weight_value / 16  # Convert ounces to pounds

            package_weight = {
                "value": str(round(weight_value, 2)),
                "unit": "POUND"
            }

    # If no weight found, use a default (required by eBay)
    if not package_weight:
        package_weight = {
            "value": "1.0",
            "unit": "POUND"
        }
        print(f"  [WARNING] No weight found in specs, using default: 1.0 lb")

    inventory_item = {
        "sku": sku,
        "locale": "en_US",
        "product": {
            "title": title,  # Already optimized to ≤80 chars by LLM with smart truncation
            "description": description,
            "imageUrls": images[:12],  # eBay limit
            "aspects": aspects
        },
        "condition": "NEW",
        "packageWeightAndSize": {
            "weight": package_weight
        },
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

    # STEP 7: Create or update offer
    print("\n[Step 7] Creating or updating offer...")

    # First, check if an offer already exists for this SKU
    check_offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
    check_response = requests.get(check_offer_url, headers=headers, params={'sku': sku})

    existing_offer_id = None
    if check_response.status_code == 200:
        existing_offers = check_response.json().get('offers', [])
        if existing_offers:
            existing_offer_id = existing_offers[0].get('offerId')
            print(f"  Found existing offer (ID: {existing_offer_id}), will update it")

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

    if existing_offer_id:
        # Update existing offer
        offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{existing_offer_id}"
        response = requests.put(offer_url, headers=headers, json=offer)
        offer_id = existing_offer_id
    else:
        # Create new offer
        offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
        response = requests.post(offer_url, headers=headers, json=offer)

    if response.status_code in [200, 201, 204]:
        if not existing_offer_id:
            offer_id = response.json().get("offerId")
        print(f"  [OK] Offer {'updated' if existing_offer_id else 'created'} (ID: {offer_id})")
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

"""
Complete end-to-end flow with PARALLEL PROCESSING + SMART CACHING
Flow: JSON -> LLM Category Selection -> Inventory Item -> Offer -> Published Listing

OPTIMIZATIONS:
- Parallel processing with configurable worker pool (10x faster for large batches)
- Rate limit monitoring and automatic throttling
- Smart caching for category requirements
- Progress tracking and detailed timing stats

BACKWARD COMPATIBLE: Uses same data format and LLM flow as complete_listing_flow_llm.py
"""

import json
import requests
import logging
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Dict, List, Tuple, Optional
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


class RateLimitMonitor:
    """Monitor eBay API rate limits and throttle requests"""

    def __init__(self):
        self.lock = Lock()
        self.remaining_calls = None
        self.limit = None
        self.reset_time = None
        self.last_check = time.time()

    def update_from_headers(self, headers: Dict[str, str]):
        """Update rate limit info from response headers"""
        with self.lock:
            # eBay returns rate limit info in headers like:
            # X-EBAY-C-RATE-LIMIT-REMAINING
            # X-EBAY-C-RATE-LIMIT-LIMIT
            # X-EBAY-C-RATE-LIMIT-RESET

            remaining = headers.get('X-EBAY-C-RATE-LIMIT-REMAINING')
            limit = headers.get('X-EBAY-C-RATE-LIMIT-LIMIT')
            reset_time = headers.get('X-EBAY-C-RATE-LIMIT-RESET')

            if remaining:
                self.remaining_calls = int(remaining)
            if limit:
                self.limit = int(limit)
            if reset_time:
                self.reset_time = int(reset_time)

            self.last_check = time.time()

    def should_throttle(self) -> Tuple[bool, float]:
        """
        Check if we should throttle requests

        Returns:
            Tuple of (should_throttle, wait_seconds)
        """
        with self.lock:
            if self.remaining_calls is None:
                return False, 0.0

            # If we're running low on calls (less than 20%), throttle
            if self.limit and self.remaining_calls < (self.limit * 0.2):
                # Calculate wait time based on reset time
                if self.reset_time:
                    wait_time = max(0, self.reset_time - time.time())
                    return True, min(wait_time, 60)  # Max 60 seconds
                return True, 2.0  # Default 2 second wait

            return False, 0.0

    def get_status(self) -> str:
        """Get current rate limit status"""
        with self.lock:
            if self.remaining_calls is None:
                return "Unknown"
            return f"{self.remaining_calls}/{self.limit} calls remaining"


class CategoryRequirementsCache:
    """Cache category requirements to avoid redundant API calls"""

    def __init__(self):
        self.cache = {}
        self.lock = Lock()
        self.hits = 0
        self.misses = 0

    def get(self, category_id: str) -> Optional[Dict]:
        """Get cached requirements for a category"""
        with self.lock:
            if category_id in self.cache:
                self.hits += 1
                return self.cache[category_id]
            self.misses += 1
            return None

    def set(self, category_id: str, requirements: Dict):
        """Cache requirements for a category"""
        with self.lock:
            self.cache[category_id] = requirements

    def get_stats(self) -> str:
        """Get cache statistics"""
        total = self.hits + self.misses
        if total == 0:
            return "No cache requests"
        hit_rate = (self.hits / total) * 100
        return f"Cache: {self.hits} hits, {self.misses} misses ({hit_rate:.1f}% hit rate)"


class ParallelListingProcessor:
    """Process multiple listings in parallel with rate limiting"""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.rate_monitor = RateLimitMonitor()
        self.requirements_cache = CategoryRequirementsCache()
        self.results_lock = Lock()
        self.results = []
        self.category_selector = None
        self.headers = None
        self.location_key = "us_warehouse"
        self.policies = None

    def initialize(self):
        """Initialize shared resources"""
        print("\n" + "="*70)
        print("Parallel eBay Listing Flow with Smart Caching")
        print(f"Max Workers: {self.max_workers}")
        print("="*70)

        # Initialize semantic category selector (Vector DB + LLM hybrid)
        print("\nInitializing semantic category selector (Vector DB)...")
        try:
            self.category_selector = SemanticCategorySelector()
            print(f"  [OK] Vector DB loaded with semantic search enabled")
        except Exception as e:
            print(f"  [ERROR] Failed to initialize LLM selector: {str(e)}")
            raise

        # Setup headers
        self.headers = {
            "Authorization": f"Bearer {auth_manager.access_token}",
            "Content-Type": "application/json",
            "Content-Language": "en-US"
        }

        # Load business policies
        self.policies = settings.get_business_policies()

        # Ensure merchant location exists
        self._ensure_merchant_location()

    def _ensure_merchant_location(self):
        """Ensure merchant location exists (one-time check)"""
        print("\n" + "="*70)
        print("[Setup] Ensuring merchant location exists...")
        print("="*70)

        location_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/location/{self.location_key}"
        response = requests.get(location_url, headers=self.headers)

        # Update rate limit info
        self.rate_monitor.update_from_headers(response.headers)

        if response.status_code == 404:
            print(f"\nCreating merchant location '{self.location_key}'...")
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

            response = requests.post(location_url, headers=self.headers, json=location_data)
            self.rate_monitor.update_from_headers(response.headers)

            if response.status_code in [200, 201, 204]:
                print(f"  [OK] Created location '{self.location_key}'")
            else:
                print(f"  [ERROR] {response.text}")
                raise Exception("Failed to create merchant location")
        else:
            print(f"  [OK] Location '{self.location_key}' already exists")

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make an API request with rate limit monitoring

        Args:
            method: HTTP method (GET, POST, PUT)
            url: Request URL
            **kwargs: Additional arguments for requests

        Returns:
            Response object
        """
        # Check if we should throttle
        should_wait, wait_time = self.rate_monitor.should_throttle()
        if should_wait:
            logger.warning(f"  [THROTTLE] Waiting {wait_time:.1f}s due to rate limits...")
            time.sleep(wait_time)

        # Make request
        if method.upper() == 'GET':
            response = requests.get(url, headers=self.headers, **kwargs)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=self.headers, **kwargs)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=self.headers, **kwargs)
        else:
            raise ValueError(f"Unsupported method: {method}")

        # Update rate limit info
        self.rate_monitor.update_from_headers(response.headers)

        return response

    def _get_category_requirements(self, category_id: str) -> Dict:
        """Get category requirements with caching"""
        # Check cache first
        cached = self.requirements_cache.get(category_id)
        if cached is not None:
            return cached

        # Fetch from API
        try:
            requirements = self.category_selector.get_category_requirements(category_id)
            # Cache the result
            self.requirements_cache.set(category_id, requirements)
            return requirements
        except Exception as e:
            logger.error(f"  [WARNING] Could not fetch requirements: {str(e)}")
            empty_requirements = {'required': [], 'recommended': [], 'optional': []}
            self.requirements_cache.set(category_id, empty_requirements)
            return empty_requirements

    def process_single_product(self, product: Dict, idx: int, total: int) -> Dict:
        """
        Process a single product (will be run in parallel)

        Args:
            product: Product data from JSON
            idx: Product index (1-based)
            total: Total number of products

        Returns:
            Result dictionary
        """
        start_time = time.time()

        print("\n" + "="*70)
        print(f"Processing Product {idx}/{total}")
        print("="*70)

        asin = product["asin"]
        sku = asin
        title = product["title"]
        description = product.get("description", "")
        bullet_points = product.get("bulletPoints", [])
        specifications = product.get("specifications", {})
        raw_images = product.get("images", [])

        # Filter images (same logic as original)
        images = []
        for img_url in raw_images:
            if "_AC_SL" in img_url or "AC_SL" in img_url:
                continue
            if "/images/G/" in img_url or "/G/01/" in img_url:
                continue
            if "PKplay-button" in img_url or "play-icon" in img_url or "play_button" in img_url:
                continue
            if "360_icon" in img_url or "360-icon" in img_url or "imageBlock" in img_url:
                continue
            if "transparent-pixel" in img_url or "transparent_pixel" in img_url:
                continue
            images.append(img_url)

        print(f"  Filtered images: {len(raw_images)} -> {len(images)}")

        # Create description if empty
        if not description or description.strip() == "":
            if bullet_points:
                description = "\n\n".join(bullet_points)
            else:
                description = title

        print(f"\nProduct: {title[:60]}...")
        print(f"SKU: {sku}")

        try:
            # STEP 1: Vector DB selects category + LLM optimizes title & extracts brand
            print("\n[Step 1] Vector DB Category Selection + LLM Title Optimization...")
            optimized_title, brand, category_id, category_name, confidence = self.category_selector.optimize_title_and_select_category(
                title, description, bullet_points, specifications
            )
            print(f"  [OK] Original: {title[:60]}...")
            print(f"  [OK] Optimized ({len(optimized_title)} chars): {optimized_title}")
            print(f"  [OK] Brand: {brand}")
            print(f"  [OK] Category: {category_name} (ID: {category_id})")
            print(f"  [OK] Similarity: {confidence:.3f}")

            title = optimized_title

        except Exception as e:
            print(f"  [ERROR] Optimization failed: {str(e)}")
            if len(title) > 80:
                title = title[:77] + "..."
            brand = "Generic"
            return {'sku': sku, 'status': 'failed', 'stage': 'llm_optimization', 'error': str(e)}

        try:
            # STEP 2: Get category requirements (WITH CACHING!)
            print("\n[Step 2] Fetching category requirements (cached)...")
            requirements = self._get_category_requirements(category_id)
            required_count = len(requirements.get('required', []))
            recommended_count = len(requirements.get('recommended', []))
            print(f"  [OK] Found {required_count} required, {recommended_count} recommended aspects")

            if required_count > 0:
                print(f"  Required aspects:")
                for aspect in requirements['required'][:5]:  # Show first 5
                    print(f"    - {aspect['name']} ({aspect['mode']}, {aspect['cardinality']})")

            if recommended_count > 0:
                print(f"  Recommended aspects (will enhance visibility):")
                for aspect in requirements['recommended'][:3]:  # Show first 3
                    print(f"    - {aspect['name']} ({aspect['mode']}, {aspect['cardinality']})")
                if recommended_count > 3:
                    print(f"    ... and {recommended_count - 3} more")

        except Exception as e:
            print(f"  [WARNING] Requirements fetch failed: {str(e)}")
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
                # Enhanced call: include_recommended=True
                filled_aspects = self.category_selector.fill_category_requirements(
                    product_data,
                    requirements,
                    include_recommended=True
                )
                print(f"  [OK] Filled {len(filled_aspects)} aspects total")
                for name, value in list(filled_aspects.items())[:5]:  # Show first 5
                    print(f"    - {name}: {value}")
                if len(filled_aspects) > 5:
                    print(f"    ... and {len(filled_aspects) - 5} more")
            except Exception as e:
                print(f"  [WARNING] Could not fill aspects: {str(e)}")
                filled_aspects = {}

        # STEP 4: Calculate price
        print("\n[Step 4] Calculating pricing...")
        amazon_price = product_mapper.parse_price(product.get("price", "$0.00"))
        delivery_fee = product_mapper.parse_price(product.get("deliveryFee", "$0.00"))
        multiplier = product.get("price_multiplier", None)
        ebay_price = product_mapper.calculate_ebay_price(amazon_price, delivery_fee=delivery_fee, multiplier=multiplier)

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

        # Extract package weight
        package_weight = None
        weight_str = specifications.get("Item Weight", "")

        if weight_str:
            import re
            match = re.search(r'([\d.]+)\s*(pound|lb|ounce|oz)', weight_str.lower())
            if match:
                weight_value = float(match.group(1))
                weight_unit = match.group(2)

                if 'oz' in weight_unit or 'ounce' in weight_unit:
                    weight_value = weight_value / 16

                package_weight = {
                    "value": str(round(weight_value, 2)),
                    "unit": "POUND"
                }

        if not package_weight:
            package_weight = {
                "value": "1.0",
                "unit": "POUND"
            }

        inventory_item = {
            "sku": sku,
            "locale": "en_US",
            "product": {
                "title": title,  # Already optimized to ≤80 chars by LLM with smart truncation
                "description": description,
                "imageUrls": images[:12],
                "aspects": aspects
            },
            "condition": "NEW",
            "packageWeightAndSize": {
                "weight": package_weight
            },
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": settings.default_inventory_quantity,
                    "availabilityDistributions": [
                        {
                            "merchantLocationKey": self.location_key,
                            "quantity": settings.default_inventory_quantity
                        }
                    ]
                }
            }
        }

        inv_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/inventory_item/{sku}"
        response = self._make_request('PUT', inv_url, json=inventory_item)

        if response.status_code in [200, 201, 204]:
            print(f"  [OK] Inventory item created")
        else:
            print(f"  [ERROR] {response.text}")
            return {'sku': sku, 'status': 'failed', 'stage': 'inventory', 'error': response.text}

        # STEP 6: Build listing description HTML
        print("\n[Step 6] Building listing description...")
        listing_description = product_mapper._build_html_description({
            "title": title,
            "description": description,
            "bulletPoints": bullet_points,
            "images": images,
            "specifications": specifications
        })

        # STEP 7: Create or update offer
        print("\n[Step 7] Creating or updating offer...")

        # First, check if an offer already exists for this SKU
        check_offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
        check_response = self._make_request('GET', check_offer_url, params={'sku': sku})

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
            "availableQuantity": settings.default_inventory_quantity,
            "categoryId": category_id,
            "listingDescription": listing_description,
            "listingPolicies": {
                "paymentPolicyId": self.policies["payment_policy_id"],
                "returnPolicyId": self.policies["return_policy_id"],
                "fulfillmentPolicyId": self.policies["fulfillment_policy_id"]
            },
            "pricingSummary": {
                "price": {
                    "value": str(ebay_price),
                    "currency": "USD"
                }
            },
            "merchantLocationKey": self.location_key
        }

        if existing_offer_id:
            # Update existing offer
            offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{existing_offer_id}"
            response = self._make_request('PUT', offer_url, json=offer)
            offer_id = existing_offer_id
        else:
            # Create new offer
            offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
            response = self._make_request('POST', offer_url, json=offer)

        if response.status_code in [200, 201, 204]:
            if not existing_offer_id:
                offer_id = response.json().get("offerId")
            print(f"  [OK] Offer {'updated' if existing_offer_id else 'created'} (ID: {offer_id})")
        else:
            print(f"  [ERROR] {response.text}")
            return {'sku': sku, 'status': 'failed', 'stage': 'offer', 'error': response.text}

        # STEP 8: Publish offer
        print("\n[Step 8] Publishing offer...")

        publish_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}/publish"
        response = self._make_request('POST', publish_url)

        elapsed = time.time() - start_time

        if response.status_code in [200, 201]:
            listing_id = response.json().get("listingId")
            print(f"  [SUCCESS] Published! Listing ID: {listing_id}")
            print(f"  View at: https://www.ebay.com/itm/{listing_id}")
            print(f"  Processing time: {elapsed:.1f}s")

            return {
                'sku': sku,
                'status': 'success',
                'category_id': category_id,
                'category_name': category_name,
                'offer_id': offer_id,
                'listing_id': listing_id,
                'processing_time': elapsed
            }
        else:
            error_data = response.text
            print(f"  [ERROR] Publish failed: {error_data}")
            print(f"  Processing time: {elapsed:.1f}s")
            return {
                'sku': sku,
                'status': 'failed',
                'stage': 'publish',
                'error': error_data,
                'category_id': category_id,
                'offer_id': offer_id,
                'processing_time': elapsed
            }

    def process_products(self, products: List[Dict]) -> List[Dict]:
        """
        Process multiple products in parallel

        Args:
            products: List of product dictionaries

        Returns:
            List of result dictionaries
        """
        print(f"\nProcessing {len(products)} products with {self.max_workers} parallel workers...")
        print(f"Rate limit status: {self.rate_monitor.get_status()}")
        print("="*70)

        start_time = time.time()
        results = []

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_product = {
                executor.submit(self.process_single_product, product, idx, len(products)): product
                for idx, product in enumerate(products, 1)
            }

            # Process completed tasks
            for future in as_completed(future_to_product):
                product = future_to_product[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Product {product.get('asin', 'unknown')} raised exception: {str(e)}")
                    results.append({
                        'sku': product.get('asin', 'unknown'),
                        'status': 'failed',
                        'stage': 'exception',
                        'error': str(e)
                    })

        elapsed = time.time() - start_time

        # FINAL SUMMARY
        print("\n" + "="*70)
        print("FINAL SUMMARY")
        print("="*70)

        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']

        print(f"\nTotal products processed: {len(products)}")
        print(f"Successfully published: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print(f"Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")

        if successful:
            avg_time = sum(r.get('processing_time', 0) for r in successful) / len(successful)
            print(f"Average time per item: {avg_time:.1f}s")
            print(f"Throughput: {len(products)/elapsed*3600:.0f} items/hour")

        print(f"\n{self.requirements_cache.get_stats()}")
        print(f"Rate limit status: {self.rate_monitor.get_status()}")

        if successful:
            print("\n[SUCCESS] Published listings:")
            for result in successful[:10]:  # Show first 10
                print(f"  - {result['sku']}: {result['category_name']} (ID: {result['category_id']})")
                print(f"    https://www.ebay.com/itm/{result['listing_id']}")
            if len(successful) > 10:
                print(f"  ... and {len(successful) - 10} more")

        if failed:
            print("\n[FAILED] Failed listings:")
            for result in failed[:10]:  # Show first 10
                print(f"  - {result['sku']}: Failed at {result.get('stage', 'unknown')}")
                if 'category_id' in result:
                    print(f"    Category: {result.get('category_id')}")
            if len(failed) > 10:
                print(f"  ... and {len(failed) - 10} more")

        print("\nView all active listings at:")
        print("https://www.ebay.com/sh/lst/active")
        print("\n" + "="*70)

        return results


def main():
    """Main entry point"""
    # Get active account and token manager
    active_account = settings.active_account
    account_name = f"Account {active_account}" + (" (Primary)" if active_account == 1 else " (Secondary)")
    token_manager = get_token_manager(active_account)

    # Load tokens for active account
    if not token_manager.load_tokens():
        print(f"ERROR: No OAuth token found for {account_name}!")
        print(f"Please run: python authorize_account.py {active_account}")
        exit(1)

    # Load Amazon products from processed folder (most recent file)
    processed_folder = Path(settings.processed_folder)
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

    # Get max workers from settings
    max_workers = settings.max_workers

    # Process products in parallel
    processor = ParallelListingProcessor(max_workers=max_workers)
    processor.initialize()
    results = processor.process_products(products)

    # Optionally save results
    results_file = processed_folder / f"{json_file.stem}_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            'source_file': json_file.name,
            'processed_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'total_products': len(products),
            'successful': len([r for r in results if r['status'] == 'success']),
            'failed': len([r for r in results if r['status'] == 'failed']),
            'results': results
        }, f, indent=2)

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    import os
    main()

"""
Test downloading category requirements (item aspects) from eBay Taxonomy API
API: getItemAspectsForCategory
Docs: https://developer.ebay.com/api-docs/commerce/taxonomy/resources/category_tree/methods/getItemAspectsForCategory
"""
import requests
import json
from category_suggester import CategorySuggester
from config import settings

print("="*70)
print("Testing Category Requirements API (getItemAspectsForCategory)")
print("="*70)

# Initialize suggester to get app token
suggester = CategorySuggester(
    client_id=settings.ebay_app_id,
    client_secret=settings.ebay_cert_id
)

# Get application token
token = suggester.get_application_token()

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json"
}

# Test with different categories we tried earlier
test_categories = {
    "360": "Art Prints (worked - minimal requirements)",
    "261186": "Books (failed - requires Book Title)",
    "139973": "Video Games (failed - requires Platform)",
    "182073": "Vintage Cell Phones (failed - requires Model)",
}

category_tree_id = "0"  # EBAY_US

print(f"\nTesting getItemAspectsForCategory API...\n")

for cat_id, description in test_categories.items():
    print("="*70)
    print(f"Category {cat_id}: {description}")
    print("="*70)

    url = f"{settings.ebay_api_base_url}/commerce/taxonomy/v1/category_tree/{category_tree_id}/get_item_aspects_for_category"

    params = {
        "category_id": cat_id
    }

    print(f"\nCalling API: GET {url}")
    print(f"Params: {params}\n")

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        print(f"Response: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Parse the aspects
            aspects = data.get('aspects', [])

            print(f"\nFound {len(aspects)} aspects for this category:")

            # Separate by requirement level
            required = []
            recommended = []
            optional = []

            for aspect in aspects:
                aspect_name = aspect.get('localizedAspectName', 'Unknown')
                constraint = aspect.get('aspectConstraint', {})

                is_required = constraint.get('aspectRequired', False)
                is_recommended = constraint.get('aspectUsage') == 'RECOMMENDED'
                cardinality = constraint.get('itemToAspectCardinality', 'SINGLE')

                aspect_info = {
                    'name': aspect_name,
                    'required': is_required,
                    'cardinality': cardinality,
                    'mode': constraint.get('aspectMode', 'UNKNOWN')
                }

                if is_required:
                    required.append(aspect_info)
                elif is_recommended:
                    recommended.append(aspect_info)
                else:
                    optional.append(aspect_info)

            print(f"\n  REQUIRED ({len(required)}):")
            for asp in required:
                print(f"    - {asp['name']} (cardinality: {asp['cardinality']})")

            print(f"\n  RECOMMENDED ({len(recommended)}):")
            for asp in recommended[:5]:  # Show first 5
                print(f"    - {asp['name']}")
            if len(recommended) > 5:
                print(f"    ... and {len(recommended) - 5} more")

            print(f"\n  OPTIONAL ({len(optional)}):")
            if optional:
                print(f"    {len(optional)} optional aspects available")

            # Save full response for this category
            output_file = f"category_aspects_{cat_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"\n  [Saved full response to {output_file}]")

        elif response.status_code == 204:
            print("  No aspects data available for this category")
        else:
            print(f"  [ERROR] Failed: {response.text}")

    except Exception as e:
        print(f"  [EXCEPTION] {str(e)}")

    print()

print("\n" + "="*70)
print("Summary")
print("="*70)
print("\nThis API returns:")
print("  - Required item specifics (must provide)")
print("  - Recommended item specifics (should provide)")
print("  - Optional item specifics (can provide)")
print("  - Cardinality (SINGLE or MULTI value)")
print("  - Aspect mode and usage information")
print("\nWe can cache this data along with the category tree!")
print("="*70)

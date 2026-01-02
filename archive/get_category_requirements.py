"""
Get required aspects for category 11450 using eBay Taxonomy API
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

category_id = "11450"
marketplace = "EBAY_US"

print("="*70)
print(f"Getting Category Requirements for {category_id}")
print("="*70)

# eBay Taxonomy API - Get Item Aspects for Category
url = f"{settings.ebay_api_base_url}/commerce/taxonomy/v1/category_tree/{marketplace}/get_item_aspects_for_category"

response = requests.get(
    url,
    headers=headers,
    params={"category_id": category_id}
)

print(f"\nStatus Code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    aspects = data.get('aspects', [])

    print(f"\nFound {len(aspects)} aspects for this category\n")

    required_aspects = [a for a in aspects if a.get('aspectConstraint', {}).get('aspectRequired')]
    recommended_aspects = [a for a in aspects if not a.get('aspectConstraint', {}).get('aspectRequired')]

    print(f"REQUIRED Aspects ({len(required_aspects)}):")
    print("="*70)
    for aspect in required_aspects:
        name = aspect.get('localizedAspectName')
        mode = aspect.get('aspectConstraint', {}).get('aspectMode')
        print(f"  - {name} (Mode: {mode})")

        # Show possible values
        values = aspect.get('aspectValues', [])
        if values and len(values) <= 10:
            print(f"    Possible values: {', '.join([v.get('localizedValue') for v in values[:10]])}")

    print(f"\nRECOMMENDED Aspects ({len(recommended_aspects)}):")
    print("="*70)
    for aspect in recommended_aspects[:10]:  # Show first 10
        name = aspect.get('localizedAspectName')
        print(f"  - {name}")

else:
    print(f"Error: {response.text}")

print("\n" + "="*70)

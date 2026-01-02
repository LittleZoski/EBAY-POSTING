"""
Final diagnosis - try publishing one offer and capture full error
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

offer_id = "100502317011"

print("="*70)
print("Detailed Publish Attempt")
print("="*70)

# Get full offer details first
offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}"
response = requests.get(offer_url, headers=headers)

print(f"\nOffer Status: {response.status_code}")
if response.status_code == 200:
    offer = response.json()
    print(f"  Offer ID: {offer.get('offerId')}")
    print(f"  SKU: {offer.get('sku')}")
    print(f"  Status: {offer.get('status')}")
    print(f"  Has listingDescription: {bool(offer.get('listingDescription'))}")
    print(f"  Category ID: {offer.get('categoryId')}")
    print(f"  Merchant Location Key: {offer.get('merchantLocationKey')}")
    print(f"  Has all policies: {bool(offer.get('listingPolicies'))}")

# Try to publish
print(f"\nAttempting to publish offer {offer_id}...")
publish_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}/publish"
response = requests.post(publish_url, headers=headers)

print(f"Publish Status Code: {response.status_code}")
print(f"\nFull Response:")
print(json.dumps(response.json() if response.status_code != 204 else {"success": True}, indent=2))

# Also check the response headers
print(f"\nResponse Headers:")
for key, value in response.headers.items():
    if key.lower() in ['content-type', 'x-ebay-c-request-id', 'x-ebay-c-correlation-id']:
        print(f"  {key}: {value}")

print("\n" + "="*70)

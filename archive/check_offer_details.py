"""
Check detailed offer information to find what might be missing
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
print("Detailed Offer Analysis")
print("="*70)

# Get one offer to inspect
offer_id = "100502317011"  # First offer from the list
sku = "AMZN-B08KT2Z93D"

print(f"\nInspecting Offer ID: {offer_id}")
print(f"SKU: {sku}")

# Get full offer details
offer_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}"
response = requests.get(offer_url, headers=headers)

print(f"\n--- OFFER DETAILS ---")
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    offer = response.json()
    print(json.dumps(offer, indent=2))
else:
    print(f"Error: {response.text}")

# Get inventory item details
inv_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/inventory_item/{sku}"
response = requests.get(inv_url, headers=headers)

print(f"\n--- INVENTORY ITEM DETAILS ---")
print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    inventory = response.json()
    print(json.dumps(inventory, indent=2))
else:
    print(f"Error: {response.text}")

print("\n" + "="*70)

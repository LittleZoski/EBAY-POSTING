"""
Delete specific eBay offers by offer ID
"""

import sys
import codecs

# Fix Windows console encoding for Unicode
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import requests
from config import settings
from token_manager import get_token_manager
from ebay_auth import auth_manager

# Get active account and token manager
active_account = settings.active_account
token_manager = get_token_manager(active_account)

# Load tokens
if not token_manager.load_tokens():
    print(f"ERROR: No OAuth token found for account {active_account}!")
    exit(1)

headers = {
    "Authorization": f"Bearer {auth_manager.access_token}",
    "Content-Type": "application/json"
}

# Offer IDs to delete (from the error messages)
offer_ids = [
    "101526229011",
    "101526234011",
    "101526250011",
    "101526261011"
]

print("=" * 70)
print("Deleting Existing eBay Offers")
print("=" * 70)

for offer_id in offer_ids:
    print(f"\nDeleting offer {offer_id}...")

    delete_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}"
    response = requests.delete(delete_url, headers=headers)

    if response.status_code == 204:
        print(f"  ✓ Successfully deleted offer {offer_id}")
    elif response.status_code == 404:
        print(f"  ⚠ Offer {offer_id} not found (already deleted?)")
    else:
        print(f"  ✗ Failed to delete offer {offer_id}")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")

print("\n" + "=" * 70)
print("Done!")
print("=" * 70)

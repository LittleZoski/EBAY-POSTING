"""
Quick script to publish existing unpublished offers
"""

import sys
import requests
from config import settings
from token_manager import get_token_manager
from ebay_auth import auth_manager

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Get active account
active_account = settings.active_account
token_manager = get_token_manager(active_account)

# Load tokens
if not token_manager.load_tokens():
    print(f"ERROR: No OAuth token found!")
    exit(1)

headers = {
    "Authorization": f"Bearer {auth_manager.access_token}",
    "Content-Type": "application/json"
}

# Offer IDs from the error messages
offer_ids = ["100777373011", "100777379011"]

print("\n" + "="*70)
print("Publishing Existing Offers")
print(f"Active Account: Account {active_account}")
print("="*70)

for offer_id in offer_ids:
    print(f"\nPublishing offer {offer_id}...")
    publish_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}/publish"
    response = requests.post(publish_url, headers=headers)

    if response.status_code in [200, 201]:
        listing_id = response.json().get("listingId")
        print(f"  ✅ SUCCESS! Listing ID: {listing_id}")
        print(f"  View at: https://www.ebay.com/itm/{listing_id}")
    else:
        print(f"  ❌ ERROR: {response.text}")

print("\n" + "="*70)
print("\nCheck all your listings at:")
print("https://www.ebay.com/sh/lst/active")
print("="*70)

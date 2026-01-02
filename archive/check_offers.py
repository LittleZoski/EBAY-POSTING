"""
Check unpublished offers and attempt to publish them
"""
import requests
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
print("Checking Unpublished Offers")
print("="*70)

# Get all offers
url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
response = requests.get(url, headers=headers, params={'limit': 100})

print(f"\nStatus Code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    offers = data.get('offers', [])

    print(f"\nFound {len(offers)} offers")

    unpublished = [o for o in offers if o.get('status') == 'UNPUBLISHED']
    published = [o for o in offers if o.get('status') == 'PUBLISHED']

    print(f"  - Unpublished: {len(unpublished)}")
    print(f"  - Published: {len(published)}")

    if unpublished:
        print("\n" + "="*70)
        print("Unpublished Offers:")
        print("="*70)

        for offer in unpublished:
            offer_id = offer.get('offerId')
            sku = offer.get('sku')
            price = offer.get('pricingSummary', {}).get('price', {})

            print(f"\nOffer ID: {offer_id}")
            print(f"  SKU: {sku}")
            print(f"  Price: {price.get('value')} {price.get('currency')}")
            print(f"  Status: {offer.get('status')}")
            print(f"  Marketplace: {offer.get('marketplaceId')}")

        # Ask if user wants to try publishing
        print("\n" + "="*70)
        choice = input(f"\nAttempt to publish {len(unpublished)} offers individually? (y/n): ")

        if choice.lower() == 'y':
            print("\nAttempting to publish offers...")

            for offer in unpublished:
                offer_id = offer.get('offerId')
                sku = offer.get('sku')

                print(f"\nPublishing {sku} (Offer ID: {offer_id})...")

                publish_url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer/{offer_id}/publish"
                pub_response = requests.post(publish_url, headers=headers)

                if pub_response.status_code in [200, 201]:
                    listing_id = pub_response.json().get('listingId')
                    print(f"  ✅ SUCCESS! Listing ID: {listing_id}")
                    print(f"     View at: https://www.ebay.com/itm/{listing_id}")
                else:
                    print(f"  ❌ FAILED: {pub_response.status_code}")
                    print(f"     Error: {pub_response.text}")

    if published:
        print("\n" + "="*70)
        print("Published Listings:")
        print("="*70)

        for offer in published:
            listing_id = offer.get('listing', {}).get('listingId')
            sku = offer.get('sku')

            print(f"\n✅ {sku}")
            print(f"   Listing ID: {listing_id}")
            print(f"   URL: https://www.ebay.com/itm/{listing_id}")
else:
    print(f"Error: {response.text}")

print("\n" + "="*70)

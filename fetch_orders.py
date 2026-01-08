"""
Quick script to fetch eBay orders and prepare for Amazon fulfillment
Simplified wrapper around orders_flow.py
"""

import sys
from orders_flow import EbayOrderFetcher, logger
from config import settings

def main():
    """Quick fetch of unshipped orders"""
    print("\n" + "="*70)
    print("eBay Order Fetcher - Quick Mode")
    print("="*70 + "\n")

    # Use active account from settings
    account = settings.active_account
    fetcher = EbayOrderFetcher(account=account)

    # Check authentication
    if not fetcher.token_manager.load_tokens():
        print(f"❌ Authentication Required!")
        print(f"\nPlease authorize your eBay account with fulfillment scope:")
        print(f"   python authorize_account.py {account}\n")
        print("="*70 + "\n")
        sys.exit(1)

    # Fetch and export
    try:
        output_path = fetcher.fetch_and_export_orders(limit=200)

        if output_path:
            print(f"\n✅ SUCCESS!")
            print(f"\n📁 Orders exported to:")
            print(f"   {output_path}")
            print(f"\n📋 Next Steps:")
            print(f"   1. Open the JSON file to review orders")
            print(f"   2. Use web extension to populate Amazon addresses")
            print(f"   3. Place orders on Amazon")
            print(f"   4. Update eBay with tracking numbers\n")
        else:
            print(f"\nℹ️  No unshipped orders found.")
            print(f"   All caught up! 🎉\n")

        print("="*70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
        print("="*70 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

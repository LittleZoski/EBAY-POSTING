"""
Check if the current OAuth token has fulfillment API access
"""

import sys
import os
import requests
from config import settings
from token_manager import get_token_manager
from ebay_auth import auth_manager

# Fix Windows console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def check_fulfillment_access(account: int = None):
    """Test if we can access the fulfillment API"""
    account_num = account or settings.active_account
    token_manager = get_token_manager(account_num)

    print("\n" + "="*70)
    print(f"Checking eBay Fulfillment API Access - Account {account_num}")
    print("="*70 + "\n")

    # Load tokens
    if not token_manager.load_tokens():
        print("❌ No valid OAuth token found!")
        print(f"\nPlease authorize your account:")
        print(f"   python authorize_account.py {account_num}\n")
        print("="*70 + "\n")
        return False

    print("✅ OAuth token loaded")

    # Test fulfillment API access
    endpoint = f"{settings.ebay_api_base_url}/sell/fulfillment/v1/order"
    headers = {
        "Authorization": f"Bearer {auth_manager.access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    params = {
        "filter": "orderfulfillmentstatus:{NOT_STARTED|IN_PROGRESS}",
        "limit": 1  # Just test with 1 order
    }

    try:
        print("🔍 Testing Fulfillment API access...")
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            total_orders = data.get("total", 0)
            print(f"✅ Fulfillment API access confirmed!")
            print(f"\n📦 Found {total_orders} unshipped order(s)")

            if total_orders > 0:
                print("\nℹ️  You can now run:")
                print("   python fetch_orders.py")
                print("   or")
                print("   python orders_flow.py")
            else:
                print("\nℹ️  No unshipped orders at this time.")
                print("   The system is ready when orders arrive!")

            print("\n" + "="*70 + "\n")
            return True

        elif response.status_code == 401:
            print("❌ Authentication failed!")
            print("\nYour token may not have the fulfillment scope.")
            print("\nPlease re-authorize with updated scopes:")
            print(f"   python authorize_account.py {account_num}\n")
            print("="*70 + "\n")
            return False

        elif response.status_code == 403:
            print("❌ Access forbidden!")
            print("\nYour token doesn't have the 'sell.fulfillment' scope.")
            print("\nPlease re-authorize with fulfillment access:")
            print(f"   python authorize_account.py {account_num}\n")
            print("="*70 + "\n")
            return False

        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}\n")
            print("="*70 + "\n")
            return False

    except requests.exceptions.Timeout:
        print("❌ Request timeout!")
        print("\neBay API is not responding. Try again later.\n")
        print("="*70 + "\n")
        return False

    except Exception as e:
        print(f"❌ Error: {str(e)}\n")
        print("="*70 + "\n")
        return False


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check eBay Fulfillment API access"
    )
    parser.add_argument(
        "--account",
        type=int,
        default=None,
        choices=[1, 2],
        help="eBay account to check (1 or 2)"
    )

    args = parser.parse_args()
    success = check_fulfillment_access(account=args.account)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

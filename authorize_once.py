"""
One-Time Authorization Script
Run this once to authorize your eBay account and save tokens
After this, tokens will auto-refresh for 18 months!

Usage:
    python authorize_once.py           # Authorize Account 1 (default)
    python authorize_once.py 1         # Authorize Account 1
    python authorize_once.py 2         # Authorize Account 2 (wife's account)
"""

import requests
import sys
import webbrowser
from urllib.parse import urlparse, parse_qs

BASE_URL = "http://localhost:8000"

def main():
    # Check for account number argument
    account = 1
    if len(sys.argv) > 1:
        try:
            account = int(sys.argv[1])
            if account not in [1, 2]:
                print("ERROR: Account must be 1 or 2")
                sys.exit(1)
        except ValueError:
            print("ERROR: Account must be a number (1 or 2)")
            sys.exit(1)

    account_name = "Account 1 (Primary)" if account == 1 else "Account 2 (Secondary)"

    print("\n" + "="*70)
    print(" "*15 + "eBay One-Time Authorization")
    print("="*70)
    print(f"\nAuthorizing: {account_name}")
    print("\nThis script will help you authorize your eBay account ONCE.")
    print("After this, tokens will automatically refresh for 18 months!")
    print("="*70)

    print("\n⚠️  IMPORTANT - Logout from eBay First!")
    print("="*70)
    print("If you're already logged into eBay in your browser, the authorization")
    print("will use that account automatically. To authorize a different account:")
    print("\n  1. Open https://www.ebay.com in your browser")
    print("  2. Click 'Sign out' in the top right")
    print("  3. Then come back here and press Enter to continue")
    print("\nPress Enter when ready, or Ctrl+C to cancel...")
    input()

    # Step 1: Get consent URL
    print("\n[Step 1/4] Getting authorization URL...")
    try:
        response = requests.get(f"{BASE_URL}/auth/consent-url", timeout=5)
        if response.status_code != 200:
            print(f"ERROR: Error: Server returned {response.status_code}")
            print("   Make sure the server is running: python main.py")
            sys.exit(1)

        data = response.json()
        consent_url = data['consent_url']

        print("OK: Authorization URL generated")

    except Exception as e:
        print(f"ERROR: Error connecting to server: {e}")
        print("\n   Make sure the server is running:")
        print("   python main.py")
        sys.exit(1)

    # Step 2: Show URL to user
    print("\n" + "="*70)
    print("[Step 2/4] Authorize in your browser")
    print("="*70)
    print("\nOpening authorization URL in your browser...")
    print("-" * 70)
    print(consent_url)
    print("-" * 70)

    # Try to open in browser automatically
    try:
        webbrowser.open(consent_url)
        print("\n✅ Browser opened!")
    except:
        print("\n⚠️  Could not open browser automatically.")
        print("   Please copy the URL above and open it manually.")

    print("\nInstructions:")
    print(f"1. Sign in to the eBay account you want to authorize ({account_name})")
    print("2. Click 'Agree' to authorize the app")
    print("3. Copy the FULL redirect URL from your browser address bar")
    print(f"\n💡 Make sure you sign in to the CORRECT eBay account!")

    # Step 3: Get redirect URL from user
    print("\n" + "="*70)
    print("[Step 3/4] Enter the redirect URL")
    print("="*70)
    print()

    redirect_url = input("Paste the redirect URL here: ").strip()

    if not redirect_url:
        print("ERROR: No URL provided. Exiting.")
        sys.exit(1)

    # Parse the authorization code
    try:
        parsed = urlparse(redirect_url)
        params = parse_qs(parsed.query)

        if 'code' not in params:
            print(f"\nERROR: Error: No 'code' parameter found in URL")
            print(f"   URL: {redirect_url}")

            if 'error' in params:
                print(f"\n   eBay returned an error: {params['error'][0]}")
                if params['error'][0] == 'invalid_scope':
                    print("   This means one or more requested API scopes are not enabled.")
                    print("   Check your eBay app settings at: https://developer.ebay.com/my/keys")

            sys.exit(1)

        authorization_code = params['code'][0]
        print(f"\nOK: Authorization code extracted")

    except Exception as e:
        print(f"\nERROR: Error parsing URL: {e}")
        print("\n   If you just have the code (not the full URL), enter it here:")
        authorization_code = input("   Authorization code: ").strip()

        if not authorization_code:
            print("ERROR: No code provided. Exiting.")
            sys.exit(1)

    # Step 4: Exchange code for token
    print("\n" + "="*70)
    print("[Step 4/4] Exchanging code for tokens...")
    print("="*70)

    try:
        response = requests.post(
            f"{BASE_URL}/auth/callback",
            params={"authorization_code": authorization_code, "account": account},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            token_file = f"ebay_tokens_account{account}.json"

            print("\n SUCCESS!")
            print("="*70)
            print(f"OK: OAuth tokens obtained and saved for {account_name}!")
            print("="*70)

            print(f"\n Summary:")
            print(f"   - Account: {account_name}")
            print(f"   - Access token: Valid for 2 hours")
            print(f"   - Refresh token: Valid for 18 months")
            print(f"   - Auto-refresh: Enabled")

            print(f"\n What happens next:")
            print(f"   - Tokens saved to: {token_file}")
            print(f"   - Server will auto-load tokens on startup")
            print(f"   - Tokens will auto-refresh before expiration")
            print(f"   - You won't need to re-authorize for 18 months!")

            if account == 2:
                print(f"\n📝 Next Steps for Account 2:")
                print(f"   1. Get your wife's business policy IDs from eBay")
                print(f"   2. Add them to .env file:")
                print(f"      PAYMENT_POLICY_ID_ACCOUNT2=...")
                print(f"      RETURN_POLICY_ID_ACCOUNT2=...")
                print(f"      FULFILLMENT_POLICY_ID_ACCOUNT2=...")
                print(f"   3. Set ACTIVE_ACCOUNT=2 in .env to use this account")

            print(f"\n You're ready to go!")
            print(f"   The app can now process Amazon products → eBay listings")

            print("\n" + "="*70)

        else:
            print(f"\nERROR: Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   {error_data.get('detail', response.text)}")
            except:
                print(f"   {response.text}")

            print("\n Common issues:")
            print("   - Authorization code expired (valid for ~5 minutes)")
            print("   - Code was already used")
            print("   - Wrong code copied")
            print("\n   Solution: Get a new code by starting over")

            sys.exit(1)

    except Exception as e:
        print(f"\nERROR: Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Cancelled by user")
        sys.exit(0)

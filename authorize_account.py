"""
eBay Account Authorization Script (Multi-Account Support)
Run this to authorize your eBay accounts and save tokens

Usage:
    python authorize_account.py           # Authorize Account 1 (default)
    python authorize_account.py 1         # Authorize Account 1
    python authorize_account.py 2         # Authorize Account 2 (wife's account)
"""

import sys
import webbrowser
from urllib.parse import urlparse, parse_qs
from ebay_auth import auth_manager
from token_manager import get_token_manager

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
    token_file = f"ebay_tokens_account{account}.json"

    print("\n" + "="*70)
    print(" "*15 + "eBay Account Authorization")
    print("="*70)
    print(f"\nAuthorizing: {account_name}")
    print("\nThis script will help you authorize your eBay account.")
    print("After this, tokens will automatically refresh for 18 months!")
    print("="*70)

    print("\n⚠️  IMPORTANT - Make Sure You're Logged Out First!")
    print("="*70)
    print("If you're already logged into eBay in your browser, the authorization")
    print("will use that account automatically. To authorize a different account:")
    print("\n  1. Open https://www.ebay.com in your browser")
    print("  2. Click 'Sign out' in the top right")
    print("  3. Close all eBay browser tabs")
    print("  4. Then come back here and press Enter to continue")
    print("\nPress Enter when ready, or Ctrl+C to cancel...")
    input()

    # Step 1: Get consent URL
    print("\n[Step 1/3] Generating authorization URL...")
    print("="*70)

    try:
        consent_url = auth_manager.get_consent_url()
        print("✅ Authorization URL generated")
    except Exception as e:
        print(f"ERROR: Failed to generate consent URL: {e}")
        sys.exit(1)

    # Step 2: Open browser and get authorization code
    print("\n[Step 2/3] Opening browser for authorization...")
    print("="*70)
    print("\nURL:")
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
    print("3. You'll be redirected to a page (may show an error - that's OK!)")
    print("4. Copy the FULL URL from your browser address bar")
    print(f"\n💡 Make sure you sign in to the CORRECT eBay account!")

    # Step 3: Get authorization code from redirect URL
    print("\n[Step 3/3] Enter the redirect URL")
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
            print(f"\nERROR: No 'code' parameter found in URL")
            print(f"   URL: {redirect_url}")

            if 'error' in params:
                print(f"\n   eBay returned an error: {params['error'][0]}")
                if params['error'][0] == 'invalid_scope':
                    print("   This means one or more requested API scopes are not enabled.")
                    print("   Check your eBay app settings at: https://developer.ebay.com/my/keys")

            sys.exit(1)

        authorization_code = params['code'][0]
        print(f"\n✅ Authorization code extracted")

    except Exception as e:
        print(f"\nERROR: Error parsing URL: {e}")
        print("\n   If you just have the code (not the full URL), enter it here:")
        authorization_code = input("   Authorization code: ").strip()

        if not authorization_code:
            print("ERROR: No code provided. Exiting.")
            sys.exit(1)

    # Exchange code for token
    print("\n" + "="*70)
    print("Exchanging authorization code for tokens...")
    print("="*70)

    try:
        # Get the token
        auth_manager.get_user_token(authorization_code)

        # Save to the appropriate account file
        tm = get_token_manager(account)
        tm.save_tokens()

        print("\n✨ SUCCESS!")
        print("="*70)
        print(f"✅ OAuth tokens obtained and saved for {account_name}!")
        print("="*70)

        print(f"\n📋 Summary:")
        print(f"   - Account: {account_name}")
        print(f"   - Tokens saved to: {token_file}")
        print(f"   - Access token: Valid for 2 hours")
        print(f"   - Refresh token: Valid for 18 months")
        print(f"   - Auto-refresh: Enabled ✓")

        if account == 2:
            print(f"\n📝 Next Steps for Account 2:")
            print(f"   1. Get your wife's eBay business policy IDs")
            print(f"   2. Add them to your .env file:")
            print(f"      PAYMENT_POLICY_ID_ACCOUNT2=<her_payment_policy_id>")
            print(f"      RETURN_POLICY_ID_ACCOUNT2=<her_return_policy_id>")
            print(f"      FULFILLMENT_POLICY_ID_ACCOUNT2=<her_fulfillment_policy_id>")
            print(f"   3. To use Account 2, set ACTIVE_ACCOUNT=2 in .env")
        else:
            print(f"\n✅ You're all set!")
            print(f"   Your app is now authorized and ready to create eBay listings")

        print("\n" + "="*70)

    except Exception as e:
        print(f"\n❌ ERROR: Failed to exchange authorization code")
        print(f"   {str(e)}")
        print("\n💡 Common issues:")
        print("   - Authorization code expired (valid for ~5 minutes)")
        print("   - Code was already used")
        print("   - Wrong code copied")
        print("\n   Solution: Run this script again to get a new code")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(0)

"""
One-Time Authorization Script
Run this once to authorize your eBay account and save tokens
After this, tokens will auto-refresh for 18 months!
"""

import requests
import sys
from urllib.parse import urlparse, parse_qs

BASE_URL = "http://localhost:8000"

def main():
    print("\n" + "="*70)
    print(" "*15 + "eBay One-Time Authorization")
    print("="*70)
    print("\nThis script will help you authorize your eBay account ONCE.")
    print("After this, tokens will automatically refresh for 18 months!")
    print("="*70)

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
    print("\n Copy this URL and open it in your browser:")
    print("-" * 70)
    print(consent_url)
    print("-" * 70)
    print("\nInstructions:")
    print("1. Open the URL above in your browser")
    print("2. Sign in to your eBay account")
    print("3. Click 'Agree' to authorize the app")
    print("4. Copy the FULL redirect URL from your browser address bar")

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
            params={"authorization_code": authorization_code},
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()

            print("\n SUCCESS!")
            print("="*70)
            print("OK: OAuth tokens obtained and saved to disk!")
            print("="*70)

            print(f"\n Summary:")
            print(f"   - Access token: Valid for 2 hours")
            print(f"   - Refresh token: Valid for 18 months")
            print(f"   - Auto-refresh: Enabled")

            print(f"\n What happens next:")
            print(f"   - Tokens are saved to: ebay_tokens.json")
            print(f"   - Server will auto-load tokens on startup")
            print(f"   - Tokens will auto-refresh before expiration")
            print(f"   - You won't need to re-authorize for 18 months!")

            print(f"\n You're ready to go!")
            print(f"   The app can now process Amazon products  eBay listings")

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

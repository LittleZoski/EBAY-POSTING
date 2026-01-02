"""
eBay OAuth 2.0 Authentication Module
Following eBay's official OAuth implementation:
https://developer.ebay.com/api-docs/static/oauth-tokens.html
"""

import base64
import requests
import time
from typing import Optional
from config import settings


class EbayAuthManager:
    """Manages eBay OAuth 2.0 authentication and token refresh"""

    def __init__(self):
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[float] = None
        self.refresh_token: Optional[str] = None

    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        eBay access tokens expire after 2 hours.
        """
        if self.access_token and self.token_expiry:
            # Check if token is still valid (with 5 minute buffer)
            if time.time() < (self.token_expiry - 300):
                return self.access_token

        # Token expired or doesn't exist, get new one
        return self._request_new_token()

    def _request_new_token(self) -> str:
        """
        Request new OAuth token using Application credentials.
        For production, you'll need User Token flow for selling APIs.

        eBay OAuth Flow:
        1. Application Token (for read-only APIs)
        2. User Token (for selling/trading APIs) - requires user consent
        """
        # Create base64 encoded credentials
        credentials = f"{settings.ebay_app_id}:{settings.ebay_cert_id}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }

        # For selling APIs, use authorization_code grant type with user token
        # For now, using client_credentials (limited functionality)
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory"
        }

        try:
            response = requests.post(
                settings.ebay_auth_url,
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            # eBay returns expiry in seconds
            self.token_expiry = time.time() + token_data["expires_in"]

            return self.access_token

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to obtain eBay access token: {str(e)}")

    def get_user_token(self, authorization_code: str) -> str:
        """
        Exchange authorization code for user access token.

        This is required for Inventory API (creating listings).
        Flow:
        1. Direct user to consent URL
        2. User authorizes app
        3. eBay redirects with authorization code
        4. Exchange code for access token

        For production use, implement proper OAuth flow:
        https://developer.ebay.com/api-docs/static/oauth-authorization-code-grant.html
        """
        credentials = f"{settings.ebay_app_id}:{settings.ebay_cert_id}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }

        data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": settings.ebay_redirect_uri
        }

        try:
            response = requests.post(
                settings.ebay_auth_url,
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.refresh_token = token_data.get("refresh_token")
            self.token_expiry = time.time() + token_data["expires_in"]

            return self.access_token

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to exchange authorization code: {str(e)}")

    def refresh_user_token(self) -> str:
        """
        Refresh user access token using refresh token.
        User tokens can be refreshed for up to 18 months.
        """
        if not self.refresh_token:
            raise Exception("No refresh token available")

        credentials = f"{settings.ebay_app_id}:{settings.ebay_cert_id}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": "https://api.ebay.com/oauth/api_scope/sell.inventory"
        }

        try:
            response = requests.post(
                settings.ebay_auth_url,
                headers=headers,
                data=data,
                timeout=10
            )
            response.raise_for_status()

            token_data = response.json()
            self.access_token = token_data["access_token"]
            self.token_expiry = time.time() + token_data["expires_in"]

            return self.access_token

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to refresh token: {str(e)}")

    def get_consent_url(self, state: str = "state") -> str:
        """
        Generate eBay user consent URL.
        Direct users to this URL to authorize your app.

        Scopes for Inventory API:
        - https://api.ebay.com/oauth/api_scope/sell.inventory
        - https://api.ebay.com/oauth/api_scope/sell.inventory.readonly
        """
        if settings.ebay_environment.upper() == "PRODUCTION":
            base_url = "https://auth.ebay.com/oauth2/authorize"
        else:
            base_url = "https://auth.sandbox.ebay.com/oauth2/authorize"

        # Request all necessary scopes for listing creation
        scopes = [
            "https://api.ebay.com/oauth/api_scope/sell.inventory",
            "https://api.ebay.com/oauth/api_scope/sell.account",  # For business policies
            "https://api.ebay.com/oauth/api_scope/sell.marketing.readonly"  # For offers
        ]

        consent_url = (
            f"{base_url}"
            f"?client_id={settings.ebay_app_id}"
            f"&redirect_uri={settings.ebay_redirect_uri}"
            f"&response_type=code"
            f"&state={state}"
            f"&scope={' '.join(scopes)}"
        )

        return consent_url


# Global auth manager instance
auth_manager = EbayAuthManager()

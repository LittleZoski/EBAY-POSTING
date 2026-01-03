"""
Token persistence and automatic refresh management
This handles saving tokens to disk and auto-refreshing them
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional, Dict
from ebay_auth import auth_manager

logger = logging.getLogger(__name__)

TOKEN_FILE = Path("ebay_tokens.json")
TOKEN_FILE_ACCOUNT1 = Path("ebay_tokens_account1.json")
TOKEN_FILE_ACCOUNT2 = Path("ebay_tokens_account2.json")


class TokenManager:
    """Manages token persistence and automatic refresh"""

    def __init__(self, account: int = 1):
        """Initialize token manager for a specific account"""
        self.account = account
        self.token_file = TOKEN_FILE_ACCOUNT1 if account == 1 else TOKEN_FILE_ACCOUNT2

    def load_tokens(self, account: int = None) -> bool:
        """
        Load tokens from disk if they exist.
        Returns True if valid tokens were loaded, False otherwise.
        """
        if account:
            self.account = account
            self.token_file = TOKEN_FILE_ACCOUNT1 if account == 1 else TOKEN_FILE_ACCOUNT2

        if not self.token_file.exists():
            logger.info(f"No saved tokens found for account {self.account}")
            return False

        try:
            with open(self.token_file, 'r') as f:
                data = json.load(f)

            # Restore tokens to auth_manager
            auth_manager.access_token = data.get('access_token')
            auth_manager.refresh_token = data.get('refresh_token')
            auth_manager.token_expiry = data.get('token_expiry')

            # Check if access token is still valid
            if auth_manager.token_expiry and time.time() < (auth_manager.token_expiry - 300):
                logger.info(f"✅ Loaded valid access token from disk for account {self.account}")
                return True

            # Access token expired, try to refresh it
            if auth_manager.refresh_token:
                logger.info("Access token expired, refreshing...")
                try:
                    auth_manager.refresh_user_token()
                    self.save_tokens()
                    logger.info("✅ Successfully refreshed access token")
                    return True
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    return False

            logger.warning("No valid tokens available")
            return False

        except Exception as e:
            logger.error(f"Error loading tokens: {e}")
            return False

    def save_tokens(self) -> bool:
        """
        Save current tokens to disk.
        Returns True if successful, False otherwise.
        """
        try:
            data = {
                'access_token': auth_manager.access_token,
                'refresh_token': auth_manager.refresh_token,
                'token_expiry': auth_manager.token_expiry,
                'saved_at': time.time()
            }

            with open(self.token_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"✅ Tokens saved to disk for account {self.account}")
            return True

        except Exception as e:
            logger.error(f"Error saving tokens: {e}")
            return False

    def is_authenticated(self) -> bool:
        """
        Check if we have valid authentication.
        Automatically refreshes if needed.
        """
        # No access token at all
        if not auth_manager.access_token:
            return False

        # Token is still valid
        if auth_manager.token_expiry and time.time() < (auth_manager.token_expiry - 300):
            return True

        # Token expired, try to refresh
        if auth_manager.refresh_token:
            try:
                logger.info("Token expired, auto-refreshing...")
                auth_manager.refresh_user_token()
                self.save_tokens()
                logger.info("✅ Token auto-refreshed successfully")
                return True
            except Exception as e:
                logger.error(f"Auto-refresh failed: {e}")
                return False

        return False

    def get_auth_status(self) -> Dict:
        """Get current authentication status"""
        if not auth_manager.access_token:
            return {
                "authenticated": False,
                "message": "No OAuth token available",
                "action_required": "Please authorize the app at /auth/consent-url"
            }

        if auth_manager.token_expiry:
            remaining = int(auth_manager.token_expiry - time.time())
            if remaining > 0:
                return {
                    "authenticated": True,
                    "expires_in_seconds": remaining,
                    "expires_in_hours": round(remaining / 3600, 2),
                    "has_refresh_token": bool(auth_manager.refresh_token),
                    "message": "Authenticated and ready"
                }

        return {
            "authenticated": False,
            "message": "Token expired and cannot be refreshed",
            "action_required": "Please re-authorize at /auth/consent-url"
        }


# Global token manager instances
token_manager = TokenManager(account=1)  # Default to account 1
token_manager_account2 = TokenManager(account=2)

def get_token_manager(account: int = 1) -> TokenManager:
    """Get the token manager for the specified account"""
    return token_manager if account == 1 else token_manager_account2

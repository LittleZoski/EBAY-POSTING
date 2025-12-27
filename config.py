from pydantic_settings import BaseSettings
from pathlib import Path
import sys
import os


class Settings(BaseSettings):
    # eBay API Credentials
    ebay_app_id: str
    ebay_cert_id: str
    ebay_dev_id: str
    ebay_redirect_uri: str = "YourRedirectURI"
    ebay_user_token: str = ""
    ebay_environment: str = "SANDBOX"

    # Folder Settings
    watch_folder: Path = Path("c:/Users/31243/Downloads")
    processed_folder: Path = Path("c:/Users/31243/ebay-listing-app/processed")
    failed_folder: Path = Path("c:/Users/31243/ebay-listing-app/failed")

    # Pricing Settings
    price_markup_percentage: float = 20.0
    fixed_markup_amount: float = 5.00

    # eBay Settings
    ebay_site_id: int = 0  # 0=US, 3=UK, 2=Canada

    # Batch Settings
    max_items_per_batch: int = 25
    processing_delay_seconds: int = 2

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def ebay_api_base_url(self) -> str:
        """Return correct eBay API base URL based on environment"""
        if self.ebay_environment.upper() == "PRODUCTION":
            return "https://api.ebay.com"
        return "https://api.sandbox.ebay.com"

    @property
    def ebay_auth_url(self) -> str:
        """Return correct eBay Auth URL based on environment"""
        if self.ebay_environment.upper() == "PRODUCTION":
            return "https://api.ebay.com/identity/v1/oauth2/token"
        return "https://api.sandbox.ebay.com/identity/v1/oauth2/token"


# Initialize settings with helpful error message if .env is missing
try:
    settings = Settings()
except Exception as e:
    print("\n" + "="*70)
    print("❌ ERROR: Configuration file missing or invalid!")
    print("="*70)
    print("\nThe application requires a .env file with your eBay API credentials.")
    print("\n📋 Quick Setup:")
    print("   1. Copy .env.example to .env")
    print("   2. Edit .env with your eBay API keys")
    print("   3. See QUICK_TEST_SETUP.md for detailed instructions")
    print("\n💡 Command to create .env:")
    print("   copy .env.example .env")
    print("\n" + "="*70)
    print(f"\nOriginal error: {str(e)}")
    print("="*70 + "\n")
    sys.exit(1)

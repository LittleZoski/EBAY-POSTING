"""
Simple script to list all offers
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

print("Fetching all offers...")

# Get all offers without any query params
url = f"{settings.ebay_api_base_url}/sell/inventory/v1/offer"
response = requests.get(url, headers=headers)

print(f"Status Code: {response.status_code}\n")
print("Response:")
print(response.text)

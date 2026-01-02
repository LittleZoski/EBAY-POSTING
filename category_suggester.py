"""
eBay Category Suggestion Helper using Taxonomy API
Dynamically suggests categories based on product title and description
"""
import requests
from typing import Dict, List, Optional
from config import settings
import logging

logger = logging.getLogger(__name__)


class CategorySuggester:
    """
    Uses eBay's Taxonomy API to suggest categories based on product information.

    IMPORTANT: Requires application token with scope https://api.ebay.com/oauth/api_scope
    This is different from user tokens - uses client credentials grant flow.
    """

    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize with OAuth credentials for application token.

        Args:
            client_id: eBay App ID (Client ID)
            client_secret: eBay Cert ID (Client Secret)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.app_token = None
        self.token_expires_at = 0

    def get_application_token(self) -> str:
        """
        Get application-level OAuth token using client credentials grant flow.

        Returns:
            Access token for Taxonomy API calls
        """
        import time
        import base64

        # Check if we have a valid cached token
        if self.app_token and time.time() < self.token_expires_at:
            return self.app_token

        # Request new application token
        logger.info("Requesting new eBay application token...")

        # Encode credentials
        credentials = f"{self.client_id}:{self.client_secret}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {b64_credentials}"
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }

        # Use production or sandbox based on environment
        if settings.ebay_environment == "PRODUCTION":
            token_url = "https://api.ebay.com/identity/v1/oauth2/token"
        else:
            token_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"

        response = requests.post(token_url, headers=headers, data=data, timeout=30)

        if response.status_code == 200:
            token_data = response.json()
            self.app_token = token_data["access_token"]
            # Set expiration (typically 7200 seconds = 2 hours)
            # Refresh 5 minutes before actual expiration
            expires_in = token_data.get("expires_in", 7200)
            self.token_expires_at = time.time() + expires_in - 300

            logger.info("Successfully obtained application token")
            return self.app_token
        else:
            raise Exception(f"Failed to get application token: {response.status_code} - {response.text}")

    def get_category_suggestions(
        self,
        product_title: str,
        product_description: str = "",
        max_suggestions: int = 3
    ) -> List[Dict]:
        """
        Get category suggestions from eBay based on product info.

        Args:
            product_title: The product title
            product_description: Optional product description for better matching
            max_suggestions: Maximum number of suggestions to return (default 3)

        Returns:
            List of suggested categories with their IDs and names
            Example: [
                {
                    "categoryId": "179852",
                    "categoryName": "Car & Truck Wiper Blades & Refills",
                    "categoryPath": "eBay Motors > Parts & Accessories > ...",
                    "confidence": "high"
                }
            ]
        """
        # Build search query from title and description
        query = product_title
        if product_description:
            # Add first 100 chars of description for better context
            query += " " + product_description[:100]

        # Get application token
        token = self.get_application_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Accept-Language": "en-US"
        }

        # Get default category tree ID (0 = EBAY_US)
        category_tree_id = "0"  # EBAY_US

        # Call getCategorySuggestions API
        url = f"{settings.ebay_api_base_url}/commerce/taxonomy/v1/category_tree/{category_tree_id}/get_category_suggestions"

        params = {
            "q": query
        }

        logger.info(f"Getting category suggestions for: {product_title[:50]}...")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                suggestions = data.get("categorySuggestions", [])

                # Parse and format suggestions
                results = []
                for suggestion in suggestions[:max_suggestions]:
                    category = suggestion.get("category", {})
                    ancestors = suggestion.get("categoryTreeNodeAncestors", [])

                    # Build category path from ancestors
                    path_parts = [ancestor.get("categoryName", "") for ancestor in ancestors]
                    path_parts.append(category.get("categoryName", ""))
                    category_path = " > ".join(path_parts)

                    results.append({
                        "categoryId": category.get("categoryId"),
                        "categoryName": category.get("categoryName"),
                        "categoryPath": category_path,
                        "confidence": "high" if len(results) == 0 else "medium" if len(results) == 1 else "low"
                    })

                if results:
                    logger.info(f"  Found {len(results)} category suggestions")
                    logger.info(f"  Top suggestion: {results[0]['categoryName']} (ID: {results[0]['categoryId']})")
                else:
                    logger.warning("  No category suggestions returned by eBay")

                return results

            elif response.status_code == 204:
                # No suggestions found
                logger.warning("No category suggestions found for this product")
                return []

            else:
                logger.error(f"Category suggestion API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Exception calling category suggestion API: {str(e)}")
            return []

    def get_best_category(
        self,
        product_title: str,
        product_description: str = "",
        fallback_category_id: str = "220"  # Collectibles (safe default)
    ) -> str:
        """
        Get the best (most confident) category ID for a product.

        Args:
            product_title: The product title
            product_description: Optional product description
            fallback_category_id: Category to use if no suggestions found

        Returns:
            Category ID string (e.g., "179852")
        """
        suggestions = self.get_category_suggestions(product_title, product_description, max_suggestions=1)

        if suggestions and suggestions[0].get("categoryId"):
            return suggestions[0]["categoryId"]

        logger.warning(f"No category suggestions found, using fallback: {fallback_category_id}")
        return fallback_category_id


# Example usage
if __name__ == "__main__":
    import sys

    # Test with credentials from environment
    try:
        suggester = CategorySuggester(
            client_id=settings.ebay_app_id,
            client_secret=settings.ebay_cert_id
        )

        # Test with windshield wiper
        test_title = "Rain-X Latitude 2-In-1 Wiper Blades 26 Inch Windshield Wipers"
        test_desc = "Patented water repellent formula for automotive windshield"

        print(f"Testing category suggestions for: {test_title}\n")

        suggestions = suggester.get_category_suggestions(test_title, test_desc)

        print(f"Found {len(suggestions)} suggestions:\n")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion['categoryName']}")
            print(f"   ID: {suggestion['categoryId']}")
            print(f"   Path: {suggestion['categoryPath']}")
            print(f"   Confidence: {suggestion['confidence']}\n")

        # Test get_best_category
        best_id = suggester.get_best_category(test_title, test_desc)
        print(f"Best category ID: {best_id}")

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

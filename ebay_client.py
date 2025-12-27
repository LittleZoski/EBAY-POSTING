"""
eBay Inventory API Client
Following official documentation:
https://developer.ebay.com/api-docs/sell/inventory/overview.html
https://developer.ebay.com/api-docs/sell/inventory/resources/inventory_item/methods/bulkCreateOrReplaceInventoryItem
"""

import requests
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ebay_auth import auth_manager
from config import settings


class InventoryItem(BaseModel):
    """eBay Inventory Item structure"""
    sku: str
    product: Dict[str, Any]
    condition: str = "NEW"
    conditionDescription: Optional[str] = None
    availability: Dict[str, Any]
    packageWeightAndSize: Optional[Dict[str, Any]] = None


class Offer(BaseModel):
    """eBay Offer structure"""
    sku: str
    marketplaceId: str = "EBAY_US"
    format: str = "FIXED_PRICE"
    listingDescription: str
    listingPolicies: Dict[str, Any]
    pricingSummary: Dict[str, Any]
    quantityLimitPerBuyer: int = 10
    categoryId: str
    merchantLocationKey: Optional[str] = None
    tax: Optional[Dict[str, Any]] = None


class EbayClient:
    """Client for interacting with eBay Inventory API"""

    def __init__(self):
        self.base_url = settings.ebay_api_base_url
        self.auth_manager = auth_manager

    def _get_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        token = self.auth_manager.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def create_or_replace_inventory_item(
        self,
        sku: str,
        inventory_item: InventoryItem
    ) -> Dict[str, Any]:
        """
        Create or replace a single inventory item.
        PUT /sell/inventory/v1/inventory_item/{sku}

        Returns: Location header with inventory item URI
        """
        url = f"{self.base_url}/sell/inventory/v1/inventory_item/{sku}"

        try:
            response = requests.put(
                url,
                headers=self._get_headers(),
                json=inventory_item.model_dump(exclude_none=True),
                timeout=30
            )

            # eBay returns 204 No Content on success for PUT
            if response.status_code == 204:
                return {
                    "success": True,
                    "sku": sku,
                    "message": "Inventory item created/updated successfully"
                }

            # Handle errors
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "sku": sku,
                "error": str(e),
                "response": response.text if 'response' in locals() else None
            }

    def bulk_create_or_replace_inventory_item(
        self,
        inventory_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create or replace up to 25 inventory items in bulk.
        POST /sell/inventory/v1/bulk_create_or_replace_inventory_item

        eBay API Limit: Maximum 25 items per request

        Request format:
        {
            "requests": [
                {
                    "sku": "SKU123",
                    "product": {...},
                    "condition": "NEW",
                    "availability": {...}
                }
            ]
        }

        Returns: Array of responses with success/failure for each item
        """
        url = f"{self.base_url}/sell/inventory/v1/bulk_create_or_replace_inventory_item"

        # Ensure we don't exceed eBay's limit
        if len(inventory_items) > settings.max_items_per_batch:
            raise ValueError(
                f"Cannot process more than {settings.max_items_per_batch} items. "
                f"Got {len(inventory_items)} items."
            )

        payload = {"requests": inventory_items}

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "response": response.text if 'response' in locals() else None
            }

    def create_offer(self, offer: Offer) -> Dict[str, Any]:
        """
        Create an offer for an inventory item.
        POST /sell/inventory/v1/offer

        Returns: offerId and offer details
        """
        url = f"{self.base_url}/sell/inventory/v1/offer"

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=offer.model_dump(exclude_none=True),
                timeout=30
            )
            response.raise_for_status()

            return {
                "success": True,
                "data": response.json()
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "response": response.text if 'response' in locals() else None
            }

    def bulk_create_offer(self, offers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create up to 25 offers in bulk.
        POST /sell/inventory/v1/bulk_create_offer

        Important: Provide all necessary details upfront as there's no bulk update!

        Returns: Array of responses with offerId or errors
        """
        url = f"{self.base_url}/sell/inventory/v1/bulk_create_offer"

        if len(offers) > settings.max_items_per_batch:
            raise ValueError(
                f"Cannot process more than {settings.max_items_per_batch} offers. "
                f"Got {len(offers)} offers."
            )

        payload = {"requests": offers}

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "response": response.text if 'response' in locals() else None
            }

    def publish_offer(self, offer_id: str) -> Dict[str, Any]:
        """
        Publish an offer to create an active listing.
        POST /sell/inventory/v1/offer/{offerId}/publish

        This converts the staged offer into a live eBay listing.
        """
        url = f"{self.base_url}/sell/inventory/v1/offer/{offer_id}/publish"

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            return {
                "success": True,
                "data": response.json()
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "response": response.text if 'response' in locals() else None
            }

    def bulk_publish_offer(self, offer_ids: List[str]) -> Dict[str, Any]:
        """
        Publish multiple offers at once.
        POST /sell/inventory/v1/bulk_publish_offer

        Maximum 25 offers per request.
        """
        url = f"{self.base_url}/sell/inventory/v1/bulk_publish_offer"

        payload = {
            "requests": [
                {"offerId": offer_id} for offer_id in offer_ids
            ]
        }

        try:
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "response": response.text if 'response' in locals() else None
            }

    def get_inventory_item(self, sku: str) -> Dict[str, Any]:
        """
        Retrieve an inventory item by SKU.
        GET /sell/inventory/v1/inventory_item/{sku}
        """
        url = f"{self.base_url}/sell/inventory/v1/inventory_item/{sku}"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()

            return {
                "success": True,
                "data": response.json()
            }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e),
                "response": response.text if 'response' in locals() else None
            }


# Global client instance
ebay_client = EbayClient()

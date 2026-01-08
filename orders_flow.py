"""
eBay Order Fulfillment Flow
Fetches unshipped orders from eBay and prepares them for Amazon order placement
"""

import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import settings
from token_manager import get_token_manager
from ebay_auth import auth_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EbayOrderFetcher:
    """Fetches and processes unshipped orders from eBay"""

    def __init__(self, account: int = None):
        """Initialize order fetcher for specific account"""
        self.account = account or settings.active_account
        self.token_manager = get_token_manager(self.account)
        self.base_url = settings.ebay_api_base_url
        self.output_folder = Path("ebay_orders")
        self.output_folder.mkdir(exist_ok=True)

    def _get_headers(self) -> Dict[str, str]:
        """Get API request headers with OAuth token"""
        # Ensure token is valid and refreshed if needed
        if not self.token_manager.is_authenticated():
            self.token_manager.load_tokens(self.account)

        return {
            "Authorization": f"Bearer {auth_manager.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_unshipped_orders(
        self,
        limit: int = 50,
        offset: int = 0,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        Fetch orders that have not been fully shipped from eBay.

        Uses eBay Fulfillment API: getOrders
        https://developer.ebay.com/api-docs/sell/fulfillment/resources/order/methods/getOrders

        Args:
            limit: Number of orders to fetch per request (max 200)
            offset: Pagination offset
            days_back: How many days back to search (max 90)

        Returns:
            Dict containing orders and metadata
        """
        endpoint = f"{self.base_url}/sell/fulfillment/v1/order"

        # Filter for orders that are NOT_STARTED or IN_PROGRESS
        # NOT_STARTED: No shipping fulfillments started
        # IN_PROGRESS: At least one item shipped but not all
        params = {
            "filter": "orderfulfillmentstatus:{NOT_STARTED|IN_PROGRESS}",
            "limit": min(limit, 200),  # eBay max is 200
            "offset": offset
        }

        try:
            logger.info(f"Fetching unshipped orders from eBay (Account {self.account})...")
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                params=params,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            orders = data.get("orders", [])
            total = data.get("total", 0)

            logger.info(f"✅ Found {len(orders)} unshipped orders (Total: {total})")
            return data

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("❌ Authentication failed. Please re-authorize the app.")
                logger.error(f"   Run: python authorize_account.py {self.account}")
            else:
                logger.error(f"❌ API Error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to fetch orders: {str(e)}")
            raise

    def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """
        Fetch detailed information for a specific order.

        Args:
            order_id: eBay order ID

        Returns:
            Dict containing full order details
        """
        endpoint = f"{self.base_url}/sell/fulfillment/v1/order/{order_id}"

        try:
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"❌ Failed to fetch order {order_id}: {str(e)}")
            raise

    def extract_shipping_info(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract shipping information from eBay order for Amazon address creation.

        Args:
            order: eBay order object

        Returns:
            Dict containing formatted shipping information
        """
        # Extract buyer information
        buyer = order.get("buyer", {})
        buyer_reg_address = buyer.get("buyerRegistrationAddress", {})
        contact_address = buyer_reg_address.get("contactAddress", {})

        # Extract shipping address from fulfillmentStartInstructions
        # This contains the actual ship-to address (may differ from buyer registration)
        fulfillment_instructions = order.get("fulfillmentStartInstructions", [])
        shipping_address = {}

        if fulfillment_instructions:
            # Get first fulfillment instruction (most orders have one)
            first_instruction = fulfillment_instructions[0]
            shipping_step = first_instruction.get("shippingStep", {})
            ship_to = shipping_step.get("shipTo", {})
            shipping_address = ship_to.get("contactAddress", {})
            full_name = ship_to.get("fullName", "")
            primary_phone = ship_to.get("primaryPhone", {}).get("phoneNumber", "")
            email = ship_to.get("email", buyer.get("email", ""))
        else:
            # Fallback to buyer registration address
            shipping_address = contact_address
            full_name = buyer_reg_address.get("fullName", "")
            primary_phone = buyer_reg_address.get("primaryPhone", {}).get("phoneNumber", "")
            email = buyer.get("email", "")

        # Format shipping info for Amazon
        shipping_info = {
            "name": full_name,
            "addressLine1": shipping_address.get("addressLine1", ""),
            "addressLine2": shipping_address.get("addressLine2", ""),
            "city": shipping_address.get("city", ""),
            "stateOrProvince": shipping_address.get("stateOrProvince", ""),
            "postalCode": shipping_address.get("postalCode", ""),
            "countryCode": shipping_address.get("countryCode", "US"),
            "phoneNumber": primary_phone,
            "email": email
        }

        return shipping_info

    def extract_line_items(self, order: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract line items (products) from eBay order.

        Args:
            order: eBay order object

        Returns:
            List of line items with product details
        """
        line_items = order.get("lineItems", [])
        extracted_items = []

        for item in line_items:
            # Extract SKU (which is the ASIN in our mapping)
            sku = item.get("sku", "")
            line_item_id = item.get("lineItemId", "")
            title = item.get("title", "")
            quantity = item.get("quantity", 1)

            # Extract pricing
            line_item_cost = item.get("lineItemCost", {})
            value = line_item_cost.get("value", "0.00")
            currency = line_item_cost.get("currency", "USD")

            extracted_items.append({
                "lineItemId": line_item_id,
                "sku": sku,  # This is the Amazon ASIN
                "asin": sku,  # Convenience field
                "title": title,
                "quantity": quantity,
                "price": float(value),
                "currency": currency
            })

        return extracted_items

    def map_order_to_amazon_format(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map eBay order to Amazon-ready format for order placement.

        Args:
            order: eBay order object

        Returns:
            Dict containing order data ready for Amazon placement
        """
        order_id = order.get("orderId", "")
        order_date = order.get("creationDate", "")
        order_status = order.get("orderFulfillmentStatus", "")

        # Extract shipping information
        shipping_info = self.extract_shipping_info(order)

        # Extract line items (products to order from Amazon)
        line_items = self.extract_line_items(order)

        # Extract payment summary for reference
        payment_summary = order.get("paymentSummary", {})
        total_paid = payment_summary.get("totalDueSeller", {})

        mapped_order = {
            "ebayOrderId": order_id,
            "ebayOrderDate": order_date,
            "ebayOrderStatus": order_status,
            "totalPaidByBuyer": {
                "amount": total_paid.get("value", "0.00"),
                "currency": total_paid.get("currency", "USD")
            },
            "shippingAddress": shipping_info,
            "items": line_items,
            "orderNote": f"eBay Order {order_id} - Ship to buyer address above",
            "processedAt": datetime.utcnow().isoformat() + "Z"
        }

        return mapped_order

    def fetch_and_export_orders(
        self,
        limit: int = 50,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Fetch all unshipped orders and export to JSON file.

        Args:
            limit: Max orders per API call (will paginate if needed)
            output_filename: Custom output filename (optional)

        Returns:
            Path to the exported JSON file
        """
        logger.info("\n" + "="*70)
        logger.info(f"eBay Order Fulfillment Flow - Account {self.account}")
        logger.info("="*70)

        # Fetch orders (with pagination if needed)
        all_orders = []
        offset = 0
        has_more = True

        while has_more:
            logger.info(f"\nFetching orders (offset: {offset})...")
            response = self.get_unshipped_orders(limit=limit, offset=offset)

            orders = response.get("orders", [])
            total = response.get("total", 0)

            all_orders.extend(orders)

            # Check if there are more orders to fetch
            offset += len(orders)
            has_more = offset < total and len(orders) > 0

            if has_more:
                logger.info(f"Fetched {offset}/{total} orders. Continuing...")

        logger.info(f"\n✅ Total unshipped orders fetched: {len(all_orders)}")

        if not all_orders:
            logger.info("ℹ️  No unshipped orders found. Nothing to export.")
            return None

        # Map orders to Amazon format
        logger.info("\nMapping orders to Amazon fulfillment format...")
        mapped_orders = []

        for order in all_orders:
            try:
                mapped_order = self.map_order_to_amazon_format(order)
                mapped_orders.append(mapped_order)
                logger.info(f"  ✓ Mapped order {mapped_order['ebayOrderId']} with {len(mapped_order['items'])} items")
            except Exception as e:
                logger.error(f"  ✗ Failed to map order {order.get('orderId', 'UNKNOWN')}: {str(e)}")

        # Export to JSON file
        if not output_filename:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            output_filename = f"ebay-orders-{timestamp}.json"

        output_path = self.output_folder / output_filename

        export_data = {
            "exportedAt": datetime.utcnow().isoformat() + "Z",
            "account": self.account,
            "totalOrders": len(mapped_orders),
            "orders": mapped_orders
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"\n✅ Exported {len(mapped_orders)} orders to: {output_path}")
        logger.info("="*70 + "\n")

        return str(output_path)


def main():
    """Main entry point for order fetching flow"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch unshipped eBay orders for Amazon fulfillment"
    )
    parser.add_argument(
        "--account",
        type=int,
        default=None,
        choices=[1, 2],
        help="eBay account to use (1 or 2, defaults to active_account in settings)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of orders to fetch per request (default: 50, max: 200)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output filename (optional)"
    )

    args = parser.parse_args()

    # Initialize order fetcher
    fetcher = EbayOrderFetcher(account=args.account)

    # Check authentication
    account_name = f"Account {fetcher.account}" + (" (Primary)" if fetcher.account == 1 else " (Secondary)")
    logger.info(f"Using {account_name}")

    if not fetcher.token_manager.load_tokens():
        logger.error(f"❌ No valid OAuth token found for {account_name}!")
        logger.error(f"   Please run: python authorize_account.py {fetcher.account}")
        return

    logger.info(f"✅ OAuth authentication ready for {account_name}\n")

    # Fetch and export orders
    try:
        output_path = fetcher.fetch_and_export_orders(
            limit=args.limit,
            output_filename=args.output
        )

        if output_path:
            print(f"\n📦 Order export completed successfully!")
            print(f"📁 File location: {output_path}")
            print(f"\n💡 Next steps:")
            print(f"   1. Review the exported JSON file")
            print(f"   2. Use the web extension to populate addresses in Amazon")
            print(f"   3. Place orders for the listed products")
        else:
            print("\nℹ️  No orders to process at this time.")

    except Exception as e:
        logger.error(f"\n❌ Order fetch failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()

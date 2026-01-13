"""
eBay Sold Items Fetcher for Market Analysis
Fetches ALL sold items from eBay account, regardless of shipping status
Used for analyzing past sales performance and market trends
"""

import json
import logging
import requests
from datetime import datetime, timedelta
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


class EbaySoldItemsFetcher:
    """Fetches and processes ALL sold items from eBay for market analysis"""

    def __init__(self, account: int = None):
        """Initialize sold items fetcher for specific account"""
        self.account = account or settings.active_account
        self.token_manager = get_token_manager(self.account)
        self.base_url = settings.ebay_api_base_url
        self.output_folder = Path("ebay_sold_items_analysis")
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

    def get_sold_orders(
        self,
        limit: int = 50,
        offset: int = 0,
        days_back: int = 90,
        order_status: str = None
    ) -> Dict[str, Any]:
        """
        Fetch ALL sold orders from eBay, regardless of fulfillment status.

        Uses eBay Fulfillment API: getOrders
        https://developer.ebay.com/api-docs/sell/fulfillment/resources/order/methods/getOrders

        Args:
            limit: Number of orders to fetch per request (max 200)
            offset: Pagination offset
            days_back: How many days back to search (max 90 per request, will paginate beyond)
            order_status: Optional filter - 'NOT_STARTED', 'IN_PROGRESS', 'FULFILLED', or None for all

        Returns:
            Dict containing orders and metadata
        """
        endpoint = f"{self.base_url}/sell/fulfillment/v1/order"

        # Build filter string
        # Get orders from last N days
        date_from = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        # Filter by fulfillment status if specified, otherwise get ALL orders
        if order_status:
            # Specific status filter
            params = {
                "filter": f"orderfulfillmentstatus:{{{order_status}}}",
                "limit": min(limit, 200),
                "offset": offset
            }
        else:
            # No status filter = ALL orders (fulfilled, in_progress, not_started)
            # Note: eBay API requires at least a date filter for efficient queries
            params = {
                "filter": f"creationdate:[{date_from}..]",
                "limit": min(limit, 200),
                "offset": offset
            }

        try:
            logger.info(f"Fetching sold orders (offset: {offset}, days_back: {days_back})...")
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

            logger.info(f"  Found {len(orders)} orders in this batch (Total available: {total})")
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

    def extract_market_analysis_data(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract relevant data from eBay order for market analysis.

        Args:
            order: eBay order object

        Returns:
            Dict containing market analysis relevant information
        """
        order_id = order.get("orderId", "")
        order_date = order.get("creationDate", "")
        order_status = order.get("orderFulfillmentStatus", "")

        # Extract buyer information
        buyer = order.get("buyer", {})
        buyer_username = buyer.get("username", "")

        # Extract payment summary
        payment_summary = order.get("paymentSummary", {})
        total_paid = payment_summary.get("totalDueSeller", {})

        # Extract line items
        line_items = order.get("lineItems", [])
        items_data = []

        for item in line_items:
            sku = item.get("sku", "")
            title = item.get("title", "")
            quantity = item.get("quantity", 1)

            # Extract pricing
            line_item_cost = item.get("lineItemCost", {})
            item_price = float(line_item_cost.get("value", "0.00"))

            # Extract listing marketplace ID if available
            listing_marketplace_id = item.get("listingMarketplaceId", "EBAY_US")

            # Extract sold date (use order creation date)
            sold_date = order_date

            items_data.append({
                "sku": sku,
                "asin": sku,  # In your setup, SKU is the ASIN
                "title": title,
                "quantity": quantity,
                "soldPrice": item_price,
                "soldDate": sold_date,
                "marketplace": listing_marketplace_id
            })

        # Extract shipping costs if available
        pricing_summary = order.get("pricingSummary", {})
        delivery_cost = pricing_summary.get("deliveryCost", {})
        shipping_cost = float(delivery_cost.get("value", "0.00"))

        # Calculate total revenue and fees
        total_amount = float(total_paid.get("value", "0.00"))

        # Extract fees if available (eBay take)
        # Note: Actual fees might require separate API call to get detailed breakdown
        # This is a simplified version

        analysis_data = {
            "orderId": order_id,
            "orderDate": order_date,
            "fulfillmentStatus": order_status,
            "buyerUsername": buyer_username,
            "totalRevenue": total_amount,
            "shippingCost": shipping_cost,
            "currency": total_paid.get("currency", "USD"),
            "items": items_data,
            "totalItems": len(items_data),
            "totalQuantity": sum(item["quantity"] for item in items_data)
        }

        return analysis_data

    def fetch_all_sold_orders(
        self,
        days_back_per_batch: int = 90,
        total_days_back: int = 365,
        max_orders: int = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch ALL sold orders, paginating through multiple time periods if needed.

        eBay API limits queries to 90 days max, so we'll paginate through time periods.

        Args:
            days_back_per_batch: Days to fetch per API batch (max 90)
            total_days_back: Total days to look back (will make multiple requests)
            max_orders: Optional limit on total orders to fetch

        Returns:
            List of all sold orders
        """
        all_orders = []
        days_back_per_batch = min(days_back_per_batch, 90)  # eBay max is 90

        # Calculate number of time periods we need to query
        num_periods = (total_days_back + days_back_per_batch - 1) // days_back_per_batch

        logger.info("\n" + "="*70)
        logger.info(f"Fetching ALL sold items for market analysis")
        logger.info(f"Account: {self.account}")
        logger.info(f"Time range: Last {total_days_back} days")
        logger.info("="*70)

        for period in range(num_periods):
            # Calculate time range for this period
            period_start = period * days_back_per_batch
            period_end = min((period + 1) * days_back_per_batch, total_days_back)

            logger.info(f"\nFetching period: {period_end} to {period_start} days ago...")

            # Paginate through all orders in this time period
            offset = 0
            has_more = True

            while has_more:
                response = self.get_sold_orders(
                    limit=200,  # Max per request
                    offset=offset,
                    days_back=period_end
                )

                orders = response.get("orders", [])
                total = response.get("total", 0)

                # Filter orders by date to only include those in our period
                period_orders = []
                for order in orders:
                    order_date = datetime.fromisoformat(order.get("creationDate", "").replace("Z", "+00:00"))
                    days_ago = (datetime.now(order_date.tzinfo) - order_date).days

                    if period_start <= days_ago < period_end:
                        period_orders.append(order)

                all_orders.extend(period_orders)

                # Check if we've hit the max orders limit
                if max_orders and len(all_orders) >= max_orders:
                    logger.info(f"  Reached max_orders limit of {max_orders}")
                    all_orders = all_orders[:max_orders]
                    return all_orders

                # Check if there are more orders to fetch
                offset += len(orders)
                has_more = offset < total and len(orders) > 0

                if has_more:
                    logger.info(f"  Progress: {offset}/{total} orders in this period")
                else:
                    break

        logger.info(f"\n✅ Total sold orders fetched: {len(all_orders)}")
        return all_orders

    def export_market_analysis(
        self,
        days_back: int = 365,
        max_orders: int = None,
        output_filename: Optional[str] = None
    ) -> str:
        """
        Fetch all sold orders and export to JSON for market analysis.

        Args:
            days_back: How many days back to analyze (default: 365 for 1 year)
            max_orders: Optional limit on total orders
            output_filename: Custom output filename (optional)

        Returns:
            Path to the exported JSON file
        """
        # Fetch all orders
        all_orders = self.fetch_all_sold_orders(
            days_back_per_batch=90,
            total_days_back=days_back,
            max_orders=max_orders
        )

        if not all_orders:
            logger.info("ℹ️  No sold orders found. Nothing to export.")
            return None

        # Extract market analysis data
        logger.info("\nExtracting market analysis data...")
        analysis_data = []

        for order in all_orders:
            try:
                data = self.extract_market_analysis_data(order)
                analysis_data.append(data)
            except Exception as e:
                logger.error(f"  ✗ Failed to process order {order.get('orderId', 'UNKNOWN')}: {str(e)}")

        # Calculate summary statistics
        total_revenue = sum(item["totalRevenue"] for item in analysis_data)
        total_items_sold = sum(item["totalQuantity"] for item in analysis_data)

        # Generate output filename
        if not output_filename:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            output_filename = f"sold-items-analysis-{timestamp}.json"

        output_path = self.output_folder / output_filename

        # Create export data with summary
        export_data = {
            "exportedAt": datetime.utcnow().isoformat() + "Z",
            "account": self.account,
            "analysisTimeRange": {
                "daysBack": days_back,
                "fromDate": (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z",
                "toDate": datetime.utcnow().isoformat() + "Z"
            },
            "summary": {
                "totalOrders": len(analysis_data),
                "totalItemsSold": total_items_sold,
                "totalRevenue": round(total_revenue, 2),
                "currency": "USD",
                "averageOrderValue": round(total_revenue / len(analysis_data), 2) if analysis_data else 0
            },
            "orders": analysis_data
        }

        # Export to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"\n✅ Market analysis exported to: {output_path}")
        logger.info("\n" + "="*70)
        logger.info("SUMMARY STATISTICS")
        logger.info("="*70)
        logger.info(f"Total Orders: {len(analysis_data)}")
        logger.info(f"Total Items Sold: {total_items_sold}")
        logger.info(f"Total Revenue: ${total_revenue:,.2f}")
        logger.info(f"Average Order Value: ${export_data['summary']['averageOrderValue']:,.2f}")
        logger.info("="*70 + "\n")

        return str(output_path)


def main():
    """Main entry point for sold items fetching"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch ALL sold eBay items for market analysis"
    )
    parser.add_argument(
        "--account",
        type=int,
        default=None,
        choices=[1, 2],
        help="eBay account to use (1 or 2, defaults to active_account in settings)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days back to analyze (default: 365 for 1 year)"
    )
    parser.add_argument(
        "--max-orders",
        type=int,
        default=None,
        help="Maximum number of orders to fetch (optional, for testing)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output filename (optional)"
    )

    args = parser.parse_args()

    # Initialize fetcher
    fetcher = EbaySoldItemsFetcher(account=args.account)

    # Check authentication
    account_name = f"Account {fetcher.account}" + (" (Primary)" if fetcher.account == 1 else " (Secondary)")
    logger.info(f"Using {account_name}")

    if not fetcher.token_manager.load_tokens():
        logger.error(f"❌ No valid OAuth token found for {account_name}!")
        logger.error(f"   Please run: python authorize_account.py {fetcher.account}")
        return

    logger.info(f"✅ OAuth authentication ready for {account_name}\n")

    # Fetch and export market analysis
    try:
        output_path = fetcher.export_market_analysis(
            days_back=args.days,
            max_orders=args.max_orders,
            output_filename=args.output
        )

        if output_path:
            print(f"\n📊 Market analysis export completed!")
            print(f"📁 File location: {output_path}")
            print(f"\n💡 Use this data to:")
            print(f"   - Analyze best-selling products")
            print(f"   - Track revenue trends over time")
            print(f"   - Identify seasonal patterns")
            print(f"   - Calculate profit margins per SKU")
            print(f"   - Optimize pricing strategies\n")
        else:
            print("\nℹ️  No sold items found in the specified time range.")

    except Exception as e:
        logger.error(f"\n❌ Market analysis failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()

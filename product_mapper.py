"""
Product Data Mapper: Amazon -> eBay
Maps Amazon product data to eBay Inventory API format
"""

import re
from typing import Dict, Any, List
from config import settings


class ProductMapper:
    """Maps Amazon product data to eBay listing format"""

    def __init__(self):
        self.price_markup_percentage = settings.price_markup_percentage
        self.fixed_markup_amount = settings.fixed_markup_amount

    def parse_price(self, price_str: str) -> float:
        """
        Extract numeric price from Amazon price string.
        Examples: "$29.99", "$1,299.00", "£19.99"
        """
        if not price_str:
            return 0.0

        # Remove currency symbols and commas
        cleaned = re.sub(r'[£$€,]', '', price_str.strip())

        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def calculate_ebay_price(self, amazon_price: float) -> float:
        """
        Calculate eBay listing price with markup.
        Formula: (amazon_price * (1 + markup%)) + fixed_markup
        """
        if amazon_price <= 0:
            return 0.0

        markup_multiplier = 1 + (self.price_markup_percentage / 100)
        calculated_price = (amazon_price * markup_multiplier) + self.fixed_markup_amount

        # Round to 2 decimal places
        return round(calculated_price, 2)

    def generate_sku(self, asin: str) -> str:
        """
        Generate unique SKU for eBay listing.
        Format: AMZN-{ASIN}
        """
        return f"AMZN-{asin}"

    def extract_brand(self, title: str, description: str) -> str:
        """
        Attempt to extract brand from title or description.
        eBay requires brand for many categories.
        """
        # Common brand indicators
        brand_keywords = ["by", "Brand:", "Manufacturer:"]

        # Check title first
        for keyword in brand_keywords:
            if keyword.lower() in title.lower():
                parts = title.split(keyword, 1)
                if len(parts) > 1:
                    potential_brand = parts[1].strip().split()[0]
                    return potential_brand

        # Default fallback
        return "Unbranded"

    def map_to_inventory_item(self, amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Amazon product to eBay Inventory Item format.

        eBay Inventory Item structure:
        https://developer.ebay.com/api-docs/sell/inventory/types/api:InventoryItem
        """
        asin = amazon_product.get("asin", "")
        title = amazon_product.get("title", "Untitled Product")
        description = amazon_product.get("description", "")
        bullet_points = amazon_product.get("bulletPoints", [])
        images = amazon_product.get("images", [])
        amazon_price_str = amazon_product.get("price", "$0.00")

        # Generate SKU
        sku = self.generate_sku(asin)

        # Parse and calculate price
        amazon_price = self.parse_price(amazon_price_str)
        ebay_price = self.calculate_ebay_price(amazon_price)

        # Build product description
        full_description = self._build_description(
            title, description, bullet_points, amazon_product.get("url")
        )

        # Map to eBay format
        inventory_item = {
            "sku": sku,
            "product": {
                "title": self._truncate_title(title),
                "description": full_description,
                "imageUrls": images[:12],  # eBay allows max 12 images
                "aspects": self._extract_aspects(amazon_product)
            },
            "condition": "NEW",
            "conditionDescription": "Brand new item from Amazon",
            "availability": {
                "shipToLocationAvailability": {
                    "quantity": 10  # Adjust based on your dropshipping strategy
                }
            }
        }

        return inventory_item

    def map_to_offer(
        self,
        amazon_product: Dict[str, Any],
        category_id: str,
        payment_policy_id: str,
        return_policy_id: str,
        fulfillment_policy_id: str
    ) -> Dict[str, Any]:
        """
        Map Amazon product to eBay Offer format.

        eBay Offer structure:
        https://developer.ebay.com/api-docs/sell/inventory/types/api:EbayOfferDetailsWithAll

        Note: Business Policies (payment, return, fulfillment) must be created
        in your eBay account first via Seller Hub.
        """
        asin = amazon_product.get("asin", "")
        sku = self.generate_sku(asin)
        title = amazon_product.get("title", "Untitled Product")
        amazon_price_str = amazon_product.get("price", "$0.00")

        # Calculate pricing
        amazon_price = self.parse_price(amazon_price_str)
        ebay_price = self.calculate_ebay_price(amazon_price)

        offer = {
            "sku": sku,
            "marketplaceId": "EBAY_US",  # Adjust based on your target market
            "format": "FIXED_PRICE",
            "listingDescription": self._build_html_description(amazon_product),
            "listingPolicies": {
                "paymentPolicyId": payment_policy_id,
                "returnPolicyId": return_policy_id,
                "fulfillmentPolicyId": fulfillment_policy_id
            },
            "pricingSummary": {
                "price": {
                    "value": str(ebay_price),
                    "currency": "USD"
                }
            },
            "quantityLimitPerBuyer": 5,
            "categoryId": category_id,
            "merchantLocationKey": "default"  # Or your specific location key
        }

        return offer

    def _truncate_title(self, title: str, max_length: int = 80) -> str:
        """
        eBay title limit is 80 characters.
        Truncate Amazon title if needed.
        """
        if len(title) <= max_length:
            return title

        return title[:max_length - 3] + "..."

    def _build_description(
        self,
        title: str,
        description: str,
        bullet_points: List[str],
        url: str = None
    ) -> str:
        """Build plain text description for inventory item"""
        parts = [title, ""]

        if bullet_points:
            parts.append("Features:")
            for bullet in bullet_points[:10]:
                parts.append(f"• {bullet.strip()}")
            parts.append("")

        if description:
            parts.append("Description:")
            parts.append(description.strip())
            parts.append("")

        parts.append("Note: This is a dropshipping item. Fast shipping from trusted suppliers.")

        return "\n".join(parts)

    def _build_html_description(self, amazon_product: Dict[str, Any]) -> str:
        """
        Build HTML description for eBay listing.
        eBay supports HTML in listing descriptions.
        """
        title = amazon_product.get("title", "")
        description = amazon_product.get("description", "")
        bullet_points = amazon_product.get("bulletPoints", [])
        images = amazon_product.get("images", [])

        html_parts = [
            '<div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">',
            f'<h2 style="color: #333;">{title}</h2>',
        ]

        # Add main image
        if images:
            html_parts.append(
                f'<div style="text-align: center; margin: 20px 0;">'
                f'<img src="{images[0]}" alt="Product Image" style="max-width: 100%; height: auto;" />'
                f'</div>'
            )

        # Add bullet points
        if bullet_points:
            html_parts.append('<h3 style="color: #555;">Key Features:</h3>')
            html_parts.append('<ul style="line-height: 1.8;">')
            for bullet in bullet_points[:10]:
                html_parts.append(f'<li>{bullet.strip()}</li>')
            html_parts.append('</ul>')

        # Add description
        if description:
            html_parts.append('<h3 style="color: #555;">Product Description:</h3>')
            html_parts.append(f'<p style="line-height: 1.6;">{description.strip()}</p>')

        # Add shipping note
        html_parts.append(
            '<div style="background: #f0f0f0; padding: 15px; margin-top: 20px; border-radius: 5px;">'
            '<p style="margin: 0; font-size: 14px;"><strong>Shipping:</strong> '
            'Fast and reliable shipping. Item will be carefully packaged and shipped promptly.</p>'
            '</div>'
        )

        html_parts.append('</div>')

        return ''.join(html_parts)

    def _extract_aspects(self, amazon_product: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract product aspects (item specifics) for eBay.

        Aspects are category-specific attributes like Brand, Color, Size, etc.
        eBay requires certain aspects based on the category.

        https://developer.ebay.com/api-docs/sell/inventory/types/slr:Aspect
        """
        aspects = {}

        # Extract brand
        title = amazon_product.get("title", "")
        description = amazon_product.get("description", "")
        brand = self.extract_brand(title, description)
        aspects["Brand"] = [brand]

        # Extract from specifications if available
        specs = amazon_product.get("specifications", {})
        for key, value in specs.items():
            # Map common Amazon specs to eBay aspects
            if "brand" in key.lower() and value:
                aspects["Brand"] = [value]
            elif "color" in key.lower() and value:
                aspects["Color"] = [value]
            elif "size" in key.lower() and value:
                aspects["Size"] = [value]
            elif "material" in key.lower() and value:
                aspects["Material"] = [value]

        # Add condition
        aspects["Condition"] = ["New"]

        # Add MPN if available in ASIN
        asin = amazon_product.get("asin")
        if asin:
            aspects["MPN"] = [asin]

        return aspects


# Global mapper instance
product_mapper = ProductMapper()

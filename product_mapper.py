"""
Product Data Mapper: Amazon -> eBay
Maps Amazon product data to eBay Inventory API format
"""

import re
from typing import Dict, Any, List
from config import settings
from data_sanitizer import data_sanitizer


class ProductMapper:
    """Maps Amazon product data to eBay listing format"""

    def __init__(self):
        # Legacy pricing settings (backward compatibility)
        self.price_markup_percentage = settings.price_markup_percentage
        self.fixed_markup_amount = settings.fixed_markup_amount

        # Tiered pricing settings
        self.tier_1_max_price = settings.tier_1_max_price
        self.tier_1_multiplier = settings.tier_1_multiplier
        self.tier_2_max_price = settings.tier_2_max_price
        self.tier_2_multiplier = settings.tier_2_multiplier
        self.tier_3_max_price = settings.tier_3_max_price
        self.tier_3_multiplier = settings.tier_3_multiplier
        self.tier_4_multiplier = settings.tier_4_multiplier

        # Charm pricing strategy
        self.charm_pricing_strategy = settings.charm_pricing_strategy

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

    def get_tiered_multiplier(self, amazon_price: float) -> float:
        """
        Get the appropriate price multiplier based on tiered pricing strategy.

        Pricing tiers (optimized for Amazon-eBay arbitrage):
        - Tier 1: Items < $20 → Higher multiplier (impulse buys)
        - Tier 2: Items $20-$30 → Mid-high multiplier
        - Tier 3: Items $30-$40 → Mid multiplier
        - Tier 4: Items > $40 → Lower multiplier (price-sensitive buyers)

        Args:
            amazon_price: The Amazon product price

        Returns:
            float: The multiplier to use for this price tier
        """
        if amazon_price < self.tier_1_max_price:
            return self.tier_1_multiplier
        elif amazon_price < self.tier_2_max_price:
            return self.tier_2_multiplier
        elif amazon_price < self.tier_3_max_price:
            return self.tier_3_multiplier
        else:
            return self.tier_4_multiplier

    def apply_charm_pricing(self, price: float) -> float:
        """
        Apply charm pricing strategy to make prices more psychologically appealing.

        Strategies:
        - always_99: Round to .99 (e.g., $23.67 -> $23.99)
        - always_49: Round to .49 (e.g., $23.67 -> $23.49)
        - tiered: Under $20 use .99, $20+ use .95

        Args:
            price: The calculated price before charm pricing

        Returns:
            float: Price with charm pricing applied
        """
        if price <= 0:
            return 0.0

        # Get the dollar amount (integer part)
        dollar_amount = int(price)

        # Apply strategy
        if self.charm_pricing_strategy == "always_99":
            # Always end in .99
            return dollar_amount + 0.99

        elif self.charm_pricing_strategy == "always_49":
            # Always end in .49
            return dollar_amount + 0.49

        elif self.charm_pricing_strategy == "tiered":
            # Under $20 use .99 (impulse buys), $20+ use .95 (quality signal)
            if price < 20:
                return dollar_amount + 0.99
            else:
                return dollar_amount + 0.95

        else:
            # Unknown strategy, return original rounded price
            return round(price, 2)

    def calculate_ebay_price(self, amazon_price: float, delivery_fee: float = 0.0, multiplier: float = None) -> float:
        """
        Calculate eBay listing price with multiplier or markup, including delivery fee.

        Calculation flow:
        1. Apply tiered multiplier to (product price + delivery fee)
        2. Apply charm pricing strategy (.99, .49, or tiered)
        3. This ensures you profit on both the item cost AND shipping cost

        Priority order:
        1. If multiplier is provided in product data, use it
        2. Otherwise, use tiered pricing strategy based on amazon_price
        3. Fallback: legacy markup settings (backward compatibility)

        Args:
            amazon_price: The Amazon product price
            delivery_fee: Amazon delivery/shipping fee (default: 0.0)
            multiplier: Optional override multiplier from product data

        Returns:
            float: The calculated eBay listing price (includes delivery fee coverage + charm pricing)
        """
        if amazon_price <= 0:
            return 0.0

        # Total Amazon cost = product price + delivery fee
        total_amazon_cost = amazon_price + delivery_fee

        if multiplier is not None:
            # Use the multiplier directly (from product data)
            calculated_price = total_amazon_cost * multiplier
        else:
            # Use tiered pricing strategy based on total cost
            tiered_multiplier = self.get_tiered_multiplier(total_amazon_cost)
            calculated_price = total_amazon_cost * tiered_multiplier

        # Apply charm pricing strategy
        return self.apply_charm_pricing(calculated_price)

    def generate_sku(self, asin: str) -> str:
        """
        Generate unique SKU for eBay listing.
        Format: {ASIN}
        """
        return asin

    def extract_brand(self, title: str, description: str) -> str:
        """
        Attempt to extract brand from title or description.
        eBay requires brand for many categories.
        """
        # Invalid brand names that eBay rejects
        invalid_brands = {
            "custom", "personalized", "handmade", "vintage", "unique",
            "new", "brand", "the", "a", "an", "with", "for", "and"
        }

        # Try to extract first word if it looks like a brand (all caps or capitalized)
        words = title.split()
        if words:
            first_word = words[0]
            # Check if first word is likely a brand name
            if (first_word.isupper() or (len(first_word) > 1 and first_word[0].isupper())):
                # Make sure it's not in the invalid list
                if first_word.lower() not in invalid_brands:
                    return first_word

        # Common brand indicators
        brand_keywords = ["by", "Brand:", "Manufacturer:"]

        # Check title for brand keywords
        for keyword in brand_keywords:
            if keyword.lower() in title.lower():
                parts = title.split(keyword, 1)
                if len(parts) > 1:
                    potential_brand = parts[1].strip().split()[0]
                    if potential_brand.lower() not in invalid_brands:
                        return potential_brand

        # Default fallback - use "Generic" instead of "Unbranded"
        # (some categories reject "Unbranded" for new items)
        return "Generic"

    def map_to_inventory_item(self, amazon_product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Amazon product to eBay Inventory Item format.

        eBay Inventory Item structure:
        https://developer.ebay.com/api-docs/sell/inventory/types/api:InventoryItem

        Supports optional 'price_multiplier' field in amazon_product (default: 2.0)
        """
        # IMPORTANT: Sanitize product data first to remove eBay policy violations
        sanitized_product = data_sanitizer.sanitize_product(amazon_product)

        asin = sanitized_product.get("asin", "")
        title = sanitized_product.get("title", "Untitled Product")
        description = sanitized_product.get("description", "")
        bullet_points = sanitized_product.get("bulletPoints", [])
        images = sanitized_product.get("images", [])
        amazon_price_str = sanitized_product.get("price", "$0.00")
        delivery_fee_str = sanitized_product.get("deliveryFee", "$0.00")

        # Get price multiplier from product data (optional override)
        # If not provided, calculate_ebay_price will use tiered pricing
        price_multiplier = sanitized_product.get("price_multiplier", None)

        # Generate SKU
        sku = self.generate_sku(asin)

        # Parse and calculate price (includes delivery fee)
        amazon_price = self.parse_price(amazon_price_str)
        delivery_fee = self.parse_price(delivery_fee_str)
        ebay_price = self.calculate_ebay_price(amazon_price, delivery_fee=delivery_fee, multiplier=price_multiplier)

        # Build product description (already using sanitized data)
        full_description = self._build_description(
            title, description, bullet_points
        )

        # Map to eBay format
        inventory_item = {
            "sku": sku,
            "locale": "en_US",  # Required for bulk API
            "product": {
                "title": self._truncate_title(title),
                "description": full_description,
                "imageUrls": images[:12],  # eBay allows max 12 images
                "aspects": self._extract_aspects(sanitized_product)
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

        Supports optional 'price_multiplier' field in amazon_product (default: 2.0)
        """
        # IMPORTANT: Sanitize product data first to remove eBay policy violations
        sanitized_product = data_sanitizer.sanitize_product(amazon_product)

        asin = sanitized_product.get("asin", "")
        sku = self.generate_sku(asin)
        title = sanitized_product.get("title", "Untitled Product")
        amazon_price_str = sanitized_product.get("price", "$0.00")
        delivery_fee_str = sanitized_product.get("deliveryFee", "$0.00")

        # Get price multiplier from product data (optional override)
        # If not provided, calculate_ebay_price will use tiered pricing
        price_multiplier = sanitized_product.get("price_multiplier", None)

        # Calculate pricing (includes delivery fee)
        amazon_price = self.parse_price(amazon_price_str)
        delivery_fee = self.parse_price(delivery_fee_str)
        ebay_price = self.calculate_ebay_price(amazon_price, delivery_fee=delivery_fee, multiplier=price_multiplier)

        offer = {
            "sku": sku,
            "marketplaceId": "EBAY_US",  # Adjust based on your target market
            "format": "FIXED_PRICE",
            "listingDescription": self._build_html_description(sanitized_product),
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
        bullet_points: List[str]
    ) -> str:
        """Build plain text description for inventory item (data is already sanitized)"""
        parts = [title, ""]

        if bullet_points:
            parts.append("Features:")
            for bullet in bullet_points[:10]:
                if bullet.strip():  # Only include non-empty bullets
                    parts.append(f"• {bullet.strip()}")
            parts.append("")

        if description and description.strip():
            parts.append("Description:")
            parts.append(description.strip())
            parts.append("")

        parts.append("Note: This is a dropshipping item. Fast shipping from trusted suppliers.")

        return "\n".join(parts)

    def _build_html_description(self, amazon_product: Dict[str, Any]) -> str:
        """
        Build HTML description for eBay listing.
        eBay supports HTML in listing descriptions.
        (Product data is already sanitized before this method is called)
        """
        title = amazon_product.get("title", "")
        description = amazon_product.get("description", "")
        bullet_points = amazon_product.get("bulletPoints", [])
        images = amazon_product.get("images", [])
        specifications = amazon_product.get("specifications", {})

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
                if bullet.strip():  # Only include non-empty bullets
                    html_parts.append(f'<li>{bullet.strip()}</li>')
            html_parts.append('</ul>')

        # Add description
        if description and description.strip():
            html_parts.append('<h3 style="color: #555;">Product Description:</h3>')
            html_parts.append(f'<p style="line-height: 1.6;">{description.strip()}</p>')

        # Add specifications if available
        if specifications and isinstance(specifications, dict) and len(specifications) > 0:
            html_parts.append('<h3 style="color: #555;">Specifications:</h3>')
            html_parts.append('<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">')
            for spec_key, spec_value in specifications.items():
                if spec_value and str(spec_value).strip():  # Only include non-empty values
                    html_parts.append(
                        f'<tr style="border-bottom: 1px solid #ddd;">'
                        f'<td style="padding: 10px; font-weight: bold; width: 40%;">{spec_key}:</td>'
                        f'<td style="padding: 10px;">{spec_value}</td>'
                        f'</tr>'
                    )
            html_parts.append('</table>')

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

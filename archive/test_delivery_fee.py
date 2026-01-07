"""
Test delivery fee pricing calculation
"""

from product_mapper import product_mapper

print("=" * 70)
print("Testing Delivery Fee Pricing")
print("=" * 70)

# Test Case 1: Product with delivery fee (your example)
print("\n[Test 1] Product with delivery fee")
product_price = 6.95
delivery_fee = 5.95
total_cost = product_price + delivery_fee
ebay_price = product_mapper.calculate_ebay_price(product_price, delivery_fee=delivery_fee)
multiplier = product_mapper.get_tiered_multiplier(total_cost)

print(f"  Amazon Product: ${product_price:.2f}")
print(f"  Amazon Delivery: ${delivery_fee:.2f}")
print(f"  Total Amazon Cost: ${total_cost:.2f}")
print(f"  Tier Multiplier: {multiplier}x")
print(f"  eBay Listing Price: ${ebay_price:.2f}")
print(f"  Your Profit: ${ebay_price - total_cost:.2f}")

# Test Case 2: Product without delivery fee
print("\n[Test 2] Product without delivery fee")
product_price = 15.00
delivery_fee = 0.00
total_cost = product_price + delivery_fee
ebay_price = product_mapper.calculate_ebay_price(product_price, delivery_fee=delivery_fee)
multiplier = product_mapper.get_tiered_multiplier(total_cost)

print(f"  Amazon Product: ${product_price:.2f}")
print(f"  Amazon Delivery: ${delivery_fee:.2f}")
print(f"  Total Amazon Cost: ${total_cost:.2f}")
print(f"  Tier Multiplier: {multiplier}x")
print(f"  eBay Listing Price: ${ebay_price:.2f}")
print(f"  Your Profit: ${ebay_price - total_cost:.2f}")

# Test Case 3: Higher priced item with delivery
print("\n[Test 3] Higher priced item with delivery")
product_price = 35.00
delivery_fee = 8.50
total_cost = product_price + delivery_fee
ebay_price = product_mapper.calculate_ebay_price(product_price, delivery_fee=delivery_fee)
multiplier = product_mapper.get_tiered_multiplier(total_cost)

print(f"  Amazon Product: ${product_price:.2f}")
print(f"  Amazon Delivery: ${delivery_fee:.2f}")
print(f"  Total Amazon Cost: ${total_cost:.2f}")
print(f"  Tier Multiplier: {multiplier}x")
print(f"  eBay Listing Price: ${ebay_price:.2f}")
print(f"  Your Profit: ${ebay_price - total_cost:.2f}")

print("\n" + "=" * 70)
print("Key Insight: Delivery fee is included in total cost for tiering!")
print("=" * 70)
print("\nExample: $6.95 product + $5.95 delivery = $12.90 total")
print("This uses Tier 1 multiplier (1.9x) since $12.90 < $15")
print(f"eBay price: ${12.90 * 1.9:.2f}")
print(f"Your profit after eBay fees (~16%): ${12.90 * 1.9 * 0.84 - 12.90:.2f}")
print()

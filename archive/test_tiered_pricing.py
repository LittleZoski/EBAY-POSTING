"""
Test script to verify tiered pricing is working correctly
"""

from product_mapper import product_mapper

# Test cases based on your tiered pricing settings
test_prices = [
    10.00,   # Tier 1: < $15 -> 1.9x
    14.99,   # Tier 1: < $15 -> 1.9x
    15.00,   # Tier 2: $15-$25 -> 1.75x
    24.99,   # Tier 2: $15-$25 -> 1.75x (your vacuum sealer)
    25.00,   # Tier 3: $25-$40 -> 1.6x
    35.00,   # Tier 3: $25-$40 -> 1.6x
    40.00,   # Tier 4: > $40 -> 1.5x
    50.00,   # Tier 4: > $40 -> 1.5x
    75.00,   # Tier 4: > $40 -> 1.5x
]

print("="*70)
print("Tiered Pricing Test")
print("="*70)
print("\nCurrent tier settings:")
print(f"  Tier 1: < ${product_mapper.tier_1_max_price} -> {product_mapper.tier_1_multiplier}x")
print(f"  Tier 2: ${product_mapper.tier_1_max_price}-${product_mapper.tier_2_max_price} -> {product_mapper.tier_2_multiplier}x")
print(f"  Tier 3: ${product_mapper.tier_2_max_price}-${product_mapper.tier_3_max_price} -> {product_mapper.tier_3_multiplier}x")
print(f"  Tier 4: > ${product_mapper.tier_3_max_price} -> {product_mapper.tier_4_multiplier}x")

print("\n" + "="*70)
print("Price Calculations")
print("="*70)
print(f"{'Amazon Price':<15} {'Multiplier':<12} {'eBay Price':<12} {'Profit':<12} {'Margin'}")
print("-"*70)

for amazon_price in test_prices:
    # Calculate using tiered pricing (no override)
    ebay_price = product_mapper.calculate_ebay_price(amazon_price, multiplier=None)
    multiplier = product_mapper.get_tiered_multiplier(amazon_price)

    # Calculate profit (after eBay fees: 13.25% + 2.35% + $0.30)
    ebay_fees = (ebay_price * 0.1560) + 0.30
    profit = ebay_price - amazon_price - ebay_fees
    margin = (profit / ebay_price * 100) if ebay_price > 0 else 0

    print(f"${amazon_price:<14.2f} {multiplier}x{'':<9} ${ebay_price:<11.2f} ${profit:<11.2f} {margin:.1f}%")

print("\n" + "="*70)
print("Your Recent Product Example")
print("="*70)

# Test with your actual vacuum sealer product
vacuum_price = 24.99
vacuum_ebay = product_mapper.calculate_ebay_price(vacuum_price, multiplier=None)
vacuum_multiplier = product_mapper.get_tiered_multiplier(vacuum_price)
vacuum_fees = (vacuum_ebay * 0.1560) + 0.30
vacuum_profit = vacuum_ebay - vacuum_price - vacuum_fees

print(f"\nVacuum Sealer: ${vacuum_price}")
print(f"  Tier: 2 ({vacuum_multiplier}x multiplier)")
print(f"  eBay Price: ${vacuum_ebay:.2f}")
print(f"  eBay Fees: ${vacuum_fees:.2f}")
print(f"  Net Profit: ${vacuum_profit:.2f}")
print(f"  Profit Margin: {(vacuum_profit/vacuum_ebay*100):.1f}%")

# Compare to old 2x pricing
old_ebay = vacuum_price * 2.0
old_fees = (old_ebay * 0.1560) + 0.30
old_profit = old_ebay - vacuum_price - old_fees

print(f"\nOld 2x pricing:")
print(f"  eBay Price: ${old_ebay:.2f}")
print(f"  Net Profit: ${old_profit:.2f}")
print(f"  Profit Margin: {(old_profit/old_ebay*100):.1f}%")

print(f"\nDifference:")
print(f"  Price: ${vacuum_ebay:.2f} vs ${old_ebay:.2f} (${old_ebay-vacuum_ebay:.2f} cheaper)")
print(f"  Profit: ${vacuum_profit:.2f} vs ${old_profit:.2f} (${old_profit-vacuum_profit:.2f} less per sale)")
print(f"  But likely 2-3x more sales due to competitive pricing!")

print("\n" + "="*70)

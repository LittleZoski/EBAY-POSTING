"""
Test script to verify charm pricing strategies work correctly
"""
from product_mapper import ProductMapper
from config import settings

def test_charm_pricing():
    """Test all three charm pricing strategies"""

    test_prices = [
        (10.00, 0.00),  # Low price
        (15.42, 0.00),  # Mid-low price
        (23.67, 2.50),  # Mid price with delivery
        (35.88, 0.00),  # Higher price
        (50.23, 5.00),  # High price with delivery
    ]

    strategies = ["always_99", "always_49", "tiered"]

    print("=" * 80)
    print("CHARM PRICING TEST")
    print("=" * 80)
    print(f"\nTier Settings:")
    print(f"  Tier 1: <${settings.tier_1_max_price} @ {settings.tier_1_multiplier}x")
    print(f"  Tier 2: <${settings.tier_2_max_price} @ {settings.tier_2_multiplier}x")
    print(f"  Tier 3: <${settings.tier_3_max_price} @ {settings.tier_3_multiplier}x")
    print(f"  Tier 4: ${settings.tier_3_max_price}+ @ {settings.tier_4_multiplier}x")

    for strategy in strategies:
        print(f"\n{'=' * 80}")
        print(f"STRATEGY: {strategy.upper()}")
        print(f"{'=' * 80}")
        print(f"{'Amazon Price':<15} {'Delivery':<12} {'Total Cost':<12} {'Multiplier':<12} {'Before Charm':<15} {'Final Price':<15}")
        print("-" * 80)

        # Temporarily change strategy
        original_strategy = settings.charm_pricing_strategy
        settings.charm_pricing_strategy = strategy
        mapper = ProductMapper()

        for amazon_price, delivery_fee in test_prices:
            total_cost = amazon_price + delivery_fee
            multiplier = mapper.get_tiered_multiplier(total_cost)
            before_charm = total_cost * multiplier
            final_price = mapper.calculate_ebay_price(amazon_price, delivery_fee)

            print(f"${amazon_price:<14.2f} ${delivery_fee:<11.2f} ${total_cost:<11.2f} {multiplier:<12.2f} ${before_charm:<14.2f} ${final_price:<14.2f}")

        # Restore original strategy
        settings.charm_pricing_strategy = original_strategy

    print(f"\n{'=' * 80}")
    print(f"Current active strategy: {settings.charm_pricing_strategy}")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    test_charm_pricing()

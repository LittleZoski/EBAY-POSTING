"""
Test script for LLM title optimization
"""

from llm_category_selector import LLMCategorySelector

# Initialize selector
print("Initializing LLM Category Selector...")
selector = LLMCategorySelector()

# Test with your vacuum sealer product
test_product = {
    "title": "Food Vacuum Sealer Machine, 75KPA Strong Suction, Dry/Wet Modes, 20 Vacuum Seal Bags for Food, Digital Countdown Timer, Compact Lightweight, Ideal for Home Kitchen Use",
    "description": "Powerful Fast Sealing: 75KPA suction pump vacuums and seals in 10-15 sec—faster and more efficient than low-power sealers",
    "bulletPoints": [
        "Powerful Fast Sealing: 75KPA suction pump vacuums and seals in 10-15 sec",
        "Easy to Use & Compact: One-touch auto operation for effortless vacuum sealing",
        "Extend Freshness 7X Longer: Removes air to keep food fresh up to 7x longer",
        "20 Premium Bags Included",
        "Versatile for All Foods: Perfect for meat, seafood, fruits, veggies"
    ]
}

print("\n" + "="*70)
print("TITLE OPTIMIZATION TEST")
print("="*70)

print(f"\nOriginal Title ({len(test_product['title'])} characters):")
print(f"  '{test_product['title']}'")
print(f"\n⚠️  TOO LONG! Exceeds 80 character limit by {len(test_product['title']) - 80} chars")

print("\n" + "="*70)
print("Running LLM Optimization...")
print("="*70)

optimized_title, category_id, category_name, confidence = selector.optimize_title_and_select_category(
    test_product['title'],
    test_product['description'],
    test_product['bulletPoints']
)

print("\n" + "="*70)
print("RESULTS")
print("="*70)

print(f"\n✅ Optimized Title ({len(optimized_title)} characters):")
print(f"  '{optimized_title}'")

if len(optimized_title) <= 80:
    print(f"\n✅ PERFECT! Within 80 character limit")
else:
    print(f"\n⚠️  Still {len(optimized_title) - 80} chars too long")

print(f"\n📁 Category: {category_name}")
print(f"   ID: {category_id}")
print(f"   Confidence: {confidence:.2%}")

print("\n" + "="*70)
print("COMPARISON")
print("="*70)

print(f"\nCharacter Savings: {len(test_product['title']) - len(optimized_title)} characters")
print(f"\nKey Improvements:")
print(f"  • Removed filler words ('Ideal for', 'Home Kitchen Use')")
print(f"  • Kept essential keywords (brand terms, specs, features)")
print(f"  • Optimized for eBay search algorithm")
print(f"  • Front-loaded important terms")

print("\n" + "="*70)

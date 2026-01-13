"""
Test script to verify enhanced aspect filling (required + recommended)
"""
import logging
from semantic_category_selector import SemanticCategorySelector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_enhanced_aspects():
    print("\n" + "="*70)
    print("Testing Enhanced Aspect Filling (Required + Recommended)")
    print("="*70)

    selector = SemanticCategorySelector()

    # Test product with rich details
    test_product = {
        "title": "Stainless Steel Kitchen Knife Set 15-Piece with Wooden Block",
        "description": "Professional chef knife set made from high-carbon stainless steel. Includes 8-inch chef knife, bread knife, utility knife, paring knives, and kitchen shears. Comes with wooden storage block.",
        "bulletPoints": [
            "15-piece complete knife set",
            "High-carbon stainless steel blades",
            "Ergonomic wooden handles",
            "Includes wooden storage block",
            "Dishwasher safe"
        ],
        "specifications": {
            "Material": "Stainless Steel",
            "Color": "Silver with Wood Handles",
            "Set Size": "15 pieces"
        }
    }

    # Step 1: Get category
    print("\n[Step 1] Getting category...")
    optimized_title, brand, category_id, category_name, confidence = selector.optimize_title_and_select_category(
        test_product["title"],
        test_product["description"],
        test_product["bulletPoints"],
        test_product["specifications"]
    )
    print(f"  Category: {category_name} (ID: {category_id})")
    print(f"  Optimized Title: {optimized_title}")
    print(f"  Brand: {brand}")

    # Step 2: Get requirements
    print("\n[Step 2] Fetching category requirements...")
    requirements = selector.get_category_requirements(category_id)

    required_count = len(requirements.get('required', []))
    recommended_count = len(requirements.get('recommended', []))

    print(f"  Required: {required_count}")
    print(f"  Recommended: {recommended_count}")

    if required_count > 0:
        print("\n  Required Aspects:")
        for aspect in requirements['required']:
            print(f"    - {aspect['name']} ({aspect['mode']}, {aspect['cardinality']})")

    if recommended_count > 0:
        print("\n  Recommended Aspects:")
        for aspect in requirements['recommended'][:10]:  # Show first 10
            print(f"    - {aspect['name']} ({aspect['mode']}, {aspect['cardinality']})")
        if recommended_count > 10:
            print(f"    ... and {recommended_count - 10} more")

    # Step 3: Fill aspects WITHOUT recommended
    print("\n[Step 3a] Filling ONLY required aspects (old behavior)...")
    product_data = {
        'title': optimized_title,
        'description': test_product['description'],
        'bulletPoints': test_product['bulletPoints'],
        'specifications': test_product['specifications']
    }

    filled_aspects_old = selector.fill_category_requirements(
        product_data,
        requirements,
        include_recommended=False
    )
    print(f"  Filled {len(filled_aspects_old)} aspects")
    for name, value in filled_aspects_old.items():
        print(f"    - {name}: {value}")

    # Step 4: Fill aspects WITH recommended
    print("\n[Step 3b] Filling required + recommended aspects (NEW behavior)...")
    filled_aspects_new = selector.fill_category_requirements(
        product_data,
        requirements,
        include_recommended=True
    )
    print(f"  Filled {len(filled_aspects_new)} aspects")
    for name, value in filled_aspects_new.items():
        print(f"    - {name}: {value}")

    # Step 5: Compare results
    print("\n[Comparison]")
    print(f"  Old approach: {len(filled_aspects_old)} aspects")
    print(f"  New approach: {len(filled_aspects_new)} aspects")
    print(f"  Additional aspects filled: {len(filled_aspects_new) - len(filled_aspects_old)}")

    new_aspects = set(filled_aspects_new.keys()) - set(filled_aspects_old.keys())
    if new_aspects:
        print(f"\n  New aspects added (from recommended list):")
        for aspect in new_aspects:
            print(f"    - {aspect}: {filled_aspects_new[aspect]}")

    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70)

if __name__ == "__main__":
    test_enhanced_aspects()

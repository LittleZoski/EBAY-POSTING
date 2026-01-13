"""
Test category selection for Tiuedu Astaxanthin product
"""
import logging
from semantic_category_selector import SemanticCategorySelector

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_astaxanthin_category():
    print("\n" + "="*70)
    print("Testing Tiuedu Astaxanthin Category Selection")
    print("="*70)

    selector = SemanticCategorySelector()

    # Exact product data from the file
    product = {
        "title": "Tiuedu Astaxanthin 12mg, 120 Softgels, 4 Month Supply, Astaxanthin Antioxidant Supplements, Supports Eye, Joint, Internal Circulation, Skin Health",
        "description": "Astaxanthin 12mg, 120 Softgels, 4 Month Supply",
        "bulletPoints": [
            "Each capsule contains 12mg of natural astaxanthin,high Concentration Astaxanthin.",
            "Natural microalgae source + pure formula, safe and easily absorbed.",
            "Utilizing coconut oil-based soft capsules, increases the absorption rate of astaxanthin.",
            "Support skin,heart,Joints and eyes health, multi-functional health support.",
            "120-pill package, 1 pill per day can be taken continuously for 4 months."
        ],
        "specifications": {}
    }

    # Test 1: Get top category matches to see vector DB results
    print("\n[Step 1] Getting top 5 category matches from Vector DB...")
    matches = selector.get_top_category_matches(
        product["title"],
        product["description"],
        top_k=5
    )

    print("\nTop 5 Vector DB Matches:")
    for i, match in enumerate(matches, 1):
        print(f"  {i}. {match['name']} (ID: {match['category_id']})")
        print(f"     Similarity: {match['similarity_score']:.4f}")
        print(f"     Path: {match['path']}")
        print()

    # Test 2: LLM final selection
    print("\n[Step 2] LLM optimizing title and picking final category...")
    optimized_title, brand, category_id, category_name, confidence = selector.optimize_title_and_select_category(
        product["title"],
        product["description"],
        product["bulletPoints"],
        product["specifications"]
    )

    print(f"\nFinal LLM Selection:")
    print(f"  Category: {category_name} (ID: {category_id})")
    print(f"  Optimized Title: {optimized_title}")
    print(f"  Brand: {brand}")
    print(f"  Confidence: {confidence:.4f}")

    # Test 3: Check if "Pet Supplies" appears anywhere
    print("\n[Step 3] Checking for Pet Supplies in results...")
    pet_supply_matches = [m for m in matches if 'Pet' in m['name'] or 'pet' in m['name'].lower()]

    if pet_supply_matches:
        print("  WARNING: Pet Supplies found in top matches:")
        for match in pet_supply_matches:
            print(f"    - {match['name']} (Similarity: {match['similarity_score']:.4f})")
    else:
        print("  No Pet Supplies categories in top 5 matches.")

    print("\n" + "="*70)
    print("Analysis Complete")
    print("="*70)

if __name__ == "__main__":
    test_astaxanthin_category()

"""
Quick test to explore how the vector DB matches pet products
Run this to see semantic search in action!
"""
from semantic_category_selector import SemanticCategorySelector

selector = SemanticCategorySelector()

# Test products from your file
test_products = [
    "OLLY Ultra Strength Softgels, Healthy Hair, Skin, Nails with Biotin & Vitamins",
    "Dog Treats Training Chicken Flavor Small Breed",
    "Cat Litter Box Automatic Self-Cleaning",
    "Moisturizer Face Cream Anti-Aging Hyaluronic Acid",
    "Windshield Wiper Blades 26 Inch All-Weather"
]

print("="*70)
print("Testing Semantic Category Search")
print("="*70)

for product in test_products:
    print(f"\n{'='*70}")
    print(f"Product: {product}")
    print(f"{'='*70}")

    # Get top 5 matches
    matches = selector.get_top_category_matches(product, top_k=5)

    print("\nTop 5 category matches:")
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match['similarity_score']:.3f} - {match['name']} (Level {match['level']})")
        print(f"   Path: {match['path']}")

    # Get best category
    cat_id, cat_name, confidence = selector.select_category(product)
    print(f"\nSelected: {cat_name} (ID: {cat_id}, confidence: {confidence:.3f})")

print(f"\n{'='*70}")
print("Test Complete!")
print(f"{'='*70}")

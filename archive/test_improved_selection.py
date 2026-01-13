"""
Test the IMPROVED category selection: Vector DB top 3 + LLM picks best
"""
import logging
from semantic_category_selector import SemanticCategorySelector

# Setup logging to see all debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

print("="*70)
print("Testing IMPROVED Category Selection")
print("Vector DB finds top 3 -> LLM picks best based on context")
print("="*70)

selector = SemanticCategorySelector()

# Test cases that were problematic
test_products = [
    {
        "title": "Baby Nail Clipper Kit with Owl Case, Scissors, File, Tweezers",
        "description": "Baby grooming kit for infant nail care",
        "bulletPoints": [
            "Safe baby nail clippers with rounded edges",
            "Includes scissors, file, and tweezers",
            "Cute owl carrying case",
            "Perfect for newborns and toddlers"
        ],
        "specifications": {"Brand": "Generic"}
    },
    {
        "title": "OLLY Ultra Strength Softgels, Healthy Hair, Skin, Nails with Biotin",
        "description": "Beauty supplement with biotin for hair skin and nails",
        "bulletPoints": [
            "Contains biotin for hair health",
            "Supports healthy skin",
            "Vitamins for nail strength"
        ],
        "specifications": {"Brand": "OLLY"}
    },
    {
        "title": "Dog Training Treats Chicken Flavor Small Breed Puppy Snacks",
        "description": "Training treats for dogs",
        "bulletPoints": [
            "Chicken flavor dogs love",
            "Small size for training",
            "High protein"
        ],
        "specifications": {"Brand": "Generic"}
    }
]

for i, product in enumerate(test_products, 1):
    print(f"\n{'='*70}")
    print(f"TEST {i}: {product['title'][:50]}...")
    print(f"{'='*70}")

    # Use the full optimization method (what your listing flow uses)
    optimized_title, brand, cat_id, cat_name, confidence = selector.optimize_title_and_select_category(
        product_title=product['title'],
        product_description=product['description'],
        bullet_points=product['bulletPoints'],
        specifications=product['specifications']
    )

    print(f"\n{'='*70}")
    print(f"RESULTS:")
    print(f"  Optimized Title: {optimized_title}")
    print(f"  Brand: {brand}")
    print(f"  Category: {cat_name}")
    print(f"  Category ID: {cat_id}")
    print(f"  Confidence: {confidence:.3f}")
    print(f"{'='*70}")

print(f"\n{'='*70}")
print("All Tests Complete!")
print(f"{'='*70}")

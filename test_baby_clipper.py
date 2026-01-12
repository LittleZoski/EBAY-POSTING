"""
Test script to verify Baby Nail Clipper gets correct category (NOT pet supplies!)
"""
import logging
from semantic_category_selector import SemanticCategorySelector

# Setup logging to see all debug output
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

print("="*70)
print("Testing Baby Nail Clipper Category Selection")
print("="*70)

selector = SemanticCategorySelector()

# The problematic product
product_title = "Baby Nail Clipper Kit with Owl Case, Scissors, File, Tweezers"
description = "Baby grooming kit for infant nail care"
bullet_points = [
    "Safe baby nail clippers with rounded edges",
    "Includes scissors, file, and tweezers",
    "Cute owl carrying case",
    "Perfect for newborns and toddlers"
]

print(f"\nProduct: {product_title}")
print("\nSearching vector DB for best category match...")
print("-"*70)

# Get category with full logging
cat_id, cat_name, confidence = selector.select_category(
    product_title=product_title,
    product_description=description,
    bullet_points=bullet_points
)

print("-"*70)
print(f"\nFINAL SELECTION:")
print(f"  Category: {cat_name}")
print(f"  Category ID: {cat_id}")
print(f"  Confidence: {confidence:.3f}")
print("\n" + "="*70)

# Also test a pet product to ensure it still works
print("\nTesting pet product for comparison...")
print("="*70)

pet_title = "Dog Training Treats Chicken Flavor Small Breed Puppy Snacks"
cat_id2, cat_name2, confidence2 = selector.select_category(
    product_title=pet_title
)

print("-"*70)
print(f"\nFINAL SELECTION:")
print(f"  Category: {cat_name2}")
print(f"  Category ID: {cat_id2}")
print(f"  Confidence: {confidence2:.3f}")
print("\n" + "="*70)

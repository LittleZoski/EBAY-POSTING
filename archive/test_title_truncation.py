"""
Test title truncation - compare hard truncation vs smart truncation
"""
import sys
import codecs

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from semantic_category_selector import SemanticCategorySelector

def test_title_truncation():
    selector = SemanticCategorySelector()

    # Test case from your actual product
    test_title = "Natural Intestinal Defense for Dogs, Puppies & Cats, Kitten - Herbal Cleanse with Wormwood, Black Walnut - Promotes Healthy Gut - Advanced Broad Spectrum Formula for Large, Medium Small para Perros"

    print("="*80)
    print("Title Truncation Comparison")
    print("="*80)

    print(f"\nOriginal Title ({len(test_title)} chars):")
    print(f"  {test_title}")

    # Old method: Hard truncation [:80]
    hard_truncated = test_title[:80]
    print(f"\n❌ OLD METHOD - Hard Truncation [:80] ({len(hard_truncated)} chars):")
    print(f"  {hard_truncated}")
    print(f"  Problem: Cuts mid-word ('Black' becomes 'Bla')")

    # New method: Smart truncation
    smart_truncated = selector._smart_truncate_title(test_title, 80)
    print(f"\n✅ NEW METHOD - Smart Truncation ({len(smart_truncated)} chars):")
    print(f"  {smart_truncated}")
    print(f"  Benefit: Breaks at word boundary, looks professional")

    # More test cases
    print("\n" + "="*80)
    print("Additional Test Cases")
    print("="*80)

    test_cases = [
        "Dog Food Dry Chicken Flavor Adult Large Breed 30lb Bag with Vitamins Minerals",
        "Sony WH-1000XM5 Wireless Noise Cancelling Headphones with 30 Hour Battery Life",
        "Cat Litter Box Self-Cleaning Automatic Large Hooded Covered Enclosed Privacy"
    ]

    for i, title in enumerate(test_cases, 1):
        print(f"\nTest {i} ({len(title)} chars):")
        if len(title) > 80:
            print(f"  Hard: {title[:80]}")
            print(f"  Smart: {selector._smart_truncate_title(title, 80)}")
        else:
            print(f"  Title: {title}")
            print(f"  (No truncation needed)")

    print("\n" + "="*80)

if __name__ == "__main__":
    test_title_truncation()

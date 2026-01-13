"""
Test brand extraction from various specification field names
"""
import sys
import codecs

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from semantic_category_selector import SemanticCategorySelector

def test_brand_extraction():
    selector = SemanticCategorySelector()

    # Test cases from actual failed products
    test_cases = [
        {
            "name": "Brand Name field (GOLRISEN)",
            "title": "Cat Deterrent Spray 5oz for Indoor Cats",
            "specifications": {
                "ASIN": "B0G1S31S5Z",
                "Brand Name": "GOLRISEN",
                "Color": "Orange"
            },
            "expected": "GOLRISEN"
        },
        {
            "name": "Empty specifications",
            "title": "Dog Diapers Liners, 150 Ct, Super Absorbent",
            "specifications": {},
            "expected": "Dog"  # Should extract from title
        },
        {
            "name": "Brand Name field (Ballsill)",
            "title": "Cat Deterrent Spray Anti-Scratch Furniture",
            "specifications": {
                "ASIN": "B0FWBPJ7C2",
                "Brand Name": "Ballsill",
                "Color": "Orange/Black"
            },
            "expected": "Ballsill"
        },
        {
            "name": "Standard Brand field",
            "title": "Sony Headphones Wireless",
            "specifications": {
                "Brand": "Sony",
                "Model": "WH-1000XM5"
            },
            "expected": "Sony"
        },
        {
            "name": "Manufacturer field",
            "title": "Pet Supplies Dog Food",
            "specifications": {
                "Manufacturer": "Purina",
                "Weight": "30 lbs"
            },
            "expected": "Purina"
        }
    ]

    print("="*70)
    print("Testing Brand Extraction")
    print("="*70)

    passed = 0
    failed = 0

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print(f"  Title: {test['title'][:60]}")
        print(f"  Specifications: {test['specifications']}")

        extracted = selector._extract_brand_simple(test['title'], test['specifications'])

        print(f"  Expected: {test['expected']}")
        print(f"  Extracted: {extracted}")

        if extracted == test['expected']:
            print("  ✓ PASS")
            passed += 1
        else:
            print("  ✗ FAIL")
            failed += 1

    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)

if __name__ == "__main__":
    test_brand_extraction()

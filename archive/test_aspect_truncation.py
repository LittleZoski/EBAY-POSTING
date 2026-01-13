"""
Test aspect value truncation to ensure 65-character limit compliance
"""
import sys
import codecs

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

from llm_category_selector import LLMCategorySelector

def test_truncation():
    selector = LLMCategorySelector()

    # Test cases from actual failures
    test_cases = [
        {
            "name": "Features (128 chars)",
            "input": "SAFE AND GENTLE: The spray is made with plant extracts and contains no alcohol or harsh chemicals. It's suitable for both puppies and adults.",
            "expected_max": 65
        },
        {
            "name": "Dosage (101 chars)",
            "input": "Apply the ear mite drops daily for 7 to 10 days, if necessary, repeat treatment in two weeks.",
            "expected_max": 65
        },
        {
            "name": "Features (304 chars)",
            "input": "BRAND SERVICE : Your satisfaction is our top priority. If you have any questions about sizing or the product, our dedicated customer support team is here to help 24/7. We stand behind the quality of our products and are committed to providing you with an excellent shopping experience.",
            "expected_max": 65
        },
        {
            "name": "Short value (under limit)",
            "input": "Stainless Steel",
            "expected_max": 65
        }
    ]

    print("="*70)
    print("Testing Aspect Value Truncation")
    print("="*70)

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print(f"  Original length: {len(test['input'])} chars")
        print(f"  Original: {test['input'][:80]}...")

        truncated = selector._smart_truncate(test['input'], test['expected_max'])

        print(f"  Truncated length: {len(truncated)} chars")
        print(f"  Truncated: {truncated}")

        if len(truncated) <= test['expected_max']:
            print("  ✓ PASS - Within 65 character limit")
        else:
            print(f"  ✗ FAIL - Exceeds limit by {len(truncated) - test['expected_max']} chars")

    # Test dict validation
    print("\n" + "="*70)
    print("Testing Dictionary Validation")
    print("="*70)

    test_aspects = {
        "Features": "SAFE AND GENTLE: The spray is made with plant extracts and contains no alcohol or harsh chemicals. It's suitable for both puppies and adults.",
        "Dosage": "Apply the ear mite drops daily for 7 to 10 days, if necessary, repeat treatment in two weeks.",
        "Brand": "Generic",  # Already short
        "Color": ["Red", "Very long color description that exceeds sixty-five characters and needs truncation"]
    }

    print("\nOriginal aspects:")
    for key, val in test_aspects.items():
        if isinstance(val, list):
            print(f"  {key}: {val}")
        else:
            print(f"  {key}: {val[:80]}... ({len(val)} chars)")

    validated = selector._validate_and_truncate_aspects(test_aspects)

    print("\nValidated aspects:")
    for key, val in validated.items():
        if isinstance(val, list):
            print(f"  {key}: {val}")
            for v in val:
                if isinstance(v, str):
                    print(f"    - Length: {len(v)} chars")
        else:
            print(f"  {key}: {val} ({len(val)} chars)")

    # Check all values are within limit
    print("\n" + "="*70)
    print("Final Validation Check")
    print("="*70)

    all_valid = True
    for key, val in validated.items():
        if isinstance(val, list):
            for v in val:
                if isinstance(v, str) and len(v) > 65:
                    print(f"  ✗ FAIL - {key}: '{v}' exceeds 65 chars ({len(v)})")
                    all_valid = False
        elif isinstance(val, str) and len(val) > 65:
            print(f"  ✗ FAIL - {key}: '{val}' exceeds 65 chars ({len(val)})")
            all_valid = False

    if all_valid:
        print("  ✓ ALL VALUES PASS - All aspects within 65 character limit!")

    print("\n" + "="*70)

if __name__ == "__main__":
    test_truncation()

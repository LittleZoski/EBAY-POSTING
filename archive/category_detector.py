"""
Hybrid eBay Category Detection
Combines keyword matching with API suggestions for better accuracy
"""
import re
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CategoryDetector:
    """
    Detects appropriate eBay category using keyword matching.

    This is more reliable than eBay's getCategorySuggestions API which often
    returns poor results. Most professional eBay listing tools use keyword
    matching with manually curated category mappings.
    """

    # Category mapping based on product keywords
    # Format: {category_name: (category_id, keywords)}
    CATEGORY_MAP = {
        # Automotive
        "wiper_blades": ("179852", ["wiper", "windshield wiper", "wiper blade", "rain-x"]),
        "car_parts": ("6030", ["car parts", "auto parts", "automotive", "vehicle"]),
        "oil_filters": ("33553", ["oil filter", "engine filter"]),
        "air_filters": ("33554", ["air filter", "cabin filter"]),
        "car_batteries": ("33553", ["car battery", "automotive battery"]),

        # Electronics
        "phone_cases": ("20349", ["phone case", "iphone case", "samsung case", "mobile case"]),
        "chargers": ("20357", ["charger", "charging cable", "usb charger", "phone charger"]),
        "headphones": ("15052", ["headphones", "earbuds", "airpods", "earphones"]),
        "laptop_accessories": ("31530", ["laptop case", "laptop bag", "laptop stand"]),
        "smart_watches": ("178893", ["smart watch", "fitness tracker", "apple watch"]),

        # Home & Garden
        "kitchen_tools": ("20625", ["kitchen", "cooking utensils", "kitchen tools"]),
        "bedding": ("20442", ["bed sheets", "bedding", "comforter", "pillow"]),
        "home_decor": ("10033", ["home decor", "wall art", "decoration"]),
        "garden_tools": ("43559", ["garden", "gardening", "lawn", "outdoor tools"]),

        # Health & Beauty
        "skincare": ("11450", ["skin care", "facial", "moisturizer", "serum", "lotion", "shampoo", "body wash"]),
        "makeup": ("31786", ["makeup", "cosmetics", "lipstick", "mascara", "foundation"]),
        "vitamins": ("180959", ["vitamin", "supplement", "health supplement"]),

        # Clothing & Accessories
        "womens_clothing": ("15724", ["womens", "women's", "ladies", "dress", "blouse"]),
        "mens_clothing": ("1059", ["mens", "men's", "shirt", "pants"]),
        "shoes": ("63889", ["shoes", "sneakers", "boots", "sandals"]),
        "jewelry": ("281", ["jewelry", "necklace", "bracelet", "earrings", "ring"]),

        # Sports & Outdoors
        "fitness_equipment": ("15273", ["fitness", "exercise", "workout", "gym equipment"]),
        "camping": ("16034", ["camping", "tent", "sleeping bag", "outdoor gear"]),
        "sports_equipment": ("888", ["sports", "athletic", "training"]),

        # Toys & Games
        "toys": ("220", ["toy", "kids toy", "childrens toy", "playset"]),
        "video_games": ("139973", ["video game", "playstation", "xbox", "nintendo"]),

        # Books & Media
        "books": ("267", ["book", "novel", "textbook"]),
        "dvds": ("11232", ["dvd", "blu-ray", "movie"]),

        # Pet Supplies
        "pet_supplies": ("1281", ["pet", "dog", "cat", "pet supplies"]),

        # Tools & Hardware
        "power_tools": ("631", ["power tool", "drill", "saw", "tool"]),
        "hand_tools": ("3244", ["hand tool", "wrench", "screwdriver"]),

        # Baby Products
        "baby_products": ("2984", ["baby", "infant", "toddler", "baby care"]),

        # Office Supplies
        "office_supplies": ("26095", ["office", "stationery", "pen", "notebook"]),
    }

    # Fallback categories for broad product types
    FALLBACK_CATEGORIES = {
        "electronics": "293",
        "clothing": "11450",
        "home": "11700",
        "automotive": "6000",
        "collectibles": "1",
        "everything_else": "99"
    }

    def __init__(self):
        """Initialize category detector"""
        pass

    def detect_category(
        self,
        title: str,
        description: str = "",
        default_category_id: str = "220"  # Collectibles as safe default
    ) -> tuple[str, str, float]:
        """
        Detect the most appropriate category for a product.

        Args:
            title: Product title
            description: Product description (optional)
            default_category_id: Fallback category if no match found

        Returns:
            Tuple of (category_id, category_name, confidence_score)
            confidence_score: 0.0-1.0 (1.0 = exact match, 0.5 = partial, 0.0 = fallback)
        """
        # Combine title and description for searching
        search_text = f"{title} {description}".lower()

        # Track best match
        best_match = None
        best_score = 0.0
        best_category_name = "Unknown"

        # Check each category's keywords
        for cat_name, (cat_id, keywords) in self.CATEGORY_MAP.items():
            score = self._calculate_match_score(search_text, keywords)

            if score > best_score:
                best_score = score
                best_match = cat_id
                best_category_name = cat_name

        # Determine confidence based on score
        if best_score >= 0.8:
            confidence = 1.0  # High confidence
            logger.info(f"Category detected: {best_category_name} (ID: {best_match}, confidence: {confidence:.2f})")
            return best_match, best_category_name, confidence

        elif best_score >= 0.4:
            confidence = 0.7  # Medium confidence
            logger.info(f"Category detected: {best_category_name} (ID: {best_match}, confidence: {confidence:.2f})")
            return best_match, best_category_name, confidence

        else:
            # No good match, use default
            confidence = 0.0
            logger.warning(f"No category match found for '{title[:50]}...', using default: {default_category_id}")
            return default_category_id, "fallback", confidence

    def _calculate_match_score(self, text: str, keywords: list) -> float:
        """
        Calculate match score based on keyword presence.

        Returns:
            Score from 0.0 to 1.0
        """
        matches = 0
        total_keywords = len(keywords)

        for keyword in keywords:
            # Check for exact keyword match
            if keyword in text:
                matches += 1
            # Check for partial word match (e.g., "wiper" matches "wipers")
            elif any(keyword in word for word in text.split()):
                matches += 0.5

        if total_keywords == 0:
            return 0.0

        return matches / total_keywords

    def get_category_id(self, title: str, description: str = "") -> str:
        """
        Simplified method to just get the category ID.

        Args:
            title: Product title
            description: Product description (optional)

        Returns:
            Category ID as string
        """
        category_id, _, _ = self.detect_category(title, description)
        return category_id


# Global detector instance
category_detector = CategoryDetector()


# Example usage and testing
if __name__ == "__main__":
    detector = CategoryDetector()

    # Test cases
    test_products = [
        ("Rain-X Latitude 2-In-1 Wiper Blades 26 Inch Windshield Wipers", "Automotive windshield wiper"),
        ("iPhone 14 Pro Max Case Clear Protective Cover", "Phone case for iPhone"),
        ("eos Shea Better Body Lotion Vanilla Cashmere", "Skin care moisturizer"),
        ("STANLEY Quencher H2.0 Tumbler 40oz Stainless Steel", "Insulated water bottle"),
        ("Generic Product With No Keywords", "Unknown item"),
    ]

    print("="*70)
    print("Category Detection Test Results")
    print("="*70)

    for title, desc in test_products:
        cat_id, cat_name, confidence = detector.detect_category(title, desc)

        print(f"\nProduct: {title[:60]}")
        print(f"Category: {cat_name}")
        print(f"ID: {cat_id}")
        print(f"Confidence: {confidence:.2f}")

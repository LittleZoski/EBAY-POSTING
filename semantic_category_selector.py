"""
Semantic Category Selector - NO LLM needed!
Uses local vector database for fast, free category matching.
Falls back to LLM only if needed (e.g., for requirements filling).
"""
import logging
from typing import Dict, List, Optional, Tuple
from vector_category_db import VectorCategoryDB
from llm_category_selector import LLMCategorySelector

logger = logging.getLogger(__name__)


class SemanticCategorySelector:
    """
    Hybrid category selector that uses vector DB first, LLM as fallback.

    Cost Optimization:
    - Vector DB semantic search: FREE, instant
    - LLM only used for: title optimization, brand extraction, requirements filling
    - NO LLM calls for category selection!
    """

    def __init__(self, use_llm_fallback: bool = True):
        """
        Initialize semantic selector.

        Args:
            use_llm_fallback: If True, use LLM if vector DB fails (default: True)
        """
        # Initialize vector database
        self.vector_db = VectorCategoryDB()

        # Check if vector DB is initialized (FAISS uses index and category_metadata)
        if self.vector_db.index is None or len(self.vector_db.category_metadata) == 0:
            logger.warning("Vector database not initialized! Run: python vector_category_db.py")
            logger.warning("Initializing now...")
            self.vector_db.initialize_from_cache()

        # Optional LLM fallback
        self.use_llm_fallback = use_llm_fallback
        self.llm_selector = None
        if use_llm_fallback:
            try:
                self.llm_selector = LLMCategorySelector()
                logger.info("LLM fallback enabled")
            except Exception as e:
                logger.warning(f"LLM fallback not available: {e}")
                self.use_llm_fallback = False

    def select_category(self, product_title: str, product_description: str = "",
                       bullet_points: List[str] = None, min_similarity: float = 0.5) -> Tuple[str, str, float]:
        """
        Select category using semantic search (NO LLM call!).

        Args:
            product_title: Product title
            product_description: Product description (optional, improves matching)
            bullet_points: Product bullet points (optional, improves matching)
            min_similarity: Minimum similarity threshold (0-1, default 0.5)

        Returns:
            Tuple of (category_id, category_name, confidence_score)
        """
        logger.info(f"Semantic search for category: {product_title[:60]}...")

        # Build enhanced description from bullet points
        enhanced_description = product_description
        if bullet_points:
            # Add first few bullet points to description for better context
            bullets_text = " ".join(bullet_points[:3])
            enhanced_description = f"{product_description} {bullets_text}".strip()

        try:
            # Use vector DB semantic search - FREE and FAST!
            # First get top 5 to show alternatives
            top_matches = self.vector_db.search_category(
                product_title=product_title,
                product_description=enhanced_description,
                top_k=5
            )

            logger.info(f"  Top 5 Vector DB matches:")
            for i, match in enumerate(top_matches[:5], 1):
                logger.info(f"    {i}. {match['similarity_score']:.3f} - {match['name']} (ID: {match['category_id']})")

            # Get best match
            if top_matches:
                best = top_matches[0]
                category_id = best['category_id']
                category_name = best['name']
                similarity = best['similarity_score']

                logger.info(f"  SELECTED: {category_name} (ID: {category_id}, similarity: {similarity:.3f})")

                return category_id, category_name, similarity
            else:
                logger.warning("No matches found in vector DB")
                raise Exception("No category matches found")

        except Exception as e:
            logger.error(f"Vector DB search failed: {e}")

            # Fallback to LLM if enabled
            if self.use_llm_fallback and self.llm_selector:
                logger.warning("Falling back to LLM category selection...")
                return self.llm_selector.select_category(
                    product_title, product_description, bullet_points
                )
            else:
                # Ultimate fallback
                logger.error("No fallback available, using default category")
                return "360", "Art Prints", 0.3

    def optimize_title_and_select_category(self, product_title: str, product_description: str = "",
                                           bullet_points: List[str] = None, specifications: Dict = None,
                                           use_llm_for_title: bool = True) -> Tuple[str, str, str, str, float]:
        """
        IMPROVED Hybrid approach:
        - Vector DB: Get top 3 most semantically similar categories (fast, free)
        - LLM: Pick best category from top 3 + optimize title + extract brand (accurate, cheap)

        Args:
            product_title: Original product title
            product_description: Product description
            bullet_points: Product bullet points
            specifications: Product specifications
            use_llm_for_title: If True, use LLM for title optimization (default: True)

        Returns:
            Tuple of (optimized_title, brand, category_id, category_name, confidence_score)
        """
        logger.info(f"Optimizing title and selecting category for: {product_title[:60]}...")

        # STEP 1: Get top K categories from Vector DB for LLM analysis
        # Configurable via settings.category_candidates_top_k (default: 3)
        from config import settings

        top_k = getattr(settings, 'category_candidates_top_k', 3)

        # Build enhanced query for better semantic matching
        # Priority: Title > Key Features (bullets) > Description
        # Vector DB will internally construct: title + " " + enhanced_description
        enhanced_description_parts = []

        # Add first 5 bullet points (key features are very informative)
        if bullet_points:
            # Bullet points often contain target audience info like "for adults", "pet-safe", etc.
            bullets_text = " ".join(bullet_points[:5])
            enhanced_description_parts.append(bullets_text)

        # Add description (but limit to avoid noise)
        if product_description:
            enhanced_description_parts.append(product_description[:300])

        enhanced_description = " ".join(enhanced_description_parts).strip()

        logger.debug(f"Vector DB query: title ({len(product_title)} chars) + enhanced ({len(enhanced_description)} chars)")

        try:
            top_matches = self.vector_db.search_category(
                product_title=product_title,
                product_description=enhanced_description,  # Bullets + description (title added by vector DB)
                top_k=top_k
            )

            logger.info(f"  Top {top_k} Vector DB candidates:")
            for i, match in enumerate(top_matches[:top_k], 1):
                logger.info(f"    {i}. {match['similarity_score']:.3f} - {match['name']} (ID: {match['category_id']})")

            if not top_matches:
                raise Exception("No category matches found in vector DB")

        except Exception as e:
            logger.error(f"Vector DB search failed: {e}")
            # Fallback to simple category
            top_matches = [{'category_id': '360', 'name': 'Art Prints', 'similarity_score': 0.3, 'path': 'Art > Art Prints'}]

        # STEP 2: LLM picks best category from top K + optimizes title + extracts brand
        if use_llm_for_title and self.llm_selector:
            logger.info(f"  LLM analyzing product context and picking best category from top {top_k}...")

            try:
                optimized_title, brand, selected_category_id = self._llm_optimize_title_brand_and_pick_category(
                    product_title, product_description, bullet_points, specifications, top_matches
                )

                # Find the selected category details
                category_name = None
                confidence = 0.0
                for match in top_matches:
                    if match['category_id'] == selected_category_id:
                        category_name = match['name']
                        confidence = match['similarity_score']
                        break

                if not category_name:
                    # LLM picked something not in top 3? Use first match
                    logger.warning(f"LLM selected category {selected_category_id} not in top 3, using first match")
                    category_name = top_matches[0]['name']
                    selected_category_id = top_matches[0]['category_id']
                    confidence = top_matches[0]['similarity_score']

            except Exception as e:
                logger.error(f"LLM optimization failed: {e}")
                # Fallback to first vector DB match
                optimized_title = product_title[:77] + "..." if len(product_title) > 80 else product_title
                brand = self._extract_brand_simple(product_title, specifications)
                selected_category_id = top_matches[0]['category_id']
                category_name = top_matches[0]['name']
                confidence = top_matches[0]['similarity_score']
        else:
            # Simple fallback: use first vector DB match
            optimized_title = product_title[:77] + "..." if len(product_title) > 80 else product_title
            brand = self._extract_brand_simple(product_title, specifications)
            selected_category_id = top_matches[0]['category_id']
            category_name = top_matches[0]['name']
            confidence = top_matches[0]['similarity_score']

        logger.info(f"  FINAL SELECTION:")
        logger.info(f"    Optimized Title: {optimized_title}")
        logger.info(f"    Brand: {brand}")
        logger.info(f"    Category: {category_name} (ID: {selected_category_id})")
        logger.info(f"    Similarity Score: {confidence:.3f}")

        return optimized_title, brand, selected_category_id, category_name, confidence

    def _llm_optimize_title_brand_and_pick_category(self, title: str, description: str,
                                                     bullet_points: List[str], specifications: Dict,
                                                     top_categories: List[Dict]) -> Tuple[str, str, str]:
        """
        IMPROVED: Use LLM for title, brand, AND picking best category from top K vector DB results.
        This combines vector DB speed with LLM reasoning for maximum accuracy.

        Returns:
            Tuple of (optimized_title, brand, selected_category_id)
        """
        import json
        from anthropic import Anthropic
        from config import settings

        client = Anthropic(api_key=settings.anthropic_api_key)

        bullet_text = "\n".join(bullet_points[:3]) if bullet_points else "N/A"
        desc_text = description[:200] if description else "N/A"
        specs_text = json.dumps(specifications, indent=2) if specifications else "N/A"

        # Format top categories for LLM (number determined by settings.category_candidates_top_k)
        top_k = len(top_categories)
        categories_info = []
        for i, cat in enumerate(top_categories, 1):
            categories_info.append({
                "id": cat['category_id'],
                "name": cat['name'],
                "path": cat['path'],
                "similarity_score": cat['similarity_score']
            })
        categories_json = json.dumps(categories_info, indent=2)

        prompt = f"""You are an eBay listing optimization expert. Perform THREE tasks:

TASK 1: EXTRACT BRAND NAME
- Identify the actual brand/manufacturer from the product data
- Check specifications for: "Brand", "Brand Name", "BrandName", "Manufacturer" fields
- Use context to find the real brand (e.g., in "Waterproof Sony Headphones", brand is "Sony")
- Avoid generic terms like: Custom, Personalized, Handmade, Vintage, New, Unique, etc.
- If no clear brand exists, use "Generic"

TASK 2: OPTIMIZE TITLE (Max 80 characters)
- Make it compelling and keyword-rich for eBay search
- Include brand, key features, and product type
- Front-load important keywords
- Use natural language, avoid keyword stuffing
- MUST be ≤80 characters

TASK 3: SELECT BEST CATEGORY FROM TOP {top_k} CANDIDATES
- You are given the top {top_k} semantically similar categories from vector search
- Review the FULL product context (title, description, features, specs)
- Pick the MOST APPROPRIATE category based on:
  * Product's primary purpose and intended use
  * Target audience (baby/adult/pet/automotive/etc)
  * Specific product type (tool vs toy vs food vs accessory)
  * Category PATH HIERARCHY (check the full path, not just the final category name!)

- CRITICAL: Always examine the ROOT CATEGORY (first level after "Root >") in the path:
  * Common root categories: "Pet Supplies", "Health & Beauty", "Baby", "Home & Garden", "Automotive", "Electronics", etc.
  * The ROOT CATEGORY must match the product's target audience/domain
  * Example: If final category is "Vitamins & Supplements", check the ROOT:
    - "Root > Pet Supplies > ... > Vitamins & Supplements" = for PETS
    - "Root > Health & Beauty > ... > Vitamins & Supplements" = for HUMANS
  * Example: If product is "Astaxanthin supplement for skin/eye health":
    - WRONG: "Root > Pet Supplies > Dog Supplies > ... > Vitamins & Supplements" (pet root)
    - CORRECT: "Root > Health & Beauty > Vitamins & Lifestyle Supplements > ..." (human root)

- IMPORTANT: High similarity score ≠ correct category!
  * Vector search matches on word overlap, which can be misleading
  * Example: "Baby Nail Clipper" might match "Pet Grooming Clippers" (0.51) due to word overlap,
    but "Manicure & Pedicure Tools" (0.50) is CORRECT based on product context
  * Always prioritize ROOT CATEGORY match over similarity score

- Decision Process:
  1. Identify the product's target domain (human, pet, baby, automotive, etc.)
  2. For each candidate, check if the ROOT CATEGORY matches the target domain
  3. Eliminate candidates with mismatched root categories
  4. From remaining valid candidates, pick the most specific and appropriate one

PRODUCT DATA:
Title: {title}
Description: {desc_text}
Key Features:
{bullet_text}
Specifications:
{specs_text}

TOP {top_k} CANDIDATE CATEGORIES (from vector search):
{categories_json}

ANALYSIS INSTRUCTIONS:
1. Read the product title, description, and features carefully
2. Identify the product's TARGET DOMAIN:
   - Is it for humans? (Health & Beauty, Home & Garden, Clothing, etc.)
   - Is it for pets? (Pet Supplies)
   - Is it for babies? (Baby)
   - Is it for vehicles? (Automotive, Motorcycle)
   - Is it electronics? (Electronics, Computers)
3. For EACH of the {top_k} candidates, examine the ROOT CATEGORY (first level in path):
   - Extract: "Root > [ROOT_CATEGORY] > ..."
   - Does this ROOT match the product's target domain?
   - Example: Human supplement needs "Health & Beauty" root, NOT "Pet Supplies" root
4. ELIMINATE all candidates where ROOT CATEGORY doesn't match target domain
5. From the REMAINING valid candidates, pick the most specific and appropriate sub-category
6. NEVER pick based on highest similarity score alone - ROOT CATEGORY match is mandatory

OUTPUT FORMAT (JSON only, no explanations outside JSON):
{{
  "brand": "extracted brand name or 'Generic'",
  "optimized_title": "your optimized title here (max 80 chars)",
  "category_id": "selected category ID from the {top_k} candidates",
  "reasoning": "1-2 sentence explanation mentioning why the ROOT CATEGORY matches and why this specific path is best"
}}"""

        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text.strip()

        # Parse JSON response
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # Try to extract JSON if wrapped in markdown
            if "```json" in result_text:
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()
                result = json.loads(result_text)
            else:
                raise

        logger.info(f"    LLM Reasoning: {result.get('reasoning', 'N/A')}")

        # Get optimized title and enforce 80 char limit with smart truncation
        optimized_title = result.get('optimized_title', title)
        if len(optimized_title) > 80:
            # Smart truncate: break at word boundary, not mid-word
            optimized_title = self._smart_truncate_title(optimized_title, 80)
            logger.warning(f"    Title exceeded 80 chars, truncated to: {optimized_title}")

        return (
            optimized_title,
            result.get('brand', 'Generic'),
            result.get('category_id', top_categories[0]['category_id'])
        )

    def _smart_truncate_title(self, title: str, max_length: int = 80) -> str:
        """
        Smart truncate title to max_length, breaking at word boundaries.

        Args:
            title: Title to truncate
            max_length: Maximum length (default 80 for eBay)

        Returns:
            Truncated title that ends at a word boundary
        """
        if len(title) <= max_length:
            return title

        # Find the last space before max_length
        truncated = title[:max_length]
        last_space = truncated.rfind(' ')

        if last_space > 0:
            # Truncate at last word boundary
            return title[:last_space].strip()
        else:
            # No space found, hard truncate (rare case)
            return title[:max_length].strip()

    def _extract_brand_simple(self, title: str, specifications: Dict = None) -> str:
        """Simple brand extraction without LLM"""
        # Try to extract from specifications first
        if specifications:
            # Check common brand field names (Amazon uses various names)
            for key in ['Brand', 'brand', 'Brand Name', 'BrandName', 'Manufacturer', 'manufacturer']:
                if key in specifications:
                    brand = specifications[key]
                    if brand and len(brand) > 2:
                        return brand

        # Fallback: use first word of title if it looks like a brand
        first_word = title.split()[0] if title else ""
        if first_word and len(first_word) > 2 and first_word[0].isupper():
            return first_word

        return "Generic"

    def get_category_requirements(self, category_id: str) -> Dict:
        """
        Get category requirements (delegates to LLM selector).
        This doesn't use LLM, just fetches from eBay API.
        """
        if not self.llm_selector:
            logger.warning("LLM selector not available for requirements fetching")
            return {'required': [], 'recommended': [], 'optional': []}

        return self.llm_selector.get_category_requirements(category_id)

    def fill_category_requirements(self, product_data: Dict, requirements: Dict, include_recommended: bool = False) -> Dict:
        """
        Fill category requirements using LLM (delegates to LLM selector).
        This is one of the few places where LLM is genuinely useful.

        Args:
            product_data: Product information
            requirements: Category requirements from get_category_requirements()
            include_recommended: If True, also fill recommended aspects in the same LLM call
        """
        if not self.llm_selector:
            logger.warning("LLM selector not available for requirements filling")
            return {}

        return self.llm_selector.fill_category_requirements(product_data, requirements, include_recommended)

    def get_top_category_matches(self, product_title: str, product_description: str = "",
                                 top_k: int = 5) -> List[Dict]:
        """
        Get top K category matches with similarity scores.
        Useful for debugging or showing alternatives.

        Returns:
            List of dicts with category_id, name, path, level, similarity_score
        """
        enhanced_description = product_description
        return self.vector_db.search_category(product_title, enhanced_description, top_k=top_k)


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("="*70)
    print("Semantic Category Selector Test")
    print("="*70)

    selector = SemanticCategorySelector()

    # Test products
    test_products = [
        {
            "title": "OLLY Ultra Strength Softgels, Healthy Hair, Skin, Nails with Biotin & Vitamins",
            "description": "Beauty supplement with biotin for hair skin and nails",
            "bulletPoints": ["Contains biotin", "Supports healthy hair", "Vitamins included"]
        },
        {
            "title": "Dog Food Dry Chicken Flavor Adult Large Breed 30lb Bag",
            "description": "Premium dog food for large breeds",
            "bulletPoints": ["Chicken flavor", "Large breed formula", "30 pound bag"]
        },
        {
            "title": "Rain-X Latitude Windshield Wiper Blades 26 Inch All-Weather",
            "description": "Automotive wiper blades with water repellent technology",
            "bulletPoints": ["26 inch size", "All-weather", "Water repellent"]
        }
    ]

    for product in test_products:
        print(f"\n{'='*70}")
        print(f"Product: {product['title'][:60]}...")
        print(f"{'='*70}")

        # Test semantic search
        cat_id, cat_name, confidence = selector.select_category(
            product['title'],
            product['description'],
            product['bulletPoints']
        )

        print(f"\nSelected Category: {cat_name}")
        print(f"Category ID: {cat_id}")
        print(f"Confidence: {confidence:.3f}")

        # Show top 3 matches
        print("\nTop 3 matches:")
        matches = selector.get_top_category_matches(product['title'], product['description'], top_k=3)
        for match in matches:
            print(f"  {match['similarity_score']:.3f} - {match['name']}")
            print(f"           Path: {match['path']}")

    print(f"\n{'='*70}")
    print("Test Complete!")
    print(f"{'='*70}")

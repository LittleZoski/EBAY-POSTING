"""
LLM-powered Category Selection and Requirements Handler
Uses Claude Haiku for fast, cost-effective category decisions
"""
import json
import logging
from typing import Dict, List, Optional, Tuple
from anthropic import Anthropic
from config import settings
from category_cache import CategoryCache
import requests

logger = logging.getLogger(__name__)


class LLMCategorySelector:
    """
    Uses Claude LLM to intelligently select categories and fill requirements
    """

    def __init__(self):
        """Initialize with Claude API and category cache"""
        if not settings.anthropic_api_key or settings.anthropic_api_key == "your_claude_api_key_here":
            raise ValueError("ANTHROPIC_API_KEY not configured in .env file")

        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.cache = CategoryCache()
        self.cache.initialize()

        logger.info(f"LLM Category Selector initialized with {len(self.cache.categories)} cached categories")

    def select_category(self, product_title: str, product_description: str = "",
                       bullet_points: List[str] = None) -> Tuple[str, str, float]:
        """
        Use LLM to select the best category for a product.

        Args:
            product_title: Product title (primary input for category selection)
            product_description: Product description (not used - title is sufficient)
            bullet_points: List of product bullet points (not used - title is sufficient)

        Returns:
            Tuple of (category_id, category_name, confidence_score)
        """
        logger.info(f"LLM selecting category for: {product_title[:60]}...")

        # Prepare product information - ONLY use title for category selection
        # Title is sufficient to determine category, reduces token usage significantly
        product_info = {
            "title": product_title
        }

        # Build simplified category list for LLM (only leaf categories)
        leaf_categories = []
        for cat_id, cat_data in self.cache.categories.items():
            if cat_data.get('leaf'):
                path = self.cache.get_category_path(cat_id)
                # Only include categories at reasonable depth (level 2-3 preferred, up to 4)
                level = cat_data.get('level', 0)
                if 2 <= level <= 4:
                    leaf_categories.append({
                        "id": cat_id,
                        "name": cat_data['name'],
                        "path": path,
                        "level": level
                    })

        # Sort by level (prefer level 2-3 categories - less specialized, fewer requirements)
        leaf_categories.sort(key=lambda x: (x['level'], x['name']))

        # Sample across different levels to get diverse categories
        level_2 = [c for c in leaf_categories if c['level'] == 2][:100]
        level_3 = [c for c in leaf_categories if c['level'] == 3][:100]
        level_4 = [c for c in leaf_categories if c['level'] == 4][:50]

        # Combine: prioritize level 2-3, add some level 4
        leaf_categories = level_2 + level_3 + level_4

        # Create prompt for Claude
        prompt = self._build_category_selection_prompt(product_info, leaf_categories)

        try:
            # Call Claude Haiku (fast and cheap)
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,  # Deterministic output
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse response
            result_text = response.content[0].text.strip()
            logger.debug(f"LLM response: {result_text}")

            # Extract JSON from response
            result = json.loads(result_text)

            category_id = result.get('category_id')
            reasoning = result.get('reasoning', '')

            # Validate category exists
            category_info = self.cache.get_category(category_id)
            if not category_info:
                logger.warning(f"LLM selected invalid category {category_id}, using fallback")
                return self._fallback_category_selection(product_title, product_description)

            category_name = category_info['name']
            confidence = result.get('confidence', 0.7)

            logger.info(f"  Selected: {category_name} (ID: {category_id})")
            logger.info(f"  Reasoning: {reasoning}")
            logger.info(f"  Confidence: {confidence}")

            return category_id, category_name, confidence

        except Exception as e:
            logger.error(f"LLM category selection failed: {str(e)}")
            return self._fallback_category_selection(product_title, product_description)

    def _build_category_selection_prompt(self, product_info: Dict, categories: List[Dict]) -> str:
        """Build prompt for category selection - optimized to use only title"""
        categories_json = json.dumps(categories[:100], indent=2)  # Top 100 to keep prompt size reasonable

        return f"""You are an eBay category selection expert. Select the BEST matching category based on the product title.

PRODUCT TITLE: {product_info['title']}

AVAILABLE EBAY CATEGORIES (leaf categories only):
{categories_json}

SELECTION CRITERIA:
1. Choose the MOST SPECIFIC category that accurately describes the product
2. Prefer Level 2-3 categories (less specialized, fewer requirements)
3. Avoid categories with strict requirements unless product clearly matches
4. Consider the product's primary purpose and use case

OUTPUT FORMAT (JSON only, no explanations):
{{
  "category_id": "the category ID",
  "reasoning": "brief 1-sentence explanation",
  "confidence": 0.0-1.0
}}"""

    def _fallback_category_selection(self, title: str, description: str) -> Tuple[str, str, float]:
        """Fallback to simple keyword matching if LLM fails"""
        logger.warning("Using fallback category selection")

        # Search for keywords in title
        keywords = title.lower().split()[:5]
        for keyword in keywords:
            results = self.cache.search_categories(keyword, leaf_only=True)
            if results:
                # Pick first result at level 2-3
                for cat in results:
                    if 2 <= cat.get('level', 0) <= 3:
                        return cat['id'], cat['name'], 0.5

        # Ultimate fallback - Art Prints (360) - minimal requirements
        return "360", "Art Prints", 0.3

    def get_category_requirements(self, category_id: str) -> Dict:
        """
        Fetch category-specific requirements (item aspects) from eBay API.

        Returns:
            Dict with required, recommended, and optional aspects
        """
        logger.info(f"Fetching requirements for category {category_id}...")

        from category_suggester import CategorySuggester

        suggester = CategorySuggester(
            client_id=settings.ebay_app_id,
            client_secret=settings.ebay_cert_id
        )

        token = suggester.get_application_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        url = f"{settings.ebay_api_base_url}/commerce/taxonomy/v1/category_tree/0/get_item_aspects_for_category"
        params = {"category_id": category_id}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)

            if response.status_code == 200:
                data = response.json()
                aspects = data.get('aspects', [])

                # Categorize aspects
                required = []
                recommended = []
                optional = []

                for aspect in aspects:
                    aspect_name = aspect.get('localizedAspectName')
                    constraint = aspect.get('aspectConstraint', {})

                    aspect_info = {
                        'name': aspect_name,
                        'required': constraint.get('aspectRequired', False),
                        'cardinality': constraint.get('itemToAspectCardinality', 'SINGLE'),
                        'mode': constraint.get('aspectMode', 'SELECTION_ONLY'),
                        'data_type': constraint.get('aspectDataType', 'STRING'),
                        'values': [v.get('localizedValue') for v in aspect.get('aspectValues', [])[:50]]
                    }

                    if aspect_info['required']:
                        required.append(aspect_info)
                    elif constraint.get('aspectUsage') == 'RECOMMENDED':
                        recommended.append(aspect_info)
                    else:
                        optional.append(aspect_info)

                logger.info(f"  Found {len(required)} required, {len(recommended)} recommended aspects")

                return {
                    'required': required,
                    'recommended': recommended,
                    'optional': optional
                }

            elif response.status_code == 204:
                logger.info("  No specific requirements for this category")
                return {'required': [], 'recommended': [], 'optional': []}
            else:
                logger.error(f"  Failed to fetch requirements: {response.status_code}")
                return {'required': [], 'recommended': [], 'optional': []}

        except Exception as e:
            logger.error(f"Exception fetching requirements: {str(e)}")
            return {'required': [], 'recommended': [], 'optional': []}

    def fill_category_requirements(self, product_data: Dict, requirements: Dict) -> Dict:
        """
        Use LLM to fill required category-specific fields from product data.

        Args:
            product_data: Product information (title, description, specs, etc.)
            requirements: Category requirements from get_category_requirements()

        Returns:
            Dict of aspect_name -> value mappings
        """
        required = requirements.get('required', [])

        if not required:
            logger.info("No required aspects to fill")
            return {}

        logger.info(f"LLM filling {len(required)} required aspects...")

        # Build prompt
        prompt = self._build_requirements_filling_prompt(product_data, required)

        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = response.content[0].text.strip()
            logger.debug(f"LLM requirements response: {result_text}")

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in result_text:
                # Extract JSON from markdown code block
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()
            elif "```" in result_text:
                # Extract from generic code block
                start = result_text.find("```") + 3
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()

            # Find JSON object boundaries
            if not result_text.startswith("{"):
                # Try to find the first {
                start = result_text.find("{")
                if start >= 0:
                    result_text = result_text[start:]

            # Find the closing brace and trim everything after
            # Handle nested braces by counting
            if result_text.startswith("{"):
                brace_count = 0
                for i, char in enumerate(result_text):
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            # Found the closing brace
                            result_text = result_text[:i+1]
                            break

            # Parse JSON response
            filled_aspects = json.loads(result_text)

            logger.info(f"  Filled aspects: {list(filled_aspects.keys())}")

            return filled_aspects

        except json.JSONDecodeError as e:
            logger.error(f"LLM requirements filling - JSON parse error: {str(e)}")
            logger.error(f"  Response text: {result_text[:200]}...")
            # Return empty dict - will let eBay validation handle it
            return {}
        except Exception as e:
            logger.error(f"LLM requirements filling failed: {str(e)}")
            # Return empty dict - will let eBay validation handle it
            return {}

    def _build_requirements_filling_prompt(self, product_data: Dict, required_aspects: List[Dict]) -> str:
        """Build prompt for filling requirements - optimized to use only essential data"""
        aspects_info = []
        for aspect in required_aspects:
            aspect_desc = {
                'name': aspect['name'],
                'mode': aspect['mode'],
                'cardinality': aspect['cardinality']
            }
            if aspect.get('values') and aspect['mode'] != 'FREE_TEXT':
                aspect_desc['allowed_values'] = aspect['values'][:20]  # Limit for prompt size
            aspects_info.append(aspect_desc)

        # Only use title, description, and bullet points (skip full specifications to save tokens)
        bullet_points = product_data.get('bulletPoints', [])[:3]  # Only first 3 bullet points
        description = product_data.get('description', '')[:300]  # Truncate description

        return f"""You are filling out required eBay listing fields based on product information.

PRODUCT DATA:
Title: {product_data.get('title', '')}
Description: {description}
Key Features: {json.dumps(bullet_points)}

REQUIRED ASPECTS TO FILL:
{json.dumps(aspects_info, indent=2)}

INSTRUCTIONS:
1. Extract appropriate values from product data for each required aspect
2. If mode is SELECTION_ONLY, MUST use one of the allowed_values
3. If mode is FREE_TEXT, extract from product information
4. If cardinality is MULTI, return array. If SINGLE, return string
5. If information not available, use best reasonable default

OUTPUT FORMAT (JSON only):
{{
  "aspect_name": "value",
  "another_aspect": ["value1", "value2"],
  ...
}}"""


# Example usage
if __name__ == "__main__":
    import sys

    selector = LLMCategorySelector()

    # Test with windshield wiper
    test_product = {
        "title": "Rain-X Latitude 2-In-1 Wiper Blades 26 Inch Windshield Wipers",
        "description": "Patented water repellent formula for automotive windshield",
        "bulletPoints": [
            "26 inch wiper blade",
            "Water repellent technology",
            "Universal fit",
            "All-weather performance"
        ],
        "specifications": {
            "Brand": "Rain-X",
            "Item Length": "26 Inches",
            "Model": "5079281-2"
        }
    }

    print("="*70)
    print("LLM Category Selection Test")
    print("="*70)

    # Select category
    cat_id, cat_name, confidence = selector.select_category(
        test_product['title'],
        test_product['description'],
        test_product['bulletPoints']
    )

    print(f"\nSelected Category: {cat_name} (ID: {cat_id})")
    print(f"Confidence: {confidence}")

    # Get requirements
    requirements = selector.get_category_requirements(cat_id)
    print(f"\nRequired aspects: {len(requirements['required'])}")
    for aspect in requirements['required']:
        print(f"  - {aspect['name']} ({aspect['mode']}, {aspect['cardinality']})")

    # Fill requirements
    if requirements['required']:
        print("\nFilling requirements with LLM...")
        filled = selector.fill_category_requirements(test_product, requirements)
        print(f"\nFilled values:")
        print(json.dumps(filled, indent=2))

    print("\n" + "="*70)

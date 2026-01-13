"""
LLM-powered Category Selection and Requirements Handler
Uses Claude Haiku for fast, cost-effective category decisions
"""
import json
import logging
from pathlib import Path
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

    def _load_priority_category_ids(self) -> set:
        """Load priority category IDs from priority_categories.json based on configured groups"""
        priority_file = Path("priority_categories.json")
        if not priority_file.exists():
            logger.warning("priority_categories.json not found, no priority categories will be used")
            return set()

        try:
            with open(priority_file, 'r', encoding='utf-8') as f:
                priority_data = json.load(f)

            # Get configured groups from settings
            configured_groups = settings.get_priority_category_groups()
            if not configured_groups:
                logger.info("No priority category groups configured in .env")
                return set()

            # Collect category IDs from all configured groups
            priority_ids = set()
            for group_name in configured_groups:
                if group_name in priority_data:
                    group_cats = priority_data[group_name].get('categories', [])
                    for cat in group_cats:
                        priority_ids.add(cat['id'])
                    logger.info(f"Loaded {len(group_cats)} priority categories from group '{group_name}'")
                else:
                    logger.warning(f"Priority group '{group_name}' not found in priority_categories.json")

            logger.info(f"Total priority categories loaded: {len(priority_ids)}")
            return priority_ids

        except Exception as e:
            logger.error(f"Error loading priority categories: {e}")
            return set()

    def optimize_title_and_select_category(self, product_title: str, product_description: str = "",
                                           bullet_points: List[str] = None, specifications: Dict = None) -> Tuple[str, str, str, str, float]:
        """
        COST-EFFICIENT: Use single LLM call for THREE tasks:
        1. Optimize title (80 chars max)
        2. Select category
        3. Extract brand name

        Args:
            product_title: Original Amazon product title
            product_description: Product description
            bullet_points: List of product bullet points
            specifications: Product specifications dict

        Returns:
            Tuple of (optimized_title, brand, category_id, category_name, confidence_score)
        """
        logger.info(f"LLM optimizing title and selecting category for: {product_title[:60]}...")

        # Build simplified category list
        leaf_categories = self._get_leaf_categories()

        # Create combined prompt for title optimization + category selection + brand extraction
        prompt = self._build_combined_prompt(product_title, product_description, bullet_points, specifications, leaf_categories)

        try:
            # Single LLM call for THREE tasks (cost-efficient!)
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=700,
                temperature=0.3,  # Slight creativity for title optimization
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = response.content[0].text.strip()
            logger.debug(f"LLM response: {result_text}")

            # Parse response
            result = json.loads(result_text)

            # Get optimized title and enforce 80 char limit with smart truncation
            optimized_title = result.get('optimized_title', product_title)
            if len(optimized_title) > 80:
                # Smart truncate: break at word boundary, not mid-word
                optimized_title = self._smart_truncate_title(optimized_title, 80)
                logger.warning(f"  Title exceeded 80 chars, truncated to: {optimized_title}")

            brand = result.get('brand', 'Generic')
            category_id = result.get('category_id')
            reasoning = result.get('reasoning', '')

            # Validate and clean brand
            brand = self._validate_brand(brand)

            # Validate category exists
            category_info = self.cache.get_category(category_id)
            if not category_info:
                logger.warning(f"LLM selected invalid category {category_id}, using fallback")
                category_id, category_name, confidence = self._fallback_category_selection(product_title, product_description)
                # Still use the optimized title and brand
                return optimized_title, brand, category_id, category_name, confidence

            category_name = category_info['name']
            confidence = result.get('confidence', 0.7)

            logger.info(f"  Optimized Title: {optimized_title}")
            logger.info(f"  Extracted Brand: {brand}")
            logger.info(f"  Selected Category: {category_name} (ID: {category_id})")
            logger.info(f"  Reasoning: {reasoning}")
            logger.info(f"  Confidence: {confidence}")

            return optimized_title, brand, category_id, category_name, confidence

        except Exception as e:
            logger.error(f"LLM optimization failed: {str(e)}")
            # Fallback: truncate title, use Generic brand, and fallback category
            truncated_title = product_title[:77] + "..." if len(product_title) > 80 else product_title
            category_id, category_name, confidence = self._fallback_category_selection(product_title, product_description)
            return truncated_title, "Generic", category_id, category_name, confidence

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

    def _get_leaf_categories(self) -> List[Dict]:
        """
        Get optimized list of leaf categories with smart sampling.

        Strategy:
        1. ALWAYS include priority categories from priority_categories.json
        2. Use stratified sampling across alphabetical ranges (not just A-Z start)
        3. Target ~300 total categories for better coverage
        """
        # Load priority category IDs from JSON file based on configured groups
        priority_ids = self._load_priority_category_ids()

        # Build full category list
        all_categories = []
        priority_categories = []

        for cat_id, cat_data in self.cache.categories.items():
            if not cat_data.get('leaf'):
                continue

            level = cat_data.get('level', 0)
            if level < 2 or level > 4:
                continue

            cat_dict = {
                "id": cat_id,
                "name": cat_data['name'],
                "path": self.cache.get_category_path(cat_id),
                "level": level
            }

            # Separate priority categories
            if cat_id in priority_ids:
                priority_categories.append(cat_dict)
            else:
                all_categories.append(cat_dict)

        # Group remaining categories by level
        by_level = {}
        for cat in all_categories:
            by_level.setdefault(cat['level'], []).append(cat)

        # Smart sampling: take evenly spaced categories (not alphabetically biased)
        def stratified_sample(categories: List[Dict], target_count: int) -> List[Dict]:
            """Take evenly distributed samples across the full list"""
            if len(categories) <= target_count:
                return categories

            # Sort alphabetically first
            sorted_cats = sorted(categories, key=lambda x: x['name'])

            # Take every Nth category to get even distribution
            step = len(sorted_cats) / target_count
            return [sorted_cats[int(i * step)] for i in range(target_count)]

        # Sample from each level (increased limits for 300 total)
        # With ~150 priority categories, we sample ~150 more from general pool
        level_2_sample = stratified_sample(by_level.get(2, []), 50)   # ~140 total Level 2
        level_3_sample = stratified_sample(by_level.get(3, []), 70)   # ~2800 total Level 3
        level_4_sample = stratified_sample(by_level.get(4, []), 30)   # ~6700 total Level 4

        # Combine: priority categories + sampled general categories
        result = priority_categories + level_2_sample + level_3_sample + level_4_sample

        logger.info(f"Category selection pool: {len(result)} total "
                   f"({len(priority_categories)} priority + {len(level_2_sample + level_3_sample + level_4_sample)} sampled)")

        return result

    def _build_combined_prompt(self, title: str, description: str, bullet_points: List[str], specifications: Dict, categories: List[Dict]) -> str:
        """Build cost-efficient prompt for THREE tasks: title optimization, brand extraction, AND category selection"""
        bullet_text = "\n".join(bullet_points[:3]) if bullet_points else "N/A"
        desc_text = description[:200] if description else "N/A"
        specs_text = json.dumps(specifications, indent=2) if specifications else "N/A"
        categories_json = json.dumps(categories[:100], indent=2)

        return f"""You are an eBay listing optimization expert. Perform THREE tasks in ONE response:

TASK 1: EXTRACT BRAND NAME
- Identify the actual brand/manufacturer from the product data
- Check specifications for: "Brand", "Brand Name", "BrandName", "Manufacturer" fields
- Use context to find the real brand (e.g., in "Waterproof Sony Headphones", brand is "Sony" not "Waterproof")
- Avoid generic terms like: Custom, Personalized, Handmade, Vintage, New, Unique, etc.
- If no clear brand exists, use "Generic"

TASK 2: OPTIMIZE TITLE (Max 80 characters)
- Make it compelling and keyword-rich for eBay search
- Include brand, key features, and product type
- Front-load important keywords
- Use natural language, avoid keyword stuffing
- MUST be ≤80 characters

TASK 3: SELECT CATEGORY
- Choose the MOST SPECIFIC matching eBay category
- Prefer Level 2-3 categories (fewer requirements)
- CRITICAL: AVOID Book/Media categories (Books, Music, Movies, etc.) UNLESS the product is clearly a physical book, DVD, or music album
- For beauty, skincare, health products → use Health & Beauty categories
- For cosmetics, patches, skincare tools → NOT books!

ORIGINAL PRODUCT DATA:
Title: {title}
Description: {desc_text}
Key Features:
{bullet_text}
Specifications:
{specs_text}

AVAILABLE EBAY CATEGORIES (top 100 leaf categories):
{categories_json}

OPTIMIZATION GUIDELINES:
1. Brand should be the actual manufacturer/company name
2. Title should capture buyer intent and eBay search algorithm
3. Include: Brand + Type + Key Feature + Size/Spec (if relevant)
4. Remove filler words like "perfect for", "great", etc.
5. Category should match the product's primary purpose

OUTPUT FORMAT (JSON only, no explanations):
{{
  "brand": "extracted brand name or 'Generic'",
  "optimized_title": "your optimized title here (max 80 chars)",
  "category_id": "the category ID",
  "reasoning": "brief 1-sentence explanation for all three decisions",
  "confidence": 0.0-1.0
}}"""

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

    def _validate_brand(self, brand: str) -> str:
        """
        Validate and clean brand name extracted by LLM.
        Ensures brand doesn't contain invalid terms that eBay rejects.
        """
        if not brand or not brand.strip():
            return "Generic"

        brand = brand.strip()

        # Invalid brand names that eBay rejects
        invalid_brands = {
            "custom", "personalized", "handmade", "vintage", "unique",
            "new", "brand", "the", "a", "an", "with", "for", "and",
            "n/a", "none", "unknown", "generic"
        }

        if brand.lower() in invalid_brands:
            return "Generic"

        # If brand is too short (likely an article or filler word)
        if len(brand) <= 2:
            return "Generic"

        return brand

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

    def fill_category_requirements(self, product_data: Dict, requirements: Dict, include_recommended: bool = False) -> Dict:
        """
        Use LLM to fill required (and optionally recommended) category-specific fields from product data.

        Args:
            product_data: Product information (title, description, specs, etc.)
            requirements: Category requirements from get_category_requirements()
            include_recommended: If True, also fill recommended aspects in the same LLM call

        Returns:
            Dict of aspect_name -> value mappings
        """
        required = requirements.get('required', [])
        recommended = requirements.get('recommended', []) if include_recommended else []

        if not required and not recommended:
            logger.info("No aspects to fill")
            return {}

        total_aspects = len(required) + len(recommended)
        logger.info(f"LLM filling {len(required)} required + {len(recommended)} recommended aspects (total: {total_aspects})...")

        # Build prompt with both required and recommended aspects
        prompt = self._build_requirements_filling_prompt(product_data, required, recommended)

        try:
            # Generous max_tokens to handle many aspects (required + recommended)
            # Categories can have 10-20+ aspects combined, each needing thoughtful extraction
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=3000,  # Increased to ensure complete responses for aspect-heavy categories
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            result_text = response.content[0].text.strip()
            logger.debug(f"LLM requirements response: {result_text}")

            # Check if we hit the token limit (response might be truncated)
            if response.stop_reason == "max_tokens":
                logger.warning(f"LLM response hit max_tokens limit! Response may be incomplete.")
                logger.warning(f"Consider increasing max_tokens or filtering more recommended aspects.")

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

            # CRITICAL: Validate and truncate aspect values to eBay's 65-character limit
            filled_aspects = self._validate_and_truncate_aspects(filled_aspects)

            # Log which aspects were filled
            required_names = {a['name'] for a in required}
            recommended_names = {a['name'] for a in recommended}

            filled_required = [k for k in filled_aspects.keys() if k in required_names]
            filled_recommended = [k for k in filled_aspects.keys() if k in recommended_names]

            logger.info(f"  Filled {len(filled_required)} required aspects: {filled_required}")
            if filled_recommended:
                logger.info(f"  Filled {len(filled_recommended)} recommended aspects: {filled_recommended}")

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

    def _validate_and_truncate_aspects(self, aspects: Dict) -> Dict:
        """
        Validate and truncate aspect values to meet eBay's 65-character limit.

        eBay enforces a strict 65-character maximum for aspect values.
        This method intelligently truncates long values while preserving meaning.

        Args:
            aspects: Dict of aspect_name -> value mappings

        Returns:
            Dict with validated and truncated values
        """
        MAX_LENGTH = 65
        validated = {}

        for aspect_name, aspect_value in aspects.items():
            if isinstance(aspect_value, list):
                # Handle multi-value aspects (cardinality: MULTI)
                truncated_list = []
                for val in aspect_value:
                    if isinstance(val, str) and len(val) > MAX_LENGTH:
                        truncated = self._smart_truncate(val, MAX_LENGTH)
                        logger.warning(f"  Truncated '{aspect_name}' value: '{val[:80]}...' -> '{truncated}'")
                        truncated_list.append(truncated)
                    else:
                        truncated_list.append(val)
                validated[aspect_name] = truncated_list
            elif isinstance(aspect_value, str):
                # Handle single-value aspects (cardinality: SINGLE)
                if len(aspect_value) > MAX_LENGTH:
                    truncated = self._smart_truncate(aspect_value, MAX_LENGTH)
                    logger.warning(f"  Truncated '{aspect_name}' value: '{aspect_value[:80]}...' -> '{truncated}'")
                    validated[aspect_name] = truncated
                else:
                    validated[aspect_name] = aspect_value
            else:
                # Handle non-string values (numbers, etc.)
                validated[aspect_name] = aspect_value

        return validated

    def _smart_truncate(self, text: str, max_length: int) -> str:
        """
        Intelligently truncate text to max_length while preserving meaning.

        Strategy:
        1. Try to break at sentence/phrase boundaries (period, comma, semicolon)
        2. Try to break at word boundaries
        3. As last resort, hard truncate with ellipsis

        Args:
            text: Text to truncate
            max_length: Maximum length (default 65 for eBay aspects)

        Returns:
            Truncated text that fits within max_length
        """
        if len(text) <= max_length:
            return text

        # Strategy 1: Try to extract the first complete sentence/phrase
        # Look for sentence boundaries (period, colon, semicolon) within first max_length chars
        truncate_at = max_length - 3  # Reserve 3 chars for "..."

        for delimiter in ['. ', ': ', '; ', ', ']:
            pos = text[:truncate_at].rfind(delimiter)
            if pos > max_length // 2:  # Only use if we get at least half the text
                return text[:pos].strip()

        # Strategy 2: Break at word boundary
        if ' ' in text[:truncate_at]:
            last_space = text[:truncate_at].rfind(' ')
            return text[:last_space].strip() + "..."

        # Strategy 3: Hard truncate (last resort)
        return text[:truncate_at].strip() + "..."

    def _build_requirements_filling_prompt(self, product_data: Dict, required_aspects: List[Dict], recommended_aspects: List[Dict] = None) -> str:
        """Build prompt for filling requirements - optimized to use only essential data"""
        if recommended_aspects is None:
            recommended_aspects = []

        # Process required aspects (MUST fill these)
        required_info = []
        for aspect in required_aspects:
            aspect_desc = {
                'name': aspect['name'],
                'mode': aspect['mode'],
                'cardinality': aspect['cardinality'],
                'priority': 'REQUIRED'
            }
            if aspect.get('values') and aspect['mode'] != 'FREE_TEXT':
                aspect_desc['allowed_values'] = aspect['values'][:20]  # Limit for prompt size
            required_info.append(aspect_desc)

        # Process recommended aspects (fill if possible, skip if not applicable)
        recommended_info = []
        for aspect in recommended_aspects:
            # Filter out recommended aspects with too many values (usually generic/less relevant)
            aspect_values = aspect.get('values', [])
            if aspect['mode'] != 'FREE_TEXT' and len(aspect_values) > 50:
                continue  # Skip aspects with 50+ values to save tokens

            aspect_desc = {
                'name': aspect['name'],
                'mode': aspect['mode'],
                'cardinality': aspect['cardinality'],
                'priority': 'RECOMMENDED'
            }
            if aspect_values and aspect['mode'] != 'FREE_TEXT':
                aspect_desc['allowed_values'] = aspect_values[:30]  # More values for recommended
            recommended_info.append(aspect_desc)

        all_aspects = required_info + recommended_info

        # Only use title, description, and bullet points (skip full specifications to save tokens)
        bullet_points = product_data.get('bulletPoints', [])[:5]  # Increased to 5 for better extraction
        description = product_data.get('description', '')[:500]  # Increased to 500 for better context

        return f"""You are filling out eBay listing fields based on product information.

PRODUCT DATA:
Title: {product_data.get('title', '')}
Description: {description}
Key Features: {json.dumps(bullet_points)}

ASPECTS TO FILL:
{json.dumps(all_aspects, indent=2)}

INSTRUCTIONS:
1. For REQUIRED aspects: MUST provide values, use best reasonable default if not found
2. For RECOMMENDED aspects: Only fill if information is clearly available in product data
3. If mode is SELECTION_ONLY, MUST choose from allowed_values (case-sensitive match)
4. If mode is FREE_TEXT, extract relevant information from product data
5. If cardinality is MULTI, return array; if SINGLE, return string or single value
6. Skip RECOMMENDED aspects if product data doesn't clearly provide the information

CRITICAL - CHARACTER LIMIT:
- ALL aspect values MUST be ≤65 characters (eBay hard limit)
- Be concise: extract key information only, remove filler words
- Examples:
  * BAD (128 chars): "SAFE AND GENTLE: The spray is made with plant extracts and contains no alcohol or harsh chemicals. It's suitable for both puppies and adults."
  * GOOD (62 chars): "Made with plant extracts, no alcohol, safe for puppies/adults"
  * BAD (101 chars): "Apply the ear mite drops daily for 7 to 10 days, if necessary, repeat treatment in two weeks."
  * GOOD (49 chars): "Apply daily for 7-10 days, repeat after 2 weeks"

QUALITY GUIDELINES:
- Prefer specific values over generic ones (e.g., "Stainless Steel" better than "Metal")
- For colors, materials, sizes: extract from title/bullets first, then description
- Don't guess or infer beyond what's explicitly stated
- For RECOMMENDED aspects, it's better to skip than provide uncertain values
- Keep all values concise and under 65 characters

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

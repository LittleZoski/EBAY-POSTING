"""
eBay Category Cache System using Taxonomy API
Downloads and caches the complete category tree for fast lookups
"""
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from category_suggester import CategorySuggester
from config import settings

logger = logging.getLogger(__name__)


class CategoryCache:
    """
    Downloads and caches eBay's category tree for fast category lookups.
    Uses Taxonomy API (modern REST API) instead of deprecated GetCategories.
    """

    def __init__(self, cache_file: str = "ebay_categories_cache.json"):
        """
        Initialize category cache.

        Args:
            cache_file: Path to cache file for storing category data
        """
        self.cache_file = Path(cache_file)
        self.categories = {}
        self.category_tree_version = None
        self.last_updated = None
        self.suggester = None

    def _get_suggester(self) -> CategorySuggester:
        """Get or create CategorySuggester instance for API calls"""
        if not self.suggester:
            self.suggester = CategorySuggester(
                client_id=settings.ebay_app_id,
                client_secret=settings.ebay_cert_id
            )
        return self.suggester

    def is_cache_valid(self, max_age_days: int = 90) -> bool:
        """
        Check if cached data is still valid.

        Args:
            max_age_days: Maximum age of cache in days (eBay updates quarterly ~90 days)

        Returns:
            True if cache exists and is not too old
        """
        if not self.cache_file.exists():
            return False

        if not self.last_updated:
            self.load_cache()

        if not self.last_updated:
            return False

        age = datetime.now() - self.last_updated
        return age.days < max_age_days

    def load_cache(self) -> bool:
        """
        Load category data from cache file.

        Returns:
            True if cache loaded successfully
        """
        try:
            if not self.cache_file.exists():
                logger.info("No category cache file found")
                return False

            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.categories = data.get('categories', {})
            self.category_tree_version = data.get('version')
            last_updated_str = data.get('last_updated')

            if last_updated_str:
                self.last_updated = datetime.fromisoformat(last_updated_str)

            logger.info(f"Loaded {len(self.categories)} categories from cache")
            logger.info(f"Cache version: {self.category_tree_version}, Last updated: {self.last_updated}")

            return True

        except Exception as e:
            logger.error(f"Failed to load category cache: {str(e)}")
            return False

    def save_cache(self):
        """Save category data to cache file"""
        try:
            data = {
                'categories': self.categories,
                'version': self.category_tree_version,
                'last_updated': self.last_updated.isoformat() if self.last_updated else None
            }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self.categories)} categories to cache")

        except Exception as e:
            logger.error(f"Failed to save category cache: {str(e)}")

    def download_categories(self, marketplace_id: str = "EBAY_US") -> bool:
        """
        Download complete category tree from eBay Taxonomy API.

        Args:
            marketplace_id: eBay marketplace (default: EBAY_US)

        Returns:
            True if download successful
        """
        try:
            logger.info(f"Downloading category tree for {marketplace_id}...")

            suggester = self._get_suggester()
            token = suggester.get_application_token()

            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            # Get category tree ID for marketplace
            category_tree_id = "0"  # EBAY_US

            # Download category tree (this gets the root and metadata)
            tree_url = f"{settings.ebay_api_base_url}/commerce/taxonomy/v1/category_tree/{category_tree_id}"
            response = requests.get(tree_url, headers=headers, timeout=60)

            if response.status_code != 200:
                logger.error(f"Failed to get category tree: {response.status_code} - {response.text}")
                return False

            tree_data = response.json()
            self.category_tree_version = tree_data.get('categoryTreeVersion')

            logger.info(f"Category tree version: {self.category_tree_version}")

            # Parse the entire category tree (returned in one call)
            # The root node contains all categories in a hierarchical structure
            root_node = tree_data.get('rootCategoryNode')

            if not root_node:
                logger.error("No root category node found")
                return False

            # Parse and store categories
            self.categories = {}
            self._parse_category_tree(root_node)

            self.last_updated = datetime.now()

            logger.info(f"Successfully downloaded {len(self.categories)} categories")

            # Save to cache
            self.save_cache()

            return True

        except Exception as e:
            logger.error(f"Exception downloading categories: {str(e)}")
            return False

    def _parse_category_tree(self, node: Dict, parent_id: Optional[str] = None):
        """
        Recursively parse category tree node and store categories.

        Args:
            node: Category tree node
            parent_id: Parent category ID
        """
        if not node:
            return

        category = node.get('category', {})
        category_id = category.get('categoryId')

        if category_id:
            # Store category info
            self.categories[category_id] = {
                'id': category_id,
                'name': category.get('categoryName', ''),
                'parent_id': parent_id,
                'level': node.get('categoryTreeNodeLevel', 0),
                'leaf': not bool(node.get('childCategoryTreeNodes'))
            }

        # Recurse into children
        children = node.get('childCategoryTreeNodes', [])
        for child in children:
            self._parse_category_tree(child, category_id)

    def get_category(self, category_id: str) -> Optional[Dict]:
        """
        Get category information by ID.

        Args:
            category_id: eBay category ID

        Returns:
            Category dict with id, name, parent_id, level, leaf
        """
        return self.categories.get(category_id)

    def is_leaf_category(self, category_id: str) -> bool:
        """
        Check if category is a leaf category (can be used for listings).

        Args:
            category_id: eBay category ID

        Returns:
            True if category is a leaf category
        """
        category = self.get_category(category_id)
        return category.get('leaf', False) if category else False

    def search_categories(self, keyword: str, leaf_only: bool = True) -> List[Dict]:
        """
        Search for categories by name keyword.

        Args:
            keyword: Search keyword
            leaf_only: Only return leaf categories (default True)

        Returns:
            List of matching categories
        """
        keyword_lower = keyword.lower()
        results = []

        for cat_id, cat_data in self.categories.items():
            if keyword_lower in cat_data['name'].lower():
                if not leaf_only or cat_data['leaf']:
                    results.append(cat_data)

        # Sort by name
        results.sort(key=lambda x: x['name'])

        return results

    def get_category_path(self, category_id: str) -> str:
        """
        Get full category path (e.g., "eBay Motors > Parts & Accessories > Wiper Blades").

        Args:
            category_id: eBay category ID

        Returns:
            Category path string
        """
        path_parts = []
        current_id = category_id

        # Walk up the tree
        while current_id:
            category = self.get_category(current_id)
            if not category:
                break

            path_parts.insert(0, category['name'])
            current_id = category.get('parent_id')

        return " > ".join(path_parts)

    def initialize(self, force_refresh: bool = False) -> bool:
        """
        Initialize category cache (load from file or download if needed).

        Args:
            force_refresh: Force download even if cache is valid

        Returns:
            True if initialization successful
        """
        if not force_refresh and self.is_cache_valid():
            logger.info("Using existing category cache")
            return True

        logger.info("Category cache is stale or missing, downloading...")
        return self.download_categories()


# Global category cache instance
category_cache = CategoryCache()


# Example usage
if __name__ == "__main__":
    import sys

    cache = CategoryCache()

    print("="*70)
    print("eBay Category Cache Test")
    print("="*70)

    # Initialize (will download if needed)
    print("\nInitializing category cache...")
    if cache.initialize():
        print(f"[OK] Cache ready with {len(cache.categories)} categories")
        print(f"  Version: {cache.category_tree_version}")
        print(f"  Last updated: {cache.last_updated}")

        # Test search
        print("\nSearching for 'wiper' categories:")
        results = cache.search_categories("wiper", leaf_only=True)

        for i, cat in enumerate(results[:10], 1):
            path = cache.get_category_path(cat['id'])
            print(f"\n{i}. {cat['name']} (ID: {cat['id']})")
            print(f"   Path: {path}")
            print(f"   Leaf: {cat['leaf']}")

    else:
        print("[FAILED] Failed to initialize cache")
        sys.exit(1)

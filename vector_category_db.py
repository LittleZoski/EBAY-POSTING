"""
Vector Database for eBay Category Semantic Search
Uses FAISS + sentence-transformers for fast, local semantic search
NO LLM CALLS NEEDED - completely free and fast!
Works great on Windows (no C++ build tools required)
"""
import json
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from category_cache import CategoryCache

logger = logging.getLogger(__name__)


class VectorCategoryDB:
    """
    Local vector database for semantic category matching.
    Uses FAISS with sentence-transformers embeddings.
    """

    def __init__(self, db_path: str = "./vector_category_db"):
        """
        Initialize FAISS-based vector database.

        Args:
            db_path: Path to store the vector database files
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(exist_ok=True)

        self.index_file = self.db_path / "faiss_index.bin"
        self.metadata_file = self.db_path / "category_metadata.pkl"

        # Initialize embedding model (runs locally, no API needed)
        # Using all-MiniLM-L6-v2: fast, efficient, 384 dimensions
        logger.info("Loading sentence transformer model...")
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.embedding_dim = 384

        # Load existing index if available
        self.index = None
        self.category_metadata = []
        self._load_index()

    def _load_index(self):
        """Load existing FAISS index and metadata if available"""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_file, 'rb') as f:
                    self.category_metadata = pickle.load(f)
                logger.info(f"Loaded existing vector DB with {len(self.category_metadata)} categories")
            except Exception as e:
                logger.warning(f"Failed to load existing index: {e}")
                self.index = None
                self.category_metadata = []
        else:
            logger.info("No existing vector DB found")

    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.category_metadata, f)
        logger.info(f"Saved vector DB with {len(self.category_metadata)} categories")

    def initialize_from_cache(self, force_rebuild: bool = False):
        """
        Build vector database from CategoryCache.
        This only needs to be run once, or when categories update.

        Args:
            force_rebuild: If True, delete and rebuild the entire database
        """
        if force_rebuild and self.index:
            logger.info("Force rebuilding vector database...")
            self.index = None
            self.category_metadata = []

        if self.index and len(self.category_metadata) > 0:
            logger.info(f"Vector DB already initialized with {len(self.category_metadata)} categories")
            return

        logger.info("Building vector database from category cache...")

        # Load category cache
        cache = CategoryCache()
        cache.initialize()

        # Prepare category data
        category_ids = []
        category_texts = []
        category_metadata = []

        for cat_id, cat_data in cache.categories.items():
            # Only include leaf categories (actual usable categories)
            if not cat_data.get('leaf'):
                continue

            level = cat_data.get('level', 0)
            # Include levels 2-4 (reasonable specificity)
            if level < 2 or level > 4:
                continue

            # Build rich text for semantic search
            # Include category name + full path for context
            category_path = cache.get_category_path(cat_id)

            # Create searchable text combining name and path
            # This helps the embedding understand context
            searchable_text = f"{cat_data['name']} - {category_path}"

            category_ids.append(cat_id)
            category_texts.append(searchable_text)
            category_metadata.append({
                "id": cat_id,
                "name": cat_data['name'],
                "level": level,
                "path": category_path,
                "parent_id": cat_data.get('parent_id', '')
            })

        logger.info(f"Generating embeddings for {len(category_texts)} categories...")

        # Generate embeddings (this happens locally, no API calls!)
        embeddings = self.model.encode(
            category_texts,
            show_progress_bar=True,
            batch_size=32,
            normalize_embeddings=True  # Normalize for cosine similarity
        )

        # Create FAISS index
        # Using IndexFlatIP for cosine similarity (Inner Product with normalized vectors)
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.index.add(embeddings.astype('float32'))

        # Store metadata
        self.category_metadata = category_metadata

        # Save to disk
        self._save_index()

        logger.info(f"Vector database built with {len(category_metadata)} categories")

    def search_category(self, product_title: str, product_description: str = "",
                       top_k: int = 5) -> List[Dict]:
        """
        Semantic search for best matching categories.

        Args:
            product_title: Product title
            product_description: Optional product description for better matching
            top_k: Number of top results to return

        Returns:
            List of dicts with category_id, name, path, level, and similarity_score
        """
        if not self.index or len(self.category_metadata) == 0:
            raise RuntimeError("Vector database not initialized. Run initialize_from_cache() first.")

        # Build search query - combine title and description
        # Title is weighted more heavily by putting it first
        if product_description:
            query = f"{product_title} {product_description[:200]}"
        else:
            query = product_title

        logger.debug(f"Searching for: {query[:100]}...")

        # Generate embedding for query
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True
        ).astype('float32')

        # Search FAISS index
        distances, indices = self.index.search(query_embedding, top_k)

        # Format results
        matches = []
        for idx, (distance, index) in enumerate(zip(distances[0], indices[0])):
            if index < 0 or index >= len(self.category_metadata):
                continue

            metadata = self.category_metadata[index]

            # distance is cosine similarity (0-1, higher is better)
            similarity = float(distance)

            matches.append({
                'category_id': metadata['id'],
                'name': metadata['name'],
                'path': metadata['path'],
                'level': metadata['level'],
                'similarity_score': round(similarity, 3)
            })

        return matches

    def get_best_category(self, product_title: str, product_description: str = "",
                         min_similarity: float = 0.5) -> Tuple[str, str, float]:
        """
        Get single best matching category with confidence score.

        Args:
            product_title: Product title
            product_description: Optional product description
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            Tuple of (category_id, category_name, confidence_score)
        """
        matches = self.search_category(product_title, product_description, top_k=3)

        if not matches:
            logger.warning("No category matches found!")
            # Fallback to a generic category
            return "360", "Art Prints", 0.3

        # Get best match
        best = matches[0]

        # Check if similarity is good enough
        if best['similarity_score'] < min_similarity:
            logger.warning(f"Best match similarity {best['similarity_score']} below threshold {min_similarity}")

        logger.info(f"Best match: {best['name']} (ID: {best['category_id']}, similarity: {best['similarity_score']})")

        # Also log top 3 for debugging
        if len(matches) > 1:
            logger.debug("Top 3 matches:")
            for match in matches[:3]:
                logger.debug(f"  {match['similarity_score']:.3f} - {match['name']} ({match['path']})")

        return best['category_id'], best['name'], best['similarity_score']


def build_vector_db():
    """Utility function to build/rebuild the vector database"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("="*70)
    print("Building Vector Database for eBay Categories")
    print("="*70)

    db = VectorCategoryDB()
    db.initialize_from_cache(force_rebuild=True)

    print("\n" + "="*70)
    print("SUCCESS: Vector database built successfully!")
    print("="*70)

    # Test search
    print("\nTesting semantic search...")
    test_queries = [
        "Dog food treats chicken flavor",
        "Moisturizer face cream anti-aging",
        "Windshield wiper blades rain-x",
        "Cat litter box automatic"
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")
        matches = db.search_category(query, top_k=3)
        for match in matches:
            print(f"  {match['similarity_score']:.3f} - {match['name']} (Level {match['level']})")


if __name__ == "__main__":
    build_vector_db()

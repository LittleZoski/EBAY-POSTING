"""
File Processor: Monitors folder for Amazon product JSON exports
and processes them for eBay listing creation
"""

import json
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from product_mapper import product_mapper
from ebay_client import ebay_client
from config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AmazonProductFileHandler(FileSystemEventHandler):
    """Handles new Amazon product JSON files"""

    def __init__(self, processor):
        self.processor = processor

    def on_created(self, event: FileSystemEvent):
        """Called when a file is created in the watched folder"""
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process JSON files with expected pattern
        if file_path.suffix == '.json' and 'amazon-products' in file_path.name:
            logger.info(f"New Amazon product file detected: {file_path.name}")
            # Use asyncio to process file
            asyncio.create_task(self.processor.process_file(file_path))


class FileProcessor:
    """Processes Amazon product JSON files and creates eBay listings"""

    def __init__(self):
        self.watch_folder = settings.watch_folder
        self.processed_folder = settings.processed_folder
        self.failed_folder = settings.failed_folder
        self.observer = None

        # Create folders if they don't exist
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        self.processed_folder.mkdir(parents=True, exist_ok=True)
        self.failed_folder.mkdir(parents=True, exist_ok=True)

    async def process_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Process a single Amazon product JSON file.

        Steps:
        1. Read and validate JSON
        2. Map products to eBay format
        3. Create inventory items in bulk
        4. Create offers in bulk
        5. Publish offers
        6. Move file to processed/failed folder
        """
        logger.info(f"Processing file: {file_path}")

        try:
            # Read JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            products = data.get('products', [])

            if not products:
                raise ValueError("No products found in file")

            logger.info(f"Found {len(products)} products to process")

            # Process in batches (max 25 per eBay API limit)
            batch_size = settings.max_items_per_batch
            results = {
                "total_products": len(products),
                "successful": 0,
                "failed": 0,
                "batches": []
            }

            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} items)")

                batch_result = await self._process_batch(batch)
                results["batches"].append(batch_result)
                results["successful"] += batch_result.get("successful", 0)
                results["failed"] += batch_result.get("failed", 0)

                # Delay between batches to avoid rate limiting
                if i + batch_size < len(products):
                    await asyncio.sleep(settings.processing_delay_seconds)

            # Save results
            await self._save_results(file_path, results)

            # Move file to processed folder
            destination = self.processed_folder / file_path.name
            shutil.move(str(file_path), str(destination))

            logger.info(
                f"Processing complete: {results['successful']} successful, "
                f"{results['failed']} failed"
            )

            return results

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")

            # Move file to failed folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            failed_name = f"{file_path.stem}_FAILED_{timestamp}{file_path.suffix}"
            destination = self.failed_folder / failed_name
            shutil.move(str(file_path), str(destination))

            # Save error log
            error_log = {
                "file": file_path.name,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            error_log_path = self.failed_folder / f"{file_path.stem}_error.json"
            with open(error_log_path, 'w', encoding='utf-8') as f:
                json.dump(error_log, f, indent=2)

            return {"success": False, "error": str(e)}

    async def _process_batch(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of products (max 25).

        Note: For MVP, we're creating inventory items.
        To create actual listings, you need:
        1. Business Policies set up in eBay account
        2. Category ID for each product
        3. Location key
        """
        inventory_items = []
        successful = 0
        failed = 0
        errors = []

        # Step 1: Map products to eBay inventory items
        for product in products:
            try:
                inventory_item = product_mapper.map_to_inventory_item(product)
                inventory_items.append(inventory_item)
            except Exception as e:
                logger.error(f"Error mapping product {product.get('asin')}: {str(e)}")
                errors.append({
                    "asin": product.get('asin'),
                    "error": str(e),
                    "stage": "mapping"
                })
                failed += 1

        # Step 2: Create inventory items in bulk
        if inventory_items:
            logger.info(f"Creating {len(inventory_items)} inventory items...")

            result = ebay_client.bulk_create_or_replace_inventory_item(inventory_items)

            # Parse results
            if "responses" in result:
                for response in result["responses"]:
                    if response.get("statusCode") in [200, 201, 204]:
                        successful += 1
                    else:
                        failed += 1
                        errors.append({
                            "sku": response.get("sku"),
                            "error": response.get("errors", []),
                            "stage": "inventory_creation"
                        })
            else:
                # Bulk operation failed entirely
                logger.error(f"Bulk operation failed: {result}")
                failed = len(inventory_items)
                errors.append({
                    "error": result.get("error"),
                    "stage": "bulk_operation"
                })

        return {
            "successful": successful,
            "failed": failed,
            "errors": errors,
            "items_processed": len(products)
        }

    async def _save_results(self, original_file: Path, results: Dict[str, Any]):
        """Save processing results to a log file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.processed_folder / f"{original_file.stem}_results_{timestamp}.json"

        results_data = {
            "original_file": original_file.name,
            "processed_at": datetime.now().isoformat(),
            "results": results
        }

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2)

    def start_watching(self):
        """Start watching the folder for new files"""
        logger.info(f"Starting file watcher on: {self.watch_folder}")

        event_handler = AmazonProductFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_folder), recursive=False)
        self.observer.start()

        logger.info("File watcher started successfully")

    def stop_watching(self):
        """Stop watching the folder"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("File watcher stopped")

    async def process_existing_files(self):
        """Process any existing JSON files in the watch folder"""
        logger.info("Checking for existing files...")

        json_files = list(self.watch_folder.glob("amazon-products-*.json"))

        if json_files:
            logger.info(f"Found {len(json_files)} existing files to process")

            for file_path in json_files:
                await self.process_file(file_path)
        else:
            logger.info("No existing files found")


# Global processor instance
file_processor = FileProcessor()

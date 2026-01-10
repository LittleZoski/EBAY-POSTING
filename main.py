"""
eBay Listing Manager - File Watcher Entry Point
Monitors Downloads folder for Amazon product JSON files and processes them with LLM
"""

import logging
import time
from file_processor import file_processor
from token_manager import get_token_manager
from store_selector import confirm_or_select_store, get_store_name

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the file watcher service"""
    print("\n" + "="*70)
    print("eBay Listing Manager with LLM Category Selection")
    print("="*70)

    # Interactive store selection - this will update .env if needed
    active_account = confirm_or_select_store()

    # Get the token manager for the selected account
    store_name = get_store_name(active_account)
    account_name = f"Account {active_account} - {store_name}" + (" (Primary)" if active_account == 1 else " (Secondary)")
    token_manager = get_token_manager(active_account)

    # Check OAuth tokens
    logger.info(f"Checking OAuth authentication for {account_name}...")
    if token_manager.load_tokens():
        logger.info(f"✅ OAuth authentication ready for {account_name}")
    else:
        logger.warning(f"⚠️  No valid OAuth token found for {account_name}!")
        logger.warning(f"   Please run: python authorize_account.py {active_account}")
        print("\n" + "="*70)
        return

    # Start file watcher
    file_processor.start_watching()

    # Process any existing files in the watch folder
    from pathlib import Path
    watch_folder = Path(file_processor.watch_folder)
    existing_files = list(watch_folder.glob("amazon-products-*.json"))

    if existing_files:
        logger.info(f"\nFound {len(existing_files)} existing file(s) in watch folder. Processing...")
        for file_path in existing_files:
            logger.info(f"Processing existing file: {file_path.name}")
            file_processor.process_file(file_path)

    # Keep the script running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        file_processor.stop_watching()
        logger.info("File watcher stopped. Goodbye!")
        print("="*70 + "\n")


if __name__ == "__main__":
    main()

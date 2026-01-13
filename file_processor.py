"""
File Processor: Monitors folder for Amazon product JSON exports
and processes them using LLM-powered listing flow
"""

import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from config import settings
import logging
import queue
import threading

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

            # Wait briefly to ensure file is fully written
            import time
            time.sleep(2)

            # Check if file still exists (might have been moved/deleted)
            if not file_path.exists():
                logger.warning(f"File no longer exists: {file_path.name}")
                return

            # Add file to processing queue
            self.processor.add_to_queue(file_path)


class FileProcessor:
    """Processes Amazon product JSON files using LLM flow"""

    def __init__(self):
        self.watch_folder = settings.watch_folder
        self.processed_folder = settings.processed_folder
        self.failed_folder = settings.failed_folder
        self.observer = None

        # Queue for files waiting to be processed
        self.file_queue = queue.Queue()
        self.processing_lock = threading.Lock()
        self.is_processing = False
        self.should_stop = False

        # Worker thread for processing files from queue
        self.worker_thread = None

        # Create folders if they don't exist
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        self.processed_folder.mkdir(parents=True, exist_ok=True)
        self.failed_folder.mkdir(parents=True, exist_ok=True)

        logger.info(f"File Processor initialized")
        logger.info(f"  Watching: {self.watch_folder}")
        logger.info(f"  Processed: {self.processed_folder}")

    def process_file(self, file_path: Path):
        """
        Process a new Amazon product JSON file by moving it to processed folder
        and running the LLM listing flow
        """
        try:
            logger.info(f"\n{'='*70}")
            logger.info(f"Processing: {file_path.name}")
            logger.info(f"{'='*70}")

            # Move file to processed folder first
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_path = self.processed_folder / file_path.name

            # If file already exists, use timestamp
            if new_path.exists():
                stem = file_path.stem
                new_path = self.processed_folder / f"{stem}_{timestamp}.json"

            shutil.move(str(file_path), str(new_path))
            logger.info(f"Moved to: {new_path}")

            # Run the LLM listing flow
            logger.info(f"\nStarting LLM-powered listing flow...")

            # Choose between parallel and sequential processing
            if settings.use_parallel_processing:
                script_path = Path(__file__).parent / "complete_listing_flow_parallel.py"
                logger.info(f"Using PARALLEL processing with {settings.max_workers} workers")
            else:
                script_path = Path(__file__).parent / "complete_listing_flow_llm.py"
                logger.info(f"Using SEQUENTIAL processing (original flow)")

            # Run as subprocess to avoid import conflicts
            # Use configurable timeout (default: 30 minutes for large batches)
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=settings.processing_timeout_seconds
            )

            # Log output
            if result.stdout:
                logger.info(f"\nLLM Flow Output:")
                logger.info(result.stdout)

            if result.stderr:
                logger.error(f"\nLLM Flow Errors:")
                logger.error(result.stderr)

            if result.returncode == 0:
                logger.info(f"\n{'='*70}")
                logger.info(f"[SUCCESS] Processing completed for {file_path.name}")
                logger.info(f"{'='*70}\n")
            else:
                logger.error(f"\n{'='*70}")
                logger.error(f"[FAILED] Processing failed for {file_path.name}")
                logger.error(f"Return code: {result.returncode}")
                logger.error(f"{'='*70}\n")

        except subprocess.TimeoutExpired:
            logger.error(f"[TIMEOUT] Processing took too long for {file_path.name}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to process {file_path.name}: {str(e)}")
            # Move to failed folder
            try:
                failed_path = self.failed_folder / file_path.name
                if new_path.exists():
                    shutil.move(str(new_path), str(failed_path))
                    logger.info(f"Moved to failed folder: {failed_path}")
            except Exception as move_error:
                logger.error(f"Could not move to failed folder: {move_error}")

    def add_to_queue(self, file_path: Path):
        """Add a file to the processing queue"""
        self.file_queue.put(file_path)
        queue_size = self.file_queue.qsize()
        logger.info(f"✅ Added to queue: {file_path.name}")
        logger.info(f"📋 Queue status: {queue_size} file(s) waiting")

        if queue_size > 1:
            logger.info(f"⏳ File will be processed after {queue_size - 1} other file(s)")

    def queue_worker(self):
        """Worker thread that processes files from the queue one at a time"""
        logger.info("🔧 Queue worker thread started")

        while not self.should_stop:
            try:
                # Wait for a file to be available in the queue (with timeout for graceful shutdown)
                try:
                    file_path = self.file_queue.get(timeout=1)
                except queue.Empty:
                    continue

                # Mark as processing
                with self.processing_lock:
                    self.is_processing = True

                remaining = self.file_queue.qsize()
                logger.info(f"\n🚀 Starting processing: {file_path.name}")
                if remaining > 0:
                    logger.info(f"📋 Files remaining in queue: {remaining}")

                # Process the file
                self.process_file(file_path)

                # Mark as done and not processing
                self.file_queue.task_done()
                with self.processing_lock:
                    self.is_processing = False

                logger.info(f"✅ Completed: {file_path.name}")

            except Exception as e:
                logger.error(f"❌ Worker error: {str(e)}")
                with self.processing_lock:
                    self.is_processing = False

        logger.info("🔧 Queue worker thread stopped")

    def start_watching(self):
        """Start watching the folder for new files"""
        # Start the queue worker thread
        self.should_stop = False
        self.worker_thread = threading.Thread(target=self.queue_worker, daemon=True)
        self.worker_thread.start()

        # Start file system watcher
        event_handler = AmazonProductFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_folder), recursive=False)
        self.observer.start()

        logger.info(f"\n{'='*70}")
        logger.info(f"File Watcher Started")
        logger.info(f"{'='*70}")
        logger.info(f"Watching: {self.watch_folder}")
        logger.info(f"Waiting for Amazon product JSON files...")
        logger.info(f"Mode: Queue-based processing (one file at a time)")
        logger.info(f"{'='*70}\n")

    def stop_watching(self):
        """Stop watching the folder"""
        logger.info("Stopping file watcher...")

        # Stop file system observer
        if self.observer:
            self.observer.stop()
            self.observer.join()
            logger.info("File system watcher stopped")

        # Signal worker thread to stop
        self.should_stop = True

        # Wait for current processing to complete
        if self.worker_thread and self.worker_thread.is_alive():
            logger.info("Waiting for worker thread to finish current task...")
            self.worker_thread.join(timeout=10)  # Wait up to 10 seconds

            if self.worker_thread.is_alive():
                logger.warning("Worker thread did not stop gracefully")
            else:
                logger.info("Worker thread stopped")

        # Report any remaining items in queue
        remaining = self.file_queue.qsize()
        if remaining > 0:
            logger.warning(f"⚠️  {remaining} file(s) were still in queue")

        logger.info("File watcher stopped completely")


# Global processor instance
file_processor = FileProcessor()

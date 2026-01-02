# eBay Listing Manager with LLM-Powered Category Selection

Automated eBay listing creation from Amazon product data using Claude AI for intelligent category selection and requirement fulfillment.

## Features

✅ **LLM-Powered Category Selection** - Claude Haiku intelligently selects from 17,105+ eBay categories
✅ **Automatic Requirement Fulfillment** - AI extracts and fills category-specific required fields
✅ **Category Tree Caching** - Downloads and caches eBay's complete category hierarchy (90-day cache)
✅ **File Watcher** - Automatically processes new product files dropped in Downloads folder
✅ **Full Publishing Flow** - Complete automation from JSON file to live eBay listing

## Architecture

```
Amazon Product JSON → File Watcher → LLM Category Selection →
  ↓
Category Requirements Fetching → LLM Requirements Filling →
  ↓
Inventory Item Creation → Offer Creation → Publishing → Live eBay Listing
```

## Core Files

### Main Processing Flow
- **`complete_listing_flow_llm.py`** - Main LLM-powered listing workflow
- **`file_processor.py`** - File watcher that triggers LLM flow
- **`main.py`** - Entry point for file watcher service

### LLM & Categories
- **`llm_category_selector.py`** - Claude-powered category selection and requirements filling
- **`category_cache.py`** - eBay category tree caching system
- **`category_suggester.py`** - eBay Taxonomy API wrapper (used by cache)

### Core Services
- **`config.py`** - Configuration management
- **`token_manager.py`** - OAuth token persistence
- **`ebay_auth.py`** - eBay OAuth 2.0 authentication
- **`product_mapper.py`** - Product data transformation

### Utilities
- **`delete_all_offers.py`** - Clean up unpublished test offers
- **`authorize_once.py`** - Initial OAuth setup

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Edit `.env` file with your credentials:
```bash
# eBay API Credentials
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
EBAY_DEV_ID=your_dev_id
EBAY_REDIRECT_URI=your_redirect_uri
EBAY_ENVIRONMENT=PRODUCTION  # or SANDBOX

# Claude API
ANTHROPIC_API_KEY=your_claude_api_key

# Folders
WATCH_FOLDER=c:\Users\YourName\Downloads
PROCESSED_FOLDER=c:\Users\YourName\ebay-listing-app\processed
FAILED_FOLDER=c:\Users\YourName\ebay-listing-app\failed
```

### 3. Configure Business Policies
Edit `business_policies_config.json`:
```json
{
  "payment_policy_id": "your_payment_policy_id",
  "return_policy_id": "your_return_policy_id",
  "fulfillment_policy_id": "your_fulfillment_policy_id"
}
```

### 4. Authorize eBay Access
```bash
python authorize_once.py
```
Follow the prompts to complete OAuth authorization.

## Usage

### Automatic Mode (File Watcher)
```bash
python main.py
```
Drop Amazon product JSON files into your Downloads folder. The system will automatically:
1. Detect the new file
2. Use Claude to select the best category
3. Fetch category requirements
4. Fill required fields with AI
5. Create inventory and offers
6. Publish to eBay

### Manual Mode
```bash
python complete_listing_flow_llm.py
```
Processes the most recent product file in the `processed` folder.

### Cleanup Utilities
```bash
# Delete all unpublished test offers
python delete_all_offers.py
```

## Product File Format

Input: Amazon product JSON export
```json
{
  "exportedAt": "2026-01-02T19:02:13.022Z",
  "totalProducts": 2,
  "products": [
    {
      "asin": "B0C1Y8Z6VT",
      "title": "Product Title",
      "description": "Product description...",
      "bulletPoints": ["Feature 1", "Feature 2"],
      "images": ["https://..."],
      "price": "$9.99",
      "specifications": {
        "Brand": "BrandName",
        "Color": "Black"
      }
    }
  ]
}
```

## How It Works

### 1. Category Selection
Claude analyzes the product title, description, and specifications to select the most appropriate category from eBay's 17,105+ categories. It prioritizes:
- Level 2-3 categories (less specialized, fewer requirements)
- Categories that match the product's primary purpose
- Categories with reasonable requirement complexity

### 2. Requirements Fulfillment
For each selected category, the system:
1. Fetches required item specifics via eBay Taxonomy API
2. Uses Claude to extract values from product data
3. Handles both FREE_TEXT and SELECTION_ONLY aspect modes
4. Supports SINGLE and MULTI cardinality

### 3. Publishing
Creates complete eBay listings with:
- Inventory items with proper location distribution
- Offers with business policies
- HTML listing descriptions
- Category-specific item aspects
- Automatic publishing to live marketplace

## Category Cache

The system maintains a local cache of eBay's category tree:
- **File**: `ebay_categories_cache.json`
- **Updates**: Every 90 days automatically
- **Contains**: 17,105+ categories with hierarchy, leaf status, paths
- **API**: eBay Taxonomy API (Commerce API)

## Cost Optimization

- **Claude Haiku** - Fast, low-cost model (~$0.25 per million tokens)
- **Category Cache** - Reduces API calls to eBay
- **Token Management** - Reuses OAuth tokens (2-hour expiry)
- **Efficient Prompts** - Sends only 250 categories to LLM (top levels)

## Troubleshooting

### "No OAuth token found"
Run `python authorize_once.py` to complete initial authorization.

### "Category X is invalid"
The category may not be a valid leaf category. Check:
```python
from category_cache import CategoryCache
cache = CategoryCache()
cache.initialize()
cat = cache.get_category("YOUR_CATEGORY_ID")
print(f"Is leaf: {cat['leaf']}")
```

### "Missing required aspect: XYZ"
The LLM couldn't extract the required value. Check:
1. Product data contains the information
2. Claude API key is valid
3. Review `complete_listing_flow_llm.py` output for LLM response

### Publishing fails with HTTP 400
Common causes:
- Missing required item specifics for the category
- Invalid category ID (not a leaf category)
- Missing business policies
- Missing merchant location

## API Documentation

- [eBay Taxonomy API](https://developer.ebay.com/api-docs/commerce/taxonomy/overview.html)
- [eBay Inventory API](https://developer.ebay.com/api-docs/sell/inventory/overview.html)
- [Claude API](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)

## Project Structure

```
ebay-listing-app/
├── main.py                          # File watcher entry point
├── complete_listing_flow_llm.py     # Main LLM workflow
├── file_processor.py                # File watcher logic
├── llm_category_selector.py         # LLM category selection
├── category_cache.py                # Category tree cache
├── category_suggester.py            # eBay Taxonomy API
├── product_mapper.py                # Product transformation
├── config.py                        # Configuration
├── token_manager.py                 # OAuth persistence
├── ebay_auth.py                     # eBay authentication
├── delete_all_offers.py             # Cleanup utility
├── authorize_once.py                # OAuth setup
├── .env                             # Environment variables
├── business_policies_config.json    # eBay policies
├── ebay_categories_cache.json       # Category cache (auto-generated)
├── ebay_tokens.json                 # OAuth tokens (auto-generated)
├── processed/                       # Processed product files
├── failed/                          # Failed processing files
└── archive/                         # Old/deprecated scripts
```

## License

Private project - All rights reserved

## Support

For issues or questions, check the archive folder for diagnostic scripts or review the eBay API documentation.

# eBay Listing App - Quick Start Guide

## Overview
Automated tool to create eBay listings from Amazon product JSON files with configurable price multipliers.

## Prerequisites
- Python 3.7+
- eBay Developer Account with Production API keys
- eBay Seller Account with Business Policies set up

## Setup

### 1. Configure eBay Credentials
Edit `.env` file with your eBay Production credentials:
```
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
EBAY_DEV_ID=your_dev_id
EBAY_REDIRECT_URI=your_runame
EBAY_ENVIRONMENT=PRODUCTION
```

### 2. Configure Business Policies
Edit `business_policies_config.json` with your policy IDs:
```json
{
  "payment_policy_id": "370857833023",
  "return_policy_id": "370857832023",
  "fulfillment_policy_id": "370857831023",
  "default_category_id": "11450",
  "default_marketplace": "EBAY_US"
}
```

To find your policy IDs:
1. Go to https://www.ebay.com/sh/fin/business-policies
2. Click on each policy
3. Copy the `policyId` from the URL

### 3. Authorize the App (One-Time Setup)

**Step 1:** Start the server
```bash
python main.py
```

**Step 2:** Run authorization script
```bash
python authorize_once.py
```

**Step 3:** Follow the prompts
- Copy the authorization URL
- Open it in your browser
- Sign in to eBay and click "Agree"
- Copy the redirect URL back to the script

**Done!** Tokens are saved to `ebay_tokens.json` and will auto-refresh for 18 months.

## Usage

### Process Amazon Products

**1. Prepare your JSON file** in `C:\Users\31243\Downloads\`:
```json
[
  {
    "asin": "B0CM7ZXQWC",
    "title": "Product Title",
    "price": "$34.39",
    "description": "Product description",
    "bulletPoints": ["Feature 1", "Feature 2"],
    "images": ["https://m.media-amazon.com/images/..."],
    "price_multiplier": 2.0,
    "url": "https://www.amazon.com/dp/B0CM7ZXQWC"
  }
]
```

**2. Update file path** in `complete_listing_flow.py` (line 31):
```python
json_file = Path("C:/Users/31243/Downloads/your-file.json")
```

**3. Run the script:**
```bash
python complete_listing_flow.py
```

This will:
- Create inventory items with US location
- Apply price multiplier (default 2x if not specified)
- Create offers with your business policies
- Attempt to publish listings

## Price Multiplier

The `price_multiplier` field in your JSON is **optional** and defaults to `2.0`:

- No multiplier specified → 2x (e.g., $10 → $20)
- `"price_multiplier": 1.5` → 1.5x (e.g., $10 → $15)
- `"price_multiplier": 3.0` → 3x (e.g., $10 → $30)

Formula: `eBay Price = Amazon Price × Multiplier`

## File Watcher (Automatic Processing)

To automatically process new JSON files dropped in the Downloads folder:

**1. Start the server:**
```bash
python main.py
```

**2. Drop JSON files in:** `C:\Users\31243\Downloads\`

**3. The server will automatically:**
- Detect new `amazon-products-*.json` files
- Wait 2 seconds to ensure file is fully written
- Process the file in a background thread
- Create inventory items and offers
- Move processed files to `processed/` folder
- Move failed files to `failed/` folder with error logs

**Note:** For manual control, use `complete_listing_flow.py` instead.

## Project Structure

### Core Files:
- `main.py` - FastAPI server with file watcher
- `ebay_auth.py` - OAuth authentication
- `ebay_client.py` - eBay API client
- `product_mapper.py` - Amazon → eBay mapping with price multiplier
- `token_manager.py` - Token persistence and auto-refresh
- `file_processor.py` - File watching and processing
- `config.py` - Settings management
- `authorize_once.py` - OAuth setup script
- `complete_listing_flow.py` - Manual end-to-end processing

### Configuration Files:
- `.env` - eBay API credentials
- `business_policies_config.json` - Business policy IDs
- `ebay_tokens.json` - OAuth tokens (auto-generated)

## Known Issues

### Publishing via API
The eBay Inventory API currently returns "System error" (Error 25002) when trying to publish offers. This is an eBay server-side issue.

**Workaround:**
1. The script creates inventory items and offers successfully
2. Offers are created with status "UNPUBLISHED"
3. These won't show in Seller Hub UI (API limitation)
4. You may need to manually create listings through Seller Hub

**What Works:**
- ✅ OAuth authentication and auto-refresh
- ✅ Price multiplier (default 2x, customizable per product)
- ✅ Inventory item creation with US location
- ✅ Offer creation with business policies
- ❌ API publishing (eBay system error)

## Troubleshooting

### "No OAuth token found"
Run `python authorize_once.py` to set up authentication.

### "Invalid policy ID"
Update `business_policies_config.json` with your actual policy IDs from eBay Seller Hub.

### "System error" when publishing
This is an eBay API issue. The offers are created correctly but can't be published via API. Try creating listings manually in Seller Hub.

### File watcher not working
Use manual processing with `complete_listing_flow.py` instead.

## Support
For eBay API issues, contact eBay Developer Support at https://developer.ebay.com/support

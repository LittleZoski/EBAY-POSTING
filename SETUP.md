# eBay Listing & Order Fulfillment Setup

Complete guide for Amazon → eBay dropshipping automation.

## Quick Reference

### Key Commands

```bash
# Authorization
python authorize_account.py 1          # Authorize Account 1
python authorize_account.py 2          # Authorize Account 2

# Vector DB Setup (one-time, ~3-5 minutes)
pip install faiss-cpu sentence-transformers torch
python vector_category_db.py           # Build category database

# Listing Products
python main.py                          # Start listing automation

# Order Fulfillment
python check_order_access.py           # Verify order API access
python fetch_orders.py                  # Fetch unshipped orders
python orders_flow.py --limit 100       # Fetch with custom limit
```

## Setup Order

### 1. Configure .env File

Add your eBay API credentials and business policies:

```bash
# eBay API Credentials
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
EBAY_DEV_ID=your_dev_id
EBAY_REDIRECT_URI=your_redirect_uri
EBAY_ENVIRONMENT=PRODUCTION

# Account 1 Business Policies
PAYMENT_POLICY_ID=370857833023
RETURN_POLICY_ID=370857832023
FULFILLMENT_POLICY_ID=370857831023

# Account 2 Business Policies (Optional)
PAYMENT_POLICY_ID_ACCOUNT2=your_id
RETURN_POLICY_ID_ACCOUNT2=your_id
FULFILLMENT_POLICY_ID_ACCOUNT2=your_id

# Active Account (1 or 2)
ACTIVE_ACCOUNT=1

# Parallel Processing (3x faster, avoids API rate limits)
MAX_WORKERS=3                       # 3-5 workers recommended (avoids Anthropic rate limits)
USE_PARALLEL_PROCESSING=true        # true = parallel, false = sequential

# Anthropic API
ANTHROPIC_API_KEY=your_key
```

### 2. Build Vector Database (One-Time)

**Category Selection System:**
- Uses local vector database for semantic search
- Searches ALL ~10,000 eBay categories (vs 300 priority categories)
- Zero cost, instant results (<50ms vs 1-3 seconds)
- No LLM API calls needed for category selection

```bash
pip install faiss-cpu sentence-transformers torch
python vector_category_db.py
```

**What happens:**
- Loads all eBay categories from cache
- Generates semantic embeddings
- Builds FAISS index
- Saves to `vector_category_db/` folder

### 3. Authorize eBay Account

**First Time or Re-authorization:**

```bash
python authorize_account.py 1
```

**Important**: If authorizing different account, sign out from eBay first.

**What this does:**
- Opens browser to eBay authorization page
- Requests fulfillment, inventory, and account scopes
- Saves tokens to `ebay_tokens_account1.json`
- Tokens auto-refresh for 18 months

### 4. Verify Order Access

```bash
python check_order_access.py
```

**What this does:**
- Checks if OAuth token has fulfillment scope
- Tests eBay Fulfillment API connection
- Shows count of unshipped orders

## Daily Workflow

### A. Listing Products (Amazon → eBay)

**Step 1**: Scrape Amazon products to JSON file
**Step 2**: Place JSON in watch folder (`Downloads/`)
**Step 3**: Run listing automation
```bash
python main.py
```

**What happens:**
- Watches for `amazon-products-*.json` files
- Uses vector DB for category selection (free, instant)
- Uses LLM for title optimization and requirements (optional)
- Applies tiered pricing strategy
- Creates inventory items and offers
- Publishes listings to eBay
- **Processes multiple items in parallel** (3x faster)

### B. Order Fulfillment (eBay → Amazon)

**Step 1**: Fetch unshipped eBay orders
```bash
python fetch_orders.py
```

**What happens:**
- Fetches orders with status NOT_STARTED or IN_PROGRESS
- Extracts buyer shipping information
- Maps to Amazon ASIN from SKU
- Exports to `ebay_orders/ebay-orders-*.json`

**Step 2**: Review JSON output

Check `ebay_orders/` folder for exported file. Each order contains:
- Customer name, address, phone
- Amazon ASIN to order
- Quantity needed
- eBay order ID for reference

**Step 3**: Use web extension to populate Amazon addresses

*(Next automation step - manual for now)*

**Step 4**: Place orders on Amazon

**Step 5**: Update eBay with tracking numbers

## Multi-Account Setup

### Switch Between Accounts

Edit `.env` file:
```bash
ACTIVE_ACCOUNT=2
```

Restart the app:
```bash
python main.py
```

### Authorize Second Account

**Before running:**
1. Go to https://www.ebay.com
2. Sign out
3. Close all eBay tabs

**Then authorize:**
```bash
python authorize_account.py 2
```

Sign in to the correct account when browser opens.

## Exported Order Format

```json
{
  "exportedAt": "2026-01-07T10:30:00Z",
  "account": 1,
  "totalOrders": 4,
  "orders": [
    {
      "ebayOrderId": "12-34567-89012",
      "ebayOrderDate": "2026-01-07T15:30:00.000Z",
      "ebayOrderStatus": "NOT_STARTED",
      "shippingAddress": {
        "name": "John Doe",
        "addressLine1": "123 Main Street",
        "addressLine2": "Apt 4B",
        "city": "New York",
        "stateOrProvince": "NY",
        "postalCode": "10001",
        "countryCode": "US",
        "phoneNumber": "555-123-4567",
        "email": "buyer@example.com"
      },
      "items": [
        {
          "sku": "B0FYSB63JF",
          "asin": "B0FYSB63JF",
          "title": "Product Title",
          "quantity": 2,
          "price": 45.99
        }
      ]
    }
  ]
}
```

## Troubleshooting

### No valid OAuth token found
**Solution**: Re-authorize the account
```bash
python authorize_account.py 1
```

### Access forbidden (403)
**Solution**: Token missing fulfillment scope, re-authorize
```bash
python authorize_account.py 1
```

### No unshipped orders found
**Reasons**:
- All orders fulfilled
- Orders older than 90 days
- Wrong account selected

**Check**: eBay Seller Hub → Orders

### Wrong account authorized
**Solution**: Delete token file and re-authorize
```bash
del ebay_tokens_account1.json
python authorize_account.py 1
```

Sign in to correct account when prompted.

## Files Overview

### Configuration
- `.env` - API credentials and settings
- `config.py` - Settings manager
- `business_policies_config.json` - Business policy IDs

### Authentication
- `ebay_auth.py` - OAuth manager
- `token_manager.py` - Token persistence
- `authorize_account.py` - Authorization script
- `ebay_tokens_account1.json` - Saved tokens (auto-generated)

### Listing Flow
- `main.py` - File watcher entry point
- `file_processor.py` - JSON file handler
- `product_mapper.py` - Amazon → eBay mapping
- `semantic_category_selector.py` - Vector DB category selection (free, fast)
- `vector_category_db.py` - FAISS-based category database builder
- `complete_listing_flow_parallel.py` - Parallel listing (3 workers)
- `complete_listing_flow_llm.py` - Sequential listing (original)

### Order Flow
- `orders_flow.py` - Order fetcher (main module)
- `fetch_orders.py` - Quick wrapper script
- `check_order_access.py` - API access tester

### Output Folders
- `processed/` - Processed Amazon JSON files
- `ebay_orders/` - Exported order files
- `failed/` - Failed listings

## API Scopes Required

The app requests these eBay OAuth scopes:
- `sell.inventory` - Create/manage listings
- `sell.account` - Access business policies
- `sell.marketing.readonly` - View offers
- `sell.fulfillment` - **Access orders**

All scopes are requested during authorization.

## Performance

**Vector Database (Category Selection):**
- Zero cost - no LLM API calls
- <50ms per query (vs 1-3 seconds with LLM)
- Searches all ~10,000 categories (vs 300 priority)
- Offline capable after initial setup

**Parallel Processing:**
- 30 items: ~30 seconds (vs 3-5 minutes sequential)
- 400 items: ~10-15 minutes (vs 40-67 minutes sequential)
- Automatic rate limit monitoring and throttling

**Smart Caching:**
- Category requirements cached in-memory per session
- Reduces redundant API calls within same batch

**Toggle Settings:**
- `USE_PARALLEL_PROCESSING=true` - Fast (recommended)
- `USE_PARALLEL_PROCESSING=false` - Original flow
- `MAX_WORKERS=3` - Safe for Anthropic API (3-5 recommended)

**Cost Savings:**
- Before: ~$0.003 per product (3 LLM calls)
- After: ~$0.002 per product (2 LLM calls, vector DB free)
- Pure vector: ~$0.001 per product (requirements only)

## Notes

- Tokens auto-refresh for 18 months
- Orders only available for last 90 days (eBay limitation)
- Address details removed after 90 days
- Process orders promptly to avoid data loss
- Export files saved locally only
- Handle buyer data per eBay policies
- Vector DB stored in `vector_category_db/` (~50-80MB)
- Rebuild vector DB if categories update: `python vector_category_db.py`

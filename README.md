# Amazon to eBay Listing Manager

A FastAPI application that automatically monitors a folder for exported Amazon product data and creates eBay listings via the eBay Inventory API. Built for dropshipping arbitrage business.

## Features

- **Automated File Monitoring**: Watches a folder for Amazon product JSON exports
- **Bulk Processing**: Processes up to 25 items per batch (eBay API limit)
- **OAuth 2.0 Authentication**: Secure eBay API authentication following 2025 standards
- **Smart Price Markup**: Configurable percentage and fixed markup
- **Product Mapping**: Converts Amazon product data to eBay Inventory API format
- **Error Handling**: Robust error handling with detailed logging
- **FastAPI Dashboard**: Web interface for monitoring and management
- **Background Tasks**: Async processing for optimal performance

## Architecture

```
Amazon Extension → JSON Export → Watch Folder → FastAPI App → eBay Inventory API
                                      ↓
                              [Processed/Failed]
```

## Project Structure

```
ebay-listing-app/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration and settings
├── ebay_auth.py           # eBay OAuth 2.0 authentication
├── ebay_client.py         # eBay Inventory API client
├── product_mapper.py      # Amazon → eBay data mapping
├── file_processor.py      # File monitoring and processing
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── README.md             # This file
├── processed/            # Successfully processed files
└── failed/               # Failed processing attempts
```

## Installation

### 1. Install Python Dependencies

```bash
cd ebay-listing-app
pip install -r requirements.txt
```

### 2. Set Up eBay Developer Account

1. Go to [eBay Developers Program](https://developer.ebay.com/)
2. Sign up or log in
3. Create a new application
4. Get your credentials:
   - App ID (Client ID)
   - Cert ID (Client Secret)
   - Dev ID

### 3. Configure Environment Variables

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# eBay API Credentials
EBAY_APP_ID=YourAppID
EBAY_CERT_ID=YourCertID
EBAY_DEV_ID=YourDevID
EBAY_REDIRECT_URI=YourRedirectURI

# Environment (SANDBOX or PRODUCTION)
EBAY_ENVIRONMENT=SANDBOX

# Folders
WATCH_FOLDER=c:\Users\31243\Downloads
PROCESSED_FOLDER=c:\Users\31243\ebay-listing-app\processed
FAILED_FOLDER=c:\Users\31243\ebay-listing-app\failed

# Pricing
PRICE_MARKUP_PERCENTAGE=20.0
FIXED_MARKUP_AMOUNT=5.00
```

### 4. Set Up Business Policies (Required for eBay Listings)

Before creating listings, you must create Business Policies in eBay Seller Hub:

1. Log in to [eBay Seller Hub](https://www.ebay.com/sh/ovw)
2. Go to **Account** → **Business Policies**
3. Create policies for:
   - **Payment Policy** (how you'll receive payment)
   - **Return Policy** (30+ days recommended for 2025 compliance)
   - **Fulfillment Policy** (shipping methods and costs)
4. Note the Policy IDs (you'll need these)

## Usage

### Start the Application

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload
```

The application will start on `http://localhost:8000`

### Access the Dashboard

Open your browser and visit:
- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Status**: http://localhost:8000/status

### Authorize eBay Account (One-Time Setup)

1. Visit: http://localhost:8000/auth/consent-url
2. Copy the consent URL
3. Open it in your browser
4. Sign in to eBay and authorize the app
5. You'll be redirected to your `redirect_uri` with a `code` parameter
6. Send the code to: `POST /auth/callback` with the authorization code

Example using curl:
```bash
curl -X POST "http://localhost:8000/auth/callback?authorization_code=YOUR_CODE"
```

### Process Amazon Products

1. Use the browser extension to scrape Amazon products
2. Export products as JSON
3. Save JSON file to your watch folder (e.g., `Downloads`)
4. The application automatically detects and processes the file
5. Check `processed/` folder for results
6. Check `failed/` folder if any errors occurred

### Manual Processing

You can also manually trigger processing via API:

```bash
# Process specific file
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"file_name": "amazon-products-2025-12-27T04-41-02.json"}'

# Process all files in watch folder
curl -X POST "http://localhost:8000/process"
```

## API Endpoints

### Core Endpoints

- `GET /` - Dashboard with application info
- `GET /status` - Application status and stats
- `POST /process` - Manually trigger file processing
- `GET /auth/consent-url` - Get eBay OAuth consent URL
- `POST /auth/callback` - Exchange auth code for token
- `GET /test/mapper` - Test product mapper with sample data

### API Documentation

FastAPI auto-generates interactive documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## eBay API Implementation

This application follows eBay's official 2025 API standards:

### Authentication
- Uses OAuth 2.0 protocol
- Implements User Token flow for Inventory API
- Tokens auto-refresh every 2 hours
- Supports both Sandbox and Production environments

### Inventory API Flow

1. **Create Inventory Items** (bulk, max 25)
   - `POST /sell/inventory/v1/bulk_create_or_replace_inventory_item`

2. **Create Offers** (bulk, max 25)
   - `POST /sell/inventory/v1/bulk_create_offer`

3. **Publish Offers** (converts to live listings)
   - `POST /sell/inventory/v1/bulk_publish_offer`

### Best Practices Implemented

✅ Batch processing (max 25 items per request)
✅ Rate limiting with configurable delays
✅ Comprehensive error handling
✅ Complete offer details provided upfront
✅ Async/await for optimal performance
✅ Detailed logging and result tracking
✅ File-based processing with backup

## Configuration

### Pricing Strategy

Configure your markup in `.env`:

```env
PRICE_MARKUP_PERCENTAGE=20.0  # 20% markup
FIXED_MARKUP_AMOUNT=5.00      # Plus $5 fixed
```

Formula: `eBay Price = (Amazon Price × 1.20) + $5.00`

Example:
- Amazon: $29.99
- eBay: ($29.99 × 1.20) + $5.00 = $40.99

### Batch Settings

```env
MAX_ITEMS_PER_BATCH=25        # eBay API limit
PROCESSING_DELAY_SECONDS=2    # Delay between batches
```

## Data Mapping

### Amazon → eBay

| Amazon Field | eBay Field | Notes |
|-------------|------------|-------|
| asin | SKU | Prefixed with "AMZN-" |
| title | product.title | Truncated to 80 chars |
| price | pricingSummary.price | With markup applied |
| images | product.imageUrls | Max 12 images |
| description | product.description | Plain text |
| bulletPoints | listingDescription | Converted to HTML |
| specifications | aspects | Category-specific attributes |

## Troubleshooting

### Common Issues

**1. "Failed to obtain eBay access token"**
- Check your App ID and Cert ID in `.env`
- Verify you're using the correct environment (Sandbox/Production)
- Ensure credentials are not expired

**2. "Business Policies required"**
- You must create Business Policies in eBay Seller Hub first
- Update policy IDs in the code (see Advanced Setup)

**3. "Category ID required"**
- eBay requires category IDs for listings
- Use eBay's Category API to find appropriate categories
- Update the mapping logic with category detection

**4. File not processing**
- Check file name matches pattern: `amazon-products-*.json`
- Verify file is valid JSON
- Check `failed/` folder for error logs

### Logs

Application logs are output to console. For production, configure file logging:

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
```

## Advanced Setup

### Creating Full Listings

To create actual published listings (not just inventory items), you need to:

1. **Get Category IDs** for your products
   - Use eBay's Browse API or Category Tree API
   - Or manually find categories in eBay Seller Hub

2. **Get Policy IDs** from your Business Policies
   - Payment Policy ID
   - Return Policy ID
   - Fulfillment Policy ID

3. **Update the code** to create and publish offers:

```python
# In file_processor.py, add after creating inventory items:

# Create offers
offers = []
for product in products:
    offer = product_mapper.map_to_offer(
        product,
        category_id="YOUR_CATEGORY_ID",
        payment_policy_id="YOUR_PAYMENT_POLICY_ID",
        return_policy_id="YOUR_RETURN_POLICY_ID",
        fulfillment_policy_id="YOUR_FULFILLMENT_POLICY_ID"
    )
    offers.append(offer)

# Bulk create offers
offer_result = ebay_client.bulk_create_offer(offers)

# Publish offers
offer_ids = [r["offerId"] for r in offer_result["responses"] if r.get("offerId")]
publish_result = ebay_client.bulk_publish_offer(offer_ids)
```

## Production Deployment

### Environment Setup

1. Change environment to production:
```env
EBAY_ENVIRONMENT=PRODUCTION
```

2. Use production eBay credentials

3. Set up proper redirect URI (must be HTTPS)

### Security

- Never commit `.env` file to version control
- Use environment variables for sensitive data
- Implement proper access controls
- Enable HTTPS in production

### Scaling

For high-volume processing:
- Use Celery for distributed task processing
- Implement queue system (RabbitMQ/Redis)
- Add database for tracking listings
- Implement retry logic with exponential backoff

## Resources

### Official Documentation

- [eBay Developers Program](https://developer.ebay.com/)
- [eBay Inventory API](https://developer.ebay.com/api-docs/sell/inventory/overview.html)
- [OAuth 2.0 Guide](https://developer.ebay.com/api-docs/static/oauth-tokens.html)
- [Business Policies](https://www.ebay.com/help/selling/listings/creating-managing-listings/creating-business-policies?id=4212)

### API Limits

- Inventory Items: 25 per bulk request
- Offers: 25 per bulk request
- Rate Limits: Vary by account type (check eBay developer portal)

## Legal & Compliance

### Dropshipping Policy

Ensure you comply with:
- eBay's dropshipping policy
- Amazon's Terms of Service
- Product resale restrictions
- Copyright and trademark laws

### 2025 Compliance Updates

- Parts & Accessories listings require 30+ day return windows
- Seller-paid return shipping required for certain categories
- Domestic return policy compliance

## Future Enhancements

- [ ] Automatic category detection
- [ ] Image downloading and hosting
- [ ] Price monitoring and updates
- [ ] Inventory sync with Amazon availability
- [ ] Profit calculator
- [ ] Multi-marketplace support
- [ ] Database integration
- [ ] Web dashboard for listing management

## License

This is a tool for personal/business use. Ensure compliance with eBay and Amazon terms of service.

## Support

For issues and questions:
- Check the [eBay Developer Community](https://community.ebay.com/)
- Review FastAPI documentation at [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
- Check application logs for errors

---

**Built with:**
- FastAPI for high-performance async API
- eBay Inventory API (2025 standards)
- Python watchdog for file monitoring
- Pydantic for data validation

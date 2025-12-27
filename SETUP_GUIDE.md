# Quick Setup Guide

Follow these steps to get your Amazon to eBay listing system running.

## Step 1: Install Dependencies

```bash
cd ebay-listing-app
pip install -r requirements.txt
```

## Step 2: Get eBay Developer Credentials

### 2.1 Create eBay Developer Account

1. Visit https://developer.ebay.com/
2. Click "Register" (or sign in if you have an account)
3. Complete the registration

### 2.2 Create an Application

1. Go to https://developer.ebay.com/my/keys
2. Click "Create Application Keys"
3. Fill in:
   - **Application Title**: "Amazon eBay Dropship Tool"
   - **Application Type**: "Platform Notification"
4. Click "Create Application"

### 2.3 Get Your Keys

You'll receive three keys:
- **App ID (Client ID)**: Starts with "YourName-..."
- **Dev ID**: Your developer ID
- **Cert ID (Client Secret)**: Long string

### 2.4 Set Redirect URI

1. In your application settings, find "OAuth Redirect URIs"
2. For development, use: `https://localhost:8000/callback`
3. For production, use your actual domain
4. Click "Save"

## Step 3: Configure Environment

### 3.1 Create .env File

```bash
cp .env.example .env
```

### 3.2 Edit .env

Open `.env` and fill in your credentials:

```env
# From Step 2.3
EBAY_APP_ID=YourAppID-Here
EBAY_CERT_ID=YourCertIDHere
EBAY_DEV_ID=YourDevIDHere

# From Step 2.4
EBAY_REDIRECT_URI=https://localhost:8000/callback

# Start with SANDBOX for testing
EBAY_ENVIRONMENT=SANDBOX

# Set your folders
WATCH_FOLDER=c:\Users\31243\Downloads
PROCESSED_FOLDER=c:\Users\31243\ebay-listing-app\processed
FAILED_FOLDER=c:\Users\31243\ebay-listing-app\failed

# Configure your pricing
PRICE_MARKUP_PERCENTAGE=20.0
FIXED_MARKUP_AMOUNT=5.00
```

## Step 4: Set Up eBay Sandbox Account

For testing, use eBay's Sandbox environment:

### 4.1 Create Sandbox User

1. Go to https://developer.ebay.com/sandbox
2. Click "Create a test user"
3. Select "Seller" account type
4. Complete registration
5. Note your sandbox username and password

### 4.2 Create Business Policies in Sandbox

1. Go to https://sandbox.ebay.com
2. Sign in with your sandbox seller account
3. Navigate to "Account" → "Business Policies"
4. Create these policies:

#### Payment Policy
- Name: "Default Payment"
- Accepted payments: PayPal, Credit Card
- Payment instructions: "Payment due upon purchase"

#### Return Policy
- Name: "30 Day Returns"
- Returns accepted: Yes
- Return period: 30 days
- Return shipping paid by: Buyer (or Seller for better ratings)

#### Fulfillment Policy (Shipping)
- Name: "Standard Shipping"
- Handling time: 1-2 business days
- Domestic shipping service: USPS First Class
- Cost: Free or set your price

### 4.3 Note Policy IDs

After creating policies, you need to get their IDs via API or note them from the URL.

## Step 5: Authorize Your Application

### 5.1 Start the Application

```bash
python main.py
```

### 5.2 Get Consent URL

Visit: http://localhost:8000/auth/consent-url

You'll see something like:
```json
{
  "consent_url": "https://auth.sandbox.ebay.com/oauth2/authorize?client_id=...",
  "instructions": [...]
}
```

### 5.3 Authorize

1. Copy the `consent_url`
2. Open it in your browser
3. Sign in with your eBay sandbox account (or production account if not using sandbox)
4. Click "Agree" to authorize
5. You'll be redirected to your `redirect_uri` with a `code` parameter

Example redirect:
```
https://localhost:8000/callback?code=v%5E1.1%23i%5E1%23...&expires_in=299
```

### 5.4 Exchange Code for Token

Copy the `code` value and send it to the callback endpoint:

```bash
curl -X POST "http://localhost:8000/auth/callback?authorization_code=YOUR_CODE_HERE"
```

If successful, you'll see:
```json
{
  "success": true,
  "message": "Authorization successful! You can now create eBay listings.",
  "token_expires_in": "2 hours"
}
```

## Step 6: Test the System

### 6.1 Test Product Mapper

Visit: http://localhost:8000/test/mapper

This shows how Amazon products are mapped to eBay format.

### 6.2 Test with Real Data

1. Open the Amazon scraper extension
2. Go to any Amazon product page
3. Click "Scrape for eBay"
4. Click "Export All" in the extension popup
5. Save the JSON file to your watch folder (Downloads)
6. Check the application logs to see processing

### 6.3 Check Results

- **Processed files**: `ebay-listing-app/processed/`
- **Failed files**: `ebay-listing-app/failed/`
- **Results**: Look for `*_results_*.json` files

## Step 7: Moving to Production

### 7.1 Switch to Production Environment

In `.env`:
```env
EBAY_ENVIRONMENT=PRODUCTION
```

### 7.2 Get Production Keys

1. Go to https://developer.ebay.com/my/keys
2. Request production keys
3. eBay will review your application (may take a few days)
4. Replace sandbox keys with production keys in `.env`

### 7.3 Set Up Production Business Policies

1. Go to https://www.ebay.com
2. Sign in to your seller account
3. Go to Seller Hub → Account → Business Policies
4. Create production policies (same as sandbox)

### 7.4 Re-authorize for Production

Repeat Step 5 with production credentials

## Troubleshooting

### Issue: "Failed to obtain access token"

**Solution:**
- Verify credentials in `.env` are correct
- Ensure no extra spaces in credential strings
- Check you're using matching environment (sandbox keys with SANDBOX, production keys with PRODUCTION)

### Issue: "Category ID required"

**Solution:**
This MVP creates inventory items only. To create full listings, you need to:
1. Find eBay category IDs for your products
2. Update `file_processor.py` to include offer creation
3. See "Advanced Setup" in README.md

### Issue: "Business Policies not found"

**Solution:**
- Ensure you've created policies in eBay Seller Hub
- Get policy IDs from eBay API or seller hub
- Update the offer creation code with your policy IDs

### Issue: File not processing

**Solution:**
- Check file name matches pattern: `amazon-products-*.json`
- Verify JSON is valid (use JSON validator)
- Check application logs for errors
- Look in `failed/` folder for error logs

## Next Steps

### To Create Full Published Listings

The current MVP creates **inventory items** only. To create **published listings**:

1. **Get Category IDs**
   - Use eBay's GetSuggestedCategories API
   - Or browse categories at https://www.ebay.com/
   - Note category ID from URL

2. **Get Policy IDs**
   - Use eBay's Fulfillment Policy API
   - Or note IDs from Seller Hub

3. **Update Code**
   - Modify `file_processor.py`
   - Add offer creation after inventory items
   - See commented examples in the code

### Recommended Enhancements

- [ ] Implement category auto-detection
- [ ] Add inventory sync
- [ ] Set up price monitoring
- [ ] Create listing management dashboard
- [ ] Add image hosting service
- [ ] Implement order fulfillment automation

## Support Resources

- **eBay Developer Forums**: https://community.ebay.com/
- **eBay API Documentation**: https://developer.ebay.com/docs
- **FastAPI Documentation**: https://fastapi.tiangolo.com/

## Quick Reference

### Important URLs

- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Status Check**: http://localhost:8000/status
- **eBay Sandbox**: https://sandbox.ebay.com
- **eBay Production**: https://www.ebay.com
- **Developer Portal**: https://developer.ebay.com

### File Locations

```
Downloads/                          # Watch folder (JSON exports)
ebay-listing-app/
  ├── processed/                    # Successfully processed
  ├── failed/                       # Failed attempts
  └── .env                         # Your configuration
```

### Common Commands

```bash
# Start application
python main.py

# Install dependencies
pip install -r requirements.txt

# Check status
curl http://localhost:8000/status

# Manual process
curl -X POST http://localhost:8000/process
```

---

**You're all set!** Start scraping Amazon products and watch them automatically transform into eBay inventory items.

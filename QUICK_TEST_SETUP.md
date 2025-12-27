# Quick Test Setup - eBay API Integration

Follow these steps to test the application with real eBay API credentials.

## Step 1: Create eBay Developer Account (5 minutes)

### 1.1 Register
1. Go to: https://developer.ebay.com/
2. Click **"Register"** (or sign in if you have an account)
3. Use your personal eBay account or create a new one
4. Complete the registration

### 1.2 Verify Email
- Check your email for verification link
- Click to verify your developer account

## Step 2: Create Application Keys (2 minutes)

### 2.1 Access Application Keys
1. Go to: https://developer.ebay.com/my/keys
2. You'll see **"Create Application Keys"** section

### 2.2 Create Keyset
1. Click **"Get Your OAuth Credentials"**
2. Fill in the form:
   - **Application Title**: "Amazon eBay Dropship Tool"
   - **Application Type**: Choose "Platform Notification"
3. Click **"Create Application"**

### 2.3 Get Your Credentials

You'll now see three keys:

```
App ID (Client ID):    YourName-AmazonEb-SBX-abcd1234-abcd1234
Dev ID:                abcd1234-abcd-1234-abcd-123456789012
Cert ID (Secret):      SBX-abcd1234abcd-1234-5678-9012-abcd
```

**IMPORTANT**: These are **SANDBOX** keys (notice "SBX"). Perfect for testing!

## Step 3: Set Redirect URI (1 minute)

### 3.1 Configure OAuth Settings
1. Still on the keys page, scroll to **"Redirect URI"** section
2. Click **"Add Redirect URI"**
3. Enter: `https://localhost:8000/callback`
   - Or use: `https://127.0.0.1:8000/callback`
4. Click **"Save"**

**Note**: For local testing, eBay accepts localhost URIs.

## Step 4: Create .env File (2 minutes)

### 4.1 Copy Template

In your terminal:
```bash
cd c:\Users\31243\ebay-listing-app
copy .env.example .env
```

Or manually:
1. Open `.env.example`
2. Save As → `.env` (in the same folder)

### 4.2 Edit .env File

Open `.env` in any text editor and fill in your credentials:

```env
# ===== PASTE YOUR KEYS HERE =====

# From Step 2.3 - Your Application Keys
EBAY_APP_ID=YourName-AmazonEb-SBX-abcd1234-abcd1234
EBAY_CERT_ID=SBX-abcd1234abcd-1234-5678-9012-abcd
EBAY_DEV_ID=abcd1234-abcd-1234-abcd-123456789012

# From Step 3.1 - Your Redirect URI
EBAY_REDIRECT_URI=https://localhost:8000/callback

# Leave empty for now (we'll get this in Step 6)
EBAY_USER_TOKEN=

# Use SANDBOX for testing (safe, no real listings)
EBAY_ENVIRONMENT=SANDBOX

# ===== FOLDER SETTINGS (can leave as-is) =====
WATCH_FOLDER=c:\Users\31243\Downloads
PROCESSED_FOLDER=c:\Users\31243\ebay-listing-app\processed
FAILED_FOLDER=c:\Users\31243\ebay-listing-app\failed

# ===== PRICING SETTINGS =====
PRICE_MARKUP_PERCENTAGE=20.0
FIXED_MARKUP_AMOUNT=5.00

# ===== OTHER SETTINGS =====
EBAY_SITE_ID=0
MAX_ITEMS_PER_BATCH=25
PROCESSING_DELAY_SECONDS=2
HOST=0.0.0.0
PORT=8000
```

**Save the file!**

## Step 5: Create eBay Sandbox Test Account (3 minutes)

You need a **sandbox seller account** to test listings.

### 5.1 Create Test User
1. Go to: https://developer.ebay.com/my/users
2. Click **"Create a test user"**
3. Fill in:
   - **User Type**: Select **"Seller"**
   - **Site**: Select **"eBay US (EBAY-US)"**
   - Email will be auto-generated
4. Click **"Create"**

### 5.2 Note Credentials

You'll get:
```
Username: testuser_yourusername123
Password: (auto-generated)
Email: (auto-generated)
```

**SAVE THESE!** You'll need them in Step 6.

## Step 6: Start Application & Get Authorization (5 minutes)

### 6.1 Install Dependencies

```bash
cd c:\Users\31243\ebay-listing-app
pip install -r requirements.txt
```

### 6.2 Start Application

```bash
python main.py
```

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 6.3 Get Authorization URL

Open browser and visit:
```
http://localhost:8000/auth/consent-url
```

You'll see JSON response:
```json
{
  "consent_url": "https://auth.sandbox.ebay.com/oauth2/authorize?client_id=...",
  "instructions": [...]
}
```

### 6.4 Copy the Consent URL

Copy the entire `consent_url` value (it's long!)

### 6.5 Authorize Your App

1. Paste the consent URL in a new browser tab
2. You'll be redirected to eBay sandbox login
3. **Sign in with your SANDBOX TEST USER** credentials (from Step 5.2)
   - Username: `testuser_yourusername123`
   - Password: (from Step 5.2)
4. Click **"Agree"** to authorize the app

### 6.6 Get Authorization Code

After agreeing, you'll be redirected to:
```
https://localhost:8000/callback?code=v%5E1.1%23i%5E1%23...&expires_in=299
```

**Browser will show an error** (connection refused) - **THIS IS NORMAL!**

Look at the URL bar and copy the `code` parameter value.

Example URL:
```
https://localhost:8000/callback?code=v%5E1.1%23i%5E1%23p%5E1%23f%5E0%23r%5E0%23...&expires_in=299
```

Copy everything after `code=` and before `&expires_in`:
```
v%5E1.1%23i%5E1%23p%5E1%23f%5E0%23r%5E0%23...
```

### 6.7 Exchange Code for Token

Open a new terminal/command prompt and run:

```bash
curl -X POST "http://localhost:8000/auth/callback?authorization_code=PASTE_YOUR_CODE_HERE"
```

**IMPORTANT**: Replace `PASTE_YOUR_CODE_HERE` with your actual code!

If successful, you'll see:
```json
{
  "success": true,
  "message": "Authorization successful! You can now create eBay listings.",
  "token_expires_in": "2 hours"
}
```

**🎉 You're now authenticated!**

## Step 7: Test the System (2 minutes)

### 7.1 Test Product Mapper

Visit in browser:
```
http://localhost:8000/test/mapper
```

You should see JSON output showing how Amazon products are mapped to eBay format.

### 7.2 Test with Real Amazon Data

1. Open your Amazon scraper extension
2. Go to any Amazon product page
3. Click **"Scrape for eBay"**
4. In extension popup, click **"Export All"**
5. Save JSON to: `c:\Users\31243\Downloads`

### 7.3 Watch the Magic

In your terminal where the app is running, you should see:
```
INFO: New Amazon product file detected: amazon-products-2025-12-27T...json
INFO: Processing file: ...
INFO: Found 3 products to process
INFO: Processing batch 1 (3 items)
INFO: Creating 3 inventory items...
INFO: Processing complete: 3 successful, 0 failed
```

### 7.4 Check Results

Look in:
```
c:\Users\31243\ebay-listing-app\processed\
```

You'll find:
- `amazon-products-XXX.json` (original file moved here)
- `amazon-products-XXX_results_XXX.json` (processing results)

## Step 8: Verify on eBay Sandbox (Optional)

### 8.1 Login to Sandbox Seller Hub

1. Go to: https://sandbox.ebay.com
2. Sign in with your **sandbox test user** credentials
3. Go to **"Selling"** → **"Active Listings"**

**NOTE**: The MVP creates **inventory items**, not published listings yet. To see them:
- You'd need to use eBay's Inventory Management tools
- Or add the offer creation code (see Advanced Setup)

## Troubleshooting

### Error: "ValidationError: EBAY_APP_ID field required"

**Solution**: You didn't create the `.env` file. Go back to Step 4.

### Error: "Failed to obtain eBay access token"

**Solution**:
- Check credentials in `.env` are correct
- Ensure no extra spaces or quotes
- Verify you're using SANDBOX keys with `EBAY_ENVIRONMENT=SANDBOX`

### Redirect shows "Connection Refused"

**Solution**: This is NORMAL! Just copy the `code` from the URL bar.

### Error: "Invalid authorization code"

**Solution**:
- The code expires in ~5 minutes, get a new one
- Make sure you copied the entire code (it's very long)
- Don't include `&expires_in=` part

### No files being processed

**Solution**:
- Check file name matches pattern: `amazon-products-*.json`
- Verify file is in the watch folder
- Check application logs for errors

## What You've Accomplished

✅ eBay Developer account set up
✅ Application keys obtained
✅ OAuth authorization completed
✅ Application running and monitoring
✅ Successfully processing Amazon exports
✅ Creating eBay inventory items via API

## Next Steps

1. **Test with multiple products** - Scrape more Amazon items
2. **Check pricing calculations** - Verify markup is correct
3. **Review processed results** - Look at the generated JSON
4. **Set up Business Policies** - To create full published listings
5. **Add category detection** - For automatic category assignment

## Time Estimate

- **Total Setup Time**: ~20 minutes
- **Most of it**: Waiting for eBay account verification and reading instructions

## Important Notes

### About Sandbox vs Production

**SANDBOX** (current setup):
- ✅ Safe testing environment
- ✅ No real listings created
- ✅ No real money involved
- ✅ Perfect for development
- ❌ Not visible to real eBay buyers

**PRODUCTION** (later):
- ✅ Real listings on eBay.com
- ⚠️ Real money transactions
- ⚠️ Requires eBay approval
- ⚠️ Need proper business policies

### Token Expiration

eBay tokens expire every **2 hours**. The app handles this automatically, but if you get auth errors:
1. Restart the app
2. Get a new authorization code (Step 6)

### Rate Limits

eBay has API rate limits:
- Sandbox: Usually 5,000 calls/day
- Production: Varies by account type

The app respects these with delays between batches.

---

**You're ready to test!** Follow these steps and you'll see your Amazon products automatically transformed into eBay inventory items. 🚀

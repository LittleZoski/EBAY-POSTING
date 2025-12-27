# Quick Test Checklist

Follow this checklist to test your Amazon to eBay system in ~20 minutes.

## Pre-Test Setup (15 minutes)

### ☐ 1. Get eBay Developer Account
- [ ] Go to https://developer.ebay.com/
- [ ] Click "Register" and complete signup
- [ ] Verify your email

### ☐ 2. Create Application & Get Keys
- [ ] Visit https://developer.ebay.com/my/keys
- [ ] Click "Create Application Keys"
- [ ] Name it: "Amazon eBay Dropship Tool"
- [ ] Copy these three keys:
  - [ ] App ID (Client ID): `______________________________`
  - [ ] Cert ID (Secret): `______________________________`
  - [ ] Dev ID: `______________________________`

### ☐ 3. Set Redirect URI
- [ ] On the same page, find "Redirect URI"
- [ ] Click "Add Redirect URI"
- [ ] Enter: `https://localhost:8000/callback`
- [ ] Click "Save"

### ☐ 4. Create Sandbox Test Account
- [ ] Go to https://developer.ebay.com/my/users
- [ ] Click "Create a test user"
- [ ] Select "Seller" type
- [ ] Save credentials:
  - Username: `______________________________`
  - Password: `______________________________`

### ☐ 5. Create .env File
```bash
cd c:\Users\31243\ebay-listing-app
copy .env.example .env
notepad .env
```

- [ ] Paste your App ID
- [ ] Paste your Cert ID
- [ ] Paste your Dev ID
- [ ] Set redirect URI: `https://localhost:8000/callback`
- [ ] Save file

### ☐ 6. Install Dependencies
```bash
pip install -r requirements.txt
```

## Testing Phase (5 minutes)

### ☐ 7. Start Application
```bash
python main.py
```

**Expected Output**:
```
INFO:     Started server process
INFO:     Waiting for application startup.
Starting file watcher on: c:\Users\31243\Downloads
File watcher started successfully
INFO:     Application startup complete.
```

### ☐ 8. Authorize eBay Account

**8.1 Get Consent URL**
- [ ] Open browser: http://localhost:8000/auth/consent-url
- [ ] Copy the long `consent_url` value

**8.2 Authorize**
- [ ] Paste consent URL in new browser tab
- [ ] Sign in with **sandbox test user** (from Step 4)
- [ ] Click "Agree"
- [ ] Browser redirects to: `https://localhost:8000/callback?code=v%5E1.1...`
- [ ] Copy the `code` parameter value (everything after `code=` and before `&`)

**8.3 Exchange Code for Token**
```bash
curl -X POST "http://localhost:8000/auth/callback?authorization_code=YOUR_CODE_HERE"
```

**Expected Response**:
```json
{
  "success": true,
  "message": "Authorization successful!"
}
```

### ☐ 9. Test Product Mapper
- [ ] Visit: http://localhost:8000/test/mapper
- [ ] Verify JSON output shows product mapping
- [ ] Check price calculation is correct

### ☐ 10. Test with Real Amazon Data

**10.1 Scrape Amazon Product**
- [ ] Open Amazon product page
- [ ] Click extension "Scrape for eBay" button
- [ ] See success notification

**10.2 Export Data**
- [ ] Click extension icon
- [ ] Click "Export All"
- [ ] Save to: `c:\Users\31243\Downloads`

**10.3 Verify Auto-Processing**

Check application terminal for:
```
INFO: New Amazon product file detected: amazon-products-...json
INFO: Found X products to process
INFO: Creating X inventory items...
INFO: Processing complete: X successful, 0 failed
```

**10.4 Check Results**
- [ ] Open: `c:\Users\31243\ebay-listing-app\processed\`
- [ ] Find original JSON file (moved here)
- [ ] Find results file: `*_results_*.json`
- [ ] Open results file and verify:
  - [ ] "successful": X
  - [ ] "failed": 0

## Success Criteria ✅

You've successfully tested if:
- [x] Application starts without errors
- [x] eBay authorization works
- [x] Product mapping works
- [x] Files are auto-detected
- [x] Products are processed
- [x] Results saved to processed folder
- [x] No errors in failed folder

## Troubleshooting

### "Config file missing"
```bash
# Create .env file
copy .env.example .env
# Edit with your credentials
notepad .env
```

### "Failed to obtain token"
- Check credentials in .env are correct
- Ensure no extra spaces
- Verify EBAY_ENVIRONMENT=SANDBOX matches your sandbox keys

### "Connection refused" on redirect
- This is NORMAL! Just copy the `code` from URL bar

### Files not processing
- Check file name: `amazon-products-*.json`
- Verify file is in Downloads folder
- Look in failed/ folder for errors

## What Happens After Success?

### You'll See:
1. **Inventory Items Created** on eBay (sandbox)
2. **Processed Files** in processed/ folder
3. **Detailed Results** in *_results.json files

### To Create Published Listings:
1. Set up eBay Business Policies (Payment, Return, Fulfillment)
2. Get policy IDs
3. Update code to create offers
4. See README.md "Advanced Setup"

## Time Tracking

- [ ] Setup started at: ___:___
- [ ] Setup completed at: ___:___
- [ ] Total time: _____ minutes

**Target**: 20 minutes total

## Next Steps After Testing

### Immediate:
- [ ] Test with 5-10 different Amazon products
- [ ] Verify pricing calculations are profitable
- [ ] Check all product data is captured correctly

### Short Term:
- [ ] Set up eBay Business Policies
- [ ] Implement offer creation
- [ ] Test with real eBay listings (sandbox)

### Long Term:
- [ ] Move to production environment
- [ ] Scale to handle more products
- [ ] Add category auto-detection
- [ ] Implement order fulfillment

## Questions to Verify

After testing, answer these:

1. **Does the extension work?**
   - [ ] Yes - scrapes all product data
   - [ ] No - what's missing? ___________

2. **Does file monitoring work?**
   - [ ] Yes - auto-detects new files
   - [ ] No - error: ___________

3. **Is pricing correct?**
   - Amazon: $29.99
   - Expected eBay: ($29.99 × 1.20) + $5.00 = $40.99
   - [ ] Calculation is correct

4. **Are inventory items created on eBay?**
   - [ ] Yes - check sandbox seller hub
   - [ ] No - check errors in results file

## Support

If you get stuck:
- Check [QUICK_TEST_SETUP.md](QUICK_TEST_SETUP.md) for detailed steps
- Check [ENV_CONFIG_EXPLAINED.md](ENV_CONFIG_EXPLAINED.md) for .env help
- Review application logs for errors
- Look in failed/ folder for error details

---

**Ready to test?** Start at Step 1! 🚀

# Quick Reference

## Common Commands

### Start File Watcher
```bash
python main.py
```
Watches Downloads folder for Amazon product JSON files.

### Manual Processing
```bash
python complete_listing_flow_llm.py
```
Processes the most recent file in `processed/` folder.

### Clean Up Test Offers
```bash
python delete_all_offers.py
```
Deletes all unpublished offers from eBay.

### Re-authorize eBay
```bash
python authorize_once.py
```
Get fresh OAuth tokens (if expired or issues).

## File Locations

- **Drop zone**: `C:\Users\31243\Downloads\`
- **Processed**: `C:\Users\31243\ebay-listing-app\processed\`
- **Failed**: `C:\Users\31243\ebay-listing-app\failed\`

## Workflow

1. Drop `amazon-products-*.json` file in Downloads
2. File watcher detects file
3. LLM selects category (from 17,105 options)
4. System fetches category requirements
5. LLM fills required fields
6. Creates inventory + offer
7. Publishes to eBay
8. File moved to `processed/` folder

## Key Files

| File | Purpose |
|------|---------|
| `complete_listing_flow_llm.py` | Main LLM workflow |
| `file_processor.py` | File watcher logic |
| `llm_category_selector.py` | Category AI |
| `category_cache.py` | 17K+ categories cache |
| `.env` | API keys & settings |
| `business_policies_config.json` | eBay policies |

## Troubleshooting

### No items publishing?
1. Check eBay tokens: `ebay_tokens.json` should exist
2. Run `python authorize_once.py` if needed
3. Verify business policies IDs in `business_policies_config.json`

### Wrong category selected?
- LLM uses product title + description
- Prefers simpler categories (Level 2-3)
- Check category cache is recent (90-day expiry)

### "Missing required aspect"?
- Category has required fields LLM couldn't fill
- Check product data has sufficient information
- May need to use different category

## Environment Variables

Required in `.env`:
```bash
EBAY_APP_ID=...
EBAY_CERT_ID=...
EBAY_DEV_ID=...
EBAY_REDIRECT_URI=...
EBAY_ENVIRONMENT=PRODUCTION
ANTHROPIC_API_KEY=sk-ant-...
```

## Success Indicators

✅ File moved to `processed/` folder
✅ Console shows "[SUCCESS] Published listing!"
✅ Listing ID displayed: `https://www.ebay.com/itm/XXXXXXXXXX`
✅ Item visible at: https://www.ebay.com/sh/lst/active

## Common Errors

| Error | Solution |
|-------|----------|
| "No OAuth token found" | Run `authorize_once.py` |
| "Category X is invalid" | Not a leaf category - LLM will retry |
| "Missing aspect Y" | Product missing required data |
| HTTP 400 | Check business policies + location |
| HTTP 500 | Usually category/validation issue |

## Performance

- **Processing time**: 10-30 seconds per product
- **LLM cost**: ~$0.002 per product (Claude Haiku)
- **Category cache**: Updates every 90 days
- **Token expiry**: OAuth tokens valid 2 hours

## Archive Folder

Contains old scripts for reference:
- `complete_listing_flow.py` - Old non-LLM flow
- `category_detector.py` - Old keyword matching
- Various diagnostic scripts

**Don't run archived scripts** - they use old logic!

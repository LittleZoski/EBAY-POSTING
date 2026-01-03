# Multi-Account Setup Guide

This guide explains how to set up and manage multiple eBay seller accounts with your listing app.

## Overview

The app now supports **two separate eBay seller accounts**:
- **Account 1**: Your primary account
- **Account 2**: Your wife's account (or any secondary account)

Each account has:
- ✅ Its own OAuth tokens (stored separately)
- ✅ Its own business policy IDs
- ✅ Independent authentication

## Quick Start

### 1. Configure Business Policies in .env

Your `.env` file now includes business policies. Add the policy IDs for both accounts:

```bash
# Account 1 (Your Account) - Already configured
PAYMENT_POLICY_ID=370857833023
RETURN_POLICY_ID=370857832023
FULFILLMENT_POLICY_ID=370857831023

# Account 2 (Wife's Account) - Add these after authorization
PAYMENT_POLICY_ID_ACCOUNT2=<her_payment_policy_id>
RETURN_POLICY_ID_ACCOUNT2=<her_return_policy_id>
FULFILLMENT_POLICY_ID_ACCOUNT2=<her_fulfillment_policy_id>

# Which account to use for new listings (1 or 2)
ACTIVE_ACCOUNT=1
```

### 2. Authorize Each Account

#### Authorize Account 1 (Your Account)

```bash
python authorize_account.py 1
```

#### Authorize Account 2 (Wife's Account)

**IMPORTANT**: Before running this, make sure to:
1. Open https://www.ebay.com in your browser
2. Sign OUT of your eBay account
3. Close all eBay tabs
4. Then run:

```bash
python authorize_account.py 2
```

The script will:
- Open your browser to eBay's authorization page
- Prompt you to sign in to **your wife's eBay account**
- Save the tokens to `ebay_tokens_account2.json`

### 3. Get Business Policy IDs for Account 2

After authorizing Account 2, you need to get the business policy IDs from your wife's eBay account:

1. Log into her eBay Seller Hub
2. Go to Account Settings → Business Policies
3. Note down the IDs for:
   - Payment Policy
   - Return Policy
   - Fulfillment Policy
4. Add them to your `.env` file (see step 1)

### 4. Switch Between Accounts

To change which account creates listings, edit `.env`:

```bash
# Use Account 1
ACTIVE_ACCOUNT=1

# Use Account 2
ACTIVE_ACCOUNT=2
```

Then restart the app:
```bash
python main.py
```

## How It Works

### Token Storage

Each account has its own token file:
- **Account 1**: `ebay_tokens_account1.json`
- **Account 2**: `ebay_tokens_account2.json`

These files are automatically gitignored and contain:
- Access token (expires every 2 hours, auto-refreshes)
- Refresh token (valid for 18 months)

### Business Policies

The app reads business policies from your `.env` file based on the active account:

```python
# In your code, this automatically uses the right policies:
policies = settings.get_business_policies()  # Uses ACTIVE_ACCOUNT
```

### Re-authorization

You only need to re-authorize if:
- ❌ The refresh token expires (after 18 months)
- ❌ You revoke access in eBay's settings
- ❌ You delete the token file

Otherwise, tokens auto-refresh indefinitely!

## Important Notes

### ⚠️ Logout Before Authorizing Different Accounts

eBay uses browser cookies to determine which account to authorize. If you're already logged into eBay when you click "Authorize", it will use that account automatically.

**To authorize a different account:**
1. Go to https://www.ebay.com
2. Click "Sign out" (top right)
3. Close all eBay browser tabs
4. Run the authorization script
5. Sign in to the correct account when prompted

### ⚠️ One Active Account at a Time

The app processes files using ONE account at a time (set by `ACTIVE_ACCOUNT` in `.env`).

To process listings for different accounts:
1. Set `ACTIVE_ACCOUNT=1` in `.env`
2. Run the app, process files
3. Stop the app
4. Set `ACTIVE_ACCOUNT=2` in `.env`
5. Run the app again

### ⚠️ Separate Product Folders (Optional)

Consider organizing your product files by account:

```
Downloads/
├── account1/
│   └── amazon-products-*.json
└── account2/
    └── amazon-products-*.json
```

Then update `WATCH_FOLDER` in `.env` when switching accounts.

## Troubleshooting

### "Already logged in" Problem

**Problem**: When I run `authorize_account.py`, eBay shows I'm already logged in to the wrong account.

**Solution**:
1. Sign out from eBay.com
2. Clear your browser cookies for ebay.com
3. Close all eBay tabs
4. Try again

### Wrong Account Authorized

**Problem**: I authorized the wrong account!

**Solution**:
1. Delete the token file: `del ebay_tokens_account2.json`
2. Sign out from eBay
3. Run `python authorize_account.py 2` again
4. Sign in to the correct account

### Account 2 Tokens Not Loading

**Problem**: App says "No valid OAuth token found for Account 2"

**Solution**:
1. Make sure `ACTIVE_ACCOUNT=2` in `.env`
2. Verify `ebay_tokens_account2.json` exists
3. Try running `python authorize_account.py 2` again

## Advanced: Adding More Accounts

The current implementation supports 2 accounts, but you can extend it:

1. Update [config.py](config.py):
   - Add `payment_policy_id_account3`, etc.

2. Update [token_manager.py](token_manager.py):
   - Add `TOKEN_FILE_ACCOUNT3`
   - Update `get_token_manager()` function

3. Update `.env`:
   - Add policy IDs for account 3

## Files Modified

- ✅ [config.py](config.py) - Business policies moved here
- ✅ [.env](.env) - Now includes business policies
- ✅ [token_manager.py](token_manager.py) - Multi-account token management
- ✅ [authorize_account.py](authorize_account.py) - New authorization script
- ✅ [main.py](main.py) - Loads tokens based on active account
- ✅ [.gitignore](.gitignore) - Token files protected

## Need Help?

If you have questions or run into issues, check:
1. This guide
2. [INSTRUCTIONS.md](INSTRUCTIONS.md) for general setup
3. eBay Developer Documentation: https://developer.ebay.com/api-docs/

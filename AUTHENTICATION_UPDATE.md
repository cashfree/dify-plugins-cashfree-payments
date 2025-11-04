# Authentication System Updates - Cashfree Payments Plugin

## Summary of Changes

This document outlines the comprehensive changes made to transition the Cashfree Payments plugin from bearer token authentication to a more robust client credentials + public key signature system.

## Changes Made

### 1. Provider Configuration (`provider/cashfree_payments.yaml`)

**Before:**
- Auth methods: `client_credentials` and `bearer_token`
- Required `bearer_token` field for token-based auth

**After:**
- Auth methods: `client_credentials` and `public_key`
- Added `cashfree_public_key` field for RSA public key in PEM format
- Removed `bearer_token` field

### 2. Provider Implementation (`provider/cashfree_payments.py`)

**Simplified Structure:**
- Moved authentication logic to separate utility module (`auth_utils.py`)
- Provider now only handles credential validation
- Uses `parse_public_key()` from auth_utils for public key validation

### 3. Authentication Utilities (`auth_utils.py`) - **NEW FILE**

**Core Functions:**
- `parse_public_key()`: Validates and parses RSA public key in PEM format
- `generate_signature()`: Creates RSA-encrypted signature using client_id + timestamp
- `get_bearer_token()`: Calls Cashfree authorize API to get bearer token
- `get_auth_headers()`: Returns appropriate headers based on auth method

### 4. Dependencies (`requirements.txt`)

**Added:**
- `cryptography>=3.4.8` for RSA encryption operations
- `requests>=2.25.1` for HTTP requests

### 5. Tool Updates

**All tools updated to use the new authentication system:**

1. **Cashgram Tools** (use Payout API without x-api-version):
   - `create_cashgram.py`
   - `deactivate_cashgram.py`

2. **Payment Tools** (use Payments API with x-api-version):
   - `get_order.py`
   - `fetch_payment_link_details.py`
   - `get_order_refunds.py`
   - `create_payment_link.py`
   - `cancel_payment_link.py`
   - `create_refund.py`
   - `create_order.py`
   - `get_payment_link_orders.py`

**Changes in each tool:**
- Added `from auth_utils import get_auth_headers` import
- Replaced `bearer_token` auth method with `public_key`
- Updated credential validation to check for public key requirements
- Replaced `self.runtime.provider.get_auth_headers()` with `get_auth_headers()`
- Removed `api_version` dependency (now handled by auth_utils)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Dify Plugin                          │
├─────────────────────────────────────────────────────────────┤
│  Provider (cashfree_payments.py)                           │
│  - Credential validation only                              │
│  - Validates public key format                             │
├─────────────────────────────────────────────────────────────┤
│  Auth Utils (auth_utils.py)                                │
│  - RSA signature generation                                │
│  - Bearer token retrieval                                  │
│  - Header construction                                      │
├─────────────────────────────────────────────────────────────┤
│  Tools (tools/*.py)                                        │
│  - Import get_auth_headers from auth_utils                 │
│  - Call get_auth_headers(credentials, include_api_version) │
│  - Handle authentication errors gracefully                 │
└─────────────────────────────────────────────────────────────┘
```

## Authentication Flow

### Client Credentials Method
- Uses `x-client-id` and `x-client-secret` headers directly
- Works for both Payments API and Payout API operations
- No additional processing required

### Public Key Signature Method
**Important:** Public key authentication with bearer tokens is **only used for Payout API operations** (Cashgram create/deactivate).

#### For Payout API (Cashgram operations):
1. Generate signature using client_id + epoch timestamp
2. Encrypt signature with RSA public key (OAEP padding, SHA-1)
3. Call `/payout/v1/authorize` with signature headers
4. Extract bearer token from response
5. Use bearer token for subsequent Payout API calls

#### For Payments API (all other operations):
- Even with `public_key` auth method selected, these operations still use direct client credentials
- Uses `x-client-id` and `x-client-secret` headers (same as client_credentials method)
- No bearer token required or used

## Benefits

1. **Automated Token Management**: Eliminates need for manual bearer token updates
2. **Enhanced Security**: Uses RSA encryption for signature generation
3. **Workflow Friendly**: Tokens auto-refresh, preventing workflow interruption
4. **Modular Architecture**: Authentication logic separated from tools
5. **Consistent Headers**: Uniform header management across all tools
6. **Error Handling**: Graceful authentication failure handling

## API Endpoints Used

### Cashfree APIs Overview
Cashfree has two separate API systems:

1. **Payments API** (`api.cashfree.com/pg`) - For payment processing, orders, refunds, payment links
2. **Payout API** (`payout-api.cashfree.com`) - For cashgram operations and payouts

### Authentication by API Type

#### Payments API Operations:
- **Always use client credentials** (regardless of auth_method setting)
- Endpoints: `https://api.cashfree.com/pg` (production) / `https://sandbox.cashfree.com/pg` (sandbox)
- Headers: `x-client-id`, `x-client-secret`, `x-api-version`
- Tools: get_order, create_order, create_payment_link, fetch_payment_link_details, etc.

#### Payout API Operations (Cashgram):
- **Use bearer token when public_key auth is selected**
- **Use client credentials when client_credentials auth is selected**
- Endpoints: `https://payout-api.cashfree.com` (production) / `https://payout-gamma.cashfree.com` (sandbox)
- Tools: create_cashgram, deactivate_cashgram

### Authorization (for public key method on Payout API):
- Production: `https://payout-api.cashfree.com/payout/v1/authorize`
- Sandbox: `https://payout-gamma.cashfree.com/payout/v1/authorize`

### Required Headers for Authorization:
- `x-client-id`: Client ID
- `x-client-secret`: Client Secret  
- `x-cf-signature`: RSA encrypted signature
- `Content-Type`: application/json

## File Structure

```
├── auth_utils.py                    # NEW: Authentication utilities
├── provider/
│   └── cashfree_payments.py         # UPDATED: Simplified provider
│   └── cashfree_payments.yaml       # UPDATED: New auth method
├── tools/
│   ├── create_cashgram.py           # UPDATED: Uses auth_utils
│   ├── deactivate_cashgram.py       # UPDATED: Uses auth_utils
│   ├── get_order.py                 # UPDATED: Uses auth_utils
│   ├── fetch_payment_link_details.py # UPDATED: Uses auth_utils
│   ├── get_order_refunds.py         # UPDATED: Uses auth_utils
│   ├── create_payment_link.py       # UPDATED: Uses auth_utils
│   ├── cancel_payment_link.py       # UPDATED: Uses auth_utils
│   ├── create_refund.py             # UPDATED: Uses auth_utils
│   ├── create_order.py              # UPDATED: Uses auth_utils
│   └── get_payment_link_orders.py   # UPDATED: Uses auth_utils
├── requirements.txt                 # UPDATED: Added cryptography
└── AUTHENTICATION_UPDATE.md         # NEW: This documentation
```

## Notes

- All import errors in the code are expected and will resolve when the plugin runs in the Dify environment
- The signature generation follows the Java implementation pattern provided
- Bearer tokens are automatically managed and refreshed as needed
- Public key must be in PEM format with proper BEGIN/END markers
- The modular structure makes it easy to maintain and test authentication logic separately

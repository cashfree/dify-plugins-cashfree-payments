#!/usr/bin/env python3
"""
Test the complete cashgram flow including bearer token and API call
This matches the curl command you provided
"""

import sys
import os
import requests
import json

sys.path.insert(0, os.getcwd())

def test_cashgram_api_call():
    """Test the complete flow: get bearer token + call cashgram API"""
    
    print("=== Cashfree Cashgram API Test ===")
    print()
    
    # Get credentials from user
    client_id = input("Enter your Client ID: ").strip()
    if not client_id:
        print("Client ID is required!")
        return
    
    client_secret = input("Enter your Client Secret: ").strip()
    if not client_secret:
        print("Client Secret is required!")
        return
    
    print("\nEnter your Public Key (paste the entire key including headers):")
    print("Paste your key and press Enter twice when done:")
    public_key_lines = []
    while True:
        line = input()
        if line.strip() == "" and public_key_lines:
            break
        public_key_lines.append(line)
    
    public_key = "\n".join(public_key_lines)
    if not public_key.strip():
        print("Public Key is required!")
        return
    
    environment = input("Enter environment (sandbox/production) [sandbox]: ").strip() or "sandbox"
    
    # Prepare credentials
    credentials = {
        "auth_method": "public_key",
        "cashfree_environment": environment,
        "cashfree_client_id": client_id,
        "cashfree_client_secret": client_secret,
        "cashfree_public_key": public_key
    }
    
    print(f"\n=== Testing Bearer Token + Cashgram API Call ===")
    print(f"Environment: {environment}")
    print()
    
    try:
        from auth_utils import get_bearer_token
        
        # Step 1: Get Bearer Token
        print("Step 1: Getting bearer token...")
        print("-" * 40)
        
        try:
            bearer_token = get_bearer_token(credentials)
            print(f"✓ Bearer token obtained: {bearer_token[:20]}...")
        except Exception as e:
            print(f"✗ Bearer token failed: {e}")
            return False
        
        # Step 2: Test Cashgram API Call (exactly like your curl)
        print(f"\nStep 2: Testing cashgram API call...")
        print("-" * 40)
        
        # Determine API URL
        if environment == "production":
            api_url = "https://payout-api.cashfree.com/payout/v1/createCashgram"
        else:
            api_url = "https://payout-gamma.cashfree.com/payout/v1/createCashgram"
        
        # Prepare headers (matching your curl exactly)
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'content-type': 'application/json',
            'kong-debug': '1'
        }
        
        # Request body (empty object like your curl)
        request_body = {}
        
        print(f"API URL: {api_url}")
        print(f"Headers: {json.dumps(headers, indent=2)}")
        print(f"Request Body: {json.dumps(request_body)}")
        print()
        
        # Make the API call
        response = requests.post(api_url, headers=headers, json=request_body, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        print()
        
        if response.status_code == 200:
            print("✓ API call successful!")
            return True
        elif response.status_code == 400:
            print("⚠️  Expected 400 error (empty request body)")
            print("This confirms the token is VALID but request is incomplete")
            return True
        elif response.status_code == 401:
            print("✗ 401 Unauthorized - Token is invalid")
            return False
        elif response.status_code == 403:
            print("✗ 403 Forbidden - Token valid but no permission")
            return False
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            return False
            
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're in the right directory with auth_utils.py")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def test_manual_token():
    """Test with a manually provided bearer token"""
    print("=== Manual Bearer Token Test ===")
    print()
    
    token = input("Enter your bearer token: ").strip()
    if not token:
        print("Token is required!")
        return
    
    environment = input("Enter environment (sandbox/production) [sandbox]: ").strip() or "sandbox"
    
    # Determine API URL
    if environment == "production":
        api_url = "https://payout-api.cashfree.com/payout/v1/createCashgram"
    else:
        api_url = "https://payout-gamma.cashfree.com/payout/v1/createCashgram"
    
    # Test the API call
    headers = {
        'Authorization': f'Bearer {token}',
        'content-type': 'application/json',
        'kong-debug': '1'
    }
    
    print(f"Testing: {api_url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print()
    
    try:
        response = requests.post(api_url, headers=headers, json={}, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 400:
            print("✓ Token is valid (400 = bad request due to empty body)")
        elif response.status_code == 401:
            print("✗ Token is invalid (401 = unauthorized)")
        else:
            print(f"⚠️  Unexpected response: {response.status_code}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Complete flow (generate token + test API)")
    print("2. Test with existing bearer token")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("\n⚠️  This will make real API calls to Cashfree!")
        confirm = input("Continue? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            test_cashgram_api_call()
        else:
            print("Test cancelled.")
    elif choice == "2":
        test_manual_token()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice")

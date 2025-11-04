#!/usr/bin/env python3
"""
Test cashgram authentication with debug output
"""

import sys
import os
sys.path.insert(0, os.getcwd())

from auth_utils import get_auth_headers, get_bearer_token

def test_cashgram_auth():
    """Test the authentication for cashgram operations"""
    
    # Dummy credentials for testing - replace with real ones
    test_credentials = {
        "auth_method": "public_key",
        "cashfree_environment": "sandbox",
        "cashfree_client_id": "your_client_id_here",
        "cashfree_client_secret": "your_client_secret_here",
        "cashfree_public_key": """-----BEGIN PUBLIC KEY-----
your_actual_public_key_content_here
-----END PUBLIC KEY-----"""
    }
    
    print("=== Testing Cashgram Authentication ===")
    print()
    
    try:
        # Test getting auth headers for payout API (cashgram)
        print("Getting authentication headers for cashgram (payout API)...")
        headers = get_auth_headers(test_credentials, include_api_version=False, is_payout_api=True)
        
        print("\n✓ Authentication headers generated successfully!")
        print(f"Headers: {headers}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Authentication failed: {e}")
        return False

if __name__ == "__main__":
    print("This test requires real credentials.")
    print("Please edit the test_credentials in the script with your actual:")
    print("- cashfree_client_id")
    print("- cashfree_client_secret") 
    print("- cashfree_public_key")
    print()
    
    # Uncomment the line below after adding real credentials
    # test_cashgram_auth()
    
    print("After adding credentials, uncomment the test_cashgram_auth() call to run the test.")

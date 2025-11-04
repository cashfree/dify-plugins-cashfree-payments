#!/usr/bin/env python3
"""
Test the complete authentication flow for Cashfree payments
This tests both signature generation and bearer token retrieval
"""

import sys
import os

# Add the current directory to sys.path so we can import auth_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_utils import generate_signature, get_bearer_token

def test_auth_flow():
    """Test the complete authentication flow"""
    
    # Test credentials - replace with your actual values
    test_credentials = {
        "client_id": "your_client_id_here",
        "client_secret": "your_client_secret_here", 
        "public_key": """-----BEGIN PUBLIC KEY-----
your_public_key_content_here
-----END PUBLIC KEY-----""",
        "environment": "sandbox"  # or "production"
    }
    
    print("=== Testing Cashfree Authentication Flow ===")
    print()
    
    # Test 1: Signature Generation
    print("1. Testing signature generation...")
    try:
        signature = generate_signature(
            test_credentials["client_id"], 
            test_credentials["public_key"]
        )
        print(f"✓ Signature generated successfully")
        print()
    except Exception as e:
        print(f"✗ Signature generation failed: {e}")
        return False
    
    # Test 2: Bearer Token Retrieval
    print("2. Testing bearer token retrieval...")
    try:
        token = get_bearer_token(
            test_credentials["client_id"],
            test_credentials["client_secret"],
            test_credentials["public_key"],
            test_credentials["environment"]
        )
        print(f"✓ Bearer token retrieved successfully: {token[:20]}...")
        print()
        return True
    except Exception as e:
        print(f"✗ Bearer token retrieval failed: {e}")
        return False

def test_signature_only():
    """Test just the signature generation with dummy data"""
    print("=== Testing Signature Generation Only ===")
    print()
    
    # Use dummy data for testing
    dummy_client_id = "TEST_CLIENT_123"
    dummy_public_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyour_public_key_content_here
-----END PUBLIC KEY-----"""
    
    try:
        signature = generate_signature(dummy_client_id, dummy_public_key)
        print(f"✓ Signature generation test passed")
        return True
    except Exception as e:
        print(f"✗ Signature generation test failed: {e}")
        return False

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Full authentication flow (requires real credentials)")
    print("2. Signature generation only (uses dummy data)")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\nNote: Please edit this script and add your real credentials before running full test")
        # test_auth_flow()
        print("Edit the test_credentials in test_auth_flow() function first")
    elif choice == "2":
        test_signature_only()
    else:
        print("Invalid choice")

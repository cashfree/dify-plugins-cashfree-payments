#!/usr/bin/env python3
"""
Comprehensive test for Cashfree authentication debugging
Run this with your real credentials to see detailed debug output
"""

import sys
import os
sys.path.insert(0, os.getcwd())

def test_complete_auth_flow():
    """Test the complete authentication flow with real credentials"""
    
    print("=== Cashfree Authentication Debug Test ===")
    print()
    print("Please provide your real credentials for testing:")
    print()
    
    # Get credentials from user input
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
    
    # Test credentials
    test_credentials = {
        "auth_method": "public_key",
        "cashfree_environment": environment,
        "cashfree_client_id": client_id,
        "cashfree_client_secret": client_secret,
        "cashfree_public_key": public_key
    }
    
    print(f"\n=== Testing with environment: {environment} ===")
    print()
    
    try:
        from auth_utils import get_auth_headers, generate_signature, get_bearer_token
        
        # Test 1: Public Key Parsing
        print("1. Testing public key parsing...")
        try:
            from auth_utils import parse_public_key
            parsed_key = parse_public_key(public_key)
            print("✓ Public key parsed successfully")
        except Exception as e:
            print(f"✗ Public key parsing failed: {e}")
            return
        
        # Test 2: Signature Generation
        print("\n2. Testing signature generation...")
        try:
            signature = generate_signature(client_id, public_key)
            print("✓ Signature generated successfully")
        except Exception as e:
            print(f"✗ Signature generation failed: {e}")
            return
        
        # Test 3: Bearer Token Retrieval
        print("\n3. Testing bearer token retrieval...")
        try:
            token = get_bearer_token(test_credentials)
            print("✓ Bearer token retrieved successfully")
        except Exception as e:
            print(f"✗ Bearer token retrieval failed: {e}")
            return
        
        # Test 4: Complete Auth Headers
        print("\n4. Testing complete auth headers for cashgram...")
        try:
            headers = get_auth_headers(test_credentials, include_api_version=False, is_payout_api=True)
            print("✓ Auth headers generated successfully")
            print(f"Final headers: {headers}")
        except Exception as e:
            print(f"✗ Auth headers generation failed: {e}")
            return
        
        print("\n🎉 All tests passed! Your authentication should work now.")
        return True
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running this from the plugin directory with dependencies installed.")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

def test_with_dummy_data():
    """Test with dummy data to check basic functionality"""
    print("=== Testing with dummy data ===")
    
    try:
        from auth_utils import parse_public_key
        
        # Test public key parsing with obviously invalid data
        test_key = """-----BEGIN PUBLIC KEY-----
INVALID_KEY_DATA_FOR_TESTING
-----END PUBLIC KEY-----"""
        
        try:
            parse_public_key(test_key)
            print("✗ Should have failed with invalid key")
        except Exception as e:
            print(f"✓ Correctly rejected invalid key: {e}")
            
    except ImportError as e:
        print(f"Import error: {e}")

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Complete authentication test (requires real credentials)")
    print("2. Basic functionality test (uses dummy data)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("\n⚠️  WARNING: This will make real API calls to Cashfree!")
        print("Only proceed if you want to test with real credentials.")
        confirm = input("Continue? (y/N): ").strip().lower()
        if confirm in ['y', 'yes']:
            test_complete_auth_flow()
        else:
            print("Test cancelled.")
    elif choice == "2":
        test_with_dummy_data()
    elif choice == "3":
        print("Goodbye!")
    else:
        print("Invalid choice")

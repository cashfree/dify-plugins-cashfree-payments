"""
Authentication utilities for Cashfree Payments Plugin
Handles RSA signature generation and bearer token retrieval
"""

from typing import Any, Dict
import base64
import time
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


def parse_public_key(public_key_content: str):
    """Parse and validate the RSA public key"""
    try:
        # Clean the public key content following Java implementation
        cleaned_key = public_key_content.strip()
        
        # Remove tabs, newlines, and carriage returns
        cleaned_key = cleaned_key.replace('\t', '').replace('\n', '').replace('\r', '')
        
        # Remove PEM headers and footers
        cleaned_key = cleaned_key.replace("-----BEGIN PUBLIC KEY-----", "").replace("-----END PUBLIC KEY-----", "")
        
        # Remove any remaining whitespace
        cleaned_key = cleaned_key.strip()
        
        # Decode base64 to get raw key bytes
        key_bytes = base64.b64decode(cleaned_key)
        
        # Parse the public key using DER format (equivalent to X509EncodedKeySpec in Java)
        public_key = serialization.load_der_public_key(key_bytes, backend=default_backend())
        
        return public_key
    except Exception as e:
        raise ValueError(f"Failed to parse public key: {str(e)}")


def generate_signature(client_id: str, public_key_content: str) -> str:
    """Generate RSA encrypted signature using public key"""
    try:
        # Create client_id with epoch timestamp
        epoch_timestamp = int(time.time())
        client_id_with_timestamp = f"{client_id}.{epoch_timestamp}"
        
        print(f"[DEBUG] Signature generation:")
        print(f"[DEBUG] Client ID: {client_id}")
        print(f"[DEBUG] Timestamp: {epoch_timestamp}")
        print(f"[DEBUG] Data to encrypt: {client_id_with_timestamp}")
        
        # Parse the public key
        public_key = parse_public_key(public_key_content)
        
        # Encrypt using RSA/OAEP padding (equivalent to Java's RSA/ECB/OAEPWithSHA-1AndMGF1Padding)
        encrypted_data = public_key.encrypt(
            client_id_with_timestamp.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        
        # Encode to base64
        encrypted_signature = base64.b64encode(encrypted_data).decode('utf-8')
        
        print(f"[DEBUG] Generated signature length: {len(encrypted_signature)}")
        print(f"[DEBUG] Generated signature: {encrypted_signature}")
        
        return encrypted_signature
        
    except Exception as e:
        raise Exception(f"Failed to generate signature: {str(e)}")


def get_bearer_token(credentials: dict[str, Any]) -> str:
    """Get bearer token from Cashfree authorize API"""
    try:
        environment = credentials.get("cashfree_environment", "sandbox")
        client_id = credentials.get("cashfree_client_id")
        client_secret = credentials.get("cashfree_client_secret")
        public_key = credentials.get("cashfree_public_key")
        
        # Generate signature
        signature = generate_signature(client_id, public_key)
        
        # Determine API URL based on environment
        if environment == "production":
            api_url = "https://payout-api.cashfree.com/payout/v1/authorize"
        else:
            api_url = "https://payout-gamma.cashfree.com/payout/v1/authorize"
        
        print(f"[DEBUG] Bearer token request URL: {api_url}")
        print(f"[DEBUG] Generated signature: {signature}")
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "X-Client-Id": client_id,
            "X-Client-Secret": client_secret,
            "X-Cf-Signature": signature
        }
        
        print(f"[DEBUG] Request headers: {headers}")
        
        # Make the authorize request
        response = requests.post(api_url, headers=headers, json={}, timeout=30)
        
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response body: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            bearer_token = response_data.get("data", {}).get("token")
            if bearer_token:
                print(f"[DEBUG] Successfully obtained bearer token: {bearer_token[:20]}...")
                return bearer_token
            else:
                raise Exception(f"Bearer token not found in response. Response structure: {response_data}")
        else:
            error_msg = f"Failed to get bearer token. Status: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f", Message: {error_data.get('message', 'Unknown error')}"
                # Add more details for debugging
                if 'subCode' in error_data:
                    error_msg += f", SubCode: {error_data['subCode']}"
                if 'status' in error_data:
                    error_msg += f", Status: {error_data['status']}"
            except:
                error_msg += f", Response: {response.text}"
            raise Exception(error_msg)
            
    except Exception as e:
        raise Exception(f"Bearer token retrieval failed: {str(e)}")


def get_auth_headers(credentials: dict[str, Any], include_api_version: bool = True, is_payout_api: bool = False) -> Dict[str, str]:
    """Get authentication headers based on the configured auth method"""
    auth_method = credentials.get("auth_method", "client_credentials")
    headers = {"Content-Type": "application/json"}
    
    # Add API version if requested (only for Payments API, not Payout API)
    if include_api_version and not is_payout_api:
        api_version = credentials.get("cashfree_api_version", "2025-01-01")
        headers["X-Api-Version"] = api_version
    
    if auth_method == "client_credentials":
        headers["X-Client-Id"] = credentials["cashfree_client_id"]
        headers["X-Client-Secret"] = credentials["cashfree_client_secret"]
    elif auth_method == "public_key":
        # For public key auth, only use bearer token for payout/cashgram operations
        if is_payout_api:
            # Get bearer token for payout operations (cashgram)
            bearer_token = get_bearer_token(credentials)
            headers["Authorization"] = f"Bearer {bearer_token}"
        else:
            # For regular payment operations, use client credentials even with public_key method
            headers["X-Client-Id"] = credentials["cashfree_client_id"]
            headers["X-Client-Secret"] = credentials["cashfree_client_secret"]
    
    return headers

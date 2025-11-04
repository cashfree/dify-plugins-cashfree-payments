import requests
import json
import uuid
import re
from collections.abc import Generator
from typing import Any, Dict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from auth_utils import get_auth_headers

class DeactivateCashgramTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # Initialize a consistent response structure
        response_data: Dict[str, Any] = {
            "status_code": None,
            "success": False,
            "api_response": None,
            "message": "",
            "cashgram_id": None,
            "status": None
        }

        # --- 1. Retrieve & Validate Required Inputs ---
        cashgram_id = tool_parameters.get("cashgramId")

        # Validate required parameters
        if not cashgram_id:
            response_data["message"] = "Fatal Error: cashgramId is required"
            yield self.create_json_message(response_data)
            return

        # Validate cashgram_id format
        if not (1 <= len(cashgram_id) <= 35):
            response_data["message"] = "Fatal Error: cashgramId must be between 1 and 35 characters"
            yield self.create_json_message(response_data)
            return
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', cashgram_id):
            response_data["message"] = "Fatal Error: cashgramId can only contain alphanumeric characters, '_' and '-'"
            yield self.create_json_message(response_data)
            return

        # --- 2. Retrieve Credentials ---
        try:
            credentials = self.runtime.credentials
            environment = credentials.get("cashfree_environment", "sandbox")
            auth_method = credentials.get("auth_method", "client_credentials")
            
            # Validate that we have the required credentials for the selected auth method
            if auth_method == "client_credentials":
                if not (credentials.get("cashfree_client_id") and credentials.get("cashfree_client_secret")):
                    response_data["message"] = "Fatal Error: Cashfree client credentials (Client ID/Secret) are missing."
                    yield self.create_json_message(response_data)
                    return
            elif auth_method == "public_key":
                required_fields = ["cashfree_client_id", "cashfree_client_secret", "cashfree_public_key"]
                missing_fields = [field for field in required_fields if not credentials.get(field)]
                if missing_fields:
                    response_data["message"] = f"Fatal Error: Missing required fields for public key auth: {', '.join(missing_fields)}"
                    yield self.create_json_message(response_data)
                    return
                    
        except Exception as e:
            response_data["message"] = f"Fatal Error: Failed to retrieve credentials: {str(e)}"
            yield self.create_json_message(response_data)
            return

        # --- 3. Construct API URL and Headers ---
        # Note: Cashgram uses Payout API, different base URL
        base_url = "https://payout-api.cashfree.com" if environment == "production" else "https://payout-gamma.cashfree.com"
        api_url = f"{base_url}/payout/v1/deactivateCashgram"
        
        # Get authentication headers from auth utils (excluding x-api-version for cashgram)
        try:
            headers = get_auth_headers(credentials, include_api_version=False, is_payout_api=True)
        except Exception as e:
            response_data["message"] = f"Fatal Error: Authentication failed: {str(e)}"
            yield self.create_json_message(response_data)
            return

        # --- 4. Build Request Body ---
        request_body = {
            "cashgramId": cashgram_id
        }

        # --- 5. Execute API Call (POST request) ---
        try:
            response = requests.post(api_url, headers=headers, json=request_body, timeout=30)
            
            # Update base status information
            response_data["status_code"] = response.status_code
            response_data["success"] = (response.status_code == 200)

            # Attempt to parse JSON body
            try:
                raw_api_data = response.json()
                response_data["api_response"] = raw_api_data
                
                if response_data["success"]:
                    # Extract key information for success response
                    response_data["cashgram_id"] = raw_api_data.get("cashgramId")
                    response_data["status"] = raw_api_data.get("status")
                    response_data["message"] = f"Cashgram deactivated successfully. Cashgram ID: {response_data['cashgram_id']}, Status: {response_data['status']}"
                else:
                    # Handle error response
                    error_message = raw_api_data.get('message', f"API returned error status {response.status_code}")
                    
                    # Check for common deactivation errors
                    if response.status_code == 400:
                        if "already deactivated" in error_message.lower():
                            response_data["message"] = f"Cashgram '{cashgram_id}' is already deactivated"
                        elif "expired" in error_message.lower():
                            response_data["message"] = f"Cashgram '{cashgram_id}' has already expired"
                        elif "not found" in error_message.lower():
                            response_data["message"] = f"Cashgram '{cashgram_id}' not found"
                        elif "claimed" in error_message.lower():
                            response_data["message"] = f"Cashgram '{cashgram_id}' has already been claimed and cannot be deactivated"
                        else:
                            response_data["message"] = f"Cannot deactivate Cashgram: {error_message}"
                    elif response.status_code == 401:
                        response_data["message"] = "Authentication failed. Please check your credentials"
                    elif response.status_code == 403:
                        response_data["message"] = "Access forbidden. Please check your permissions"
                    elif response.status_code == 404:
                        response_data["message"] = f"Cashgram '{cashgram_id}' not found"
                    elif response.status_code == 422:
                        response_data["message"] = f"Cashgram '{cashgram_id}' cannot be deactivated (may have been claimed or expired)"
                    else:
                        response_data["message"] = error_message

            except json.JSONDecodeError:
                # Handle cases where the server returns a non-JSON body
                response_data["api_response"] = {"raw_text": response.text}
                response_data["message"] = f"API returned non-JSON response with status code {response.status_code}."
            
            # 6. Yield the final, standardized JSON message
            yield self.create_json_message(response_data)

        except requests.exceptions.RequestException as e:
            # Handle connection or timeout errors
            response_data["status_code"] = 0 
            response_data["success"] = False
            response_data["message"] = f"Network Error: Could not connect to API within timeout. Details: {str(e)}"
            
            yield self.create_json_message(response_data)

import requests
import json
import uuid
import re
from collections.abc import Generator
from typing import Any, Dict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class CancelPaymentLinkTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # Initialize a consistent response structure
        response_data: Dict[str, Any] = {
            "status_code": None,
            "success": False,
            "api_response": None,
            "message": "",
            "link_id": None,
            "link_status": None
        }

        # --- 1. Retrieve & Validate Required Inputs ---
        link_id = tool_parameters.get("link_id")

        # Validate required parameters
        if not link_id:
            response_data["message"] = "Fatal Error: link_id is required"
            yield self.create_json_message(response_data)
            return

        # Validate link_id format
        if not (1 <= len(link_id) <= 50):
            response_data["message"] = "Fatal Error: link_id must be between 1 and 50 characters"
            yield self.create_json_message(response_data)
            return
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', link_id):
            response_data["message"] = "Fatal Error: link_id can only contain alphanumeric characters, '_' and '-'"
            yield self.create_json_message(response_data)
            return

        # --- 2. Retrieve Credentials ---
        try:
            credentials = self.runtime.credentials
            environment = credentials.get("cashfree_environment", "sandbox")
            api_version = credentials.get("cashfree_api_version", "2025-01-01")
            auth_method = credentials.get("auth_method", "client_credentials")
            
            # Validate that we have the required credentials for the selected auth method
            if auth_method == "client_credentials":
                if not (credentials.get("cashfree_client_id") and credentials.get("cashfree_client_secret")):
                    response_data["message"] = "Fatal Error: Cashfree client credentials (Client ID/Secret) are missing."
                    yield self.create_json_message(response_data)
                    return
            elif auth_method == "bearer_token":
                if not credentials.get("bearer_token"):
                    response_data["message"] = "Fatal Error: Cashfree bearer token is missing."
                    yield self.create_json_message(response_data)
                    return
                    
        except Exception as e:
            response_data["message"] = f"Fatal Error: Failed to retrieve credentials: {str(e)}"
            yield self.create_json_message(response_data)
            return

        # --- 3. Construct API URL and Headers ---
        base_url = "https://api.cashfree.com/pg" if environment == "production" else "https://sandbox.cashfree.com/pg"
        api_url = f"{base_url}/links/{link_id}/cancel"
        
        # Build authentication headers based on auth method
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-api-version": api_version,
            "x-request-id": str(uuid.uuid4())
        }
        
        if auth_method == "client_credentials":
            headers["x-client-id"] = credentials.get("cashfree_client_id")
            headers["x-client-secret"] = credentials.get("cashfree_client_secret")
        elif auth_method == "bearer_token":
            headers["Authorization"] = f"Bearer {credentials.get('bearer_token')}"

        # --- 4. Execute API Call (POST request) ---
        try:
            response = requests.post(api_url, headers=headers, timeout=30)
            
            # Update base status information
            response_data["status_code"] = response.status_code
            response_data["success"] = (response.status_code == 200)

            # Attempt to parse JSON body
            try:
                raw_api_data = response.json()
                response_data["api_response"] = raw_api_data
                
                if response_data["success"]:
                    # Extract key information for success response
                    response_data["link_id"] = raw_api_data.get("link_id")
                    response_data["link_status"] = raw_api_data.get("link_status")
                    response_data["message"] = f"Payment link cancelled successfully. Link ID: {response_data['link_id']}, Status: {response_data['link_status']}"
                else:
                    # Handle specific error cases
                    error_message = raw_api_data.get('message', f"API returned error status {response.status_code}")
                    
                    # Check for common cancellation errors
                    if response.status_code == 400:
                        if "already cancelled" in error_message.lower():
                            response_data["message"] = f"Payment link '{link_id}' is already cancelled"
                        elif "expired" in error_message.lower():
                            response_data["message"] = f"Payment link '{link_id}' has expired and cannot be cancelled"
                        elif "not found" in error_message.lower():
                            response_data["message"] = f"Payment link '{link_id}' not found"
                        else:
                            response_data["message"] = f"Cannot cancel payment link: {error_message}"
                    elif response.status_code == 404:
                        response_data["message"] = f"Payment link '{link_id}' not found"
                    elif response.status_code == 422:
                        response_data["message"] = f"Payment link '{link_id}' cannot be cancelled (may have active payments)"
                    else:
                        response_data["message"] = error_message

            except json.JSONDecodeError:
                # Handle cases where the server returns a non-JSON body
                response_data["api_response"] = {"raw_text": response.text}
                response_data["message"] = f"API returned non-JSON response with status code {response.status_code}."
            
            # 5. Yield the final, standardized JSON message
            yield self.create_json_message(response_data)

        except requests.exceptions.RequestException as e:
            # Handle connection or timeout errors
            response_data["status_code"] = 0 
            response_data["success"] = False
            response_data["message"] = f"Network Error: Could not connect to API within timeout. Details: {str(e)}"
            
            yield self.create_json_message(response_data)

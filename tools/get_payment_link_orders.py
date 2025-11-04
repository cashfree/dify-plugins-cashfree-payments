import requests
import json
import uuid
from collections.abc import Generator
from typing import Any, Dict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from auth_utils import get_auth_headers

class GetPaymentLinkOrdersTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # Initialize a consistent response structure
        response_data: Dict[str, Any] = {
            "status_code": None,
            "success": False,
            "api_response": None,
            "message": "",
            "link_id": None,
            "orders_count": 0,
            "orders": []
        }

        # --- 1. Retrieve & Validate Required Input (Link ID) ---
        link_id = tool_parameters.get("link_id")
        if not link_id:
            response_data["message"] = "Fatal Error: link_id is required but was not provided."
            yield self.create_json_message(response_data)
            return

        # Store the link_id for response
        response_data["link_id"] = link_id

        # Validate status parameter if provided
        status = tool_parameters.get("status", "PAID")
        if status and status not in ["ALL", "PAID"]:
            response_data["message"] = "Fatal Error: status must be either 'ALL' or 'PAID'"
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
        base_url = "https://api.cashfree.com/pg" if environment == "production" else "https://sandbox.cashfree.com/pg"
        api_url = f"{base_url}/links/{link_id}/orders"
        
        # Add query parameter if status is provided
        if status:
            api_url += f"?status={status}"
                
        # Get authentication headers from provider
        try:
            headers = get_auth_headers(credentials, include_api_version=True, is_payout_api=False)
            headers["Accept"] = "application/json"
            headers["x-request-id"] = str(uuid.uuid4())
        except Exception as e:
            response_data["message"] = f"Fatal Error: Authentication failed: {str(e)}"
            yield self.create_json_message(response_data)
            return

        # --- 4. Execute API Call (GET request) ---
        try:
            response = requests.get(api_url, headers=headers, timeout=30)
            
            # Update base status information
            response_data["status_code"] = response.status_code
            response_data["success"] = (response.status_code == 200)

            # Attempt to parse JSON body, even if the status code is an error
            try:
                raw_api_data = response.json()
                response_data["api_response"] = raw_api_data
                
                # Set a friendly message based on Cashfree's status/error messages
                if response_data["success"]:
                    # Extract order information for success response
                    orders = raw_api_data if isinstance(raw_api_data, list) else raw_api_data.get('orders', [])
                    response_data["orders"] = orders
                    response_data["orders_count"] = len(orders)
                    
                    if response_data["orders_count"] > 0:
                        response_data["message"] = f"Retrieved {response_data['orders_count']} order(s) for payment link {link_id} with status filter: {status}"
                    else:
                        response_data["message"] = f"No orders found for payment link {link_id} with status filter: {status}"
                else:
                    # Handle specific error cases
                    error_message = raw_api_data.get('message', f"API returned error status {response.status_code}")
                    
                    # Provide more context for common error scenarios
                    if response.status_code == 404:
                        response_data["message"] = f"Payment link not found: {link_id}. Please verify the link_id."
                    elif response.status_code == 400:
                        response_data["message"] = f"Bad Request: {error_message}. Please check the link_id format and status parameter."
                    else:
                        response_data["message"] = error_message

            except json.JSONDecodeError:
                # Handle cases where the server returns a non-JSON body (e.g., plain text 500 error)
                response_data["api_response"] = {"raw_text": response.text}
                response_data["message"] = f"API returned non-JSON response with status code {response.status_code}."
            
            # 5. Yield the final, standardized JSON message
            yield self.create_json_message(response_data)

        except requests.exceptions.RequestException as e:
            # Handle connection or timeout errors (no response received from server)
            response_data["status_code"] = 0 
            response_data["success"] = False
            response_data["message"] = f"Network Error: Could not connect to API within timeout. Details: {str(e)}"
            
            yield self.create_json_message(response_data)

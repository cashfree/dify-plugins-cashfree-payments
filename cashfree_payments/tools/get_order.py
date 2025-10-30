import requests
import json
from collections.abc import Generator
from typing import Any, Dict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class GetOrderTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # Initialize a consistent response structure
        response_data: Dict[str, Any] = {
            "status_code": None,
            "success": False,
            "api_response": None,
            "message": ""
        }

        # --- 1. Retrieve & Validate Required Input (Order ID) ---
        order_id = tool_parameters.get("order_id")
        if not order_id:
            response_data["message"] = "Fatal Error: order_id is required but was not provided."
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

        # 3. Construct API URL and Headers
        base_url = "https://api.cashfree.com/pg" if environment == "production" else "https://sandbox.cashfree.com/pg"
        api_url = f"{base_url}/orders/{order_id}"
                
        # Build authentication headers based on auth method
        headers = {
            "Accept": "application/json",
            "x-api-version": api_version
        }
        
        if auth_method == "client_credentials":
            headers["x-client-id"] = credentials.get("cashfree_client_id")
            headers["x-client-secret"] = credentials.get("cashfree_client_secret")
        elif auth_method == "bearer_token":
            headers["Authorization"] = f"Bearer {credentials.get('bearer_token')}"

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
                    response_data["message"] = f"Details fetched successfully. Order Status: {raw_api_data.get('order_status')}"
                else:
                    response_data["message"] = raw_api_data.get('message', f"API returned error status {response.status_code}")

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

import requests
import json
import uuid
import re
from collections.abc import Generator
from typing import Any, Dict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class CreateRefundTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # Initialize a consistent response structure
        response_data: Dict[str, Any] = {
            "status_code": None,
            "success": False,
            "api_response": None,
            "message": "",
            "refund_id": None,
            "refund_status": None,
            "order_id": None
        }

        # --- 1. Retrieve & Validate Required Inputs ---
        order_id = tool_parameters.get("order_id")
        refund_amount = tool_parameters.get("refund_amount")
        refund_id = tool_parameters.get("refund_id")

        # Validate required parameters
        required_params = {
            "order_id": order_id,
            "refund_amount": refund_amount,
            "refund_id": refund_id
        }

        missing_params = [key for key, value in required_params.items() if not value]
        if missing_params:
            response_data["message"] = f"Fatal Error: Required parameters missing: {', '.join(missing_params)}"
            yield self.create_json_message(response_data)
            return

        # Store IDs for response
        response_data["order_id"] = order_id
        response_data["refund_id"] = refund_id

        # Validate refund amount
        try:
            refund_amount = float(refund_amount)
            if refund_amount <= 0:
                response_data["message"] = "Fatal Error: refund_amount must be greater than 0"
                yield self.create_json_message(response_data)
                return
        except (ValueError, TypeError):
            response_data["message"] = "Fatal Error: refund_amount must be a valid number"
            yield self.create_json_message(response_data)
            return

        # Validate refund_id format and length (3-40 characters, alphanumeric)
        if not (3 <= len(refund_id) <= 40):
            response_data["message"] = "Fatal Error: refund_id must be between 3 and 40 characters"
            yield self.create_json_message(response_data)
            return
        
        if not re.match(r'^[a-zA-Z0-9]+$', refund_id):
            response_data["message"] = "Fatal Error: refund_id must contain only alphanumeric characters"
            yield self.create_json_message(response_data)
            return

        # Validate refund_note length if provided (3-100 characters)
        refund_note = tool_parameters.get("refund_note")
        if refund_note and not (3 <= len(refund_note) <= 100):
            response_data["message"] = "Fatal Error: refund_note must be between 3 and 100 characters"
            yield self.create_json_message(response_data)
            return

        # Validate refund_speed if provided
        refund_speed = tool_parameters.get("refund_speed", "STANDARD")
        if refund_speed and refund_speed not in ["STANDARD", "INSTANT"]:
            response_data["message"] = "Fatal Error: refund_speed must be either 'STANDARD' or 'INSTANT'"
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
        api_url = f"{base_url}/orders/{order_id}/refunds"
        
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

        # --- 4. Build Request Body ---
        request_body = {
            "refund_amount": refund_amount,
            "refund_id": refund_id
        }

        # Add optional parameters if provided
        if refund_note:
            request_body["refund_note"] = refund_note

        if refund_speed:
            request_body["refund_speed"] = refund_speed

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
                    response_data["refund_status"] = raw_api_data.get("refund_status")
                    response_data["message"] = f"Refund created successfully for order {order_id}. Refund ID: {refund_id}, Status: {response_data['refund_status']}"
                else:
                    # Handle specific error cases
                    error_message = raw_api_data.get('message', f"API returned error status {response.status_code}")
                    
                    # Provide more context for common error scenarios
                    if response.status_code == 400:
                        if "already refunded" in error_message.lower():
                            response_data["message"] = f"Refund failed: {error_message}. The payment may have already been fully refunded."
                        elif "insufficient" in error_message.lower() or "exceeds" in error_message.lower():
                            response_data["message"] = f"Refund failed: {error_message}. Refund amount may exceed the available refundable amount."
                        elif "six months" in error_message.lower() or "expired" in error_message.lower():
                            response_data["message"] = f"Refund failed: {error_message}. Refunds can only be initiated within six months of the original transaction."
                        elif "duplicate" in error_message.lower():
                            response_data["message"] = f"Refund failed: {error_message}. The refund_id may already exist."
                        else:
                            response_data["message"] = f"Bad Request: {error_message}"
                    elif response.status_code == 404:
                        response_data["message"] = f"Order not found: {order_id}. Please verify the order_id."
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

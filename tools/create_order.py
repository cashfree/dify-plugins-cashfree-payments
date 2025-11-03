import requests
import json
import uuid
import re
from collections.abc import Generator
from typing import Any, Dict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class CreateOrderTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # Initialize a consistent response structure
        response_data: Dict[str, Any] = {
            "status_code": None,
            "success": False,
            "api_response": None,
            "message": "Tool started successfully",
            "order_id": None,
            "payment_session_id": None,
            "tool_execution": "STARTED"
        }

        try:
            # --- 1. Retrieve & Validate Required Inputs ---
            order_amount = tool_parameters.get("order_amount")
            order_currency = tool_parameters.get("order_currency", "INR")
            customer_id = tool_parameters.get("customer_id")
            customer_email = tool_parameters.get("customer_email")
            customer_phone = tool_parameters.get("customer_phone")
            customer_name = tool_parameters.get("customer_name")

            # Debug: Add parameter info
            response_data["received_parameters"] = {
                "order_amount": order_amount,
                "order_currency": order_currency,
                "customer_id": customer_id,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "customer_name": customer_name,
                "total_params": len(tool_parameters),
                "all_param_keys": list(tool_parameters.keys())
            }
            response_data["tool_execution"] = "PARAMETERS_RECEIVED"

            # Validate required parameters
            required_params = {
                "order_amount": order_amount,
                "customer_id": customer_id,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "customer_name": customer_name
            }

            missing_params = [key for key, value in required_params.items() if not value]
            if missing_params:
                response_data["message"] = f"Fatal Error: Required parameters missing: {', '.join(missing_params)}"
                response_data["tool_execution"] = "VALIDATION_FAILED"
                yield self.create_json_message(response_data)
                return

            # Continue with rest of validation...
            response_data["tool_execution"] = "PARAMETERS_VALIDATED"

            # Validate order amount
            try:
                order_amount = float(order_amount)
                if order_amount < 1:
                    response_data["message"] = "Fatal Error: order_amount must be at least 1"
                    yield self.create_json_message(response_data)
                    return
            except (ValueError, TypeError):
                response_data["message"] = "Fatal Error: order_amount must be a valid number"
                yield self.create_json_message(response_data)
                return

            # Validate order_id format if provided
            order_id = tool_parameters.get("order_id")
            if order_id:
                # Check length (3-45 characters)
                if not (3 <= len(order_id) <= 45):
                    response_data["message"] = "Fatal Error: order_id must be between 3 and 45 characters"
                    yield self.create_json_message(response_data)
                    return
                # Check allowed characters (alphanumeric, '_', '-')
                if not re.match(r'^[a-zA-Z0-9_-]+$', order_id):
                    response_data["message"] = "Fatal Error: order_id can only contain alphanumeric characters, '_' and '-'"
                    yield self.create_json_message(response_data)
                    return

            # Validate order_note length if provided
            order_note = tool_parameters.get("order_note")
            if order_note and not (3 <= len(order_note) <= 200):
                response_data["message"] = "Fatal Error: order_note must be between 3 and 200 characters"
                yield self.create_json_message(response_data)
                return

            # Validate URL lengths if provided
            return_url = tool_parameters.get("return_url")
            if return_url and len(return_url) > 250:
                response_data["message"] = "Fatal Error: return_url must not exceed 250 characters"
                yield self.create_json_message(response_data)
                return

            notify_url = tool_parameters.get("notify_url")
            if notify_url and len(notify_url) > 250:
                response_data["message"] = "Fatal Error: notify_url must not exceed 250 characters"
                yield self.create_json_message(response_data)
                return

            # Validate notify_url is HTTPS if provided
            if notify_url and not notify_url.startswith('https://'):
                response_data["message"] = "Fatal Error: notify_url must use HTTPS protocol"
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
            api_url = f"{base_url}/orders"
            
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
                "order_amount": order_amount,
                "order_currency": order_currency,
                "customer_details": {
                    "customer_id": customer_id,
                    "customer_email": customer_email,
                    "customer_phone": customer_phone,
                    "customer_name": customer_name
                }
            }

            # Add optional parameters if provided
            optional_params = {
                "order_id": tool_parameters.get("order_id"),
                "order_note": tool_parameters.get("order_note"),
                "order_expiry_time": tool_parameters.get("order_expiry_time"),
                "customer_bank_account_number": tool_parameters.get("customer_bank_account_number"),
                "customer_bank_ifsc": tool_parameters.get("customer_bank_ifsc")
            }

            # Add optional customer details
            for key, value in optional_params.items():
                if value:
                    if key.startswith("customer_bank_"):
                        request_body["customer_details"][key] = value
                    else:
                        request_body[key] = value

            # Add order meta if return_url, notify_url, or payment_methods are provided
            order_meta = {}
            if tool_parameters.get("return_url"):
                order_meta["return_url"] = tool_parameters.get("return_url")
            if tool_parameters.get("notify_url"):
                order_meta["notify_url"] = tool_parameters.get("notify_url")
            if tool_parameters.get("payment_methods"):
                order_meta["payment_methods"] = tool_parameters.get("payment_methods")
            
            if order_meta:
                request_body["order_meta"] = order_meta

            # --- 5. Execute API Call (POST request) ---
            try:
                # Add debugging info
                response_data["debug_info"] = {
                    "api_url": api_url,
                    "environment": environment,
                    "auth_method": auth_method,
                    "request_body_keys": list(request_body.keys()),
                    "has_credentials": bool(credentials.get("cashfree_client_id") if auth_method == "client_credentials" else credentials.get("bearer_token"))
                }
                
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
                        response_data["order_id"] = raw_api_data.get("order_id")
                        response_data["payment_session_id"] = raw_api_data.get("payment_session_id")
                        response_data["message"] = f"Order created successfully. Order ID: {response_data['order_id']}"
                    else:
                        # Handle error response
                        error_message = raw_api_data.get('message', f"API returned error status {response.status_code}")
                        response_data["message"] = f"API Error: {error_message}"

                except json.JSONDecodeError:
                    # Handle cases where the server returns a non-JSON body
                    response_data["api_response"] = {"raw_text": response.text}
                    response_data["message"] = f"API returned non-JSON response with status code {response.status_code}. Response: {response.text[:200]}"
                
                # 6. Yield the final, standardized JSON message
                yield self.create_json_message(response_data)

            except requests.exceptions.RequestException as e:
                # Handle connection or timeout errors
                response_data["status_code"] = 0 
                response_data["success"] = False
                response_data["message"] = f"Network Error: Could not connect to API within timeout. Details: {str(e)}"
                response_data["debug_info"] = {
                    "api_url": api_url,
                    "environment": environment,
                    "error_type": type(e).__name__
                }
                
                yield self.create_json_message(response_data)

        except Exception as e:
            # Catch any unexpected errors
            response_data["status_code"] = 0 
            response_data["success"] = False
            response_data["message"] = f"Unexpected Error in Tool: {str(e)}"
            response_data["tool_execution"] = "EXCEPTION_CAUGHT"
            response_data["error_type"] = type(e).__name__
            
            yield self.create_json_message(response_data)

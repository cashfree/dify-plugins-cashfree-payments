import requests
import json
import uuid
import re
from datetime import datetime, timedelta
from collections.abc import Generator
from typing import Any, Dict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from auth_utils import get_auth_headers

class CreateCashgramTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # Initialize a consistent response structure
        response_data: Dict[str, Any] = {
            "status_code": None,
            "success": False,
            "api_response": None,
            "message": "",
            "cashgram_id": None,
            "cashgram_link": None
        }

        # --- 1. Retrieve & Validate Required Inputs ---
        cashgram_id = tool_parameters.get("cashgramId")
        amount = tool_parameters.get("amount")
        name = tool_parameters.get("name")
        phone = tool_parameters.get("phone")
        link_expiry = tool_parameters.get("linkExpiry")

        # Validate required parameters
        required_params = {
            "cashgramId": cashgram_id,
            "amount": amount,
            "name": name,
            "phone": phone,
            "linkExpiry": link_expiry
        }

        missing_params = [key for key, value in required_params.items() if not value]
        if missing_params:
            response_data["message"] = f"Fatal Error: Required parameters missing: {', '.join(missing_params)}"
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

        # Validate amount
        try:
            amount = float(amount)
            if amount < 1.00:
                response_data["message"] = "Fatal Error: amount must be >= 1.00"
                yield self.create_json_message(response_data)
                return
        except (ValueError, TypeError):
            response_data["message"] = "Fatal Error: amount must be a valid number"
            yield self.create_json_message(response_data)
            return

        # Validate link expiry date format
        try:
            expiry_date = datetime.strptime(link_expiry, "%Y/%m/%d")
            current_date = datetime.now()
            max_expiry = current_date + timedelta(days=30)
            
            if expiry_date <= current_date:
                response_data["message"] = "Fatal Error: linkExpiry must be a future date"
                yield self.create_json_message(response_data)
                return
                
            if expiry_date > max_expiry:
                response_data["message"] = "Fatal Error: linkExpiry cannot be more than 30 days from today"
                yield self.create_json_message(response_data)
                return
                
        except ValueError:
            response_data["message"] = "Fatal Error: linkExpiry must be in YYYY/MM/DD format"
            yield self.create_json_message(response_data)
            return

        # Validate name length
        if len(name.strip()) == 0:
            response_data["message"] = "Fatal Error: name cannot be empty"
            yield self.create_json_message(response_data)
            return

        # Validate phone number (basic validation)
        if not re.match(r'^[\d\+\-\(\)\s]+$', phone):
            response_data["message"] = "Fatal Error: phone number contains invalid characters"
            yield self.create_json_message(response_data)
            return

        # Validate email format if provided
        email = tool_parameters.get("email")
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            response_data["message"] = "Fatal Error: Invalid email format"
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
        api_url = f"{base_url}/payout/v1/createCashgram"
        
        # Get authentication headers from auth utils (excluding x-api-version for cashgram)
        try:
            headers = get_auth_headers(credentials, include_api_version=False, is_payout_api=True)
        except Exception as e:
            response_data["message"] = f"Fatal Error: Authentication failed: {str(e)}"
            yield self.create_json_message(response_data)
            return

        # --- 4. Build Request Body ---
        request_body = {
            "cashgramId": cashgram_id,
            "amount": amount,
            "name": name,
            "phone": phone,
            "linkExpiry": link_expiry
        }

        # Add optional parameters if provided
        if email:
            request_body["email"] = email
            
        remarks = tool_parameters.get("remarks")
        if remarks:
            request_body["remarks"] = remarks
            
        notify_customer = tool_parameters.get("notifyCustomer")
        if notify_customer is not None:
            request_body["notifyCustomer"] = notify_customer

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
                    response_data["cashgram_link"] = raw_api_data.get("link")
                    response_data["message"] = f"Cashgram created successfully. Cashgram ID: {response_data['cashgram_id']}"
                else:
                    # Handle error response
                    error_message = raw_api_data.get('message', f"API returned error status {response.status_code}")
                    
                    # Check for common Cashgram creation errors
                    if response.status_code == 400:
                        if "duplicate" in error_message.lower():
                            response_data["message"] = f"Cashgram with ID '{cashgram_id}' already exists"
                        elif "invalid amount" in error_message.lower():
                            response_data["message"] = "Invalid amount specified"
                        elif "invalid date" in error_message.lower():
                            response_data["message"] = "Invalid expiry date format or date range"
                        else:
                            response_data["message"] = f"Cannot create Cashgram: {error_message}"
                    elif response.status_code == 401:
                        response_data["message"] = "Authentication failed. Please check your credentials"
                    elif response.status_code == 403:
                        response_data["message"] = "Access forbidden. Please check your permissions"
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

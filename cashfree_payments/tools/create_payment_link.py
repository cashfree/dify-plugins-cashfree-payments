import requests
import json
import uuid
import re
from collections.abc import Generator
from typing import Any, Dict

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class CreatePaymentLinkTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        
        # Initialize a consistent response structure
        response_data: Dict[str, Any] = {
            "status_code": None,
            "success": False,
            "api_response": None,
            "message": "",
            "link_id": None,
            "link_url": None
        }

        # --- 1. Retrieve & Validate Required Inputs ---
        link_id = tool_parameters.get("link_id")
        link_amount = tool_parameters.get("link_amount")
        link_currency = tool_parameters.get("link_currency", "INR")
        link_purpose = tool_parameters.get("link_purpose")
        customer_phone = tool_parameters.get("customer_phone")

        # Validate required parameters
        required_params = {
            "link_id": link_id,
            "link_amount": link_amount,
            "link_purpose": link_purpose,
            "customer_phone": customer_phone
        }

        missing_params = [key for key, value in required_params.items() if not value]
        if missing_params:
            response_data["message"] = f"Fatal Error: Required parameters missing: {', '.join(missing_params)}"
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

        # Validate link amount
        try:
            link_amount = float(link_amount)
            if link_amount <= 0:
                response_data["message"] = "Fatal Error: link_amount must be greater than 0"
                yield self.create_json_message(response_data)
                return
        except (ValueError, TypeError):
            response_data["message"] = "Fatal Error: link_amount must be a valid number"
            yield self.create_json_message(response_data)
            return

        # Validate link_purpose length
        if len(link_purpose) > 500:
            response_data["message"] = "Fatal Error: link_purpose must not exceed 500 characters"
            yield self.create_json_message(response_data)
            return

        # Validate partial payment amount if provided
        link_minimum_partial_amount = tool_parameters.get("link_minimum_partial_amount")
        if link_minimum_partial_amount:
            try:
                link_minimum_partial_amount = float(link_minimum_partial_amount)
                if link_minimum_partial_amount >= link_amount:
                    response_data["message"] = "Fatal Error: link_minimum_partial_amount must be less than link_amount"
                    yield self.create_json_message(response_data)
                    return
            except (ValueError, TypeError):
                response_data["message"] = "Fatal Error: link_minimum_partial_amount must be a valid number"
                yield self.create_json_message(response_data)
                return

        # Validate return_url length if provided
        return_url = tool_parameters.get("return_url")
        if return_url and len(return_url) > 250:
            response_data["message"] = "Fatal Error: return_url must not exceed 250 characters"
            yield self.create_json_message(response_data)
            return

        # Validate notify_url is HTTPS if provided
        notify_url = tool_parameters.get("notify_url")
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
        api_url = f"{base_url}/links"
        
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
            "link_id": link_id,
            "link_amount": link_amount,
            "link_currency": link_currency,
            "link_purpose": link_purpose,
            "customer_details": {
                "customer_phone": customer_phone
            }
        }

        # Add optional customer details
        customer_email = tool_parameters.get("customer_email")
        if customer_email:
            request_body["customer_details"]["customer_email"] = customer_email

        customer_name = tool_parameters.get("customer_name")
        if customer_name:
            request_body["customer_details"]["customer_name"] = customer_name

        customer_bank_account_number = tool_parameters.get("customer_bank_account_number")
        if customer_bank_account_number:
            request_body["customer_details"]["customer_bank_account_number"] = customer_bank_account_number

        customer_bank_ifsc = tool_parameters.get("customer_bank_ifsc")
        if customer_bank_ifsc:
            request_body["customer_details"]["customer_bank_ifsc"] = customer_bank_ifsc

        # Add optional link settings
        link_partial_payments = tool_parameters.get("link_partial_payments")
        if link_partial_payments:
            request_body["link_partial_payments"] = link_partial_payments
            if link_minimum_partial_amount:
                request_body["link_minimum_partial_amount"] = link_minimum_partial_amount

        link_expiry_time = tool_parameters.get("link_expiry_time")
        if link_expiry_time:
            request_body["link_expiry_time"] = link_expiry_time

        link_auto_reminders = tool_parameters.get("link_auto_reminders")
        if link_auto_reminders:
            request_body["link_auto_reminders"] = link_auto_reminders

        # Add notification settings
        send_sms = tool_parameters.get("send_sms")
        send_email = tool_parameters.get("send_email")
        if send_sms is not None or send_email is not None:
            request_body["link_notify"] = {}
            if send_sms is not None:
                request_body["link_notify"]["send_sms"] = send_sms
            if send_email is not None:
                request_body["link_notify"]["send_email"] = send_email

        # Add link meta if any meta fields are provided
        link_meta = {}
        if notify_url:
            link_meta["notify_url"] = notify_url
        if return_url:
            link_meta["return_url"] = return_url
        
        payment_methods = tool_parameters.get("payment_methods")
        if payment_methods:
            link_meta["payment_methods"] = payment_methods
        
        upi_intent = tool_parameters.get("upi_intent")
        if upi_intent is not None:
            link_meta["upi_intent"] = upi_intent
        
        if link_meta:
            request_body["link_meta"] = link_meta

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
                    response_data["link_id"] = raw_api_data.get("link_id")
                    response_data["link_url"] = raw_api_data.get("link_url")
                    response_data["message"] = f"Payment link created successfully. Link ID: {response_data['link_id']}"
                else:
                    # Handle error response
                    error_message = raw_api_data.get('message', f"API returned error status {response.status_code}")
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

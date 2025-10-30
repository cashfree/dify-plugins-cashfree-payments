## Cashfree Payments - Dify Plugin

**Author:** cashfree
**Version:** 0.0.1
**Type:** tool

### Description

This plugin provides comprehensive integration with Cashfree Payment Gateway and Payout APIs for Dify.ai workflows. It enables users to create orders, process refunds, manage payment links, handle Cashgrams, and track various payment operations through Cashfree's services.

### Available Tools

#### Payment Gateway Tools
1. **create_order** - Create a new order with Cashfree Payment Gateway
2. **get_order** - Fetch details of an existing order
3. **create_refund** - Process refunds for successful payments (within 6 months)
4. **get_order_refunds** - Get all refunds processed against an order
5. **create_payment_link** - Create payment links for customers to make payments
6. **cancel_payment_link** - Cancel active payment links
7. **fetch_payment_link_details** - Retrieve payment link information and status
8. **get_payment_link_orders** - Get all orders associated with a payment link

#### Payout Tools
9. **create_cashgram** - Create Cashgrams to send money to contacts
10. **deactivate_cashgram** - Deactivate active Cashgrams

### Configuration

The plugin supports dual authentication methods:

#### Authentication Options
- **Client ID & Secret** (Default) - Traditional Cashfree credentials
- **Bearer Token** - Modern token-based authentication

#### Required Credentials
- **Authentication Type** - Choose between "Client ID & Secret" or "Bearer Token"
- **Cashfree Client ID** - Your Cashfree merchant Client ID (required for Client ID & Secret auth)
- **Cashfree Client Secret** - Your Cashfree merchant Client Secret (required for Client ID & Secret auth)
- **Bearer Token** - Your Cashfree Bearer Token (required for Bearer Token auth)
- **API Version** - Cashfree API version (default: 2025-01-01)
- **Environment** - Choose between sandbox and production

### Usage

This plugin can be used in Dify workflows to:
- Create payment orders programmatically
- Process refunds for completed payments
- Track refund history and status for orders
- Track order status and payment completion
- Create and manage payment links for customers
- Cancel payment links when needed
- Manage payment link lifecycle and orders
- Create Cashgrams for sending money to contacts
- Deactivate Cashgrams for security or management purposes
- Handle customer service scenarios with refund processing
- Integrate payment flows with AI-driven workflows
- Enable payout operations within conversational AI

### Tool Examples

#### Create Order
```
Tool: create_order
Required Parameters:
- order_amount: 100.50
- customer_id: "CUST_001"
- customer_email: "customer@example.com"
- customer_phone: "9876543210"
- customer_name: "John Doe"

Optional Parameters:
- order_currency: "INR" (default)
- order_id: "ORDER_123"
- order_note: "Payment for product purchase"
- return_url: "https://yoursite.com/payment/success"
- notify_url: "https://yoursite.com/webhook/cashfree"
- payment_methods: "cc,dc,upi,nb"
```

#### Create Refund
```
Tool: create_refund
Required Parameters:
- order_id: "ORDER_123"
- refund_amount: 50.00
- refund_id: "REFUND_001"

Optional Parameters:
- refund_note: "Customer requested refund"
- refund_speed: "STANDARD" (or "INSTANT")
```

#### Get Order
```
Tool: get_order
Required Parameters:
- order_id: "ORDER_123"
```

#### Get Order Refunds
```
Tool: get_order_refunds
Required Parameters:
- order_id: "ORDER_123"
```

#### Fetch Payment Link Details
```
Tool: fetch_payment_link_details
Required Parameters:
- link_id: "LINK_123"
```

#### Get Payment Link Orders
```
Tool: get_payment_link_orders
Required Parameters:
- link_id: "LINK_123"

Optional Parameters:
- status: "PAID" (default) or "ALL"
```

#### Create Payment Link
```
Tool: create_payment_link
Required Parameters:
- link_id: "LINK_001"
- link_amount: 100.00
- link_currency: "INR"
- link_purpose: "Payment for services"
- customer_phone: "9876543210"

Optional Parameters:
- customer_email: "customer@example.com"
- customer_name: "John Doe"
- link_partial_payments: true
- link_minimum_partial_amount: 50.00
- link_expiry_time: "2025-12-31T23:59:59+05:30"
- send_sms: true
- send_email: true
- link_auto_reminders: true
- notify_url: "https://yoursite.com/webhook/cashfree"
- return_url: "https://yoursite.com/payment/success"
- payment_methods: "cc,dc,upi,nb"
- upi_intent: false
```

#### Cancel Payment Link
```
Tool: cancel_payment_link
Required Parameters:
- link_id: "LINK_001"
```

#### Create Cashgram
```
Tool: create_cashgram
Required Parameters:
- cashgramId: "CASHGRAM_001"
- amount: 500.00
- name: "Jane Smith"
- phone: "9876543210"
- linkExpiry: "2025/11/30"

Optional Parameters:
- email: "jane@example.com"
- remarks: "Birthday gift"
- notifyCustomer: true
```

#### Deactivate Cashgram
```
Tool: deactivate_cashgram
Required Parameters:
- cashgramId: "CASHGRAM_001"
```




import os
import json
import requests
from util.common import older_than
from util.logger import get_logger
from datetime import datetime, timedelta
from query.shopify import get_pending_orders_query, get_mark_paid_order_query, get_cancel_order_query, get_fetching_cancelled_orders_query
from util.handler import handle_rate_limiting, handle_status_codes

log = get_logger()

class ShopifyAPIClient:
    def __init__(self, paypal_client, slack_client):
        self.api_key = os.environ.get('SHOPIFY_API_KEY')
        self.store_domain = os.environ.get('SHOPIFY_STORE_DOMAIN')
        self.endpoint = f"https://{self.store_domain}/admin/api/2024-07/graphql.json"
        self.paypal_client = paypal_client
        self.slack_client = slack_client
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.api_key
        }

    def fetch_pending_orders(self):
        cursor = None
        has_next_page = True
        all_orders = []

        while has_next_page:
            query = get_pending_orders_query(cursor)
            response = self._make_pending_order_request(query)

            if not handle_status_codes(response):
                break  # Exit if there is an error

            log.info("Extracting the data from the Shopify response")
            data = response.json()['data']['orders']
            orders = data['edges']
            for order in orders:
                order_data = order['node']
                log.info(f"Fetching transaction details for order data {order_data}")

                # Filter out the most recent transaction
                recent_transaction = max(order_data['transactions'], key=lambda t: datetime.strptime(t['createdAt'], "%Y-%m-%dT%H:%M:%SZ"))

                # Fetch the transaction details from the Paypal API
                paypal_details = self.paypal_client.get_transaction_details(recent_transaction['authorizationCode'])
                if paypal_details:
                    recent_transaction['paypal_details'] = paypal_details
                
                order_data['transactions'] = [recent_transaction]
                
                log.info(f"Fetched complete order details {order_data}")
                all_orders.append(order_data)

            # Pagination handling
            has_next_page = data['pageInfo']['hasNextPage']
            if has_next_page:
                cursor = orders[-1]['cursor']
                log.info("Fetch the orders from next page...")

        log.info("Finished calling Shopify endpoint for fetching orders")

        return all_orders

    def _make_pending_order_request(self, query):
        while True:
            log.info("Calling Shopify API to fetch orders")
            response = requests.post(self.endpoint, headers=self.headers, json={'query': query})

            # Rate limiting handling
            if handle_rate_limiting(response):
                continue  # Retry after waiting

            return response
    
    def _mark_order_as_paid(self, order_id):
        # Variables for the mutation
        variables = {
            "input": {
                "id": order_id,  # Shopify order ID (e.g., "gid://shopify/Order/1234567890")
            }
        }
        
        # Execute the request
        response = requests.post(self.endpoint, headers=self.headers, data=json.dumps({
            "query": get_mark_paid_order_query(),
            "variables": variables
        }))
        
        # Handle response
        if response.status_code == 200:
            result = response.json()
            paid_order = result['data']['orderMarkAsPaid']
            if "userErrors" in paid_order and paid_order['userErrors']:
                log.error(f"GraphQL Error: {paid_order['userErrors']}")
            return paid_order
        else:
            log.error(f"Marking the order paid not successful for order {order_id}")
            return None
    
    def _cancel_order(self, order_id, restock=False, notify_customer=True, refund=False, reason="DECLINED"):
        log.info(f"Cancelling order {order_id} on Shopify")

        # Variables for the mutation
        variables = {
            "orderId": order_id,  # Shopify order ID (e.g., "gid://shopify/Order/1234567890")
            "restock": restock,  # Whether to restock the items (True or False)
            "notifyCustomer": notify_customer,  # Whether to notify the customer about the cancellation (True or False)
            "refund": refund,  # Whether to issue a refund (True or False)
            "reason": reason # The reason why it is being cancelled
        }
        
        # Send the request
        response = requests.post(self.endpoint, headers=self.headers, data=json.dumps({
            "query": get_cancel_order_query(),
            "variables": variables
        }))
        
        # Handle the response
        if response.status_code == 200:
            result = response.json()
            order_cancel = result['data']['orderCancel']
            if "orderCancelUserErrors" in order_cancel and order_cancel['orderCancelUserErrors']:
                log.error(f"Received user errors from the response: {order_cancel['orderCancelUserErrors']}")
            return order_cancel
        else:
            log.error(f"Cancelling was not successful for order {order_id}")
            return response.json()
    
    # Utility function to take action on Paypal status
    def handle_paypal_status(self, order):
        transaction = order['transactions'][0]
        paypal_details = transaction['paypal_details']
        transaction_status = paypal_details['status']

        csv_row = [order['name'], order['id'], order['createdAt'], paypal_details['amount']['value'], order['displayFinancialStatus'], transaction_status]

        if transaction_status == 'PENDING':
            log.info(f"Order {order['id']} is PENDING at Paypal, will try after 24 hours")
            csv_row.append('No')
        elif transaction_status == 'COMPLETED':
            log.info(f"Order {order['id']} is COMPLETED at Paypal")
            order_paid_response = self._mark_order_as_paid(order['id'])
            log.info(f"Response received from marking the order paid {order_paid_response}")
            if order_paid_response:
                fully_paid = order_paid_response['order']['fullyPaid']
                if fully_paid:
                    log.info(f"Order {order['id']} marked fully paid successfully")
                    csv_row[4] = "PAID"
                    csv_row.append("Yes")
                else:
                    log.info(f"Order not {order['id']} marked fully paid")
                    csv_row.append("No")
            else:
                csv_row.append("No")
        elif transaction_status == 'DECLINED':
            log.info(f"Order {order['id']} is DECLINED at Paypal")
            cancel_response = self._cancel_order(order['id'], reason=transaction_status)
            log.info(f"Response received from cancelling order {cancel_response}")
            csv_row.append("No")
        elif transaction_status == 'REFUNDED':
            log.info(f"Order {order['id']} is REFUNDED at Paypal")
            cancel_response = self._cancel_order(order['id'], reason=transaction_status)
            log.info(f"Response received from cancelling order {cancel_response}")
            csv_row.append("No")
        else:
            log.warning(f"Order {order['id']} has unknown status: {transaction_status} at Paypal")
            csv_row.append("No")
        
        return csv_row
    
    def fetch_cancelled_orders(self):
        cursor = None
        has_next_page = True
        all_orders = []

        while has_next_page:
            query = get_fetching_cancelled_orders_query(cursor)
            response = self._make_cancelled_order_request(query)

            if not handle_status_codes(response):
                break  # Exit if there is an error

            log.info("Extracting the data from the Shopify response")
            data = response.json()['data']['orders']
            orders = data['edges']
            for order in orders:
                order_data = order['node']
                log.info(f"Fetching transaction details for order data {order_data}")

                # Filter out the most recent transaction
                recent_transaction = max(order_data['transactions'], key=lambda t: datetime.strptime(t['createdAt'], "%Y-%m-%dT%H:%M:%SZ"))

                if recent_transaction['authorizationCode']:
                    # Fetch the transaction details from the Paypal API
                    paypal_details = self.paypal_client.get_transaction_details(recent_transaction['authorizationCode'])
                    if paypal_details:
                        recent_transaction['paypal_details'] = paypal_details
                    
                    order_data['transactions'] = [recent_transaction]
                    
                    log.info(f"Fetched complete order details {order_data}")
                    all_orders.append(order_data)
                else:
                    log.info(f"Authorization code does not exists for order {order_data['name']}")

            # Pagination handling
            has_next_page = data['pageInfo']['hasNextPage']
            if has_next_page:
                cursor = orders[-1]['cursor']
                log.info("Fetch the orders from next page...")

        log.info("Finished calling Shopify endpoint for fetching cancelled orders")

        return all_orders
    
    def _make_cancelled_order_request(self, query):
        while True:
            log.info("Calling Shopify API to fetch cancelled orders")
            response = requests.post(self.endpoint, headers=self.headers, json={'query': query})

            # Rate limiting handling
            if handle_rate_limiting(response):
                continue  # Retry after waiting

            return response


import os
import base64
import requests
from util.logger import get_logger
from util.common import get_days_ago
from datetime import datetime

log = get_logger()

class PayPalClient:
    def __init__(self) -> None:
        self.client_id = os.environ.get('PAYPAL_CLIENT_ID')
        self.client_secret = os.environ.get('PAYPAL_CLIENT_SECRET')
        self.api_url = os.environ.get('PAYPAL_CLIENT_URL')
        self.token = self.get_access_token()

    def get_access_token(self):
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "client_credentials",
            "scope": "https://uri.paypal.com/services/payments/payment/authcapture https://uri.paypal.com/services/payments/refund"
        }
        response = requests.post(f"{self.api_url}/v1/oauth2/token", headers=headers, data=data)
        response.raise_for_status()
        return response.json()['access_token']
    
    def get_transaction_details(self, transaction_id):
        log.info(f"Fetching transaction details for Transaction ID: {transaction_id}")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        url = f"{self.api_url}/v2/payments/captures/{transaction_id}"

        response = requests.get(url, headers=headers)
        
        response.raise_for_status()
        return response.json()
    
    def refund_captured_payment(self, transaction_id):
        log.info(f"Processing refund for captured Payment having Transaction ID: {transaction_id}")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        url = f'{self.api_url}/v2/payments/captures/{transaction_id}/refund'

        # Make the request to refund the payment
        response = requests.post(url, headers=headers, json={})

        response.raise_for_status()
        return response.json()
    
    def fetch_refund_details(self, transaction_id):
        log.info(f"Fetching the refund details for Transaction ID: {transaction_id}")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        url = f'{self.api_url}/v2/payments/refunds/{transaction_id}'

        response = requests.get(url, headers=headers)

        response.raise_for_status()
        return response.json()
    
    # Utility function to take action on Paypal status
    def process_pending_refunds(self, order):
        transaction = order['transactions'][0]
        paypal_details = transaction['paypal_details']
        transaction_status = paypal_details['status']
        transaction_id = paypal_details['id']

        csv_row = [order['name'], order['id'], order['createdAt'], order['cancelledAt'], paypal_details['amount']['value'], transaction_status]

        refund_response = self.fetch_refund_details(transaction_id)
        log.info(f"Response received from fetching the refund status details {refund_response}")

        if transaction_status == 'PENDING':
            log.info(f"E-Check for Order {order['id']} is PENDING at Paypal, will try after 24 hours")
            csv_row.append("NA Yet")
        elif transaction_status == 'COMPLETED':
            log.info(f"E-Check for Order {order['id']} is COMPLETED at Paypal")

            if refund_response['status'] == 'PENDING':
                process_refund_response = self.refund_captured_payment(transaction_id)
                log.info(f"Response received from processing the PayPal refund {process_refund_response}")
                csv_row.append(process_refund_response['status'])
            elif refund_response['status'] == 'COMPLETED':
                csv_row.append('COMPLETED')
            else:
                csv_row.append('PENDING')

        elif transaction_status == 'DECLINED':
            log.info(f"E-Check for Order {order['id']} is DECLINED at Paypal")
            csv_row.append(refund_response['status'])
        elif transaction_status == 'REFUNDED':
            log.info(f"E-Check for Order {order['id']} is REFUNDED at Paypal")
            csv_row.append(refund_response['status'])
        else:
            log.warning(f"E-Check for Order {order['id']} has unknown status: {transaction_status} at Paypal")
            csv_row.append(refund_response['status'])

        return csv_row

from datetime import datetime
from dotenv import load_dotenv
from util.logger import get_logger
from prettytable import PrettyTable
from client.slack_client import SlackClient
from client.paypal_api_client import PayPalClient
from client.shopify_api_client import ShopifyAPIClient

load_dotenv()

log = get_logger()

def main():
    log.info(f"Sync Cancelled Orders Job running at {datetime.now()}")

    # Initialize PayPal client
    paypal_client = PayPalClient()

    # Initialize Slack Client
    slack_client = SlackClient()

    # Initialize Shopify client
    shopify_client = ShopifyAPIClient(paypal_client, slack_client)

    # Fetch Cancelled Orders
    log.info("Fetching cancelled orders from the last 30 days...")
    orders = shopify_client.fetch_cancelled_orders()

    if orders:
        csv_data = [['Name', 'Order ID', 'Created At', 'Cancelled At', 'Amount', 'eCheck Status', 'PayPal Refund']]
        log.info(f"Fetched {len(orders)} cancelled orders.")
        log.info("Iterating over each order to process refunds...")
        for order in orders:
            log.info(f"Processing for Order: {order['id']}")
            data_row = paypal_client.process_pending_refunds(order)
            csv_data.append(data_row)
        
        # Send report Notification
        csv_path = slack_client.create_csv_file(csv_data)
        slack_client.send_csv_to_slack(csv_path, "PayPal <> Shopify Cancelled Orders sync")

        # Send Pretty Table notification to Slack channel
        tab = PrettyTable(csv_data[0])
        tab.add_rows(csv_data[1:])
        slack_client.send_notification(tab)

        log.info(f"Here is the cancelled orders report your requested \n{tab}")

    else:
        log.info("No cancelled orders found.")

    log.info(f"Sync Cancelled Orders Job finished at {datetime.now()}")

if __name__ == "__main__":
    main()
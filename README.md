# PayPal <> Shopify Payment Sync

This project provides automation scripts to synchronize payment statuses between Shopify and PayPal. It helps ensure that order statuses on Shopify reflect the actual transaction outcomes on PayPal, particularly for payments made via eCheck or other pending methods.

## Features

- **Sync Pending Orders**: Fetches Shopify orders with a `pending` financial status.
  - If the corresponding PayPal transaction is `COMPLETED`, the Shopify order is marked as `Paid`.
  - If the PayPal transaction is `DECLINED`, the Shopify order is `Cancelled`.
- **Sync Cancelled Orders**: Fetches recently cancelled Shopify orders to process refunds on PayPal for completed eCheck payments.
- **Slack Notifications**: Sends detailed daily reports to a designated Slack channel, including a summary table and a comprehensive CSV file attachment.

## Getting Started

Follow these steps to set up and run the project.

### Prerequisites

- Python 3.8+
- pip

### Installation

1.  **Clone the repository:**

    ```bash
    git clone git@github.com:mhaider97/payment-status-sync.git
    cd payment-status-sync
    ```

2.  **Install dependencies:**
    It's recommended to use a virtual environment.

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the root directory of the project by copying the example file:
    ```bash
    cp .env.example .env
    ```
    Then, fill in the required values in the `.env` file.

### Configuration

Your `.env` file should contain the following API keys and configuration details:

```
# Shopify API Credentials
SHOPIFY_API_KEY="your_shopify_admin_api_access_token"
SHOPIFY_STORE_DOMAIN="your-store.myshopify.com"

# PayPal API Credentials
PAYPAL_CLIENT_ID="your_paypal_client_id"
PAYPAL_CLIENT_SECRET="your_paypal_client_secret"
PAYPAL_CLIENT_URL="https://api-m.sandbox.paypal.com" # Use https://api-m.paypal.com for production

# Slack Bot Credentials
SLACK_TOKEN="your-slack-bot-token"
BOT_CHANNEL="C0123456789" # Slack Channel ID
BOT_USER="Payment Bot"
```

## Usage

The project contains two main scripts that can be run independently.

### Sync Pending Orders

To check PayPal transaction statuses for pending Shopify orders and update them accordingly:

```bash
python sync_pending_orders.py
```

### Sync Cancelled Orders

To process refunds on PayPal for recently cancelled Shopify orders:

```bash
python sync_cancelled_orders.py
```

### Scheduling

For complete automation, you can schedule these scripts to run daily using a cron job.

**Example cron job (runs every day at 8 AM):**

```cron
0 8 * * * /path/to/your/project/venv/bin/python /path/to/your/project/sync_pending_orders.py
0 8 * * * /path/to/your/project/venv/bin/python /path/to/your/project/sync_cancelled_orders.py
```

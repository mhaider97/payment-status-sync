import os
import csv
from datetime import datetime
from slack_sdk import WebClient
from util.logger import get_logger
from slack_sdk.errors import SlackApiError

log = get_logger()

class SlackClient():
    '''Class to handle sending notifications to slack'''
    def __init__(self) -> None:
        # Set up a WebClient with the Slack OAuth token
        self.client = WebClient(token=os.getenv('SLACK_TOKEN'))
        self.channel = os.getenv('BOT_CHANNEL')
        self.username = os.getenv('BOT_USER')
      
    def send_notification(self, table):
        '''Method to send slack notification'''
        # Send a message
        self.client.chat_postMessage(
            channel=self.channel, 
            text=f"Triggered the Paypal <> Shopify daily sync automation. Here is the report: \n ```\n{table}\n```", 
            username=self.username
        )

        log.info(f'Sync notification sent to the slack channel #{self.channel}')

    def create_csv_file(self, data, file_path=None):
        if not file_path:
            file_path = f"reports/{datetime.now().strftime("%Y-%m-%d")}_daily-report.csv"

        # Create and write to CSV file
        with open(file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)
            log.info(f"CSV file '{file_path}' created.")
            return file_path
    
    # Function to send CSV file as attachment in Slack
    def send_csv_to_slack(self, file_path, name):
        try:
            # Upload file to Slack
            response = self.client.files_upload_v2(
                channel=self.channel,
                file=file_path,
                title=f"{name} Report",
                initial_comment=f"<!subteam^SU0D3NYQ6> Triggered the {name} automation. Here is the CSV report you requested <@U0690AB2SKX>"
            )
            log.info(f"File uploaded successfully: {response['file']['name']}")
        except SlackApiError as e:
            log.info(f"Error uploading file: {e.response['error']}")

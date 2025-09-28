import time
from util.logger import get_logger

log = get_logger()

# Utility function to handle rate limiting and retries
def handle_rate_limiting(response):
    if 'X-Shopify-Shop-Api-Call-Limit' in response.headers:
        api_limit = response.headers['X-Shopify-Shop-Api-Call-Limit']
        log.info(f"API call limit: {api_limit}")
        
    if response.status_code == 429:  # Too many requests
        retry_after = int(response.headers.get("Retry-After", 5))
        log.warning(f"Rate limit exceeded. Retrying after {retry_after} seconds...")
        time.sleep(retry_after)
        return True
    return False

# Utility function to handle status codes
def handle_status_codes(response):
    if response.status_code == 200:
        log.info("Successfully fetched pending orders.")
        return True
    elif response.status_code == 401:
        log.error("Unauthorized access. Check your API key.")
    elif response.status_code == 404:
        log.error("Resource not found.")
    elif response.status_code == 500:
        log.error("Internal server error.")
    else:
        log.error(f"Unexpected status code: {response.status_code}")
    return False

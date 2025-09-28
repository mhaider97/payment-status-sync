from datetime import datetime, timedelta

def get_days_ago(days=30):
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

def older_than(ref_date, days=30):
    return datetime.now() - datetime.strptime(ref_date, '%Y-%m-%dT%H:%M:%SZ') > timedelta(days=days)

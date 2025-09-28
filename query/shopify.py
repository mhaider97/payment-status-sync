from util.common import get_days_ago

def get_pending_orders_query(cursor=None):
    thirty_days_ago = get_days_ago(30)

    query = f"""
    {{
        orders(query: "financial_status:pending created_at:>{thirty_days_ago} gateway:paypal status:open", first: 50, after: CURSOR_PLACEHOLDER) {{
            edges {{
                node {{
                    id
                    name
                    createdAt
                    displayFinancialStatus
                    displayFulfillmentStatus
                    transactions {{
                        id
                        createdAt
                        gateway
                        paymentId
                        authorizationCode
                        status
                        amount
                    }}
                }}
                cursor
            }}
            pageInfo {{
                hasNextPage
            }}
        }}
    }}
    """
    
    # Replace placeholder with the actual cursor if pagination is needed
    if cursor:
        query = query.replace("CURSOR_PLACEHOLDER", f'"{cursor}"')
    else:
        query = query.replace("CURSOR_PLACEHOLDER", "null")
    
    return query

def get_mark_paid_order_query():
    # GraphQL query for marking the order as paid
    return """
    mutation orderMarkAsPaid($input: OrderMarkAsPaidInput!) {
      orderMarkAsPaid(input: $input) {
        order {
          id
          name
          closed
          confirmed
          closedAt
          fullyPaid
        }
        userErrors {
          field
          message
        }
      }
    }
    """

def get_cancel_order_query():
    return """
    mutation orderCancel($orderId: ID!, $reason: OrderCancelReason!, $refund: Boolean!, $restock: Boolean!, $notifyCustomer: Boolean!) {
      orderCancel(orderId: $orderId, reason: $reason, refund: $refund, restock: $restock, notifyCustomer: $notifyCustomer) {
        job {
          id
          done
        }
        orderCancelUserErrors {
          code
          field
          message
        }
      }
    }
    """

def get_fetching_cancelled_orders_query(cursor=None):
    thirty_days_ago = get_days_ago(30)

    query = f"""
    {{
        orders(query: "NOT financial_status:refunded NOT financial_status:partially_refunded created_at:>{thirty_days_ago} gateway:paypal status:cancelled", first: 50, after: CURSOR_PLACEHOLDER) {{
            edges {{
                node {{
                    id
                    name
                    createdAt
                    cancelledAt
                    displayFinancialStatus
                    displayFulfillmentStatus
                    transactions {{
                        id
                        createdAt
                        gateway
                        paymentId
                        authorizationCode
                        status
                        amount
                    }}
                }}
                cursor
            }}
            pageInfo {{
                hasNextPage
            }}
        }}
    }}
    """
    
    # Replace placeholder with the actual cursor if pagination is needed
    if cursor:
        query = query.replace("CURSOR_PLACEHOLDER", f'"{cursor}"')
    else:
        query = query.replace("CURSOR_PLACEHOLDER", "null")
    
    return query

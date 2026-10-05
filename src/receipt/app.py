"""ReceiptFn - Step Functions task: GenerateReceipt
Writes receipts/<orderId>.html to the receipts bucket.
Input:  output of ReserveStock
Output: {"receiptKey": "receipts/<orderId>.html"}
Env: RECEIPTS_BUCKET
IAM: s3:PutObject on receipts/*; kms:GenerateDataKey on your key (after Block I)
"""
import html
import os
from datetime import datetime, timezone

import boto3

s3 = boto3.client("s3")
BUCKET = os.environ["RECEIPTS_BUCKET"]


def handler(event, context):
    order_id = event["orderId"]
    key = f"receipts/{order_id}.html"

    rows = "".join(
        f"<tr><td>{html.escape(str(i['name']))}</td><td>{i['qty']}</td>"
        f"<td>{i['price']}</td><td>{i['lineTotal']}</td></tr>"
        for i in event["items"]
    )
    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>CloudCart receipt {order_id}</title></head>
<body style="font-family:sans-serif;max-width:600px;margin:2rem auto">
<h1>CloudCart receipt</h1>
<p>Order: {order_id}<br>Date: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC</p>
<table border="1" cellpadding="6" cellspacing="0" width="100%">
<tr><th>Item</th><th>Qty</th><th>Price</th><th>Line total</th></tr>
{rows}
<tr><td colspan="3"><b>Total</b></td><td><b>{event['total']}</b></td></tr>
</table>
</body></html>"""

    s3.put_object(Bucket=BUCKET, Key=key, Body=page.encode(), ContentType="text/html")
    return {"receiptKey": key}

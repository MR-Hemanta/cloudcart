"""ProductsFn - GET /products
Returns the product catalog from the Products table.
Env: PRODUCTS_TABLE
IAM: dynamodb:Scan on the Products table
"""
import json
import os
from decimal import Decimal

import boto3

table = boto3.resource("dynamodb").Table(os.environ["PRODUCTS_TABLE"])

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",  # Block I: change to your CloudFront URL
}


def to_json(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Cannot serialise {type(obj)}")


def handler(event, context):
    items = table.scan().get("Items", [])
    items.sort(key=lambda p: p["productId"])
    return {
        "statusCode": 200,
        "headers": HEADERS,
        "body": json.dumps({"products": items}, default=to_json),
    }

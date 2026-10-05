"""OrdersFn - POST /orders, GET /orders, GET /orders/{id}
POST saves the order as PENDING, sends it to SQS, returns 202.
Env: ORDERS_TABLE, QUEUE_URL (added in Block G - sending is skipped until it is set)
IAM: dynamodb:PutItem, GetItem, Query (table + index); sqs:SendMessage
"""
import json
import os
import time
import uuid
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key

table = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE"])
sqs = boto3.client("sqs")
QUEUE_URL = os.environ.get("QUEUE_URL", "")
INDEX = "userId-createdAt-index"

HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",  # Block I: change to your CloudFront URL
}


def to_json(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Cannot serialise {type(obj)}")


def reply(status, body):
    return {"statusCode": status, "headers": HEADERS, "body": json.dumps(body, default=to_json)}


def create_order(user_id, body):
    try:
        data = json.loads(body or "{}")
        items = [{"productId": str(i["productId"]), "qty": int(i["qty"])} for i in data["items"]]
    except (ValueError, KeyError, TypeError):
        return reply(400, {"message": 'Body must be {"items":[{"productId":"p1","qty":2}]}'})
    if not items or any(i["qty"] < 1 for i in items):
        return reply(400, {"message": "Add at least one item with qty 1 or more"})

    order = {
        "orderId": str(uuid.uuid4()),
        "userId": user_id,
        "items": items,
        "status": "PENDING",
        "createdAt": int(time.time()),
    }
    table.put_item(Item=order)

    if QUEUE_URL:
        msg = {"orderId": order["orderId"], "userId": user_id, "items": items}
        sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(msg))
    else:
        print("QUEUE_URL not set - order saved but not queued (expected before Block G)")

    return reply(202, {"orderId": order["orderId"], "status": "PENDING"})


def list_orders(user_id):
    res = table.query(
        IndexName=INDEX,
        KeyConditionExpression=Key("userId").eq(user_id),
        ScanIndexForward=False,  # newest first
    )
    return reply(200, {"orders": res.get("Items", [])})


def get_order(user_id, order_id):
    item = table.get_item(Key={"orderId": order_id}).get("Item")
    if not item or item["userId"] != user_id:  # never show another user's order
        return reply(404, {"message": "Order not found"})
    return reply(200, item)


def handler(event, context):
    user_id = event["requestContext"]["authorizer"]["claims"]["sub"]
    method = event["httpMethod"]
    order_id = (event.get("pathParameters") or {}).get("id")

    if method == "POST":
        return create_order(user_id, event.get("body"))
    if method == "GET" and order_id:
        return get_order(user_id, order_id)
    if method == "GET":
        return list_orders(user_id)
    return reply(405, {"message": f"{method} not supported"})

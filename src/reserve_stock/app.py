"""ReserveStockFn - Step Functions task: ReserveStock
Takes stock for every item with a conditional update, so stock never goes below 0.
Input:  {"orderId", "userId", "items": [{"productId", "qty"}]}
Output: same order plus name, price and lineTotal per item, and the order total
Env: PRODUCTS_TABLE
IAM: dynamodb:UpdateItem on the Products table
"""
import os

import boto3
from botocore.exceptions import ClientError

table = boto3.resource("dynamodb").Table(os.environ["PRODUCTS_TABLE"])


class OutOfStock(Exception):
    """Error name the workflow catches (Catch -> MarkFailed)."""


def handler(event, context):
    lines = []
    for it in event["items"]:
        try:
            res = table.update_item(
                Key={"productId": it["productId"]},
                UpdateExpression="SET stock = stock - :q",
                ConditionExpression="stock >= :q",  # blocks overselling
                ExpressionAttributeValues={":q": it["qty"]},
                ReturnValues="ALL_NEW",
            )
        except ClientError as err:
            if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
                # Bonus: restore stock already taken for earlier items (compensating rollback)
                raise OutOfStock(f"Not enough stock for {it['productId']}") from err
            raise

        product = res["Attributes"]
        price = int(product.get("price", 0))
        lines.append({
            "productId": it["productId"],
            "name": product.get("name", it["productId"]),
            "qty": it["qty"],
            "price": price,
            "lineTotal": price * it["qty"],
        })

    return {
        "orderId": event["orderId"],
        "userId": event["userId"],
        "items": lines,
        "total": sum(line["lineTotal"] for line in lines),
    }

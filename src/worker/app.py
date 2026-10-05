"""WorkerFn - SQS trigger (batch size 1)
Starts one Step Functions execution per order.
Env: STATE_MACHINE_ARN (added in Block H - until then it only logs the message)
IAM: sqs:ReceiveMessage, DeleteMessage, GetQueueAttributes; states:StartExecution
"""
import json
import os

import boto3

sfn = boto3.client("stepfunctions")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")


def handler(event, context):
    for record in event["Records"]:
        print("Message body:", record["body"])
        order = json.loads(record["body"])

        if not STATE_MACHINE_ARN:
            print("STATE_MACHINE_ARN not set - logging only (expected in Block G)")
            continue

        try:
            sfn.start_execution(
                stateMachineArn=STATE_MACHINE_ARN,
                name=order["orderId"],  # one execution per order, even if SQS delivers twice
                input=json.dumps(order),
            )
            print("Started workflow for order", order["orderId"])
        except sfn.exceptions.ExecutionAlreadyExists:
            print("Workflow already started for order", order["orderId"])

"""
EC2 Auto Start/Stop Scheduler
-----------------------------
Triggered by Amazon EventBridge Scheduler with an input like:
    {"action": "stop"}   -> stops running instances that carry the tag
    {"action": "start"}  -> starts stopped instances that carry the tag

Only instances tagged  <TAG_KEY>=<TAG_VALUE>  (default: Schedule=office-hours)
are ever touched.
"""

import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client("ec2")

TAG_KEY = os.environ.get("TAG_KEY", "Schedule")
TAG_VALUE = os.environ.get("TAG_VALUE", "office-hours")


def get_tagged_instances(states):
    """Return IDs of tagged instances that are in one of the given states."""
    instance_ids = []
    paginator = ec2.get_paginator("describe_instances")
    pages = paginator.paginate(
        Filters=[
            {"Name": f"tag:{TAG_KEY}", "Values": [TAG_VALUE]},
            {"Name": "instance-state-name", "Values": states},
        ]
    )
    for page in pages:
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                instance_ids.append(instance["InstanceId"])
    return instance_ids


def lambda_handler(event, context):
    action = (event or {}).get("action", "").lower()
    logger.info("Received action: %s | Tag filter: %s=%s", action, TAG_KEY, TAG_VALUE)

    if action == "stop":
        instance_ids = get_tagged_instances(["running"])
        if instance_ids:
            ec2.stop_instances(InstanceIds=instance_ids)
            logger.info("Stopping instances: %s", instance_ids)
        else:
            logger.info("No running instances found with the tag.")

    elif action == "start":
        instance_ids = get_tagged_instances(["stopped"])
        if instance_ids:
            ec2.start_instances(InstanceIds=instance_ids)
            logger.info("Starting instances: %s", instance_ids)
        else:
            logger.info("No stopped instances found with the tag.")

    else:
        raise ValueError(
            f"Unknown action '{action}'. Use {{\"action\": \"start\"}} or {{\"action\": \"stop\"}}."
        )

    return {"action": action, "instances": instance_ids, "count": len(instance_ids)}

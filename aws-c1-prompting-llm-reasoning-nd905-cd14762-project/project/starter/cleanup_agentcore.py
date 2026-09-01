#!/usr/bin/env python3
"""Delete the harness, the gateway target, and the gateway (in that order),
reading their ids from agentcore_config.json.
"""
import json
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
CONFIG_PATH = Path("agentcore_config.json")


def safe(fn, label):
    try:
        fn()
        print(f"Deleted {label}.")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("ResourceNotFoundException", "ResourceNotFound"):
            print(f"{label} already gone.")
        else:
            print(f"Could not delete {label}: {e}", file=sys.stderr)


def main():
    if not CONFIG_PATH.exists():
        sys.exit("agentcore_config.json not found - nothing to delete.")
    config = json.loads(CONFIG_PATH.read_text())

    ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)

    if "harness_id" in config:
        safe(lambda: ctl.delete_harness(
            harnessId=config["harness_id"], deleteManagedMemory=True),
            f"harness {config['harness_id']}")
    if "gateway_target_id" in config and "gateway_id" in config:
        safe(lambda: ctl.delete_gateway_target(
            gatewayIdentifier=config["gateway_id"],
            targetId=config["gateway_target_id"]),
            f"gateway target {config['gateway_target_id']}")
    if "gateway_id" in config:
        safe(lambda: ctl.delete_gateway(
            gatewayIdentifier=config["gateway_id"]),
            f"gateway {config['gateway_id']}")

    print("Done.")


if __name__ == "__main__":
    main()

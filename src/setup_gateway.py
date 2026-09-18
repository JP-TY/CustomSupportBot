#!/usr/bin/env python3
"""Create the AgentCore Gateway and register the bug report Lambda as the
create_bug_report tool. Saves what later steps need to agentcore_config.json.

If this fails right after the stack finishes with an access or validation
error mentioning the role, that's IAM propagation delay - the script retries;
just run it again a minute later if it still fails.
"""
import json
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
STACK_NAME = "bug-report-tool-stack"
GATEWAY_NAME = "support-gateway"
TARGET_NAME = "bugreports"
CONFIG_PATH = Path("agentcore_config.json")

TOOL_SCHEMA = [{
    "name": "create_bug_report",
    "description": (
        "Create a bug report ticket for the engineering team. Call only after "
        "the customer has supplied all three values. Do not call when any "
        "value is missing, guessed, empty, whitespace-only, or an HTML/text "
        "placeholder."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": (
                    "The specific bug, in the customer's own words. Do not use "
                    "a vague placeholder such as 'it doesn't work'."
                ),
            },
            "stepsToReproduce": {
                "type": "string",
                "description": (
                    "Numbered steps supplied by the customer. Do not invent "
                    "steps from the FAQ or use empty, whitespace-only, or "
                    "placeholder text."
                ),
            },
            "environment": {
                "type": "string",
                "description": (
                    "Customer's browser, operating system, and device. Do not "
                    "use empty, whitespace-only, or placeholder text."
                ),
            },
        },
        "required": ["description", "stepsToReproduce", "environment"],
    },
}]


def build_target_payload(lambda_arn):
    return {
        "targetConfiguration": {"mcp": {"lambda": {
            "lambdaArn": lambda_arn,
            "toolSchema": {"inlinePayload": TOOL_SCHEMA},
        }}},
        "credentialProviderConfigurations": [
            {"credentialProviderType": "GATEWAY_IAM_ROLE"}
        ],
    }


def target_matches(target, payload):
    current = target.get("targetConfiguration", {})
    desired = payload["targetConfiguration"]
    current_credentials = target.get("credentialProviderConfigurations")
    desired_credentials = payload["credentialProviderConfigurations"]
    return current == desired and current_credentials == desired_credentials


def update_target(ctl, gateway_id, target_id, target_name, target_description, payload):
    return ctl.update_gateway_target(
        gatewayIdentifier=gateway_id,
        targetId=target_id,
        name=target_name,
        description=target_description,
        credentialProviderConfigurations=payload["credentialProviderConfigurations"],
        targetConfiguration=payload["targetConfiguration"],
    )


def stack_outputs():
    cfn = boto3.client("cloudformation", region_name=REGION)
    stacks = cfn.describe_stacks(StackName=STACK_NAME)["Stacks"]
    return {o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])}


def create_gateway_with_retry(ctl, role_arn, attempts=5, pause=30):
    for attempt in range(1, attempts + 1):
        try:
            return ctl.create_gateway(
                name=GATEWAY_NAME,
                roleArn=role_arn,
                protocolType="MCP",
                authorizerType="AWS_IAM",
            )
        except ClientError as e:
            msg = str(e)
            retryable = attempt < attempts and any(
                s in msg for s in ("AccessDenied", "not authorized", "NotFound", "not exist")
            )
            if not retryable:
                raise
            print(f"  IAM propagation delay (attempt {attempt}/{attempts}), retrying in {pause}s...")
            time.sleep(pause)
    raise RuntimeError("create_gateway failed after retries")


def wait_gateway_ready(ctl, gateway_id, timeout=300):
    for _ in range(timeout // 10):
        gw = ctl.get_gateway(gatewayIdentifier=gateway_id)  # flat response
        status = gw.get("status")
        if status in ("READY", "ACTIVE"):
            return gw
        if status == "FAILED":
            raise RuntimeError(f"gateway entered FAILED: {gw.get('statusReasons')}")
        time.sleep(10)
    raise TimeoutError("gateway did not become READY in time")


def wait_target_ready(ctl, gateway_id, target_id, timeout=300):
    for _ in range(timeout // 10):
        t = ctl.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
        status = t.get("status")
        if status in ("READY", "ACTIVE"):
            return t
        if status == "FAILED":
            raise RuntimeError(f"gateway target entered FAILED: {t.get('statusReasons')}")
        time.sleep(10)
    raise TimeoutError("gateway target did not become READY in time")


def main():
    outputs = stack_outputs()
    lambda_arn = outputs["LambdaFunctionArn"]
    gateway_role_arn = outputs["GatewayRoleArn"]
    print(f"Lambda: {lambda_arn}")
    print(f"Gateway role: {gateway_role_arn}")

    ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)

    base_config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}

    # Reuse an existing gateway (idempotent re-run) or create one.
    gateway_id = base_config.get("gateway_id")
    if gateway_id:
        try:
            gw = ctl.get_gateway(gatewayIdentifier=gateway_id)
            print(f"Reusing gateway {gateway_id} (status {gw.get('status')})")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") not in {
                "ResourceNotFoundException",
                "ResourceNotFound",
            }:
                raise
            print(f"Saved gateway {gateway_id} no longer exists; creating a replacement.")
            gateway_id = None
            base_config.pop("gateway_id", None)
            base_config.pop("gateway_target_id", None)
    if not gateway_id:
        existing = next((g for g in ctl.list_gateways(maxResults=50).get("items", [])
                         if g.get("name") == GATEWAY_NAME), None)
        if existing:
            gateway_id = existing["gatewayId"]
            gw = ctl.get_gateway(gatewayIdentifier=gateway_id)
            print(f"Found existing gateway '{GATEWAY_NAME}': {gw['gatewayArn']}")
        else:
            print(f"Creating gateway '{GATEWAY_NAME}'...")
            gw = create_gateway_with_retry(ctl, gateway_role_arn)
            gateway_id = gw["gatewayId"]
            print(f"Gateway: {gw['gatewayArn']} (status {gw.get('status', '?')})")
    gateway_arn = gw["gatewayArn"]
    gateway_url = gw.get("gatewayUrl", "")

    wait_gateway_ready(ctl, gateway_id)

    # Reuse an existing target (idempotent re-run) or register the Lambda.
    # Always reconcile its tool schema so prompt and gateway stay consistent.
    payload = build_target_payload(lambda_arn)
    target = None
    target_id = base_config.get("gateway_target_id")
    if target_id:
        try:
            target = ctl.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
            print(f"Found saved target {target_id}")
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") not in {
                "ResourceNotFoundException",
                "ResourceNotFound",
            }:
                raise
            print(f"Saved target {target_id} no longer exists; registering a replacement.")
            target_id = None
            target = None
            base_config.pop("gateway_target_id", None)
    if target is None:
        existing_t = next((t for t in ctl.list_gateway_targets(
            gatewayIdentifier=gateway_id).get("items", [])
            if t.get("name") == TARGET_NAME), None)
        if existing_t:
            target_id = existing_t["targetId"]
            target = ctl.get_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
            print(f"Found existing target '{TARGET_NAME}': {target_id}")
    if target is None:
        print(f"Registering Lambda target '{TARGET_NAME}'...")
        target = ctl.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=TARGET_NAME,
            description="Bug report ticket tool",
            **payload,
        )
        target_id = target["targetId"]
        print(f"Target: {target_id} (status {target.get('status', '?')})")
    elif not target_matches(target, payload):
        print(f"Updating Lambda target '{TARGET_NAME}' to the current tool schema...")
        target = update_target(
            ctl,
            gateway_id,
            target_id,
            TARGET_NAME,
            "Bug report ticket tool",
            payload,
        )
        print(f"Target: {target_id} (status {target.get('status', '?')})")
    else:
        print(f"Reusing target {target_id}")

    wait_target_ready(ctl, gateway_id, target_id)

    config = {
        **base_config,
        "gateway_id": gateway_id,
        "gateway_arn": gateway_arn,
        "gateway_url": gateway_url,
        "gateway_target_id": target_id,
        "lambda_arn": lambda_arn,
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    print(f"\nSaved {CONFIG_PATH}:")
    print(json.dumps(config, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

#!/usr/bin/env python3
"""Create (or update) the support-chatbot managed harness from system_prompt.txt.

The {{FAQ}} placeholder in the prompt is replaced with the contents of
online_shop_faq.md. The harness is pinned to us.amazon.nova-pro-v1:0 (do not
rely on the harness default model, which needs a marketplace subscription)
and gets the bug report gateway attached as its tool source.

Re-run after every change to system_prompt.txt.
"""
import json
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
HARNESS_NAME = "support_chatbot"
MODEL_ID = "us.amazon.nova-pro-v1:0"
CONFIG_PATH = Path("agentcore_config.json")
PROMPT_PATH = Path("system_prompt.txt")
FAQ_PATH = Path("online_shop_faq.md")


def build_system_prompt():
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    faq = FAQ_PATH.read_text(encoding="utf-8")
    if "{{FAQ}}" not in prompt:
        raise RuntimeError("system_prompt.txt is missing the {{FAQ}} placeholder")
    return prompt.replace("{{FAQ}}", faq)


def create_with_retry(ctl, harness_role_arn, system_prompt, tools,
                      attempts=5, pause=30):
    payload = {
        "harnessName": HARNESS_NAME,
        "executionRoleArn": harness_role_arn,
        "systemPrompt": [{"text": system_prompt}],
        "model": {"bedrockModelConfig": {"modelId": MODEL_ID}},
        "tools": tools,
        # Managed long-term memory cross-contaminates sessions (retrieved
        # memories look like "already provided" bug details). Session state
        # alone gives us multi-turn behavior; disable memory.
        "memory": {"disabled": {}},
    }
    for attempt in range(1, attempts + 1):
        try:
            return ctl.create_harness(**payload)
        except ClientError as e:
            msg = str(e)
            retryable = attempt < attempts and any(
                s in msg for s in ("AccessDenied", "not authorized", "NotFound", "not exist")
            )
            if not retryable:
                raise
            print(f"  IAM propagation delay (attempt {attempt}/{attempts}), retrying in {pause}s...")
            time.sleep(pause)
    raise RuntimeError("create_harness failed after retries")


def wait_harness_ready(ctl, harness_id, timeout=600):
    for _ in range(timeout // 15):
        h = ctl.get_harness(harnessId=harness_id)["harness"]
        status = h.get("status")
        if status == "READY":
            return h
        if status in ("FAILED", "CREATE_FAILED", "UPDATE_FAILED"):
            raise RuntimeError(f"harness entered {status}: {h.get('failureReason')}")
        print(f"  status: {status}...")
        time.sleep(15)
    raise TimeoutError("harness did not become READY in time")


def main():
    outputs_role = None
    cfn = boto3.client("cloudformation", region_name=REGION)
    stacks = cfn.describe_stacks(StackName="bug-report-tool-stack")["Stacks"]
    outputs_role = {
        o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])
    }["HarnessRoleArn"]

    config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    if "gateway_arn" not in config:
        sys.exit("agentcore_config.json missing gateway_arn - run setup_gateway.py first.")

    system_prompt = build_system_prompt()
    tools = [{
        "type": "agentcore_gateway",
        "config": {"agentCoreGateway": {"gatewayArn": config["gateway_arn"]}},
    }]

    ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)

    existing = next((h for h in ctl.list_harnesses(maxResults=50).get("harnesses", [])
                     if h.get("harnessName") == HARNESS_NAME), None)

    if config.get("harness_id") or existing:
        harness_id = config.get("harness_id") or existing["harnessId"]
        print(f"Updating harness {harness_id}...")
        ctl.update_harness(
            harnessId=harness_id,
            executionRoleArn=outputs_role,
            systemPrompt=[{"text": system_prompt}],
            model={"bedrockModelConfig": {"modelId": MODEL_ID}},
            tools=tools,
            memory={"optionalValue": {"disabled": {}}},  # UpdateHarness wraps memory
        )
    else:
        print(f"Creating harness '{HARNESS_NAME}' (model {MODEL_ID})...")
        created = create_with_retry(ctl, outputs_role, system_prompt, tools)
        harness_id = created["harness"]["harnessId"]
        print(f"Harness id: {harness_id}")

    harness = wait_harness_ready(ctl, harness_id)

    config.update({
        "harness_id": harness_id,
        "harness_arn": harness["arn"],
        "harness_name": harness.get("harnessName", HARNESS_NAME),
        "model_id": MODEL_ID,
    })
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n")
    print(f"\nHarness READY: {harness['arn']}")
    print(f"Saved {CONFIG_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

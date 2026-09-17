#!/usr/bin/env python3
"""Invoke the deployed Bedrock message-routing flow for one customer message."""
import argparse
import json
import sys
from pathlib import Path

import boto3

REGION = "us-east-1"
CONFIG_PATH = Path("flow-config.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message", required=True, help="Customer message to route.")
    parser.add_argument("--enable-trace", action="store_true")
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    client = boto3.client("bedrock-agent-runtime", region_name=REGION)
    response = client.invoke_flow(
        flowIdentifier=config["flow_id"],
        flowAliasIdentifier=config["alias_id"],
        enableTrace=args.enable_trace,
        inputs=[
            {
                "nodeName": config["input_node"],
                "nodeOutputName": config["input_output"],
                "content": {"document": args.message},
            }
        ],
    )

    output = None
    for event in response["responseStream"]:
        if "flowOutputEvent" in event:
            output = event["flowOutputEvent"]
    if output is None:
        raise RuntimeError("flow completed without an output event")

    node_name = output.get("nodeName")
    node_type = output.get("nodeType")
    if node_type:
        print(f"[flow output node] {node_name} ({node_type})")
    else:
        print(f"[flow output node] {node_name}")
    print(output.get("content", {}).get("document", ""))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

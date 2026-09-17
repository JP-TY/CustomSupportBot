#!/usr/bin/env python3
"""Create or update the Bedrock message-routing flow from a checked-in definition.

The flow template contains a ``{{FAQ}}`` placeholder. This script expands it
with ``online_shop_faq.md``, validates the classifier/condition/output graph
locally, validates it with Bedrock, then creates or updates the flow, prepares
a version, and points the live alias at that version.
"""
import argparse
import json
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
STACK_NAME = "bug-report-tool-stack"
FLOW_NAME = "CustomerSupportRouter"
ALIAS_NAME = "live"
TEMPLATE_PATH = Path("bedrock-flow-definition.template.json")
FAQ_PATH = Path("online_shop_faq.md")
DEFINITION_PATH = Path("bedrock-flow-definition.json")
CONFIG_PATH = Path("flow-config.json")
REQUIRED_CONDITIONS = {
    "IsBugReport": 'category == "BUG_REPORT"',
    "IsPlatformQuestion": 'category == "PLATFORM_QUESTION"',
}
# The default branch handles OTHER and any unexpected classifier value.
TERMINAL_OUTPUTS = {
    "IsBugReport": ("Prompt_Bug_Report_Intake", "FlowOutput_Bug_Report"),
    "IsPlatformQuestion": ("Prompt_Platform_Answer", "FlowOutput_Platform_Answer"),
    "default": ("Prompt_Other_Handoff", "FlowOutput_Other_Handoff"),
}


def load_definition():
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    faq = FAQ_PATH.read_text(encoding="utf-8")
    if "{{FAQ}}" not in template:
        raise RuntimeError("flow template is missing the {{FAQ}} placeholder")
    payload = json.loads(template.replace("{{FAQ}}", json.dumps(faq)[1:-1]))
    payload["generatedFrom"] = [TEMPLATE_PATH.name, FAQ_PATH.name]
    DEFINITION_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def validate_local_graph(payload):
    nodes = {node["name"]: node for node in payload["definition"]["nodes"]}
    connections = payload["definition"]["connections"]
    required_nodes = {
        "FlowInputNode",
        "Prompt_Classify_Customer_Message",
        "InlineCode_Normalize_Category",
        "Condition_Route_Customer_Message",
        "Prompt_Bug_Report_Intake",
        "Prompt_Platform_Answer",
        "Prompt_Other_Handoff",
        "FlowOutput_Bug_Report",
        "FlowOutput_Platform_Answer",
        "FlowOutput_Other_Handoff",
    }
    missing = required_nodes - set(nodes)
    if missing:
        raise RuntimeError(f"flow definition is missing nodes: {sorted(missing)}")

    condition = nodes["Condition_Route_Customer_Message"]["configuration"]["condition"]
    expressions = {
        item["name"]: item.get("expression")
        for item in condition["conditions"]
        if item["name"] != "default"
    }
    if expressions != REQUIRED_CONDITIONS:
        raise RuntimeError(f"unexpected condition expressions: {expressions}")
    if not any(item["name"] == "default" for item in condition["conditions"]):
        raise RuntimeError("condition node must include a default condition")

    conditional_targets = {
        (item["source"], item["configuration"]["conditional"]["condition"]): item["target"]
        for item in connections
        if item["type"] == "Conditional"
    }
    for condition_name, (route, output) in TERMINAL_OUTPUTS.items():
        actual_route = conditional_targets.get(
            ("Condition_Route_Customer_Message", condition_name)
        )
        if actual_route != route:
            raise RuntimeError(f"{condition_name} does not target {route}")
        terminal = next(
            item["target"]
            for item in connections
            if item["type"] == "Data" and item["source"] == route
        )
        if terminal != output:
            raise RuntimeError(f"{route} does not terminate at {output}")


def flow_model_ids(payload):
    model_ids = set()
    for node in payload["definition"]["nodes"]:
        inline = (
            node.get("configuration", {})
            .get("prompt", {})
            .get("sourceConfiguration", {})
            .get("inline", {})
        )
        if "modelId" in inline:
            model_ids.add(inline["modelId"])
    return sorted(model_ids)


def stack_output(name):
    cfn = boto3.client("cloudformation", region_name=REGION)
    stacks = cfn.describe_stacks(StackName=STACK_NAME)["Stacks"]
    outputs = {item["OutputKey"]: item["OutputValue"] for item in stacks[0].get("Outputs", [])}
    return outputs[name]


def find_flow(client, name):
    flows = client.list_flows(maxResults=100).get("flowSummaries", [])
    return next((flow for flow in flows if flow.get("name") == name), None)


def find_alias(client, flow_id, name):
    aliases = client.list_flow_aliases(flowIdentifier=flow_id, maxResults=100).get(
        "flowAliasSummaries", []
    )
    return next((alias for alias in aliases if alias.get("name") == name), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow-name", default=FLOW_NAME)
    parser.add_argument("--alias-name", default=ALIAS_NAME)
    args = parser.parse_args()

    payload = load_definition()
    validate_local_graph(payload)
    definition = payload["definition"]
    role_arn = stack_output("FlowExecutionRoleArn")
    client = boto3.client("bedrock-agent", region_name=REGION)

    try:
        client.validate_flow_definition(definition=definition)
    except ClientError as error:
        raise RuntimeError(f"Bedrock rejected the flow definition: {error}") from error

    existing = find_flow(client, args.flow_name)
    if existing:
        print(f"Updating flow {existing['id']}...")
        flow = client.update_flow(
            name=args.flow_name,
            description=payload["description"],
            executionRoleArn=role_arn,
            flowIdentifier=existing["id"],
            definition=definition,
        )
        flow_id = flow["id"]
    else:
        print(f"Creating flow '{args.flow_name}'...")
        flow = client.create_flow(
            name=args.flow_name,
            description=payload["description"],
            executionRoleArn=role_arn,
            definition=definition,
        )
        flow_id = flow["id"]
        print(f"Flow id: {flow_id}")

    print("Preparing flow...")
    client.prepare_flow(flowIdentifier=flow_id)
    version = client.create_flow_version(
        flowIdentifier=flow_id,
        description=f"Message-router version for {args.flow_name}",
    )["version"]
    print(f"Flow version: {version}")

    alias = find_alias(client, flow_id, args.alias_name)
    if alias:
        print(f"Updating alias {args.alias_name}...")
        alias_response = client.update_flow_alias(
            flowIdentifier=flow_id,
            aliasIdentifier=alias["id"],
            name=args.alias_name,
            routingConfiguration=[{"flowVersion": version}],
        )
        alias_id = alias_response["id"]
    else:
        print(f"Creating alias {args.alias_name}...")
        alias_response = client.create_flow_alias(
            flowIdentifier=flow_id,
            name=args.alias_name,
            routingConfiguration=[{"flowVersion": version}],
        )
        alias_id = alias_response["id"]

    config = {
        "flow_id": flow_id,
        "flow_arn": flow["arn"],
        "flow_version": version,
        "alias_id": alias_id,
        "alias_arn": alias_response["arn"],
        "alias_name": args.alias_name,
        "input_node": "FlowInputNode",
        "input_output": "document",
        "model_ids": flow_model_ids(payload),
        "region": REGION,
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"\nFlow ready: {flow['arn']} (alias {args.alias_name} -> version {version})")
    print(f"Saved {CONFIG_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

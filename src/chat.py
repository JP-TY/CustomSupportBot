#!/usr/bin/env python3
"""Terminal chat client for the support-chatbot AgentCore harness.

Each run is one fresh conversation. Use interactively, or send a single
message non-interactively:

    python chat.py
    python chat.py --message "Where do you ship?" [--session-id <id>]
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

import boto3

from harness_client import REGION, gateway_tools, invoke_text

CONFIG_PATH = Path("agentcore_config.json")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--message", help="Send one message and exit (non-interactive).")
    p.add_argument("--session-id", default=str(uuid.uuid4()),
                   help="Reuse a session id for multi-turn scripting (default: fresh per run).")
    args = p.parse_args()
    args.session_id = args.session_id.ljust(33, "0")  # API requires >= 33 chars

    config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    if "harness_arn" not in config:
        sys.exit("agentcore_config.json missing harness_arn - run create_harness.py first.")

    client = boto3.client("bedrock-agentcore", region_name=REGION)
    tools = gateway_tools(config)

    def handle_tool_call(name):
        print(f"\n[tool call] {name}", flush=True)

    def turn(text):
        reply = invoke_text(client, config["harness_arn"], args.session_id,
                            text, tools=tools, on_tool_call=handle_tool_call)
        print(reply, flush=True)
        print()

    if args.message is not None:
        turn(args.message)
        return

    print(f"Support chatbot (session {args.session_id})")
    print("Type your message. Ctrl-D or 'exit' to quit.\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text or text.lower() in ("exit", "quit"):
            break
        turn(text)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run the harness against a test suite and produce a JSONL dataset for
Bedrock Evaluations (LLM-as-a-judge, BYOI).

Reads the harness and gateway ARNs from agentcore_config.json, invokes the
harness once per test with a fresh runtimeSessionId (tests cannot influence
each other), attaching the gateway on every invoke so the model can call
create_bug_report, and pins the model to us.amazon.nova-pro-v1:0.

Usage:
    python generate-eval-dataset.py --tests-json flow-tests.json
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
    p.add_argument("--tests-json", required=True,
                   help="Path to the test suite JSON.")
    p.add_argument("--config", default=str(CONFIG_PATH))
    p.add_argument("--model-identifier", default="my-support-chatbot",
                   help="Value for modelResponses[0].modelIdentifier (must "
                        "match the precomputedInferenceSourceIdentifier in "
                        "the evaluation job).")
    p.add_argument("--out-jsonl", default="output_eval_dataset.jsonl")
    args = p.parse_args()

    config = json.loads(Path(args.config).read_text())
    harness_arn = config["harness_arn"]
    tools = gateway_tools(config)

    client = boto3.client("bedrock-agentcore", region_name=REGION)
    suite = json.loads(Path(args.tests_json).read_text(encoding="utf-8"))
    tests = suite["tests"]

    out_path = Path(args.out_jsonl)
    n_ok = 0

    with out_path.open("w", encoding="utf-8") as f:
        for t in tests:
            test_id = t["id"]
            prompt = t.get("prompt", "")
            reference = t.get("expected", "")
            session_id = str(uuid.uuid4())  # fresh session per test (>= 33 chars)

            try:
                response_text = invoke_text(
                    client, harness_arn, session_id, prompt, tools=tools)
                n_ok += 1
            except Exception as e:
                print(f"{test_id}: {e}", file=sys.stderr)
                response_text = f"[HARNESS_ERROR] {type(e).__name__}: {e}"

            record = {
                "prompt": prompt,
                "referenceResponse": reference,
                "modelResponses": [{
                    "response": response_text,
                    "modelIdentifier": args.model_identifier,
                }],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"{test_id}: wrote eval line", file=sys.stderr)

    print(f"\nWrote {len(tests)} JSONL lines to {out_path} "
          f"({n_ok} harness calls succeeded).", file=sys.stderr)


if __name__ == "__main__":
    main()

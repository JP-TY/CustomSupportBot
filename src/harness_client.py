"""Shared helper for invoking the support-chatbot harness."""
import json
import re

REGION = "us-east-1"

_THINKING_RE = re.compile(r"<thinking>.*?</thinking>\s*", re.S)


def strip_thinking(text):
    """Remove Nova's <thinking> reasoning blocks from model output."""
    return _THINKING_RE.sub("", text)


def gateway_tools(config):
    """Tools override that attaches the gateway on every invoke."""
    return [{
        "type": "agentcore_gateway",
        "config": {"agentCoreGateway": {"gatewayArn": config["gateway_arn"]}},
    }]


def invoke_text(client, harness_arn, session_id, text, tools=None, on_tool_call=None):
    """Invoke the harness with one user message; return the assistant text.

    Prints streaming text unless silent=True (not used); tool calls are
    reported through on_tool_call(name) when provided.
    """
    kwargs = {
        "harnessArn": harness_arn,
        "runtimeSessionId": session_id,
        "messages": [{"role": "user", "content": [{"text": text}]}],
    }
    if tools:
        kwargs["tools"] = tools

    response = client.invoke_harness(**kwargs)

    chunks = []
    seen_tool_calls = set()
    for event in response["stream"]:
        if "contentBlockStart" in event:
            tu = event["contentBlockStart"].get("start", {}).get("toolUse") or {}
            name = tu.get("name")
            if name and name not in seen_tool_calls:
                seen_tool_calls.add(name)
                if on_tool_call:
                    on_tool_call(name)
        elif "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                chunks.append(delta["text"])
            tu = delta.get("toolUse") or {}
            name = tu.get("name")
            if name and name not in seen_tool_calls:
                seen_tool_calls.add(name)
                if on_tool_call:
                    on_tool_call(name)
        elif "internalServerException" in event:
            raise RuntimeError(f"harness internalServerException: {json.dumps(event)}")
        elif "validationException" in event:
            raise RuntimeError(f"harness validationException: {json.dumps(event)}")
        elif "runtimeClientError" in event:
            raise RuntimeError(f"harness runtimeClientError: {json.dumps(event)}")
    return strip_thinking("".join(chunks))

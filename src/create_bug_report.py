import html
import json
import os
import uuid
from datetime import datetime, timezone
import boto3

table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])

REQUIRED_FIELDS = ("description", "stepsToReproduce", "environment")
INVISIBLE_CHARACTERS = ("\u200b", "\u200c", "\u200d", "\ufeff")


def clean_value(value):
    """Normalize tool input so encoded blanks cannot pass validation."""
    text = html.unescape(str(value or ""))
    for character in INVISIBLE_CHARACTERS:
        text = text.replace(character, "")
    return text.strip()


def lambda_handler(event, _):
    print("EVENT:", json.dumps(event, indent=2, default=str))

    if not isinstance(event, dict):
        return {"error": "unsupported_event"}

    # The AgentCore Gateway sends tool arguments directly as the Lambda
    # event: a plain JSON object with no wrapper envelope.
    values = {
        field: clean_value(event.get(field))
        for field in REQUIRED_FIELDS
    }
    missing = [field for field, value in values.items() if not value]
    if missing:
        return {"error": "missing_required_fields", "missing": missing}

    ticket_id = str(uuid.uuid4())
    table.put_item(Item={
        "ticketId": ticket_id,
        "description": values["description"],
        "stepsToReproduce": values["stepsToReproduce"],
        "environment": values["environment"],
        "status": "OPEN",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    })

    return {"ticketId": ticket_id, "status": "OPEN"}

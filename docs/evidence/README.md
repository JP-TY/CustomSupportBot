# Visual evidence package

The PNG files in this directory are **deterministic local renderings**, not
photographs of the AWS Management Console. This environment has CLI access
but no browser-based console-capture tool, so each image is generated from a
checked-in source, transcript, or API/CLI-derived JSON snapshot.

Run:

```bash
python3 docs/evidence/make_evidence_images.py
```

## Image inventory

| Image | Rendered source |
| --- | --- |
| `01-message-routing-flow.png` | `src/system_prompt.txt`, `src/create_harness.py`, `src/chat.py` |
| `02-classifier-prompt-configuration.png` | `src/agentcore_config.json`, `src/system_prompt.txt:5-46` |
| `03-condition-expressions.png` | `src/system_prompt.txt:23-46` |
| `04-dynamodb-ticket-table.png` | `docs/evidence/dynamodb-ticket-scan.json` from `aws dynamodb scan` |
| `05-faq-prompt-template.png` | `src/create_harness.py:27-32`, `src/system_prompt.txt:145-147`, `src/online_shop_faq.md:1-45` |
| `06-covered-question-response.png` | `src/flow-tests.json`, `src/transcripts/route_tests.txt` |
| `07-uncovered-question-response.png` | `src/flow-tests.json`, `src/transcripts/route_tests.txt` |
| `08-other-request-response.png` | `src/flow-tests.json`, `src/transcripts/route_tests.txt` |
| `09-evaluation-results.png` | `src/transcripts/eval_run7_results.jsonl` |

## Required AWS Console screenshots

If the reviewer requires unedited AWS Console screenshots, capture these
manually while the resources exist:

1. DynamoDB console:
   - Open table `bug-report-tool-stack-bug-reports` in `us-east-1`.
   - Open **Explore table items** and photograph the chatbot-created item,
     including `ticketId`, `description`, `stepsToReproduce`, `environment`,
     `status`, and `createdAt`.
2. Bedrock Evaluations console:
   - Open **Evaluations**, then job `support-chatbot-eval-run-7`.
   - Photograph the overall `Builtin.Correctness` score and at least one
     per-record explanation.
3. AgentCore console, if available:
   - Photograph the harness configuration showing model
     `us.amazon.nova-pro-v1:0`, `temperature: 0.0`, disabled memory, and the
     attached gateway target.
   - There is no separate Bedrock Flow, classifier node, condition node, or
     output node: those rubric concepts map to sections of
     `src/system_prompt.txt` shown in images `01`, `02`, and `03`.

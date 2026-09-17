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
| `01-message-routing-flow.png` | `src/bedrock-flow-definition.json`, `src/create_flow.py`, `src/invoke_flow.py` |
| `02-classifier-prompt-configuration.png` | `src/bedrock-flow-definition.json` |
| `03-condition-expressions.png` | `src/bedrock-flow-definition.json` |
| `04-dynamodb-ticket-table.png` | `docs/evidence/dynamodb-ticket-scan.json` from `aws dynamodb scan` |
| `05-faq-prompt-template.png` | `src/bedrock-flow-definition.json` and `src/online_shop_faq.md` |
| `06-covered-question-response.png` | `src/flow-tests.json` and `src/transcripts/flow_route_tests.txt` |
| `07-uncovered-question-response.png` | `src/flow-tests.json` and `src/transcripts/flow_route_tests.txt` |
| `08-other-request-response.png` | `src/flow-tests.json` and `src/transcripts/flow_route_tests.txt` |
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
3. Bedrock console, Flow builder:
   - Open **Bedrock**, choose **Flows**, then open `CustomerSupportRouter`.
   - Photograph the complete node graph, the classifier prompt configuration,
     the condition expressions, the FAQ prompt node with embedded FAQ text,
     and the three terminal output nodes.
   - The local images `01`, `02`, `03`, and `05` render the deployed
     `src/bedrock-flow-definition.json`; the response images render live
     invocations recorded in `src/transcripts/flow_route_tests.txt`.

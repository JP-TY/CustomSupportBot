# Visual evidence package

This directory contains two complementary kinds of evidence:

1. **AWS Console screenshots** (`*.jpeg`), captured from the live `us-east-1`
   project environment for submission.
2. **Deterministic local renderings** (`*.png`), generated from checked-in
   sources, transcripts, and API/CLI-derived JSON. They supplement console
   views that cannot display long configuration text in one viewport.

Run:

```bash
python3 docs/evidence/make_evidence_images.py
```

## Image inventory

| Image | Rendered source |
| --- | --- |
| `BedrockFlowDiagram.jpeg` | Live Bedrock Flow-builder canvas for `CustomerSupportRouter` |
| `ClassifierPromptConfig.jpeg` | Live classifier inference/node configuration |
| `Condition-nodeExpressions.jpeg` | Live condition-node expressions |
| `DynamoDBTable.jpeg` | Live DynamoDB **Explore table items** result |
| `FAQPromptNode.jpeg` | Live FAQ prompt-node configuration |
| `FlowTestFAQCovered.jpeg` | Live covered-question Flow test |
| `FlowTestFAQUncovered.jpeg` | Live uncovered-question Flow test |
| `FlowTestFAQOther.jpeg` | Live other-request Flow test |
| `BedrockEvaluations.jpeg` | Live Bedrock model-evaluation report |
| `01-message-routing-flow.png` | `src/bedrock-flow-definition.json`, `src/create_flow.py`, `src/invoke_flow.py` |
| `02-classifier-prompt-configuration.png` | `src/bedrock-flow-definition.json` |
| `03-condition-expressions.png` | `src/bedrock-flow-definition.json` |
| `04-dynamodb-ticket-table.png` | `docs/evidence/dynamodb-ticket-scan.json` from `aws dynamodb scan` |
| `05-faq-prompt-template.png` | `src/bedrock-flow-definition.json` and `src/online_shop_faq.md` |
| `06-covered-question-response.png` | `src/flow-tests.json` and `src/transcripts/flow_route_tests.txt` |
| `07-uncovered-question-response.png` | `src/flow-tests.json` and `src/transcripts/flow_route_tests.txt` |
| `08-other-request-response.png` | `src/flow-tests.json` and `src/transcripts/flow_route_tests.txt` |
| `09-evaluation-results.png` | `src/transcripts/eval_run7_results.jsonl` |

## AWS Console screenshot checklist

The required console captures are now checked in as the `*.jpeg` files
above. They were captured from the live `us-east-1` environment before
cleanup. The checklist below preserves the capture procedure for
reproducibility:

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

# CustomSupportBot

A customer-support chatbot for a fictional online shop, built on **Amazon
Bedrock AgentCore** for the Udacity ND905 "Prompting LLM Reasoning" (C1)
project. It answers platform questions from the product FAQ, collects bug
reports through a tool, and is evaluated with LLM-as-a-judge.

## How it works

```
 user ──▶ chat.py ──▶ Bedrock AgentCore harness (invoke_harness, streaming)
                          │  model: Amazon Nova Pro (us.amazon.nova-pro-v1:0)
                          │  system prompt: conversation rules + FAQ embedded
                          │
                          ├─ FAQ question ──▶ answered directly from the prompt
                          │
                          └─ bug report ──▶ AgentCore Gateway (MCP)
                                               └─ create_bug_report tool
                                                    └─ AWS Lambda
                                                         └─ DynamoDB ticket table
```

- The **harness** is created/updated by `src/create_harness.py` from
  `src/system_prompt.txt` (with `{{FAQ}}` replaced by the FAQ contents) and
  pinned to Nova Pro. Managed memory is disabled on purpose: retrieved
  memories from other sessions leaked "already provided" bug details.
- The **gateway** (`src/setup_gateway.py`) exposes the bug-report Lambda as an
  MCP tool with an explicit input schema; IAM propagation delays are retried.
- **Evaluation** (`src/generate-eval-dataset.py`) runs the test suite in
  `harness-tests.json` (fresh session per test) and writes a BYOI JSONL
  dataset consumed by Bedrock Evaluations LLM-as-a-judge
  (`output_eval_dataset.jsonl`, job ARN in `eval_job_arn.txt`).

## Repository layout

| Path | Contents |
|------|----------|
| `src/` | All application and tooling code — run everything from here |
| `infra/` | CloudFormation templates (tool stack: Lambda + DynamoDB + IAM; testing stack) |
| `docs/udacity-project-brief.md` | Original project assignment (reference) |
| `ATTRIBUTION.md` | Sources this project was derived from / consulted |
| `LICENSE-UDACITY.md` | License covering the Udacity starter-derived files |

## Setup

Requires an AWS account with Bedrock access (use `us-east-1`), AWS
credentials configured, and Python 3.9+.

```bash
cd src
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## Usage

All commands run from `src/`, in this order:

```bash
# 1. Deploy the bug-report tool stack (Lambda + DynamoDB + IAM roles)
aws cloudformation deploy \
  --template-file ../infra/cloudformation-tool.yaml \
  --stack-name bug-report-tool-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# 2. Create the gateway and register the bug-report tool
python setup_gateway.py

# 3. Create/update the harness from system_prompt.txt
python create_harness.py

# 4. Chat
python chat.py                       # interactive
python chat.py --message "Where do you ship?"   # one-shot

# 5. Regenerate the evaluation dataset after prompt changes
python generate-eval-dataset.py --tests-json harness-tests.json
```

State (gateway/harness ARNs) is cached in `src/agentcore_config.json`; the
scripts are idempotent and reuse existing resources on re-run.

## Cleanup

```bash
python cleanup_agentcore.py          # harness, gateway target, gateway
aws cloudformation delete-stack --stack-name bug-report-tool-stack --region us-east-1
aws cloudformation delete-stack --stack-name bug-report-testing-stack --region us-east-1
```

## Attribution & license

Content derived from other sources (Udacity's starter template) and the
documentation consulted are recorded in
[ATTRIBUTION.md](./ATTRIBUTION.md). Starter-derived files remain subject to
Udacity's license ([LICENSE-UDACITY.md](./LICENSE-UDACITY.md)); all other
code is the author's own work.

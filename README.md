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

## Testing & evaluation

The suite in `src/harness-tests.json` covers all three routes plus edge
cases: covered FAQ questions (return policy, shipping cost, payment
declines), the covered/uncovered boundary ("my package hasn't arrived" is a
FAQ question, not a bug), uncovered questions, two out-of-scope requests, a
one-word ambiguous message, a mixed bug+question message, two prompt
injection attempts (direct and roleplay), and a non-English FAQ question.
Each test runs in a fresh harness session.

```bash
cd src
python generate-eval-dataset.py --tests-json harness-tests.json   # -> output_eval_dataset.jsonl
aws s3 cp output_eval_dataset.jsonl s3://<EvalDatasetBucketName>/output_eval_dataset.jsonl
aws bedrock create-evaluation-job ...   # Builtin.Correctness, judge amazon.nova-pro-v1:0
```

Evaluation runs (LLM-as-a-judge, `Builtin.Correctness`, 14 records):

| Run | Job | Score | Notes |
|-----|-----|-------|-------|
| 1 | `ewmr6a2exbie` | 0.964 (13/14) | Mixed bug+question reply didn't answer the FAQ part |
| 2 | `p5cxed5smz99` | 0.929 (13/14) | "it doesn't work" filed a ticket from a vague description |
| 3 | `hlzpmetxmlou` | 0.893 (12/14) | One transient Nova `ToolUse` stream error; mixed reply again |
| 4 | `yrq7cp9qun11` | 1.000 (14/14) | After description-clarity gate + FAQ-in-same-reply rule |
| 5 | `hdmyub0q6ezl` | 0.893 (12/14) | Temperature 0 didn't stop two flaky behaviors |
| **6 (final)** | `62zdjck1kjmn` | **1.000 (14/14)** | After few-shot examples for mixed-intent and OTHER redirect |

All six jobs ran on the same dataset schema; per-record results for the
final run are archived in `src/transcripts/eval_run6_results.jsonl`.

## Observations

What moved the score, and why:

1. **Managed memory was the biggest hidden failure mode.** With managed
   memory enabled, the harness retrieved details from *previous sessions*
   (e.g. steps/environment captured in an earlier demo) and treated them as
   "already provided", then invented the rest — filing tickets that violated
   the collection gate. Disabling memory (`memory: {"disabled": {}}`) and
   relying on runtime-session state fixed multi-turn behavior.
2. **Rules lose to examples.** Prose gates ("never call the tool before all
   three fields") still leaked eager tool calls on Nova Pro. A short
   scripted example conversation in the prompt eliminated them entirely.
3. **Few-shots also fixed routing variance** on mixed bug+question messages
   and on the phone-line redirect format (the model kept dropping the
   number until an example pinned it).
4. **A vague description is not a complete description.** Adding a
   description-clarity rule to the completion gate stopped tickets filed
   from one-liners like "it doesn't work".
5. **`temperature: 0.0` improved determinism but not enough alone** — the
   last two failure modes only disappeared with the few-shot examples.
6. **Transient model errors happen.** One run lost a record to Nova's
   "invalid sequence as part of ToolUse" stream error; regenerating the
   dataset and re-running the job is the right response.
7. **Bug-route eval tests can write real tickets.** Misrouted bug tests
   created garbage DynamoDB rows during runs 2–5; the final prompt no
   longer does (table contains only intentionally created tickets).

Region note: the lab account's service control policy blocks
CloudFormation/DynamoDB/Lambda outside `us-east-1`, and Nova Pro inference
profiles (`us.`-prefixed) only resolve in US regions — so everything is
pinned to `us-east-1` with the direct model ID `us.amazon.nova-pro-v1:0`.

## Evidence for submission

| Rubric item | Artifact |
|-------------|----------|
| Bug-report route + collection rules | `src/system_prompt.txt` |
| Multi-turn collection + tool call | `src/transcripts/bug_report_multiturn.txt` (`[tool call] bugreports___create_bug_report` on the final turn only) |
| Ticket persisted | DynamoDB table `bug-report-tool-stack-bug-reports` — screenshot needed (console) |
| Routing behavior | `src/transcripts/route_tests.txt` (FAQ covered/uncovered, OTHER) |
| Test suite covers 3 routes | `src/harness-tests.json` |
| JSONL dataset | `src/output_eval_dataset.jsonl` (also in S3) |
| Evaluation job results | Bedrock console → Evaluations → job `62zdjck1kjmn` — screenshot needed; per-record JSON archived in `src/transcripts/eval_run6_results.jsonl` |
| Written observations | This README ("Observations" section) |

## Cleanup

Not yet run — resources are kept live until the submission screenshots are
taken. When done:

```bash
python cleanup_agentcore.py          # harness, gateway target, gateway
aws s3 rm s3://udacity-agentic-engineer-c1-eval-770570504263 --recursive
aws cloudformation delete-stack --stack-name bug-report-testing-stack --region us-east-1
aws cloudformation delete-stack --stack-name bug-report-tool-stack --region us-east-1
```

## Attribution & license

Content derived from other sources (Udacity's starter template) and the
documentation consulted are recorded in
[ATTRIBUTION.md](./ATTRIBUTION.md). Starter-derived files remain subject to
Udacity's license ([LICENSE-UDACITY.md](./LICENSE-UDACITY.md)); all other
code is the author's own work.

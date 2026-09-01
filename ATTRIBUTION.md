# Attribution

This statement covers all content in this repository obtained from other
sources, as well as the documentation consulted while building it.

## 1. Content derived from other sources

### Udacity starter template

The project scaffold and starter files are derived from the Udacity course
repository for **AWS C1 – Prompting LLM Reasoning (ND905)**:

- Source: https://github.com/udacity/aws-c1-prompting-llm-reasoning-nd905-cd14762-project
- License: Udacity Educational Content license, based on
  [CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/) —
  see [LICENSE-UDACITY.md](./LICENSE-UDACITY.md)

Files derived from the starter include:

- `src/create_bug_report.py` — Lambda tool from the starter (since modified)
- `src/online_shop_faq.md` — fictional shop FAQ (unmodified starter content)
- `src/flow-tests-template.json`, `src/harness-tests-template.json` — test
  suite templates
- `infra/cloudformation-tool.yaml`, `infra/cloudformation-testing.yaml` —
  starter templates (since modified and extended)
- `docs/udacity-project-brief.md` — original project instructions
- `LICENSE-UDACITY.md`

Everything else `chat.py`, `harness_client.py`, `create_harness.py`,
`setup_gateway.py`, `cleanup_agentcore.py`, `generate-eval-dataset.py`,
`system_prompt.txt`, `harness-tests.json`, and the AgentCore permissions
added to the CloudFormation tool stack are my own work.

## 2. Documentation and references consulted

Official documentation for the services and APIs this project uses. No code
was copied from these sources. they were used as API references and guides.

- **Amazon Bedrock AgentCore Developer Guide** — Gateway creation with the
  MCP protocol, Lambda tool targets with inline tool schemas, harness
  creation/update, `invoke_harness` streaming events, runtime session IDs,
  and disabling managed memory.
  https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
- **Amazon Bedrock User Guide — Bedrock Evaluations** — LLM-as-a-judge
  evaluation jobs and the bring-your-own-inference JSONL dataset format
  (`prompt`, `referenceResponse`, `modelResponses`,
  `precomputedInferenceSourceIdentifier`).
  https://docs.aws.amazon.com/bedrock/latest/userguide/evaluation.html
- **Amazon Bedrock User Guide — Flows, Agents** — course-referenced
  orchestration and tool-use background.
  https://docs.aws.amazon.com/bedrock/latest/userguide/flows.html ,
  https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- **Amazon Nova User Guide** — model ID `us.amazon.nova-pro-v1:0` and the
  `<thinking>` reasoning blocks that `harness_client.py` strips from output.
  https://docs.aws.amazon.com/nova/latest/userguide/
- **boto3 documentation** — `bedrock-agentcore`, `bedrock-agentcore-control`,
  and `cloudformation` client APIs used throughout `src/`.
  https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **AWS CloudFormation User Guide** — DynamoDB table, Lambda (inline ZipFile),
  and IAM role/policy template syntax in `infra/`.
  https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/
- **Model Context Protocol** — the protocol type used by the AgentCore
  Gateway. https://modelcontextprotocol.io
- **Udacity ND905 course materials** — lesson concepts and the project
  instructions in `docs/udacity-project-brief.md`.

## 3. Other sources

No other websites, books, forums, blogs, or GitHub repositories contributed
content to this repository. If any additional source is used in the future,
it will be recorded here.

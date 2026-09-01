# CustomSupportBot

A customer-support chatbot built for the Udacity ND905 "Prompting LLM
Reasoning" (C1) project, using Amazon Bedrock AgentCore (Runtime, Gateway,
and Evaluations).

## Structure

- [`aws-c1-prompting-llm-reasoning-nd905-cd14762-project/`](./aws-c1-prompting-llm-reasoning-nd905-cd14762-project)
  — the project workspace, originally scaffolded from Udacity's starter repo.
  The working code lives in `project/starter/`.

## Setup

```bash
cd aws-c1-prompting-llm-reasoning-nd905-cd14762-project/project/starter
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Credentials are loaded from a local `.env` file (git-ignored).

## Attribution

Content derived from other sources (including the Udacity starter template)
is attributed in [ATTRIBUTION.md](./ATTRIBUTION.md).

## License

Original starter content remains subject to Udacity's license (see
`aws-c1-prompting-llm-reasoning-nd905-cd14762-project/LICENSE.md`). All
other project code is the author's work.

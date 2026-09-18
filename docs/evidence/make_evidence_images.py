#!/usr/bin/env python3
"""Generate deterministic local evidence renderings for project review.

The PNG files in this directory are not photographs of the AWS Management
Console. They are locally generated, source-backed renderings of repository
text, checked-in transcripts, a DynamoDB Scan snapshot, and Bedrock
evaluation-result JSON. Each image names the source file or command used.

Only the Python standard library is required; ``rsvg-convert`` renders the
intermediate SVG files as PNG images.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
EVIDENCE = ROOT / "docs" / "evidence"
WIDTH = 1600
MARGIN = 72
BACKGROUND = "#ffffff"
PANEL = "#f7f8fb"
INK = "#111827"
MUTED = "#4b5563"
ACCENT = "#1d4ed8"
BORDER = "#d1d5db"
MONO = "DejaVu Sans Mono, Liberation Mono, monospace"
SANS = "DejaVu Sans, Liberation Sans, sans-serif"


class Card:
    """A simple SVG document with a title, body area, and provenance footer."""

    def __init__(self, title: str, subtitle: str, provenance: str, width: int = WIDTH):
        self.title = title
        self.subtitle = subtitle
        self.provenance = provenance
        self.width = width
        self.parts: list[str] = []
        self.y = 0

    def start(self, body_height: int) -> int:
        height = 168 + body_height + 76
        self.parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" '
            f'height="{height}" viewBox="0 0 {self.width} {height}">'
            f'<rect x="0" y="0" width="{self.width}" height="{height}" fill="{BACKGROUND}"/>'
            f'<rect x="24" y="24" width="{self.width - 48}" height="{height - 48}" '
            f'rx="18" fill="{PANEL}" stroke="{BORDER}" stroke-width="2"/>'
            f'<text x="{MARGIN}" y="94" font-family="{SANS}" font-size="42" '
            f'font-weight="700" fill="{INK}">{escape(self.title)}</text>'
            f'<text x="{MARGIN}" y="132" font-family="{SANS}" font-size="23" '
            f'fill="{MUTED}">{escape(self.subtitle)}</text>'
            f'<line x1="{MARGIN}" y1="150" x2="{self.width - MARGIN}" y2="150" '
            f'stroke="{BORDER}" stroke-width="2"/>'
        )
        self.y = 196
        self.footer_y = height - 38
        return height

    def finish(self, filename: str) -> Path:
        self.parts.append(
            f'<text x="{MARGIN}" y="{self.footer_y}" font-family="{SANS}" '
            f'font-size="20" fill="{MUTED}">{escape(self.provenance)}</text>'
            "</svg>"
        )
        svg_text = "".join(self.parts)
        if shutil.which("rsvg-convert") is None:
            raise RuntimeError("rsvg-convert is required to render evidence PNG files")
        with tempfile.TemporaryDirectory(prefix="customsuppbot-evidence-") as tmp:
            svg_path = Path(tmp) / (Path(filename).stem + ".svg")
            svg_path.write_text(svg_text, encoding="utf-8")
            png_path = EVIDENCE / filename
            subprocess.run(
                ["rsvg-convert", "-w", str(self.width), str(svg_path), "-o", str(png_path)],
                check=True,
            )
        return png_path


def wrapped_lines(text: str, width: int, font_size: int, mono: bool = True) -> list[str]:
    char_width = font_size * (0.60 if mono else 0.52)
    usable = WIDTH - (2 * MARGIN) - (120 if mono else 0)
    wrapped: list[str] = []
    for paragraph in text.splitlines() or [""]:
        if not paragraph.strip():
            wrapped.append("")
            continue
        wrapped.extend(
            textwrap.wrap(
                paragraph,
                width=max(20, int(usable / char_width) if width <= 0 else width),
                break_long_words=True,
                break_on_hyphens=False,
            )
        )
    return wrapped


def code_card(filename: str, title: str, subtitle: str, text: str, provenance: str) -> None:
    lines = wrapped_lines(text, 0, 22, mono=True)
    line_height = 33
    body_height = max(120, len(lines) * line_height + 36)
    card = Card(title, subtitle, provenance)
    card.start(body_height)
    y = card.y
    for number, line in enumerate(lines, start=1):
        card.parts.append(
            f'<text x="{MARGIN}" y="{y}" font-family="{MONO}" font-size="20" '
            f'fill="#6b7280">{number:>3}</text>'
            f'<text x="{MARGIN + 92}" y="{y}" font-family="{MONO}" '
            f'font-size="22" fill="{INK}">{escape(line) if line else " "}</text>'
        )
        y += line_height
    card.finish(filename)


def user_assistant_card(
    filename: str, title: str, user: str, assistant: str, provenance: str
) -> None:
    user_lines = wrapped_lines(user, 0, 25, mono=False)
    assistant_lines = wrapped_lines(assistant, 0, 25, mono=False)
    body_height = (
        78 + len(user_lines) * 37 + 72 + len(assistant_lines) * 37 + 40
    )
    card = Card(title, "Actual prompt and chatbot response", provenance)
    card.start(body_height)
    y = card.y
    card.parts.append(
        f'<rect x="{MARGIN}" y="{y - 38}" width="{WIDTH - 2 * MARGIN}" '
        f'height="{len(user_lines) * 37 + 78}" rx="14" fill="#dbeafe" '
        f'stroke="#93c5fd" stroke-width="2"/>'
        f'<text x="{MARGIN + 24}" y="{y}" font-family="{SANS}" font-size="23" '
        f'font-weight="700" fill="{INK}">Customer</text>'
    )
    y += 42
    for line in user_lines:
        card.parts.append(
            f'<text x="{MARGIN + 24}" y="{y}" font-family="{SANS}" '
            f'font-size="25" fill="{INK}">{escape(line) if line else " "}</text>'
        )
        y += 37
    y += 38
    card.parts.append(
        f'<rect x="{MARGIN}" y="{y - 38}" width="{WIDTH - 2 * MARGIN}" '
        f'height="{len(assistant_lines) * 37 + 78}" rx="14" fill="#ffffff" '
        f'stroke="{BORDER}" stroke-width="2"/>'
        f'<text x="{MARGIN + 24}" y="{y}" font-family="{SANS}" font-size="23" '
        f'font-weight="700" fill="{INK}">Support chatbot</text>'
    )
    y += 42
    for line in assistant_lines:
        card.parts.append(
            f'<text x="{MARGIN + 24}" y="{y}" font-family="{SANS}" '
            f'font-size="25" fill="{INK}">{escape(line) if line else " "}</text>'
        )
        y += 37
    card.finish(filename)


def read_lines(path: Path, start: int, end: int) -> str:
    return "\n".join(path.read_text(encoding="utf-8").splitlines()[start - 1 : end])


def excerpt_between(path: Path, start_marker: str, end_marker: str) -> tuple[str, int, int]:
    """Return text and 1-based line numbers between two exact line markers."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(index for index, line in enumerate(lines) if line == start_marker)
    end = next(
        index
        for index, line in enumerate(lines[start:], start=start)
        if line == end_marker
    )
    return "\n".join(lines[start : end + 1]), start + 1, end + 1


def split_transcript(path: Path) -> list[str]:
    chunks = re.split(r"^--- \d+: .+ ---$", path.read_text(encoding="utf-8"), flags=re.M)
    return [chunk.strip() for chunk in chunks[1:]]


def routing_diagram() -> None:
    width, height = 1600, 1320
    card = Card(
        "Message-routing flow",
        "AgentCore harness behavior: one prompt-driven classifier and three terminal response paths",
        "Source: src/system_prompt.txt; implementation: src/create_harness.py and src/chat.py",
        width=width,
    )
    card.start(height - 244)
    svg = "".join(card.parts)

    def box(x0: int, y0: int, x1: int, y1: int, title: str, body: str, fill: str) -> str:
        wrapped = textwrap.wrap(body, width=34)
        text = "".join(
            f'<text x="{(x0 + x1) // 2}" y="{y0 + 58 + i * 30}" text-anchor="middle" '
            f'font-family="{SANS}" font-size="22" fill="{INK}">{escape(line)}</text>'
            for i, line in enumerate(wrapped)
        )
        return (
            f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="16" '
            f'fill="{fill}" stroke="{ACCENT if "Terminal" in title else BORDER}" '
            f'stroke-width="3"/>'
            f'<text x="{(x0 + x1) // 2}" y="{y0 + 34}" text-anchor="middle" '
            f'font-family="{SANS}" font-size="22" font-weight="700" '
            f'fill="{ACCENT if "Terminal" in title else INK}">{escape(title)}</text>{text}'
        )

    def arrow(x1: int, y1: int, x2: int, y2: int, label: str = "") -> str:
        text = (
            f'<text x="{(x1 + x2) // 2}" y="{(y1 + y2) // 2 - 10}" text-anchor="middle" '
            f'font-family="{MONO}" font-size="19" font-weight="700" fill="{MUTED}">'
            f'{escape(label)}</text>'
            if label
            else ""
        )
        return (
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{MUTED}" '
            f'stroke-width="3" marker-end="url(#arrow)"/>{text}'
        )

    svg += (
        '<defs><marker id="arrow" markerWidth="12" markerHeight="12" refX="8" '
        'refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#4b5563"/></marker></defs>'
    )
    svg += box(550, 200, 1050, 290, "Customer message", "Live-chat input in one harness session", "#ffffff")
    svg += box(
        390, 330, 1210, 450,
        "support_chatbot harness",
        "Nova Pro, temperature 0.0, session state; AgentCore Gateway attached; managed memory disabled",
        "#eef2ff",
    )
    svg += box(
        390, 490, 1210, 630,
        "Prompt classifier: system_prompt.txt",
        "Classify every message as exactly one of BUG_REPORT, PLATFORM_QUESTION, or OTHER",
        "#fff7ed",
    )
    svg += box(80, 700, 500, 820, "BUG_REPORT path", "Collect description, reproduction steps, and environment", "#ffffff")
    svg += box(80, 850, 500, 930, "Gateway tool", "bugreports___create_bug_report through AgentCore Gateway", "#ffffff")
    svg += box(80, 960, 500, 1040, "Lambda and DynamoDB", "Validate fields, assign ticketId, PutItem with status OPEN", "#ffffff")
    svg += box(590, 700, 1010, 820, "PLATFORM_QUESTION path", "Answer only from the embedded FAQ; hand off when uncovered", "#ffffff")
    svg += box(590, 960, 1010, 1070, "Terminal response: FAQ answer", "Separate output path", "#ecfdf5")
    svg += box(1100, 700, 1528, 820, "OTHER path", "Politely decline and redirect to 1-800-555-0199", "#ffffff")
    svg += box(1100, 960, 1528, 1070, "Terminal response: human handoff", "Separate output path", "#ecfdf5")
    svg += box(80, 1100, 500, 1210, "Terminal response: ticket ID", "Separate output path", "#ecfdf5")
    svg += arrow(800, 290, 800, 330, "")
    svg += arrow(800, 450, 800, 490, "")
    svg += arrow(560, 560, 290, 700, "BUG_REPORT")
    svg += arrow(800, 630, 800, 700, "PLATFORM_QUESTION")
    svg += arrow(1040, 560, 1310, 700, "OTHER")
    svg += arrow(290, 820, 290, 850, "")
    svg += arrow(290, 930, 290, 960, "")
    svg += arrow(290, 1040, 290, 1100, "")
    svg += arrow(800, 820, 800, 960, "")
    svg += arrow(1314, 820, 1314, 960, "")
    card.parts = [svg]
    card.footer_y = height - 38
    card.finish("01-message-routing-flow.png")


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    prompt = SRC / "system_prompt.txt"
    config = json.loads((SRC / "agentcore_config.json").read_text(encoding="utf-8"))
    harness = SRC / "create_harness.py"

    routing_diagram()

    classifier_text = (
        f"harness_name: {config['harness_name']}\n"
        f"model_id: {config['model_id']}\n"
        "temperature: 0.0\n"
        "memory: disabled (runtime-session state only)\n\n"
        + read_lines(prompt, 5, 46)
    )
    code_card(
        "02-classifier-prompt-configuration.png",
        "Classifier prompt configuration",
        "Actual harness model settings and routing excerpt",
        classifier_text,
        "Sources: src/agentcore_config.json and src/system_prompt.txt:5-46",
    )

    code_card(
        "03-condition-expressions.png",
        "Routing condition expressions",
        "Deterministic classifier predicates transcribed from the prompt",
        "\n".join(
            [
                "BUG_REPORT :=",
                "  describes_broken_or_misbehaving(message)",
                "",
                "PLATFORM_QUESTION :=",
                "  asks_question(message) AND faq_contains_answer(message, FAQ)",
                "",
                "OTHER :=",
                "  NOT (BUG_REPORT OR PLATFORM_QUESTION)",
                "",
                "PRECEDENCE:",
                "  1. broken behavior -> BUG_REPORT",
                "  2. covered question -> PLATFORM_QUESTION",
                "  3. uncovered question -> OTHER",
                "  4. all remaining messages -> OTHER",
                "",
                "TERMINALS:",
                "  BUG_REPORT -> bug-report output",
                "  PLATFORM_QUESTION -> FAQ output",
                "  OTHER -> human-handoff output",
            ]
        ),
        "Source: src/system_prompt.txt:23-46",
    )

    scan = json.loads((EVIDENCE / "dynamodb-ticket-scan.json").read_text(encoding="utf-8"))
    item = scan["Items"][0]
    ticket_lines = [
        f"Table: bug-report-tool-stack-bug-reports",
        f"Count: {scan['Count']} of {scan['ScannedCount']} scanned",
        "",
        f"ticketId: {item['ticketId']['S']}",
        f"status: {item['status']['S']}",
        f"createdAt: {item['createdAt']['S']}",
        f"description: {item['description']['S']}",
        f"stepsToReproduce: {item['stepsToReproduce']['S']}",
        f"environment: {item['environment']['S']}",
    ]
    code_card(
        "04-dynamodb-ticket-table.png",
        "DynamoDB ticket-table evidence",
        "Local rendering of the live DynamoDB Scan JSON snapshot",
        "\n".join(ticket_lines),
        "Source: docs/evidence/dynamodb-ticket-scan.json from aws dynamodb scan",
    )

    harness_excerpt, harness_start, harness_end = excerpt_between(
        harness, "def build_system_prompt():", '    return prompt.replace("{{FAQ}}", faq)'
    )
    prompt_excerpt, prompt_start, prompt_end = excerpt_between(
        prompt, "# FAQ DOCUMENT", "{{FAQ}}"
    )
    faq_excerpt_lines = (SRC / "online_shop_faq.md").read_text(encoding="utf-8").splitlines()[:45]
    template_text = "\n".join(
        [
            "# src/create_harness.py",
            harness_excerpt,
            "",
            "# src/system_prompt.txt",
            prompt_excerpt,
            "",
            "# src/online_shop_faq.md (embedded excerpt)",
            *faq_excerpt_lines,
        ]
    )
    code_card(
        "05-faq-prompt-template.png",
        "FAQ prompt template and embedding",
        "Placeholder substitution plus the embedded FAQ source excerpt",
        template_text,
        f"Sources: src/create_harness.py:{harness_start}-{harness_end}; "
        f"src/system_prompt.txt:{prompt_start}-{prompt_end}; src/online_shop_faq.md:1-45",
    )

    tests = json.loads((SRC / "flow-tests.json").read_text(encoding="utf-8"))["tests"]
    responses = split_transcript(SRC / "transcripts" / "route_tests.txt")
    pairs = [
        ("06-covered-question-response.png", "Covered platform-question response", 2, 0),
        ("07-uncovered-question-response.png", "Uncovered-question handoff response", 6, 1),
        ("08-other-request-response.png", "Other-request handoff response", 7, 2),
    ]
    for filename, title, test_index, response_index in pairs:
        user_assistant_card(
            filename,
            title,
            tests[test_index]["prompt"],
            responses[response_index],
            "Sources: src/flow-tests.json and src/transcripts/route_tests.txt",
        )

    results = [
        json.loads(line)
        for line in (SRC / "transcripts" / "eval_run7_results.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
    ]
    scores = [row["automatedEvaluationResult"]["scores"][0]["result"] for row in results]
    summary = (
        f"evaluation job: support-chatbot-eval-run-7\n"
        f"metric: Builtin.Correctness\n"
        f"judge: amazon.nova-pro-v1:0\n"
        f"records: {len(results)}\n"
        f"average correctness: {sum(scores) / len(scores):.3f}\n"
        f"perfect records: {int(sum(scores))} of {len(scores)}\n\n"
        + "\n".join(
            f"{index + 1:02d}  {score:.1f}  "
            f"{row['inputRecord']['prompt'][:100]}"
            for index, (row, score) in enumerate(zip(results, scores))
        )
    )
    code_card(
        "09-evaluation-results.png",
        "Bedrock evaluation results",
        "Local rendering of the archived Bedrock Evaluations result JSON",
        summary,
        "Source: src/transcripts/eval_run7_results.jsonl",
    )


if __name__ == "__main__":
    main()

"""Tier 3 — behavioral LLM evals (opt-in: `pytest -m eval`).

Each case prompts the model with a skill injected as system context (mirroring how
Codex surfaces a relevant skill) and asserts the generated SQL takes the
MariaDB-preferred form the skill teaches. Assertions are regex/substring — stable
and cheap — rather than an LLM judge.

Because this plugin targets Codex, the eval exercises an OpenAI model (the model
Codex itself runs on), via the official `openai` SDK.

Deselected by default (see pyproject.toml `addopts`); needs OPENAI_API_KEY.

Model/SDK notes:
  * Default model is `gpt-5.1-codex`; override with EVAL_MODEL to whatever model
    your OpenAI key can reach.
  * No `temperature` is sent: several current OpenAI reasoning/codex models only
    accept the default. The assertions are tolerant of minor sampling variation.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest
import yaml

from lib import skills

pytestmark = pytest.mark.eval

CASES_DIR = Path(__file__).resolve().parent / "cases"
MODEL = os.environ.get("EVAL_MODEL", "gpt-5.1-codex")

SYSTEM_PREAMBLE = (
    "You are a MariaDB expert assistant. A relevant MariaDB skill is provided "
    "below as authoritative context. Follow it. When asked for SQL, reply with "
    "only the SQL statement(s) in a ```sql code block and no prose.\n\n"
    "--- SKILL ---\n"
)


def _load_eval_cases():
    items, ids = [], []
    for path in sorted(CASES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        skill = data.get("skill", path.stem)
        for case in data.get("cases") or []:
            items.append((skill, case))
            ids.append(f"{skill}::{case['name']}")
    return items, ids


_CASES, _IDS = _load_eval_cases()


def _skill_text(skill_name: str) -> str:
    for s in skills.load_skills():
        if s.name == skill_name:
            return s.raw_text()
    raise AssertionError(f"eval references unknown skill: {skill_name}")


def _generate(system: str, prompt: str) -> str:
    try:
        import openai
    except ImportError:
        pytest.skip("openai SDK not installed — skipping behavioral evals")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set — skipping behavioral evals")

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=MODEL,
        max_completion_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


@pytest.mark.skipif(not _CASES, reason="no eval cases defined yet")
@pytest.mark.parametrize(("skill", "case"), _CASES, ids=_IDS)
def test_behavioral_case(skill, case):
    system = SYSTEM_PREAMBLE + _skill_text(skill)
    output = _generate(system, case["prompt"])

    for pattern in case.get("expect_regex", []):
        assert re.search(pattern, output, re.IGNORECASE), (
            f"expected /{pattern}/ in model output, got:\n{output}"
        )
    for forbidden in case.get("expect_absent", []):
        assert forbidden.lower() not in output.lower(), (
            f"did not expect {forbidden!r} in model output, got:\n{output}"
        )

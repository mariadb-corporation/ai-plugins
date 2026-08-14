# Copyright (c) 2026, MariaDB plc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License, version 2.0,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See
# the GNU General Public License, version 2.0, for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

"""Tier 3 — behavioral LLM evals (opt-in: `pytest -m eval`).

Each case prompts Claude with a skill injected as system context (mirroring how
Claude Code surfaces a relevant skill) and asserts the generated SQL takes the
MariaDB-preferred form the skill teaches. Assertions are regex/substring — stable
and cheap — rather than an LLM judge.

Deselected by default (see pyproject.toml `addopts`); needs ANTHROPIC_API_KEY.

Model/SDK notes (per the claude-api skill):
  * Default model is `claude-opus-4-8`; override with EVAL_MODEL.
  * `temperature` is REJECTED (400) on Opus 4.8 — do not send it. The documented
    determinism lever is `output_config={"effort": "low"}`, used below.
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
MODEL = os.environ.get("EVAL_MODEL", "claude-opus-4-8")

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
        import anthropic
    except ImportError:
        pytest.skip("anthropic SDK not installed — skipping behavioral evals")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set — skipping behavioral evals")

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        output_config={"effort": "low"},  # determinism lever; temperature is rejected on Opus 4.8
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in response.content if b.type == "text")


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

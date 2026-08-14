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

"""Tier 4 — end-to-end via the real pi CLI (opt-in: `pytest -m e2e`).

The pi counterpart of `claude/dev-plugin-tests/test_e2e_claude.py`, scoped to what
pi actually offers. The single `pi -p` run happens in the module-scoped `workflow`
fixture; each side effect is its own `test_stepN_*`:

  1. the vendored skills reached the model — it can name several of them, which
     only the installed package can supply,
  2. `notes-app.sql` was written, and
  3. it opens with the *Start Block* the `mariadb-schema-create-script` skill
     mandates → a skill was not merely visible but followed.

Two deliberate differences from the Claude and Codex tiers:

* **No MCP tool-call assertions.** pi has no built-in MCP; the mariadb server is
  reached through the community `pi-mcp-adapter`, installed separately from this
  package (see `pi/README.md`). What this repo *does* control is the registration,
  and `test_setup_script_registers_the_mcp_server` covers it without a model.
* **No fixed model.** pi runs whatever provider it is configured for, which may be
  a local one; the run records which model answered, so a failure can be read in
  that light rather than blamed on the plugin.

Deselected by default (see pyproject.toml `addopts`). It self-skips unless `pi` is
present and can actually reach a model — checked with a trivial round trip, since
`pi auth check` reports `not_ready` even when runs work.

Knobs (all optional): PI_BIN, E2E_TIMEOUT.
"""

from __future__ import annotations

import json
import os
import re

import pytest

from lib import pi_cli, skills

pytestmark = pytest.mark.e2e

SCHEMA_SQL = "notes-app.sql"
TIMEOUT = int(os.environ.get("E2E_TIMEOUT", "900"))

# The two lines that uniquely identify the skill's mandated Start Block.
START_BLOCK_MARKERS = ("@OLD_UNIQUE_CHECKS", "SET NAMES utf8mb4")



def _build_prompt() -> str:
    return (
        "Work in the current directory and do both of the following.\n\n"
        "1. Name the MariaDB skills you are using for this task.\n"
        f"2. Create a MariaDB database schema named notes-app for a note-taking "
        f"app and write it to a file named {SCHEMA_SQL} in the current directory. "
        "Follow the MariaDB schema create script conventions from your skills "
        "exactly, including the mandated start block."
    )


@pytest.fixture(scope="module")
def workflow(tmp_path_factory):
    reason = pi_cli.missing_prerequisite()
    if reason:
        pytest.skip(reason)
    reason = pi_cli.provider_ready()
    if reason:
        pytest.skip(reason)

    project = tmp_path_factory.mktemp("pi_e2e") / "project"
    project.mkdir()

    installed = pi_cli.install_package(project)
    assert installed.returncode == 0, (
        f"pi install -l failed:\n{installed.stdout}\n{installed.stderr}"
    )

    run = pi_cli.run_pi(_build_prompt(), project=project, timeout=TIMEOUT)
    print(f"pi e2e ran against model: {run.model()}")
    yield {"project": project, "run": run}


def test_step0_run_finished(workflow):
    """The pi run completed within the timeout (gate for the later steps)."""
    run = workflow["run"]
    assert not run.timed_out, f"pi did not finish within {TIMEOUT}s.{run.diagnostics}"
    assert run.returncode == 0, f"pi exited {run.returncode}.{run.diagnostics}"


def test_step1_vendored_skills_reached_the_model(workflow):
    """The model referred to skills that only this package supplies.

    Checked against the *actual* vendored names rather than a hand-picked few, and
    satisfied by a single hit: with 75 names, most of which no model would invent
    (`mariadb-schema-create-script`, `mariadb-rest-service-create`, …), one is
    enough to show the package's skills were in context. Asking a model to
    reproduce a fixed list is a test of its obedience, not of the wiring — a weak
    local provider named one skill and did the work correctly, which is a pass,
    not a failure. The substantive evidence is test_step3.
    """
    run = workflow["run"]
    text = run.assistant_text().lower()
    named = sorted(name for name in skills.skill_names() if name.lower() in text)
    assert named, (
        "the model named none of this package's 75 vendored skills, so pi did not put "
        f"them in context (model: {run.model()}).{run.diagnostics}"
    )
    print(f"skills the model referred to: {named}")


def test_step2_schema_script_written(workflow):
    """The run produced the requested SQL file in the project dir."""
    run = workflow["run"]
    sql_path = workflow["project"] / SCHEMA_SQL
    assert sql_path.is_file(), (
        f"{SCHEMA_SQL} was not created (model: {run.model()}).{run.diagnostics}"
    )


def test_step3_start_block_from_the_skill(workflow):
    """The script opens with the Start Block `mariadb-schema-create-script` mandates."""
    run = workflow["run"]
    sql_path = workflow["project"] / SCHEMA_SQL
    if not sql_path.is_file():
        pytest.skip("no schema script — see test_step2")
    sql = sql_path.read_text(encoding="utf-8")
    for marker in START_BLOCK_MARKERS:
        assert marker in sql, (
            f"{SCHEMA_SQL} is missing the Start Block marker {marker!r} required by "
            f"mariadb-schema-create-script (model: {run.model()}).{run.diagnostics}"
        )
    first_ddl = re.search(r"(?im)^\s*CREATE\s+(OR\s+REPLACE\s+)?(SCHEMA|DATABASE|TABLE)", sql)
    first_marker = sql.find("@OLD_UNIQUE_CHECKS")
    assert first_ddl is None or first_marker < first_ddl.start(), (
        f"Start Block must precede the first CREATE statement.{run.diagnostics}"
    )


# --------------------------------------------------------------------------- #
# MCP registration, without a model.
#
# pi cannot start an MCP server by itself, so the plugin's contribution is the
# entry it writes into pi-mcp-adapter's config. That is checkable directly, and
# unlike the model steps above it is deterministic.
# --------------------------------------------------------------------------- #
def test_setup_script_registers_the_mcp_server(tmp_path):
    reason = pi_cli.missing_prerequisite()
    if reason:
        pytest.skip(reason)

    config = tmp_path / "mcp.json"
    result = pi_cli.run_setup_script(config)
    assert result.returncode == 0, (
        f"setup-pi-mcp.sh failed:\n{result.stdout}\n{result.stderr}"
    )
    assert config.is_file(), f"the script wrote no config at {config}"

    entry = (json.loads(config.read_text(encoding="utf-8")).get("mcpServers") or {}).get(
        pi_cli.SERVER_NAME
    )
    assert entry, f"no {pi_cli.SERVER_NAME!r} server in {config}"
    assert entry.get("command") == str(pi_cli.LAUNCHER), (
        f"registered command {entry.get('command')!r} is not this plugin's launcher "
        f"({pi_cli.LAUNCHER})"
    )
    # `lazy` is what keeps mariadb-shell from being spawned until a MariaDB tool
    # is first used; dropping it would start a shell for every pi session.
    assert entry.get("lifecycle") == "lazy", (
        f"expected lifecycle 'lazy', got {entry.get('lifecycle')!r}"
    )


def test_setup_script_is_idempotent_and_preserves_other_servers(tmp_path):
    """Re-running must update our entry in place and leave other servers alone."""
    reason = pi_cli.missing_prerequisite()
    if reason:
        pytest.skip(reason)

    config = tmp_path / "mcp.json"
    config.write_text(
        json.dumps({"mcpServers": {"other": {"command": "/bin/true"}}, "someSetting": 1}),
        encoding="utf-8",
    )
    assert pi_cli.run_setup_script(config).returncode == 0
    assert pi_cli.run_setup_script(config).returncode == 0  # twice: must not duplicate

    data = json.loads(config.read_text(encoding="utf-8"))
    assert pi_cli.SERVER_NAME in data["mcpServers"], "our server went missing"
    assert data["mcpServers"].get("other", {}).get("command") == "/bin/true", (
        "the script clobbered an unrelated MCP server"
    )
    assert data.get("someSetting") == 1, "the script dropped an unrelated adapter setting"

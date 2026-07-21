"""Tier 4 — end-to-end via the real Claude Code CLI (opt-in: `pytest -m e2e`).

Unlike the other tiers (which check the skills statically, run their SQL, or
prompt the API directly), this one drives the actual `claude` binary with the
**dev-plugin loaded** and its **mariadb-shell MCP server wired in**, then proves
the whole stack worked by its side effects:

  1. `notes-app.sql` is written and opens with the *Start Block* mandated by the
     `mariadb-schema-create-script` skill  → the skill was loaded and followed.
  2. A MariaDB sandbox is reachable on port 33310                → the MCP
     `sandbox`/create tool ran.
  3. The `notes-app` schema exists inside that sandbox           → the MCP SQL
     execution ran the generated script.

Teardown drops the sandbox with a real `sandbox.delete` MCP call (discovered
from the server's own tools/list, so we don't hardcode the arg schema).

Deselected by default (see pyproject.toml `addopts`). It self-skips unless the
whole toolchain is present:
  * the `claude` CLI on PATH (override: CLAUDE_BIN), already authenticated —
    either via a logged-in session or ANTHROPIC_API_KEY,
  * a `mariadb-shell` the launcher can resolve — on PATH at a version >= the
    plugin's pin, or via MARIADB_SHELL_BIN,
  * PyMySQL, to inspect the sandbox.

Knobs (all optional): CLAUDE_BIN, E2E_MODEL, E2E_TIMEOUT, E2E_SANDBOX_HOST,
E2E_SANDBOX_PORT, E2E_SANDBOX_USER, E2E_SANDBOX_PASSWORD.
"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

from lib.mcp_stdio import MCPStdioClient

pytestmark = pytest.mark.e2e

PLUGIN_DIR = (Path(__file__).resolve().parent.parent / "dev-plugin").resolve()
LAUNCHER = PLUGIN_DIR / "scripts" / "mariadb-mcp-launcher.sh"

def _build_prompt(port: int, password: str) -> str:
    # The root password is pinned so the test can both connect to verify the
    # schema and stop the sandbox for teardown (sandbox.deploy sets a password;
    # a blank one is rejected on connect).
    return (
        "Create a MariaDB database schema named notes-app for a note-taking app "
        "and store it in a notes-app.sql file. Then spin up a sandbox instance on "
        f"port {port} with root password '{password}', connect to it and run the "
        "script via the MCP server."
    )


def _pick_port() -> int:
    """The sandbox port: an explicit E2E_SANDBOX_PORT, else a free ephemeral one."""
    override = os.environ.get("E2E_SANDBOX_PORT")
    if override:
        return int(override)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# The two lines that uniquely identify the skill's mandated Start Block.
START_BLOCK_MARKERS = (
    "@OLD_UNIQUE_CHECKS",
    "SET NAMES utf8mb4",
)

SANDBOX_HOST = os.environ.get("E2E_SANDBOX_HOST", "127.0.0.1")
SANDBOX_USER = os.environ.get("E2E_SANDBOX_USER", "root")
SANDBOX_PASSWORD = os.environ.get("E2E_SANDBOX_PASSWORD", "test")
MODEL = os.environ.get("E2E_MODEL", "claude-opus-4-8")
TIMEOUT = int(os.environ.get("E2E_TIMEOUT", "600"))

# The sandbox schema may be created as `notes-app` or normalized to `notes_app`.
SCHEMA_CANDIDATES = ("notes-app", "notes_app")


# --------------------------------------------------------------------------- #
# Prerequisite gates — skip (never fail) when the toolchain is absent.
# --------------------------------------------------------------------------- #
def _claude_bin() -> str:
    return os.environ.get("CLAUDE_BIN") or shutil.which("claude") or ""


def _launcher_env() -> dict:
    """Env for the MCP launcher: inherit, and let it resolve mariadb-shell."""
    return dict(os.environ)


def _mariadb_shell_resolvable() -> bool:
    if os.environ.get("MARIADB_SHELL_BIN"):
        return True
    return shutil.which("mariadb-shell") is not None


def _require_toolchain():
    if not _claude_bin():
        pytest.skip("claude CLI not found (set CLAUDE_BIN or add it to PATH)")
    # No ANTHROPIC_API_KEY gate: a ready `claude` may authenticate via a
    # logged-in session instead. If it can't reach the model, the run fails
    # (surfacing claude's own auth error) rather than silently skipping.
    if not _mariadb_shell_resolvable():
        pytest.skip("mariadb-shell not resolvable (set MARIADB_SHELL_BIN or put it on PATH)")
    if not LAUNCHER.is_file():
        pytest.skip(f"launcher missing at {LAUNCHER}")
    try:
        import pymysql  # noqa: F401
    except ImportError:
        pytest.skip("PyMySQL not installed — cannot inspect the sandbox")


# --------------------------------------------------------------------------- #
# Wiring: an isolated project dir with the plugin's skills + MCP config.
# --------------------------------------------------------------------------- #
def _write_mcp_config(dest: Path) -> Path:
    """Materialize the plugin's .mcp.json with ${CLAUDE_PLUGIN_ROOT} resolved."""
    raw = (PLUGIN_DIR / ".mcp.json").read_text(encoding="utf-8")
    resolved = raw.replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN_DIR))
    out = dest / "mcp.json"
    out.write_text(resolved, encoding="utf-8")
    return out


def _expose_skills(project: Path) -> None:
    """Make the plugin's skills discoverable as project skills."""
    skills_link = project / ".claude" / "skills"
    skills_link.parent.mkdir(parents=True, exist_ok=True)
    skills_link.symlink_to(PLUGIN_DIR / "skills", target_is_directory=True)


def _run_claude(project: Path, mcp_config: Path, prompt: str) -> subprocess.CompletedProcess:
    cmd = [
        _claude_bin(),
        "-p", prompt,
        "--model", MODEL,
        "--mcp-config", str(mcp_config),
        "--strict-mcp-config",              # ignore any user/global MCP servers
        "--dangerously-skip-permissions",   # non-interactive; sandboxed test box
    ]
    return subprocess.run(
        cmd,
        cwd=project,
        env=_launcher_env(),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


# --------------------------------------------------------------------------- #
# Sandbox inspection + teardown.
# --------------------------------------------------------------------------- #
def _sandbox_schemas(port: int, retries: int = 10, delay: float = 1.0) -> list[str]:
    """Connect to the sandbox and return its schema names ([] if unreachable)."""
    import pymysql

    last_exc = None
    for _ in range(retries):
        try:
            conn = pymysql.connect(
                host=SANDBOX_HOST,
                port=port,
                user=SANDBOX_USER,
                password=SANDBOX_PASSWORD,
                connect_timeout=3,
                read_timeout=5,
            )
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT schema_name FROM information_schema.schemata")
                    return [row[0] for row in cur.fetchall()]
            finally:
                conn.close()
        except Exception as exc:  # sandbox may still be starting
            last_exc = exc
            time.sleep(delay)
    print(f"sandbox unreachable at {SANDBOX_HOST}:{port}: {last_exc}")
    return []


def _teardown_sandbox(port: int, password: str) -> None:
    """Best-effort: stop then drop the sandbox with real MCP calls.

    sandbox.delete refuses to remove a *running* instance, so it must be stopped
    first (gracefully via sandbox.stop, which needs the root password; forcibly
    via sandbox.kill as a fallback if the password is wrong or stop hangs).
    """
    def _errored(result) -> bool:
        return isinstance(result, dict) and result.get("isError")

    try:
        with MCPStdioClient([str(LAUNCHER)], env=_launcher_env(), timeout=60) as client:
            stop = client.call_tool("sandbox.stop", {"port": port, "password": password})
            if _errored(stop):
                print(f"sandbox.stop errored ({stop}); forcing sandbox.kill")
                client.call_tool("sandbox.kill", {"port": port})
            result = client.call_tool("sandbox.delete", {"port": port})
            if _errored(result):  # still running? kill and retry once
                client.call_tool("sandbox.kill", {"port": port})
                result = client.call_tool("sandbox.delete", {"port": port})
            print(f"sandbox.delete via MCP -> {result}")
    except Exception as exc:  # never let teardown mask the test result
        print(f"sandbox teardown via MCP failed: {exc}")


# --------------------------------------------------------------------------- #
# The test.
# --------------------------------------------------------------------------- #
def test_e2e_notes_app(tmp_path):
    _require_toolchain()

    port = _pick_port()
    project = tmp_path
    mcp_config = _write_mcp_config(project)
    _expose_skills(project)

    try:
        proc = _run_claude(project, mcp_config, _build_prompt(port, SANDBOX_PASSWORD))
    except subprocess.TimeoutExpired:
        pytest.fail(f"claude did not finish within {TIMEOUT}s")

    diagnostics = f"\n--- claude stdout ---\n{proc.stdout}\n--- claude stderr ---\n{proc.stderr}"

    try:
        # 1) The SQL file exists and opens with the skill's mandated Start Block.
        sql_path = project / "notes-app.sql"
        assert sql_path.is_file(), f"notes-app.sql was not created.{diagnostics}"
        sql = sql_path.read_text(encoding="utf-8")
        for marker in START_BLOCK_MARKERS:
            assert marker in sql, (
                f"notes-app.sql is missing the Start Block marker {marker!r} "
                f"required by mariadb-schema-create-script.{diagnostics}"
            )
        # Start Block must be at the top, before any DDL.
        first_ddl = re.search(r"(?im)^\s*CREATE\s+(OR\s+REPLACE\s+)?(SCHEMA|DATABASE|TABLE)", sql)
        first_marker = sql.find("@OLD_UNIQUE_CHECKS")
        assert first_ddl is None or first_marker < first_ddl.start(), (
            f"Start Block must precede the first CREATE statement.{diagnostics}"
        )

        # 2) The sandbox is up, and 3) it contains the notes-app schema.
        schemas = _sandbox_schemas(port)
        assert schemas, (
            f"sandbox not reachable at {SANDBOX_HOST}:{port} — the MCP "
            f"sandbox tool did not create it.{diagnostics}"
        )
        assert any(s in SCHEMA_CANDIDATES for s in schemas), (
            f"none of {SCHEMA_CANDIDATES} found in sandbox schemas {schemas}; the "
            f"generated script was not run via the MCP server.{diagnostics}"
        )
    finally:
        _teardown_sandbox(port, SANDBOX_PASSWORD)

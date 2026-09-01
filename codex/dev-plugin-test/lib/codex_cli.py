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

"""Driving the real ``codex`` CLI for the tier-4 e2e tests.

Everything specific to *how Codex is wired up* lives here, so the two e2e
modules can concentrate on what the model was asked to do. What the tests need
from Codex differs from Claude Code in three ways that shaped this module:

* **Skills arrive through an installed plugin, not a project directory.** Claude
  Code discovers `.claude/skills/`; Codex only loads skills from a plugin it has
  installed from a marketplace. So the fixtures install this repo's Codex plugin
  into a throwaway ``CODEX_HOME``.

* **Codex 0.147 reads `.agents/plugins/marketplace.json`, falling back to
  `.claude-plugin/marketplace.json`. It never reads `.codex-plugin/`.** The repo
  therefore ships the former, and these fixtures install from the repo root — so
  a regression that makes Codex resolve `dev@mariadb` to the *Claude* plugin
  fails the e2e tier rather than passing unnoticed.

* **Codex expands no placeholder when it spawns a plugin's MCP server.** It
  execs the stored `.mcp.json` `command` verbatim, so a ``${CLAUDE_PLUGIN_ROOT}``
  in it is exec'd literally and the server dies with "MCP startup failed: No such
  file or directory". The plugin therefore ships a *relative, extensionless*
  command plus ``"cwd": "."`` (which Codex does resolve to the plugin root) —
  see `scripts/mariadb-mcp-launcher` for why that one name works on every OS.
  `scripts/setup-codex-mcp.sh` (`codex mcp add` with an absolute path) remains
  the documented fallback, and is what :func:`run_setup_script` exercises. The
  workflow fixtures inject the server with ``-c`` instead, to keep the model runs
  independent of however the user's Codex happens to be configured.

* **Evidence comes from the event stream.** ``codex exec --json`` prints JSONL;
  an MCP call surfaces as an ``item.completed`` event whose item is
  ``{"type": "mcp_tool_call", "server": ..., "tool": ..., "status": ...}``. That
  is what proves the MariaDB MCP server was actually *used*, rather than merely
  configured.

Authentication is reused, never created: ``auth.json`` is copied out of the real
``CODEX_HOME`` into the throwaway one, so the tests run as the already
authenticated user and no credentials are minted here.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = TESTS_ROOT.parent / "dev-plugin"
REPO_ROOT = TESTS_ROOT.parents[1]
LAUNCHER = PLUGIN_DIR / "scripts" / "mariadb-mcp-launcher.sh"

# The MCP server name the plugin registers, and the marketplace/plugin ids.
SERVER_NAME = "mariadb"
MARKETPLACE_NAME = "mariadb"
PLUGIN_ID = f"dev@{MARKETPLACE_NAME}"


# --------------------------------------------------------------------------- #
# Toolchain discovery
# --------------------------------------------------------------------------- #
def codex_bin() -> str:
    return os.environ.get("CODEX_BIN") or shutil.which("codex") or ""


def mariadb_shell_resolvable() -> bool:
    return bool(os.environ.get("MARIADB_SHELL_BIN")) or shutil.which("mariadb-shell") is not None


def real_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def missing_prerequisite() -> str | None:
    """Why the e2e tier cannot run here, or None when it can."""
    if not codex_bin():
        return "codex CLI not found (set CODEX_BIN or add it to PATH)"
    if not mariadb_shell_resolvable():
        return "mariadb-shell not resolvable (set MARIADB_SHELL_BIN or put it on PATH)"
    if not LAUNCHER.is_file():
        return f"launcher missing at {LAUNCHER}"
    if not (real_codex_home() / "auth.json").is_file():
        return (
            f"codex is not authenticated ({real_codex_home()}/auth.json is missing) "
            "— run `codex login` first"
        )
    return None


# --------------------------------------------------------------------------- #
# A throwaway CODEX_HOME with this repo's Codex plugin installed
# --------------------------------------------------------------------------- #
def prepare_codex_home(root: Path) -> Path:
    """An isolated ``CODEX_HOME`` carrying the real one's authentication.

    Isolation matters here for the same reason it does for the shell's config
    home: the tests install a plugin and register an MCP server, and neither
    belongs in the user's own Codex configuration. Only ``auth.json`` is carried
    over — with 0600, as Codex writes it — so the run is authenticated as the
    user without this suite ever handling a login.
    """
    home = root / "codex_home"
    home.mkdir(parents=True, exist_ok=True)
    auth = real_codex_home() / "auth.json"
    if auth.is_file():
        dest = home / "auth.json"
        shutil.copyfile(auth, dest)
        dest.chmod(0o600)
    return home


def run_setup_script(home: Path, plugin_dir: Path | None = None) -> subprocess.CompletedProcess:
    """Run the plugin's `setup-codex-mcp.sh` against an isolated CODEX_HOME."""
    plugin_dir = plugin_dir or PLUGIN_DIR
    env = dict(os.environ)
    env["CODEX_HOME"] = str(home)
    env["CODEX_BIN"] = codex_bin()
    return subprocess.run(
        ["bash", str(plugin_dir / "scripts" / "setup-codex-mcp.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        stdin=subprocess.DEVNULL,
    )


def _codex(home: Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["CODEX_HOME"] = str(home)
    return subprocess.run(
        [codex_bin(), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        stdin=subprocess.DEVNULL,
    )


def install_plugin(home: Path, marketplace_root: Path) -> dict:
    """Add the marketplace and install the plugin; return the install JSON."""
    added = _codex(home, "plugin", "marketplace", "add", str(marketplace_root))
    if added.returncode != 0:
        raise RuntimeError(f"codex plugin marketplace add failed: {added.stderr or added.stdout}")
    installed = _codex(home, "plugin", "add", PLUGIN_ID, "--json")
    if installed.returncode != 0:
        raise RuntimeError(f"codex plugin add failed: {installed.stderr or installed.stdout}")
    try:
        return json.loads(installed.stdout)
    except json.JSONDecodeError:
        return {"raw": installed.stdout}


def plugin_listing(home: Path, marketplace_root: Path) -> str:
    """`codex plugin list` output for a marketplace root (which plugin path wins)."""
    _codex(home, "plugin", "marketplace", "add", str(marketplace_root))
    return _codex(home, "plugin", "list").stdout


def registered_server(home: Path) -> dict:
    """Parse `codex mcp get <server>` into a dict (empty when not registered)."""
    got = _codex(home, "mcp", "get", SERVER_NAME)
    if got.returncode != 0:
        return {}
    out: dict = {}
    for line in got.stdout.splitlines():
        if ":" in line and line.startswith((" ", "\t")):
            key, _, value = line.strip().partition(":")
            out[key.strip()] = value.strip()
    return out


# --------------------------------------------------------------------------- #
# The shell's own config home (plugins + the path allow-list)
# --------------------------------------------------------------------------- #
def prepare_shell_config_home(root: Path, allowed: list[Path]) -> Path:
    """An isolated mariadb-shell config home that still carries its plugins.

    Two things are mandatory and easy to miss (both cost this project time
    before): the shell loads its plugins *from the config home*, so a bare temp
    dir yields "There is no object registered under name 'mcp'"; and the
    file-touching MCP tools reject paths outside ``allowedPaths``, falling back
    to an elicitation a headless CLI cannot answer — which fails `msm.*` calls
    and hangs `sandbox.deploy`.
    """
    home = root / "shell_config_home"
    home.mkdir(parents=True, exist_ok=True)

    real = None
    for candidate in (
        os.environ.get("MARIADB_SHELL_USER_CONFIG_HOME"),
        os.environ.get("MYSQLSH_USER_CONFIG_HOME"),
        Path.home() / ".mariadb-shell",
        Path.home() / ".mysqlsh",
    ):
        if candidate and Path(candidate).is_dir():
            real = Path(candidate)
            break

    if real and (real / "plugins").is_dir():
        plugins = home / "plugins"
        plugins.mkdir(exist_ok=True)
        for entry in (real / "plugins").iterdir():
            target = entry.resolve()
            dest = plugins / entry.name
            if not dest.exists():
                dest.symlink_to(target, target_is_directory=target.is_dir())

    settings = home / "plugin_data" / "mcp_plugin" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for entry in allowed:
        for variant in _path_spellings(entry):
            if variant not in paths:
                paths.append(variant)
    settings.write_text(json.dumps({"allowedPaths": paths}, indent=4), encoding="utf-8")
    return home


def _path_spellings(path: Path) -> list[str]:
    """Every spelling of `path` the allow-list might be checked against.

    The guard compares paths as strings, and on macOS the same directory has two
    names: ``$TMPDIR`` hands out ``/var/folders/...`` while ``Path.resolve()``
    returns ``/private/var/folders/...`` (likewise ``/tmp`` and ``/private/tmp``).
    Seeding only one of them makes the tier flaky — whether it passes depends on
    which spelling the model happens to send, which is not something worth
    leaving to chance.
    """
    out = [str(path), str(path.resolve())]
    for name in list(out):
        if name.startswith("/private/var/") or name.startswith("/private/tmp/"):
            out.append(name.replace("/private", "", 1))
        elif name.startswith("/var/") or name.startswith("/tmp/"):
            out.append("/private" + name)
    seen: list[str] = []
    for name in out:
        if name not in seen:
            seen.append(name)
    return seen


def launcher_probe(root: Path, marker: Path) -> Path:
    """A launcher wrapper that records that it ran, then execs the real one.

    Codex may hold more than one definition of a server called ``mariadb`` (the
    installed plugin's, plus the one the fixture injects). Routing the injected
    one through this wrapper turns "a mariadb server answered" into "*this
    plugin's* launcher was the process Codex spawned".
    """
    probe = root / "launcher_probe.sh"
    probe.write_text(
        "#!/usr/bin/env bash\n"
        f'echo "started" >> "{marker}"\n'
        f'exec "{LAUNCHER}" "$@"\n',
        encoding="utf-8",
    )
    probe.chmod(0o755)
    return probe


# --------------------------------------------------------------------------- #
# Running codex non-interactively and reading its event stream
# --------------------------------------------------------------------------- #
@dataclass
class CodexRun:
    """One `codex exec` invocation: its raw streams plus the parsed JSONL events."""

    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    events: list[dict] = field(default_factory=list)

    @property
    def diagnostics(self) -> str:
        if self.timed_out:
            return "\ncodex did not finish within the timeout"
        return f"\n--- codex stderr ---\n{self.stderr[-4000:]}\n--- last messages ---\n" + "\n".join(
            self.agent_messages()[-3:]
        )

    def items(self, item_type: str) -> list[dict]:
        """Completed items of one type, in order (e.g. "mcp_tool_call")."""
        out = []
        for event in self.events:
            item = event.get("item") or {}
            if event.get("type") == "item.completed" and item.get("type") == item_type:
                out.append(item)
        return out

    def mcp_tool_calls(self, server: str = SERVER_NAME) -> list[dict]:
        return [c for c in self.items("mcp_tool_call") if c.get("server") == server]

    def completed_mcp_tools(self, server: str = SERVER_NAME) -> list[str]:
        """Names of the server's tools that ran to completion."""
        return [
            c.get("tool", "")
            for c in self.mcp_tool_calls(server)
            if c.get("status") == "completed"
        ]

    def error_events(self) -> list[str]:
        """`{"type": "error"}` messages from the stream (not item-level errors)."""
        return [
            e.get("message", "")
            for e in self.events
            if e.get("type") == "error" and e.get("message")
        ]

    def blocking_error(self) -> str | None:
        """An error that means "the account cannot run this", not "the test failed".

        A usage limit or an expired login produces a well-formed run that simply
        never reaches the model: `turn.started` and then an error. Reporting that
        as six failed assertions about missing MSM artifacts hides the cause, so
        the fixtures turn it into a skip — the same treatment the tier gives a
        missing toolchain.
        """
        needles = ("usage limit", "quota", "rate limit", "too many requests",
                   "not authenticated", "please log in", "unauthorized")
        for message in self.error_events():
            low = message.lower()
            if any(n in low for n in needles):
                return message
        return None

    def agent_messages(self) -> list[str]:
        return [i.get("text", "") for i in self.items("agent_message")]


def run_codex(
    prompt: str,
    *,
    project: Path,
    codex_home: Path,
    shell_config_home: Path,
    launcher: Path,
    timeout: int,
    model: str | None = None,
) -> CodexRun:
    """Run `codex exec` once in `project`, with the MariaDB MCP server wired in.

    ``--dangerously-bypass-approvals-and-sandbox`` is required, not merely
    convenient: without it Codex asks for approval before each MCP tool call and,
    with no one to ask, cancels it — the call then reports
    ``user cancelled MCP tool call`` and every later assertion fails for the
    wrong reason. The runs are confined to a throwaway project dir.
    """
    env = dict(os.environ)
    env["CODEX_HOME"] = str(codex_home)
    # Both spellings: the current build reads MARIADB_SHELL_*, older ones MYSQLSH_*.
    env["MARIADB_SHELL_USER_CONFIG_HOME"] = str(shell_config_home)
    env["MYSQLSH_USER_CONFIG_HOME"] = str(shell_config_home)

    # The server's environment has to be declared in its own config entry, not
    # merely exported here: Codex spawns MCP servers with a filtered environment,
    # so an exported MARIADB_SHELL_USER_CONFIG_HOME never reaches the shell and it
    # falls back to the real ~/.mariadb-shell — whose allow-list does not contain
    # this run's throwaway project, which the MSM tools then reject.
    server_env = {
        "MARIADB_SHELL_USER_CONFIG_HOME": str(shell_config_home),
        "MYSQLSH_USER_CONFIG_HOME": str(shell_config_home),
    }
    for name in ("MARIADB_SHELL_BIN", "MARIADB_SHELL_VERSION", "MARIADB_SHELL_PRERELEASE",
                 "MARIADB_SHELL_TOKEN", "GH_TOKEN", "PATH"):
        if os.environ.get(name):
            server_env[name] = os.environ[name]
    env_toml = "{" + ", ".join(f'{k}="{v}"' for k, v in server_env.items()) + "}"

    cmd = [
        codex_bin(),
        "exec",
        "--json",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C", str(project),
        "-c", f'mcp_servers.{SERVER_NAME}.command="{launcher}"',
        "-c", f"mcp_servers.{SERVER_NAME}.env={env_toml}",
    ]
    if model:
        cmd += ["--model", model]

    run = CodexRun()
    try:
        # The prompt goes in on **stdin**, with no prompt argument: that is the
        # documented path ("instructions are read from stdin"), and it is the only
        # one that behaves under a test harness. Passing the prompt as an argument
        # leaves stdin to chance — inherited, it can be a pipe that never reaches
        # EOF and codex blocks forever; closed (DEVNULL), codex reads the empty
        # stdin and exits at once having done nothing at all.
        proc = subprocess.run(
            cmd,
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=prompt,
        )
    except subprocess.TimeoutExpired as exc:
        run.timed_out = True
        run.stdout = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        run.stderr = (exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    else:
        run.returncode, run.stdout, run.stderr = proc.returncode, proc.stdout, proc.stderr

    for line in run.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            run.events.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a partial line from a killed run
    return run

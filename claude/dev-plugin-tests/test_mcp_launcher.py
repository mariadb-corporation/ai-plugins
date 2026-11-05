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

"""The POSIX MCP launcher's install step (step 4), run against stubs.

Nothing is downloaded: a `curl` stub hands the launcher a fake install.sh that
links a stub mariadb-shell of a newer version into the bin dir. Like the real
installer before its own lock, the fake one fails when another one is unpacking
at the same moment, so a race between launchers shows up as a failed install.
Every stub shell prints `STARTED <version>` on stdout when started as the MCP
server, which also proves the launcher wrote nothing else there.

Covers the shared launcher (claude/codex/opencode/pi) and Hermes' own, whose
step 4 takes turns the same way.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

from lib import skills

pytestmark = [
    pytest.mark.static,
    pytest.mark.skipif(os.name == "nt", reason="runs the POSIX launcher"),
]

LAUNCHERS = {
    "shared": skills.PLUGIN_ROOT / "scripts" / "mariadb-mcp-launcher.sh",
    "hermes": skills.REPO_ROOT / "hermes" / "dev-plugin" / "scripts" / "mariadb-mcp-launcher.sh",
}
LSP_LAUNCHER = skills.PLUGIN_ROOT / "scripts" / "mariadb-lsp-launcher.sh"
FLOOR, OLD, NEW = "26.10.4", "26.10.1", "26.11.0"

SHELL_STUB = """#!/bin/sh
if [ "$1" = --version ]; then echo "mariadb-shell   Ver {ver} for test"; exit 0; fi
echo "STARTED {ver}"
"""
LSP_STUB = """#!/bin/sh
echo "LSP {ver}"
"""
# The installer the curl stub serves. FAKE_* come from the test's environment,
# which the launcher passes on.
FAKE_INSTALLER = """#!/bin/sh
echo "run $$" >>"$FAKE_DIR/installs"
if [ -n "${FAKE_OTHER_WINS:-}" ]; then
  # Another installer finishes first, somewhere else on PATH; this one fails.
  mkdir -p "$FAKE_DIR/other"
  cp "$FAKE_DIR/new-shell" "$FAKE_DIR/other/mariadb-shell"
  exit 1
fi
[ -z "${FAKE_FAIL:-}" ] || { echo "fake install failing" >&2; exit 1; }
mkdir "$FAKE_DIR/unpacking" 2>/dev/null || { echo "Can't create: File exists" >&2; exit 1; }
sleep "${FAKE_SLEEP:-1}"
d="$MARIADB_SHELL_PREFIX/$FAKE_NEW/bin"
mkdir -p "$d"
cp "$FAKE_DIR/new-shell" "$d/mariadb-shell"
cp "$FAKE_DIR/new-lsp" "$d/mariadb-lsp"
mkdir -p "$MARIADB_SHELL_BINDIR"
ln -sfn "$d/mariadb-shell" "$MARIADB_SHELL_BINDIR/mariadb-shell"
ln -sfn "$d/mariadb-lsp" "$MARIADB_SHELL_BINDIR/mariadb-lsp"
rmdir "$FAKE_DIR/unpacking"
"""
CURL_STUB = """#!/bin/sh
while [ $# -gt 0 ]; do
  if [ "$1" = -o ]; then cp "{installer}" "$2"; exit 0; fi
  shift
done
exit 1
"""


def _exe(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)
    return path


class Box:
    """Temporary bin dir, prefix and stubs; an old shell linked into the bin dir."""

    def __init__(self, root: Path, launcher: Path):
        self.root, self.launcher = root, launcher
        self.fake = root / "fake"
        self.bindir = root / "bin"
        self.prefix = root / "share"
        self.stubs = root / "stubs"
        self.lock = self.prefix / ".mcp-launcher.lock"
        old = _exe(root / "old" / "mariadb-shell", SHELL_STUB.format(ver=OLD))
        self.bindir.mkdir(parents=True)
        (self.bindir / "mariadb-shell").symlink_to(old)
        _exe(self.fake / "new-shell", SHELL_STUB.format(ver=NEW))
        _exe(self.fake / "new-lsp", LSP_STUB.format(ver=NEW))
        installer = _exe(self.fake / "install.sh", FAKE_INSTALLER)
        _exe(self.stubs / "curl", CURL_STUB.format(installer=installer))
        self.env = {
            "HOME": str(root), "PATH": os.pathsep.join(
                [str(self.stubs), str(self.fake / "other"), str(self.bindir), "/usr/bin", "/bin"]),
            "MARIADB_SHELL_VERSION": FLOOR, "MARIADB_SHELL_BINDIR": str(self.bindir),
            "MARIADB_SHELL_PREFIX": str(self.prefix), "MARIADB_SHELL_PRERELEASE": "0",
            "FAKE_DIR": str(self.fake), "FAKE_NEW": NEW,
        }

    def start(self, script: Path | None = None, **env: str) -> subprocess.Popen:
        return subprocess.Popen(
            [str(script or self.launcher)], env={**self.env, **env}, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
        )

    def run(self, **env: str) -> subprocess.CompletedProcess:
        proc = self.start(**env)
        out, err = proc.communicate(timeout=60)
        return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)

    def installs(self) -> int:
        f = self.fake / "installs"
        return len(f.read_text().splitlines()) if f.exists() else 0

    def wait_for(self, cond, what: str, timeout: float = 20) -> None:
        end = time.monotonic() + timeout
        while not cond():
            assert time.monotonic() < end, f"timed out waiting for {what}"
            time.sleep(0.1)

    def lock_pids(self) -> list[str]:
        try:
            return (self.lock / "pid").read_text().split()
        except OSError:
            return []


@pytest.fixture(params=list(LAUNCHERS), ids=list(LAUNCHERS))
def box(request, tmp_path) -> Box:
    return Box(tmp_path, LAUNCHERS[request.param])


def _started(run, ver: str) -> None:
    assert run.stdout == f"STARTED {ver}\n", f"stdout {run.stdout!r}\nstderr:\n{run.stderr}"


def test_one_launcher_installs_and_starts_the_new_shell(box: Box):
    run = box.run()
    _started(run, NEW)
    assert box.installs() == 1
    assert not box.lock.exists(), "the lock was left behind"


def test_launchers_started_together_install_once(box: Box):
    procs = [box.start(FAKE_SLEEP="3") for _ in range(3)]
    runs = [p.communicate(timeout=60) for p in procs]
    for out, err in runs:
        assert out == f"STARTED {NEW}\n", f"stdout {out!r}\nstderr:\n{err}"
        assert "File exists" not in err
    assert box.installs() == 1, "\n---\n".join(err for _, err in runs)
    assert any("waiting for another MCP launcher" in err for _, err in runs)
    assert not box.lock.exists(), "the lock was left behind"


def test_a_launcher_killed_with_its_installer_leaves_no_blocking_lock(box: Box):
    """The whole process group dies (lock holder and installer): the lock is stale."""
    first = box.start(FAKE_SLEEP="30")
    box.wait_for(lambda: (box.fake / "unpacking").exists() and len(box.lock_pids()) == 2,
                 "the first launcher's installer, named in the lock, to unpack")
    os.killpg(first.pid, signal.SIGKILL)
    first.wait(timeout=10)
    (box.fake / "unpacking").rmdir()  # the fake installer's marker, which its kill left
    start = time.monotonic()
    run = box.run()
    _started(run, NEW)
    assert "clearing a lock left by an install that is gone" in run.stderr
    assert time.monotonic() - start < 15
    assert not box.lock.exists()


def test_a_launcher_stopped_by_the_harness_leaves_the_lock_to_its_installer(box: Box):
    """SIGTERM to the launcher alone: its install carries on, and the next one waits for it."""
    first = box.start(FAKE_SLEEP="4")
    box.wait_for(lambda: len(box.lock_pids()) == 2, "the first launcher's installer")
    first.send_signal(signal.SIGTERM)
    first.wait(timeout=10)
    assert box.lock.exists(), "the lock was dropped while its installer still ran"
    run = box.run()
    _started(run, NEW)
    assert box.installs() == 1, run.stderr
    assert not box.lock.exists()


def test_a_failed_install_starts_a_good_shell_another_installer_put_in_place(box: Box):
    run = box.run(FAKE_OTHER_WINS="1")
    _started(run, NEW)
    assert "another install put in place" in run.stderr


def test_a_failed_install_with_nothing_better_starts_the_old_shell_with_a_warning(box: Box):
    run = box.run(FAKE_FAIL="1")
    _started(run, OLD)
    assert f"no mariadb-shell >= {FLOOR} could be installed" in run.stderr
    assert not box.lock.exists()


def test_an_install_already_running_is_waited_for(box: Box):
    """install.sh's own lock (once it has one): wait, look again, install nothing."""
    other = subprocess.Popen(
        ["/bin/sh", "-c",
         'mkdir -p "$P/.install.lock" && echo $$ >"$P/.install.lock/pid" && sleep 2 && '
         'mkdir -p "$P/x" && cp "$F/new-shell" "$P/x/mariadb-shell" && '
         'ln -sfn "$P/x/mariadb-shell" "$B/mariadb-shell" && rm -rf "$P/.install.lock"'],
        env={"P": str(box.prefix), "F": str(box.fake), "B": str(box.bindir), "PATH": "/usr/bin:/bin"},
    )
    try:
        box.wait_for(lambda: (box.prefix / ".install.lock" / "pid").exists(), "the other install")
        run = box.run()
    finally:
        other.wait(timeout=10)
    _started(run, NEW)
    assert "waiting for an install already running" in run.stderr
    assert box.installs() == 0


def test_waiting_gives_up_after_the_lock_wait(box: Box):
    holder = subprocess.Popen(["sleep", "30"])
    try:
        box.lock.mkdir(parents=True)
        (box.lock / "pid").write_text(f"{holder.pid}\n")
        start = time.monotonic()
        run = box.run(MARIADB_SHELL_LOCK_WAIT="2")
        assert time.monotonic() - start < 10
    finally:
        holder.kill()
        holder.wait()
    _started(run, OLD)
    assert "gave up after" in run.stderr
    assert box.installs() == 0
    assert box.lock.exists(), "a lock this launcher never held was removed"


def test_the_lsp_launcher_waits_for_the_locked_install(tmp_path):
    box = Box(tmp_path, LAUNCHERS["shared"])
    mcp = [box.start(FAKE_SLEEP="3") for _ in range(2)]
    lsp = box.start(LSP_LAUNCHER, MARIADB_LSP_WAIT="30")
    out, err = lsp.communicate(timeout=60)
    for p in mcp:
        p.communicate(timeout=60)
    assert out == f"LSP {NEW}\n", f"stdout {out!r}\nstderr:\n{err}"
    assert box.installs() == 1


def test_a_shell_printing_messages_before_its_version_is_accepted(box: Box):
    """Some builds print plugin registration errors before the "Ver" line."""
    noisy = SHELL_STUB.format(ver=NEW).replace(
        'if [ "$1" = --version ]; then',
        'if [ "$1" = --version ]; then echo "Error registering plugin 2.1 in server 3.4";')
    (box.bindir / "mariadb-shell").unlink()
    _exe(box.bindir / "mariadb-shell", noisy)
    run = box.run()
    _started(run, NEW)
    assert box.installs() == 0, run.stderr

"""Shared pytest fixtures.

Makes ``lib`` importable and provides the live-MariaDB connection used by the
``db`` tier. The static tier needs none of the DB machinery, so PyMySQL is
imported lazily inside the fixtures.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

# Make `from lib import skills` work regardless of where pytest is invoked.
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _db_config() -> dict:
    return {
        "host": os.environ.get("MARIADB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MARIADB_PORT", "3306")),
        "user": os.environ.get("MARIADB_USER", "root"),
        "password": os.environ.get("MARIADB_PASSWORD", "test"),
    }


@pytest.fixture(scope="session")
def mariadb_connection():
    """A session-scoped connection to the test MariaDB server.

    Skips the entire db tier if PyMySQL is missing or the server is unreachable,
    so the static tier never depends on a database.
    """
    try:
        import pymysql
    except ImportError:
        pytest.skip("PyMySQL not installed — skipping the live-DB tier")

    cfg = _db_config()
    try:
        conn = pymysql.connect(
            autocommit=True,
            charset="utf8mb4",
            **cfg,
        )
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(
            f"MariaDB unreachable at {cfg['host']}:{cfg['port']} ({exc}); "
            "set MARIADB_* env vars or start the docker-compose service"
        )
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def scratch_db(mariadb_connection):
    """A throwaway database, dropped after the test, for isolation.

    Yields the open connection with the scratch database selected as default.
    """
    name = "skilltest_" + uuid.uuid4().hex[:12]
    with mariadb_connection.cursor() as cur:
        cur.execute(f"CREATE DATABASE `{name}`")
        cur.execute(f"USE `{name}`")
    try:
        yield mariadb_connection, name
    finally:
        with mariadb_connection.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{name}`")

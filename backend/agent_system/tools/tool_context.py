"""ContextVar that the ToolRegistry uses to inject a DB connection into handlers.

The registry sets this var around every handler dispatch so that tool
implementations can call get_tool_conn() without accepting `conn` as an
explicit parameter (which would surface it in the capability-token scope).
"""
from __future__ import annotations

from contextvars import ContextVar

import psycopg

_conn_var: ContextVar[psycopg.Connection | None] = ContextVar("tool_conn", default=None)


def get_tool_conn() -> psycopg.Connection:
    """Return the DB connection injected by the ToolRegistry for this call."""
    conn = _conn_var.get()
    if conn is None:
        raise RuntimeError(
            "No database connection in tool context. "
            "This function must be called inside ToolRegistry.invoke()."
        )
    return conn

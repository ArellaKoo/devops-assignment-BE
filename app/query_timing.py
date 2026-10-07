"""Opt-in timing instrumentation for the Q6(b) local load measurement.

Inactive unless the API server process sets ``SKIPQ_QUERY_TIMING=1`` and
``SKIPQ_QUERY_TIMING_FILE``. When active it adds exactly three things:

- a wall-clock timer around the menu endpoint's existing materialisation
  (the route fills the list the segment yields — no query logic moves here);
- a per-request wall-clock timer via Flask before/after hooks;
- a pymongo command monitor installed **at client construction** through
  MongoEngine's ``mongo_client_class`` hook (PyMongo 4 has no post-hoc
  listener registration) that counts the find commands each request's
  thread issues (the auth user lookup and the menu query) with the rows
  each find returned.

One JSON line per event goes to the configured file (``request`` and
``segment`` lines carry ``wall_ms``; find entries carry ``rows`` and the
client-observed command wall time). Nothing in this module issues a query
of its own, and with the flag off every entry point is a boolean check.
The client-side timings intentionally include loopback network time and
Python document materialisation; the measurement's limits are recorded with
the Q6(b) evidence.
"""

from __future__ import annotations

import json
import os
import threading
import time
from contextlib import contextmanager

from pymongo import MongoClient
from pymongo.monitoring import CommandListener

_ENABLED = os.environ.get("SKIPQ_QUERY_TIMING") == "1"
_FILE = os.environ.get("SKIPQ_QUERY_TIMING_FILE", "")

_lock = threading.Lock()
_local = threading.local()


def enabled() -> bool:
    """True only when the flag is set *and* a file path was supplied."""
    return _ENABLED and bool(_FILE)


def configure(enabled: bool, file_path: str = "") -> None:
    """Test seam for the module-level state (the server reads the environment at import)."""
    global _ENABLED, _FILE
    _ENABLED = enabled
    _FILE = file_path


def _record(event: dict) -> None:
    if not enabled():
        return
    event = {"ts": time.time(), **event}
    with _lock:
        with open(_FILE, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event) + "\n")


class _CommandTracker:
    """One request thread's tally of the find commands it issues."""

    def __init__(self) -> None:
        self.finds: list[dict] = []
        self.other_commands = 0

    def command_started(self, event) -> None:
        name = (getattr(event, "command_name", "") or "").lower()
        if name in ("find", "aggregate"):
            # PyMongo 4 dropped the event.collection property; the collection
            # name is the "find"/"aggregate" field of the command body.
            command = getattr(event, "command", None) or {}
            self.finds.append(
                {
                    "command": name,
                    "database": getattr(event, "database_name", None),
                    "collection": command.get("find") or command.get("aggregate"),
                    "started": time.perf_counter(),
                }
            )
        else:
            self.other_commands += 1

    def command_succeeded(self, event) -> None:
        name = (getattr(event, "command_name", "") or "").lower()
        if name not in ("find", "aggregate") or not self.finds:
            return
        entry = self.finds[-1]
        entry["wall_ms"] = round((time.perf_counter() - entry["started"]) * 1000, 3)
        reply = getattr(event, "reply", None)
        if isinstance(reply, dict):
            entry["rows"] = len(reply.get("cursor", {}).get("firstBatch", []))
        micros = getattr(event, "duration_micros", None)
        if micros is not None:
            entry["command_ms"] = round(micros / 1000, 3)
        else:
            command_ms = getattr(event, "duration", None)
            if command_ms is not None:
                entry["command_ms"] = command_ms

    def command_failed(self, event) -> None:
        name = (getattr(event, "command_name", "") or "").lower()
        if name in ("find", "aggregate") and self.finds:
            entry = self.finds[-1]
            entry["failed"] = True
            entry["wall_ms"] = round((time.perf_counter() - entry["started"]) * 1000, 3)


class _Dispatcher(CommandListener):
    """The command monitor; forwards each event to the running request's thread-local tracker.

    PyMongo 4's listener contract is ``started``/``succeeded``/``failed``
    (the PyMongo 3 ``command_*`` names are gone).
    """

    def _route(self, method, event) -> None:
        tracker = getattr(_local, "tracker", None)
        if tracker is not None:
            getattr(tracker, method)(event)

    def started(self, event) -> None:
        self._route("command_started", event)

    def succeeded(self, event) -> None:
        self._route("command_succeeded", event)

    def failed(self, event) -> None:
        self._route("command_failed", event)


_CLIENT_CLASS: type[MongoClient] | None = None


def client_class() -> type[MongoClient]:
    """The (cached) MongoClient that installs the command monitor at construction.

    MongoEngine's ``mongo_client_class`` setting hands this class to
    ``connect()``; PyMongo 4 validates and keeps the listeners passed to
    the constructor (there is no post-hoc registration on a live client).
    With the flag off the subclass is a pure pass-through. One process
    gets one class object so repeated connection registrations compare
    equal in MongoEngine's settings.
    """
    global _CLIENT_CLASS
    if _CLIENT_CLASS is None:

        class _TracedMongoClient(MongoClient):
            def __init__(self, *args, **kwargs) -> None:
                if enabled():
                    listeners = list(kwargs.get("event_listeners") or [])
                    listeners.append(_Dispatcher())
                    kwargs["event_listeners"] = listeners
                super().__init__(*args, **kwargs)

        _CLIENT_CLASS = _TracedMongoClient
    return _CLIENT_CLASS


def install(app) -> None:
    """Register the per-request hooks on a Flask app; a no-op unless enabled."""
    if not enabled() or getattr(app, "skipq_query_timing_installed", False):
        return
    app.skipq_query_timing_installed = True

    @app.before_request
    def _start_request() -> None:
        from flask import g

        import mongoengine

        g.qt_start = time.perf_counter()
        _local.tracker = _CommandTracker()
        # Materialise the (already monitored) MongoEngine client before this
        # request's first command so the monitor is in place for it too.
        mongoengine.get_db("default")

    @app.after_request
    def _finish_request(response):
        from flask import g, request as flask_request

        start = g.pop("qt_start", None)
        tracker = getattr(_local, "tracker", None)
        if start is None or tracker is None:
            return response
        _record(
            {
                "type": "request",
                "path": flask_request.path,
                "method": flask_request.method,
                "status": response.status_code,
                "wall_ms": round((time.perf_counter() - start) * 1000, 3),
                "finds": tracker.finds,
                "other_commands": tracker.other_commands,
            }
        )
        _local.tracker = None
        return response

    return app


@contextmanager
def timed_segment(label: str):
    """Time an existing materialisation in place; the caller fills the yielded list.

    With the flag off this yields a plain list and records nothing.
    """
    if not enabled():
        yield []
        return
    start = time.perf_counter()
    out: list = []
    try:
        yield out
    finally:
        _record(
            {
                "type": "segment",
                "label": label,
                "wall_ms": round((time.perf_counter() - start) * 1000, 3),
                "rows": len(out),
            }
        )

"""Q6(b) opt-in query timing: inert without the flag, exact JSONL records with it.

The instrumentation must add no query logic and no behaviour when the
environment flag is off; these cases prove the switch, the record shapes,
the per-request command accounting and the Flask hook registration without
opening a database connection.
"""

import json
from types import SimpleNamespace

from flask import Flask

from app import query_timing
from app.query_timing import _CommandTracker, _Dispatcher


def _find_event(rows=3, duration_ms=None):
    # PyMongo 4 events carry the command body, not a .collection attribute.
    return SimpleNamespace(
        command_name="find",
        database_name="skipq_system_test",
        command={"find": "menu_items", "filter": {}},
        reply={"cursor": {"firstBatch": [{} for _ in range(rows)]}},
        duration=duration_ms,
    )


def _other_event(name="insert"):
    return SimpleNamespace(command_name=name, database_name="skipq_system_test")


def _lines(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def test_disabled_by_default_writes_nothing(tmp_path):
    """GIVEN the flag is off WHEN a segment runs and records are requested THEN no file exists."""
    out = tmp_path / "off.jsonl"
    query_timing.configure(False, str(out))
    try:
        with query_timing.timed_segment("menu_materialize") as items:
            items.extend(["a", "b"])
        query_timing._record({"type": "request", "path": "/x"})
        assert list(items) == ["a", "b"]
        assert not out.exists()
    finally:
        query_timing.configure(False, "")


def test_enabled_requires_a_file_path(tmp_path):
    """GIVEN the flag is set without a file path WHEN the state is read THEN the module reports disabled."""
    query_timing.configure(True, "")
    try:
        assert query_timing.enabled() is False
        with query_timing.timed_segment("menu_materialize") as items:
            items.append("a")
        assert not (tmp_path / "nothing.jsonl").exists()
    finally:
        query_timing.configure(False, "")


def test_segment_record_shape(tmp_path):
    """GIVEN the flag and a path WHEN the caller fills the segment THEN one segment line carries label, rows and wall time."""
    out = tmp_path / "seg.jsonl"
    query_timing.configure(True, str(out))
    try:
        with query_timing.timed_segment("menu_materialize") as items:
            items.extend(["a", "b", "c"])
        records = _lines(out)
        assert len(records) == 1
        record = records[0]
        assert record["type"] == "segment"
        assert record["label"] == "menu_materialize"
        assert record["rows"] == 3
        assert record["wall_ms"] >= 0
        assert record["ts"] > 0
    finally:
        query_timing.configure(False, "")


def test_request_record_appends_without_clobbering(tmp_path):
    """GIVEN one segment line WHEN a request record is written THEN both lines survive in order."""
    out = tmp_path / "mix.jsonl"
    query_timing.configure(True, str(out))
    try:
        with query_timing.timed_segment("menu_materialize") as items:
            items.append("a")
        query_timing._record({"type": "request", "path": "/api/diner/menu", "status": 200, "wall_ms": 1.0, "finds": [], "other_commands": 0})
        records = _lines(out)
        assert [record["type"] for record in records] == ["segment", "request"]
        assert records[1]["path"] == "/api/diner/menu"
    finally:
        query_timing.configure(False, "")


def test_tracker_counts_find_rows_and_wall_time():
    """GIVEN a find command pair WHEN it starts and succeeds THEN the tracker keeps collection, rows and a non-negative wall time."""
    tracker = _CommandTracker()
    tracker.command_started(_find_event(rows=5, duration_ms=1.25))
    tracker.command_succeeded(_find_event(rows=5, duration_ms=1.25))
    assert tracker.other_commands == 0
    assert len(tracker.finds) == 1
    entry = tracker.finds[0]
    assert entry["command"] == "find"
    assert entry["collection"] == "menu_items"
    assert entry["database"] == "skipq_system_test"
    assert entry["rows"] == 5
    assert entry["wall_ms"] >= 0
    assert entry["command_ms"] == 1.25


def test_tracker_converts_duration_micros_to_milliseconds():
    """GIVEN a PyMongo 4 event carrying duration_micros WHEN it succeeds THEN the tracker stores milliseconds."""
    event = _find_event(rows=2)
    event.duration_micros = 1500  # 1.5 ms; the legacy ms attribute is absent
    del event.duration
    tracker = _CommandTracker()
    tracker.command_started(event)
    tracker.command_succeeded(event)
    assert tracker.finds[0]["command_ms"] == 1.5


def test_tracker_counts_other_commands_separately():
    """GIVEN non-find commands WHEN they start THEN only the other-command counter moves."""
    tracker = _CommandTracker()
    tracker.command_started(_other_event("insert"))
    tracker.command_started(_other_event("command"))
    assert tracker.finds == []
    assert tracker.other_commands == 2


def test_tracker_marks_a_failed_find():
    """GIVEN a started find WHEN it fails instead of succeeding THEN the entry is marked failed with a wall time."""
    tracker = _CommandTracker()
    tracker.command_started(_find_event(rows=2))
    tracker.command_failed(_find_event(rows=2))
    entry = tracker.finds[0]
    assert entry["failed"] is True
    assert entry["wall_ms"] >= 0
    assert "rows" not in entry


def test_tracker_ignores_succeeded_events_without_a_start():
    """GIVEN no started find WHEN a success event arrives THEN nothing is recorded and nothing raises."""
    tracker = _CommandTracker()
    tracker.command_succeeded(_find_event(rows=9))
    assert tracker.finds == []


def test_dispatcher_overrides_the_pymongo_4_contract_methods():
    """GIVEN the dispatcher WHEN its PyMongo 4 methods (started/succeeded/failed) run WITHOUT a tracker THEN they handle the event instead of raising the base class's NotImplementedError."""
    dispatcher = _Dispatcher()
    for method in ("started", "succeeded", "failed"):
        assert _Dispatcher.__dict__.get(method) is not None, (
            f"_Dispatcher must override PyMongo 4's {method!r} (the base raises NotImplementedError)"
        )
    dispatcher.started(_find_event(rows=1))  # no tracker on this thread: dropped, not raised
    dispatcher.succeeded(_find_event(rows=1))
    dispatcher.failed(_find_event(rows=1))


def test_install_registers_hooks_only_when_enabled():
    """GIVEN a plain Flask app WHEN install runs enabled THEN before/after hooks are registered; WHEN disabled THEN the app is left untouched."""
    off = Flask("off")
    query_timing.configure(False, "")
    query_timing.install(off)
    assert not off.before_request_funcs
    assert not off.after_request_funcs

    on = Flask("on")
    query_timing.configure(True, "/tmp/skipq-unit-query-timing.jsonl")
    try:
        query_timing.install(on)
        assert len(on.before_request_funcs[None]) == 1
        assert len(on.after_request_funcs[None]) == 1
    finally:
        query_timing.configure(False, "")


def test_install_is_idempotent_per_app():
    """GIVEN an enabled app WHEN install runs twice THEN exactly one pair of hooks remains."""
    app = Flask("twice")
    query_timing.configure(True, "/tmp/skipq-unit-query-timing.jsonl")
    try:
        query_timing.install(app)
        query_timing.install(app)
        assert len(app.before_request_funcs[None]) == 1
        assert len(app.after_request_funcs[None]) == 1
    finally:
        query_timing.configure(False, "")


def _installed_dispatchers(client):
    listeners = client.options.event_listeners or []
    return [listener for listener in listeners if isinstance(listener, _Dispatcher)]


def test_client_class_is_a_cached_mongo_client_subclass():
    """GIVEN the factory WHEN it is called twice THEN one cached MongoClient subclass comes back."""
    from pymongo import MongoClient

    first = query_timing.client_class()
    second = query_timing.client_class()
    assert first is second
    assert issubclass(first, MongoClient)


def test_client_class_installs_no_dispatcher_when_disabled():
    """GIVEN the flag is off WHEN the traced client is constructed THEN no command monitor is attached (pass-through)."""
    query_timing.configure(False, "")
    try:
        client = query_timing.client_class()("mongodb://127.0.0.1:1", connect=False)
        assert _installed_dispatchers(client) == []
    finally:
        client.close()
        query_timing.configure(False, "")


def test_client_class_installs_one_dispatcher_when_enabled():
    """GIVEN the flag and a path WHEN the traced client is constructed THEN exactly one command monitor is attached."""
    query_timing.configure(True, "/tmp/skipq-unit-query-timing.jsonl")
    try:
        client = query_timing.client_class()("mongodb://127.0.0.1:1", connect=False)
        assert len(_installed_dispatchers(client)) == 1
    finally:
        client.close()
        query_timing.configure(False, "")

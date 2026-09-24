"""
Tests for the mid-loop break retry-storm fix in Embedder.migrate_baseline().

No live embedding server is required: Embedder.encode is monkeypatched so the
real OpenAI client is never called, and chroma_db_path points at tmp_path so
no real vector-store state is touched.
"""

import logging
from hashlib import sha256
from pathlib import Path
from typing import Any

import chromadb
import pytest

from main import _similar_incidents_note
from ravensight.embedder import Embedder

MIGRATED_MSG = "Migrated {count} entries from baseline to vector store"


@pytest.fixture()
def embedder(tmp_path: Path) -> Embedder:
    """Build an Embedder backed by a temporary ChromaDB path."""
    config = {"chroma_db_path": str(tmp_path / "chromadb")}
    return Embedder(config)


def _baseline_data(findings: int, recommendations: int) -> dict[str, Any]:
    """Build baseline data with the given number of findings and recommendations."""
    return {
        "updated_at": "2026-09-24T00:00:00",
        "findings": [f"finding {i}" for i in range(findings)],
        "recommendations": [f"recommendation {i}" for i in range(recommendations)],
    }


def test_server_down_stops_after_first_failure(
    embedder: Embedder, monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    """One encode failure migrates nothing, logs one warning, and stops."""
    calls: list[str] = []

    def fake_encode(self: Embedder, text: str) -> list[float]:
        """Mimic real encode(): set degraded before raising."""
        calls.append(text)
        self._degraded = True
        raise ValueError("server unreachable")

    monkeypatch.setattr(Embedder, "encode", fake_encode)
    caplog.set_level(logging.INFO, logger="ravensight.embedder")

    result = embedder.migrate_baseline(_baseline_data(3, 3))

    assert len(calls) == 1
    assert result == 0
    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING"]
    assert len(warnings) == 1
    assert any(MIGRATED_MSG.format(count=0) in rec.message for rec in caplog.records)


def test_healthy_server_migrates_all_entries(
    embedder: Embedder, monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    """Successful encodes migrate everything with no warnings."""
    calls: list[str] = []

    def fake_encode(self: Embedder, text: str) -> list[float]:
        """Return a valid embedding for every call."""
        calls.append(text)
        return [0.0] * 8

    monkeypatch.setattr(Embedder, "encode", fake_encode)
    caplog.set_level(logging.INFO, logger="ravensight.embedder")

    result = embedder.migrate_baseline(_baseline_data(3, 3))

    assert len(calls) == 6
    assert result == 6
    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING"]
    assert len(warnings) == 0
    assert any(MIGRATED_MSG.format(count=6) in rec.message for rec in caplog.records)


def test_partial_success_stops_at_second_failure(
    embedder: Embedder, monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    """First entry migrates, second fails; recommendations loop never starts."""
    calls: list[str] = []

    def fake_encode(self: Embedder, text: str) -> list[float]:
        """Succeed once, then set degraded and raise like real encode()."""
        calls.append(text)
        if len(calls) > 1:
            self._degraded = True
            raise ValueError("server unreachable")
        return [0.0] * 8

    monkeypatch.setattr(Embedder, "encode", fake_encode)
    caplog.set_level(logging.INFO, logger="ravensight.embedder")

    result = embedder.migrate_baseline(_baseline_data(3, 3))

    assert len(calls) == 2
    assert result == 1
    warnings = [rec for rec in caplog.records if rec.levelname == "WARNING"]
    assert len(warnings) == 1
    assert any(MIGRATED_MSG.format(count=1) in rec.message for rec in caplog.records)


def _metadata(summary: str) -> dict[str, Any]:
    """Build valid ChromaDB metadata for add_embedding calls."""
    return {
        "timestamp": "2026-09-24T00:00:00",
        "rule_group": "test_group",
        "severity": "unknown",
        "summary": summary,
    }


def test_add_embedding_deterministic_id(
    embedder: Embedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Identical text produces an identical id, so repeats overwrite rather than duplicate."""
    monkeypatch.setattr(Embedder, "encode", lambda self, text: [0.0] * 8)

    embedder.add_embedding("repeat me", _metadata("repeat me"))
    embedder.add_embedding("repeat me", _metadata("repeat me"))

    expected_id = "alert-" + sha256("repeat me".encode("utf-8")).hexdigest()[:32]
    assert embedder._collection.count() == 1
    assert embedder._collection.get(ids=[expected_id])["ids"] == [expected_id]


def test_add_embedding_skipped_when_degraded(
    embedder: Embedder, monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    """A degraded embedder never encodes or touches the vector store."""
    encode_calls: list[str] = []

    def fake_encode(self: Embedder, text: str) -> list[float]:
        """Track any encode attempt."""
        encode_calls.append(text)
        return [0.0] * 8

    monkeypatch.setattr(Embedder, "encode", fake_encode)
    caplog.set_level(logging.WARNING, logger="ravensight.embedder")
    embedder._degraded = True

    embedder.add_embedding("should not land", _metadata("should not land"))

    assert encode_calls == []
    assert embedder._collection.count() == 0
    assert any("vector-store add skipped" in rec.message for rec in caplog.records)


def test_migrate_baseline_deletes_before_reinsert(
    embedder: Embedder, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each category's existing vectors are deleted before its re-insert loop runs."""
    monkeypatch.setattr(Embedder, "encode", lambda self, text: [0.0] * 8)

    events: list[tuple[str, Any]] = []
    real_delete = chromadb.Collection.delete
    real_upsert = chromadb.Collection.upsert

    def recording_delete(self: Any, **kwargs: Any) -> Any:
        """Record delete calls with their where clause."""
        events.append(("delete", kwargs.get("where")))
        return real_delete(self, **kwargs)

    def recording_upsert(self: Any, **kwargs: Any) -> Any:
        """Record upsert calls."""
        events.append(("upsert", None))
        return real_upsert(self, **kwargs)

    monkeypatch.setattr(chromadb.Collection, "delete", recording_delete)
    monkeypatch.setattr(chromadb.Collection, "upsert", recording_upsert)

    embedder.migrate_baseline(_baseline_data(1, 1))

    assert events == [
        ("delete", {"rule_group": "baseline_finding"}),
        ("upsert", None),
        ("delete", {"rule_group": "baseline_recommendation"}),
        ("upsert", None),
    ]


def test_chroma_unreachable_degrades_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    """A Chroma failure at collection creation degrades gracefully instead of crashing."""

    class FakeClient:
        """Stand-in client whose collection call always fails."""

        def get_or_create_collection(self, **kwargs: Any) -> Any:
            """Raise as an unreachable Chroma server would."""
            raise ValueError("chroma is down")

    monkeypatch.setattr(chromadb, "PersistentClient", lambda **kwargs: FakeClient())
    caplog.set_level(logging.WARNING, logger="ravensight.embedder")

    emb = Embedder({"chroma_db_path": str(tmp_path / "chromadb")})

    assert emb.degraded is True
    assert emb._chroma_failure is not None
    assert emb._collection is None
    assert any("ChromaDB unreachable" in rec.message for rec in caplog.records)


def test_chroma_construction_failure_degrades_gracefully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: Any
) -> None:
    """A ValueError raised by PersistentClient construction degrades gracefully."""

    def failing_client(**kwargs: Any) -> Any:
        """Raise as chromadb clients do when no server is listening at construction time."""
        raise ValueError("Could not connect to a Chroma server. Are you sure it is running?")

    monkeypatch.setattr(chromadb, "PersistentClient", failing_client)
    caplog.set_level(logging.WARNING, logger="ravensight.embedder")

    emb = Embedder({"chroma_db_path": str(tmp_path / "chromadb")})

    assert emb.degraded is True
    assert emb._chroma_failure
    assert emb._collection is None
    assert any("ChromaDB unreachable" in rec.message for rec in caplog.records)


def test_similar_incidents_note_derivation(embedder: Embedder) -> None:
    """The note names the chroma cause when set, else blames the embedding server."""
    assert _similar_incidents_note(None) is None
    assert _similar_incidents_note(embedder) is None

    embedder._degraded = True
    assert _similar_incidents_note(embedder) == (
        "Similar Past Incidents: unavailable — embedding server unreachable"
    )

    embedder._chroma_failure = "ConnectError: connection refused"
    assert _similar_incidents_note(embedder) == (
        "Similar Past Incidents: unavailable — ConnectError: connection refused"
    )

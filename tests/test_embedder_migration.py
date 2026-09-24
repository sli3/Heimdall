"""
Tests for the mid-loop break retry-storm fix in Embedder.migrate_baseline().

No live embedding server is required: Embedder.encode is monkeypatched so the
real OpenAI client is never called, and chroma_db_path points at tmp_path so
no real vector-store state is touched.
"""

import logging
from pathlib import Path
from typing import Any

import pytest

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

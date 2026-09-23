"""
baseline.py — Baseline memory persistence for security analysis.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class Manager:
    """Manages baseline memory persistence."""

    def __init__(self, config: dict[str, Any], embedder=None) -> None:
        """
        Initialise baseline manager.

        Args:
            config: Baseline config with path key.
            embedder: Optional Embedder instance for vector store updates.
        """
        self._path = Path(config["path"])
        self._embedder = embedder
        self._load()

    def _load(self) -> None:
        """Load baseline from disk."""
        if self._path.exists():
            try:
                with self._path.open("r") as f:
                    self._baseline = json.load(f)
                logger.info(f"Loaded baseline from {self._path}")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode baseline, starting fresh: {e}")
                self._baseline = {"findings": [], "recommendations": [], "scan_history": []}
        else:
            self._baseline = {"findings": [], "recommendations": [], "scan_history": []}

    def load(self) -> dict[str, Any]:
        """
        Return current baseline dict.

        Returns:
            Baseline dict with findings and recommendations.
        """
        return self._baseline

    def update(
        self, 
        analysis: dict[str, Any], 
        rule_counts: dict[str, int] | None = None
    ) -> None:
        """
        Update baseline with new analysis results.

        Args:
            analysis: Analysis dict from analyser.analyse().
            rule_counts: Optional dict of rule-group counts for this run.
        """
        findings = analysis.get("findings", [])
        recommendations = analysis.get("recommendations", [])

        if findings:
            self._baseline["findings"] = findings
            self._baseline["updated_at"] = datetime.now().isoformat()

        if recommendations:
            self._baseline["recommendations"] = recommendations

        # Add embeddings from rule_counts when embedder is present
        if self._embedder is not None and rule_counts:
            for rule_desc, count in rule_counts.items():
                text = f"{rule_desc}: {count} alerts"
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "rule_group": rule_desc,
                    "severity": "unknown",
                    "summary": text,
                }
                self._embedder.add_embedding(text, metadata)

        if rule_counts:
            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "rule_groups": rule_counts
            }
            self._baseline.setdefault("scan_history", []).append(snapshot)

        self._save()
        logger.info(f"Updated baseline with {len(findings)} findings")

    def _save(self) -> None:
        """Save baseline to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(self._baseline, f, indent=2)
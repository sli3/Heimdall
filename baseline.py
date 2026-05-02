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

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialise baseline manager.

        Args:
            config: Baseline config with path key.
        """
        self._path = Path(config["path"])
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
                self._baseline = {"findings": [], "recommendations": []}
        else:
            self._baseline = {"findings": [], "recommendations": []}

    def load(self) -> dict[str, Any]:
        """
        Return current baseline dict.

        Returns:
            Baseline dict with findings and recommendations.
        """
        return self._baseline

    def update(self, analysis: dict[str, Any]) -> None:
        """
        Update baseline with new analysis results.

        Args:
            analysis: Analysis dict from analyser.analyse().
        """
        findings = analysis.get("findings", [])
        recommendations = analysis.get("recommendations", [])

        if findings:
            self._baseline["findings"] = findings
            self._baseline["updated_at"] = datetime.now().isoformat()

        if recommendations:
            self._baseline["recommendations"] = recommendations

        self._save()
        logger.info(f"Updated baseline with {len(findings)} findings")

    def _save(self) -> None:
        """Save baseline to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w") as f:
            json.dump(self._baseline, f, indent=2)
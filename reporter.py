"""
reporter.py — Markdown security report generation.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Any


logger = logging.getLogger(__name__)


class Reporter:
    """Generates markdown security reports."""

    def __init__(self, config: dict[str, Any]) -> None:
        """
        Initialise reporter.

        Args:
            config: Reports config with output_dir key.
        """
        self._output_dir = Path(config["output_dir"])
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, data: dict[str, Any]) -> None:
        """
        Generate markdown report from analysis data.

        Args:
            data: Analysis or baseline dict with summary, findings, recommendations.
        """
        report = self._build_report(data)
        filename = self._output_dir / f"{datetime.now().strftime('%Y-%m-%d')}_security_report.md"
        with filename.open("w") as f:
            f.write(report)
        logger.info(f"Report written to {filename}")

    def _build_report(self, data: dict[str, Any]) -> str:
        """Build markdown report content."""
        lines = [
            "# Security Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            "",
            data.get("summary", "No summary available"),
            "",
            "## Findings",
            "",
        ]

        findings = data.get("findings", [])
        if findings:
            for finding in findings:
                lines.append(f"- {finding}")
        else:
            lines.append("*No findings*")

        lines.extend([
            "",
            "## Recommendations",
            "",
        ])

        recommendations = data.get("recommendations", [])
        if recommendations:
            for rec in recommendations:
                lines.append(f"- {rec}")
        else:
            lines.append("*No recommendations*")

        lines.append("")
        return "\n".join(lines)
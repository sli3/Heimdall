"""
reporter.py — Markdown security report generation.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


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

    def generate(self, data: dict[str, Any], trends: Optional[str] = None) -> None:
        """
        Generate markdown report from analysis data.

        Args:
            data: Analysis or baseline dict with summary, findings, recommendations.
            trends: Optional trending markdown to append to report.
        """
        report = self._build_report(data, trends=trends)
        filename = self._output_dir / f"{datetime.now().strftime('%Y-%m-%d')}_security_report.md"
        with filename.open("w") as f:
            f.write(report)
        logger.info(f"Report written to {filename}")

    def _build_report(self, data: dict[str, Any], trends: Optional[str] = None) -> str:
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

        # Similar past incidents — context for findings
        similar = data.get("similar_incidents", "").strip()
        if similar:
            lines.extend([
                "",
                "## Similar Past Incidents",
                "",
                similar,
                "",
            ])

        # MITRE ATT&CK Tags — threat classification
        mitre_tags = data.get("mitre_tags", [])
        if mitre_tags:
            lines.extend([
                "## MITRE ATT&CK Tags",
                "",
                "| Tactic | Description |",
                "|--------|-------------|",
            ])
            for tag in mitre_tags:
                tactic = tag.get("tactic", "Unknown")
                description = tag.get("description", "No description")
                lines.append(f"| {tactic} | {description} |")
            lines.append("")

        # Historical trends — supporting data
        if trends:
            lines.extend(["", trends])

        # Recommendations last — actions flow from all evidence above
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
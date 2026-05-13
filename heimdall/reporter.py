"""
reporter.py — Markdown security report generation.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


logger = logging.getLogger(__name__)


def _render_asd_section(asd_data: dict) -> str:
    """
    Render ASD Framework section as markdown.

    Args:
        asd_data: Parsed ASD framework data dict from asd_framework.json.

    Returns:
        Markdown string for the ASD section, or empty string if no data.
    """
    if not asd_data:
        return ""

    lines = ["## ASD Framework", ""]

    # Essential Eight Maturity Summary
    lines.extend(["### Essential Eight Maturity Summary", "",])

    essential_eight = asd_data.get("essential_eight", [])
    strategies: dict[str, list[int]] = {}
    for entry in essential_eight:
        s = entry.get("strategy", "")
        ml = entry.get("maturity_level", 0)
        strategies.setdefault(s, []).append(ml)

    if strategies:
        ml_levels = ["ML1", "ML2", "ML3", "ML4"]
        header = "| Strategy | ML1 | ML2 | ML3 | ML4 |"
        separator = "|----------|-----|-----|-----|-----|"
        lines.extend([header, separator])
        for strategy, mls in strategies.items():
            row = f"| {strategy} |"
            for level in [1, 2, 3, 4]:
                row += " ✓ |" if level in mls else " - |"
            lines.append(row)
        lines.append("")

    # Relevant ISM Controls
    lines.extend(["### Relevant ISM Controls", "",])

    ism_controls = asd_data.get("ism", [])
    if ism_controls:
        lines.append("| Control ID | Category | Description |")
        lines.append("|------------|----------|-------------|")

        for control in ism_controls:
            control_id = control.get("id", "Unknown")
            category = control.get("category", "Unknown")
            description = control.get("description", "")
            truncated_desc = description[:120] if len(description) > 120 else description
            lines.append(f"| {control_id} | {category} | {truncated_desc} |")

        lines.append("")

    return "\n".join(lines)


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

    def generate(self, data: dict[str, Any], trends: Optional[str] = None, asd_data: Optional[dict[str, Any]] = None) -> None:
        """
        Generate markdown report from analysis data.

        Args:
            data: Analysis or baseline dict with summary, findings, recommendations.
            trends: Optional trending markdown to append to report.
            asd_data: Optional ASD framework data for Essential Eight and ISM controls.
        """
        report = self._build_report(data, trends=trends, asd_data=asd_data)
        filename = self._output_dir / f"{datetime.now().strftime('%Y-%m-%d')}_security_report.md"
        with filename.open("w") as f:
            f.write(report)
        logger.info(f"Report written to {filename}")

    def _build_report(self, data: dict[str, Any], trends: Optional[str] = None, asd_data: dict[str, Any] = None) -> str:
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

        # ASD Framework section
        if asd_data:
            lines.extend([
                "",
                _render_asd_section(asd_data),
            ])

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
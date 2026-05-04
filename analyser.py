"""
analyser.py — LLM-based security alert analysis via OpenAI-compatible REST API.
"""

import json
import logging
from pathlib import Path
from typing import Any

from openai import OpenAI
from openai import APIConnectionError, APIStatusError

logger = logging.getLogger(__name__)


def _load_mitre_tactics(path: str) -> list[dict[str, Any]]:
    """Load MITRE tactics from local JSON file."""
    try:
        with Path(path).open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("tactics", [])
    except FileNotFoundError:
        logger.warning(f"MITRE tactics file not found: {path}")
        return []


def _build_mitre_reference(tactics: list[dict[str, Any]]) -> str:
    """Build compact MITRE tactic reference for prompt."""
    parts = []
    for tactic in tactics:
        name = tactic.get("name", "Unknown")
        shortname = tactic.get("shortname", "")
        if shortname:
            parts.append(f"{name} ({shortname})")
        else:
            parts.append(name)
    return ", ".join(parts)


def analyse(alerts: list[dict[str, Any]], baseline: dict[str, Any], llm_config: dict[str, Any], mitre_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Analyse security alerts using a remote LLM server.

    Args:
        alerts: List of alert dicts from wazuh_client.fetch_alerts()
        baseline: Previous baseline data from baseline.Manager.load()
        llm_config: LLM config section with base_url, api_key, model, etc.
        mitre_config: MITRE ATT&CK config section with path and sync_source (optional)

    Returns:
        Analysis dict with summary, findings, and recommendations.
    """
    if not alerts:
        logger.info("No alerts to analyse")
        return {"summary": "No alerts", "findings": [], "recommendations": []}

    client = OpenAI(
        base_url=llm_config["base_url"],
        api_key=llm_config["api_key"],
    )

    # Load MITRE ATT&CK tactic reference for prompt context
    mitre_config = mitre_config or {}
    mitre_tactics_path = mitre_config.get("path", "data/mitre_attack.json")
    mitre_data = _load_mitre_tactics(mitre_tactics_path)
    mitre_context = _build_mitre_reference(mitre_data)

    prompt = _build_prompt(alerts, baseline, mitre_context)

    try:
        response = client.chat.completions.create(
            model=llm_config["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=llm_config.get("temperature", 0.3),
            max_tokens=llm_config.get("max_tokens", 1024),
        )
    except APIConnectionError as e:
        logger.error(f"Failed to connect to LLM server: {e}")
        raise
    except APIStatusError as e:
        logger.error(f"LLM server returned error status: {e}")
        raise

    analysis_text = response.choices[0].message.content.strip()
    return _parse_analysis(analysis_text)


def _build_prompt(alerts: list[dict[str, Any]], baseline: dict[str, Any], mitre_context: str = "") -> str:
    """Build prompt with alert summary, baseline context, and MITRE ATT&CK reference."""
    alert_summary = _summarise_alerts(alerts)

    baseline_context = ""
    if baseline.get("findings"):
        baseline_context = f"Previous baseline findings: {', '.join(baseline['findings'][:3])}"

    return f"""You are a security analyst. Analyse these Wazuh alerts and provide findings.

Recent alerts:
{alert_summary}

{baseline_context}

MITRE ATT&CK Tactics: {mitre_context}

Provide your analysis in this format:
<findings>
- Finding 1
- Finding 2
</findings>
<recommendations>
- Recommendation 1
- Recommendation 2
</recommendations>"""


def _summarise_alerts(alerts: list[dict[str, Any]]) -> str:
    """Create a summary of alerts for the LLM."""
    by_rule: dict[str, dict[str, Any]] = {}
    for alert in alerts:
        source = alert.get("_source", {})
        rule = source.get("rule", {}).get("description", "Unknown")
        level = source.get("rule", {}).get("level", 0)
        agent = source.get("agent", {}).get("name", "Unknown")
        if rule not in by_rule:
            by_rule[rule] = {"count": 0, "level": level, "agents": set()}
        by_rule[rule]["count"] += 1
        by_rule[rule]["agents"].add(agent)

    lines = [
        f"- {rule}: {d['count']} alerts (level {d['level']}, agents: {', '.join(d['agents'])})"
        for rule, d in by_rule.items()
    ]
    return "\n".join(lines)


def extract_rule_counts(alerts: list[dict[str, Any]]) -> dict[str, int]:
    """
    Extract per-rule-group alert counts from raw alerts.

    Args:
        alerts: List of alert dicts from wazuh_client.fetch_alerts()

    Returns:
        Dict mapping rule description to alert count.
    """
    rule_counts: dict[str, int] = {}
    for alert in alerts:
        source = alert.get("_source", {})
        rule = source.get("rule", {})
        description = rule.get("description", "Unknown")
        rule_counts[description] = rule_counts.get(description, 0) + 1
    return rule_counts


def _parse_analysis(text: str) -> dict[str, Any]:
    """Parse LLM response into structured dict."""
    findings: list[str] = []
    recommendations: list[str] = []

    current_section: str | None = None
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("<findings>"):
            current_section = "findings"
        elif line.startswith("</findings>"):
            current_section = None
        elif line.startswith("<recommendations>"):
            current_section = "recommendations"
        elif line.startswith("</recommendations>"):
            current_section = None
        elif line.startswith("- ") and current_section == "findings":
            findings.append(line[2:])
        elif line.startswith("- ") and current_section == "recommendations":
            recommendations.append(line[2:])

    return {
        "summary": text[:200] + "..." if len(text) > 200 else text,
        "findings": findings,
        "recommendations": recommendations,
    }
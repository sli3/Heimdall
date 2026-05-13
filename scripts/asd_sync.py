"""
asd_sync.py — Fetch ASD ISM OSCAL catalog and combine with Essential Eight dataset.

Usage:
    python scripts/asd_sync.py [--output data/asd_framework.json] [--categories ...]
"""

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("data/asd_framework.json")
DEFAULT_CATEGORIES = [
    "Access Control",
    "System Monitoring",
    "Patch Management",
    "Incident Response",
    "Network Management",
    "System Hardening",
    "Authentication",
    "Logging",
]

ISM_CATALOG_URL = "https://www.cyber.gov.au/ism/oscal/latest-version/artifacts/ISM_catalog.json"


# Essential Eight dataset: 8 strategies × 4 maturity levels = 32 entries
ESSENTIAL_EIGHT_DATA: list[dict[str, Any]] = [
    # Strategy 1: Patch Applications
    {
        "strategy": "Patch Applications",
        "maturity_level": 1,
        "description": "Identify applications requiring patches through vendor notifications and IT asset management.",
    },
    {
        "strategy": "Patch Applications",
        "maturity_level": 2,
        "description": "Automate patch identification and testing in a controlled environment before deployment.",
    },
    {
        "strategy": "Patch Applications",
        "maturity_level": 3,
        "description": "Implement automated patch management with defined timelines and exception handling processes.",
    },
    {
        "strategy": "Patch Applications",
        "maturity_level": 4,
        "description": "Fully enforce patch compliance across all systems with continuous verification and reporting.",
    },
    # Strategy 2: Patch Operating Systems
    {
        "strategy": "Patch Operating Systems",
        "maturity_level": 1,
        "description": "Identify operating systems requiring patches through vendor notifications and asset inventory.",
    },
    {
        "strategy": "Patch Operating Systems",
        "maturity_level": 2,
        "description": "Automate patch identification and testing for operating systems in a controlled environment.",
    },
    {
        "strategy": "Patch Operating Systems",
        "maturity_level": 3,
        "description": "Implement automated OS patch management with defined timelines and security exception approval process.",
    },
    {
        "strategy": "Patch Operating Systems",
        "maturity_level": 4,
        "description": "Fully enforce OS patch compliance across all systems with continuous monitoring and verification.",
    },
    # Strategy 3: Multi-Factor Authentication
    {
        "strategy": "Multi-Factor Authentication",
        "maturity_level": 1,
        "description": "Implement multi-factor authentication for remote access to critical systems.",
    },
    {
        "strategy": "Multi-Factor Authentication",
        "maturity_level": 2,
        "description": "Extend MFA to all remote access solutions and cloud-based applications.",
    },
    {
        "strategy": "Multi-Factor Authentication",
        "maturity_level": 3,
        "description": "Implement phishing-resistant authentication methods and enforce MFA for all privileged accounts.",
    },
    {
        "strategy": "Multi-Factor Authentication",
        "maturity_level": 4,
        "description": "Enforce hardware-based or biometric MFA across all access vectors with continuous compliance monitoring.",
    },
    # Strategy 4: Restrict Administrative Privileges
    {
        "strategy": "Restrict Administrative Privileges",
        "maturity_level": 1,
        "description": "Identify accounts with administrative privileges and document justification.",
    },
    {
        "strategy": "Restrict Administrative Privileges",
        "maturity_level": 2,
        "description": "Document and review administrative accounts regularly; limit local administrator accounts.",
    },
    {
        "strategy": "Restrict Administrative Privileges",
        "maturity_level": 3,
        "description": "Implement least privilege access with automated monitoring of privilege escalation attempts.",
    },
    {
        "strategy": "Restrict Administrative Privileges",
        "maturity_level": 4,
        "description": "Enforce least privilege across all systems with continuous monitoring and automated remediation.",
    },
    # Strategy 5: Application Control
    {
        "strategy": "Application Control",
        "maturity_level": 1,
        "description": "Identify devices requiring application control and whitelist approved applications.",
    },
    {
        "strategy": "Application Control",
        "maturity_level": 2,
        "description": "Implement application whitelisting on all devices with defined approval process.",
    },
    {
        "strategy": "Application Control",
        "maturity_level": 3,
        "description": "Enforce application control across all endpoints with automated enforcement and exception management.",
    },
    {
        "strategy": "Application Control",
        "maturity_level": 4,
        "description": "Fully enforce application control with continuous monitoring and zero-trust architecture integration.",
    },
    # Strategy 6: Restrict Microsoft Office Macros
    {
        "strategy": "Restrict Microsoft Office Macros",
        "maturity_level": 1,
        "description": "Disable macros in Microsoft Office by default on all devices.",
    },
    {
        "strategy": "Restrict Microsoft Office Macros",
        "maturity_level": 2,
        "description": "Block all macros except digitally signed ones; document business justification for exceptions.",
    },
    {
        "strategy": "Restrict Microsoft Office Macros",
        "maturity_level": 3,
        "description": "Implement strict macro policies with automated detection and blocking of unsigned macros.",
    },
    {
        "strategy": "Restrict Microsoft Office Macros",
        "maturity_level": 4,
        "description": "Enforce zero-trust macro execution policies with continuous monitoring and threat intelligence integration.",
    },
    # Strategy 7: User Application Hardening
    {
        "strategy": "User Application Hardening",
        "maturity_level": 1,
        "description": "Configure web browsers to disable unnecessary features and plugins.",
    },
    {
        "strategy": "User Application Hardening",
        "maturity_level": 2,
        "description": "Implement browser hardening standards across all devices with regular configuration reviews.",
    },
    {
        "strategy": "User Application Hardening",
        "maturity_level": 3,
        "description": "Enforce hardened browser configurations with automated compliance checking and exception management.",
    },
    {
        "strategy": "User Application Hardening",
        "maturity_level": 4,
        "description": "Fully enforce application hardening across all platforms with continuous monitoring and threat-based adjustments.",
    },
    # Strategy 8: Regular Backups
    {
        "strategy": "Regular Backups",
        "maturity_level": 1,
        "description": "Implement regular backups of critical data with documented retention policies.",
    },
    {
        "strategy": "Regular Backups",
        "maturity_level": 2,
        "description": "Test backup restoration procedures regularly and store copies in off-site locations.",
    },
    {
        "strategy": "Regular Backups",
        "maturity_level": 3,
        "description": "Implement automated backups with immutability features and regular integrity verification.",
    },
    {
        "strategy": "Regular Backups",
        "maturity_level": 4,
        "description": "Maintain immutable, air-gapped backups with continuous monitoring and disaster recovery testing.",
    },
]


def fetch_ism_catalog() -> dict[str, Any]:
    """
    Fetch the ASD ISM OSCAL catalog from the official source.

    Returns:
        Parsed JSON catalog data.

    Raises:
        requests.RequestException: If fetch fails after retries.
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(ISM_CATALOG_URL, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                raise
            logger.info(f"Retrying in 30 seconds...")
            time.sleep(30)


def walk_control_tree(obj: Any, category: str = "") -> list[dict[str, Any]]:
    """
    Recursively walk the OSCAL catalog groups and extract controls.

    Args:
        obj: Group/control dictionary or list from the catalog.
        category: The top-level group title for categorizing controls.

    Returns:
        List of dictionaries with control id, category, and description.
    """
    results: list[dict[str, Any]] = []

    if isinstance(obj, list):
        for item in obj:
            results.extend(walk_control_tree(item, category))
        return results

    if not isinstance(obj, dict):
        return results

    title = obj.get("title", "")
    if title:
        current_category = title
    else:
        current_category = category

    # Recursively process nested groups
    nested_groups = obj.get("groups", [])
    if nested_groups:
        nested_results = walk_control_tree(nested_groups, current_category)
        results.extend(nested_results)

    # Process controls at this level
    controls = obj.get("controls", [])
    for control in controls:
        control_id = str(control.get("id", ""))
        if not control_id:
            continue

        description = extract_control_description(control)
        results.append({
            "id": control_id.upper().replace("-", "-"),
            "category": current_category,
            "description": description,
        })

    return results


def extract_control_description(control: dict[str, Any]) -> str:
    """
    Extract the prose description from a control's statement part.

    Args:
        control: Control dictionary from OSCAL catalog.

    Returns:
        Prose text from statement or control title as fallback.
    """
    parts = control.get("parts", [])
    for part in parts:
        if part.get("name") == "statement":
            prose = part.get("prose", "")
            if prose:
                return prose

    # Fallback to control title
    title = control.get("title", "")
    if title:
        return title

    return ""


def filter_controls_by_category(
    controls: list[dict[str, Any]], categories: list[str]
) -> list[dict[str, Any]]:
    """
    Filter controls to include only those matching category keywords.

    Args:
        controls: List of all extracted controls.
        categories: List of category keywords for matching.

    Returns:
        Filtered list of controls.
    """
    filtered = []
    category_patterns = [cat.lower() for cat in categories]

    for control in controls:
        category = control["category"].lower()
        if any(pattern in category for pattern in category_patterns):
            filtered.append(control)

    return filtered


def save_output(data: dict[str, Any], output_path: Path) -> None:
    """
    Save combined data to JSON file.

    Args:
        data: Combined Essential Eight and ISM data dictionary.
        output_path: Destination file path.
    """
    with output_path.open("w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Output written to {output_path}")


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Sync ASD ISM OSCAL catalog with Essential Eight dataset."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help=f"Output file path (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--categories",
        nargs="*",
        default=DEFAULT_CATEGORIES,
        help=f"Category keywords for filtering (default: {', '.join(DEFAULT_CATEGORIES)})",
    )

    args = parser.parse_args()

    output_path = Path(args.output)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        logger.info(f"Fetching ISM catalog from {ISM_CATALOG_URL}")
        catalog = fetch_ism_catalog()

        logger.info("Walking control tree...")
        all_controls = walk_control_tree(
            catalog.get("catalog", {}).get("groups", []),
            category="",
        )
        total_controls = len(all_controls)

        logger.info(f"Filtering controls by category keywords...")
        filtered_controls = filter_controls_by_category(all_controls, args.categories)
        ism_controls = filtered_controls

        logger.info(
            f"Found {len(ism_controls)} matching ISM controls "
            f"(filtered from {total_controls} total)"
        )

        output_data = {
            "generated_at": iso_timestamp(),
            "ism_source": ISM_CATALOG_URL,
            "essential_eight": ESSENTIAL_EIGHT_DATA,
            "ism": ism_controls,
        }

        save_output(output_data, output_path)

        ee_count = len(ESSENTIAL_EIGHT_DATA)
        logger.info(
            f"Essential Eight entries: {ee_count}\n"
            f"ISM controls fetched:    {len(ism_controls)} (filtered from {total_controls} total)\n"
            f"Output written to:       {output_path}"
        )

    except requests.RequestException as e:
        logger.error(f"Failed to fetch ISM catalog: {e}")
        raise
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise


def iso_timestamp() -> str:
    """Generate ISO 8601 timestamp for output."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


__all__ = [
    "main",
    "fetch_ism_catalog",
    "walk_control_tree",
    "extract_control_description",
    "filter_controls_by_category",
]


if __name__ == "__main__":
    main()

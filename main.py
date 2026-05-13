"""
main.py — Heimdall Security Log Analyser entry point.
"""
import argparse
import logging
import sys
import tomllib
from pathlib import Path

from tqdm import tqdm
from heimdall import wazuh_client, analyser, reporter, baseline, trending, e8_scorer, embedder as embedder_module

logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for Heimdall."""
    parser = argparse.ArgumentParser(description="Heimdall Security Log Analyser")
    parser.add_argument("--config", default="config.toml", help="Path to config file")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours")
    parser.add_argument("--agent", type=str, default=None, help="Wazuh agent ID")
    parser.add_argument("--level", type=int, default=7, help="Minimum alert level")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing baseline")
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable tqdm progress bars (e.g. for cron or log redirection)"
    )
    args = parser.parse_args()

    show_progress = not args.no_progress and sys.stdout.isatty()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        with Path(args.config).open("rb") as f:
            config = tomllib.load(f)
    except FileNotFoundError:
        logging.critical(f"Config file not found: {args.config}")
        sys.exit(1)
    except tomllib.TOMLDecodeError as e:
        logging.critical(f"Invalid config file: {e}")
        sys.exit(1)

    # NEW: Load embeddings config section (optional) and instantiate Embedder
    embedder_config = config.get("embeddings") if "embeddings" in config else None
    embedder = embedder_module.Embedder(embedder_config, show_progress=show_progress) if embedder_config else None

    for section in ("wazuh", "llm", "reports", "baseline"):
        if section not in config:
            logging.critical(f"Missing required config section: [{section}]")
            sys.exit(1)

    # Pass embedder to baseline.Manager constructor  
    baseline_mgr = baseline.Manager(config["baseline"], embedder=embedder)
    wazuh = wazuh_client.Client(config["wazuh"], show_progress=show_progress)

    # NEW: Migrate baseline embeddings on first run (before any conditional branches)
    if embedder is not None:
        migrated = embedder.migrate_baseline(baseline_mgr.load())
        if migrated > 0:
            logging.info(f"Migrated {migrated} entries to vector store")

    if args.report_only:
        trends_output = None
        if "trending" in config:
            trend_mgr = trending.Trending(config["trending"])
            trends_output = trend_mgr.generate(baseline_mgr.load())
        
        rep = reporter.Reporter(config["reports"])
        rep.generate(baseline_mgr.load(), trends=trends_output)
        return

    alerts = wazuh.fetch_alerts(hours=args.hours, agent=args.agent, level=args.level)

    mitre_path = config.get("mitre", {}).get("path") if "mitre" in config else None
    asd_path = config.get("asd", {}).get("path") if "asd" in config else None
    platform_hints_path = config.get("platform", {}).get("hints_path") if "platform" in config else None
    analysis = analyser.analyse(alerts, baseline_mgr.load(), config["llm"], embedder=embedder, mitre_path=mitre_path, asd_path=asd_path, platform_hints_path=platform_hints_path, show_progress=show_progress)
    baseline_mgr.update(analysis, rule_counts=analyser.extract_rule_counts(alerts))

    trends_output = None
    if "trending" in config:
        trend_mgr = trending.Trending(config["trending"])
        trends_output = trend_mgr.generate(baseline_mgr.load())

    asd_data = analyser._load_asd_data(asd_path) if asd_path else {}
    overrides_path = config.get("e8", {}).get("overrides_path") if "e8" in config else None
    e8_scores = e8_scorer.score_findings(analysis.get("findings", []), asd_data, overrides_path=overrides_path) if asd_data else {}
    matched_controls = e8_scorer.match_ism_controls(analysis.get("findings", []), asd_data, overrides_path=overrides_path) if asd_data else []
    rep = reporter.Reporter(config["reports"])
    rep.generate(analysis, trends=trends_output, asd_data=asd_data, e8_scores=e8_scores, matched_controls=matched_controls)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(0)
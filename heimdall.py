import argparse
import logging
import sys
import tomllib
from pathlib import Path

import wazuh_client
import analyser
import reporter
import baseline
import trending

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Heimdall Security Log Analyser")
    parser.add_argument("--config", default="config.toml", help="Path to config file")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours")
    parser.add_argument("--agent", type=str, default=None, help="Wazuh agent ID")
    parser.add_argument("--level", type=int, default=7, help="Minimum alert level")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Logging level")
    parser.add_argument("--report-only", action="store_true", help="Generate report from existing baseline")
    args = parser.parse_args()

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

    for section in ("wazuh", "llm", "reports", "baseline"):
        if section not in config:
            logging.critical(f"Missing required config section: [{section}]")
            sys.exit(1)

    baseline_mgr = baseline.Manager(config["baseline"])
    wazuh = wazuh_client.Client(config["wazuh"])

    if args.report_only:
        rep = reporter.Reporter(config["reports"])
        rep.generate(baseline_mgr.load())
        return

    alerts = wazuh.fetch_alerts(hours=args.hours, agent=args.agent, level=args.level)
    analysis = analyser.analyse(alerts, baseline_mgr.load(), config["llm"])
    baseline_mgr.update(analysis, rule_counts=analyser.extract_rule_counts(alerts))

    # Wire up Trending calls after each run
    trends_output = None
    trending_cfg = config.get("trending", {})
    if trending_cfg:
        trend_tracker = trending.Trending(trending_cfg)
        baseline_data = baseline_mgr.load()
        trends_output = trend_tracker.generate(baseline_data)

    rep = reporter.Reporter(config["reports"])
    rep.generate(analysis, trends=trends_output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        sys.exit(0)
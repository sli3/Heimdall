# Heimdall — Wazuh Security Log Analyser

A local-first security log analyser that pulls alerts from the Wazuh REST API,
analyses them using a local LLM (Qwen3 via llama.cpp), and generates structured
markdown security reports with baseline memory tracking and historical trending.

> Named after Heimdall, the Norse watchman — guardian of Bifröst, ever-vigilant
> against threats.

---

## What It Does

- Connects to the **Wazuh Indexer (OpenSearch)** to pull security alerts by time range,
  agent, or severity level
- Analyses alert patterns using a **local Qwen3 8B model** — no data leaves
  your network
- Generates **markdown security reports** summarising threats, anomalies, and
  recommended actions
- Maintains a **baseline memory** of normal behaviour so repeated noise is
  distinguished from genuine alerts
- Tracks **historical alert trends** per rule group — surfaces slow-burn threats
  that single-run baseline comparison misses
- Runs on a local homelab — designed for self-hosted Wazuh deployments

---

## Architecture

```
heimdall.py          # Entry point — CLI and orchestration
wazuh_client.py      # Wazuh Indexer (OpenSearch) REST API client
analyser.py          # LLM analysis via llama.cpp OpenAI-compatible API
reporter.py          # Markdown report generation
baseline.py          # Baseline memory persistence (JSON store)
trending.py          # Historical trend analysis and anomaly detection
```

---

## Requirements

| Dependency | Purpose |
|------------|---------|
| Python 3.11+ | Runtime (tomllib requires 3.11+) |
| `requests` | Wazuh Indexer REST API calls |
| `openai` | llama.cpp OpenAI-compatible client |
| Wazuh 4.x | Alert source (self-hosted) |
| llama.cpp server | Local LLM inference (Qwen3 8B) |

---

## Setup

### 1. Clone the repo

```bash
git clone git@github.com:sli3/Heimdall.git
cd Heimdall
```

### 2. Create a virtual environment

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

Or with standard venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure

Copy the example config and fill in your values:

```bash
cp config.example.toml config.toml
```

| Key | Description |
|-----|-------------|
| `wazuh.host` | Your Wazuh manager hostname or IP |
| `wazuh.port` | Wazuh API port (default: 55000) |
| `wazuh.user` | Wazuh API username |
| `wazuh.password` | Wazuh API password |
| `wazuh.indexer_host` | Wazuh Indexer (OpenSearch) IP — often same as manager |
| `wazuh.indexer_port` | Indexer port (default: 9200) |
| `wazuh.indexer_user` | Indexer username (default: admin) |
| `wazuh.indexer_password` | Indexer password |
| `llm.base_url` | llama.cpp server URL (e.g. `http://yubaba:8080/v1`) |
| `llm.model` | Model ID served by llama.cpp (e.g. `Qwen3`) |
| `llm.api_key` | Any string — llama.cpp does not validate |
| `reports.output_dir` | Where to write markdown reports |
| `baseline.path` | Path to the baseline JSON file |

> **Note:** The Wazuh Indexer must be accessible on port 9200 from the machine
> running Heimdall. If your indexer is bound to localhost only, update
> `network.host` in `/etc/wazuh-indexer/opensearch.yml` to `0.0.0.0` and
> restart the indexer service.

### 4. Run

```bash
python heimdall.py --hours 24
```

---

## Usage

```
usage: heimdall.py [-h] [--config CONFIG] [--hours N] [--agent AGENT]
                   [--level LEVEL] [--log-level LEVEL] [--report-only]

options:
  --config PATH    Path to config file (default: config.toml)
  --hours N        Analyse alerts from the last N hours (default: 24)
  --agent AGENT    Filter to a specific agent name or ID
  --level LEVEL    Minimum alert level to include (default: 7)
  --log-level      Logging verbosity: DEBUG, INFO, WARNING, ERROR (default: INFO)
  --report-only    Generate report from last baseline without re-querying Wazuh
```

### Example output

```
2026-05-02 18:18:00 - INFO - Fetched 9984 alerts from Wazuh Indexer
2026-05-02 18:18:00 - INFO - Updated baseline with 2 findings
2026-05-02 18:18:01 - INFO - Report written to reports/2026-05-02_security_report.md
```

---

## Reports

Reports are saved to the `reports/` directory as markdown files, named by date.
Each report contains:

- **Summary** — overall threat posture for the period
- **Findings** — LLM-identified threats and patterns grouped by rule group
- **Recommendations** — LLM-generated response suggestions

---

## Baseline Memory

Heimdall tracks a baseline of findings and recommendations from previous runs.
On each run, the current analysis updates the baseline. The `--report-only` flag
generates a report from the last saved baseline without querying Wazuh or the LLM.

The baseline is stored as a JSON file at the path configured in `config.toml`.

---

## Historical Trending

`trending.py` tracks per-rule-group alert volumes across runs and detects
slow-burn threats that single-run baseline comparison misses.

- Each run appends a timestamped snapshot of rule group counts to the scan history
- `trending.py` reads the history over a configurable rolling window (default 30 days)
- Rule groups with consistently increasing counts across 3+ consecutive runs are
  flagged as anomalies with a ⚠️ marker
- Output is a markdown table embedded in the main report or written as a
  standalone `reports/trending_YYYY-MM-DD.md`

> **Note:** Historical Trending is implemented but not yet wired into the main
> pipeline. `baseline.py` scan history schema extension and `heimdall.py`
> integration are in progress.

---

## Roadmap

| Feature | Status | Notes |
|---------|--------|-------|
| Historical Trending | 🔧 In progress | `trending.py` written — baseline schema extension and wiring pending |
| MITRE ATT&CK Tagging | 📋 Planned | `mitre_sync.py` + prompt injection — fully offline after initial sync |
| Multi-Model Routing | 📋 Planned | Two-pass pipeline — Qwen2.5-Coder triage → Qwen3 deep analysis (sequential, 12GB VRAM constraint) |

Full design notes for each feature are in [`docs/HEIMDALL_ROADMAP.md`](docs/HEIMDALL_ROADMAP.md).

---

## Inference Server

Heimdall is designed to run against a dedicated local llama.cpp inference node
running Qwen3 8B. All LLM calls are made over the local LAN via the
OpenAI-compatible REST API. No data is sent to any cloud service.

See [`docs/yubaba-server-reference.md`](docs/yubaba-server-reference.md) for
the full server specification (gitignored — contains local network details).

---

## Development Workflow

This project uses the [Huginn](https://github.com/sli3/Huginn) OpenCode workflow
template — structured sessions, safety gates, and session memos.

```
Heimdall/
├── heimdall.py
├── wazuh_client.py
├── analyser.py
├── reporter.py
├── baseline.py
├── trending.py
├── config.example.toml
├── requirements.txt
├── docs/
│   └── HEIMDALL_ROADMAP.md
├── AGENTS.md
├── opencode.json
├── .gitignore
├── .session-memos/          # Gitignored working notes
└── .opencode/
    └── skills/
```

---

## Licence

MIT — see [LICENSE](LICENSE)
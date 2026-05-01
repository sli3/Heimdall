# Heimdall — Wazuh Security Log Analyser

A local-first security log analyser that pulls alerts from the Wazuh REST API,
analyses them using a local LLM (Qwen3 via llama.cpp), and generates structured
markdown security reports with baseline memory tracking.

> Named after Heimdall, the Norse watchman — guardian of Bifröst, ever-vigilant
> against threats.

---

## What It Does

- Connects to the **Wazuh REST API** to pull security alerts by time range,
  agent, or severity level
- Analyses alert patterns using a **local Qwen3 8B model** — no data leaves
  your network
- Generates **markdown security reports** summarising threats, anomalies, and
  recommended actions
- Maintains a **baseline memory** of normal behaviour so repeated noise is
  distinguished from genuine alerts
- Runs on a local homelab — designed for self-hosted Wazuh deployments

---

## Architecture

```
heimdall.py          # Entry point — CLI and orchestration
wazuh_client.py      # Wazuh REST API client (auth, alert fetch, pagination)
analyser.py          # LLM analysis via llama.cpp OpenAI-compatible API
reporter.py          # Markdown report generation
baseline.py          # Baseline memory persistence (JSON store)
```

---

## Requirements

| Dependency | Purpose |
|------------|---------|
| Python 3.11+ | Runtime |
| `requests` | Wazuh REST API calls |
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
| `llm.base_url` | llama.cpp server URL (e.g. `http://yubaba:8080/v1`) |
| `llm.model` | Model ID served by llama.cpp (e.g. `Qwen3`) |
| `llm.api_key` | Any string — llama.cpp does not validate |
| `reports.output_dir` | Where to write markdown reports |
| `baseline.store_path` | Path to the baseline JSON file |

### 4. Run

```bash
python heimdall.py --hours 24
```

---

## Usage

```
usage: heimdall.py [-h] [--hours N] [--agent AGENT] [--level LEVEL] [--report-only]

options:
  --hours N        Analyse alerts from the last N hours (default: 24)
  --agent AGENT    Filter to a specific agent name or ID
  --level LEVEL    Minimum alert level to include (default: 7)
  --report-only    Generate report from last fetch without re-querying Wazuh
```

### Example output

```
[2026-04-24 08:15] Fetching alerts from Wazuh (last 24h, level ≥ 7)...
[2026-04-24 08:15] 342 alerts retrieved — 18 above baseline threshold
[2026-04-24 08:16] LLM analysis complete
[2026-04-24 08:16] Report written to reports/2026-04-24_security_report.md
```

---

## Reports

Reports are saved to the `reports/` directory as markdown files, named by date.
Each report contains:

- **Executive summary** — overall threat posture for the period
- **Alert breakdown** — grouped by rule group and severity
- **Anomalies** — alerts that deviate from the established baseline
- **Top offenders** — most active source IPs and agents
- **Recommended actions** — LLM-generated response suggestions

---

## Baseline Memory

Heimdall tracks a rolling baseline of normal alert volumes per rule group. On
each run, the current counts are compared to the baseline. Alerts in categories
that are significantly above their normal rate are flagged as anomalies in the
report. The baseline is stored as a JSON file and updated after each run.

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
├── config.example.toml
├── requirements.txt
├── AGENTS.md                    # OpenCode agent instructions
├── opencode.json                # OpenCode config (local model + MCP)
├── .gitignore
├── .session-memos/              # Gitignored working notes
└── .opencode/
    └── skills/                  # Huginn skills (preflight, memo, git, etc.)
```

---

## Inference Server

Heimdall is designed to run against [yubaba](docs/yubaba-server-reference.md) —
a dedicated local llama.cpp inference node running Qwen3 8B. All LLM calls are
made over the local LAN. No data is sent to any cloud service.

---

## Licence

MIT — see [LICENSE](LICENSE)

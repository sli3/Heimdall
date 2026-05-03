# Heimdall — Feature Roadmap

> This document captures planned features to be built after the base project is complete.
> Hand this back to Claude at the start of a planning session to resume from here.

---

## Base Project Status

The base project is complete when the following modules are working end-to-end:

- `heimdall.py` — entry point and orchestration
- `wazuh_client.py` — Wazuh REST API auth and alert fetch
- `analyser.py` — LLM analysis via Qwen3 on the local inference server
- `reporter.py` — markdown report generation
- `baseline.py` — baseline memory persistence (JSON store)

---

## Planned Features

---

### 1. Multi-Model Routing

**What it does:**
Two-pass analysis pipeline using both models on the local inference server — fast triage first, deep analysis only on flagged clusters.

**How it works:**
- Pass 1: Qwen2.5-Coder (fast, lower overhead) triages all alerts — classifies severity, filters noise, scores clusters
- Pass 2: Qwen3 (deeper reasoning) receives only clusters that cross a severity threshold for contextual threat assessment
- Models run strictly sequentially — one finishes completely before the other starts
- llama.cpp router mode handles model switching via model ID in the API call

**Hardware constraint:**
The inference server has 12GB VRAM. Qwen2.5-Coder sits at ~5.9GB and Qwen3 at ~5.7GB — they cannot co-exist in VRAM simultaneously. Sequential is the only viable approach.

**Key design decision:**
Threshold rule for routing must be explicit and configurable (e.g. in `config.toml`) — not hardcoded logic.

**New files/changes:**
- `analyser.py` — add `triage_alerts()` function for Pass 1, update `analyse_clusters()` for Pass 2
- `config.toml` — add `[routing]` section with severity threshold and model IDs for each pass

---

### 2. MITRE ATT&CK Tagging

**What it does:**
Maps alert clusters to MITRE ATT&CK tactics and techniques, making reports more actionable and giving a standard vocabulary for describing threats.

**How it works:**
- A separate `mitre_sync.py` script fetches the latest ATT&CK dataset from MITRE's official source and saves it locally
- Data source: `github.com/mitre-attack/attack-stix-data` (STIX 2.1 format, Enterprise ATT&CK)
- `mitre_sync.py` parses the STIX data and saves a simplified local lookup file (e.g. `data/mitre_attack.json`)
- At analysis time, `analyser.py` reads the local file and includes relevant tactic/technique definitions in the LLM prompt context
- The LLM maps alert clusters to ATT&CK tactics (e.g. Initial Access, Discovery, Lateral Movement, Exfiltration)

**Key design decisions:**
- No live fetching during report runs — always reads from local file
- `mitre_sync.py` run manually or via cron (weekly recommended) before report runs
- Fully offline capable after initial sync — no external dependency during analysis
- Need to evaluate whether Qwen3 8B has sufficient ATT&CK knowledge or requires tactic definitions injected into prompt

**New files/changes:**
- `mitre_sync.py` — new standalone sync script
- `data/mitre_attack.json` — local ATT&CK lookup (gitignored if large)
- `analyser.py` — update prompt builder to include ATT&CK context
- `reporter.py` — add ATT&CK tags to report output sections
- `config.toml` — add `[mitre]` section with local data path and sync source URL

---

### 3. Historical Trending

**What it does:**
Visualises alert volume patterns over time — week-on-week per rule group — to surface slow-burn threats that single-run baseline comparison misses.

**How it works:**
- Builds on existing `baseline_state.json` which already stores per-rule-group counts and scan history per run
- Each run appends a timestamped snapshot to the scan history
- A new `trending.py` module reads the history and produces either:
  - A markdown summary table in the report (alert volumes per rule group, last 7/30 days)
  - A separate `reports/trending_YYYY-MM-DD.md` document on demand
- Anomaly detection: flags rule groups where volume is trending up over multiple consecutive runs, not just spiking once

**Key design decisions:**
- No new data store needed — extends existing `baseline_state.json` schema
- Rolling window configurable (default 30 days) — already exists as `rolling_window_days` in baseline
- Keep it simple: markdown tables first, no charting libraries

**New files/changes:**
- `trending.py` — new module for trend calculation and output
- `baseline.py` — extend scan history schema to store per-rule-group counts per run (not just totals)
- `reporter.py` — optionally embed trending summary in main report
- `config.toml` — add `[trending]` section with window size and output preferences

---

### 4. Embedding Model — Semantic Memory & Alert Retrieval

**What it does:**
Replaces the flat `baseline_state.json` memory with a vector store of embedded historical alerts. At analysis time, retrieves only the semantically closest past incidents and feeds them as context to Qwen3 — finding similar past attacks by meaning, not keyword matching.

**The problem it solves:**
The current baseline summarises everything into a flat JSON. As history grows, the prompt context fills with irrelevant past runs. Two incidents can describe the same attack pattern using completely different words — keyword matching misses them entirely. Semantic search solves both problems.

**How it works:**
- A dedicated local embedding model (see model choice below) encodes each alert cluster into a vector at the end of every run
- Vectors are stored in a local vector store (see store choice below) alongside metadata (timestamp, rule group, severity, raw summary)
- At analysis time, the current alert clusters are embedded and the top-N most similar past incidents are retrieved by cosine similarity
- Retrieved incidents are injected into the Qwen3 prompt as structured context: "Similar past incidents: ..."
- `baseline.py` is extended to manage both the existing JSON store and the new vector store

**Model choice — Qwen3-Embedding-0.6B (recommended):**
- ~0.5GB VRAM — can co-exist with Qwen3-8B (~5.7GB) simultaneously within 12GB
- This is the first feature that does NOT require sequential model switching
- Served via a second llama.cpp instance on port 8081, using the `/v1/embeddings` endpoint
- Qwen3-Embedding-4B (~2.5GB) is an alternative if retrieval quality needs improving — still fits with Qwen3-8B at ~8.2GB combined

**Vector store choice — ChromaDB (recommended):**
- Pure Python, no separate server process needed
- Persistent SQLite backend — single file, fits the existing local-first philosophy
- Simple API: `collection.add()`, `collection.query()`
- Handles metadata filtering natively (e.g. filter by date range or rule group)
- Alternative: `sqlite-vec` (even lighter, SQLite extension) — viable if ChromaDB feels heavy
- Avoid: Pinecone (cloud), FAISS (C++ deps, overkill), numpy flat file (no persistence or indexing)

**Key design decisions:**
- Embedding model runs on a second llama.cpp instance (port 8081) — keeps routing clean and avoids endpoint conflicts with the main inference server
- Migration path needed: existing `baseline_state.json` entries should be embedded on first run and loaded into ChromaDB so history is not lost
- Retrieval window is configurable — default top-5 most similar past incidents injected as context
- Both stores (JSON baseline and vector store) run in parallel initially — JSON baseline is not removed until vector retrieval is proven stable
- Evaluate whether 0.6B embedding quality is sufficient before considering 4B upgrade

**New files/changes:**
- `embedder.py` — new module: connects to llama.cpp embeddings endpoint, encodes alert clusters, manages ChromaDB collection
- `baseline.py` — extend to write embeddings on update, add `retrieve_similar()` method
- `analyser.py` — update `_build_prompt()` to call `baseline.retrieve_similar()` and inject retrieved context
- `config.toml` — add `[embeddings]` section with model ID, endpoint port, ChromaDB path, top-N retrieval count
- `requirements.txt` — add `chromadb`
- `data/chromadb/` — vector store directory (gitignored)

---

## Suggested Build Order

1. **Historical Trending** — lowest risk, extends existing code, no new external dependencies
2. **MITRE ATT&CK Tagging** — adds `mitre_sync.py` as a standalone tool, then integrates into analyser
3. **Multi-Model Routing** — invasive change to the analysis pipeline
4. **Embedding Model** — most architectural change; replaces core memory layer last when everything else is stable

---

## Infrastructure Reference

| Item | Detail |
|------|--------|
| Inference server | `<inference-server>` (llama.cpp, OpenAI-compatible API) |
| API endpoint (main) | `http://<inference-server-ip>:8080/v1` |
| API endpoint (embeddings) | `http://<inference-server-ip>:8081/v1` |
| Model — triage | `Qwen2.5-Coder` (~5.9GB VRAM) |
| Model — analysis | `Qwen3` (~5.7GB VRAM) |
| Model — embeddings | `Qwen3-Embedding-0.6B` (~0.5GB VRAM) |
| VRAM total | 12GB (RTX 3060) |
| Co-load viable | Qwen3 + Embedding-0.6B only (~6.2GB combined) |
| Sequential only | Qwen3 ↔ Qwen2.5-Coder (too large to co-load) |
| Router mode | Enabled in llama.cpp via `model.ini` |
| Vector store | ChromaDB (local SQLite backend) |

---

*Created: 2026-05-01 — last updated: 2026-05-03*
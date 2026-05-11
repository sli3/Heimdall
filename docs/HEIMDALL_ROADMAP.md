# Heimdall — Feature Roadmap

> This document captures planned features to be built after the base project is complete.
> Hand this back to Claude at the start of a planning session to resume from here.

---

## Base Project Status

The base project is complete. All modules are working end-to-end:

- `main.py` — entry point and orchestration
- `heimdall/wazuh_client.py` — Wazuh Indexer (OpenSearch) REST API client
- `heimdall/analyser.py` — LLM analysis via Qwen3.6-35B on the local inference server
- `heimdall/reporter.py` — markdown report generation
- `heimdall/baseline.py` — baseline memory persistence (JSON store)
- `heimdall/trending.py` — historical trend analysis and anomaly detection
- `scripts/mitre_sync.py` — MITRE ATT&CK STIX data sync script

---

## Feature Status

| Feature | Status | Notes |
|---------|--------|-------|
| Historical Trending | ✅ Complete | `trending.py` wired into main pipeline |
| MITRE ATT&CK Tagging | ✅ Complete | Tactic reference injected into LLM prompt, tags in report |
| Multi-Model Routing | ~~Superseded~~ | See note below |
| Embedding Model | 🔄 Validation | All 5 sessions complete — awaiting run 2 to confirm retrieval |

---

## Planned Features

---

### 1. Multi-Model Routing — Superseded

**Status:** Not building — superseded by Qwen3.6-35B-A3B MoE model.

**Reason:** The original design assumed a single 8B model insufficient for deep
analysis, requiring a two-pass triage approach. Qwen3.6-35B running via CPU-MoE
offload produces significantly better single-pass analysis than the proposed
two-pass pipeline, without the added complexity. The VRAM constraints that made
sequential routing necessary no longer apply with MoE expert offload to RAM.

---

### 2. MITRE ATT&CK Tagging — Complete ✅

**What was built:**
- `mitre_sync.py` — standalone script fetching Enterprise ATT&CK STIX 2.1 bundle
- `data/mitre_attack.json` — local lookup file (15 tactics, 365 techniques, 493 subtechniques)
- `analyser.py` — compact tactic reference injected into LLM prompt
- `reporter.py` — MITRE ATT&CK Tags table in report output
- `config.example.toml` — `[mitre]` section with path and sync_source

---

### 3. Historical Trending — Complete ✅

**What was built:**
- `trending.py` — trend calculation per rule group, anomaly detection
- `baseline.py` — extended with `scan_history` schema
- `main.py` — trending wired into main pipeline
- `reporter.py` — Historical Trends table embedded in report
- `config.example.toml` — `[trending]` section

---

### 4. Embedding Model — Semantic Memory & Alert Retrieval

**What it does:**
Replaces the flat `baseline_state.json` memory with a vector store of embedded
historical alerts. At analysis time, retrieves only the semantically closest past
incidents and feeds them as context to the LLM — finding similar past attacks by
meaning, not keyword matching.

**The problem it solves:**
The current baseline summarises everything into a flat JSON. As history grows,
the prompt context fills with irrelevant past runs. Two incidents can describe the
same attack pattern using completely different words — keyword matching misses them
entirely. Semantic search solves both problems.

**How it works:**
- A dedicated local embedding model encodes each alert cluster into a vector at
  the end of every run
- Vectors are stored in a local vector store alongside metadata (timestamp, rule
  group, severity, raw summary)
- At analysis time, the current alert clusters are embedded and the top-N most
  similar past incidents are retrieved by cosine similarity
- Retrieved incidents are injected into the LLM prompt as structured context:
  "Similar past incidents: ..."
- `baseline.py` is extended to manage both the existing JSON store and the new
  vector store

**Model choice — Qwen3-Embedding-0.6B (recommended):**
- ~0.5GB VRAM — can co-exist with Qwen3.6-35B MoE model simultaneously
- Served via a second llama.cpp instance on port 8081, using the `/v1/embeddings`
  endpoint
- Qwen3-Embedding-4B (~2.5GB) is an alternative if retrieval quality needs
  improving

**Vector store choice — ChromaDB (recommended):**
- Pure Python, no separate server process needed
- Persistent SQLite backend — single file, fits the existing local-first philosophy
- Simple API: `collection.add()`, `collection.query()`
- Handles metadata filtering natively (e.g. filter by date range or rule group)
- Alternative: `sqlite-vec` (even lighter, SQLite extension)

**Key design decisions:**
- Embedding model runs on a second llama.cpp instance (port 8081)
- Migration path needed: existing `baseline_state.json` entries should be embedded
  on first run and loaded into ChromaDB so history is not lost
- Retrieval window is configurable — default top-5 most similar past incidents
- Both stores (JSON baseline and vector store) run in parallel initially — JSON
  baseline is not removed until vector retrieval is proven stable
- Evaluate whether 0.6B embedding quality is sufficient before considering 4B upgrade

---

**Implementation Sessions:**

- **Session 1 — embedder.py** ✅ Complete
  - New module: ChromaDB connection, llama.cpp embeddings endpoint, `add_embedding()` and `query_similar()` methods
  - Out of scope: all other files

- **Session 2 — baseline.py + config** ✅ Complete
  - Extend `Manager.__init__()` to accept optional `embedder` parameter and store as `self._embedder`
  - Extend `Manager.update()` to call `self._embedder.add_embedding()` when embedder is present
  - Add `[embeddings]` section to `config.example.toml`
  - Add `chromadb` to `requirements.txt`
  - Out of scope: `retrieve_similar()`, `analyser.py`, `main.py`, `embedder.py` (read only)

- **Session 3 — analyser.py** ✅ Complete
  - Update `_build_prompt()` to accept and inject retrieved similar incidents context
  - Add `retrieve_similar()` call before prompt construction
  - Out of scope: `baseline.py`, `main.py`, `embedder.py`

- **Session 4 — main.py wiring** ✅ Complete
  - Instantiate `Embedder` from config
  - Pass embedder instance to `Baseline.Manager` constructor
  - Wire retrieval into the main analysis pipeline
  - Out of scope: any changes to `baseline.py`, `analyser.py`, or `embedder.py`

- **Session 5 — config + requirements final pass** ✅ Complete
  - Verified `config.example.toml` `[embeddings]` section has correct keys
  - Verified `chromadb` present in `requirements.txt`
  - Updated `README.md` — added chromadb to requirements table, port 8081 server entry, `[embeddings]` config keys section
  - ⚠️ **Manual step required:** `config.example.toml` is the template — any new `[embeddings]` section must be manually copied into the live `config.toml` by the user. The agent never touches `config.toml` as it contains credentials.
  - Out of scope: any logic changes

---

**Validation Status:**

- Run 1 completed — alerts embedded into ChromaDB, no retrieval output yet (empty vector store on first run, expected)
- Run 2 required to confirm "Similar past incidents" context appears in LLM prompt and report
- If retrieval output is absent after run 2, check logs for `embed`, `chroma`, `similar`, `retriev` keywords

**Operational Notes:**

- Embedding server (`start-embed`) must be started before running Heimdall
- Use `--ctx-size 512 --n-gpu-layers 0` on the embedding server — keeps VRAM footprint to ~564 MiB
- Do not use `--ub` flag — invalid on current llama.cpp build
- VRAM budget with both servers running: ~8.6GB / 12GB (3.6GB headroom)
- `[embeddings]` section must be present in live `config.toml` — agent only updates `config.example.toml`

---
- `heimdall/embedder.py` — new module: connects to llama.cpp embeddings endpoint, encodes
  alert clusters, manages ChromaDB collection
- `heimdall/baseline.py` — extend to write embeddings on update, add `retrieve_similar()`
- `heimdall/analyser.py` — update `_build_prompt()` to inject retrieved context
- `config.toml` — add `[embeddings]` section with model ID, endpoint port,
  ChromaDB path, top-N retrieval count
- `requirements.txt` — add `chromadb`
- `data/chromadb/` — vector store directory (gitignored)

---

## Suggested Build Order

1. ~~Historical Trending~~ — Complete ✅
2. ~~MITRE ATT&CK Tagging~~ — Complete ✅
3. ~~Multi-Model Routing~~ — Superseded ✅
4. **Embedding Model** — In Progress

---

## Infrastructure Reference

| Item | Detail |
|------|--------|
| Inference server | yubaba (llama.cpp b9037, OpenAI-compatible API) |
| GPU | RTX 3060 12GB VRAM |
| CPU | Intel i7-1260P, 16GB RAM |
| OS | Ubuntu Server 24.04 LTS, NVIDIA driver 580.159.03, CUDA 13.0 |
| API endpoint (main) | `http://<yubaba-ip>:8080/v1` |
| API endpoint (embeddings) | `http://<yubaba-ip>:8081/v1` |
| Model — analysis | `Qwen3.6-35B-A3B` (~2.8GB VRAM, ~7-8GB RAM experts, ~17 t/s) |
| Model — triage (unused) | `Qwen2.5-Coder` (~5.9GB VRAM) |
| Model — embeddings | `Qwen3-Embedding-0.6B` (~0.5GB VRAM) |
| Model — coding (OpenCode) | `Qwen3.5-9B` (~5.5GB VRAM, ~42 t/s) |
| Router mode | Enabled in llama.cpp via `model.ini` |
| MoE offload | `cpu-moe = true` for Qwen3.6-35B and Gemma4-26B |
| Vector store | ChromaDB (local SQLite backend) |

---

*Created: 2026-05-01 — last updated: 2026-05-11*
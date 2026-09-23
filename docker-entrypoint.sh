#!/bin/sh
set -eu

# --- Defaults for optional variables ---
# Required variables (no sane default — checked below) are NOT set here:
# WAZUH_HOST, WAZUH_API_USER, WAZUH_API_PASSWORD, WAZUH_INDEXER_HOST,
# WAZUH_INDEXER_PASSWORD, LLM_BASE_URL, LLM_MODEL, EMBEDDINGS_ENDPOINT
: "${WAZUH_PORT:=55000}"; export WAZUH_PORT
: "${WAZUH_INDEXER_PORT:=9200}"; export WAZUH_INDEXER_PORT
: "${WAZUH_INDEXER_USER:=admin}"; export WAZUH_INDEXER_USER
: "${LLM_API_KEY:=local}"; export LLM_API_KEY
: "${LLM_TEMPERATURE:=0.3}"; export LLM_TEMPERATURE
: "${LLM_MAX_TOKENS:=1024}"; export LLM_MAX_TOKENS
: "${EMBEDDINGS_MODEL:=Qwen3-Embedding-0.6B}"; export EMBEDDINGS_MODEL
: "${EMBEDDINGS_TOP_K:=5}"; export EMBEDDINGS_TOP_K
: "${EMBEDDINGS_CHROMA_HOST:=}"; export EMBEDDINGS_CHROMA_HOST
: "${EMBEDDINGS_CHROMA_PORT:=8000}"; export EMBEDDINGS_CHROMA_PORT
: "${TRENDING_WINDOW_DAYS:=30}"; export TRENDING_WINDOW_DAYS
: "${TRENDING_OUTPUT_STANDALONE:=false}"; export TRENDING_OUTPUT_STANDALONE
: "${RAVENSIGHT_DATA_DIR:=/app/data}"; export RAVENSIGHT_DATA_DIR
: "${RAVENSIGHT_REPORTS_DIR:=/app/reports}"; export RAVENSIGHT_REPORTS_DIR

# --- Required variables: fail fast with a clear message rather than let
# tomllib.load() or main.py fail later with a confusing placeholder value ---
required_vars="WAZUH_HOST WAZUH_API_USER WAZUH_API_PASSWORD WAZUH_INDEXER_HOST WAZUH_INDEXER_PASSWORD LLM_BASE_URL LLM_MODEL EMBEDDINGS_ENDPOINT"
missing=""
for var in $required_vars; do
    eval "value=\${$var:-}"
    if [ -z "$value" ]; then
        missing="$missing $var"
    fi
done
if [ -n "$missing" ]; then
    echo "ERROR: missing required environment variable(s):$missing" >&2
    echo "Set these in your .env file before starting the container." >&2
    exit 1
fi

# --- Substitute the template into a real config.toml ---
python3 -c "
import os
import string

with open('/app/config.template.toml') as f:
    template = string.Template(f.read())

with open('/app/config.toml', 'w') as f:
    f.write(template.substitute(os.environ))
"

mkdir -p "$RAVENSIGHT_DATA_DIR" "$RAVENSIGHT_REPORTS_DIR"

# --- Seed hand-edited default files only if the user hasn't provided their
# own (never overwrite an existing file in the mounted data volume) ---
if [ ! -f "$RAVENSIGHT_DATA_DIR/e8_keyword_overrides.json" ]; then
    cp /app/data/defaults/e8_keyword_overrides.json "$RAVENSIGHT_DATA_DIR/e8_keyword_overrides.json"
fi

if [ ! -f "$RAVENSIGHT_DATA_DIR/platform_hints.json" ]; then
    cp /app/data/defaults/platform_hints.json "$RAVENSIGHT_DATA_DIR/platform_hints.json"
fi

# --- Sync reference data only if missing (not on every start) ---
if [ ! -f "$RAVENSIGHT_DATA_DIR/mitre_attack.json" ]; then
    echo "MITRE ATT&CK data not found — running initial sync..."
    python3 scripts/mitre_sync.py --output "$RAVENSIGHT_DATA_DIR/mitre_attack.json"
fi

if [ ! -f "$RAVENSIGHT_DATA_DIR/asd_framework.json" ]; then
    echo "ASD framework data not found — running initial sync..."
    python3 scripts/asd_sync.py --output "$RAVENSIGHT_DATA_DIR/asd_framework.json"
fi

# --- On-demand forced re-sync: `docker run <image> sync` refreshes both
# reference datasets even if they already exist (e.g. a new MITRE ATT&CK
# or ASD ISM release), bypassing the missing-file check above ---
if [ "${1:-}" = "sync" ]; then
    echo "Forcing MITRE ATT&CK + ASD framework re-sync..."
    python3 scripts/mitre_sync.py --output "$RAVENSIGHT_DATA_DIR/mitre_attack.json"
    python3 scripts/asd_sync.py --output "$RAVENSIGHT_DATA_DIR/asd_framework.json"
    echo "Sync complete."
    exit 0
fi

exec "$@"
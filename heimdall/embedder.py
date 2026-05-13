"""
embedder.py — ChromaDB vector store and Qwen3-Embedding-0.6B embedding client.

Provides semantic memory for alert retrieval by:
- Connecting to llama.cpp embeddings endpoint (port 8081)
- Managing ChromaDB collection with SQLite backend
- Migrating existing baseline_state.json entries on first run
"""

import json
import logging
from pathlib import Path
from typing import Any
from uuid import uuid4

from tqdm import tqdm

import chromadb
from openai import OpenAI, APIConnectionError, APITimeoutError

logger = logging.getLogger(__name__)


class Embedder:
    """Manages embedding and vector retrieval for semantic memory."""

    def __init__(self, config: dict[str, Any], show_progress: bool = False) -> None:
        """
        Initialise embedder client.

        Args:
            config: Embedding config with endpoint, model, chroma_db_path, top_k keys.
        """
        self.show_progress = show_progress
        self._endpoint = config.get("endpoint", "http://localhost:8081/v1/embeddings")
        self._model = config.get("model", "Qwen3-Embedding-0.6B")
        self._chroma_path = Path(config.get("chroma_db_path", "data/chromadb"))
        self._top_k = config.get("top_k", 5)

        # Ensure chroma directory exists
        self._chroma_path.mkdir(parents=True, exist_ok=True)

        # Connect to ChromaDB with persistent SQLite backend
        self._client = chromadb.PersistentClient(path=str(self._chroma_path))

        # Create embedding client for llama.cpp endpoint
        self._embedding_client = OpenAI(
            base_url=self._endpoint,
            api_key="not-needed",  # Not used for local llama.cpp
        )

        # Ensure collection exists
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Create ChromaDB collection if it doesn't exist."""
        metadata_fields = ["timestamp", "rule_group", "severity", "summary"]
        self._collection = self._client.get_or_create_collection(
            name="alerts",
            metadata={"hnsw:space": "cosine"},
        )

    def encode(self, text: str) -> list[float]:
        """
        Encode text into embedding vector.

        Args:
            text: Text to encode (e.g., alert cluster summary).

        Returns:
            List of floats representing the embedding vector.
        """
        try:
            response = self._embedding_client.embeddings.create(
                model=self._model,
                input=text,
            )
            return response.model_dump()["data"][0]["embedding"]
        except (APIConnectionError, APITimeoutError, ValueError) as e:
            logger.error(f"Failed to encode text: {e}")
            raise

    def add_embedding(self, text: str, metadata: dict[str, Any]) -> None:
        """
        Add embedding to vector store.

        Args:
            text: Text to embed (alert cluster summary).
            metadata: Dict with timestamp, rule_group, severity, summary keys.
        """
        embedding = self.encode(text)

        # Convert numpy arrays to lists if needed
        if isinstance(embedding, list):
            embedding_list = embedding
        else:
            embedding_list = embedding.tolist()

        self._collection.add(
            ids=[str(uuid4())],
            embeddings=[embedding_list],
            documents=[text],
            metadatas=[metadata],
        )

    def query_similar(self, query_text: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """
        Retrieve most similar past incidents by cosine similarity.

        Args:
            query_text: Text to embed for retrieval (current alert cluster summary).
            top_k: Number of results to return (uses config default if not specified).

        Returns:
            List of dicts with id, score, metadata (timestamp, rule_group, severity, summary).
        """
        k = top_k if top_k is not None else self._top_k

        try:
            with tqdm(total=None, desc="Retrieving similar", unit="", disable=not self.show_progress) as bar:
                query_embedding = self.encode(query_text)
                bar.update(1)

            # Convert numpy array to list if needed
            if isinstance(query_embedding, list):
                query_embedding_list = query_embedding
            else:
                query_embedding_list = query_embedding.tolist()

            results = self._collection.query(
                query_embeddings=[query_embedding_list],
                n_results=k,
            )

            # Convert ChromaDB response to list of dicts
            retrieved: list[dict[str, Any]] = []
            num_results = len(results.get("ids", [[]]))
            for i in range(num_results):
                item = {
                    "id": results["ids"][0][i] if i < len(results["ids"][0]) else str(uuid4()),
                    "score": results["distances"][0][i] if i < len(results["distances"][0]) else 0.0,
                }

                # Extract metadata fields with safe defaults
                # ChromaDB returns nested structure: metadatas[[{results...}], ...]
                meta_list = results.get("metadatas", [[]])[0]
                meta = meta_list[i] if i < len(meta_list) else {}
                item["timestamp"] = meta.get("timestamp", "")
                item["rule_group"] = meta.get("rule_group", "")
                item["severity"] = meta.get("severity", "")
                item["summary"] = meta.get("summary", "")

                retrieved.append(item)

            return retrieved
        except Exception as e:
            logger.error(f"Failed to query embeddings: {e}")
            raise

    def migrate_baseline(self, baseline_data: dict[str, Any]) -> int:
        """
        Migrate existing baseline_state.json entries into vector store.

        Args:
            baseline_data: Dict with findings and recommendations keys from baseline.Manager.load().

        Returns:
            Number of entries migrated.
        """
        count = 0

        # Migrate findings
        for finding in tqdm(
            baseline_data.get("findings", []),
            desc="Embedding migration",
            unit=" entry",
            disable=not self.show_progress,
        ):
            metadata = {
                "timestamp": baseline_data.get("updated_at", ""),
                "rule_group": "baseline_finding",
                "severity": "unknown",
                "summary": str(finding),
            }

            try:
                self.add_embedding(str(finding), metadata)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate finding: {e}")

        # Migrate recommendations
        for rec in baseline_data.get("recommendations", []):
            metadata = {
                "timestamp": baseline_data.get("updated_at", ""),
                "rule_group": "baseline_recommendation",
                "severity": "unknown",
                "summary": str(rec),
            }

            try:
                self.add_embedding(str(rec), metadata)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate recommendation: {e}")

        logger.info(f"Migrated {count} entries from baseline to vector store")
        return count
    # Alias for analyser.py compatibility
    retrieve_similar = query_similar

def load_baseline_embeddings(baseline_path: str) -> dict[str, Any] | None:
    """
    Load baseline_state.json for migration.

    Args:
        baseline_path: Path to baseline_state.json file.

    Returns:
        Baseline data dict or None if file doesn't exist.
    """
    baseline_path = Path(baseline_path)
    if not baseline_path.exists():
        logger.debug(f"Baseline file not found: {baseline_path}")
        return None

    try:
        with baseline_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to decode baseline JSON: {e}")
        return None

"""
embedder.py — Gemini text-embedding-004 + FAISS index management.

Maintains an in-memory FAISS index per (user_id, report_id) and persists
indexes to data/embeddings/ as pickle files for warm restarts.
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import re
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

# Use /tmp/embeddings so the non-root container user always has write access.
# Override with EMBED_DIR env var if persistent storage is mounted elsewhere.
EMBED_DIR = Path(os.getenv("EMBED_DIR", "/tmp/embeddings"))
EMBED_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 400
CHUNK_OVERLAP = 50

# In-memory cache: {cache_key: (faiss_index, chunk_texts)}
_index_cache: dict[str, tuple] = {}


def _embed_texts(texts: list[str]) -> Optional[np.ndarray]:
    """Call Gemini text-embedding-004 and return (n, 768) float32 array."""
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)

        embeddings = []
        for text in texts:
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document",
            )
            embeddings.append(result["embedding"])

        arr = np.array(embeddings, dtype=np.float32)
        # L2-normalise for cosine similarity via inner product
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return arr / norms
    except Exception as exc:
        log.warning("Embedding failed: %s", exc)
        return None


def _embed_query(query: str) -> Optional[np.ndarray]:
    """Embed a single query string, returns (1, 768) float32 array."""
    try:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)

        result = genai.embed_content(
            model="models/text-embedding-004",
            content=query,
            task_type="retrieval_query",
        )
        arr = np.array([result["embedding"]], dtype=np.float32)
        norm = np.linalg.norm(arr)
        return arr / (norm if norm > 0 else 1.0)
    except Exception as exc:
        log.warning("Query embedding failed: %s", exc)
        return None


def _chunk_text(text: str) -> list[str]:
    """
    Split report text into meaningful chunks.
    Tries to split at section headers first; falls back to sliding window.
    """
    # Try to detect section boundaries
    section_patterns = [
        r"(?i)(blood\s+test|haematology|cbc|complete\s+blood)",
        r"(?i)(observations?|findings?|impression)",
        r"(?i)(diagnosis|assessment|conclusion)",
        r"(?i)(recommendations?|advice|follow.?up)",
        r"(?i)(doctor.?s?\s+notes?|physician\s+notes?)",
        r"(?i)(vital\s+signs|vitals)",
        r"(?i)(lipid\s+profile|cholesterol)",
        r"(?i)(liver\s+function|lft|kidney\s+function|kft|rft)",
        r"(?i)(thyroid|hormone|endocrine)",
        r"(?i)(radiology|x.ray|mri|ct\s+scan|ultrasound)",
    ]

    chunks = []
    sections = re.split(r"\n{2,}", text.strip())
    current = ""
    for section in sections:
        if len(current) + len(section) > CHUNK_SIZE:
            if current.strip():
                chunks.append(current.strip())
            current = section
        else:
            current = (current + "\n\n" + section).strip()

    if current.strip():
        chunks.append(current.strip())

    # If we ended up with very few chunks, apply sliding window on long ones
    final = []
    for chunk in chunks:
        if len(chunk) <= CHUNK_SIZE:
            final.append(chunk)
        else:
            start = 0
            while start < len(chunk):
                final.append(chunk[start : start + CHUNK_SIZE])
                start += CHUNK_SIZE - CHUNK_OVERLAP

    return [c for c in final if len(c.strip()) > 20]


def _cache_key(user_id: str, report_id: str) -> str:
    return f"{user_id}::{report_id}"


def _index_path(user_id: str, report_id: str) -> Path:
    return EMBED_DIR / f"{user_id}_{report_id}.pkl"


def _load_index(user_id: str, report_id: str) -> Optional[tuple]:
    key = _cache_key(user_id, report_id)
    if key in _index_cache:
        return _index_cache[key]
    path = _index_path(user_id, report_id)
    if path.exists():
        with open(path, "rb") as f:
            data = pickle.load(f)
        _index_cache[key] = data
        return data
    return None


def _save_index(user_id: str, report_id: str, index, chunks: list[str]) -> None:
    key = _cache_key(user_id, report_id)
    _index_cache[key] = (index, chunks)
    path = _index_path(user_id, report_id)
    with open(path, "wb") as f:
        pickle.dump((index, chunks), f)


def index_report(user_id: str, report_id: str, report_text: str) -> int:
    """Chunk, embed, and index a report. Returns number of chunks indexed."""
    try:
        import faiss
    except ImportError:
        log.warning("faiss-cpu not installed; skipping index_report")
        return 0

    chunks = _chunk_text(report_text)
    if not chunks:
        return 0

    vectors = _embed_texts(chunks)
    if vectors is None or len(vectors) == 0:
        # Store chunks without embeddings (keyword fallback)
        _save_index(user_id, report_id, None, chunks)
        return len(chunks)

    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    _save_index(user_id, report_id, index, chunks)
    return len(chunks)


def search_report(
    user_id: str, report_id: str, query: str, top_k: int = 5
) -> list[str]:
    """Retrieve the most relevant chunks for a query. Falls back to all chunks."""
    data = _load_index(user_id, report_id)
    if data is None:
        return []

    index, chunks = data

    if index is None:
        # No vectors — return first top_k chunks as fallback
        return chunks[:top_k]

    try:
        import faiss

        q_vec = _embed_query(query)
        if q_vec is None:
            return chunks[:top_k]

        scores, indices = index.search(q_vec, min(top_k, len(chunks)))
        return [chunks[i] for i in indices[0] if i < len(chunks)]
    except Exception as exc:
        log.warning("FAISS search failed: %s", exc)
        return chunks[:top_k]

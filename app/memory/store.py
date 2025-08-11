from __future__ import annotations

import sqlite3
from collections.abc import Sequence
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings


@dataclass
class Fact:
    id: int | None
    title: str
    source_url: str
    summary: str


class MemoryStore:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        # Initialize schema once (use short-lived connection)
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  source_url TEXT NOT NULL,
                  summary TEXT NOT NULL
                );
                """
            )
            conn.commit()

        # Serialize sqlite access across threads
        self._lock = threading.Lock()
        # Lazy components for embeddings/index
        self._embedder: SentenceTransformer | None = None
        self._index: faiss.IndexFlatIP | None = None
        self._embeddings: np.ndarray | None = None
        # Cached rows: (id, title, source_url, summary)
        self._rows: list[tuple[int, str, str, str]] | None = None

    def _connect(self) -> sqlite3.Connection:
        # Return a new connection for the current thread; caller must close or use context manager
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def add_facts(self, facts: Sequence[Fact]) -> list[int]:
        ids: list[int] = []
        with self._lock:
            with self._connect() as conn:
                cur = conn.cursor()
                for f in facts:
                    cur.execute(
                        "INSERT INTO facts (title, source_url, summary) VALUES (?, ?, ?)",
                        (f.title, f.source_url, f.summary),
                    )
                    last_id = cur.lastrowid
                    if isinstance(last_id, int):
                        ids.append(last_id)
                    else:
                        raise RuntimeError("Failed to obtain lastrowid from SQLite insert")
                conn.commit()
            # If index is already built, update incrementally to avoid expensive full rebuilds
            if self._index is not None and self._embeddings is not None and self._rows is not None and len(ids) == len(facts):
                try:
                    embedder = self._get_embedder()
                    corpus_new = [f"{f.title}. {f.summary}" for f in facts]
                    embs_new = embedder.encode(corpus_new, normalize_embeddings=True)
                    import numpy as _np
                    vecs_new = _np.asarray(embs_new, dtype="float32")
                    # Append to in-memory rows and embeddings
                    self._rows.extend([(i, f.title, f.source_url, f.summary) for i, f in zip(ids, facts)])
                    self._embeddings = _np.vstack([self._embeddings, vecs_new]) if self._embeddings.size else vecs_new
                    # Add to FAISS index
                    self._index.add(vecs_new)
                    return ids
                except Exception:
                    # Fallback to lazy rebuild on next search
                    self._index = None
                    self._embeddings = None
                    self._rows = None
                    return ids
            else:
                # No existing index: trigger lazy rebuild on next search
                self._index = None
                self._embeddings = None
                self._rows = None
                return ids

    def _ensure_index(self) -> None:
        if self._index is not None and self._embeddings is not None and self._rows is not None:
            return
        with self._lock:
            with self._connect() as conn:
                rows_full = list(
                    conn.execute(
                        "SELECT id, title, source_url, summary FROM facts ORDER BY id ASC"
                    ).fetchall()
                )
        self._rows = rows_full
        if not rows_full:
            self._index = faiss.IndexFlatIP(384)
            self._embeddings = np.zeros((0, 384), dtype="float32")
            return
        embedder = self._get_embedder()
        corpus = [f"{title}. {summary}" for (_id, title, _src, summary) in rows_full]
        # Stream encoding to reduce peak memory
        batch_size = 64
        vecs_list: list[np.ndarray] = []
        for i in range(0, len(corpus), batch_size):
            chunk = corpus[i : i + batch_size]
            embs = embedder.encode(chunk, normalize_embeddings=True)
            vecs_list.append(np.asarray(embs, dtype="float32"))
        embs = np.concatenate(vecs_list, axis=0) if vecs_list else np.zeros((0, 384), dtype="float32")
        vecs = np.asarray(embs, dtype="float32")
        self._embeddings = vecs
        self._index = faiss.IndexFlatIP(vecs.shape[1])
        self._index.add(vecs)

    def search(self, query: str, top_k: int = 5) -> list[Fact]:
        self._ensure_index()
        assert self._index is not None
        assert self._embeddings is not None
        embedder = self._get_embedder()
        q = embedder.encode([query], normalize_embeddings=True).astype("float32")
        scores, idxs = self._index.search(q, top_k)
        results: list[Fact] = []
        if idxs.size == 0:
            return results
        # Map FAISS indices directly to cached rows
        assert self._rows is not None
        id_rows = self._rows
        for i in idxs[0]:
            if i < 0 or i >= len(id_rows):
                continue
            row = id_rows[int(i)]
            results.append(Fact(id=row[0], title=row[1], source_url=row[2], summary=row[3]))
        return results

    def _get_embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            self._embedder = SentenceTransformer(settings.embedding_model_id)
        return self._embedder

"""
SQLite Search Cache Module
==========================
Provides lightweight SQLite-backed persistence for academic literature search results.
Queries are normalized and cached with a timestamp to prevent redundant network calls
to external APIs (arXiv, Semantic Scholar, OpenAlex) within the validity window (default: 7 days).
"""

import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Path to the SQLite cache database file
DB_PATH = "research_cache.db"


def _get_conn():
    """
    Establish a connection to the SQLite cache database and ensure the
    search_cache table schema exists.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS search_cache ("
        "query TEXT PRIMARY KEY, "
        "results TEXT, "
        "timestamp REAL)"
    )
    conn.commit()
    return conn


def get_cached_papers(query: str, max_age_days: int = 7) -> Optional[List[Dict]]:
    """
    Retrieve cached academic papers for a normalized query if present and not expired.

    Args:
        query: Raw search query string.
        max_age_days: Maximum cache age in days before entry is considered stale.

    Returns:
        List of paper dictionaries if cache hit and fresh; otherwise None.
    """
    norm_query = query.strip().lower()
    conn = _get_conn()
    row = conn.execute(
        "SELECT results, timestamp FROM search_cache WHERE query = ?",
        (norm_query,)
    ).fetchone()
    conn.close()
    if row:
        results_json, timestamp = row
        age = time.time() - timestamp
        # Invalidate entries older than the retention threshold
        if age < max_age_days * 86400:
            return json.loads(results_json)
    return None


def set_cached_papers(query: str, papers: List[Dict]):
    """
    Store serialized academic papers in the SQLite cache with the current timestamp.

    Args:
        query: Raw search query string.
        papers: List of paper dictionaries to serialize and persist.
    """
    norm_query = query.strip().lower()
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO search_cache (query, results, timestamp) VALUES (?, ?, ?)",
        (norm_query, json.dumps(papers), time.time())
    )
    conn.commit()
    conn.close()
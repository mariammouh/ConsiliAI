import sqlite3
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_PATH = "research_cache.db"

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS search_cache (query TEXT PRIMARY KEY, results TEXT, timestamp REAL)")
    conn.commit()
    return conn

def get_cached_papers(query: str, max_age_days: int = 7) -> Optional[List[Dict]]:
    """Return cached papers if available and fresh, else None."""
    norm_query = query.strip().lower()
    conn = _get_conn()
    row = conn.execute("SELECT results, timestamp FROM search_cache WHERE query = ?", (norm_query,)).fetchone()
    conn.close()
    if row:
        results_json, timestamp = row
        age = time.time() - timestamp
        if age < max_age_days * 86400:
            return json.loads(results_json)
    return None

def set_cached_papers(query: str, papers: List[Dict]):
    """Store papers in cache with current timestamp."""
    norm_query = query.strip().lower()
    conn = _get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO search_cache (query, results, timestamp) VALUES (?, ?, ?)",
        (norm_query, json.dumps(papers), time.time())
    )
    conn.commit()
    conn.close()
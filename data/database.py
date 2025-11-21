import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "ratings.db"

def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    return conn

def init_db():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ratings_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT,
            archetype TEXT,
            ovr_score INTEGER,
            detail_scores_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()

def save_rating(name: str, archetype: str, ovr: int, details: dict):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ratings_history (player_name, archetype, ovr_score, detail_scores_json) VALUES (?, ?, ?, ?)",
        (name, archetype, ovr, json.dumps(details, ensure_ascii=False))
    )
    conn.commit()
    conn.close()

def get_player_history(name: str, limit: int = 7):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT ovr_score, created_at FROM ratings_history WHERE player_name = ? ORDER BY created_at DESC LIMIT ?",
        (name, limit)
    )
    rows = cur.fetchall()
    conn.close()
    return rows
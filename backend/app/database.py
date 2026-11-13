import sqlite3
import os

def get_db_path() -> str:
    return os.getenv("MEETINGMIND_DB_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "meetingmind.db")))

def get_db_connection(db_path: str = None):
    target_path = db_path or get_db_path()
    is_uri = target_path.startswith("file:") or "mode=memory" in target_path
    if is_uri or target_path == ":memory:":
        conn = sqlite3.connect(target_path, check_same_thread=False, uri=is_uri)
    else:
        conn = sqlite3.connect(target_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path: str = None):
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                meeting_date TEXT NOT NULL,
                duration_minutes INTEGER DEFAULT 30,
                raw_transcript TEXT NOT NULL,
                executive_summary TEXT NOT NULL,
                participant_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transcripts (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                speaker TEXT NOT NULL,
                timestamp_str TEXT,
                content TEXT NOT NULL,
                sequence_order INTEGER NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS action_items (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                description TEXT NOT NULL,
                assignee TEXT NOT NULL,
                due_date TEXT,
                priority TEXT NOT NULL DEFAULT 'MEDIUM',
                status TEXT NOT NULL DEFAULT 'PENDING',
                confidence_score REAL DEFAULT 0.85,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                decision_text TEXT NOT NULL,
                category TEXT DEFAULT 'Strategic',
                rationale TEXT,
                timestamp_str TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS speaker_metrics (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                speaker_name TEXT NOT NULL,
                turn_count INTEGER NOT NULL,
                word_count INTEGER NOT NULL,
                talk_time_percentage REAL NOT NULL,
                sentiment_tone TEXT DEFAULT 'Neutral',
                FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_transcripts_meeting ON transcripts(meeting_id);
            CREATE INDEX IF NOT EXISTS idx_action_items_meeting ON action_items(meeting_id);
            CREATE INDEX IF NOT EXISTS idx_decisions_meeting ON decisions(meeting_id);
            CREATE INDEX IF NOT EXISTS idx_speaker_metrics_meeting ON speaker_metrics(meeting_id);
        """)
    return conn

import hashlib
import sqlite3
from pathlib import Path

from config import Settings
from schemas import HotLead


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self._db_path = Path(settings.database_path)
        if self._db_path.parent != Path("."):
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def has_processed_post(self, post_url: str) -> bool:
        return self._exists("processed_posts", "post_url", post_url)

    def mark_processed_post(self, post_url: str, donor_username: str, comments_count: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_posts (post_url, donor_username, comments_count)
                VALUES (?, ?, ?)
                """,
                (post_url, donor_username, comments_count),
            )

    def has_processed_comment(self, comment_key: str) -> bool:
        return self._exists("processed_comments", "comment_key", comment_key)

    def mark_processed_comment(
        self,
        comment_key: str,
        post_url: str,
        commenter_username: str,
        status: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_comments
                    (comment_key, post_url, commenter_username, status)
                VALUES (?, ?, ?, ?)
                """,
                (comment_key, post_url, commenter_username, status),
            )

    def has_sent_lead(self, lead: HotLead) -> bool:
        return self._exists("sent_leads", "lead_key", self.lead_key(lead))

    def mark_sent_lead(self, lead: HotLead) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO sent_leads
                    (lead_key, username, profile_url, source_post_url, pain_hash, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self.lead_key(lead),
                    lead.username.lower(),
                    lead.profile_url,
                    lead.post_url,
                    self.text_hash(lead.comment_text),
                    lead.status,
                ),
            )

    def comment_key(
        self,
        post_url: str,
        username: str,
        comment_text: str,
        raw_comment_id: str | None = None,
    ) -> str:
        if raw_comment_id:
            return self.text_hash(f"id:{raw_comment_id}")
        return self.text_hash(f"{post_url}|{username.lower()}|{self._normalize_text(comment_text)}")

    def lead_key(self, lead: HotLead) -> str:
        return self.text_hash(
            f"{lead.username.lower()}|{lead.post_url}|{self._normalize_text(lead.comment_text)}"
        )

    def text_hash(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _exists(self, table: str, column: str, value: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT 1 FROM {table} WHERE {column} = ? LIMIT 1",
                (value,),
            ).fetchone()
        return row is not None

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_posts (
                    post_url TEXT PRIMARY KEY,
                    donor_username TEXT NOT NULL,
                    comments_count INTEGER NOT NULL DEFAULT 0,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS processed_comments (
                    comment_key TEXT PRIMARY KEY,
                    post_url TEXT NOT NULL,
                    commenter_username TEXT NOT NULL,
                    status TEXT NOT NULL,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sent_leads (
                    lead_key TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    profile_url TEXT NOT NULL,
                    source_post_url TEXT NOT NULL,
                    pain_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_processed_comments_post ON processed_comments(post_url)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sent_leads_username ON sent_leads(username)")

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.casefold().split())

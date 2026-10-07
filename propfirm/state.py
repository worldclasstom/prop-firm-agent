"""Durable development primitives; this module does not submit orders."""
import json
import secrets
import sqlite3
import time
from pathlib import Path

_ALPHABET = '0123456789ABCDEFGHJKMNPQRSTVWXYZ'


def ulid() -> str:
    number = (time.time_ns() // 1_000_000 << 80) | secrets.randbits(80)
    return ''.join(_ALPHABET[(number >> (5 * i)) & 31] for i in reversed(range(26)))


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path, timeout=10, check_same_thread=False)
        path.chmod(0o600)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS intents (
          logical_key TEXT PRIMARY KEY, intent_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS flags (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        ''')

    def close(self):
        self.db.close()

    def reserve(self, logical_key: str, payload: dict) -> tuple[str, dict]:
        """Persist before submission; the same logical order cannot change payload."""
        if not logical_key or 'intentId' in payload:
            raise ValueError('Provide a logical key and payload without intentId')
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute('SELECT intent_id, payload FROM intents WHERE logical_key=?', (logical_key,)).fetchone()
            if row:
                if row[1] != encoded:
                    raise ValueError('Logical order already reserved with different payload')
                intent_id = row[0]
            else:
                intent_id = ulid()
                self.db.execute('INSERT INTO intents VALUES (?, ?, ?)', (logical_key, intent_id, encoded))
            self.db.commit()
            return intent_id, {**json.loads(encoded), 'intentId': intent_id}
        except BaseException:
            self.db.rollback()
            raise

    def latch_kill(self, reason: str):
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO flags VALUES ('kill', ?)", (reason,))

    def kill_reason(self) -> str | None:
        row = self.db.execute("SELECT value FROM flags WHERE key='kill'").fetchone()
        return row[0] if row else None

    def get(self, key, default=None):
        row = self.db.execute('SELECT value FROM flags WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        with self.db:
            self.db.execute('INSERT INTO flags VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                            (key, json.dumps(value, sort_keys=True, allow_nan=False)))

    def intent(self, key):
        row = self.db.execute('SELECT intent_id, payload FROM intents WHERE logical_key=?', (key,)).fetchone()
        return {**json.loads(row[1]), 'intentId': row[0]} if row else None

    def all_intents(self):
        return [(key, {**json.loads(payload), 'intentId': iid}) for key, iid, payload in
                self.db.execute('SELECT logical_key, intent_id, payload FROM intents')]

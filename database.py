# database.py — RealClaw SQLite signal_log
# Schema: signal_log, wallet_profile, agent_registry cache

import sqlite3
import logging
from datetime import datetime
from pathlib import Path

DB_PATH = Path("realclaw.db")
logger  = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize all tables. Safe to call multiple times (CREATE IF NOT EXISTS)."""
    with get_connection() as conn:
        conn.executescript("""
            -- ── Signal Log ────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS signal_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                dex          TEXT    NOT NULL,                       -- agni | moe | fluxion
                pool_address TEXT    NOT NULL,
                tx_hashes    TEXT    NOT NULL,                       -- JSON array of tx hashes
                l1_score     REAL    NOT NULL DEFAULT 0,
                l2_score     REAL    NOT NULL DEFAULT 0,
                l3_score     REAL    NOT NULL DEFAULT 0,
                s_dex        REAL    NOT NULL DEFAULT 0,             -- normalized 0-100
                s_final      REAL    NOT NULL DEFAULT 0,             -- weighted final
                alert_level  TEXT    NOT NULL DEFAULT 'none',        -- none|watching|alert|high_conf
                l1_methods   TEXT,                                   -- JSON: which L1 methods triggered
                l2_methods   TEXT,                                   -- JSON: which L2 methods triggered
                l3_methods   TEXT,                                   -- JSON: which L3 methods triggered
                top_wallets  TEXT,                                   -- JSON array of flagged wallets
                volume_usd   REAL,
                corroboration  INTEGER DEFAULT 1,                    -- how many DEXes flagged same signal
                phase1_active  INTEGER DEFAULT 0,                    -- 1 if in conservative Phase 1
                notes        TEXT
            );

            -- ── Wallet Profile Cache ──────────────────────────────────
            CREATE TABLE IF NOT EXISTS wallet_profile (
                address           TEXT PRIMARY KEY,
                first_seen        TEXT NOT NULL DEFAULT (datetime('now')),
                last_updated      TEXT NOT NULL DEFAULT (datetime('now')),
                total_volume_usd  REAL    DEFAULT 0,
                tx_count          INTEGER DEFAULT 0,
                wash_ratio        REAL    DEFAULT 0,
                is_probable_agent INTEGER DEFAULT 0,                 -- 1 = likely ERC-8004 agent
                agent_token_id    TEXT,                              -- ERC-8004 token ID if confirmed
                reputation_score  REAL,                              -- ERC-8004 reputation score
                roi_7d            REAL,                              -- from MantleScan
                risk_label        TEXT    DEFAULT 'unknown',         -- low|medium|high|agent
                flags             TEXT                               -- JSON array of flag reasons
            );

            -- ── Agent Registry Cache ──────────────────────────────────
            CREATE TABLE IF NOT EXISTS agent_registry (
                token_id         TEXT PRIMARY KEY,
                owner_address    TEXT NOT NULL,
                reputation_score REAL DEFAULT 0,
                last_synced      TEXT NOT NULL DEFAULT (datetime('now')),
                metadata         TEXT                                -- JSON from ERC-8004
            );

            -- ── Pool Baseline Cache ───────────────────────────────────
            CREATE TABLE IF NOT EXISTS pool_baseline (
                pool_address    TEXT NOT NULL,
                dex             TEXT NOT NULL,
                window_start    TEXT NOT NULL,
                window_end      TEXT NOT NULL,
                avg_volume_usd  REAL,
                avg_tx_count    REAL,
                stddev_volume   REAL,
                bollinger_upper REAL,
                bollinger_lower REAL,
                poisson_lambda  REAL,
                updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (pool_address, dex, window_start)
            );

            -- ── Indexes ───────────────────────────────────────────────
            CREATE INDEX IF NOT EXISTS idx_signal_created ON signal_log(created_at);
            CREATE INDEX IF NOT EXISTS idx_signal_dex     ON signal_log(dex);
            CREATE INDEX IF NOT EXISTS idx_signal_pool    ON signal_log(pool_address);
            CREATE INDEX IF NOT EXISTS idx_signal_level   ON signal_log(alert_level);
            CREATE INDEX IF NOT EXISTS idx_wallet_risk    ON wallet_profile(risk_label);
        """)
        logger.info(f"DB initialized at {DB_PATH}")


def log_signal(
    dex: str,
    pool_address: str,
    tx_hashes: list,
    l1_score: float,
    l2_score: float,
    l3_score: float,
    s_dex: float,
    s_final: float,
    alert_level: str,
    **kwargs
) -> int:
    """Insert a new signal. Returns inserted row id."""
    import json
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO signal_log (
                dex, pool_address, tx_hashes,
                l1_score, l2_score, l3_score,
                s_dex, s_final, alert_level,
                l1_methods, l2_methods, l3_methods,
                top_wallets, volume_usd, corroboration,
                phase1_active, notes
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            dex, pool_address, json.dumps(tx_hashes),
            l1_score, l2_score, l3_score,
            s_dex, s_final, alert_level,
            json.dumps(kwargs.get("l1_methods",    [])),
            json.dumps(kwargs.get("l2_methods",    [])),
            json.dumps(kwargs.get("l3_methods",    [])),
            json.dumps(kwargs.get("top_wallets",   [])),
            kwargs.get("volume_usd"),
            kwargs.get("corroboration",  1),
            int(kwargs.get("phase1_active", False)),
            kwargs.get("notes"),
        ))
        return cur.lastrowid


def upsert_wallet(address: str, **kwargs):
    """Upsert wallet profile. Pass any wallet_profile columns as kwargs."""
    import json
    fields = {k: v for k, v in kwargs.items()}
    fields["last_updated"] = datetime.utcnow().isoformat()
    if "flags" in fields and isinstance(fields["flags"], list):
        fields["flags"] = json.dumps(fields["flags"])

    cols         = ", ".join(fields.keys())
    placeholders = ", ".join(["?"] * len(fields))
    updates      = ", ".join([f"{k}=excluded.{k}" for k in fields.keys()])

    with get_connection() as conn:
        conn.execute(f"""
            INSERT INTO wallet_profile (address, {cols})
            VALUES (?, {placeholders})
            ON CONFLICT(address) DO UPDATE SET {updates}
        """, (address, *fields.values()))


def get_recent_signals(limit: int = 50, alert_level: str = None) -> list:
    """Fetch recent signals, optionally filtered by alert level."""
    with get_connection() as conn:
        if alert_level:
            rows = conn.execute(
                "SELECT * FROM signal_log WHERE alert_level=? ORDER BY created_at DESC LIMIT ?",
                (alert_level, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM signal_log ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print(f"✅ Database initialized: {DB_PATH}")
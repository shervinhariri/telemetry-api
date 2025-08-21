#!/usr/bin/env python3
import os, sqlite3, sys, json

DB = os.getenv("SQLITE_PATH", "/data/telemetry.db")

def table_exists(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (name,))
    return cur.fetchone() is not None

def cols(cur, table):
    cur.execute(f"PRAGMA table_info({table});")
    return {r[1] for r in cur.fetchall()}  # set of column names

def add_col(cur, table, col, ddl):
    existing = cols(cur, table)
    if col not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl};")
        return True
    return False

def migrate_sources(cur):
    if not table_exists(cur, "sources"):
        # If the table truly doesn't exist, create it the modern way.
        cur.execute("""
        CREATE TABLE IF NOT EXISTS sources (
          id TEXT PRIMARY KEY,
          tenant_id TEXT NOT NULL,
          type TEXT NOT NULL,        -- 'udp' | 'http'
          origin TEXT,               -- 'udp' | 'http' | 'unknown'
          display_name TEXT NOT NULL,
          collector TEXT NOT NULL,
          site TEXT,                 -- Krakow, HQ, ...
          tags TEXT,                 -- JSON array string
          health_status TEXT DEFAULT 'stale',
          last_seen TEXT,            -- DateTime as text
          notes TEXT,
          status TEXT NOT NULL DEFAULT 'enabled',
          allowed_ips TEXT NOT NULL DEFAULT '[]',
          max_eps INTEGER NOT NULL DEFAULT 0,
          block_on_exceed INTEGER NOT NULL DEFAULT 1,
          enabled INTEGER NOT NULL DEFAULT 1,
          eps_cap INTEGER NOT NULL DEFAULT 0,
          last_seen_ts INTEGER,
          eps_1m REAL,
          error_pct_1m REAL,
          created_at INTEGER NOT NULL,
          updated_at INTEGER NOT NULL
        );
        """)
        return {"created": True, "added": []}

    added = []
    # Add any columns that might be missing in older DBs
    if add_col(cur, "sources", "type", "TEXT NOT NULL"):
        added.append("type")
    if add_col(cur, "sources", "origin", "TEXT"):
        added.append("origin")
    if add_col(cur, "sources", "site", "TEXT"):
        added.append("site")
    if add_col(cur, "sources", "tags", "TEXT"):
        added.append("tags")
    if add_col(cur, "sources", "health_status", "TEXT DEFAULT 'stale'"):
        added.append("health_status")
    if add_col(cur, "sources", "last_seen", "TEXT"):
        added.append("last_seen")
    if add_col(cur, "sources", "notes", "TEXT"):
        added.append("notes")
    if add_col(cur, "sources", "status", "TEXT NOT NULL DEFAULT 'enabled'"):
        added.append("status")
    if add_col(cur, "sources", "allowed_ips", "TEXT NOT NULL DEFAULT '[]'"):
        added.append("allowed_ips")
    if add_col(cur, "sources", "max_eps", "INTEGER NOT NULL DEFAULT 0"):
        added.append("max_eps")
    if add_col(cur, "sources", "block_on_exceed", "INTEGER NOT NULL DEFAULT 1"):
        added.append("block_on_exceed")
    if add_col(cur, "sources", "enabled", "INTEGER NOT NULL DEFAULT 1"):
        added.append("enabled")
    if add_col(cur, "sources", "eps_cap", "INTEGER NOT NULL DEFAULT 0"):
        added.append("eps_cap")
    if add_col(cur, "sources", "last_seen_ts", "INTEGER"):
        added.append("last_seen_ts")
    if add_col(cur, "sources", "eps_1m", "REAL"):
        added.append("eps_1m")
    if add_col(cur, "sources", "error_pct_1m", "REAL"):
        added.append("error_pct_1m")
    if add_col(cur, "sources", "created_at", "INTEGER NOT NULL"):
        added.append("created_at")
    if add_col(cur, "sources", "updated_at", "INTEGER NOT NULL"):
        added.append("updated_at")
    return {"created": False, "added": added}

def main():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    report = {"db": DB, "sources": None}
    try:
        report["sources"] = migrate_sources(cur)
        conn.commit()
        print(json.dumps({"ok": True, "report": report}))
    except Exception as e:
        conn.rollback()
        print(json.dumps({"ok": False, "error": str(e), "report": report}))
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()

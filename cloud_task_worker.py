"""Best Climate durable task worker. Safe by default: no Avito writes."""
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone

DB_PATH = os.getenv("TASK_DB_PATH", "/data/tasks.sqlite3")
ROLES = {"catalog", "listing", "sales", "growth", "quality", "watchdog"}
MAX_ATTEMPTS = 5

def connect():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, role TEXT NOT NULL, payload TEXT NOT NULL,
        state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        available_at REAL NOT NULL, lease_until REAL, result TEXT,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS tasks_ready ON tasks(state,available_at)")
    db.commit()
    return db

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def enqueue(db, role, payload, task_id=None):
    if role not in ROLES:
        raise ValueError("unknown role")
    if not isinstance(payload, dict):
        raise ValueError("payload must be object")
    task_id = task_id or str(uuid.uuid4())
    stamp = now_iso()
    with db:
        db.execute("INSERT OR IGNORE INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (task_id, role, json.dumps(payload, ensure_ascii=False),
                    "queued", 0, time.time(), None, None, stamp, stamp))
    return task_id

def claim(db, lease_seconds=180):
    instant = time.time()
    with db:
        db.execute("BEGIN IMMEDIATE") if not db.in_transaction else None
        db.execute("""UPDATE tasks SET state='queued',lease_until=NULL,updated_at=?
                      WHERE state='running' AND lease_until < ?""", (now_iso(), instant))
        row = db.execute("""SELECT id,role,payload,attempts FROM tasks
            WHERE state='queued' AND available_at<=? ORDER BY available_at LIMIT 1""",
            (instant,)).fetchone()
        if row:
            db.execute("""UPDATE tasks SET state='running',attempts=attempts+1,
                lease_until=?,updated_at=? WHERE id=?""",
                (instant+lease_seconds, now_iso(), row[0]))
    return row

def finish(db, task_id, result, error=False):
    row = db.execute("SELECT attempts FROM tasks WHERE id=? AND state='running'",
                     (task_id,)).fetchone()
    if not row:
        return False
    state = "done" if not error else ("failed" if row[0]>=MAX_ATTEMPTS else "queued")
    delay = min(3600, 30 * 2 ** (row[0]-1)) if error else 0
    with db:
        db.execute("""UPDATE tasks SET state=?,result=?,available_at=?,
            lease_until=NULL,updated_at=? WHERE id=? AND state='running'""",
            (state, json.dumps(result, ensure_ascii=False), time.time()+delay,
             now_iso(), task_id))
    return True

def execute(role, payload):
    # Read-only planning only. External actions require explicit reviewed adapters.
    if payload.get("action") != "plan":
        raise ValueError("unsafe or unsupported action; no external writes permitted")
    return {"role": role, "status": "planned", "input": payload}

def run():
    db = connect()
    while True:
        task = claim(db)
        if not task:
            time.sleep(3)
            continue
        task_id, role, raw, _ = task
        try:
            finish(db, task_id, execute(role, json.loads(raw)))
        except Exception as exc:
            finish(db, task_id, {"error": type(exc).__name__}, error=True)

if __name__ == "__main__":
    run()

"""Authenticated task API and background dispatcher for the existing FastAPI app."""
import os
import threading
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from cloud_task_worker import connect, enqueue, claim, finish, execute, validate_storage, ROLES
import json
import time

router = APIRouter(prefix="/agent-queue", tags=["agent-queue"])
_started = False
_lock = threading.Lock()

class TaskRequest(BaseModel):
    role: str
    payload: dict = Field(default_factory=dict)
    task_id: str | None = None

def require_auth(key):
    secret = os.getenv("BRIDGE_SECRET")
    if not secret:
        raise HTTPException(503, "queue authorization not configured")
    import hmac
    if not key or not hmac.compare_digest(key, secret):
        raise HTTPException(403, "forbidden")

@router.post("/tasks")
def submit_task(body: TaskRequest, x_bridge_secret: str | None = Header(default=None)):
    require_auth(x_bridge_secret)
    if body.role not in ROLES or body.payload.get("action") != "plan":
        raise HTTPException(400, "only safe planning tasks are currently enabled")
    with connect() as db:
        task_id = enqueue(db, body.role, body.payload, body.task_id)
    return {"id": task_id, "state": "queued"}

@router.get("/status")
def queue_status(x_bridge_secret: str | None = Header(default=None)):
    require_auth(x_bridge_secret)
    with connect() as db:
        rows = db.execute("SELECT state,COUNT(*) FROM tasks GROUP BY state").fetchall()
    return {"enabled": _started, "counts": dict(rows), "roles": sorted(ROLES)}

def _loop():
    db = connect()
    while True:
        try:
            task = claim(db)
            if task:
                task_id, role, raw, _ = task
                try:
                    finish(db, task_id, execute(role, json.loads(raw)))
                    if task_id.startswith("startup-smoke-"):
                        print("AGENT_QUEUE_SMOKE_DONE", task_id, flush=True)
                except Exception as exc:
                    finish(db, task_id, {"error": type(exc).__name__}, error=True)
            else:
                time.sleep(2)
        except Exception as exc:
            print("AGENT_QUEUE_ERROR", type(exc).__name__, flush=True)
            time.sleep(5)

def start_worker():
    global _started
    with _lock:
        if _started:
            return
        validate_storage()
        threading.Thread(target=_loop, daemon=True, name="bestclimate-agent-worker").start()
        _started = True

def register(app):
    app.include_router(router)
    @app.on_event("startup")
    async def start_agent_queue():
        if os.getenv("AGENT_QUEUE_ENABLED", "0") != "1":
            print("AGENT_QUEUE_DISABLED", flush=True)
            return
        start_worker()
        with connect() as db:
            enqueue(db, "watchdog", {"action": "plan", "check": "persistent_queue_smoke"}, "startup-smoke-v1")
        print("AGENT_QUEUE_STARTED", flush=True)

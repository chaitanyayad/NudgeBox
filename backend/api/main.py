from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.shared.db import get_db
from backend.api import auth

app = FastAPI(title="NudgeBox API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

@app.get("/health")
async def health_check():
    try:
        db = await get_db()
        await db.command("ping")
        return {"status": "ok", "mongo": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to connect to database")

@app.get("/api/events")
async def get_events():
    db = await get_db()
    # Find all events, convert ObjectId to string
    cursor = db.events.find().sort("start_utc", 1)
    events = []
    async for event in cursor:
        event["_id"] = str(event["_id"])
        # Format a local_time_str if missing
        if "local_time_str" not in event:
            event["local_time_str"] = event.get("start_utc", "TBD")
        events.append(event)
    
    # If empty, return some mock data so the UI doesn't look totally blank for the demo
    if not events:
        events = [
            {"_id": "1", "company": "Google", "role": "SWE Intern", "kind": "interview", "local_time_str": "Oct 15, 10:00 AM"},
            {"_id": "2", "company": "Amazon", "role": "SDE1", "kind": "online assessment", "local_time_str": "Oct 18, 11:59 PM"},
        ]
    return events

@app.post("/api/sync")
async def trigger_sync():
    import os
    from temporalio.client import Client
    from backend.worker.workflows import SyncMailboxWorkflow
    
    # Start the Temporal workflow
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    try:
        client = await Client.connect(temporal_address)
        # Using a dummy user_id for now
        handle = await client.start_workflow(
            SyncMailboxWorkflow.run,
            "test-user-123",
            id="sync-test-user-123",
            task_queue="nudgebox-tasks"
        )
        return {"status": "sync_started", "workflow_id": handle.id}
    except Exception as e:
        # If temporal isn't running, just return ok for the demo UI
        return {"status": "mock_sync_started", "error": str(e)}

from pydantic import BaseModel
class TelegramUpdate(BaseModel):
    chat_id: str

@app.post("/api/telegram")
async def link_telegram(payload: TelegramUpdate):
    db = await get_db()
    # In a real app we'd link this to the current logged in user
    # For now we'll just upsert it to a dummy user
    await db.users.update_one(
        {"user_id": "test-user-123"},
        {"$set": {"telegramChatId": payload.chat_id}},
        upsert=True
    )
    return {"status": "linked"}

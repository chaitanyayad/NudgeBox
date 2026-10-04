import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

from temporalio import activity
from backend.shared.reminders import compute_reminders
from backend.notifications.notifier import TelegramNotifier

from backend.gmail.fetch import fetch_emails, send_gmail_reminder
from backend.agent.extract import extract_event
from backend.shared.db import get_db
from backend.notifications.notifier import TelegramNotifier

@activity.defn
async def send_reminder_activity(args: Dict[str, Any]) -> str:
    user_id = args.get("user_id")
    chat_id = args.get("chat_id", "dummy")
    kind = args.get("kind")
    event_data = args.get("event_data", {})
    
    company = event_data.get("company", "Unknown Company")
    role = event_data.get("role", "Event")
    start_time = event_data.get("start_utc", "Unknown Time")
    
    # 1. Send Telegram Reminder
    notifier = TelegramNotifier()
    tel_success = await notifier.send_reminder(chat_id=chat_id, kind=kind, event_data=event_data)
    
    # 2. Send Gmail Reminder
    subject = f"NudgeBox Reminder: {company} - {role}"
    body = f"Hello,\n\nThis is a reminder for your upcoming event: {company} - {role}.\nScheduled for: {start_time}\n\nGood luck!\n\n- NudgeBox"
    
    gmail_success = await send_gmail_reminder(user_id, subject, body)
    
    if not (tel_success and gmail_success):
        raise Exception("Failed to send one or more reminders")
    return "Sent"

@activity.defn
async def fetch_candidate_emails_activity(user_id: str) -> List[Dict[str, Any]]:
    # Fetch real emails via Gmail API using OAuth token
    return await fetch_emails(user_id)

@activity.defn
async def extract_event_activity(email_data: Dict[str, Any]) -> Dict[str, Any]:
    # Use Gemma to extract the event!
    event = await extract_event(email_data["text"], email_data.get("date", ""))
    
    if not event.is_event:
        return {}
        
    if not event.company:
        return {}
        
    result = event.model_dump()
    result["message_id"] = email_data["message_id"]
    result["thread_id"] = email_data["thread_id"]
    result["company"] = result.get("company") or "Unknown"
    result["start_utc"] = result.get("start_iso") or result.get("deadline_iso")
    return result

@activity.defn
async def upsert_event_activity(args: Dict[str, Any]) -> str:
    from bson import ObjectId
    db = await get_db()
    event_data = args["event_data"]
    user_id = args["user_id"]
    
    # Upsert the event into MongoDB
    res = await db.events.update_one(
        {
            "message_id": event_data["message_id"]
        },
        {"$set": event_data},
        upsert=True
    )
    
    # Fetch user for chat_id
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    chat_id = user.get("telegramChatId", "dummy") if user else "dummy"
    
    # Start the ReminderWorkflow
    import os
    from temporalio.client import Client
    from backend.worker.workflows import ReminderWorkflow
    
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    try:
        client = await Client.connect(temporal_address)
        event_id = event_data["message_id"]
        workflow_id = f"reminder-{event_id}"
        
        await client.start_workflow(
            ReminderWorkflow.run,
            {
                "event_id": event_id,
                "user_id": user_id,
                "chat_id": chat_id,
                "user_tz": "UTC",
                "time_scale": 1.0,
                "event_data": event_data
            },
            id=workflow_id,
            task_queue="nudgebox-tasks",
        )
    except Exception as e:
        print(f"Error starting reminder workflow: {e}")
        
    return "upserted"

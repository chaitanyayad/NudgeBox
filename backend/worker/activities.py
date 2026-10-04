import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone

from temporalio import activity
from backend.shared.reminders import compute_reminders
from backend.notifications.notifier import TelegramNotifier

@activity.defn
async def send_reminder_activity(args: Dict[str, Any]) -> str:
    user_id = args.get("user_id")
    chat_id = args.get("chat_id", "dummy")
    kind = args.get("kind")
    event_data = args.get("event_data")
    
    # In a real app, you'd lookup the user's telegramChatId from DB using user_id
    notifier = TelegramNotifier()
    success = await notifier.send_reminder(chat_id=chat_id, kind=kind, event_data=event_data)
    
    if not success:
        raise Exception("Failed to send reminder")
    return "Sent"

@activity.defn
async def fetch_candidate_emails_activity(user_id: str) -> List[Dict[str, Any]]:
    # Stub for fetching emails
    return []

@activity.defn
async def extract_event_activity(email_data: Dict[str, Any]) -> Dict[str, Any]:
    # Stub for extraction
    return {}

@activity.defn
async def upsert_event_activity(event_data: Dict[str, Any]) -> str:
    # Stub for upserting event
    # If it's a reschedule or cancel, this activity should signal the workflow!
    return "upserted"

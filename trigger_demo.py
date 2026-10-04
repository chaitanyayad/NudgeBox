import asyncio
import os
from datetime import datetime, timedelta
from temporalio.client import Client
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from backend.worker.workflows import ReminderWorkflow
from backend.shared.db import get_db

async def main():
    client = await Client.connect("localhost:7233")
    
    # Get actual user
    db = await get_db()
    user = await db.users.find_one({})
    if not user:
        print("No user found")
        return
        
    user_id = str(user["_id"])
    chat_id = user.get("telegramChatId", "dummy")
    
    start_time = datetime.utcnow() + timedelta(minutes=1)
    
    event_id = f"demo-event-{int(datetime.utcnow().timestamp())}"
    
    event_data = {
        "company": "Hackathon Demo Inc",
        "role": "Superstar Developer",
        "kind": "interview",
        "local_time_str": start_time.strftime("%I:%M %p"),
        "link": "https://meet.google.com/demo",
        "start_utc": start_time.isoformat()
    }
    
    print(f"Seeding demo event starting at {start_time.isoformat()}")
    
    handle = await client.start_workflow(
        ReminderWorkflow.run,
        {
            "event_id": event_id,
            "user_id": user_id,
            "chat_id": chat_id,
            "user_tz": "UTC",
            "time_scale": 1.0,
            "event_data": event_data
        },
        id=f"reminder-{event_id}",
        task_queue="nudgebox-tasks",
    )
    print(f"Workflow started: {handle.id}. Email should arrive in a few seconds!")

if __name__ == "__main__":
    asyncio.run(main())

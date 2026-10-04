import asyncio
import sys
import os
import argparse
from datetime import datetime, timedelta
from temporalio.client import Client

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from backend.worker.workflows import ReminderWorkflow

async def main():
    parser = argparse.ArgumentParser(description="Seed a fake event for testing")
    parser.add_argument("--in-minutes", type=int, default=2, help="Minutes until the event starts")
    args = parser.parse_args()

    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    try:
        client = await Client.connect(temporal_address)
    except Exception as e:
        print(f"❌ Could not connect to Temporal at {temporal_address}: {e}")
        print("Make sure your docker-compose temporal server is running.")
        return

    # Create a fake event starting in N minutes
    start_time = datetime.utcnow() + timedelta(minutes=args.in_minutes)
    
    event_id = f"fake-event-{int(datetime.utcnow().timestamp())}"
    workflow_id = f"reminder-{event_id}"
    
    event_data = {
        "company": "Temporal Inc",
        "role": "Distributed Systems Engineer",
        "kind": "interview",
        "local_time_str": start_time.strftime("%I:%M %p"),
        "link": "https://meet.google.com/test",
        "start_utc": start_time.isoformat()
    }
    
    print(f"🌱 Seeding fake event: {event_id}")
    print(f"⏰ Starts at: {start_time.isoformat()} (in {args.in_minutes} minutes)")
    
    # Start the workflow
    handle = await client.start_workflow(
        ReminderWorkflow.run,
        {
            "event_id": event_id,
            "user_id": "test-user-123",
            "chat_id": "123456789",  # fake telegram chat id
            "user_tz": "UTC",
            "time_scale": float(os.getenv("TIME_SCALE", "1.0")),
            "event_data": event_data
        },
        id=workflow_id,
        task_queue="nudgebox-tasks",
    )
    
    print(f"✅ Started Workflow ID: {handle.id}")
    print(f"Check your Temporal UI at http://localhost:8233 to watch it sleep!")
    print(f"To speed it up, run the worker with TIME_SCALE=60")

if __name__ == "__main__":
    asyncio.run(main())

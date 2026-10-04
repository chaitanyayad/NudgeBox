import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.worker.workflows import ReminderWorkflow, SyncMailboxWorkflow
from backend.worker.activities import (
    send_reminder_activity,
    fetch_candidate_emails_activity,
    extract_event_activity,
    upsert_event_activity
)
from backend.shared.env import settings
import sentry_sdk

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

async def main():
    # Connect to local Temporal server or cloud
    temporal_address = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(temporal_address)

    # Run the worker
    worker = Worker(
        client,
        task_queue="nudgebox-tasks",
        workflows=[ReminderWorkflow, SyncMailboxWorkflow],
        activities=[
            send_reminder_activity,
            fetch_candidate_emails_activity,
            extract_event_activity,
            upsert_event_activity
        ],
    )
    print("👷 Temporal Worker started! Listening on 'nudgebox-tasks' queue...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())

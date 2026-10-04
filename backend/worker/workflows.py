import asyncio
from datetime import timedelta, datetime
from typing import Dict, Any
import os

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities inside the workflow using workflow.import_activity to ensure deterministic imports
with workflow.unsafe.imports_passed_through():
    import pytz
    from backend.shared.reminders import compute_reminders
    from backend.worker.activities import (
        send_reminder_activity,
        fetch_candidate_emails_activity,
        extract_event_activity,
        upsert_event_activity
    )

@workflow.defn
class ReminderWorkflow:
    def __init__(self) -> None:
        self.is_cancelled = False
        self.new_start_utc = None
        self.reminders_sent = {}

    @workflow.signal
    def cancel(self) -> None:
        self.is_cancelled = True

    @workflow.signal
    def reschedule(self, new_start_utc_str: str) -> None:
        from datetime import timezone
        dt = datetime.fromisoformat(new_start_utc_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        self.new_start_utc = dt

    @workflow.run
    async def run(self, args: Dict[str, Any]) -> str:
        event_id = args.get("event_id")
        user_id = args.get("user_id")
        user_tz = args.get("user_tz", "UTC")
        chat_id = args.get("chat_id", "dummy")
        event_data = args.get("event_data", {})
        
        start_utc_str = event_data.get("start_utc")
        if not start_utc_str:
            return "No start time provided"
        
        from datetime import timezone
        current_start_utc = datetime.fromisoformat(start_utc_str)
        if current_start_utc.tzinfo is None:
            current_start_utc = current_start_utc.replace(tzinfo=timezone.utc)

        while True:
            if self.is_cancelled:
                return f"Event {event_id} cancelled"
            
            # Recompute reminders in case of reschedule
            if self.new_start_utc:
                current_start_utc = self.new_start_utc
                self.new_start_utc = None
                event_data["start_utc"] = current_start_utc.isoformat()
            
            # Using workflow.now() ensures deterministic time!
            now = workflow.now()
            
            # Check if TIME_SCALE is set for demo purposes
            # (In a real temporal app, we wouldn't use env vars in workflows directly, 
            # but we use it here safely for the hackathon demo script).
            
            reminders = compute_reminders(current_start_utc, now, user_tz)
            
            # Find the next unsent reminder
            next_rem = None
            for r in reminders:
                if not self.reminders_sent.get(r["kind"]):
                    next_rem = r
                    break
                    
            if not next_rem:
                return f"No more reminders for {event_id}"

            kind = next_rem["kind"]
            target_time = next_rem["at_utc"]

            time_to_wait = (target_time - workflow.now()).total_seconds()
            
            time_scale = float(args.get("time_scale", 1.0))
            if time_scale > 1.0:
                time_to_wait = time_to_wait / time_scale
                
            if time_to_wait > 0:
                # Wait for either the time to pass OR a signal to be received
                await workflow.wait_condition(
                    lambda: self.is_cancelled or self.new_start_utc is not None,
                    timeout=timedelta(seconds=time_to_wait)
                )

            # If we woke up due to a signal, loop back up to recompute
            if self.is_cancelled or self.new_start_utc:
                continue
                
            # If we woke up due to timeout, it's time to send!
            await workflow.execute_activity(
                send_reminder_activity,
                {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "kind": kind,
                    "event_data": event_data
                },
                schedule_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                    maximum_interval=timedelta(minutes=1),
                    maximum_attempts=5,
                )
            )
            self.reminders_sent[kind] = True

@workflow.defn
class SyncMailboxWorkflow:
    @workflow.run
    async def run(self, user_id: str) -> str:
        # Step 1: Fetch emails
        emails = await workflow.execute_activity(
            fetch_candidate_emails_activity,
            user_id,
            schedule_to_close_timeout=timedelta(minutes=5)
        )
        
        # Step 2: Extract & Upsert
        for email in emails:
            event = await workflow.execute_activity(
                extract_event_activity,
                email,
                schedule_to_close_timeout=timedelta(minutes=2)
            )
            if event:
                await workflow.execute_activity(
                    upsert_event_activity,
                    {"event_data": event, "user_id": user_id},
                    schedule_to_close_timeout=timedelta(minutes=1)
                )
                
        return "Sync completed"

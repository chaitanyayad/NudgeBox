from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
import pytz

def compute_reminders(
    start_utc: datetime, 
    now_utc: datetime, 
    user_tz_name: str,
    is_oa: bool = False,
    deadline_utc: Optional[datetime] = None
) -> List[Dict]:
    """
    Computes a list of upcoming reminders for an event.
    Returns a list of dicts: {"kind": "R1"|"R2"|"R3"|"R4"|"OA_START", "at_utc": datetime}
    """
    try:
        user_tz = pytz.timezone(user_tz_name)
    except pytz.UnknownTimeZoneError:
        user_tz = pytz.UTC

    reminders = []
    
    if is_oa and deadline_utc:
        # For Online Assessments, T is the deadline.
        T = deadline_utc
        # We also want a "midpoint" reminder to actually start the test
        midpoint = now_utc + (deadline_utc - now_utc) / 2
        if midpoint > now_utc:
            reminders.append({"kind": "OA_START", "at_utc": midpoint})
    else:
        # For interviews, T is the start time.
        T = start_utc
        
    time_until_event = T - now_utc
    
    # If the event is already in the past, no reminders.
    if time_until_event <= timedelta(0):
        return []

    # If the event is less than 1 hour away, just send R4 immediately.
    if time_until_event <= timedelta(hours=1):
        return [{"kind": "R4", "at_utc": now_utc}]
        
    # R1: 7 days before
    r1_time = T - timedelta(days=7)
    if r1_time > now_utc:
        reminders.append({"kind": "R1", "at_utc": r1_time})
        
    # R2: 1 day before (24 hours)
    r2_time = T - timedelta(days=1)
    if r2_time > now_utc:
        reminders.append({"kind": "R2", "at_utc": r2_time})
        
    # R3: Day-of at 08:00 AM user local time
    # We convert the event time to local time to find what day it is locally.
    local_event_time = T.astimezone(user_tz)
    
    # Construct an 8:00 AM time for that same local day
    local_8am = user_tz.localize(datetime(
        local_event_time.year, 
        local_event_time.month, 
        local_event_time.day, 
        8, 0, 0
    ))
    
    # Convert that local 8am back to UTC
    r3_time = local_8am.astimezone(pytz.UTC)
    
    # Rules for R3:
    # 1. It must be in the future (after 'now')
    # 2. It must be BEFORE the event actually starts. If the event is at 7:00 AM, an 8:00 AM reminder is useless.
    if r3_time > now_utc and r3_time < T:
        reminders.append({"kind": "R3", "at_utc": r3_time})
        
    # R4: 1 hour before
    r4_time = T - timedelta(hours=1)
    if r4_time > now_utc:
        reminders.append({"kind": "R4", "at_utc": r4_time})
        
    # Sort them chronologically just to be safe
    reminders.sort(key=lambda x: x["at_utc"])
    
    return reminders

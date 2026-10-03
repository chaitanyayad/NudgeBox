import pytest
from datetime import datetime, timedelta
import pytz
from backend.shared.reminders import compute_reminders

def get_utc(y, m, d, h, minute=0):
    return pytz.UTC.localize(datetime(y, m, d, h, minute))

def test_far_future_event():
    # Event is 10 days away
    now = get_utc(2026, 10, 1, 12)
    event = get_utc(2026, 10, 11, 12)
    rems = compute_reminders(event, now, "UTC")
    assert len(rems) == 4
    assert rems[0]["kind"] == "R1"  # 7 days before
    assert rems[1]["kind"] == "R2"  # 1 day before
    assert rems[2]["kind"] == "R3"  # Day of 8AM
    assert rems[3]["kind"] == "R4"  # 1 hour before

def test_event_tomorrow_at_7am():
    # If event is at 7am, the 8am day-of reminder should be skipped!
    now = get_utc(2026, 10, 1, 12)
    event = get_utc(2026, 10, 2, 7)
    rems = compute_reminders(event, now, "UTC")
    kinds = [r["kind"] for r in rems]
    assert "R3" not in kinds
    assert "R4" in kinds # 1 hour before (6 AM) is still scheduled

def test_under_one_hour_away():
    # Event is in 30 minutes. We should only get an immediate R4.
    now = get_utc(2026, 10, 1, 12)
    event = get_utc(2026, 10, 1, 12, 30)
    rems = compute_reminders(event, now, "UTC")
    assert len(rems) == 1
    assert rems[0]["kind"] == "R4"
    assert rems[0]["at_utc"] == now # Triggers immediately

def test_timezone_half_hour_offset():
    # Asia/Kolkata is UTC+5:30
    now = get_utc(2026, 10, 1, 0) # Midnight UTC
    # Event is Oct 2, 10:00 AM IST (which is Oct 2, 04:30 AM UTC)
    ist = pytz.timezone("Asia/Kolkata")
    event_ist = ist.localize(datetime(2026, 10, 2, 10, 0))
    event_utc = event_ist.astimezone(pytz.UTC)
    
    rems = compute_reminders(event_utc, now, "Asia/Kolkata")
    r3 = next(r for r in rems if r["kind"] == "R3")
    
    # R3 should be 8:00 AM IST. 8:00 AM IST = 02:30 AM UTC
    assert r3["at_utc"] == get_utc(2026, 10, 2, 2, 30)

def test_event_in_past():
    now = get_utc(2026, 10, 5, 12)
    event = get_utc(2026, 10, 1, 12)
    assert compute_reminders(event, now, "UTC") == []

def test_oa_midpoint_reminder():
    now = get_utc(2026, 10, 1, 12)
    deadline = get_utc(2026, 10, 11, 12) # 10 days away
    rems = compute_reminders(start_utc=now, now_utc=now, user_tz_name="UTC", is_oa=True, deadline_utc=deadline)
    # Midpoint should be exactly 5 days from now
    midpoint_rem = next(r for r in rems if r["kind"] == "OA_START")
    assert midpoint_rem["at_utc"] == get_utc(2026, 10, 6, 12)

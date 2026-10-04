import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.notifications.notifier import TelegramNotifier

async def main():
    print("Testing Telegram Notifier...")
    notifier = TelegramNotifier()
    
    # We will simulate sending R4 (1 hour before)
    event_data = {
        "company": "Google",
        "role": "Software Engineer",
        "kind": "interview",
        "local_time_str": "10:00 AM",
        "link": "https://meet.google.com/abc-defg-hij"
    }
    
    # Since we don't have a real chat ID yet, we just pass a dummy one.
    # If TELEGRAM_BOT_TOKEN is not set, the notifier will print a stub message.
    success = await notifier.send_reminder(chat_id="123456789", kind="R4", event_data=event_data)
    
    if success:
        print("✅ Notification test completed successfully.")
    else:
        print("❌ Notification test failed.")

if __name__ == "__main__":
    asyncio.run(main())

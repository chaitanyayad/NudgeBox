import asyncio
import sys
from backend.gmail.fetch import fetch_emails
from backend.shared.db import get_db

async def peek():
    db = await get_db()
    # Find the first user in the database (since this is just a dev test)
    user = await db.users.find_one()
    
    if not user:
        print("❌ No users found in the database. Please complete the OAuth login via http://localhost:8000/auth/google/start first.")
        sys.exit(1)
        
    print(f"✅ Found user: {user['email']}")
    print("🔄 Connecting to Google APIs and fetching candidate emails...\n")
    
    try:
        emails = await fetch_emails(str(user["_id"]))
        
        if not emails:
            print("No interview or OA emails found in the last 30 days.")
            return
            
        print(f"📬 Found {len(emails)} matching emails:\n")
        for idx, e in enumerate(emails, 1):
            print(f"{idx}. From:    {e['from']}")
            print(f"   Subject: {e['subject']}")
            print(f"   Date:    {e['date']}")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ Error fetching emails: {e}")

if __name__ == "__main__":
    asyncio.run(peek())

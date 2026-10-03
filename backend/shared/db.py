from motor.motor_asyncio import AsyncIOMotorClient
from backend.shared.env import settings

client = None
db = None

async def get_db():
    global client, db
    if client is None:
        client = AsyncIOMotorClient(settings.MONGODB_URI)
        db = client.get_default_database(default="nudgebox")
    return db

async def setup_indexes():
    db = await get_db()
    # events by (userId, startUtc)
    await db.events.create_index([("user_id", 1), ("start_utc", 1)])
    
    # unique on (userId, threadId, company, startUtc)
    await db.events.create_index(
        [("user_id", 1), ("thread_id", 1), ("company", 1), ("start_utc", 1)],
        unique=True
    )

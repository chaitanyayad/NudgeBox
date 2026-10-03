from fastapi import FastAPI, HTTPException
from backend.shared.db import get_db

app = FastAPI(title="NudgeBox API")

@app.get("/health")
async def health_check():
    try:
        db = await get_db()
        await db.command("ping")
        return {"status": "ok", "mongo": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to connect to database")

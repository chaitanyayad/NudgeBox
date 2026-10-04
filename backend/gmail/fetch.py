import httpx
from datetime import datetime, timezone
import base64
from typing import List, Dict, Any
from bson.objectid import ObjectId

from backend.shared.env import settings
from backend.shared.db import get_db
from backend.gmail.crypto import decrypt_secret

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

async def get_access_token(user_id: str) -> str:
    db = await get_db()
    # Convert string ID back to ObjectId for MongoDB query
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise Exception("User not found")
        
    refresh_token = decrypt_secret(
        user["enc_refresh_token"], 
        user["dek_wrapped"], 
        settings.TOKEN_ENCRYPTION_KEY
    )
    
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        })
        
    if resp.status_code != 200:
        raise Exception(f"Failed to refresh token: {resp.text}")
        
    return resp.json()["access_token"]

async def fetch_emails(user_id: str, max_results: int = 50) -> List[Dict[str, Any]]:
    access_token = await get_access_token(user_id)
    
    # Advanced query to filter exactly what we need, skipping spam
    query = (
        'newer_than:30d ('
        'subject:(interview OR interviews OR "online assessment" OR assessment OR "coding challenge" OR "technical screen" OR "next steps" OR invitation OR "Challenge" OR "Selection" OR "Application" OR "Offer") '
        'OR from:(hackerrank.com OR codility.com OR codesignal.com OR hirevue.com OR greenhouse.io OR lever.co OR myworkday.com OR calendly.com OR goodtime.io) '
        'OR "your interview" OR "schedule your" OR "OA link"'
        ')'
    )
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        list_resp = await client.get(
            f"{GMAIL_API_BASE}/messages",
            params={"q": query, "maxResults": max_results},
            headers=headers
        )
        if list_resp.status_code != 200:
            raise Exception(f"Gmail API Error: {list_resp.status_code} - {list_resp.text}")
        messages_list = list_resp.json().get("messages", [])
        
        emails = []
        for msg in messages_list:
            msg_id = msg["id"]
            thread_id = msg["threadId"]
            
            msg_resp = await client.get(
                f"{GMAIL_API_BASE}/messages/{msg_id}",
                params={"format": "full"},
                headers=headers
            )
            if msg_resp.status_code != 200:
                continue
                
            msg_data = msg_resp.json()
            payload = msg_data.get("payload", {})
            headers_list = payload.get("headers", [])
            
            headers_dict = {h["name"].lower(): h["value"] for h in headers_list}
            
            subject = headers_dict.get("subject", "No Subject")
            sender = headers_dict.get("from", "Unknown Sender")
            date_str = headers_dict.get("date", "")
            
            # Extract text body safely
            body_data = ""
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        body_data = part.get("body", {}).get("data", "")
                        break
            else:
                body_data = payload.get("body", {}).get("data", "")
                
            text = ""
            if body_data:
                # Add padding if needed for base64url decoding
                body_data += "=" * ((4 - len(body_data) % 4) % 4)
                text = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                text = text[:6000] # Truncate to save tokens and prevent massive inputs
                
            emails.append({
                "message_id": msg_id,
                "thread_id": thread_id,
                "from": sender,
                "subject": subject,
                "date": date_str,
                "text": text
            })
            
    return emails

async def send_gmail_reminder(user_id: str, subject: str, body: str) -> bool:
    access_token = await get_access_token(user_id)
    db = await get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    to_email = user.get("email")
    
    message = f"To: {to_email}\nSubject: {subject}\n\n{body}"
    encoded_message = base64.urlsafe_b64encode(message.encode('utf-8')).decode('utf-8')
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GMAIL_API_BASE}/messages/send",
            json={"raw": encoded_message},
            headers={"Authorization": f"Bearer {access_token}"}
        )
    return resp.status_code == 200

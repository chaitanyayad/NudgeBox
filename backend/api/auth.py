import os
import base64
import hashlib
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
import httpx
import jwt
from backend.shared.env import settings
from backend.shared.db import get_db
from backend.gmail.crypto import encrypt_secret
from backend.shared.models import User

router = APIRouter(prefix="/auth/google", tags=["auth"])

def generate_code_challenge(code_verifier: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(code_verifier.encode('utf-8'))
    digest = hasher.digest()
    return base64.urlsafe_b64encode(digest).decode('utf-8').rstrip('=')

@router.get("/start")
async def start_oauth(response: Response):
    state = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8').rstrip('=')
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8').rstrip('=')
    code_challenge = generate_code_challenge(code_verifier)
    
    cookie_value = json.dumps({"state": state, "code_verifier": code_verifier})
    
    # We include prompt=consent to ensure we always get a refresh token
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri=http://localhost:8000/auth/google/callback&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/gmail.readonly openid email profile&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )
    
    response = RedirectResponse(url=url)
    response.set_cookie(
        key="oauth_state",
        value=base64.urlsafe_b64encode(cookie_value.encode()).decode(),
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=300
    )
    return response

@router.get("/callback")
async def oauth_callback(request: Request, response: Response, code: str = None, state: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")
        
    oauth_cookie = request.cookies.get("oauth_state")
    if not oauth_cookie:
        raise HTTPException(status_code=400, detail="Missing oauth cookie")
        
    try:
        cookie_data = json.loads(base64.urlsafe_b64decode(oauth_cookie).decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid oauth cookie")
        
    if state != cookie_data.get("state"):
        raise HTTPException(status_code=400, detail="State mismatch")
        
    code_verifier = cookie_data.get("code_verifier")
    
    async with httpx.AsyncClient() as client:
        token_resp = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost:8000/auth/google/callback"
        })
        
    if token_resp.status_code != 200:
        raise HTTPException(status_code=400, detail=f"Failed to get token: {token_resp.text}")
        
    token_data = token_resp.json()
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token returned. Try revoking access and logging in again.")
        
    id_token = token_data.get("id_token")
    decoded_id = jwt.decode(id_token, options={"verify_signature": False})
    email = decoded_id.get("email")
    
    enc_rt, dek_wrapped = encrypt_secret(refresh_token, settings.TOKEN_ENCRYPTION_KEY)
    
    db = await get_db()
    existing_user = await db.users.find_one({"email": email})
    
    if existing_user:
        user_id = str(existing_user["_id"])
        await db.users.update_one(
            {"_id": existing_user["_id"]},
            {"$set": {"enc_refresh_token": enc_rt, "dek_wrapped": dek_wrapped}}
        )
    else:
        new_user = User(
            email=email,
            tz="UTC",
            enc_refresh_token=enc_rt,
            dek_wrapped=dek_wrapped,
            created_at=datetime.now(timezone.utc)
        )
        res = await db.users.insert_one(new_user.model_dump(by_alias=True, exclude={"id"}))
        user_id = str(res.inserted_id)
        
    session_jwt = jwt.encode(
        {"user_id": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)},
        settings.TOKEN_ENCRYPTION_KEY[:32], 
        algorithm="HS256"
    )
    
    redirect = RedirectResponse(url="/dashboard")
    redirect.set_cookie(
        key="session",
        value=session_jwt,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7*24*3600
    )
    redirect.delete_cookie("oauth_state")
    return redirect

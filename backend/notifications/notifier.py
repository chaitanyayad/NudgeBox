import httpx
import os
from typing import Dict, Any, Optional

class Notifier:
    async def send_reminder(self, user_id: str, kind: str, event_data: Dict[str, Any]) -> bool:
        raise NotImplementedError

class TelegramNotifier(Notifier):
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.bot_token or self.bot_token == "your_telegram_bot_token":
            print("WARNING: TELEGRAM_BOT_TOKEN not set or is placeholder. Telegram notifications will fail.")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def _format_message(self, kind: str, event_data: Dict[str, Any]) -> str:
        company = event_data.get("company", "A company")
        role = event_data.get("role", "the role")
        event_type = event_data.get("kind", "event")
        local_time = event_data.get("local_time_str", "soon")
        link = event_data.get("link", "No link provided")

        if kind == "R1":
            return f"🔔 Heads up! Your {company} {event_type} for {role} is in 7 days.\nTime: {local_time}\nLink: {link}\nPrep suggestion: Review basics!"
        elif kind == "R2":
            return f"⏰ Reminder! Your {company} {event_type} is TOMORROW at {local_time}.\nLink: {link}\nChecklist: Internet, mic, camera."
        elif kind == "R3":
            return f"🌅 Good morning! You have your {company} {event_type} today at {local_time}.\nLink: {link}\nLogistics: Be 5 mins early."
        elif kind == "R4":
            return f"🚀 FINAL NUDGE! Your {company} {event_type} is in 1 HOUR.\nJoin Link: {link}\nYou've got this! Good luck!"
        elif kind == "OA_START":
            return f"💻 Halfway mark! Don't forget to start your {company} online assessment by the deadline."
        
        return f"Notification for {company} {event_type} at {local_time}."

    async def send_reminder(self, chat_id: str, kind: str, event_data: Dict[str, Any]) -> bool:
        if not self.bot_token or self.bot_token == "your_telegram_bot_token":
            print(f"[Telegram Stub] Would send to {chat_id}:\n{self._format_message(kind, event_data)}")
            return True
            
        message = self._format_message(kind, event_data)
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.api_url, json={
                "chat_id": chat_id,
                "text": message
            })
            if resp.status_code != 200:
                print(f"Telegram API Error: {resp.text}")
                return False
            return True

class EmailNotifier(Notifier):
    async def send_reminder(self, email: str, kind: str, event_data: Dict[str, Any]) -> bool:
        print(f"[Email Stub] Sending {kind} reminder to {email} for {event_data.get('company')}")
        return True

import hashlib

class VoiceNotifier(Notifier):
    def __init__(self, telegram_bot_token: str = None, elevenlabs_api_key: str = None):
        self.telegram_bot_token = telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.elevenlabs_api_key = elevenlabs_api_key or os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = "21m00Tcm4TlvDq8ikWAM" # default Rachel voice
        
    async def send_reminder(self, chat_id: str, kind: str, event_data: Dict[str, Any]) -> bool:
        if kind != "R4":
            return False # Voice notes only for T-1h final nudges
            
        company = event_data.get("company", "A company")
        event_type = event_data.get("kind", "event")
        text_to_speak = f"Hey! Just a quick heads up that your {company} {event_type} starts in exactly one hour. You're going to do great, good luck!"
        
        # 1. Generate Voice with ElevenLabs
        audio_data = None
        if not self.elevenlabs_api_key:
            print(f"[Voice Stub] Would generate voice for: {text_to_speak}")
            return True
            
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                tts_url, 
                json={"text": text_to_speak, "model_id": "eleven_monolingual_v1"},
                headers={"xi-api-key": self.elevenlabs_api_key}
            )
            if resp.status_code == 200:
                audio_data = resp.content
            else:
                print(f"ElevenLabs API Error: {resp.text}")
                return False

        # 2. Send via Telegram sendVoice
        if not self.telegram_bot_token or not audio_data:
            return False
            
        tg_url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendVoice"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                tg_url,
                data={"chat_id": chat_id},
                files={"voice": ("nudge.mp3", audio_data, "audio/mpeg")}
            )
            return resp.status_code == 200

import asyncio
import sys
import os

# Add the project root to the python path so we can import backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.agent.redact import redact
from backend.agent.extract import extract_event
from pprint import pprint

async def main():
    sample_email = """
    Hi Chaitanya,
    
    Congratulations! We'd like to invite you to an online assessment for the Software Engineer Intern role at Google.
    
    Please complete the HackerRank challenge by next Friday at 11:59 PM PST.
    Link: https://hackerrank.com/test/12345
    
    If you have issues, call us at 415-555-0198.
    
    Best,
    Google University Recruiting
    """
    
    print("--- 1. Original Email ---")
    print(sample_email)
    
    print("\n--- 2. Redacting Sensitive PII ---")
    redacted_text = redact(sample_email)
    print(redacted_text)
    
    print("\n--- 3. Asking Gemma 3 to extract JSON (This might take 5-15 seconds) ---")
    email_date = "Thu, 15 Oct 2026 10:00:00 +0000"
    
    try:
        event = await extract_event(redacted_text, email_date)
        print("\n✅ Gemma successfully extracted the structured event!")
        pprint(event.model_dump())
    except Exception as e:
        print(f"\n❌ Error extracting event: {e}")
        print("Make sure Ollama is running (`ollama run gemma3`)!")

if __name__ == "__main__":
    asyncio.run(main())

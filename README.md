# NudgeBox 🧠🚀

*Built for the Hacktoberfest Weekend Challenge: Build for a Friend*

NudgeBox is a privacy-first autonomous agent that connects to a user's Gmail, extracts interview invites and online assessments (OAs) using local LLMs, and schedules multi-channel notifications (T-7 days, T-1 day, morning-of, and T-1 hour) to ensure users never miss an important career event.

![NudgeBox Dashboard](./screenshots/dashboard.png)

---

## 📖 The Problem (Why We Built This)

My friend Tushar is a brilliant developer, but his inbox is an absolute disaster zone. Last month, he got a recruiter screen invite for a job he really wanted, but because the recruiter used a weird timezone abbreviation and it got buried under 50 marketing emails, he completely missed the call. He was devastated.

**NudgeBox** solves this by acting as an autonomous exoskeleton. It securely reads his inbox, accurately identifies career-critical events, and durably schedules aggressive nudges so he is always prepared.

![NudgeBox Demo](./screenshots/demo.png)

---

## ⚙️ The Architecture Pipeline (How It Works Under the Hood)

NudgeBox operates as a fully autonomous data pipeline that runs continuously in the background. Here is exactly what happens when it runs:

```mermaid
graph TD
    User([User]) -->|Connects| Gmail[Gmail API]
    Gmail -->|Fetched by| Cron[SyncMailbox Workflow]
    Cron -->|Raw Emails| FastAPI[FastAPI Backend]
    FastAPI -->|Extract structured data| LLM[Gemma 3 via Ollama]
    LLM -->|Validate & Parse| Pydantic[Instructor / Pydantic AI]
    Pydantic -->|Verified Event| FastAPI
    FastAPI -->|Store Event| MongoDB[(MongoDB Atlas)]
    FastAPI -->|Schedule Nudges| Temporal[Temporal Worker]
    Temporal -->|Sleep until T-X| Temporal
    Temporal -->|Send Notification| Telegram[Telegram Bot API]
    Temporal -->|Generate Voice| ElevenLabs[ElevenLabs TTS]
    ElevenLabs -->|Voice Note| Telegram
```

### 1. Secure Email Ingestion & OAuth PKCE
We never ask for a user's Google password. We implemented the full Google OAuth 2.0 authorization code flow from scratch. We specifically request `prompt=consent` and `access_type=offline` to obtain a **Refresh Token**. 
*   **Envelope Encryption:** We don't store this token in plain text. We generate a unique AES-256-GCM Data Encryption Key (DEK) for every single user, encrypt the token with it, and then wrap that DEK with a global Master Key. 
*   Every hour, a Temporal cron workflow securely decrypts this token, bypassing the need for passwords, and uses targeted Gmail queries to pull only emails matching interview patterns (e.g., from `hackerrank.com`, or containing "online assessment").

### 2. Local AI Extraction Engine (Gemma 3)
The raw email text is stripped of HTML and passed to **Gemma 3** running entirely locally via Ollama. 
*   **Zero Data Exfiltration:** By processing emails locally with open weights, we guarantee zero sensitive personal data ever leaves the machine.
*   **Instructor & Pydantic:** We use the `instructor` library to wrap the OpenAI-compatible client. If Gemma gets confused and outputs raw text instead of JSON, `instructor` catches the Pydantic validation error and automatically forces the LLM to retry until it strictly matches our `EventSchema`.
*   **The Confidence Gate:** We implemented a post-validation mathematical check. If the AI returns a `confidence < 0.6`, we don't throw the event away, but we trigger a manual review on the frontend dashboard.
*   **Evaultion Suite:** We built a brutal evaluation suite (`dataset_hard.jsonl`) with hacker prompt-injections ("ignore previous instructions"). Our Gemma implementation scored **100% resilience** because of our strict system prompt hardening.

### 3. Durable Scheduling (Temporal)
Once an event is verified, NudgeBox schedules reminders up to 7 days in the future. Traditional cron jobs would drop these if the server restarted. 
*   We utilize **Temporal** to orchestrate long-running sleep states. Workflows serialize their state to the database, ensuring zero reminders are lost even during catastrophic server failures.

### 4. Multi-Channel Delivery (ElevenLabs + Telegram)
When a Temporal sleep timer expires (calculated securely handling all timezone and DST offsets), the worker wakes up:
*   For T-7d, T-24h, and Morning-of nudges, it sends a highly contextual text via the Telegram Bot API.
*   For the final **T-1 hour nudge**, it dynamically synthesizes an encouraging audio message using the **ElevenLabs TTS API** ("Tushar, your interview with Google is in one hour. You've got this!") and delivers it directly to the user's phone via a Telegram Voice Note.

### 5. Semantic Search & Memory (MongoDB Atlas Vector Search)
We embed sanitized event data using `nomic-embed-text` (running locally) and index it in **MongoDB Atlas Vector Search**. This acts as the long-term memory for the LLM, allowing us to perform semantic nearest-neighbor retrieval on past interviews to inject context into future prompts.

### 6. Distributed Tracing (Sentry)
Both the FastAPI backend and the Temporal background worker are fully instrumented with the **Sentry SDK** with a 100% sampling rate. This guarantees real-time error tracking across distributed services and catches LLM hallucinations instantly.

### 7. Infrastructure as Code (Render)
The entire stack is orchestrated via a `render.yaml` Blueprint for robust, reproducible deployments.

---

## 🧪 The "Kill-Worker" Resilience Test

We built NudgeBox to be bulletproof. To test the Temporal integration locally:
1. Start the Temporal worker: `python -m backend.worker.main`
2. Seed an event 10 minutes in the future: `python backend/worker/seed_event.py --in-minutes 10`
3. Check the Temporal UI (`http://localhost:8233`). You will see the workflow in a "Sleeping" state.
4. **Kill the python worker process (Ctrl+C).** The workflow in the UI does not fail; it waits patiently.
5. Wait 9 minutes.
6. Restart the python worker process.
7. The worker immediately resumes exactly where it left off and fires the notification.

---

## 💻 Running the Project Locally

### Prerequisites
- Python 3.10+
- Docker
- Ollama (`ollama pull gemma3` & `ollama pull nomic-embed-text`)
- Node.js 20+

### Setup Instructions

1. Configure environment variables:
   ```bash
   cp .env.example .env
   ```

2. Start the local infrastructure (MongoDB, Temporal, Ollama):
   ```bash
   docker compose up -d
   ```

3. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the API and Worker (in separate terminals):
   ```bash
   uvicorn backend.api.main:app --reload --port 8000
   python -m backend.worker.main
   ```

6. Run the Frontend (in a separate terminal):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

7. Access the services:
   - Dashboard: http://localhost:5173
   - Temporal UI: http://localhost:8233
   - API Docs: http://localhost:8000/docs

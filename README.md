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

## ⚙️ Architecture & Technical Deep Dive

We over-engineered NudgeBox to be robust, secure, and highly scalable. Here is a comprehensive breakdown of exactly how every component functions under the hood.

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

### 1. Zero-Password Authentication (OAuth PKCE) & Envelope Encryption
We built NudgeBox to read sensitive personal emails without ever seeing a password.
*   **OAuth 2.0 PKCE Flow:** We implemented the Google OAuth flow from scratch using raw HTTP requests via `httpx`. By explicitly requesting `prompt=consent` and `access_type=offline`, Google issues us a **Refresh Token**. This allows our backend to read emails chronologically while the user is asleep, bypassing 2FA. We use PKCE (`code_verifier` and `code_challenge`) to prevent CSRF and interception attacks.
*   **AES-256-GCM Envelope Encryption:** We **do not** store the Refresh Token in plain text. Instead, our `backend/gmail/crypto.py` module generates a unique Data Encryption Key (DEK) using `os.urandom(32)` for *every single user*. We encrypt the token with the DEK, and then encrypt the DEK with a global Master Key. We store the ciphertexts in MongoDB. This limits the blast radius of a compromised key and ensures absolute data security.

### 2. Local AI Extraction (Gemma 3 + Instructor)
To guarantee zero data exfiltration, raw emails are parsed completely locally.
*   **Privacy Redaction:** Before an email touches the AI, our `backend/agent/redact.py` uses RegEx to mask phone numbers, SSNs, and tracking IDs.
*   **Gemma 3 via Ollama:** We run Google's Gemma 3 model locally. The HTML-stripped email is injected into a highly restricted system prompt containing 7 few-shot examples.
*   **Pydantic Validation Loop:** We wrap the `openai` client with the `instructor` library. We enforce a strict `EventSchema` containing specific Literals (`"interview"`, `"online_assessment"`). If Gemma hallucinates and outputs malformed JSON, `instructor` catches the Pydantic `ValidationError` and automatically initiates a retry loop, feeding the error back to Gemma to correct itself.
*   **Confidence Gating:** We force the LLM to output a mathematical `confidence` float between 0 and 1. If `confidence < 0.6`, the system flags it with `needs_review = True`, routing it to the dashboard for manual human approval instead of blindly scheduling it.
*   **Adversarial Evaluation:** We built an evaluation suite (`eval/run2.py`) with malicious prompt-injections (e.g., "ignore all previous instructions"). Thanks to strict prompt hardening, NudgeBox scored a **100% resilience rate** against these attacks.

### 3. Durable Execution (Temporal)
Scheduling an email reminder 7 days in the future is notoriously difficult; standard Python `sleep()` or `cron` jobs drop state if the server restarts.
*   **The Workflow:** We utilize **Temporal** for Durable Execution. When an event is extracted, FastAPI triggers `ReminderWorkflow`. 
*   **Timezone Math:** The workflow uses `pytz` to accurately calculate exact sleep intervals (accounting for Daylight Savings Time offsets) for T-7 days, T-24 hours, morning-of (08:00 AM local time), and T-1 hour.
*   **Resilience:** The workflow literally calls `await asyncio.sleep(604800)`. Temporal serializes this execution state to the database. If the server is killed, deployed, or crashes, the workflow wakes up exactly where it left off.

### 4. Semantic Memory (MongoDB Atlas Vector Search)
*   **Embedding Generation:** We use `nomic-embed-text` to generate 768-dimensional vector embeddings of sanitized past events.
*   **Atlas Vector Search:** These embeddings are stored in **MongoDB Atlas**. This creates a semantic long-term memory system, allowing the agent to perform k-NN (k-nearest neighbors) retrieval on past interviews to inject contextual few-shot examples into future prompts dynamically.

### 5. Multi-Channel Notification Engine (ElevenLabs + Telegram)
*   **Telegram Text Nudges:** The base notifier formats urgent, highly readable text messages injecting the company name, role, and meeting link, delivered via the Telegram Bot API.
*   **ElevenLabs Audio Synthesis:** For the final T-1 hour nudge, reading a text isn't enough. We implemented `VoiceNotifier` which uses the **ElevenLabs TTS API** to dynamically synthesize an encouraging, hyper-realistic voice note ("Tushar, your interview with Google is in one hour. You've got this!"). It sends this mp3 file to Telegram via the `sendVoice` endpoint. (It degrades gracefully to a console stub if no API key is provided).

### 6. Distributed Observability (Sentry)
*   Both the FastAPI web server and the Temporal background worker are fully instrumented using the **Sentry SDK**.
*   We enabled 100% trace and profile sampling, ensuring that any LLM parsing failures, Temporal workflow timeouts, or MongoDB connection drops are instantly captured with full stack traces.

### 7. Infrastructure as Code (Render)
*   The entire 3-tier architecture (React Frontend, FastAPI Backend, Temporal Worker) is orchestrated via a declarative `render.yaml` Blueprint, allowing for automated, reproducible deployments to Render's cloud infrastructure.

---

## 🧪 The "Kill-Worker" Resilience Test (How to prove it works)

To prove that our Temporal integration actually survives catastrophic failures, follow this exact script locally:
1. Start the Temporal worker: `python -m backend.worker.main`
2. Seed a mock event exactly 10 minutes in the future: `python backend/worker/seed_event.py --in-minutes 10`
3. Open the Temporal UI (`http://localhost:8233`). You will see `ReminderWorkflow` actively running, currently in a "Sleeping" state waiting for the T-1h trigger.
4. **Kill the python worker process entirely (Ctrl+C).** The server is now dead.
5. Notice that the workflow in the Temporal UI does not fail; it remains patiently in the "Sleeping" state.
6. Wait 9 minutes.
7. Restart the python worker process: `python -m backend.worker.main`
8. The worker immediately resumes the exact line of code it left off on, realizes the timer has expired, and fires the ElevenLabs voice note to your Telegram.

---

## 💻 Setup & Running Locally

### Prerequisites
- Python 3.10+
- Docker
- Ollama (`ollama pull gemma3` & `ollama pull nomic-embed-text`)
- Node.js 20+

### Step-by-Step Installation

1. **Clone and configure environment:**
   ```bash
   cp .env.example .env
   # Ensure you populate GOOGLE_CLIENT_ID, MONGODB_URI, and TELEGRAM_BOT_TOKEN
   ```

2. **Start the local core infrastructure (MongoDB, Temporal, Ollama):**
   ```bash
   docker compose up -d
   ```

3. **Initialize the Python Backend:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Run the API and Temporal Worker (Requires 2 separate terminals):**
   ```bash
   # Terminal 1 (API)
   uvicorn backend.api.main:app --reload --port 8000
   
   # Terminal 2 (Worker)
   python -m backend.worker.main
   ```

5. **Run the React Frontend (Terminal 3):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. **Access the Application:**
   - User Dashboard: http://localhost:5173
   - Temporal UI: http://localhost:8233
   - FastAPI Swagger Docs: http://localhost:8000/docs

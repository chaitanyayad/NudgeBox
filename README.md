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

## ⚙️ Architecture & Technical Stack

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

### Core Technologies Used

1. **LLM Extraction Engine (Gemma 3)**
   - We use **Gemma 3** (served locally via Ollama) to parse unstructured email text into strict JSON schemas using `instructor` and Pydantic. By processing emails locally with open weights, we guarantee **zero data exfiltration** of highly sensitive personal emails.
2. **Durable Execution (Temporal)**
   - NudgeBox schedules reminders up to 7 days in the future. Traditional cron jobs would drop these if the server restarted. We utilize **Temporal** to orchestrate long-running sleep states. Workflows serialize their state to the database, ensuring zero reminders are lost even during catastrophic server failures.
3. **Distributed Tracing (Sentry)**
   - Both the FastAPI backend and Temporal worker are fully instrumented with the **Sentry SDK** for real-time error tracking and LLM hallucination monitoring.
4. **Multi-Channel Notifications (ElevenLabs)**
   - In addition to Telegram text reminders, NudgeBox dynamically generates an enthusiastic audio voice note using the **ElevenLabs** API at T-1 hour to hype the user up for their interview.
5. **Infrastructure as Code (Render)**
   - The entire stack is orchestrated via a `render.yaml` Blueprint for robust, reproducible deployments.

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

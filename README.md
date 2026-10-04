# NudgeBox

Never Miss an Interview or OA Again. A privacy-first agent that reads a job seeker's Gmail, finds interviews and online assessments (OAs), and nudges them at T-7 days, T-1 day, morning-of, and T-1 hour.

## Architecture
- **Backend**: Python, FastAPI, Temporal, Pydantic AI
- **Database**: MongoDB
- **LLM**: Gemma 3 (via Ollama)
- **Frontend**: Next.js (to be added)

## How to run locally

### Prerequisites
- Python 3.10+
- Docker
- Ollama (`ollama pull gemma3`)

### Setup

1. Copy `.env.example` to `.env` and fill in the values:
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
   
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

4. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the API:
   ```bash
   uvicorn backend.api.main:app --reload
   ```

6. Access the services:
   - API Docs: http://localhost:8000/docs
   - Temporal UI: http://localhost:8233
   - Health Check: http://localhost:8000/health


## Why Temporal? (The "Kill-Worker" Experiment)

Why didn't we just use a cron job or a background thread to send reminders?

NudgeBox schedules reminders up to **7 days** in the future. In a traditional architecture, if your server crashes, restarts, or deploys new code on day 3, all pending `setTimeout` calls or in-memory queues are wiped out. Your users would miss their interviews.

**Temporal provides Durable Execution.**

When a NudgeBox workflow says "sleep for 7 days," Temporal serializes the state of that function and saves it to the database. The worker process can safely be killed, restarted, or moved to another machine.

### Try it yourself:
1. Start the Temporal worker (`python backend/worker/main.py`)
2. Run the seed script to schedule an event 10 minutes in the future (`python backend/worker/seed_event.py --in-minutes 10`)
3. Check the Temporal UI (`http://localhost:8233`). You will see the workflow is in a "Sleeping" state.
4. **Kill the python worker process (Ctrl+C).** Notice how the workflow in the UI does *not* fail. It just waits.
5. Wait 9 minutes.
6. Restart the python worker process.
7. The worker immediately resumes exactly where it left off and fires the T-1h reminder!

You cannot do this reliably with CRON without writing complex, bug-prone state machines in your database. Temporal makes it look like a simple `asyncio.sleep()`.


## Cloud Deployment (Render)

We use Render's Blueprint (`render.yaml`) to deploy our microservices:
1. `nudgebox-api`: The FastAPI web server.
2. `nudgebox-frontend`: The Vite/React web dashboard.
3. `nudgebox-temporal-worker`: The Python background worker.

**Environment variables required in Render dashboard:**
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Your Google OAuth credentials
- `TOKEN_ENCRYPTION_KEY`: For envelope encryption of refresh tokens
- `MONGODB_URI`: Your MongoDB Atlas Connection String
- `TELEGRAM_BOT_TOKEN`: The bot token from @BotFather
- `OPENAI_API_KEY` / `OPENAI_BASE_URL`: Configuration for your chosen cloud GPU serving Gemma 3 (e.g. DigitalOcean, vLLM).
- `TEMPORAL_ADDRESS`: The gRPC endpoint for Temporal Cloud (or a self-hosted Temporal instance).

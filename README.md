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

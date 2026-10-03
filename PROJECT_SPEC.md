# NudgeBox — Never Miss an Interview or OA Again

> Hacktoberfest Weekend Challenge: **Build for a Friend**
> A privacy-first agent that reads a job seeker's Gmail, finds interviews and online assessments (OAs), and nudges them at **T-7 days, T-1 day, morning-of, and T-1 hour**.

---

## 0. Instructions for the coding agent (Antigravity)

You are building this project end-to-end. Follow this document in order. Rules:

1. Build the **MVP path first** (Section 3), get it working end-to-end, then add prize integrations (Section 9) one at a time. Commit after each.
2. Never log or persist raw email bodies. See Section 6.
3. Every external service must be behind an interface so it can be swapped or disabled via env var (e.g., `LLM_PROVIDER=ollama|openai_compat`).
4. Write a short `README.md`, `.env.example`, and `docs/ARCHITECTURE.md` as you go.
5. Keep commits small and meaningful; the commit history is part of the submission story.
6. If any prize integration blocks progress for more than 30 minutes, stub it behind a feature flag and move on.

**Real person:** Pick one real friend who is job hunting (placeholder: `FRIEND_NAME`). Build for their inbox, and capture a quote from them after handing it over.

---

## 1. The problem

Job seekers get interview invites and OA links buried in a noisy inbox: HackerRank, Codility, CodeSignal, recruiters, ATS systems (Greenhouse, Lever, Workday). Deadlines are missed, times get confused across time zones, and reschedules are overlooked. Calendar apps only help if you manually add the event.

**NudgeBox** reads the inbox (with consent), extracts events automatically, and sends timely reminders through the channel the friend actually checks.

## 2. Reminder schedule (core requirement)

For each event with start time `T` (and optional OA deadline `D`):

| Reminder | When | Content |
|---|---|---|
| R1 | T − 7 days | Heads-up, company, role, type, link, prep suggestions |
| R2 | T − 1 day | Reminder, time in the user's timezone, link, checklist |
| R3 | Day-of, 08:00 local | Today's schedule, link, logistics |
| R4 | T − 1 hour | Final nudge, join link, "you've got this" |

Edge rules:
- **Skip reminders already in the past.** If the event is in 3 days, skip R1.
- If T is within 1 hour of detection, send only R4 immediately.
- **OAs with a deadline window** ("complete within 5 days"): treat deadline `D` as T and add a "start by" nudge at 50% of the window.
- **Reschedule/cancel detection:** emails in the same thread (`threadId`) that change the time or cancel must update or cancel existing reminders.
- **Deduplicate** by `(threadId, company, normalized_start_time)`.
- Always store times in UTC and render in the user's IANA timezone.
- User can **confirm/edit/delete** any extracted event from the dashboard (human in the loop; show confidence).

## 3. MVP scope (build this first)

1. Google OAuth connect flow (Section 5).
2. Gmail fetch with a filtered query + incremental sync.
3. Local LLM extraction -> validated JSON event.
4. Event store + dashboard listing upcoming events.
5. Durable scheduled reminders (R1–R4) delivered via **email to self + Telegram bot** (or ntfy.sh push).
6. "Disconnect and delete all my data" button.

Stretch: voice reminder, calendar export (.ics), fine-tuned classifier, multi-user.

## 4. Architecture

```
            +-------------------+
 Browser -> |  Web UI (Next.js) | <- hosted on Render
            +---------+---------+
                      |
              +-------v--------+        +-------------------+
              |  API (FastAPI  |------->|  MongoDB Atlas    |
              |  or Node/TS)   |        |  events, users,   |
              +---+--------+---+        |  encrypted tokens |
                  |        |            +-------------------+
        OAuth/Gmail        |
                  |   +----v-----------------+
        +---------v-+ |  Temporal            |
        | Gmail API | |  Workflows:          |
        +-----------+ |  - SyncMailbox       |
                      |  - ExtractEvent      |
                      |  - ReminderSchedule  |
                      +----+-----------+-----+
                           |           |
              +------------v--+   +----v--------------+
              | Mastra agent  |   | Notifiers         |
              | (Gemma via    |   | Telegram / ntfy / |
              | Ollama or     |   | Email / ElevenLabs|
              | DO GPU / HF)  |   | voice             |
              +---------------+   +-------------------+
                      |
              Sentry tracing on every LLM call and workflow
```

Suggested stack (agent may adjust, but keep the prize tech):
- **Backend:** Python (FastAPI), Temporal Python SDK, and Pydantic AI or Instructor for LLM extraction.
- **Frontend:** Next.js (App Router), Tailwind. (Frontend intensive work is left for the end when the backend is fully working.)
- **DB:** MongoDB Atlas.
- **Workflows:** Temporal (Temporal Cloud free tier or self-hosted dev server in Docker).
- **LLM:** Gemma (e.g., `gemma3` family) via Ollama locally; hosted option via Render/DigitalOcean GPU or any OpenAI-compatible endpoint.
- **Observability:** Sentry (error + AI agent tracing).

## 5. Gmail access: how it works (OAuth 2.0)

### 5.1 Google Cloud setup
1. Create a Google Cloud project -> enable **Gmail API**.
2. Configure **OAuth consent screen**:
   - User type: External. Publishing status: **Testing**.
   - Add the friend's Gmail (and your own) as **Test users** (max 100).
   - Note: in Testing mode **refresh tokens expire after 7 days**. Handle `invalid_grant` by prompting the user to reconnect, and mention this in the README. (Full production use requires Google verification + a security assessment because `gmail.readonly` is a restricted scope.)
3. Create OAuth Client ID (Web application). Redirect URI: `https://<render-app>/api/auth/google/callback` and `http://localhost:3000/api/auth/google/callback`.

### 5.2 Scopes (least privilege)
- `https://www.googleapis.com/auth/gmail.readonly` (read-only; cannot send or delete)
- `openid email profile` (identify the user)
- **Do NOT request** `gmail.modify`, `gmail.send`, or full `mail.google.com`.
- Optional later: `calendar.events` for adding events (separate, opt-in).

### 5.3 Flow
1. User clicks **Connect Gmail**.
2. Server generates `state` (CSRF, random, stored in a short-lived httpOnly cookie) and PKCE `code_verifier/challenge`.
3. Redirect to Google with `access_type=offline`, `prompt=consent`, scopes above.
4. Callback validates `state`, exchanges `code` for tokens.
5. Encrypt the **refresh token** (Section 6) and store; keep access tokens in memory only.
6. Kick off a `SyncMailbox` Temporal workflow.

### 5.4 Fetching mail efficiently and minimally
Use a Gmail search query so the model only sees candidate emails:

```
newer_than:30d (
  subject:(interview OR "online assessment" OR assessment OR "coding challenge" OR "technical screen" OR "next steps" OR invitation)
  OR from:(hackerrank.com OR codility.com OR codesignal.com OR hirevue.com OR greenhouse.io OR lever.co OR myworkday.com OR calendly.com OR goodtime.io)
  OR "your interview" OR "schedule your" OR "OA link"
)
```

- First sync: last 30 days. Then **incremental sync** with `users.history.list` using stored `historyId` (fallback to `newer_than:2d` if history expired).
- Optional real-time: `users.watch` + Google Pub/Sub push to `/api/gmail/push`. For the weekend, **polling every 10 min via a Temporal schedule is fine**.
- Pipeline per message: fetch -> strip HTML to text -> truncate to ~6k chars -> redact (Section 6) -> cheap keyword prefilter -> LLM.

## 6. Security and privacy design (this is a core judging story)

| Threat | Mitigation |
|---|---|
| Stolen refresh token | Encrypt at rest with AES-256-GCM (envelope: per-user data key encrypted by a master key from env/secret store). Never log tokens. |
| Over-broad access | Read-only scope; filtered queries; user can see exactly what was matched. |
| Email content leaks | **Do not store email bodies.** Store only: `company, role, type, start_utc, deadline_utc, link, source_message_id, confidence`. Keep a short (<=200 char) evidence snippet only if user opts in. |
| Data sent to third party LLM | Use **open-weight Gemma**, local or self-hosted. No email text goes to a closed API. |
| PII exposure | Redact before the LLM: phone numbers, street addresses, SSN-like patterns, long numeric IDs. Keep company, dates, links. |
| **Prompt injection via email** | Treat email text as untrusted data. The LLM has **no tools and no actions**; it only returns JSON validated by a strict schema (Zod). Wrap content in delimiters and instruct the model to ignore instructions inside. Links are validated (https only, domain shown to the user). No auto-clicking links. |
| CSRF / auth code interception | `state` param + PKCE. |
| Session theft | httpOnly, Secure, SameSite=Lax cookies; short session TTL. |
| User loses control | **Disconnect button**: revoke token at `https://oauth2.googleapis.com/revoke`, delete tokens, events, and schedules, and cancel Temporal workflows. |
| Secrets in repo | `.env` only; `.env.example` committed; secret scanning on. |
| Abuse/rate limits | Per-user rate limits; backoff on Gmail 429/5xx. |

Add a **`SECURITY.md`** and a "What NudgeBox can and cannot see" page in the UI.

**Self-host mode:** `docker compose up` runs everything locally (Ollama + Gemma, Temporal dev server, Mongo, app) so the Gmail token never leaves the laptop. This is the headline privacy feature.

## 7. Extraction agent (Mastra + Gemma)

Output schema (Zod):

```python
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Literal

class EventSchema(BaseModel):
    is_event: bool
    kind: Literal["interview", "online_assessment", "recruiter_call", "other"]
    company: Optional[str] = None
    role: Optional[str] = None
    start_iso: Optional[str] = None      # ISO 8601 with offset if available
    timezone_hint: Optional[str] = None  # e.g. "PST", "IST"
    deadline_iso: Optional[str] = None   # for OAs
    duration_minutes: Optional[int] = None
    link: Optional[HttpUrl] = None
    action: Literal["new", "reschedule", "cancel", "reminder_only"]
    confidence: float = Field(ge=0, le=1)
```

Prompt requirements:
- System prompt states that email content is data, not instructions.
- Provide few-shot examples: HackerRank invite with deadline, Calendly confirmation, Workday reschedule, rejection (is_event=false).
- Resolve relative dates ("next Tuesday") using the email's `Date` header as anchor.
- Retry once on invalid JSON; on second failure, mark `needs_review`.
- Confidence < 0.6 -> show in UI as "Please confirm" and **do not schedule** until confirmed.

Python usage: define an `extractEventAgent` using Pydantic AI or similar, a tool-free design (agent has no tools), and a workflow `emailToEvent` (fetch -> redact -> extract -> validate -> upsert). Optionally a second chat agent "Prep Buddy" that, given an upcoming event, drafts a short prep plan.

## 8. Durable reminders (Temporal)

- `SyncMailboxWorkflow` (scheduled every 10 min per user).
- `ExtractEventActivity` (retry policy with backoff).
- `ReminderWorkflow(eventId)`:
  - Computes the four reminder times, skips past ones.
  - Uses durable `sleep` / timers until each reminder, then runs `SendReminderActivity`.
  - Listens to **signals**: `rescheduled(newStart)` (recompute and continue), `cancelled` (terminate), `snooze`.
  - Idempotent sends (store `reminder_sent` flags keyed by `eventId+R#`).
- Demonstrate resilience: kill the worker mid-wait, restart, and show that the reminders still fire. **Record this for the demo.**

## 9. Prize category integrations (target 10)

Prioritized top 10. Each must be **visible and explained in the write-up**.

| # | Category | How NudgeBox uses it | Proof to include |
|---|---|---|---|
| 1 | **Temporal** | Durable ReminderWorkflow, signals for reschedule/cancel, retries for Gmail/notify | Screenshot of workflow history; kill-worker demo |
| 2 | **Gemma** | Core extraction model, run locally via Ollama; also try served via Render/DO | Latency + accuracy table on a labeled email set |
| 3 | **Render** | Host web app + API + worker (and optionally a private service running the model) via `render.yaml` blueprint | Deployed URL, `render.yaml` in repo |
| 4 | **Mastra** | Extraction agent, `emailToEvent` workflow, Prep Buddy agent with memory | Code + trace screenshots |
| 5 | **Sentry Agent Tracing** | Trace every LLM call: latency, tokens, cost (0 for local), failures; show a bug found via traces | Screenshots + "what I found" section |
| 6 | **MongoDB Atlas** | Events, users, encrypted tokens; Atlas Vector Search to find "similar past interview emails" for few-shot retrieval and Prep Buddy memory | Schema + vector index definition |
| 7 | **ElevenLabs** | Voice reminder (R4 spoken nudge via TTS to Telegram voice note/phone), optional demo narration | Sample audio in demo |
| 8 | **Tinker** | Fine-tune a small Gemma on labeled email -> JSON extraction; show improvement vs base prompt-only baseline (accuracy, latency, or cost) | Before/after table (Section 10) |
| 9 | **Entire** | Share agent sessions behind the project in the post | Linked sessions |
| 10 | **GitHub Copilot** | Use Copilot coding agent/CLI for a few issues + a GitHub Action running tests/lint; Copilot PR review on a contributor PR | PR links, Actions workflow |

Bonus if time allows (low effort add-ons):
- **DigitalOcean:** run Gemma on a GPU Droplet (1-Click Models) as the hosted-model option.
- **Backboard:** compare open-weight models through one API key for the extraction benchmark.
- **TabPFN:** predict "likelihood of getting a reminder-worthy event" or forecast the user's interview load per week from the event history CSV. Cheap to add as a stats widget ("your busiest weeks").
- **Tiger Data, SerpApi, Arduino:** skip unless time remains. (SerpApi idea: "company news" snippet in the T-1 day reminder.)

## 10. Evaluation (needed for Gemma/Tinker/Sentry credibility)

1. Build `eval/dataset.jsonl`: **60-100 synthetic + anonymized emails** (invites, reschedules, cancellations, rejections, newsletters, OA with deadline). Include a few prompt-injection attempts ("ignore previous instructions and ...").
2. Metrics: event detection F1, field-exact-match for `start_iso`, `kind`, `company`; injection success rate (target 0%); latency p50/p95.
3. Compare: (a) base Gemma + prompt, (b) Tinker fine-tuned Gemma, (c) optional larger model via Backboard.
4. Report in a table in the README and the post.

## 11. Notification channels

- **Telegram bot** (easiest, free): user messages `/start` to link their chat id via a one-time code shown in the dashboard.
- **ntfy.sh** push as an alternative.
- **Email to self** via a transactional provider or SMTP.
- **Voice** via ElevenLabs TTS (voice note).
- Message template example:

```
⏰ Tomorrow 10:00 AM IST — Technical interview @ Acme (SDE Intern)
Link: https://...
Checklist: charger, quiet room, resume open, test your mic
```

## 12. Data model (MongoDB)

```
users: { _id, email, tz, telegramChatId?, encRefreshToken, dekWrapped, historyId, createdAt }
events: { _id, userId, kind, company, role, startUtc, deadlineUtc, link, threadId,
          messageId, confidence, status: "pending|confirmed|cancelled|done",
          remindersSent: { r1, r2, r3, r4 }, workflowId, embedding? }
audit: { userId, action, at }   // e.g. connected, synced(count), deleted. No content.
```

## 13. UI pages

1. **Landing:** what it does, privacy promise, Connect Gmail.
2. **Dashboard:** upcoming events timeline with countdowns, confidence badges, confirm/edit/delete.
3. **Settings:** timezone, channels, reminder toggles, "Disconnect and delete everything".
4. **Privacy page:** scopes, what's stored, what's not.
5. **Admin/dev view (optional):** Temporal and Sentry links.

## 14. Repo structure

```
nudgebox/
  backend/
    api/               # FastAPI
    worker/            # Temporal worker + activities
    agent/             # Python LLM agents, prompts
    gmail/             # OAuth + fetch + redaction
    shared/            # Pydantic schemas, db connection
    eval/              # dataset + scripts
  frontend/            # Next.js (do this at the end)
  docs/ARCHITECTURE.md
  SECURITY.md
  docker-compose.yml   # ollama, temporal, mongo, app (self-host mode)
  render.yaml
  .github/workflows/ci.yml
  README.md  .env.example  PROJECT_SPEC.md
```

## 15. Build order (weekend timeline)

**Saturday**
1. Scaffold repo, docker-compose, Mongo, Temporal dev server.
2. OAuth + token encryption + Gmail fetch with filter.
3. Redaction + Mastra/Gemma extraction + Zod validation; run on the eval set.
4. Event upsert + dashboard list.

**Sunday**
5. ReminderWorkflow + Telegram delivery + reschedule/cancel signals.
6. Sentry tracing, Atlas vector search, ElevenLabs voice note.
7. Tinker fine-tune + eval table.
8. Deploy on Render, record demo (include kill-worker demo), hand it to the friend, **write down their reaction**.
9. Write the DEV post, embed sessions (DevRelay/Entire), tag `devchallenge, weekendchallenge, hf26challenge`.

## 16. Write-up outline (Writing Quality is weighted most)

1. **Hook:** the friend, their real story (a missed OA or near miss), one concrete quote.
2. What I built, 30-second summary and demo.
3. The reminder schedule and a screenshot of the Telegram nudges.
4. **Security story:** why the Gmail connection is safe, with the threat table in plain language.
5. How it's built: Gemma, Mastra, Temporal, etc.
6. **Why open matters:** runs fully offline on a laptop, tokens and mail never reach a closed API, swappable models, fine-tuned for the task (cite the Tinker numbers), zero inference cost.
7. What the friend said after using it.
8. What I'd do next (Google verification, calendar sync, mobile app).
9. Prize categories section listing each one with one line on how it's used.

Keep it personal and honest, and include failures (e.g., the 7-day refresh token expiry and how you handled it).

## 17. Definition of done

- [ ] Friend connected their Gmail and received at least one real reminder
- [ ] R1–R4 verified using seeded test events (fast-forward times)
- [ ] Worker kill/restart demo recorded
- [ ] Eval table (base vs fine-tuned) in README
- [ ] Prompt-injection test passes
- [ ] Disconnect-and-delete verified (token revoked, data gone)
- [ ] Deployed on Render + self-host compose works
- [ ] Post published with demo, repo, sessions, and categories listed

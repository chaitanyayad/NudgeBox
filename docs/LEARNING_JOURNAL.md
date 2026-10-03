# NudgeBox Learning Journal

Welcome to your project journal! This document explains the **what**, **why**, and **how** of everything we've built so far. 

---

## 🏗 The Tech Stack (and why we chose it)

Our project uses a modern, highly scalable architecture tailored for hackathon prize categories:

1. **Python + FastAPI (Backend)**
   - **Why:** Python is the undisputed king of AI/LLM integrations. Since NudgeBox relies heavily on LLMs to extract data from emails, using Python allows us to seamlessly use tools like `pydantic-ai`. FastAPI is incredibly fast, naturally asynchronous, and gives us automatic API documentation out of the box.
2. **MongoDB + Motor (Database)**
   - **Why:** MongoDB's document model is perfect for storing varying types of event data (interviews vs. coding assessments vs. flights). Additionally, we need it to earn hackathon points for the **MongoDB Atlas Vector Search** prize category later when we build the LLM memory system! We use `motor` because it is the official asynchronous Python driver for MongoDB.
3. **Temporal (Workflow Engine)**
   - **Why:** Scheduling reminders a week in advance is notoriously hard. If a server crashes while a process is `sleep`ing, you lose the reminder. Temporal gives us **Durable Execution**—we can tell a script to literally `await sleep("7 days")` and Temporal will remember it, survive server reboots, and wake the code up exactly on time.
4. **Pydantic (Data Validation)**
   - **Why:** Pydantic enforces strict type rules. If untrusted data (like an LLM hallucination) tries to enter our system, Pydantic immediately rejects it, ensuring our database stays clean.

---

## 🛠 Task 1: Scaffolding the Infrastructure

### What we did:
- Spun up MongoDB, Temporal, and Ollama in a `docker-compose.yml` file.
- Initialized the Python project using a virtual environment (`.venv`) and a `requirements.txt` file.
- Built our very first FastAPI endpoint (`/health`) in `backend/api/main.py`.

### Why we did it:
Before writing any complex business logic, you need a stable environment. By using Docker, we avoid the dreaded "it works on my machine" problem. By creating a `/health` endpoint that actually pings the database, we have a fast way to verify our backend is fully operational.

### How we did it:
We used `uvicorn`, an ASGI server, to run FastAPI. The health endpoint uses the `motor` client to send a raw `ping` command to MongoDB.

---

## 🧱 Task 2: Data Modeling and Fail-Fast Configs

### What we did:
- Defined `User`, `AppEvent`, and `Audit` schemas in `backend/shared/models.py`.
- Wrote strict type checks and unit tests (`backend/shared/test_models.py`) to verify them using `pytest`.
- Built `backend/shared/env.py` using `pydantic-settings` to load our `.env` file.

### Why we did it:
1. **Data Integrity:** We want to know exactly what an "Event" looks like. We explicitly *omitted* storing raw email bodies in these models to enforce privacy by design. 
2. **Fail-Fast Configuration:** There is nothing worse than deploying an app, going to sleep, and realizing it crashed hours later because it was missing an API key. Our `env.py` script validates the environment the second the app starts. If a variable is missing, it crashes immediately and loudly.

### How we did it:
We used Pydantic's `BaseModel`. For example, in our tests, we intentionally passed an invalid "confidence" score (like `1.5` instead of a float between `0` and `1`), and asserted that Pydantic threw a `ValidationError`.

---

## 🔐 Task 3: The Token Encryption Vault

### What we did:
- Implemented **Envelope Encryption** using AES-256-GCM in `backend/gmail/crypto.py`.
- Created a script to generate a secure master key (`backend/gmail/generate_master_key.py`).
- Wrote tests to ensure the encryption survives round-trips and catches tampering.

### Why we did it:
NudgeBox reads people's emails. To do this, Google will give us a "Refresh Token". If our database is ever hacked, a hacker would steal everyone's tokens and gain access to their Gmails. 
We built the vault *before* touching any tokens.

### How we did it (Envelope Encryption):
We don't just encrypt the token with a master key. Instead:
1. We generate a random, unique **Data Encryption Key (DEK)** for *every single user*.
2. We encrypt the user's Refresh Token using their unique DEK.
3. We encrypt the DEK itself using our global `TOKEN_ENCRYPTION_KEY` (Master Key).
4. We store the encrypted token and the wrapped DEK in the database.

This limits the "blast radius" of a compromised key and allows us to securely rotate master keys in the future!

### What each function does under the hood:

**In `backend/gmail/crypto.py`**:
*   `_encrypt_with_key`: A private helper function. It takes a raw key and plaintext, generates a cryptographically secure random 12-byte IV (Initialization Vector), encrypts the data using `AES-256-GCM`, and returns a base64 encoded string combining the IV and the ciphertext. (AES-GCM automatically adds an "auth tag" to prevent tampering).
*   `_decrypt_with_key`: Reverses the above. It base64 decodes the string, slices off the first 12 bytes (the IV), and decrypts the rest. If a hacker flips even one character of the ciphertext, the built-in auth tag verification will fail and this function will throw an error.
*   `encrypt_secret`: The main public function. It generates a brand new 32-byte DEK (Data Encryption Key) just for this specific token. It calls `_encrypt_with_key` to encrypt the token using the DEK, then calls `_encrypt_with_key` again to encrypt the DEK using the global Master Key. It returns both pieces.
*   `decrypt_secret`: Reverses the envelope process. First, it decrypts the wrapped DEK using the Master Key. Then, it uses that newly unwrapped DEK to decrypt the actual token.

**In `backend/gmail/generate_master_key.py`**:
*   `main`: Uses Python's `os.urandom(32)` to generate 32 completely random bytes (256 bits), encodes them into a readable base64 string, and prints it out. We run this script exactly once to generate the super-secret `TOKEN_ENCRYPTION_KEY` that we put in our `.env` file!

---

## 🌐 Task 4: Google OAuth 2.0 and Session Management

### What we did:
- Implemented the full Google OAuth 2.0 authorization code flow from scratch using raw HTTP requests in `backend/api/auth.py`.
- Enforced strict scopes (`gmail.readonly`, `email`, `profile`).
- Configured PKCE (`code_verifier` and `code_challenge`) and state cookies to prevent CSRF and interception attacks.
- Exchanged the code for a Refresh Token, encrypted it using the master key from Task 3, and saved it in MongoDB.
- Created a secure JWT session cookie to log the user in.

### Why we did it:
- **No Passwords Allowed:** We never ask for a user's Google password. Storing passwords is a massive security risk. OAuth ensures we only get exactly what the user consents to (reading emails).
- **Background Access:** By specifically requesting `prompt=consent` and `access_type=offline`, Google issues us a **Refresh Token**. This special token never expires and allows our background agent to read emails at 3 AM while the user is asleep, bypassing 2FA!
- **PKCE:** Proof Key for Code Exchange (PKCE) ensures that even if a hacker intercepts our callback URL, they can't steal the token without knowing the secret `code_verifier` we generated in step 1.

### How we did it:
We used `httpx` for fast, asynchronous HTTP requests to Google's token endpoint. For session management, we used `PyJWT` to create a lightweight, stateless token signed by our master key.

---

## 📬 Task 5: Gmail Sync Workflow

### What we did:
- Built `backend/gmail/fetch.py` to connect to Google's API and securely fetch emails.
- Used a highly specific Gmail query to filter out spam and only grab interview/assessment emails from the last 30 days.
- Wrote a CLI tool (`backend/gmail/peek.py`) to safely test our connection and view the senders/subjects of candidate emails without starting the entire background server.

### What each function does under the hood:

**In `backend/gmail/fetch.py`**:
*   `get_access_token(user_id)`: Takes the user's ID, looks them up in MongoDB, and uses our encryption vault (from Task 3) to decrypt their Refresh Token. It then sends that Refresh Token to Google to get a brand new, valid 1-hour Access Token so we can read their emails.
*   `fetch_emails(user_id, max_results)`: Uses the access token to hit the Gmail API. It searches for emails matching our interview keywords (`"online assessment"`, `hackerrank.com`, etc). For each matching email, it downloads the full content, extracts the Subject and Sender headers, and safely strips out the messy HTML body down to raw text (truncated to 6000 characters).

**In `backend/gmail/peek.py`**:
*   `peek()`: A simple testing function. It grabs the first user from the database, calls `fetch_emails` for them, and prints out a clean list of the subjects and senders of the emails we found. It intentionally *doesn't* print the email bodies to keep your terminal readable.

### Bugs we faced and how we solved them:
1. **The MongoDB `ObjectId` bug:**
   - **The Error:** Our `peek.py` script crashed with `User not found`, even though it printed out the user's email perfectly a second before.
   - **The Cause:** `peek.py` passed the user's ID as a standard Python string (`"6789abc..."`). However, MongoDB stores IDs as a special binary object called `ObjectId`. When our backend asked MongoDB to find the string `"6789abc..."`, MongoDB couldn't find a match.
   - **The Fix:** We imported `ObjectId` from `bson` and wrapped the string (`ObjectId(user_id)`) before querying the database in `get_access_token`, which fixed the lookup instantly!
2. **The `403 Forbidden` Google Cloud bug:**
   - **The Error:** We successfully connected to Google, but Google threw a `403 Forbidden: Gmail API has not been used in project...` error and refused to give us the emails.
   - **The Cause:** By default, new Google Cloud Projects have all their APIs turned off to save resources. Even though we had the right tokens, the Gmail system was technically "switched off" for our app.
   - **The Fix:** We clicked the exact activation link provided in the error log, clicked "Enable Gmail API" in the Google Cloud Console, and waited 30 seconds for the servers to update. The next time we ran the script, it worked perfectly!

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

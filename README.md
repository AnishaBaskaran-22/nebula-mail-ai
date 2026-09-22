# Nebula Mail AI

AI-powered mail web application for the Nebula KnowLab hiring task. The assistant controls the UI: it can compose/fill emails, search and filter the inbox, open matching messages, and start a context-aware reply.

## Architecture

```text
React + Vite
   │
   ├── Mail UI (Inbox / Sent / Compose / Detail)
   ├── Filter + search controls
   └── Mail Copilot sidebar
          │ REST command parsing
          ▼
FastAPI
   ├── Gmail service (OAuth + Gmail API)
   ├── Assistant controller (Ollama + deterministic fallback)
   └── WebSocket event bus
          ▲
          │ Google Pub/Sub push
Gmail watch ────────────────────
```

### Key decisions
- **Gmail API + OAuth**: real send/receive mail without storing the user's Gmail password.
- **FastAPI**: keeps provider access and AI orchestration separate from the browser.
- **Ollama**: local LLM by default, matching the goal of keeping the assistant controllable and easy to run. A deterministic fallback parser keeps core commands usable if Ollama is unavailable.
- **UI-driving assistant**: assistant responses are structured actions (`compose`, `search`, `open`, `reply`, `filter`) rather than free-form chatbot answers.
- **Pub/Sub + WebSocket**: Gmail watch notifications reach FastAPI, which pushes a `mail_changed` event to connected clients so the inbox can refresh without a manual refresh.

## Prerequisites

- Python 3.11+
- Node.js 20+
- A Google Cloud project with Gmail API enabled
- OAuth client credentials for a web/desktop application
- Ollama installed locally (optional; the fallback parser works without it)

## Google setup

1. Open Google Cloud Console and create/select a project.
2. Enable **Gmail API**.
3. Configure the OAuth consent screen.
4. Create an OAuth client and download the JSON.
5. Rename the downloaded file to `credentials.json` and place it in `backend/`.
6. For real-time push, create a Pub/Sub topic and grant Gmail permission to publish to it. Set the full topic name in `GOOGLE_PUBSUB_TOPIC`.
7. Expose `POST /api/push/gmail` through a public HTTPS URL when using Google Pub/Sub push delivery (for example through a deployed backend or a secure tunnel during development).

## Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
uvicorn app.main:app --reload --port 8000
```

On first connection, the backend opens Google's OAuth flow. `token.json` is generated locally and is ignored by Git.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Ollama

```bash
ollama pull llama3.2:3b
ollama serve
```

The default model is configured in `backend/.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

## Assistant examples

- `Send an email to john@example.com with subject 'Meeting Tomorrow' and body 'Let's meet at 3pm'`
- `Show me emails from the last 10 days`
- `Find the email from Sarah about the project update`
- `Open the latest email from David`
- `Reply to this`
- `Show only unread emails from this week`

The important behavior is visible UI control: compose fields are filled in the compose view and search/open commands update the main mail view.

## What I would improve with more time

- Gmail History API delta sync instead of refreshing the current list after every push notification.
- Full conversation/thread rendering and attachment support.
- Confirmation mode before sending assistant-created emails.
- More robust structured tool calling and validation for complex natural-language date/sender filters.
- Production OAuth/session storage and encrypted token storage.
- Automated unit/integration tests and CI.
- Production deployment with HTTPS, Pub/Sub push verification, monitoring, and error tracking.

## Submission checklist

- [ ] Add real Google OAuth credentials locally (never commit them)
- [ ] Configure Pub/Sub and a public HTTPS push endpoint for real-time sync
- [ ] Run backend + frontend
- [ ] Capture screenshots/video for the README
- [ ] Create a **private** GitHub repository
- [ ] Invite `Aswath363`, `akshaiP`, and `ashwanthnebula`
- [ ] Push the repository

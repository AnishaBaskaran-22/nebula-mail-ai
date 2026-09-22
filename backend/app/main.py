from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .config import FRONTEND_URL
from .gmail_service import list_messages, get_message, send_message, mark_read, start_watch, get_credentials
from .assistant import parse_command
import base64
import json

clients = set()

app = FastAPI(title="Nebula Mail AI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_URL], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class SendRequest(BaseModel):
    to: str
    subject: str
    body: str
    in_reply_to: str | None = None

class AssistantRequest(BaseModel):
    message: str
    context: dict = {}

@app.get("/api/health")
def health():
    return {"ok": True, "gmail_connected": bool(get_credentials())}

@app.get("/api/auth/status")
def auth_status():
    return {"connected": bool(get_credentials())}

@app.post("/api/auth/connect")
def connect():
    try:
        get_credentials() or __import__('app.gmail_service', fromlist=['authorize']).authorize()
        return {"connected": True}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/api/emails")
def emails(q: str = "", label: str = "INBOX", max_results: int = 50):
    try:
        return {"emails": list_messages(q, label, max_results)}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/emails/{message_id}")
def email(message_id: str):
    try:
        item = get_message(message_id)
        if item["unread"]: mark_read(message_id)
        return item
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/send")
def send(req: SendRequest):
    try:
        return send_message(req.to, req.subject, req.body, req.in_reply_to)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/watch")
def watch():
    try: return start_watch()
    except Exception as e: raise HTTPException(400, str(e))

@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        clients.discard(ws)

@app.post("/api/push/gmail")
async def gmail_push(payload: dict):
    # Google Pub/Sub sends a notification when Gmail history changes.
    raw = payload.get("message", {}).get("data", "")
    decoded = {}
    if raw:
        try:
            decoded = json.loads(base64.b64decode(raw).decode("utf-8"))
        except Exception:
            pass
    dead = []
    for ws in clients:
        try:
            await ws.send_json({"type":"mail_changed", "historyId": decoded.get("historyId")})
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)
    return {"received": True, "historyId": decoded.get("historyId")}

@app.post("/api/assistant")
async def assistant(req: AssistantRequest):
    command = await parse_command(req.message)
    return command

import base64
import os
from email.message import EmailMessage
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from .config import GOOGLE_CLIENT_SECRET_FILE, GOOGLE_TOKEN_FILE, SCOPES, GOOGLE_PUBSUB_TOPIC


def get_credentials() -> Credentials | None:
    creds = None
    if os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(GOOGLE_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds


def authorize() -> Credentials:
    creds = get_credentials()
    if creds and creds.valid:
        return creds
    if not os.path.exists(GOOGLE_CLIENT_SECRET_FILE):
        raise FileNotFoundError(
            f"Missing {GOOGLE_CLIENT_SECRET_FILE}. Download your Google OAuth Desktop/Web client JSON and place it in backend/."
        )
    flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")
    with open(GOOGLE_TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    return creds


def service():
    return build("gmail", "v1", credentials=authorize(), cache_discovery=False)


def _headers(msg: dict[str, Any]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}


def _body(payload: dict[str, Any]) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
        nested = _body(part)
        if nested:
            return nested
    return ""


def normalize_message(msg: dict[str, Any]) -> dict[str, Any]:
    h = _headers(msg)
    labels = msg.get("labelIds", [])
    return {
        "id": msg["id"],
        "threadId": msg.get("threadId"),
        "sender": h.get("from", "Unknown sender"),
        "to": h.get("to", ""),
        "subject": h.get("subject", "(no subject)"),
        "date": h.get("date", ""),
        "snippet": msg.get("snippet", ""),
        "body": _body(msg.get("payload", {})),
        "unread": "UNREAD" in labels,
        "labels": labels,
    }


def list_messages(query: str = "", label: str = "INBOX", max_results: int = 50) -> list[dict[str, Any]]:
    svc = service()
    res = svc.users().messages().list(userId="me", labelIds=[label], q=query, maxResults=max_results).execute()
    ids = res.get("messages", [])
    result = []
    for item in ids:
        msg = svc.users().messages().get(userId="me", id=item["id"], format="full").execute()
        result.append(normalize_message(msg))
    return result


def get_message(message_id: str) -> dict[str, Any]:
    msg = service().users().messages().get(userId="me", id=message_id, format="full").execute()
    return normalize_message(msg)


def send_message(to: str, subject: str, body: str, in_reply_to: str | None = None) -> dict[str, Any]:
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = in_reply_to
    message.set_content(body)
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent = service().users().messages().send(userId="me", body={"raw": encoded}).execute()
    return {"id": sent["id"], "threadId": sent.get("threadId")}


def mark_read(message_id: str) -> None:
    service().users().messages().modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}).execute()


def start_watch() -> dict[str, Any]:
    if not GOOGLE_PUBSUB_TOPIC:
        raise ValueError("GOOGLE_PUBSUB_TOPIC is not configured")
    return service().users().watch(userId="me", body={"labelIds": ["INBOX"], "topicName": GOOGLE_PUBSUB_TOPIC}).execute()

import json
import re
import httpx
from .config import OLLAMA_BASE_URL, OLLAMA_MODEL

SYSTEM = '''You are the UI controller for an email application. Return ONLY valid JSON with keys action and args.
Allowed actions:
compose {to, subject, body}
search {query, label, unread_only}
open {query}
reply {body}
filter {query, unread_only}
No markdown. If a value is unknown, use an empty string.''' 


def _fallback(text: str) -> dict:
    t = text.strip()
    low = t.lower()
    if low.startswith("send an email") or low.startswith("compose") or "send email" in low:
        email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", t)
        subject = re.search(r"subject\s*['\"]([^'\"]+)['\"]", t, re.I)
        body = re.search(r"body\s*['\"]([^'\"]+)['\"]", t, re.I)
        return {"action":"compose","args":{"to":email.group(0) if email else "","subject":subject.group(1) if subject else "","body":body.group(1) if body else ""}}
    if "reply" in low and "this" in low:
        return {"action":"reply","args":{"body":""}}
    if "open" in low and ("latest" in low or "email from" in low):
        return {"action":"open","args":{"query":t}}
    return {"action":"search","args":{"query":t,"label":"INBOX","unread_only":"unread" in low}}


async def parse_command(text: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json={"model": OLLAMA_MODEL,"system":SYSTEM,"prompt":text,"stream":False,"format":"json"})
            r.raise_for_status()
            parsed = json.loads(r.json().get("response", "{}"))
            if parsed.get("action") in {"compose","search","open","reply","filter"}:
                return parsed
    except Exception:
        pass
    return _fallback(text)

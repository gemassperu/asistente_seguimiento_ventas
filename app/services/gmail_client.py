import os, base64
from typing import Optional, Dict, List
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.services.gmail_auth_mem import get_gmail_service_in_memory
from dotenv import load_dotenv
load_dotenv()

SENDER = os.getenv("GMAIL_SENDER")
APP_ENV = os.getenv("APP_ENV", "local")


def _service() -> any:
    token_json = os.getenv("GOOGLE_TOKEN_JSON")
    force_oauth = (APP_ENV == "local")

    res = get_gmail_service_in_memory(
        credentials_json_env="GOOGLE_CREDENTIALS_JSON",
        token_json=token_json,
        force_oauth_if_missing_token=force_oauth,
    )

    new_token = res.get("token_json")
    if new_token and APP_ENV == "local":
        print("[GMAIL] token actualizado. Copia este JSON a GOOGLE_TOKEN_JSON:")
        print(new_token)

    return res["service"]

def send_email(to: str, subject: str, body: str,
               thread_id: Optional[str] = None,
               in_reply_to_rfc_message_id: Optional[str] = None) -> Dict:
    svc = _service()
    msg = EmailMessage()
    msg["To"] = to
    msg["From"] = "gemassperu@gmail.com"
    msg["Subject"] = subject
    msg.set_content(body)

    # Para RESPONDER en el mismo hilo de forma más robusta:
    if in_reply_to_rfc_message_id:
        msg["In-Reply-To"] = in_reply_to_rfc_message_id
        msg["References"] = in_reply_to_rfc_message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw}
    if thread_id:
        payload["threadId"] = thread_id

    return svc.users().messages().send(userId="me", body=payload).execute()

def list_messages(query: str, max_results: int = 50) -> List[Dict]:
    svc = _service()
    resp = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    return resp.get("messages", [])

def get_message(msg_id: str) -> Dict:
    svc = _service()
    return svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
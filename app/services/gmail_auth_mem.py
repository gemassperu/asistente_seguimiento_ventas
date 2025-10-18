# app/services/gmail_auth_mem.py
from __future__ import annotations
import os
import json
import typing as t

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from dotenv import load_dotenv
load_dotenv()
from google.auth.exceptions import RefreshError


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

class GmailAuthResult(t.TypedDict, total=False):
    service: t.Any 
    token_json: t.Optional[str]

def _parse_json_env(var_name: str) -> dict:
    """
    Lee un JSON desde una variable de entorno. Acepta:
    - JSON plano
    - JSON con comillas escapadas (limpia y parsea)
    """
    val = os.getenv(var_name)
    if not val:
        raise RuntimeError(f"Falta variable de entorno: {var_name}")
    try:
        return json.loads(val)
    except Exception:
        cleaned = val.strip().strip('"').replace('\\"', '"')
        return json.loads(cleaned)

def _creds_from_token_json(token_json_str: str) -> Credentials:
    data = json.loads(token_json_str)
    return Credentials.from_authorized_user_info(data, scopes=SCOPES)


def get_gmail_service_in_memory(
    *,
    credentials_json_env: str = "GOOGLE_CREDENTIALS_JSON",
    token_json: t.Optional[str] = None,
    force_oauth_if_missing_token: bool = True,
) -> GmailAuthResult:

    client_info = _parse_json_env(credentials_json_env)
    creds: t.Optional[Credentials] = None

    if token_json:
        creds = _creds_from_token_json(token_json)

    if not creds and force_oauth_if_missing_token:
        flow = InstalledAppFlow.from_client_config(
            {"installed": client_info["installed"]} if "installed" in client_info else client_info,
            SCOPES
        )
        creds = flow.run_local_server(port=0)
        new_token_json = creds.to_json()
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return {"service": service, "token_json": new_token_json}

    if not creds:
        raise RuntimeError("No hay token y force_oauth_if_missing_token=False. Proporciona token_json.")

    updated_token_json: t.Optional[str] = None
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())           # intenta refresh en memoria
                updated_token_json = creds.to_json()
            except RefreshError as e:
                if force_oauth_if_missing_token:
                    flow = InstalledAppFlow.from_client_config(
                        {"installed": client_info["installed"]} if "installed" in client_info else client_info,
                        SCOPES
                    )
                    creds = flow.run_local_server(port=0)  # reautoriza en local
                    updated_token_json = creds.to_json()
                else:
                    raise RuntimeError(
                        "El refresh token es inválido o fue revocado. "
                        "Genera un nuevo GOOGLE_TOKEN_JSON en local (OAuth) y vuelve a ejecutar."
                    ) from e
        else:
            if force_oauth_if_missing_token:
                flow = InstalledAppFlow.from_client_config(
                    {"installed": client_info["installed"]} if "installed" in client_info else client_info,
                    SCOPES
                )
                creds = flow.run_local_server(port=0)
                updated_token_json = creds.to_json()
            else:
                raise RuntimeError(
                    "Token inválido y sin refresh_token. Reautoriza en local para obtener un nuevo token."
                )

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    result: GmailAuthResult = {"service": service}
    if updated_token_json:
        result["token_json"] = updated_token_json
    return result

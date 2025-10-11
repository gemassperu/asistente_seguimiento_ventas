from __future__ import annotations
import argparse, base64
from datetime import date
from typing import Optional, Dict

from app.db.base import get_db
from app.db.crud import (
    get_today_checkins_by_thread,
    replace_tasks,
    mark_replied
)
from app.services.gmail_client import list_messages, get_message
from app.services.extractor_ai import extract_structured
from dotenv import load_dotenv

load_dotenv()


def _decode_text(full_msg: Dict) -> Optional[str]:
    payload = full_msg.get("payload", {})
    parts = payload.get("parts") or []
    if parts:
        for p in parts:
            if p.get("mimeType") == "text/plain":
                data = p.get("body", {}).get("data")
                if data:
                    return base64.urlsafe_b64decode(data).decode(errors="ignore")
    else:
        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode(errors="ignore")
    return None


def _get_subject(full_msg: Dict) -> str:
    for h in full_msg.get("payload", {}).get("headers", []):
        if h.get("name") == "Subject":
            return h.get("value", "")
    return ""


def _get_employee_name(db, employee_id: str) -> str:
    """
    Supabase: obtenemos name/email por id (checkins trae employee_id).
    Devuelve name si existe; si no, email; si no, el id como fallback.
    """
    res = (
        db.table("employees")
        .select("name,email")
        .eq("id", employee_id)
        .limit(1)
        .execute()
    )
    row = (res.data or [{}])[0]
    return (row.get("name") or "").strip() or row.get("email") or str(employee_id)


def run(the_date: date):
    # 1) buscar respuestas del día (ajusta el query si cambiaste el subject)
    q = f'subject:"[Seguimiento diario] {the_date:%Y-%m-%d}" newer_than:2d to:me in:inbox'
    msgs = list_messages(q, max_results=50)
    print(f"Mensajes candidatos: {len(msgs)}")
  
    processed = 0
    saved = 0

    with get_db() as db:
        for m in msgs:
            full = get_message(m["id"])
            thread_id = full["threadId"]

            # 2) Mapear thread -> checkin de HOY
            chk = get_today_checkins_by_thread(db, thread_id)
            if not chk:
                continue  # no corresponde a un hilo nuestro de hoy

            # 3) Decodificar texto + preparar contexto
            body_text = _decode_text(full)
            if not body_text:
                continue
            subject = _get_subject(full)
            default_date = the_date.strftime("%Y-%m-%d")

            # employees ahora es tabla aparte; resolvemos el nombre por id
            employee_name = _get_employee_name(db, chk["employee_id"])

            # 4) Ejecutar IA -> estructura validada
            extracted = extract_structured(subject, body_text, default_date, employee_name)

            # 5) Mostrar resultado
            print("—" * 60)
            print("Empleado:", employee_name)
            print("Fecha:", extracted.for_date)
            for i, t in enumerate(extracted.tasks, 1):
                print(
                    f"  {i}. {t.title} | {t.status} | "
                    f"progress={t.progress} | next={t.next_steps} | blocker={t.blocker}"
                )
            processed += 1
            print(extracted.tasks)
            # checkin_id ahora es string (ligado a threadId según tu flujo)
            replace_tasks(
                db,
                checkin_id=chk["id"],
                tasks=[t.model_dump(exclude_none=True) for t in extracted.tasks]
            )
            mark_replied(db, chk["id"])
            saved += 1

    print("—" * 60)
    print(f"Procesados: {processed} | Guardados: {saved} ")


if __name__ == "__main__":
    run(date.today())
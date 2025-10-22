from __future__ import annotations

from typing import Iterable, Optional, List, Dict, Any, Tuple
from datetime import date, datetime

# --------------------------
# Employees
# --------------------------

def get_employees(client, active_only: bool = True) -> list:
    q = client.table("employees").select("*")
    if active_only:
        q = q.eq("active", True)
    res = q.order("id", desc=False).execute()
    return res.data or []

# --------------------------
# Checkins
# --------------------------
def upsert_checkin(
    client,
    *,
    the_date: date,
    employee,
    thread_id: Optional[str],
    first_message_id: Optional[str],
) -> any:

    if not (thread_id or first_message_id):
        raise ValueError("Se requiere thread_id (o first_message_id) para generar el id del check-in.")

    checkin_id = thread_id or first_message_id

    payload = {
        "id": checkin_id,
        "date": str(the_date),
        "employee_id": employee["id"],
        "thread_id": thread_id,
        "first_message_id": first_message_id,
    }

    res = (
        client.table("checkins")
        .upsert(payload, on_conflict="date,employee_id", returning="representation")
        .execute()
    )
    chk = (res.data or [None])[0]

    if chk:
        # Completar campos si venían nulos
        patch = {}
        if thread_id and not chk.get("thread_id"):
            patch["thread_id"] = thread_id
        if first_message_id and not chk.get("first_message_id"):
            patch["first_message_id"] = first_message_id
        if patch:
            res2 = (
                client.table("checkins")
                .update(patch)
                .eq("date", str(the_date))
                .eq("employee_id", employee["id"])
                .execute()
            )
            if res2.data:
                return res2.data[0]
            # fallback: leerlo después del update (por RLS/Prefer headers)
            res3 = (
                client.table("checkins")
                .select("*")
                .eq("date", str(the_date))
                .eq("employee_id", employee["id"])
                .limit(1)
                .execute()
            )
            return (res3.data or [chk])[0]
        return chk

    # Si por alguna razón no devolvió representación, re-lee
    res3 = (
        client.table("checkins")
        .select("*")
        .eq("date", str(the_date))
        .eq("employee_id", employee["id"])
        .limit(1)
        .execute()
    )
    rows = res3.data or []
    return rows[0] if rows else None

def get_pending_tasks_for_employee(client,employee_id):
    res = (
        client.table("tasks")
        .select("title,status,progress,next_steps,blocker, checkins:checkin_id(employee_id)")
        .eq("checkins.employee_id", employee_id)
        .not_.is_("checkins", "null")
        .neq("status","completado")
        .execute()
    )
    rows = res.data or []
    return rows

def get_today_tasks(client):
    res = (
        client.table("tasks")
        .select("title,status,progress,next_steps,blocker, employee:employee_id(name)")
        .eq("status", "null")
        .execute()
    )
    rows = res.data or []
    return rows

def get_today_checkins_by_thread(client, thread_id: str) -> any:
    today = date.today()
    res = (
        client.table("checkins")
        .select("*")
        .eq("date", str(today))
        .eq("thread_id", thread_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None

def mark_replied(client, checkin_id: str, ts: Optional[datetime] = None) -> None:
    when = (ts or datetime.now()).isoformat()
    _ = (
        client.table("checkins")
        .update({"reply_received_at": when})
        .eq("id", checkin_id)
        .execute()
    )

def get_pending_checkins(client) -> list:

    # 1) empleados activos
    today = date.today()
    res = (
        client.table("checkins")
        .select("id,thread_id,date,employee:employee_id(name,email,active)")
        .eq("date", str(today))
        .eq("employee.active", True)
        .is_("reply_received_at", "null")
        .execute()
    )
    return res.data or []

# --------------------------
# Tasks
# --------------------------
def replace_tasks(client, *, checkin_id: str, tasks: Iterable[dict]) -> list:
    """
    Borra todas las tareas del checkin y vuelve a insertarlas (idempotente a nivel de checkin).
    Normaliza 'status' y 'progress'.
    """

    if tasks == []:
        return []
    
    created = []
    batch: List[Dict[str, Any]] = []

    for t in tasks:
        title = (t.get("title") or "").strip()
        if not title:
            continue

        status = (t.get("status") or "en_progreso").strip().lower()
        if status not in {"pendiente", "en_progreso", "completado"}:
            status = "en_progreso"

        progress = t.get("progress")
        if isinstance(progress, int):
            progress = max(0, min(100, progress))
        else:
            progress = None
        res = (client.table("tasks").select("*").eq("title", title).neq("checkin_id",checkin_id).execute()).data or []
        if not res :
            observation = ""
            id = 0
        elif res[0].get("progress") == progress:
            observation = "No se progresó en la tarea desde el último check-in"
            id =  res[0].get("id")
        else:
            observation = ""
            id = res[0].get("id")
        batch.append(
            {   
                "checkin_id": checkin_id,
                "title": title,
                "status": status,
                "progress": progress,
                "next_steps": t.get("next_steps"),
                "blocker": t.get("blocker"),
                "observation": observation
            }
        )
        _ = client.table("tasks").delete().eq("id",id).execute()

    if batch:
        res = client.table("tasks").insert(batch, returning="representation").execute()
        created = res.data or []

    return created
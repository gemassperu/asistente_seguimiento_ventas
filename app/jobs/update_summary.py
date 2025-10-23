# scripts/upsert_summary.py
from typing import List, Dict, Any
from app.db.base import get_db
from dotenv import load_dotenv

load_dotenv()


def fetch_source_rows(sb) -> List[Dict[str, Any]]:
    res = (
        sb.table("tasks")
        .select(
            "title,status,observation,"
            "checkin:checkin_id(employee:employee_id(name))"
        )
        .execute()
    )
    return res.data or []

def _norm(s: Any) -> str:
    return (s or "").strip()

def build_summary_payload(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        emp = (r.get("checkin") or {}).get("employee") or {}
        employee_name = _norm(emp.get("name"))
        task_title    = _norm(r.get("title"))
        if not employee_name or not task_title:
            # Requeridos para la PK compuesta
            continue
        out.append({
            "employee_name": employee_name,
            "task_title": task_title,
            "status": _norm(r.get("status")),
            "observation": (r.get("observation") or None),
        })
    return out

def chunked(iterable, size=500):
    buf = []
    for item in iterable:
        buf.append(item)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def upsert_summary(sb, payloads: List[Dict[str, Any]]) -> int:
    total = 0
    for batch in chunked(payloads, size=500):
        (
            sb.table("summary")
            .upsert(
                batch,
                on_conflict="employee_name,task_title",
                returning="minimal"
            )
            .execute()
        )
        total += len(batch)
    return total

def main():
    with get_db() as db:
        source = fetch_source_rows(db)
        payloads = build_summary_payload(source)
        if not payloads:
            print("No hay filas para upsert en summary.")
            return
        total = upsert_summary(db, payloads)
    print(f"Upsert summary OK — filas procesadas: {total}")

if __name__ == "__main__":
    main()

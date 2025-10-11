# scripts/test_integration_send.py
from datetime import date

from app.db.base import get_db
from app.db.crud import get_employees, upsert_checkin, get_pending_tasks_for_employee

from app.emails.templates import render_daily
from app.services.gmail_client import send_email


def main():
    today = date.today()
    total = 0
    ok = 0
    skipped = 0
    failed = 0

    with get_db() as db:
        employees = get_employees(db, active_only=True)
        if not employees:
            raise RuntimeError("No hay empleados activos en la tabla employees.")

        for emp in employees:
            total += 1
            emp_name = (emp.get("name") or "").strip() or emp.get("email") or f"Empleado {emp.get('id')}"
            emp_email = (emp.get("email") or "").strip()
            emp_id = (emp.get("id") or "").strip()

            if not emp_email:
                print(f"Saltado (sin email): id={emp_id} nombre={emp_name}")
                skipped += 1
                continue

            subject = f"Seguimiento diario - {today:%Y-%m-%d} — {emp_name}"
            tasks = get_pending_tasks_for_employee(db,emp_id)
            body = render_daily(emp_name, today,tasks)

            try:
                sent = send_email(emp_email, subject, body)
                chk = upsert_checkin(
                    db,
                    the_date=today,
                    employee=emp,
                    thread_id=sent.get("threadId"),
                    first_message_id=sent.get("id"),
                )
                print(
                    "OK envío:",
                    emp_email,
                    "| thread:", (chk or {}).get("thread_id"),
                    "| msg:", (chk or {}).get("first_message_id"),
                )
                ok += 1
            except Exception as e:
                print(f"Error enviando a {emp_email}: {e!r}")
                failed += 1

    print("-" * 60)
    print(f"Total empleados: {total} | Enviados OK: {ok} | Saltados: {skipped} | Fallidos: {failed}")


if __name__ == "__main__":
    main()
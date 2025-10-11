from datetime import date

from app.db.base import get_db
from app.db.crud import get_pending_checkins
from app.services.gmail_client import send_email
from app.emails.templates import body_reminder_text

def main():
    today = date.today()
    with get_db() as db:
        pending_checkins = get_pending_checkins(db)
        subject = f"Recordatorio de check-in para {today:%Y-%m-%d}"
        if not pending_checkins:
            print("No hay check-ins pendientes para hoy.")
            return
        for checkin in pending_checkins:
            employee = checkin["employee"]
            body = body_reminder_text(employee["name"])
            try:
                sent = send_email(employee["email"], subject, body, thread_id=checkin["thread_id"])
                print(f"Recordatorio enviado a {employee['email']}")
            except Exception as e:
                print(f"Error enviando recordatorio a {employee['email']}: {e}")

if __name__ == "__main__":
    main()
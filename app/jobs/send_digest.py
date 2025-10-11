from datetime import date
from app.db.base import get_db
from app.db.crud import get_today_tasks
from app.services.gmail_client import send_email
from app.services.extractor_ai import extract_tasks

def main():
    today = date.today()
    
    with get_db() as db:
        tasks = get_today_tasks(db)
        if not tasks:
            print("No hay tareas para hoy.")
            return
        
        subject = f"Resumen diario - Tareas para {today:%Y-%m-%d}"
        text_body = extract_tasks(str(tasks))
        try:
            sent = send_email("enzo.ip.98@gmail.com", subject, text_body)
        except:
            print(f"Error enviando reporte de gerencia")
if __name__ == "__main__":
    main()
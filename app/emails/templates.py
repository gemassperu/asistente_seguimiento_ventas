from __future__ import annotations
from datetime import date
from textwrap import dedent

def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def _task_line(v):
    # Convierte None a texto amigable
    return "" if v is None else str(v)

def _render_task_yaml(t: dict) -> str:
    title      = _task_line(t.get("title", "<tarea>"))
    status     = _task_line(t.get("status", "pendiente"))
    progress   = _task_line(t.get("progress", 0))
    next_steps = _task_line(t.get("next_steps", ""))
    blocker    = _task_line(t.get("blocker", "ninguno"))
    status = str(status).lower()
    if status not in {"pendiente", "en_progreso", "completado"}:
        status = "pendiente"
    try:
        progress = int(progress)
    except:
        progress = 0

    return dedent(f"""\
      - Titulo: {title}
      - Estado: {status}
      - Progreso: {progress}
      - Siguientes pasos: {next_steps}
      - Bloqueantes: {blocker}""")

# =========
# 09:00 - Seguimiento diario
# =========

def body_daily_text(d: date, employee_name: str, tasks) -> str:
    tasks = tasks or []
    if not tasks:
        return f"""Hola {employee_name},

Por favor responde a este correo con la actualización de tus actividades.

Aquí te dejo un modelo para que puedas usarlo como referencia

Colaborador: {employee_name}
Fecha: {_fmt(d)}
Tareas:
- Titulo: <tarea>
- Estado: pendiente|en_progreso|completado
- Progreso: 0
- Siguientes pasos: <pasos>
- Bloqueantes: ninguno

¡Gracias!
"""
    pending = [t for t in tasks if str(t.get("status", "")).lower() != "completado"]

    # Si todas están completadas, igual mostramos el listado como referencia
    show_list = pending if pending else tasks

    rendered = "\n".join(_render_task_yaml(t) for t in show_list)

    return f"""Hola {employee_name},

Estas son tus tareas pendientes/en progreso al { _fmt(d) }.
Por favor responde actualizando cada una (Titulo, Estado, Siguientes pasos y Bloqueantes) y agrega cualquier tarea nueva.

Colaborador: {employee_name}
Fecha: {_fmt(d)}
Tareas existentes:
{rendered}

tareas_nuevas:
- Titulo: <tarea>
- Estado: pendiente|en_progreso|completado
- Progreso: 0
- Siguientes pasos: <pasos>
- Bloqueantes: ninguno

¡Gracias!
"""

# =========
# 11:00 - Recordatorio (mismo hilo)
# =========

def body_reminder_text(employee_name: str) -> str:
    return f"""Hola {employee_name},

Esto es un recordatorio amable de que todavía no has respondido al correo de seguimiento diario, recuerda hacerlo antes de las 6 pm.
"""

# =========
# Render helpers
# =========

def render_daily(name: str, d: date, tasks) -> str:
    return body_daily_text(d, name,tasks)

def render_reminder(name: str, d: date) -> str:
    return body_reminder_text(name)
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
      - title: {title}
        status: {status}
        progress: {progress}
        next_steps: {next_steps}
        blocker: {blocker}""")

# =========
# 09:00 - Seguimiento diario
# =========

def body_daily_text(d: date, employee_name: str, tasks) -> str:
    tasks = tasks or []
    if not tasks:
        return f"""Hola {employee_name},

Por favor responde con este bloque (puedes editarlo). Si lo prefieres, responde en texto libre;
nuestro sistema interpretará el contenido automáticamente:

empleado: {employee_name}
fecha: {_fmt(d)}
tareas:
- title: <tarea>
    status: pendiente|en_progreso|completado
    progress: 0
    next_steps: <pasos>
    blocker: ninguno

¡Gracias!
"""
    pending = [t for t in tasks if str(t.get("status", "")).lower() != "completado"]

    # Si todas están completadas, igual mostramos el listado como referencia
    show_list = pending if pending else tasks

    rendered = "\n".join(_render_task_yaml(t) for t in show_list)

    return f"""Hola {employee_name},

Estas son tus tareas pendientes/en progreso al { _fmt(d) }.
Por favor responde actualizando cada una (status, progress, next_steps y blocker) y agrega cualquier tarea nueva.

empleado: {employee_name}
fecha: {_fmt(d)}
tareas_existentes:
{rendered}

tareas_nuevas:
- title: <tarea>
    status: pendiente|en_progreso|completado
    progress: 0
    next_steps: <pasos>
    blocker: ninguno

¡Gracias!
"""

# =========
# 11:00 - Recordatorio (mismo hilo)
# =========

def body_reminder_text(employee_name: str) -> str:
    return f"""Hola {employee_name},

Recordatorio amable: aún no recibimos tu actualización de hoy.
¿Nos ayudas respondiendo a este hilo? ¡Gracias!
"""

# =========
# Render helpers
# =========

def render_daily(name: str, d: date, tasks) -> str:
    return body_daily_text(d, name,tasks)

def render_reminder(name: str, d: date) -> str:
    return body_reminder_text(name)
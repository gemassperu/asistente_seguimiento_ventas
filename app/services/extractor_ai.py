# app/services/extractor_ai.py
from __future__ import annotations
import os, json, re
from typing import Any, Dict
from pydantic import ValidationError
from openai import OpenAI
from ..parsing.schema import ExtractedReply, TaskItem
from dotenv import load_dotenv
import os

load_dotenv()  # carga variables de .env
PROMPT_ID = os.environ.get('OPEN_AI_PROMPT_ID')
SUMMARY_PROMPT_ID = os.environ.get('SUMMARY_PROMPT_ID')
SUMMARY_PROMPT_VERSION = os.environ.get('SUMMARY_PROMPT_VERSION')
PROMPT_VERSION = os.environ.get('OPEN_AI_PROMPT_VERSION')
# El cliente lee OPENAI_API_KEY del entorno (puedes cargar .env en app/db/base.py)
client = OpenAI()

def _build_message(subject: str, default_date: str, employee: str, body_text: str) -> str:
    """
    Unifica el contexto del correo en un único bloque para tu Prompt guardado.
    Mantiene etiquetas claras; si tu prompt espera otros nombres, ajústalos aquí.
    """
    return f"""
ASUNTO: {subject}
FECHA_REFERENCIA: {default_date}
EMPLEADO: {employee}

CUERPO:
{body_text}
""".strip()

def extract_structured(subject: str, body_text: str, default_date: str, employee: str) -> ExtractedReply:
    """
    Usa tu Prompt guardado en OpenAI para extraer un JSON con:
      - for_date (YYYY-MM-DD)
      - tasks: [{title, status, progress, next_steps, blocker}]
    Devuelve un objeto validado por Pydantic (ExtractedReply).
    """
    message = _build_message(subject, default_date, employee, body_text)

    # Llamada tal cual tu snippet: responses.create con 'prompt' (Prompt guardado)
    resp = client.responses.create(
        prompt={
            "id": PROMPT_ID,
            "version": PROMPT_VERSION,
            "variables": {
                "message": message
            }
        }
    )

    raw = resp.output_text  # el prompt guardado debe responder SOLO JSON
    data: Dict[str, Any] = json.loads(raw)

    # Normalizaciones ligeras por si tu prompt usa claves en español
    # Esperamos: {"employee": str|null, "for_date": "YYYY-MM-DD", "tasks":[...]}
    if "fecha" in data and "for_date" not in data:
        data["for_date"] = data.pop("fecha")
    if "empleado" in data and "employee" not in data:
        data["employee"] = data.pop("empleado")
    if "tareas" in data and "tasks" not in data:
        data["tasks"] = data.pop("tareas")

    # Normaliza tasks internas (progreso -> progress, siguientes pasos -> next_steps)
    if isinstance(data.get("tasks"), list):
        norm_tasks = []
        for t in data["tasks"]:
            if "progreso" in t and "progress" not in t:
                t["progress"] = t.pop("progreso")
            if "siguientes pasos" in t and "next_steps" not in t:
                t["next_steps"] = t.pop("siguientes pasos")
            if "estado" in t and "status" not in t:
                t["status"] = t.pop("estado")
            if "bloqueo" in t and "blocker" not in t:
                t["blocker"] = t.pop("bloqueo")
            norm_tasks.append(t)
        data["tasks"] = norm_tasks

    return ExtractedReply(**data)

def extract_tasks(tasks):
    
    resp = client.responses.create(
        prompt={
            "id": SUMMARY_PROMPT_ID,
            "version": SUMMARY_PROMPT_VERSION,
            "variables": {
                "message": tasks
            }
        }
    )
    raw = resp.output_text
    return raw

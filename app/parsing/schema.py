from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import date

class TaskItem(BaseModel):
    title: str
    status: Literal['pendiente', 'en_progreso', 'completado'] = 'en_progreso'
    progress: Optional[int] = Field(default=None, ge=0, le=100)
    next_steps: Optional[str] = None
    blocker: Optional[str] = None

class ExtractedReply(BaseModel):
    employee: Optional[str] = None
    for_date: date
    tasks: List[TaskItem]
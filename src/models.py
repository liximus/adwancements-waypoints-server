from typing import Any, Optional
from pydantic import BaseModel, Field


class WaypointModel(BaseModel):
    id: str = Field(..., description="Уникальный идентификатор вейпоинта")
    title: str = Field(default="", description="Название вейпоинта")
    description: str = Field(default="", description="Описание вейпоинта")
    icon: str = Field(default="minecraft:grass_block", description="Иконка предмета")
    frame: str = Field(default="task", description="Тип рамки: task, goal или challenge")
    parent: str = Field(default="", description="ID родительской ачивки")
    x: Optional[float] = Field(default=None, description="Координата X")
    y: Optional[float] = Field(default=None, description="Координата Y")
    z: Optional[float] = Field(default=None, description="Координата Z")
    author: Optional[str] = Field(default=None, description="Ник игрока")

    class Config:
        extra = "allow"  # Разрешаем любые дополнительные поля мода


class WaypointRequestPayload(BaseModel):
    data: WaypointModel


class DeclinePayload(BaseModel):
    reason: Optional[str] = Field(default=None, description="Причина отклонения")

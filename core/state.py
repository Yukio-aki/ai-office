from dataclasses import dataclass
from typing import List, Optional
import json


@dataclass
class ProjectState:
    """Состояние проекта - минимум текста, только данные"""

    # Основное
    task: str = ""
    project_type: str = "html"  # html, react, script
    complexity: str = "simple"  # simple, medium, complex

    # Требования
    colors: List[str] = None
    text: str = ""

    # Анимация (НОВОЕ)
    animation_type: str = ""  # "grow", "move", "fade", "pulse", "none"
    animation_speed: str = "medium"  # "slow", "medium", "fast"
    animation_element: str = ""  # "line", "circle", "pattern", "background"

    # Дополнительно
    features: List[str] = None

    # Статус
    status: str = "new"  # new, planning, coding, done, failed
    error: Optional[str] = None

    def __post_init__(self):
        if self.colors is None:
            self.colors = []
        if self.features is None:
            self.features = []

    def to_json(self) -> str:
        """Компактное JSON представление"""
        return json.dumps({
            "type": self.project_type,
            "colors": self.colors,
            "text": self.text,
            "anim_type": self.animation_type,
            "anim_speed": self.animation_speed,
            "anim_element": self.animation_element,
            "features": self.features,
            "complexity": self.complexity,
            "status": self.status
        }, ensure_ascii=False)

    def to_prompt(self) -> str:
        """Короткий промпт для модели"""
        parts = []

        # Цвета
        if self.colors:
            parts.append(f"colors: {', '.join(self.colors)}")

        # Текст
        if self.text:
            parts.append(f"text: {self.text}")

        # Анимация (НОВОЕ)
        if self.animation_type and self.animation_type != "none":
            anim_parts = [f"animation: {self.animation_type}"]
            if self.animation_speed:
                anim_parts.append(self.animation_speed)
            if self.animation_element:
                anim_parts.append(f"on {self.animation_element}")
            parts.append(" ".join(anim_parts))

        # Особенности
        if self.features:
            parts.append(f"features: {', '.join(self.features)}")

        return ". ".join(parts) if parts else "simple html page"
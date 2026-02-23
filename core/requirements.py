from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class ProjectRequirements:
    """Структурированные требования к проекту"""

    # Основное
    initial_task: str = ""
    clarified_task: str = ""
    project_type: str = "unknown"  # website, parser, bot, script, animation

    # Технологии
    technologies: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)

    # Визуал
    colors: List[str] = field(default_factory=list)
    style: str = "abstract"  # abstract, geometric, organic, minimal, futuristic, dark
    mood: str = "dark"  # dark, light

    # Анимация
    animation_speed: str = "medium"  # slow, medium, fast
    features: List[str] = field(default_factory=list)

    # Референсы
    examples: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)

    # Метаданные
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    dialog_history: List[dict] = field(default_factory=list)

    def update(self):
        """Обновляет время последнего изменения"""
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Конвертирует в словарь для сохранения"""
        return {
            'initial_task': self.initial_task,
            'clarified_task': self.clarified_task,
            'project_type': self.project_type,
            'technologies': self.technologies,
            'forbidden': self.forbidden,
            'colors': self.colors,
            'style': self.style,
            'mood': self.mood,
            'animation_speed': self.animation_speed,
            'features': self.features,
            'examples': self.examples,
            'references': self.references,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ProjectRequirements':
        """Создает объект из словаря"""
        req = cls(
            initial_task=data.get('initial_task', ''),
            clarified_task=data.get('clarified_task', ''),
            project_type=data.get('project_type', 'unknown'),
            technologies=data.get('technologies', []),
            forbidden=data.get('forbidden', []),
            colors=data.get('colors', []),
            style=data.get('style', 'abstract'),
            mood=data.get('mood', 'dark'),
            animation_speed=data.get('animation_speed', 'medium'),
            features=data.get('features', []),
            examples=data.get('examples', []),
            references=data.get('references', [])
        )
        if 'created_at' in data:
            req.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            req.updated_at = datetime.fromisoformat(data['updated_at'])
        return req

    def generate_project_name(self) -> str:
        """Генерирует имя проекта на основе требований"""
        parts = []

        # Тип проекта
        type_names = {
            'website': 'Site',
            'parser': 'Parser',
            'bot': 'Bot',
            'script': 'Script',
            'animation': 'Anim'
        }
        parts.append(type_names.get(self.project_type, 'Project'))

        # Стиль
        if self.style != 'abstract':
            parts.append(self.style.capitalize())

        # Цвет
        if self.colors:
            main_color = self.colors[0].capitalize()
            parts.append(main_color)

        # Анимация
        if self.features:
            main_feature = self.features[0].replace(' ', '_')
            parts.append(main_feature[:15])  # Ограничиваем длину

        # Соединяем и очищаем
        name = '_'.join(parts)
        # Убираем спецсимволы
        name = ''.join(c for c in name if c.isalnum() or c == '_')

        return name

    def get_confidence_score(self) -> float:
        """Вычисляет уверенность в готовности ТЗ (0-100)"""
        score = 0
        total = 0

        # Тип проекта (обязательно)
        total += 20
        if self.project_type != 'unknown':
            score += 20

        # Цвета (обязательно для визуала)
        total += 20
        if len(self.colors) > 0:
            score += 20

        # Технологии (важно)
        total += 15
        if len(self.technologies) > 0:
            score += 15

        # Особенности (хорошо бы иметь)
        total += 15
        if len(self.features) >= 2:
            score += 15
        elif len(self.features) == 1:
            score += 7

        # Стиль
        total += 10
        if self.style != 'abstract':
            score += 10

        # Скорость анимации
        total += 10
        if self.animation_speed != 'medium':
            score += 5
        else:
            score += 10

        # Запреты (плюс)
        total += 5
        if len(self.forbidden) > 0:
            score += 5

        # Примеры (плюс)
        total += 5
        if len(self.examples) > 0:
            score += 5

        return (score / total) * 100 if total > 0 else 0

    def is_ready(self, min_confidence: float = 70.0) -> bool:
        """Проверяет, достаточно ли информации для запуска"""
        return self.get_confidence_score() >= min_confidence

    def get_missing_fields(self) -> List[str]:
        """Возвращает список недостающих полей"""
        missing = []

        if self.project_type == 'unknown':
            missing.append("тип проекта")
        if len(self.colors) == 0:
            missing.append("цветовая гамма")
        if len(self.technologies) == 0:
            missing.append("технологии")
        if len(self.features) < 2:
            missing.append("ключевые функции")

        return missing
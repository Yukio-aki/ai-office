from dataclasses import dataclass
from typing import List


@dataclass
class ComplexityLevel:
    """Определяет сложность задачи и требования к агентам"""

    level: int  # 1-5
    name: str
    max_tokens: int
    required_agents: List[str]
    min_confidence: float


class ComplexityAnalyzer:
    """Анализирует сложность задачи на основе требований"""

    @staticmethod
    def analyze(requirements: dict) -> ComplexityLevel:
        """Определяет уровень сложности"""

        score = 0

        # Технологии повышают сложность
        tech_count = len(requirements.get('technologies', []))
        score += tech_count * 2

        # Особенности
        features_count = len(requirements.get('features', []))
        score += features_count

        # Стиль (абстрактное сложнее)
        if requirements.get('style') in ['abstract', 'organic']:
            score += 3

        # Анимация
        if requirements.get('animation_speed'):
            score += 2

        # Запреты (нужно учитывать)
        forbidden_count = len(requirements.get('forbidden', []))
        score += forbidden_count

        # Определяем уровень
        if score <= 3:
            return ComplexityLevel(1, "Trivial", 500, ["developer"], 0.6)
        elif score <= 6:
            return ComplexityLevel(2, "Simple", 1000, ["planner", "developer"], 0.7)
        elif score <= 10:
            return ComplexityLevel(3, "Moderate", 2000, ["planner", "developer", "reviewer"], 0.8)
        elif score <= 15:
            return ComplexityLevel(4, "Complex", 3000, ["planner", "developer", "reviewer", "translator"], 0.85)
        else:
            return ComplexityLevel(5, "Very Complex", 4000, ["planner", "developer", "reviewer", "translator"], 0.9)
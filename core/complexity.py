from dataclasses import dataclass
from typing import List


@dataclass
class ComplexityLevel:
    """Определяет сложность задачи и требования к агентам"""

    level: int  # 1-5
    name: str
    description: str
    required_agents: List[str]  # какие агенты нужны
    max_iterations: int  # сколько попыток дается
    min_confidence: float  # минимальная уверенность


class ComplexityAnalyzer:
    """Анализирует сложность задачи"""

    @staticmethod
    def analyze(task: str) -> ComplexityLevel:
        """Определяет уровень сложности по ключевым словам"""
        task_lower = task.lower()
        score = 0

        # Ключевые слова, повышающие сложность
        complex_indicators = [
            'анимац', 'animation', 'react', 'vue', 'angular',
            'баз дан', 'database', 'api', 'сервер', 'server',
            'регистрац', 'login', 'auth', 'пользовател', 'user',
            'нескольк', 'multiple', 'страниц', 'pages'
        ]

        for word in complex_indicators:
            if word in task_lower:
                score += 1

        # Длина задачи тоже влияет
        words = task.split()
        if len(words) > 20:
            score += 1
        if len(words) > 50:
            score += 2

        # Определяем уровень
        if score <= 1:
            return ComplexityLevel(
                level=1,
                name="Trivial",
                description="Простая задача, достаточно разработчика",
                required_agents=["developer"],
                max_iterations=1,
                min_confidence=0.7
            )
        elif score <= 3:
            return ComplexityLevel(
                level=2,
                name="Simple",
                description="Нужен план и разработка",
                required_agents=["planner", "developer"],
                max_iterations=2,
                min_confidence=0.8
            )
        elif score <= 5:
            return ComplexityLevel(
                level=3,
                name="Moderate",
                description="Нужен переводчик, план и разработка",
                required_agents=["translator", "planner", "developer"],
                max_iterations=3,
                min_confidence=0.85
            )
        else:
            return ComplexityLevel(
                level=4,
                name="Complex",
                description="Полная цепочка с проверкой",
                required_agents=["translator", "planner", "developer", "reviewer"],
                max_iterations=3,
                min_confidence=0.9
            )
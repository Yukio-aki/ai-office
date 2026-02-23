import json
from core.llm_extractor import LLMExtractor
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import re
import sys

# Добавляем путь к корню проекта
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from session_logger import get_logger


class ProjectManager:
    """Агент-менеджер для сбора требований и ведения диалога"""

    def __init__(self, session_id=None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.dialog_history = []
        self.requirements = {
            'initial_task': '',
            'clarified_task': '',
            'project_type': 'unknown',
            'technologies': [],
            'forbidden': [],
            'features': [],
            'colors': [],
            'examples': [],
            'references': [],
            'animation_speed': 'medium',
            'mood': 'dark',
            'style': 'abstract'
        }
        self.llm_extractor = LLMExtractor()

        # Инициализируем логгер
        self.logger = get_logger()

        # Категории для анализа ответов
        self.categories = {
            'type': ['сайт', 'страниц', 'html', 'парс', 'бот', 'скрипт', 'утилит', 'приложени'],
            'tech': ['react', 'vue', 'angular', 'bootstrap', 'tailwind', 'python', 'js', 'javascript'],
            'color': ['черн', 'бел', 'сер', 'темн', 'светл', 'фиолет', 'син', 'красн', 'зелен'],
            'animation': ['медлен', 'средн', 'быстр', 'движ', 'анимац'],
            'style': ['абстракт', 'геометрич', 'органическ', 'минимал', 'футурист', 'дарк', 'фэнтези'],
            'effect': ['переход', 'негатив', 'черно-бел', 'grayscale', 'hover', 'клик'],
            'forbidden': ['не используй', 'без', 'запрещ', 'не надо', 'кроме']
        }

        # Папка для сохранения диалогов
        self.dialog_dir = Path(__file__).parent.parent / "dialog_history"
        self.dialog_dir.mkdir(exist_ok=True)

    def start_dialog(self, initial_task: str):
        """Начинает диалог с пользователем"""
        self.requirements['initial_task'] = initial_task
        self._add_to_history("user", initial_task)

        welcome_message = f"""🎨 **Привет! Я помогу воплотить твою идею в жизнь.**

Я вижу, ты хочешь: **"{initial_task}"**

**Что дальше:**
1. Просто **описывай** что хочешь (коротко или подробно)
2. Я **проанализирую** и задам уточняющие вопросы
3. Когда будет достаточно инфы — **сформирую ТЗ**

**С чего начнем?** Например, расскажи подробнее о:
- 🎯 Тип проекта (сайт, анимация, эффект)
- 🎨 Цветовая гамма
- ⚡ Анимация (как должна двигаться)
- 📎 Примеры (ссылки или описания)

Я понимаю свободную речь, просто пиши что хочешь! 👇
"""

        self._add_to_history("system", welcome_message)
        self._save_dialog()
        return welcome_message

    def _add_to_history(self, role: str, message: str):
        """Добавляет сообщение в историю диалога и логгер"""
        timestamp = datetime.now()

        # Добавляем в историю
        self.dialog_history.append({
            'role': role,
            'message': message,
            'timestamp': timestamp.isoformat()
        })

        # Сохраняем в логгер
        if role == 'user':
            self.logger.log_chat("Пользователь (диалог)", message[:200])
        else:
            self.logger.log_chat("Менеджер", message[:200])

        self.logger.log(f"[ДИАЛОГ] {role}: {message[:100]}...")

    def process_response(self, user_response: str) -> Dict[str, Any]:
        """Обрабатывает ответ пользователя и обновляет требования"""
        self._add_to_history("user", user_response)

        # Анализируем ответ
        self._analyze_response_deep(user_response)

        # Сохраняем диалог
        self._save_dialog()

        # Проверяем, достаточно ли информации
        if self._is_ready_to_proceed():
            final_spec = self._generate_final_spec()
            self._add_to_history("system", f"✅ **Отлично! У меня достаточно информации.**\n\n```\n{final_spec}\n```")
            self._save_dialog()
            return {
                'status': 'ready',
                'spec': final_spec,
                'dialog': self.dialog_history
            }

        # Анализируем чего не хватает и задаем вопрос
        next_question = self._generate_smart_question()
        if next_question:
            self._add_to_history("system", next_question)
            self._save_dialog()
            return {
                'status': 'continue',
                'question': next_question,
                'dialog': self.dialog_history
            }
        else:
            final_spec = self._generate_final_spec()
            return {
                'status': 'ready',
                'spec': final_spec,
                'dialog': self.dialog_history
            }

    def _analyze_response_deep(self, response: str):
        """Глубокий анализ ответа пользователя с помощью LLM"""

        # Используем LLM для извлечения требований
        extracted = self.llm_extractor.extract(response, self.requirements)

        # Обновляем requirements извлеченными данными
        if extracted.get('project_type'):
            self.requirements['project_type'] = extracted['project_type']

        if extracted.get('technologies'):
            self.requirements['technologies'].extend(extracted['technologies'])

        if extracted.get('forbidden'):
            self.requirements['forbidden'].extend(extracted['forbidden'])

        if extracted.get('colors'):
            self.requirements['colors'].extend(extracted['colors'])

        if extracted.get('style'):
            self.requirements['style'] = extracted['style']

        if extracted.get('animation_speed'):
            self.requirements['animation_speed'] = extracted['animation_speed']

        if extracted.get('features'):
            self.requirements['features'].extend(extracted['features'])

        if extracted.get('mood'):
            self.requirements['mood'] = extracted['mood']

        # Удаляем дубликаты
        self.requirements['technologies'] = list(set(self.requirements['technologies']))
        self.requirements['colors'] = list(set(self.requirements['colors']))
        self.requirements['features'] = list(set(self.requirements['features']))
        self.requirements['forbidden'] = list(set(self.requirements['forbidden']))

    def _generate_smart_question(self) -> str:
        """Генерирует умный вопрос на основе того, чего не хватает"""

        # Словарь с вопросами по категориям
        question_bank = {
            'type': "🎯 **Уточни тип проекта:**\n   - Сайт/страница\n   - Анимация/эффект\n   - Другое",
            'colors': "🎨 **Какие цвета предпочитаешь?**\n   - Темные/светлые\n   - Конкретные оттенки\n   - Градиенты",
            'animation': "⚡ **Как должна двигаться анимация?**\n   - Плавно/медленно\n   - Средне\n   - Быстро/динамично",
            'style': "✨ **Какой стиль ближе?**\n   - Абстрактный\n   - Геометрический\n   - Органический/природный",
            'effects': "🌟 **Нужны спецэффекты?**\n   - Свечение\n   - Частицы\n   - Переходы\n   - Черно-белый режим",
            'examples': "📎 **Есть примеры/референсы?**\n   Скинь ссылки или опиши словами"
        }

        # Проверяем чего не хватает
        missing = []

        if self.requirements['project_type'] == 'unknown':
            missing.append('type')
        elif len(self.requirements['colors']) == 0:
            missing.append('colors')
        elif 'animation_speed' not in self.requirements:
            missing.append('animation')
        elif self.requirements['style'] == 'abstract' and len(self.requirements['features']) < 2:
            missing.append('effects')
        elif len(self.requirements['examples']) == 0 and len(self.dialog_history) < 4:
            missing.append('examples')

        if missing:
            # Берем первый недостающий элемент
            return question_bank.get(missing[0], "Расскажи подробнее, что ты хочешь?")

        return None

    def _is_ready_to_proceed(self) -> bool:
        """Проверяет, достаточно ли информации"""

        # Минимальные требования
        required = [
            self.requirements['project_type'] != 'unknown',
            len(self.requirements['colors']) > 0,
            self.requirements['initial_task'] != ''
        ]

        # Для сайтов нужно больше деталей
        if self.requirements['project_type'] == 'website':
            required.append(len(self.requirements['features']) >= 2)

        # Если диалог уже длинный - пора закругляться
        if len(self.dialog_history) > 6:
            return True

        return all(required)

    def _generate_final_spec(self) -> str:
        """Генерирует финальное техническое задание"""

        spec = f"""# 📋 ТЕХНИЧЕСКОЕ ЗАДАНИЕ

## 🎯 Исходный запрос:
{self.requirements['initial_task']}

## 📌 Уточненное описание:

### Тип проекта:
**{self.requirements['project_type']}** - {'Веб-сайт с анимацией' if self.requirements['project_type'] == 'website' else 'Интерактивный проект'}

### 🎨 Цветовая гамма:
{', '.join(self.requirements['colors']) if self.requirements['colors'] else 'Темные тона (по умолчанию)'}

### ⚡ Анимация:
Скорость: **{self.requirements.get('animation_speed', 'medium')}**
Стиль: **{self.requirements.get('style', 'abstract')}**

### ✨ Ключевые функции:
"""
        for feature in self.requirements['features']:
            spec += f"- {feature}\n"

        if self.requirements['technologies']:
            spec += f"\n### 🛠 Технологии:\n"
            for tech in self.requirements['technologies']:
                spec += f"- {tech}\n"

        if self.requirements['forbidden']:
            spec += f"\n### 🚫 Запрещено использовать:\n"
            for forbid in self.requirements['forbidden']:
                spec += f"- {forbid}\n"

        if self.requirements['examples']:
            spec += f"\n### 📎 Референсы:\n"
            for ex in self.requirements['examples']:
                spec += f"- {ex}\n"

        spec += f"""
## 📊 Детали реализации:

1. **Структура:** Один HTML файл
2. **Анимация:** {self.requirements.get('animation_speed', 'medium')} скорость, {self.requirements.get('style', 'abstract')} стиль
3. **Эффекты:** {', '.join(self.requirements['features']) if self.requirements['features'] else 'Базовые'}
4. **Цвета:** {', '.join(self.requirements['colors']) if self.requirements['colors'] else 'Темная тема'}

## 💡 Дополнительно:
- Код должен работать сразу после открытия
- Без внешних зависимостей (если не указано иное)
- Комментарии в коде
"""

        return spec

    def _save_dialog(self):
        """Сохраняет историю диалога в файл"""
        filename = self.dialog_dir / f"dialog_{self.session_id}.json"

        # Подготавливаем данные для сохранения
        data = {
            'session_id': self.session_id,
            'requirements': self.requirements,
            'dialog': self.dialog_history,
            'timestamp': datetime.now().isoformat(),
            'message_count': len(self.dialog_history)
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def load_previous_dialog(self, session_id: str):
        """Загружает предыдущий диалог"""
        filename = self.dialog_dir / f"dialog_{session_id}.json"
        if filename.exists():
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.requirements = data['requirements']
                self.dialog_history = data['dialog']
                return True
        return False

    def get_summary(self) -> Dict[str, Any]:
        """Возвращает краткое описание текущего состояния"""
        return {
            'session_id': self.session_id,
            'messages': len(self.dialog_history),
            'ready': self._is_ready_to_proceed(),
            'type': self.requirements['project_type'],
            'colors': len(self.requirements['colors']),
            'features': len(self.requirements['features'])
        }
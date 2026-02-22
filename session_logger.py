import os
from datetime import datetime
from pathlib import Path
import traceback
import json


class SessionLogger:
    """Логирует всё, что происходит во время сессии"""

    def __init__(self, session_name=None):
        # Создаём папку для логов
        self.log_dir = Path(__file__).parent / "session_logs"
        self.log_dir.mkdir(exist_ok=True)

        # Имя сессии
        if session_name is None:
            session_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_name = session_name

        # Основные файлы логов
        self.log_file = self.log_dir / f"session_{session_name}.log"
        self.chat_file = self.log_dir / f"chat_{session_name}.md"
        self.errors_file = self.log_dir / f"errors_{session_name}.log"
        self.state_file = self.log_dir / f"state_{session_name}.json"

        # Начинаем сессию
        self._start_session()
        print(f"✅ Логгер инициализирован: {self.log_file}")

    def _start_session(self):
        """Инициализация сессии"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"{'=' * 60}\n")
            f.write(f"SESSION START: {datetime.now()}\n")
            f.write(f"{'=' * 60}\n\n")

        with open(self.chat_file, 'w', encoding='utf-8') as f:
            f.write(f"# Чат-логи сессии {self.session_name}\n\n")
            f.write(f"**Начало:** {datetime.now()}\n\n")
            f.write("---\n\n")

        with open(self.errors_file, 'w', encoding='utf-8') as f:
            f.write(f"# Ошибки сессии {self.session_name}\n\n")
            f.write(f"**Начало:** {datetime.now()}\n\n")

        # Инициализируем state файл
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump({
                'session_start': datetime.now().isoformat(),
                'session_name': self.session_name,
                'states': []
            }, f, indent=2, ensure_ascii=False)

    def log(self, message, category="INFO"):
        """Запись обычного лога"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] [{category}] {message}\n"

        # В файл
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

        print(f"📝 {log_entry.strip()}")

    def log_chat(self, speaker, message):
        """Запись сообщения в чат-формате"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(self.chat_file, 'a', encoding='utf-8') as f:
            f.write(f"### [{timestamp}] {speaker}\n\n")
            f.write(f"{message}\n\n")
            f.write("---\n\n")

        print(f"💬 [{speaker}] {message[:50]}...")

    def log_error(self, error, context=None):
        """Запись ошибки с контекстом"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(self.errors_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'=' * 40}\n")
            f.write(f"ERROR at {timestamp}\n")
            f.write(f"{'=' * 40}\n")
            f.write(f"Type: {type(error).__name__}\n")
            f.write(f"Message: {str(error)}\n")
            if context:
                f.write(f"Context: {context}\n")
            f.write(f"Traceback:\n{traceback.format_exc()}\n")

        self.log(f"❌ ERROR: {str(error)}", category="ERROR")

    def log_state(self, key, value):
        """Запись состояния в JSON"""
        try:
            # Читаем существующий файл
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
            else:
                state_data = {'states': []}

            # Добавляем новое состояние
            state_data['states'].append({
                'timestamp': datetime.now().isoformat(),
                'key': key,
                'value': str(value),
                'type': str(type(value).__name__)
            })

            # Сохраняем
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.log_error(e, f"Failed to log state: {key}")

    def end_session(self):
        """Завершение сессии"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'=' * 60}\n")
            f.write(f"SESSION END: {datetime.now()}\n")
            f.write(f"{'=' * 60}\n")

        with open(self.chat_file, 'a', encoding='utf-8') as f:
            f.write(f"\n**Конец:** {datetime.now()}\n")

        self.log(f"✅ Сессия {self.session_name} завершена")

        return {
            'session': str(self.log_file),
            'chat': str(self.chat_file),
            'errors': str(self.errors_file),
            'state': str(self.state_file),
            'dir': str(self.log_dir)
        }


# Глобальный экземпляр
_logger = None


def get_logger(session_name=None):
    """Получить или создать логгер"""
    global _logger
    if _logger is None:
        _logger = SessionLogger(session_name)
    return _logger


def end_session():
    """Завершить сессию"""
    global _logger
    if _logger:
        result = _logger.end_session()
        _logger = None
        print("✅ Сессия завершена")
        return result
    return None
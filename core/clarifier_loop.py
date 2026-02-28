from typing import Dict, List, Optional


class ClarifierLoop:
    """Управляет диалогом уточнения с пользователем"""

    def __init__(self):
        self.questions: List[str] = []
        self.answers: Dict[str, str] = {}
        self.current_question = 0
        self.needs_clarification = True

    def set_questions(self, questions_text: str):
        """Парсит вопросы из ответа агента (ищет где угодно)"""
        print(f"\n🔍 RAW ответ Clarifier:\n{questions_text}\n")

        self.questions = []
        lines = questions_text.strip().split('\n')

        # Ищем строки, начинающиеся с "- " в любом месте текста
        for line in lines:
            line = line.strip()
            if line.startswith('- '):
                question = line[2:].strip()  # убираем "- "
                if question and len(question) > 10:  # отсеиваем пустые
                    self.questions.append(question)

        print(f"📋 Найдено вопросов: {len(self.questions)}")
        for i, q in enumerate(self.questions):
            print(f"   {i + 1}. {q}")

        self.current_question = 0
        self.needs_clarification = len(self.questions) > 0

    def get_next_question(self) -> Optional[str]:
        """Возвращает следующий вопрос"""
        if self.current_question < len(self.questions):
            return self.questions[self.current_question]
        return None

    def add_answer(self, answer: str):
        """Сохраняет ответ и переходит к следующему вопросу"""
        if self.current_question < len(self.questions):
            question = self.questions[self.current_question]
            self.answers[question] = answer
            self.current_question += 1

        self.needs_clarification = self.current_question < len(self.questions)

    def get_all_answers(self) -> str:
        """Возвращает все ответы в виде текста"""
        result = "\n=== УТОЧНЕНИЯ ===\n"
        for q, a in self.answers.items():
            result += f"Q: {q}\nA: {a}\n"
        return result

    def is_finished(self) -> bool:
        """Проверяет, завершен ли диалог"""
        return not self.needs_clarification
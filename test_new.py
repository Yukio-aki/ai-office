import os
from core.crew_runner import run_crew

# Тестовый запрос
result = run_crew("Создай страницу с черным фоном и белой линией, которая медленно растет вверх")

print("\n" + "="*60)
print("РЕЗУЛЬТАТ:")
print("="*60)
print(result)
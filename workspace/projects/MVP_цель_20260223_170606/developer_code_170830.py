# Код разработчика

# Задача: 🎯 MVP цель

Одностраничный desktop-сайт с полноэкранной плавной анимацией в стиле dark fantasy anime (олдскул).

Фокус:

атмосфера

плавность

минимализм

простота реализации

🖥 Формат страницы

Тип: Single Page (один экран)
Платформа: Desktop only (>= 1280px)
Скролла нет
Весь контент — в hero-экране

🖤 Визуальная концепция

Фон

чистый глубокий чёрный (#000000)

без текстур на MVP

без градиентов

Главный объект

Анимированный готический стебель с шипами

Стиль:

2D

тонкая рисованная линия

слегка «hand-drawn» неровность

old-school anime feel

минималистично

Поведение анимации

MVP-движение:

стебель медленно растёт вверх

лёгкое органическое покачивание

бесшовный loop

никаких резких движений

Требования к плавности

Цель:

~60 FPS на desktop

без микрофризов

без дёрганий

🧩 UI (минимальный)

На MVP поверх анимации:

Обязательно

центрированный заголовок (короткий)

Опционально

маленький логотип в углу

одна кнопка

Важное правило

UI не должен конкурировать с атмосферой

Ограничения:

мало текста

много воздуха

никаких тяжёлых панелей

⚙️ Технический стек (MVP-оптимум)

Frontend

Минимальный современный стек:

React

Vite

TypeScript (можно опционально)

Анимация (ключевой выбор)
✅ Для MVP — PixiJS (2D WebGL)

Почему:

быстро

плавно

просто стартовать

хорошо для органических линий

❗️ Чего НЕ использовать в MVP

Не нужно сейчас:

❌ Three.js

❌ сложный WebGL shader

❌ Lottie

❌ SVG-анимацию (будет менее живо)

❌ тяжёлые анимационные фреймворки

📦 Структура проекта (MVP)

src/
 ├─ app/
 │   └─ App.tsx
 ├─ scene/
 │   └─ ThornStem.ts
 ├─ styles/
 │   └─ global.css
 └─ main.tsx

🚀 Поведение при загрузке

При открытии сайта:

мгновенный чёрный экран

через ~0.3–0.6 сек появляется стебель

начинается плавный рост

дальше бесконечный loop

🎨 Художественные ограничения (важно)

Чтобы сохранить стиль:

Делать:

тонкие линии

медленное движение

много пустоты

высокий контраст

НЕ делать:

толстые линии

яркие цвета

быстрые движения

перегруженный фон

📊 Критерии готовности MVP

Проект готов, если:

✅ стабильно ~60 FPS

✅ нет лагов на desktop

✅ загрузка < 2 сек

✅ визуал читается как dark fantasy

✅ код легко расширяем

1. <!DOCTYPE html>
  2. Start from the opening HTML tag by typing in "<?php"
  3. Use "html" and "head" tags to begin coding
  4. Comment out or remove unnecessary code, leaving only CSS annotations and JavaScript blocks
  5. For page load speed: use the <meta> tag on each page link for SEO indexing and user-friendly loading time.
  6. Optimize images by compressing file sizes, ensuring they are stored appropriately (use "!jpg" for JPEGs), and avoid overusing certain image formats/dimensions in favor of using more diverse and relevant files.
  7. Write a complete code structure with each task mentioned above, from HTML to CSS and finally JavaScrip
  8. Define a dark theme or neutral backgrounds to match the specific requirements of dark mode and white background for easy reading.
  9. Provide Abstact animation (moving pattern): it is not just a feature that shows movement, but it also enhances the user experience by making content more engaging.
  10. Include JS code with no explanation or comments in the CSS file: it ensures easy readability and debugging when necessary.
  11. Make sure code is optimized for each task mentioned above; that includes CSS rules and syntax compliance.
  12. Provide complete and formatted code as per the project specifications, making the website more user-friendly to navigate and browse easily.
  13. Provide no extra unnecessary files, especially animation files or any other unrelated extensions.
  14. Optimize images that require compressing file sizes for faster loading times, and ensure they’re stored in a suitable format for users with different devices.
  15. Keep the website simple, with no visual distractions or clutter, while including all necessary elements to provide a great user experience. Final Thought: Complete HTML code with CSS and JavaScript, adhering to all project requirements mentioned above.
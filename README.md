# DND Born in Pain

A sophisticated AI-powered Dungeon Master assistant for D&D campaigns, leveraging Python, Flask, and Google's Gemini AI to create immersive storytelling experiences.

## Key Features

- Dynamic scene generation and storytelling with context awareness
- AI-driven Dungeon Master responses with personality and consistency
- Smart context tracking and scene management
- Natural language processing for player actions and requests
- Real-time interactive chat interface with Material Design
- Multi-character support with NPC interaction capabilities
- Automated dice rolling and combat management

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/dnd-born-in-pain.git
cd dnd-born-in-pain
```

2. Настройте окружение:
```bash
# Создайте и активируйте виртуальное окружение
python -m venv env
source env/bin/activate  # Для Windows: env\Scripts\activate

# Установите зависимости
pip install -r requirements.txt
```

3. Настройте переменные окружения:
```bash
# Скопируйте пример файла окружения
cp .env.example .env
```

4. Настройте учетные данные Google AI:
   - Получите API-ключ Google в Google Cloud Console
   - Добавьте ваш API-ключ в файл .env:
     ```
     GOOGLE_API_KEY="ваш-api-ключ"
     FLASK_SECRET_KEY="ваш-секретный-ключ"
     GEMINI_MODEL_DUMB="gemini-2.0-flash-lite"
     ```

## Использование

1. Запустите приложение:
```bash
python app.py
```

2. Откройте `http://localhost:5000` в вашем браузере для доступа к веб-интерфейсу

3. Основные компоненты:
   - `app.py` - Точка входа веб-приложения Flask
   - `chapter_logic.py` - Основная игровая логика и управление сценами
   - `classifier.py` - ИИ-классификация текста с использованием Gemini
   - `generator.py` - Генерация сцен и объектов с помощью Gemini
   - `models/` - Pydantic-модели для игровых сущностей
   - `static/` - Ресурсы веб-интерфейса
   - `templates/` - HTML-шаблоны

## Технические детали

### Архитектура
- Веб-фреймворк Flask для бэкенда
- Google Gemini AI для обработки естественного языка
- Pydantic для валидации данных и управления схемами
- Адаптивный веб-интерфейс на основе Material Design

### Ключевые классы
- `ChapterLogicFight`: Управляет игровыми сценами и боевыми столкновениями
- `Classifier`: Обрабатывает ИИ-классификацию текста
- `ObjectGenerator`: Генерирует игровые объекты и сцены
- `Character`, `Scene`, `Item`: Основные модели игровых сущностей

## Разработка

### Требования
- Python 3.8 или выше
- API-ключ Google с доступом к моделям Gemini
- Базовое понимание механик D&D

### Тестирование
Запустите тесты классификатора:
```bash
python classifier.py
```

## Участие в разработке

1. Создайте форк репозитория
2. Создайте ветку для вашей функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Добавлена потрясающая функция'`)
4. Отправьте изменения в репозиторий (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## Лицензия

Этот проект распространяется под лицензией MIT - подробности см. в файле LICENSE.

## Отказ от ответственности

Этот проект является фанатским инструментом и не связан с Wizards of the Coast или официальной франшизой D&D. Весь контент, связанный с D&D, используется в соответствии с принципами добросовестного использования в образовательных и развлекательных целях.

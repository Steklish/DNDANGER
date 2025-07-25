# DND Guy

Интеллектуальный ИИ Мастер Подземелий для D&D


## Принцип работы системы

Система построена на модульной архитектуре, где каждый компонент отвечает за определенную часть игровой логики.

-   **`main.py`**: Точка входа в приложение. Отвечает за запуск сервера FastAPI, обработку HTTP-запросов, маршрутизацию и управление жизненным циклом игрового экземпляра.
-   **`game.py`**: Управляет глобальным состоянием игры, включая игровой цикл, режимы игры (бой/повествование), обработку подключений игроков и трансляцию событий всем клиентам через Server-Sent Events (SSE).
-   **`chapter_logic.py`**: Содержит основную логику одной "главы" или сцены. Управляет персонажами, их взаимодействиями, действиями, ходами и обновлениями состояния сцены.
-   **`story_manager.py`**: Отвечает за управление сюжетом кампании. Загружает данные из `campaign.json`, отслеживает текущий этап сюжета и проверяет, выполнены ли условия для его продвижения.
-   **`prompter.py`**: Содержит все промпты (инструкции) для языковой модели (LLM). Этот модуль формирует точные и структурированные запросы к ИИ для генерации текста, принятия решений и обновления состояния игры.
-   **`classifier.py`**: Использует LLM для классификации запросов пользователя (например, чтобы отличить действие персонажа от вопроса к Мастеру) и для принятия тактических решений.
-   **`generator.py`**: Использует LLM для генерации структурированных данных в формате Pydantic-моделей. Например, он создает полные описания персонажей, сцен или исходов действий.
-   **`imagen.py`**: Отвечает за генерацию изображений для персонажей и сцен с помощью Gemini.

## Генерация кампании

Кампания определяется в файле `campaigns/campaign.json`. Этот файл содержит всю необходимую информацию для запуска и проведения приключения.

### Структура `campaign.json`

-   **`title`**: Название кампании.
-   **`main_goal`**: Главная цель, которую должны достичь игроки.
-   **`starting_location`**: Место, где начинается приключение.
-   **`initial_character_prompt`**: Промпт для генерации первого NPC, с которым встретятся игроки.
-   **`current_plot_point_id`**: ID текущего этапа сюжета.
-   **`plot_points`**: Массив объектов, описывающих каждый этап сюжета:
    -   **`id`**: Уникальный идентификатор этапа.
    -   **`title`**: Название этапа.
    -   **`description`**: Описание ситуации на данном этапе.
    -   **`completion_conditions`**: Условия, которые должны быть выполнены игроками для перехода к следующему этапу.

Вы можете создать свою собственную кампанию, изменив этот файл или создав новый и указав путь к нему в `story_manager.py`.

## Генерация изображений

Приложение использует Google Generative AI (Gemini) для создания изображений для персонажей и сцен.

### Принцип работы

1.  **Сервис генерации:** Взаимодействие с API Gemini реализовано в классе `ImageGenerator` (`imagen.py`).
2.  **Асинхронная генерация:** Чтобы избежать блокировки основного потока приложения, задачи по генерации изображений выполняются в отдельном потоке с использованием очереди для управления запросами.
3.  **Запуск генерации:**
    *   **Создание персонажа:** При создании нового персонажа чере�� эндпоинт `/create-character` в `main.py`, в очередь `ImageGenerator` добавляется задача на создание изображения. В качестве промпта используются данные персонажа.
    *   **Смена сцены:** Метод `game.introduce_scene()` также инициирует генерацию фонового изображения для текущей сцены.
4.  **Промпты:** Промпты, отправляемые в API Gemini, содержат данные о персонаже или сцене с дополнительной инструкцией для создания изображения в стиле "мрачного фэнтези" и "высокой реалистичности".
5.  **Хранение изображений:** Сгенерированные изображения сохраняются в директории `static/images`.
6.  **Обновление интерфейса:** После генерации изображения для сцены, на фронтенд отправляется событие `scene_change`, которое обновляет фоновое изображение чата.

## Установка

1.  **Настройте переменные окружения:**
    ```bash
    # Скопируйте пример файла окружения
    cp .env.example .env
    ```
2.  **Настройте учетные данные Google AI:**
    *   Получите ключ API Google из Google AI Studio.
    *   Добавьте ваш ключ API в файл `.env`:
        ```
        GOOGLE_API_KEY="ваш-api-ключ"
        GEMINI_MODEL_DUMB="gemini-2.5-flash-lite-preview-06-17"
        ```
3.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

## Использование

### Запуск приложения:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

После запуска приложения вы можете получить доступ к следующим страницам:

*   **Вход:** `http://localhost:8080/`
*   **Создание персонажа:** `http://localhost:8080/character-creation`
*   **Интерфейс игрока:** `http://localhost:8080/player/{имя_персонажа}`
*   **Панель администратора:** `http://localhost:8080/admin`

## Технические детали

*   **Бэкенд:** FastAPI (асинхронный фреймворк Python)
*   **Обновления в реальном времени:** Server-Sent Events (SSE) для потоков��й передачи игровых событий.
*   **ИИ:** Google Gemini для генерации контента.
*   **Валидация данных:** Pydantic
*   **Шаблонизация:** Jinja2
*   **Фронтенд:** Vanilla JavaScript и CSS

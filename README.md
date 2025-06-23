
# DND Born in Pain

Интеллектуальный AI-ассистент Dungeon Master для D&D кампаний, использующий Python, FastAPI и Google Gemini AI для создания захватывающих повествований.

## Цели проекта
- Перейти на современный асинхронный веб-фреймворк FastAPI для большей производительности и масштабируемости.
- Обеспечить удобный REST API и поддержку Server-Sent Events (SSE) для стриминга игровых событий.
- Интегрировать Google Gemini AI для генерации описаний, сцен и обработки игровых событий.
- Предоставить современный веб-интерфейс для игроков, наблюдателей и ведущего.
- Поддерживать гибкую архитектуру для расширения игровых механик и интеграции новых AI-моделей.


## Установка
1. Настройте переменные окружения:
   ```bash
   # Скопируйте пример файла окружения
   cp .env.example .env
   ```
2. Настройте учетные данные Google AI:
   - Получите API-ключ Google в Google Cloud Console
   - Добавьте ваш API-ключ в файл .env:
     ```
     GOOGLE_API_KEY="ваш-api-ключ"
     GEMINI_MODEL_DUMB="gemini-2.0-flash-lite"
     ```

## Использование


### Запуск приложения:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```


## Технические детали
- Бэкенд: FastAPI (асинхронный Python-фреймворк)
- SSE для стриминга игровых событий
- Google Gemini AI для генерации контента
- Pydantic для валидации данных
- Jinja2 для шаблонов HTML
- Современная структура фронтенда (JS/CSS вынесены отдельно)

## Участие в разработке

1. Создайте форк репозитория
2. Создайте ветку для вашей функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Добавлена потрясающая функция'`)
4. Отправьте изменения в репозиторий (`git push origin feature/amazing-feature`)
5. Откройте Pull Request



### EVENTS

- keepalive
   ```json
   {
      "data": any
   }
   ```
- lock/unlock message
   ```json
   {
      "event": "lock",
      "allowed_players": ["player_name_1", "player_name_2"]
   }
   ```
- other player's message
   ```json
   {
      "event": "other_player_message",
      "data": "text",
      "sender": "character_name"
   }
   ```
- state_update_required
   ```json
   {
      "event": "some_stat_update",
      "total": n,
      "current": c
   }
   ```


### REQUESTS

- full update - `GET`
   - `/refresh` — получить всю информацию о главе
      - (см. описание классов в ./models/schemas.py)
         ```json
         {
            "scene": sceneOBJ,
            "characters": [playerObj_1, playerObj_2],
            "chat_history": [
               {"message_text": "asdsad", "sender_name": "yyy"},
               {"message_text": "fhcghj,bbbhb", "sender_name": "xxx"}
            ]
         }
         ```
- interaction — `POST /interact`


# Пример работы со стримом (SSE)

## JS
```js
const eventSource = new EventSource("/stream");
eventSource.onmessage = function(event) {
   const data = JSON.parse(event.data);
   console.log(data);
};
```

## Python
```python
data_dict = {
    'value': random.randint(1, 100),
    'user': random.choice(['Alice', 'Bob', 'Charlie']),
    'timestamp': time.strftime('%H:%M:%S'),
    'isValid': random.choice([True, False])
}
json_data = json.dumps(data_dict)
sse_message = f"data: {json_data}\n\n"
yield sse_message
```



# ВАЖНО

### Web-часть

- `login.html` — выбор персонажа (или создание), выбор режима (игрок/админ)
- `player.html` — меню игрока: чат, боковая панель со статами, инвентарём, описаниями
- `observer.html` — общая панель: кто ходит, статы всех, состояние сцены

# TODO (на 19.06 и далее)
- Доработать стриминг событий через FastAPI SSE
- Почистить админку и передвинуть карточки
- Сделать логику отправки сигналов о блокировке ходов (сервер)
- Обработать все варианты сигналов (из events.py)
  - Сделать блокировку / разблокировку
  - Придумать, что делать с событиями обновления (n и p m)
  - Если нужна доп. дата — напиши мне
- Пофиксить списки в маркдауне
- Исправить отображение деталей в админке
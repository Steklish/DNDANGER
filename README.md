# DND Born in Pain

A sophisticated AI-powered Dungeon Master assistant for D&D campaigns, leveraging Python, Flask, and Google's Gemini AI to create immersive storytelling experiences.

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
python app.py
```

## Технические детали

## Участие в разработке

1. Создайте форк репозитория
2. Создайте ветку для вашей функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Добавлена потрясающая функция'`)
4. Отправьте изменения в репозиторий (`git push origin feature/amazing-feature`)
5. Откройте Pull Request


### EVENTS

- keepalive
   ```
   {
      data : any
   }
   ```
- lock/unlock message
      
   ```
   {
      event : lock 
      allowed_players : [  // имя игрока который сейчас ходит.
         player_name_1
         player_name_2
      ]   
   }
   ```
- other player's message
   ```
   {
      event : other_player_message 
      data : text
      sender : character_name
   }
   ```
- state_update_required
   ```
   {
      event : some_stat_update
      total: n
      current: c
   }
   ```  

### REQUESTS

- full update - `GET`
   - `/refresh - выдавать всю инфу про главу`
      - (см. описание классов в ./models/schemas.py)
         ```
         {
            scene : sceneOBJ,
            characters : [
               playerObj_1,
               playerObj_1
            ],
            schat_history : [
               {
                  message_text : "asdsad",
                  sender_name : "yyy"
               },
               {
                  message_text : "fhcghj,bbbhb",
                  sender_name : "xxx"
               }
            ]
         }
         ```

- interaction
   `/interaction - POST`

# пример работы со стримом `JS`
```js
// 1. Create a new EventSource object to connect to our /stream endpoint
const eventSource = new EventSource("/stream");

// 2. Listen for the 'message' event from the server
eventSource.onmessage = function(event) {
   const data = JSON.parse(event.data);
   console.log(data);
};
```
# пример работы со стримом `Python`
```python
data_dict = {
	'value': random.randint(1, 100),
	'user': random.choice(['Alice', 'Bob', 'Charlie']),
	'timestamp': time.strftime('%H:%M:%S'),
	'isValid': random.choice([True, False])
}
# 2. Convert the dictionary to a JSON string
json_data = json.dumps(data_dict)

# 3. Format it as an SSE message
#    The 'data:' prefix is required, followed by the JSON string.
#    The two newlines ('\n\n') signal the end of the event.
sse_message = f"data: {json_data}\n\n"

# 4. Yield the message to the client
yield sse_message
```


# ВАЖНО

### Web-часть

- `login.html`
   - тут выюор персонажа (возможно, создание)
   - тут же выбор того, зайдешь ли как игрок или как доска админа
- `player.html`
   - тут мменюшка игрока
      - чат с событиями
      - боковая панель со статами / инвентарем / описаниями
- `observer.html`
   - тут общая менюшка
      - кто сейчас ходит (включая врагов)
      - статы для всех дейстыующих лиц
      - состояние сцены (м б какая-то визуализация)

# Что нужно доделать на 19.06

- ~~сделать общий `стильный файл`~~
- ~~сделать `js` файлы отдельно от шаблонов для `html`~~
- ~~в админке карточки не работают правильно (только первая нормальная а дальше пизда)~~
- разобраться с работой стрима
   - ~~сделать `/stream` эндпоинт~~
   - ~~почитай сверху в ридми примеры работы со стримом~~
- почистить админку и передвинуть карточки
- ~~почистить говнокод в `fetchUpdate()`~~
   - сделать адекватное создание объектов после `refresh`

- сделать логику отправки сигналов о блокировке ходов (сервер)
- обработать все варианты сигналов (из events.py)
   - сделать блокировку / разблокировку
   - придумать, что делать с событиями оюновления (которые  n иp m)
   - если нужна какая-то доп дата - напиши мне
- пофиксить списки в маркдауне
- пункт `Details: {"damage":"1d8","damage_type":"Рубящий","range":"Ближний бой"}` в аблках на админке
# Импортируем необходимые библиотеки Flask для веб-приложения
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, Response
from chapter_logic import ChapterLogicFight
from models import *
import json
import time


from classifier import Classifier
from generator import ObjectGenerator
from flask import request
# Создаем экземпляр приложения Flask

app = Flask(__name__)
load_dotenv()
global message_history
message_history = [
    ]

generator = ObjectGenerator()
context = "A ground beneeth the grand tree"
global chapter
chapter = ChapterLogicFight(
    context = context,
    characters = [
        generator.generate(Character, "Борис Квадробер with full hp (50 hp) (player character) кот, которого ведьма превратила в человека (ведьма была его хозяйкой, от которой он позже сбежал), на нем него только тряпка вокруг члена и ничего больше. Среднее телосложение, черные кошачьи ушки. Нижние ноги скорее кошачь, чем человеческие. Густая шерсть по всему телу. Усы на лице. Хвост черный. У него гетерохромя с ожним глазом зеленым, а вторым синим. У него острые зубы и когти. Класс персонажа - плут(способности соответствующие). Любит рыбу и не любит молоко. Отзывается на кличку 'Барсик' - сокрощенно от 'Борис'.", context, "Russian"),
        generator.generate(Character, "random monster with full hp (50 hp) and some magic spells (enemy NPC)", context, "Russian")
    ]
)
chapter.setup_fight()
# Определяем маршрут для главной страницы
@app.route('/')
def index():
    # Отображаем шаблон login.html
    return render_template('login.html', character_list=chapter.characters)

@app.route('/interact', methods=['POST'])
def interact():
    data = request.get_json()
    
    print(data)
    message_history.append(
        {
            "message_text": data['message'],
            "sender_name": data['character']
        }
    )
    
    message_history.append(
        {
            "message_text": chapter.process_interaction(chapter.get_character_by_name(data['character']), data['message']), # type: ignore
            "sender_name": "DM"
        }
    )
    
    # Здесь вы можете обработать данные взаимодействия, например:
    # action = data.get('action')
    # target = data.get('target')
    # response = chapter.handle_interaction(action, target)
    # Для примера просто возвращаем полученные данные
    return jsonify({"status": "ok"})

@app.route('/player/<name>')
def player(name):
    return render_template('player.html', character_name=name)



@app.route('/observer')
def observer():
    return render_template('observer.html')

@app.route('/refresh')
def get_info():

    scene = chapter.scene
    
    players = chapter.characters
    
    
    # message_history = message_history
    # Convert the Pydantic objects into dictionaries that jsonify can handle.
    content = {
        # .model_dump() converts the Scene object to a dictionary
        "scene": scene.model_dump(),  # type: ignore
        
        # We use a list comprehension to convert each Character object in the list
        "characters": [p.model_dump() for p in players], 
        
        # This was already a simple list of dictionaries, so it's fine
        "chat_history": message_history
    }
    return jsonify(content)

@app.route('/stream')
def stream():
    def event_stream():
        while True:
            # Собираем данные
            data = {
                "scene": chapter.scene.model_dump(),
                "characters": [p.model_dump() for p in chapter.characters],
                "chat_history": message_history
            }
            
            # Форматируем данные как SSE сообщение
            yield f"data: {json.dumps(data)}\n\n"
            
            # Пауза между обновлениями
            time.sleep(1)
    
    return Response(event_stream(), mimetype='text/event-stream')

# Запускаем приложение в режиме отладки, если файл запущен напрямую
if __name__ == '__main__':
    
    app.run(debug=True)

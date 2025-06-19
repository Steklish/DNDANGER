# Импортируем необходимые библиотеки Flask для веб-приложения
from re import I
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, render_template, Response
from models import *
import json
import time
from game import Game
from flask import request

load_dotenv()
app = Flask(__name__)
game = Game()    

@app.route('/')
def index():
    return render_template('login.html', character_list=game.chapter.characters)

@app.route('/interact', methods=['POST'])
def interact():
    data = request.get_json()
    print(f"data received from {data['character']}\n DATA:{data}")
    game.handle_interaction_from_player(
        interaction=data['message'], 
        character_name=data['character']
    )
    return jsonify({"status": "ok"})

@app.route('/player/<name>')
def player(name):
    return render_template('player.html', character_name=name)


@app.route('/get_current_character')
def get_character_name():
    name = game.chapter.get_active_character_name()
    response = make_response(name)
    response.mimetype = 'text/plain'
    return response


@app.route('/observer')
def observer():
    return render_template('observer.html')

@app.route('/refresh')
def get_info():
    scene = game.chapter.scene
    players = game.chapter.characters
    content = {
        "scene": scene.model_dump(),  # type: ignore
        "characters": [p.model_dump() for p in players], 
        "chat_history": game.message_history
    }
    return jsonify(content)

@app.route('/stream')
def stream():
    return Response(game.listen(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
import uuid
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, render_template, Response
from models import *
from game import Game
from flask import request

load_dotenv()
app = Flask(__name__)
game = Game()    

@app.route('/login')
def login():
    return render_template('login.html', character_list=game.chapter.characters)


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
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    name = request.args.get('name')
    sid = str(uuid.uuid4())
    if name:
        return Response(game.listen(sid, listener_char_name=name), mimetype='text/event-stream', headers=headers)
    else:
        return Response(game.listen(sid), mimetype='text/event-stream', headers=headers)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
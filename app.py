# Импортируем необходимые библиотеки Flask для веб-приложения
from flask import Flask, jsonify, render_template, Response
from models import *
import json
import time
# Создаем экземпляр приложения Flask
app = Flask(__name__)

# Определяем маршрут для главной страницы
@app.route('/')
def index():
    # Отображаем шаблон login.html
    return render_template('login.html')

@app.route('/player.html')
def player():
    return render_template('player.html')

@app.route('/observer.html')
def observer():
    return render_template('observer.html')

@app.route('/refresh')
def get_info():

    scene = Scene.model_validate_json(
    """
    {
        "name": "The Whispering Crypt",
        "description": "The air in the crypt is cold and heavy with the smell of damp earth and ancient dust. The only light comes from your flickering torches, which casts long, dancing shadows across the stone walls. A faint, almost inaudible whispering seems to hang in the air, its source unclear.",
        "size_description": "A rectangular chamber approximately 30 feet wide and 40 feet long, with a high, vaulted ceiling lost in the darkness above.",
        "objects": [
            {
            "name": "Ancient Stone Sarcophagus",
            "description": "Carved from a single, massive block of black marble, the sarcophagus is covered in faded, intricate runes. A thin layer of undisturbed dust blankets its surface. The heavy lid appears to be sealed shut.",
            "size_description": "It is imposing, roughly 8 feet long and 3 feet wide.",
            "position_in_scene": "Resting on a raised stone dais in the exact center of the chamber, it is clearly the focal point of the room.",
            "interactions": [
                "Examine runes",
                "Try to open",
                "Listen to"
            ]
            },
            {
            "name": "Rusted Iron Brazier",
            "description": "A three-legged iron bowl, heavily pitted with rust and age. It is filled with cold, grey ash and chunks of unburnt charcoal.",
            "size_description": "Stands about waist-high to an average human.",
            "position_in_scene": "Tucked into the northeast corner of the room, partially shrouded in shadow.",
            "interactions": [
                "Examine",
                "Look inside",
                "Try to light"
            ]
            },
            {
            "name": "Moss-Covered Wall",
            "description": "The stone blocks of this wall are damp to the touch and covered in patches of phosphorescent green moss, which gives off a faint, sickly light.",
            "size_description": "The entire northern wall of the chamber.",
            "position_in_scene": "It forms the northern boundary of the crypt.",
            "interactions": [
                "Touch the moss",
                "Examine the stones for loose bricks"
            ]
            }
        ]
    }
    """
    )
    
    players = [Character.model_validate_json(
    """
    {
        "name": "Gideon 'Grizzly' Blackwood",
        "max_hp": 35,
        "current_hp": 28,
        "ac": 16,
        "is_player": true,
        "conditions": [],
        "inventory": [
            {
            "name": "Veteran's Longsword",
            "description": "A well-balanced longsword, its hilt wrapped in worn leather. The blade has a few nicks from past battles but remains sharp.",
            "item_type": "Weapon",
            "weight": 3.0,
            "value": 15,
            "quantity": 1,
            "rarity": "Common",
            "is_magical": false,
            "damage": "1d8",
            "damage_type": "Рубящий",
            "armor_class": null,
            "effect": null,
            "properties": [
                "Versatile (1d10)"
            ]
            },
            {
            "name": "Potion of Healing",
            "description": "A swirling red liquid in a glass vial that restores a small amount of health when consumed.",
            "item_type": "Potion",
            "weight": 0.5,
            "value": 50,
            "quantity": 2,
            "rarity": "Common",
            "is_magical": true,
            "damage": null,
            "damage_type": null,
            "armor_class": null,
            "effect": "Restores 2d4 + 2 hit points.",
            "properties": []
            },
            {
            "name": "Backpack",
            "description": "A simple but sturdy leather backpack for carrying supplies.",
            "item_type": "Gear",
            "weight": 5.0,
            "value": 2,
            "quantity": 1,
            "rarity": "Common",
            "is_magical": false,
            "damage": null,
            "damage_type": null,
            "armor_class": null,
            "effect": null,
            "properties": [
                "Can hold up to 30 pounds of gear."
            ]
            }
        ],
        "abilities": [
            {
            "name": "Second Wind",
            "description": "Once per short rest, you can use a bonus action to regain 1d10 + your fighter level in hit points.",
            "details": {
                "usage": "1 per Short Rest",
                "action_type": "Bonus Action"
            }
            }
        ],
        "personality_history": "Gideon is a former city watchman from a northern citadel. He is world-weary and cynical on the surface, but possesses a strong, unwavering sense of justice. He left his post after a corrupt captain allowed a noble to get away with a heinous crime, and now he wanders the lands as a sellsword, seeking to enact the justice that the law sometimes fails to provide. He is fiercely loyal to those he calls friends and will protect them with his life."
    }
    """
    )]
    message_history = [
        {
            "message_text": "Привет всем! Кто-нибудь знает, где найти Ключ от склепа?",
            "sender_name": "Gideon"
            },
            {
            "message_text": """
            <span class='name'>Ледяной элементаль</span> поднимает свои <span class='keyword'>ледяные когти</span> и <span class='keyword'>обрушивает их на тебя</span>, <span class='name'>Ледяной Клинок</span>, в момент, когда ты <span class='condition'>лежишь на льду</span>.

Он совершает <span class='keyword'>бросок атаки</span>...

<span class='keyword'>17!</span>

Атака <span class='keyword'>попадает</span>!

<span class='keyword'>Ледяные когти</span> обрушиваются на тебя.

<span class='keyword'>Ледяной элементаль</span> наносит тебе удар.

Кидает кубики, чтобы определить урон...

<span class='keyword'>11 рубящего урона</span>, и <span class='keyword'>1 урона холодом</span>!

Ты получаешь <span class='keyword'>12 урона</span>.""",
            "sender_name": "DM"
            },
            {
            "message_text": "Хорошая мысль. Но будьте осторожны, говорят, там водятся книжные черви размером с собаку.",
            "sender_name": "Boric"
            },
            {
            "message_text": "Отлично! Ненавижу читать, но обожаю драться. Я иду с вами.",
            "sender_name": "DM"
            },
            {
            "message_text": "Я могу наложить заклинание света, чтобы нам было лучше видно в темноте.",
            "sender_name": "Elara"
            },
            {
            "message_text": "А я могу... э-э... громко кричать, чтобы отпугивать монстров! Пошли!",
            "sender_name": "DM"
        }

    ]
     # Convert the Pydantic objects into dictionaries that jsonify can handle.
    content = {
        # .model_dump() converts the Scene object to a dictionary
        "scene": scene.model_dump(), 
        
        # We use a list comprehension to convert each Character object in the list
        "characters": [p.model_dump() for p in players], 
        
        # This was already a simple list of dictionaries, so it's fine
        "chat_history": message_history
    }
    return jsonify(content)

# Запускаем приложение в режиме отладки, если файл запущен напрямую
if __name__ == '__main__':
    app.run(debug=True)

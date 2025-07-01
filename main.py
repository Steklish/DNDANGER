import asyncio
import os
import shutil
import uuid
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from global_defines import *
from models.schemas import Character
from game import Game


# --- FastAPI Setup ---
load_dotenv()
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Pydantic Models ---
class InteractionPayload(BaseModel):
    character: str
    message: str

class CharacterCreatePayload(BaseModel):
    name: str
    background: str
    inventory: str
    stats: dict[str, int]

class CharacterUpdatePayload(BaseModel):
    name: str
    updates: dict

# --- Game Instance ---
game: Game

@app.on_event("startup")
async def startup_event():
    global game
    
    # Clear the static/images directory
    images_dir = "static/images"
    if os.path.exists(images_dir):
        for filename in os.listdir(images_dir):
            file_path = os.path.join(images_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

    game = await Game.create()
    await game.introduce_scene()
    asyncio.create_task(game.game_loop())

# --- HTML Routes ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "character_list": game.chapter.characters})

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "character_list": game.chapter.characters})

@app.get("/player/{name}", response_class=HTMLResponse)
async def player(request: Request, name: str):
    return templates.TemplateResponse("player.html", {"request": request, "character_name": name})

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request, "event_log": game.chapter.event_log})

@app.get("/character-creation", response_class=HTMLResponse)
async def character_creation(request: Request):
    return templates.TemplateResponse("character_creation.html", {"request": request})

# --- API Routes ---
@app.post("/interact")
async def interact(payload: InteractionPayload):
    await game.handle_interaction_from_player(interaction=payload.message, character_name=payload.character)
    return {"status": "ok"}

@app.post("/create-character")
async def create_character(payload: CharacterCreatePayload):
    prompt = (
        f"A new player character named {payload.name}. "
        f"Background: {payload.background}. "
        f"Inventory: {payload.inventory}. "
        f"Stats: "
        f"Strength {payload.stats['strength']}, "
        f"Dexterity {payload.stats['dexterity']}, "
        f"Constitution {payload.stats['constitution']}, "
        f"Intelligence {payload.stats['intelligence']}, "
        f"Wisdom {payload.stats['wisdom']}, "
        f"Charisma {payload.stats['charisma']}. "
        "Generate a complete character sheet with abilities, inventory, and other details."
    )
    new_char = game.generator.generate(Character, prompt, game.context, "Russian")
    new_char.is_player = True
    game.chapter.image_generator.submit_generation_task(new_char.model_dump_json(), new_char.name)
    await game.add_player_character(new_char)
    return {"status": "ok", "character_name": new_char.name}

@app.get("/api/game_state")
async def get_game_state():
    story_manager = game.story_manager
    current_plot_point = story_manager.get_current_plot_point()
    state = {
        "scene": game.chapter.scene.model_dump(), # type: ignore
        "characters": [p.model_dump() for p in game.chapter.characters],
        "chat_history": game.message_history,
        "game_mode": game.chapter.game_mode.name,
        "turn_order": [p for p in game.chapter.turn_order],
        "story": {
            "title": story_manager.story.title,
            "main_goal": story_manager.story.main_goal,
            "current_plot_point": current_plot_point.model_dump() if current_plot_point else None,
            "all_plot_points": [p.model_dump() for p in story_manager.story.plot_points]
        },
        "context": game.context,
        "event_log": game.chapter.event_log
    }
    return JSONResponse(content=state)

@app.get("/api/get_current_character")
async def get_current_character():
    active_character_name = game.chapter.get_active_character_name()
    return JSONResponse(content={"active_character": active_character_name})

@app.post("/api/story/next")
async def story_next():
    new_plot_point = game.story_manager.advance_story()
    if new_plot_point:
        return JSONResponse(content=new_plot_point.model_dump())
    raise HTTPException(status_code=404, detail="End of story")

@app.post("/api/story/previous")
async def story_previous():
    new_plot_point = game.story_manager.advance_story()
    if new_plot_point:
        return JSONResponse(content=new_plot_point.model_dump())
    raise HTTPException(status_code=404, detail="Start of story")

@app.post("/api/story/set/{plot_point_id}")
async def set_story_point(plot_point_id: str):
    new_plot_point = game.story_manager.set_plot_point(plot_point_id)
    if new_plot_point:
        return JSONResponse(content=new_plot_point.model_dump())
    raise HTTPException(status_code=404, detail="Plot point not found")

@app.post('/api/character/update')
async def update_character_api(payload: CharacterUpdatePayload):
    updated_char = game.update_character(payload.name, payload.updates)
    if updated_char:
        return JSONResponse(content=updated_char.model_dump())
    raise HTTPException(status_code=404, detail="Character not found")

@app.delete('/api/character/{character_name}')
async def delete_character_api(character_name: str):
    if await game.delete_character(character_name):
        return JSONResponse(content={"status": "ok"})
    raise HTTPException(status_code=404, detail="Character not found")

@app.get("/stream")
async def stream(name: str | None = Query(None)):
    headers = {"Cache-Control": "no-cache", "Connection": "keep-alive"}
    sid = str(uuid.uuid4())
    listener_name = name if name else "Unknown"
    return StreamingResponse(game.listen(sid, listener_char_name=listener_name), media_type='text/event-stream', headers=headers)

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")

# --- Running the App ---
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)

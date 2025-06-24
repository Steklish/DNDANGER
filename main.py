import uuid
import uvicorn  # For running the app
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, Query
from fastapi.staticfiles import StaticFiles 
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel # Pydantic for data validation

from global_defines import INFO_COLOR, Colors
from models import *
from game import Game

# --- FastAPI Setup ---
load_dotenv()
app = FastAPI() 
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

class InteractionPayload(BaseModel):
    character: str
    message: str


@app.on_event("startup")
async def startup_event():
    global game
    game = await Game.create()  # Only inside an async function!
    await game.allow_current_character_turn()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/favicon.ico")


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    context = {
        "request": request,
        "character_list": game.chapter.characters
    }
    return templates.TemplateResponse("login.html", context)


@app.get('/login', response_class=HTMLResponse)
async def login(request: Request):
    context = {
        "request": request,
        "character_list": game.chapter.characters
    }
    return templates.TemplateResponse("login.html", context)


@app.post('/interact')
async def interact(payload: InteractionPayload): 
    print(f"Data {INFO_COLOR} received from {payload.character}\n{Colors.RESET}  DATA:{payload.model_dump()}")
    
    await game.handle_interaction_from_player(
        interaction=payload.message,
        character_name=payload.character
    )
    return {"status": "ok"}


@app.get('/player/{name}', response_class=HTMLResponse)
async def player(request: Request, name: str):
    return templates.TemplateResponse("player.html", {
        "request": request, 
        "character_name": name
    })


@app.get('/get_current_character')
async def get_character_name():
    name = game.chapter.get_active_character_name()
    # Use the Response class for plain text
    return Response(content=name, media_type='text/plain')


@app.get('/observer', response_class=HTMLResponse)
async def observer(request: Request):
    return templates.TemplateResponse("observer.html", {"request": request})


@app.get('/refresh')
async def get_info():
    scene = game.chapter.scene
    players = game.chapter.characters
    content = {
        "scene": scene.model_dump(), # type: ignore
        "characters": [p.model_dump() for p in players],
        "chat_history": game.message_history
    }
    return content


@app.get('/stream')
async def stream(name: str | None = Query(None)): 
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    sid = str(uuid.uuid4())
    if name:
        return StreamingResponse(game.listen(sid, listener_char_name=name), media_type='text/event-stream', headers=headers)
    else:
        return StreamingResponse(game.listen(sid, listener_char_name="Unknown"), media_type='text/event-stream', headers=headers)


# --- Running the App ---
if __name__ == '__main__':
    # You run a FastAPI app with an ASGI server like uvicorn
    # The command line is preferred: uvicorn main:app --reload --host 0.0.0.0 --port 8080
    uvicorn.run(app, host='0.0.0.0', port=8080)
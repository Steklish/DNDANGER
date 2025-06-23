import uuid
import uvicorn  # For running the app
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, Query
from fastapi.staticfiles import StaticFiles 
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel # Pydantic for data validation

from models import *
from game import Game

# --- FastAPI Setup ---
load_dotenv()
app = FastAPI()  # Create the FastAPI app instance
app.mount("/static", StaticFiles(directory="static"), name="static")
game = Game()    # Your game logic remains the same

# Setup for rendering Jinja2 HTML templates
templates = Jinja2Templates(directory="templates")

# --- Pydantic Model for Data Validation ---
# This replaces the need to manually parse JSON and check for keys.
# FastAPI will automatically validate the incoming request body against this model.
class InteractionPayload(BaseModel):
    character: str
    message: str

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
    print(f"data received from {payload.character}\n DATA:{payload.model_dump()}")
    
    game.handle_interaction_from_player(
        interaction=payload.message,
        character_name=payload.character
    )
    return {"status": "ok"}

@app.get('/player/{name}', response_class=HTMLResponse)
async def player(request: Request, name: str): # Path parameters are type-hinted
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
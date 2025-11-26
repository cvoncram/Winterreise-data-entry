from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.routers import generate_mei, home, correct_beats, align_data, insert_mei

app = FastAPI(title="Sonic Visualiser Tools")

app.mount("/static", StaticFiles(directory="backend/static"), name="static")
templates = Jinja2Templates(directory="backend/templates")

app.include_router(home.router)
app.include_router(correct_beats.router)
app.include_router(align_data.router)
app.include_router(insert_mei.router)
app.include_router(generate_mei.router)


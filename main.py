import os
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.routers import generate_mei, home, sv_to_mei

# --- Absolute path to tmp folder ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # backend/
TMP_DIR = os.path.join(BASE_DIR, "tmp")

# --- Lifespan handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Remove tmp folder entirely (including subfolders)
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR, ignore_errors=True)
    # Recreate empty tmp folder
    os.makedirs(TMP_DIR, exist_ok=True)
    yield  # App runs here

# --- Create FastAPI app ---
app = FastAPI(title="Sonic Visualiser Tools", lifespan=lifespan)

# --- Mount static files and templates ---
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# --- Include routers ---
app.include_router(home.router)
app.include_router(generate_mei.router)
app.include_router(sv_to_mei.router)

import os
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import TEMPLATES_DIR, STATIC_DIR, DATA_DIR
from routers import generate_mei, home, sv_to_mei


# --- Lifespan handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Remove data folder entirely (including subfolders)
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR, ignore_errors=True)
    # Recreate empty data folder
    os.makedirs(DATA_DIR, exist_ok=True)
    yield  # App runs here

# --- Create FastAPI app ---
app = FastAPI(title="Sonic Visualiser Tools", lifespan=lifespan)

# --- Mount static files and templates ---
app.mount("/static", StaticFiles(directory=os.path.join(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=os.path.join(TEMPLATES_DIR))

# --- Include routers ---
app.include_router(home.router)
app.include_router(generate_mei.router)
app.include_router(sv_to_mei.router)

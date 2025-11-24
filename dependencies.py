import os
import uuid
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException, UploadFile
import pandas as pd
from io import StringIO, BytesIO
import time
import re
from typing import Union

templates = Jinja2Templates(directory="backend/templates")

def ensure_extension(file: UploadFile, allowed: tuple[str, ...]):
    # Normalize the allowed tuple to avoid accidental string usage
    if not isinstance(allowed, tuple):
        allowed = tuple(allowed)
    if not file.filename.lower().endswith(allowed):
        raise HTTPException(
            status_code=400,
            detail=f"File '{file.filename}' must end with: {', '.join(allowed)}"
        )
    return file

def read_csv_upload(file_or_bytes: Union[UploadFile, bytes, bytearray, str]) -> pd.DataFrame:
    """
    Read CSV input and return a pandas DataFrame.
    Accepts:
      - an UploadFile (FastAPI) OR
      - raw bytes (what you get from await file.read())
      - a bytearray or string path/contents
    """
    try:
        if isinstance(file_or_bytes, UploadFile):
            data = file_or_bytes.file.read().decode("utf-8")
            return pd.read_csv(StringIO(data))
        elif isinstance(file_or_bytes, (bytes, bytearray)):
            return pd.read_csv(BytesIO(file_or_bytes))
        elif isinstance(file_or_bytes, str):
            # if a file path was passed
            return pd.read_csv(file_or_bytes)
        else:
            raise ValueError("Unsupported input type for CSV reading")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")

TOKENS = {}
TOKEN_TTL = 3600  # 1 hour

def cleanup_tokens():
    now = time.time()
    expired = [t for t, d in TOKENS.items() if now - d["time"] > TOKEN_TTL]
    for t in expired:
        del TOKENS[t]


def store_file(directory: str, extension: str) -> str:
    """
    Creates a unique file path inside `directory`
    and returns its full path.
    """
    os.makedirs(directory, exist_ok=True)
    filename = f"{uuid.uuid4()}{extension}"
    return os.path.join(directory, filename)

FILENAME_SAFE = re.compile(r"[A-Za-z0-9._-]+")

def sanitize_filename(name: str, default: str):
    if not name or not FILENAME_SAFE.fullmatch(name):
        return default
    return name

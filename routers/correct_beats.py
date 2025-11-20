import uuid
from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import FileResponse
from backend.dependencies import templates
from backend.services.correct_beats_service import process_csv
import os

router = APIRouter(prefix="/correct", tags=["correct"])

TEMP = "temp_correct"
os.makedirs(TEMP, exist_ok=True)

@router.get("")
def page(request: Request):
    return templates.TemplateResponse("correct_beats.html",
                                      {"request": request, "title": "Correct Beats", "result_ready": False})

@router.post("")
async def correct(
    request: Request,
    file: UploadFile,
    bpm: int = Form(...),
    has_anacrusis: str = Form(None),
    anacrusis: float = Form(0.0),
    filename: str = Form(...)
):
    content = await file.read()
    output_path = os.path.join(TEMP, f"{uuid.uuid4()}.csv")

    process_csv(content, bpm, float(anacrusis), bool(has_anacrusis), output_path)

    token = os.path.basename(output_path)

    return templates.TemplateResponse("correct_beats.html",
                                      {"request": request, "title": "Correct Beats",
                                       "result_ready": True, "token": token})

@router.get("/download/{token}")
def download(token: str):
    path = os.path.join(TEMP, token)
    return FileResponse(path, filename="corrected.csv")


from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from backend.dependencies import templates, ensure_extension, store_file, sanitize_filename
from backend.services.correct_beats_service import add_tempo_column_inplace, process_csv
from backend.services.csv_utils import rename_column_inplace, preview_csv as service_preview_csv
from backend.services.correct_beats_service import recalc_measure_beat

import os

router = APIRouter(prefix="/correct", tags=["correct"])
TEMP = "temp_correct"
os.makedirs(TEMP, exist_ok=True)

@router.get("")
def page(request: Request):
    return templates.TemplateResponse(
        "correct_beats.html",
        {"request": request, "title": "Correct Measure/Beat & Tempo", "result_ready": False}
    )

@router.post("")
async def correct(
    request: Request,
    file: UploadFile,
    bpm: int = Form(...),
    has_anacrusis: str = Form(None),
    anacrusis: float = Form(0.0),
    filename: str = Form(...)
):
    filename = sanitize_filename(filename, default="corrected.csv")
    file = ensure_extension(file, (".csv",))
    content = await file.read()
    output_path = store_file(TEMP, ".csv")

    process_csv(content, bpm, float(anacrusis), bool(has_anacrusis), output_path)
    token = os.path.basename(output_path)

    return templates.TemplateResponse(
        "correct_beats.html",
        {"request": request, "title": "Correct Beats", "result_ready": True, "token": token}
    )

@router.get("/download/{token}")
def download(token: str):
    path = os.path.join(TEMP, token)
    return FileResponse(path, filename="corrected.csv")

@router.post("/preview")
async def preview(file: UploadFile):
    content = await file.read()
    token_path = store_file(TEMP, ".csv")
    with open(token_path, "wb") as f:
        f.write(content)
    token = os.path.basename(token_path)
    html = service_preview_csv(content, n=10)
    return {"html": html, "token": token}

@router.post("/rename")
async def rename_column(
    token: str = Form(...),
    old: str = Form(...),
    new: str = Form(...),
    move_left: str = Form("1")
):
    csv_path = os.path.join(TEMP, token)
    try:
        rename_column_inplace(csv_path, old, new, move_to_left=move_left=="1")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    with open(csv_path, "rb") as f:
        content = f.read()
    html = service_preview_csv(content, n=10)
    return {"html": html}

@router.post("/beats")
async def correct_beats_column(
    token: str = Form(...),
    bpm: int = Form(...),
    has_anacrusis: str = Form("0"),  # get as string
    anacrusis: float = Form(0.0)
):
    csv_path = os.path.join(TEMP, token)
    
    # convert string to bool
    has_anacrusis_bool = str(has_anacrusis).lower() in ("1", "true")

    
    try:
        recalc_measure_beat(csv_path, bpm, anacrusis if has_anacrusis_bool else 0)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    with open(csv_path, "rb") as f:
        content = f.read()
    html = service_preview_csv(content, n=10)
    return {"html": html}

@router.post("/tempo")
async def add_tempo_column(token: str = Form(...)):
    csv_path = os.path.join(TEMP, token)
    try:
        add_tempo_column_inplace(csv_path)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    with open(csv_path, "rb") as f:
        content = f.read()
    html = service_preview_csv(content, n=10)
    return {"html": html}

import os
from pathlib import Path
from fastapi import APIRouter, Request, Form
from fastapi.responses import FileResponse
from dependencies import templates, sanitize_filename
from services.generate_mei_service import generate_mei_package
from config import TEMP_MEI_DIR, MEI_TEMPLATES_DIR

router = APIRouter(prefix="/generate-mei", tags=["generate-mei"])

TEMP = TEMP_MEI_DIR

BASE_DIR = Path(__file__).resolve().parents[2]   # backend folder

@router.get("")
def page(request: Request):
    return templates.TemplateResponse(
        "generate_mei.html",
        {"request": request,"title": "Generate MEI-XML files", "result_ready": False}
    )


@router.post("")
def process(
    request: Request,
    pianist_first: str = Form(...),
    pianist_last: str = Form(...),
    gnd_uid: str = Form(...),
    year: str = Form(...),
    context: str = Form(...),
    label_addition: str = Form(...),
    manifestation_id: str = Form(...),
    manifestation_n: int = Form(1)
):
    # sanitize / normalize small inputs
    pianist_first = (pianist_first or "").strip()
    pianist_last = (pianist_last or "").strip()
    gnd_uid = (gnd_uid or "").strip()
    year = sanitize_filename(year or "unknown-year", default="unknown-year")
    context = (context or "").strip()
    manifestation_id = (manifestation_id or "").strip()
    manifestation_n = int(manifestation_n or 1)
    label_addition = (label_addition or "").strip()

    zip_path, first_meihead_str, first_filename = generate_mei_package(
        manifestation_id=manifestation_id,
        manifestation_n=manifestation_n,
        year=year,
        pianist_first=pianist_first,
        pianist_last=pianist_last,
        gnd_uid=gnd_uid,
        context=context,
        label_addition=label_addition,
        templates_dir=MEI_TEMPLATES_DIR,
        out_dir=TEMP_MEI_DIR
    )

    token = os.path.basename(zip_path)
    return templates.TemplateResponse("generate_mei.html",
                                      {"request": request,
                                       "result_ready": True,
                                       "token": token,
                                       "meihead_preview": first_meihead_str,
                                       "preview_filename": first_filename})


@router.get("/download/{token}")
def download(token: str):
    path = os.path.join(TEMP, token)
    return FileResponse(path, filename=token)

import os
from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import FileResponse
from backend.dependencies import templates, ensure_extension, store_file, sanitize_filename
from backend.services.mei_service import insert_into_mei

router = APIRouter(prefix="/insert-mei", tags=["mei"])

TEMP = "temp_mei"
os.makedirs(TEMP, exist_ok=True)

@router.get("")
def page(request: Request):
    return templates.TemplateResponse("insert_mei.html",
                                      {"request": request, "title": "Insert MEI", "result_ready": False})

@router.post("")
async def process(
    request: Request,
    mei: UploadFile,
    csv: UploadFile,
    tempo: str = Form(""),
    dynam: str = Form(""),
    annot: str = Form(""),
    annot_label: str = Form(""),
    filename: str = Form(...)
):
    filename = sanitize_filename(filename, default="modified.mei")
    mei = ensure_extension(mei, (".mei", ".xml"))
    csv = ensure_extension(csv, (".csv",))
    mei_bytes = await mei.read()
    csv_bytes = await csv.read()

    out_path = store_file(TEMP, ".csv")


    insert_into_mei(
        mei_bytes, csv_bytes,
        tempo, dynam, annot, annot_label,
        out_path
    )

    token = os.path.basename(out_path)
    return templates.TemplateResponse("insert_mei.html",
                                      {"request": request, "title": "Insert MEI",
                                       "result_ready": True, "token": token})

@router.get("/download/{token}")
def download(token: str):
    path = os.path.join(TEMP, token)
    return FileResponse(path, filename="modified.mei")


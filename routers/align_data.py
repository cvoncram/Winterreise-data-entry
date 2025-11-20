import uuid
import os
from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import FileResponse
from backend.dependencies import templates
from backend.services.align_data_service import align_data

router = APIRouter(prefix="/align", tags=["align"])

TEMP = "temp_align"
os.makedirs(TEMP, exist_ok=True)

@router.get("")
def page(request: Request):
    return templates.TemplateResponse("align_data.html",
                                      {"request": request, "title": "Align Data", "result_ready": False})

@router.post("")
async def process(
    request: Request,
    base: UploadFile,
    plugin: UploadFile,
    plugin_type: str = Form(...),
    agg: str = Form("mean"),
    filename: str = Form(...)
):
    base_bytes = await base.read()
    plugin_bytes = await plugin.read()

    out_path = os.path.join(TEMP, f"{uuid.uuid4()}.csv")
    align_data(base_bytes, plugin_bytes, plugin_type, agg, out_path)

    token = os.path.basename(out_path)
    return templates.TemplateResponse("align_data.html",
                                      {"request": request, "title": "Align Data",
                                       "result_ready": True, "token": token})

@router.get("/download/{token}")
def download(token: str):
    path = os.path.join(TEMP, token)
    return FileResponse(path, filename="combined.csv")


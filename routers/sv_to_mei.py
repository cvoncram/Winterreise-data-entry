import os
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, Form, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from backend.dependencies import ensure_extension, store_file, TOKENS, sanitize_filename, templates
from backend.services.sv_parser import parse_sv_bytes
from backend.services.sv_mapper import generate_mei_from_sv, generate_layer_previews
from backend.services.mei_preview import extract_preview_measures

router = APIRouter(prefix="/sv-to-mei", tags=["sv-to-mei"])

OUTPUT_DIR = os.path.join("backend", "tmp", "sv_to_mei")
os.makedirs(OUTPUT_DIR, exist_ok=True)

@router.get("/")
async def form(request: Request):
    return templates.TemplateResponse("sv_to_mei.html", {"request": request, "title": "SV → MEI"})

@router.post("/preview-layers")
async def preview_layers(sv_file: UploadFile):
    ensure_extension(sv_file, (".sv",))
    sv_bytes = await sv_file.read()

    try:
        sv_tree = parse_sv_bytes(sv_bytes)
        previews, detected_layers = generate_layer_previews(sv_tree)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid SV file: {e}")

    return JSONResponse({"previews": previews, "detected_layers": detected_layers})

@router.post("/process")
async def process(
    sv_file: UploadFile,
    mei_file: UploadFile,
    layer_beat: Optional[str] = Form(None),
    layer_spectral: Optional[str] = Form(None),
    layer_power: Optional[str] = Form(None),
    sample_rate: Optional[int] = Form(44100),
    mf_db: Optional[float] = Form(-30.0),
    step_db: Optional[float] = Form(10.0),
):
    ensure_extension(sv_file, (".sv",))
    ensure_extension(mei_file, (".mei", ".xml"))

    sv_bytes = await sv_file.read()
    mei_bytes = await mei_file.read()

    try:
        sv_tree = parse_sv_bytes(sv_bytes)
        modified_mei_bytes, preview_measures, warnings = generate_mei_from_sv(
            sv_tree=sv_tree,
            mei_bytes=mei_bytes,
            sample_rate=sample_rate,
            mf_db=mf_db,
            step_db=step_db,
            beat_layer_name=layer_beat,
            spectral_layer_name=layer_spectral,
            power_layer_name=layer_power
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    token = sanitize_filename(str(int(time.time())), default=str(int(time.time())))
    out_path = store_file(OUTPUT_DIR, f"_{token}.mei")

    with open(out_path, "wb") as f:
        f.write(modified_mei_bytes)

    TOKENS[token] = {
        "time": time.time(),
        "path": out_path,
        "preview": preview_measures,
        "warnings": warnings,
        "original_name": mei_file.filename,
        "mei_bytes": modified_mei_bytes,
    }


    return JSONResponse({"token": token, "warnings": warnings})


@router.post("/preview")
async def preview(token: str = Form(...)):
    if token not in TOKENS:
        raise HTTPException(status_code=404, detail="Token not found")

    info = TOKENS[token]
    preview_measures = info.get("preview", [])

    return JSONResponse({
        "measures": preview_measures,
        "warnings": info.get("warnings", [])
    })


@router.get("/download/{token}")
async def download(token: str):
    if token not in TOKENS:
        raise HTTPException(status_code=404, detail="Token not found")
    path = TOKENS[token]["path"]

    return FileResponse(
        path,
        filename=TOKENS[token].get("original_name") or os.path.basename(path),
        media_type="application/octet-stream"
    )
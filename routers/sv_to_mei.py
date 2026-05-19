import os
import time
from typing import Optional
from fastapi import APIRouter, UploadFile, Form, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from dependencies import ensure_extension, store_file, TOKENS, sanitize_filename, templates
from services.sv_parser import parse_sv_bytes
from services.sv_mapper import generate_mei_from_sv
from services.mei_preview import generate_layer_previews
from config import SV_TO_MEI_DIR

router = APIRouter(prefix="/sv-to-mei", tags=["sv-to-mei"])

OUTPUT_DIR = SV_TO_MEI_DIR

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
    pickup: Optional[bool] = Form(None),
    dyn_method: Optional[bool] = Form(None)
):
    ensure_extension(sv_file, (".sv",))
    ensure_extension(mei_file, (".mei", ".xml"))

    sv_bytes = await sv_file.read()
    mei_bytes = await mei_file.read()

    try:
        # Generate MEI from SV
        sv_tree = parse_sv_bytes(sv_bytes)
        modified_mei_bytes, preview_measures, warnings = generate_mei_from_sv(
            sv_tree=sv_tree,
            mei_bytes=mei_bytes,
            sample_rate=sample_rate,
            mf_db=mf_db,
            step_db=step_db,
            beat_layer_name=layer_beat,
            spectral_layer_name=layer_spectral,
            power_layer_name=layer_power,
            pickup=pickup,
            dyn_method=dyn_method
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    # -------------------------------
    # Insert <application> metadata
    # -------------------------------
    from lxml import etree
    from datetime import datetime

    XML_NS = "http://www.w3.org/XML/1998/namespace"

    mei_root = etree.fromstring(modified_mei_bytes)

    # Detect MEI namespace
    ns = {}
    if mei_root.tag.startswith("{"):
        uri = mei_root.tag.split("}")[0].strip("{")
        ns = {"mei": uri}

    # Navigate/create meiHead > encodingDesc > appInfo
    meiHead = mei_root.find("mei:meiHead", namespaces=ns)
    if meiHead is None:
        meiHead = etree.SubElement(mei_root, "meiHead")

    encodingDesc = meiHead.find("mei:encodingDesc", namespaces=ns)
    if encodingDesc is None:
        encodingDesc = etree.SubElement(meiHead, "encodingDesc")

    appInfo = encodingDesc.find("mei:appInfo", namespaces=ns)
    if appInfo is None:
        appInfo = etree.SubElement(encodingDesc, "appInfo")

    # Create new <application>
    app = etree.SubElement(appInfo, "application")
    app.set(f"{{{XML_NS}}}id", "sv_to_mei")  # Correct xml:id
    app.set("version", "1.0")

    # Name and description
    name_el = etree.SubElement(app, "name")
    name_el.text = "Sonic Visualiser to MEI mapping tool"

    p_el = etree.SubElement(app, "p")
    p_el.text = f"The Sonic Visualiser data was inserted by SV to MEI mapping tool on {datetime.now():%B %d, %Y}."

    # Store parameters as <annot>
    params = {
        "sampleRate": sample_rate,
        "mf_dB_calibration": mf_db,
        "dB_per_dynamic_level": step_db
    }
    for k, v in params.items():
        annot = etree.SubElement(app, "annot")
        annot.set("type", k)
        annot.set("value", str(v))

    # Serialize back to bytes
    modified_mei_bytes = etree.tostring(
        mei_root,
        pretty_print=True,
        encoding="UTF-8",
        xml_declaration=True
    )

    # -------------------------------
    # Save file & update TOKENS (unchanged)
    # -------------------------------
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
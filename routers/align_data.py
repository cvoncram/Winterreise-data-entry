from io import BytesIO
from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
import pandas as pd
from backend.services import csv_utils
from backend.services.align_data_service import align_spectral_centroid, align_powercurve

router = APIRouter(prefix="/align", tags=["Align Data"])
templates = Jinja2Templates(directory="backend/templates")

# NEW: unified temp directory usage
TEMP = "temp_csv"
os.makedirs(TEMP, exist_ok=True)

# ---------------------------
# GET main UI page
# ---------------------------
@router.get("")
def align_page(request: Request):
    return templates.TemplateResponse(
        "align_data.html",
        {"request": request, "title": "Align & Map SV Output"}
    )


# ---------------------------
# Preview CSV (upload)
# ---------------------------
@router.post("/preview_csv")
async def preview_csv(file: UploadFile, has_header: bool = Form(True)):
    content = await file.read()
    token = csv_utils.store_temp_csv(content, TEMP)

    if has_header:
        df = pd.read_csv(BytesIO(content), header=0)
    else:
        df = pd.read_csv(BytesIO(content), header=None, names=["time", "value"])

    html = df.head(10).to_html(classes="preview-table", index=False, escape=True)
    return JSONResponse({"html": html, "token": token})


# ---------------------------
# Preview Stored Temp CSV
# ---------------------------
@router.post("/preview_temp_csv")
async def preview_temp_csv(token: str = Form(...)):
    content = csv_utils.load_temp_csv(token, TEMP)
    df = pd.read_csv(BytesIO(content))
    df.columns = [str(c).lower() for c in df.columns]
    html = df.head(10).to_html(classes="preview-table", index=False, escape=True)
    return JSONResponse({"html": html})


# ---------------------------
# Apply Spectral Centroid Alignment
# ---------------------------
@router.post("/apply_spectral_centroid")
async def apply_spectral_centroid(
    base_token: str = Form(...),
    sc_token: str = Form(...)
):
    base_content = csv_utils.load_temp_csv(base_token, TEMP)
    sc_content = csv_utils.load_temp_csv(sc_token, TEMP)

    base_df = pd.read_csv(BytesIO(base_content), dtype=str)
    sc_df = pd.read_csv(BytesIO(sc_content), dtype=str)

    base_df.columns = [c.lower() for c in base_df.columns]
    sc_df.columns = ['time', 'value']

    base_time_col = 'time' if 'time' in base_df.columns else 'measure.beat'
    base_df[base_time_col] = pd.to_numeric(base_df[base_time_col], errors='coerce')
    sc_df['time'] = pd.to_numeric(sc_df['time'], errors='coerce')
    sc_df['value'] = pd.to_numeric(sc_df['value'], errors='coerce')

    result_df = align_spectral_centroid(base_df.rename(columns={base_time_col: 'time'}), sc_df)
    result_token = csv_utils.store_temp_csv(result_df.to_csv(index=False).encode("utf-8"), TEMP)
    return JSONResponse({"token": result_token})


# ---------------------------
# Apply Powercurve Alignment
# ---------------------------
@router.post("/apply_powercurve")
async def apply_powercurve(
    base_token: str = Form(...),
    power_token: str = Form(...),
    mf_ref: float = Form(...)
):
    base_content = csv_utils.load_temp_csv(base_token, TEMP)
    power_content = csv_utils.load_temp_csv(power_token, TEMP)

    base_df = pd.read_csv(BytesIO(base_content), dtype=str)
    power_df = pd.read_csv(BytesIO(power_content), dtype=str)

    base_df.columns = [c.lower() for c in base_df.columns]
    power_df.columns = ['time', 'value']

    base_time_col = 'time' if 'time' in base_df.columns else 'measure.beat'
    base_df[base_time_col] = pd.to_numeric(base_df[base_time_col], errors='coerce')
    power_df['time'] = pd.to_numeric(power_df['time'], errors='coerce')
    power_df['value'] = pd.to_numeric(power_df['value'], errors='coerce')

    result_df = align_powercurve(
        base_df.rename(columns={base_time_col: 'time'}),
        power_df,
        mf_ref
    )

    result_token = csv_utils.store_temp_csv(result_df.to_csv(index=False).encode("utf-8"), TEMP)
    return JSONResponse({"token": result_token})


# ---------------------------
# Download final CSV
# ---------------------------
@router.get("/download/{token}")
def download_result(token: str):
    path = os.path.join(TEMP, token)
    return FileResponse(path, filename="aligned.csv")

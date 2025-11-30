from io import BytesIO
from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
from backend.dependencies import templates, ensure_extension, store_file, sanitize_filename
from backend.services.correct_beats_service import add_tempo_column_inplace, process_csv
from backend.services.csv_utils import rename_column_inplace, preview_csv as service_preview_csv
from backend.services.correct_beats_service import recalc_measure_beat
from backend.services.correct_beats_service import preprocess_csv_for_preview
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

    # --- Preprocess only on initial upload ---
    from backend.services.correct_beats_service import preprocess_csv_for_preview
    df = preprocess_csv_for_preview(content)  # returns a pd.DataFrame

    # Save preprocessed CSV
    df.to_csv(token_path, index=False)
    token = os.path.basename(token_path)

    html = df.head(10).to_html(classes="preview-table", index=False, escape=True)
    return {"html": html, "token": token}

@router.post("/preview_temp_csv")
async def preview_temp_csv(token: str = Form(...)):
    csv_path = os.path.join(TEMP, token)
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        return JSONResponse({"error": f"Could not load token: {str(e)}"}, status_code=400)

    html = df.head(10).to_html(classes="preview-table", index=False, escape=True)
    return JSONResponse({"html": html})


@router.post("/rename")
async def rename_column(
    token: str = Form(...),
    old: str = Form(...),
    new: str = Form(...),
    move_left: str = Form("1")
):
    csv_path = os.path.join(TEMP, token)
    try:
        df = pd.read_csv(csv_path)

        # Rename if exists
        if old not in df.columns:
            raise ValueError(f"Column '{old}' not found.")
        df = df.rename(columns={old: new})

        # Optionally move renamed column to left
        if move_left == "1":
            cols = [new] + [c for c in df.columns if c != new]
            df = df[cols]

        # Save modified CSV
        df.to_csv(csv_path, index=False)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    html = df.head(10).to_html(classes="preview-table", index=False, escape=True)
    return {"html": html, "token": token}


# ---------------------------
# Recalculate measure.beat
# ---------------------------
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
        # Load CSV
        df = pd.read_csv(csv_path)
        # Ensure correct column names/order before recalculating measure.beat
        df = preprocess_csv_for_preview(df.to_csv(index=False).encode("utf-8"))
        # Recalculate measure.beat column
        n_rows = len(df)
        from backend.services.correct_beats_service import _build_measurebeat_list_for_nrows
        mb = _build_measurebeat_list_for_nrows(n_rows, int(bpm), float(anacrusis) if has_anacrusis_bool else 0)
        df["measure.beat"] = mb
        # Keep measure.beat left, time right
        cols_order = ["measure.beat", "time"] + [c for c in df.columns if c not in ("measure.beat","time")]
        df = df[cols_order]
        # Save back to disk
        df.to_csv(csv_path, index=False)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    html = df.head(10).to_html(classes="preview-table", index=False, escape=True)
    return {"html": html, "token": token}


# ---------------------------
# Add tempo column
# ---------------------------
@router.post("/tempo")
async def add_tempo_column(token: str = Form(...)):
    csv_path = os.path.join(TEMP, token)
    try:
        add_tempo_column_inplace(csv_path)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    # load CSV after modification for preview
    df = pd.read_csv(csv_path)
    html = df.head(10).to_html(classes="preview-table", index=False, escape=True)
    return {"html": html, "token": token}
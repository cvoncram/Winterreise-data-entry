import os
from fastapi import APIRouter, Request, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from backend.dependencies import templates, store_file
from backend.services.mei_service import insert_into_mei, read_csv_upload
from backend.services import csv_utils

router = APIRouter(prefix="/insert-mei", tags=["MEI"])
TEMP = "temp_mei"
os.makedirs(TEMP, exist_ok=True)


@router.get("")
def page(request: Request):
    return templates.TemplateResponse(
        "insert_mei.html",
        {"request": request, "result_ready": False}
    )


@router.post("/preview_csv")
async def preview_csv(file: UploadFile):
    content = await file.read()
    token = csv_utils.store_temp_csv(content)
    df = read_csv_upload(content)
    html = df.head(10).to_html(classes="preview-table", index=False, escape=True)
    return JSONResponse({"html": html, "token": token})


@router.post("/csv_columns")
async def csv_columns(token: str = Form(...)):
    content = csv_utils.load_temp_csv(token)
    df = read_csv_upload(content)
    return JSONResponse({"columns": list(df.columns)})


@router.post("/process")
async def process(
    csv_token: str = Form(...),
    mei_file: UploadFile = Form(...),
    tempo_col: str = Form(""),
    dynam_col: str = Form(""),
    annot_col: str = Form("")
):
    # Read uploaded MEI and CSV content
    mei_bytes = await mei_file.read()
    csv_content = csv_utils.load_temp_csv(csv_token)

    # Output file path
    out_path = store_file(TEMP, ".mei")

    # Insert CSV data into MEI
    # insert_into_mei returns a list of preview measures (strings)
    preview_measures_list = insert_into_mei(
        mei_bytes,
        csv_content,
        tempo_col,
        dynam_col,
        annot_col,
        output_path=out_path
    )

    # Generate download token
    token = os.path.basename(out_path)

    # Return JSON for frontend (preview + download)
    return JSONResponse({
        "token": token,
        "preview_measures": preview_measures_list
    })


@router.get("/download/{token}")
def download(token: str):
    path = os.path.join(TEMP, token)
    return FileResponse(path, filename="modified.mei")

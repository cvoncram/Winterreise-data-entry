import pandas as pd
from io import BytesIO
import uuid
import os

# Temp folder for preview CSVs
TEMP_DIR = "temp_csv"
os.makedirs(TEMP_DIR, exist_ok=True)

def read_csv_upload(content: bytes) -> pd.DataFrame:
    """
    Read CSV from uploaded bytes.
    Detect headers: use first row if mostly strings, otherwise add defaults.
    """
    df = pd.read_csv(BytesIO(content), dtype=str, header=None)
    df = ensure_headers(df)
    return df

def preview_csv(content: bytes, n: int = 10, has_header: bool = True) -> str:
    """Return HTML table preview of first n rows, optionally using first row as header."""
    if has_header:
        df = pd.read_csv(BytesIO(content), header=0)
    else:
        df = pd.read_csv(BytesIO(content), header=None, names=["time", "value"])
    
    return df.head(n).to_html(classes="preview-table", index=False, escape=True)


def store_temp_csv(content: bytes, suffix=".csv") -> str:
    token = f"{uuid.uuid4()}{suffix}"
    path = os.path.join(TEMP_DIR, token)
    with open(path, "wb") as f:
        f.write(content)
    return token

def load_temp_csv(token: str) -> bytes:
    path = os.path.join(TEMP_DIR, token)
    with open(path, "rb") as f:
        return f.read()

def apply_csv_operation(token: str, operation) -> None:
    path = os.path.join(TEMP_DIR, token)
    df = pd.read_csv(path, dtype=str)
    df = operation(df)
    df.to_csv(path, index=False)

def rename_column_inplace(csv_path: str, old: str, new: str, move_to_left: bool = True):
    df = pd.read_csv(csv_path, dtype=str, header=None)
    df = ensure_headers(df)

    cols_lower = [c.lower() for c in df.columns]
    try:
        idx = cols_lower.index(old.lower())
    except ValueError:
        raise ValueError(f"Column '{old}' not found.")

    real_name = df.columns[idx]
    df = df.rename(columns={real_name: new})

    if move_to_left:
        cols = [new] + [c for c in df.columns if c != new]
        df = df[cols]

    df.to_csv(csv_path, index=False)

def ensure_headers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect headers:
      - If first row mostly numeric → no headers → add defaults
      - If first row mostly strings → use as headers
    Lowercase all headers.
    """
    first_row = df.iloc[0]
    numeric_count = sum(pd.to_numeric(first_row, errors='coerce').notna())
    n_cols = len(df.columns)

    if numeric_count >= n_cols / 2:
        # Most numeric → no headers
        default_headers = ["measure.beat", "time"]
        if n_cols > 2:
            default_headers += ["tempo (bpm)"] + [f"col{i}" for i in range(4, n_cols+1)]
        default_headers = default_headers[:n_cols]

        # Move first row into data
        df = pd.concat([
            pd.DataFrame([first_row.values], columns=default_headers),
            df.iloc[1:].reset_index(drop=True)
        ], ignore_index=True)
        df.columns = [str(c).lower() for c in df.columns]
    else:
        # Use first row as header
        df.columns = [str(c).lower() for c in df.iloc[0]]
        df = df.iloc[1:].reset_index(drop=True)

    return df

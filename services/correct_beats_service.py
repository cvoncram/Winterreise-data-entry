import pandas as pd
import numpy as np
from io import BytesIO
from backend.services.csv_utils import read_csv_upload

def _build_measurebeat_list_for_nrows(n_rows: int, bpm: int, anacrusis_value: float) -> list:
    k = int(np.floor(anacrusis_value))
    frac = float(anacrusis_value) - k

    prepended = []

    if frac > 0:
        prepended.append("0")

    if k > 0:
        for b in range(1, k + 1):
            prepended.append(f"0.{b}")

    needed = max(0, n_rows - len(prepended))
    regular = []
    current_measure = 1
    current_beat = 1
    while len(regular) < needed:
        regular.append(f"{current_measure}.{current_beat}")
        current_beat += 1
        if current_beat > bpm:
            current_measure += 1
            current_beat = 1

    combined = (prepended + regular)[:n_rows]
    return combined

def process_csv(content, bpm, anacrusis_value, has_anacrusis, output_path):
    df = read_csv_upload(content)
    df.columns = [c.lower() for c in df.columns]

    time_col = None
    for c in df.columns:
        if c.lower() == "time":
            time_col = c
            break
    if time_col is None:
        raise ValueError("No time column found")

    n_rows = len(df)
    A = float(anacrusis_value) if has_anacrusis else 0.0

    mb = _build_measurebeat_list_for_nrows(n_rows, int(bpm), float(A))
    df["measure.beat"] = mb

    cols = ["measure.beat"] + [c for c in df.columns if c != "measure.beat"]
    df = df[cols]

    times = pd.to_numeric(df[time_col], errors="coerce").to_numpy()
    tempo_vals = np.full(len(times), np.nan)
    valid = ~np.isnan(times)
    if sum(valid) >= 2:
        diffs = np.diff(times)
        with np.errstate(divide='ignore', invalid='ignore'):
            bpm_vals = 60.0 / diffs
        tempo_vals[:-1] = bpm_vals
    df["tempo (bpm)"] = tempo_vals

    df.to_csv(output_path, index=False)

def recalc_measure_beat(csv_path: str, bpm: int, anacrusis_value: float):
    df = pd.read_csv(csv_path)
    n_rows = len(df)
    mb = _build_measurebeat_list_for_nrows(n_rows, int(bpm), float(anacrusis_value))
    df["measure.beat"] = mb
    cols = ["measure.beat"] + [c for c in df.columns if c != "measure.beat"]
    df = df[cols]
    df.to_csv(csv_path, index=False)

def add_tempo_column_inplace(csv_path: str):
    df = pd.read_csv(csv_path)
    time_col = None
    for c in df.columns:
        if c.lower() == "time":
            time_col = c
            break
    if time_col is None:
        raise ValueError("No 'time' column found.")

    times = pd.to_numeric(df[time_col], errors="coerce")
    tempo_vals = [None] * len(times)
    for i in range(len(times)-1):
        if pd.isna(times[i]) or pd.isna(times[i+1]):
            tempo_vals[i] = None
        else:
            tempo_vals[i] = 60.0 / (times[i+1]-times[i])
    df["tempo (bpm)"] = tempo_vals
    df.to_csv(csv_path, index=False)


# ===============================
# New function for CSV preview preprocessing
# ===============================
def preprocess_csv_for_preview(content: bytes) -> pd.DataFrame:
    """
    Preprocess CSV specifically for the Correct Beats page preview.
    - Checks if first row has text headers
    - Assigns 'measure.beat' and 'time' columns
    - Moves columns appropriately
    - Lowercases all headers
    """
    df = pd.read_csv(BytesIO(content), dtype=str, header=None)
    first_row = df.iloc[0]

    # Detect if first row has non-numeric values
    numeric_count = sum(pd.to_numeric(first_row, errors='coerce').notna())
    n_cols = len(df.columns)
    df_processed = None

    if numeric_count < n_cols / 2:
        # First row has text headers
        headers = [str(c).lower() for c in first_row]
        df_processed = df[1:].copy()
        df_processed.columns = headers

        # Identify TIME column (case-insensitive)
        time_col = next((c for c in headers if "time" in c.lower()), None)
        # Rename the other column to 'measure.beat' by default
        other_cols = [c for c in headers if c != time_col]
        for c in other_cols:
            df_processed = df_processed.rename(columns={c: "measure.beat"})

        # Reorder columns: measure.beat left, time right
        cols_order = ["measure.beat"]
        if time_col:
            cols_order.append(time_col)
        df_processed = df_processed[cols_order]

    else:
        # First row mostly numeric → pick column with longer number as 'time'
        first_values = pd.to_numeric(first_row, errors='coerce')
        col_lengths = [len(str(v)) for v in first_values]
        time_idx = col_lengths.index(max(col_lengths))
        other_idx = 1 - time_idx if n_cols == 2 else [i for i in range(n_cols) if i != time_idx][0]

        data = df.copy()
        data.columns = [f"col{i}" for i in range(n_cols)]
        df_processed = data.copy()
        df_processed.columns = [f"measure.beat" if i == other_idx else "time" if i == time_idx else f"col{i}" for i in range(n_cols)]
        # Move measure.beat left, time right
        cols_order = ["measure.beat", "time"] + [c for c in df_processed.columns if c not in ("measure.beat","time")]
        df_processed = df_processed[cols_order]

    return df_processed

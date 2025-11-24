import pandas as pd
import numpy as np
from io import BytesIO
from backend.services.csv_utils import read_csv_upload

def find_col_ci(df, name):
    """Case-insensitive column lookup"""
    lower = [c.lower() for c in df.columns]
    try:
        return df.columns[lower.index(name.lower())]
    except ValueError:
        return None
    

def _build_measurebeat_list_for_nrows(n_rows: int, bpm: int, anacrusis_value: float) -> list:
    """
    Build measure.beat strings for n_rows according to the anacrusis rules:
    - if frac == 0 and k>0 -> prepend 0.1 .. 0.k
    - if frac > 0 -> prepend '0' and then (if k>0) 0.1 .. 0.k
    then continue with regular beats 1.1,1.2.. up to bpm, 2.1...
    """
    k = int(np.floor(anacrusis_value))
    frac = float(anacrusis_value) - k

    prepended = []

    # if there is a fractional part, always add a single '0'
    if frac > 0:
        prepended.append("0")

    # if there is an integer part, append 0.1 ... 0.k
    if k > 0:
        for b in range(1, k + 1):
            prepended.append(f"0.{b}")

    # Now generate regular beats until we have enough rows
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

    # concat and ensure length n_rows (trim if prepended longer than n_rows)
    combined = (prepended + regular)[:n_rows]
    return combined

def process_csv(content, bpm, anacrusis_value, has_anacrusis, output_path):
    """
    Existing full-file processing: read CSV, compute measure.beat and tempo and write output_path.
    Uses read_csv_upload (which ensures headers/lowercase).
    """
    df = read_csv_upload(content)

    # keep headers lowercase for consistency
    df.columns = [c.lower() for c in df.columns]

    # find time column (case-insensitive)
    time_col = None
    for c in df.columns:
        if c.lower() == "time":
            time_col = c
            break
    if time_col is None:
        raise ValueError("No time column found")

    n_rows = len(df)
    A = float(anacrusis_value) if has_anacrusis else 0.0

    # Build measure.beat column using helper
    mb = _build_measurebeat_list_for_nrows(n_rows, int(bpm), float(A))
    df["measure.beat"] = mb

    # move measure.beat to left
    cols = ["measure.beat"] + [c for c in df.columns if c != "measure.beat"]
    df = df[cols]

    # compute tempo (bpm) from time column
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
    """
    Recalculate the measure.beat column for an already-stored CSV on disk.
    Uses the exact same rules as process_csv to be consistent.
    """
    df = pd.read_csv(csv_path)

    n_rows = len(df)
    mb = _build_measurebeat_list_for_nrows(n_rows, int(bpm), float(anacrusis_value))

    df["measure.beat"] = mb

    # move measure.beat to left
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

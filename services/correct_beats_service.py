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

def process_csv(content, bpm, anacrusis_value, has_anacrusis, output_path):
    df = read_csv_upload(content)
    df.columns = [c.lower() for c in df.columns]

    time_col = find_col_ci(df, "time")
    if time_col is None:
        raise ValueError("No time column found")
    time_col = time_col.lower()

    # Measure.beat column
    n_rows = len(df)
    measurebeat_values = []
    A = anacrusis_value if has_anacrusis else 0.0
    k = int(np.floor(A))
    frac = A - k

    if A > 0:
        if frac > 0:
            measurebeat_values.append("0")
            for b in range(1, k + 1):
                measurebeat_values.append(f"0.{b}")
        else:
            for b in range(1, k + 1):
                measurebeat_values.append(f"0.{b}")

    current_measure = 1
    current_beat = 1
    remaining = n_rows - len(measurebeat_values)

    for _ in range(remaining):
        measurebeat_values.append(f"{current_measure}.{current_beat}")
        current_beat += 1
        if current_beat > bpm:
            current_measure += 1
            current_beat = 1

    df["measure.beat"] = measurebeat_values
    cols = ["measure.beat"] + [c for c in df.columns if c != "measure.beat"]
    df = df[cols]

    # Tempo calculation
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
    measurebeat_values = []

    A = anacrusis_value
    k = int(np.floor(A))
    frac = A - k

    if A > 0:
        if frac > 0:
            measurebeat_values.append("0")
            for b in range(1, k+1):
                measurebeat_values.append(f"0.{b}")
        else:
            for b in range(1, k+1):
                measurebeat_values.append(f"0.{b}")

    current_measure = 1
    current_beat = 1
    remaining = n_rows - len(measurebeat_values)
    for _ in range(remaining):
        measurebeat_values.append(f"{current_measure}.{current_beat}")
        current_beat += 1
        if current_beat > bpm:
            current_measure += 1
            current_beat = 1

    df["measure.beat"] = measurebeat_values
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

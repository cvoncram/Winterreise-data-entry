import pandas as pd
import numpy as np
from io import BytesIO
from backend.dependencies import read_csv_upload

def find_col_ci(df, name):
    lower = [c.lower() for c in df.columns]
    try:
        return df.columns[lower.index(name.lower())]
    except ValueError:
        return None

def process_csv(content, bpm, anacrusis_value, has_anacrusis, output_path):

    df = read_csv_upload(content)

    time_col = find_col_ci(df, "time")
    if time_col is None:
        raise ValueError("No time column found")

    df.columns = [c.lower() for c in df.columns]
    time_col = time_col.lower()

    A = anacrusis_value if has_anacrusis else 0.0

    n_rows = len(df)
    measurebeat_values = []

    k = int(np.floor(A))
    frac = A - k

    if A > 0:
        if frac == 0:
            for b in range(1, k + 1):
                measurebeat_values.append(f"0.{b}")
        else:
            measurebeat_values.append("0")
            for b in range(1, k + 1):
                measurebeat_values.append(f"0.{b}")

    remaining = n_rows - len(measurebeat_values)

    current_measure = 1
    current_beat = 1

    for _ in range(remaining):
        measurebeat_values.append(f"{current_measure}.{current_beat}")
        current_beat += 1
        if current_beat > bpm:
            current_measure += 1
            current_beat = 1

    df["measure.beat"] = measurebeat_values
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


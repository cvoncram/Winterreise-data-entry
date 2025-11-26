import pandas as pd
import numpy as np

# ---------------------------
# Spectral Centroid Alignment
# ---------------------------
def align_spectral_centroid(base_df: pd.DataFrame, sc_df: pd.DataFrame):
    """
    Aggregate spectral centroid values from sc_df into base_df intervals.
    base_df: must have 'time' column
    sc_df: must have 'time' and 'value' columns
    New column is always appended to the right.
    """

    # Ensure numeric
    base_df['time'] = pd.to_numeric(base_df['time'], errors='coerce')
    sc_df['time'] = pd.to_numeric(sc_df['time'], errors='coerce')
    sc_df['value'] = pd.to_numeric(sc_df['value'], errors='coerce')

    # Sort by time
    base_df = base_df.sort_values('time').reset_index(drop=True)
    sc_df = sc_df.sort_values('time').reset_index(drop=True)

    # Determine new column name
    col_base = "spectral centroid (Hz)"
    col_name = col_base
    i = 2
    while col_name in base_df.columns:
        col_name = f"{col_base}_{i}"
        i += 1

    aggregated = []
    for i, row in base_df.iterrows():
        start = row['time']
        end = base_df['time'][i + 1] if i + 1 < len(base_df) else np.inf

        # Select plugin values in interval
        mask = (sc_df['time'] >= start) & (sc_df['time'] < end)
        values = sc_df.loc[mask, 'value']

        aggregated.append(values.mean() if not values.empty else np.nan)

    base_df[col_name] = aggregated
    return base_df


# ---------------------------
# PowerCurve Alignment
# ---------------------------
def align_powercurve(base_df: pd.DataFrame, power_df: pd.DataFrame, mf_ref: float):
    """
    Aggregate powercurve values from power_df into base_df intervals.
    Added columns:
      • 'powercurve (dBFS)' – RMS per interval
      • 'interpreted dynamics' – based on mf_ref and 10dB step size
    Always append columns to the right.
    """

    base_df['time'] = pd.to_numeric(base_df['time'], errors='coerce')
    power_df['time'] = pd.to_numeric(power_df['time'], errors='coerce')
    power_df['value'] = pd.to_numeric(power_df['value'], errors='coerce')

    base_df = base_df.sort_values('time').reset_index(drop=True)
    power_df = power_df.sort_values('time').reset_index(drop=True)

    # Determine column names
    col_base_db = "powercurve (dBFS)"
    col_base_dyn = "interpreted dynamics"
    col_db = col_base_db
    col_dyn = col_base_dyn
    i = 2
    while col_db in base_df.columns:
        col_db = f"{col_base_db}_{i}"
        col_dyn = f"{col_base_dyn}_{i}"
        i += 1

    dB_values = []
    dyn_values = []

    # Dynamic labels (center points, 10 dB step)
    dynamic_levels = {
        "fff": mf_ref + 30,
        "ff":  mf_ref + 20,
        "f":   mf_ref + 10,
        "mf":  mf_ref + 0,
        "mp":  mf_ref - 10,
        "p":   mf_ref - 20,
        "pp":  mf_ref - 30,
        "ppp": mf_ref - 40
    }
    level_centers = np.array(list(dynamic_levels.values()))
    level_names = list(dynamic_levels.keys())

    for i, row in base_df.iterrows():
        start = row['time']
        end = base_df['time'][i + 1] if i + 1 < len(base_df) else np.inf

        mask = (power_df['time'] >= start) & (power_df['time'] < end)
        segment = power_df.loc[mask, 'value']

        if segment.empty:
            dB_values.append(np.nan)
            dyn_values.append("")
            continue

        # Convert dBFS → linear amplitude
        linear_segment = 10 ** (segment / 20)
        rms_linear = np.sqrt(np.mean(linear_segment ** 2))
        dB_rms = 20 * np.log10(rms_linear) if rms_linear > 0 else -120
        dB_values.append(dB_rms)

        # Determine nearest dynamic class
        diffs = np.abs(level_centers - dB_rms)
        idx = np.argmin(diffs)
        class_name = level_names[idx]
        class_center = level_centers[idx]

        offset = round(dB_rms - class_center)
        if offset > 0:
            dyn_label = f"{class_name}+{offset}"
        elif offset < 0:
            dyn_label = f"{class_name}{offset}"
        else:
            dyn_label = class_name

        dyn_values.append(dyn_label)

    base_df[col_db] = dB_values
    base_df[col_dyn] = dyn_values

    return base_df

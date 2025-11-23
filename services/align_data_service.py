import pandas as pd
import numpy as np
from io import BytesIO
from backend.dependencies import read_csv_upload, sanitize_filename

def align_data(base_bytes, plugin_bytes, plugin_type, agg, output_path):

    df_base = read_csv_upload(base_bytes)
    df_plugin = read_csv_upload(plugin_bytes)

    time_col = df_plugin.columns[0]
    value_col = df_plugin.columns[1]

    results = []

    for idx, row in df_base.iterrows():
        start = row["time"]
        try:
            end = df_base.loc[idx + 1, "time"]
        except:
            end = start

        mask = (df_plugin[time_col] >= start) & (df_plugin[time_col] < end)
        vals = df_plugin.loc[mask, value_col]

        if len(vals) == 0:
            results.append(np.nan)
            continue

        if plugin_type == "powercurve":
            p = 10 ** (vals / 10)
            m = np.mean(p)
            results.append(10 * np.log10(m))
        else:
            if agg == "mean":
                results.append(vals.mean())
            elif agg == "max":
                results.append(vals.max())
            elif agg == "min":
                results.append(vals.min())
            else:
                results.append(np.nan)

    df_base[value_col] = results
    df_base.to_csv(output_path, index=False)


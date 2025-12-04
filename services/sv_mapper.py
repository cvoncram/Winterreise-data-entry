from lxml import etree
from typing import List, Tuple, Optional
import numpy as np
from backend.services.sv_parser import find_datasets, extract_points
from copy import deepcopy

def generate_mei_from_sv(
    sv_tree,
    mei_bytes: bytes,
    sample_rate: int = 44100,
    mf_db: float = -30.0,
    step_db: float = 10.0,
    beat_layer_name: Optional[str] = None,
    spectral_layer_name: Optional[str] = None,
    power_layer_name: Optional[str] = None,
    pickup: bool = False
) -> Tuple[bytes, List[str], List[str]]:

    warnings = []

    parser = etree.XMLParser(remove_blank_text=True)
    mei_root = etree.fromstring(mei_bytes, parser)

    # -----------------------
    # Detect namespace
    # -----------------------
    ns = {}
    if mei_root.tag.startswith("{"):
        uri = mei_root.tag.split("}")[0].strip("{")
        ns = {"mei": uri}

    # -----------------------
    # Find datasets
    # -----------------------
    datasets = find_datasets(sv_tree)

    def select_layer(name, default_criteria):
        if name:
            for d in datasets.values():
                if d['element'].get('id') == name:
                    return d
        return next((d for d in datasets.values() if default_criteria(d)), None)

    beat_layer = select_layer(beat_layer_name, lambda d: d.get('model_name','')=="" or d['element'].get("dimensions")=="1")
    spectral_layer = select_layer(spectral_layer_name, lambda d: 'spectral' in d.get('model_name','').lower())
    power_layer = select_layer(power_layer_name, lambda d: 'power' in d.get('model_name','').lower())

    if not beat_layer:
        raise ValueError("No beat layer found in SV file.")

    beat_points = extract_points(beat_layer['element'])
    spectral_points = extract_points(spectral_layer['element']) if spectral_layer else []
    power_points = extract_points(power_layer['element']) if power_layer else []

    # -----------------------
    # Find <measure> elements
    # -----------------------
    measures = mei_root.findall('.//mei:measure', namespaces=ns)
    if not measures:
        raise ValueError("MEI file contains no <measure> elements.")
    num_measures = len(measures)

    # -----------------------
    # Determine beats per measure from first measure
    # -----------------------
    first_measure = measures[0]
    first_add = first_measure.find('mei:add', namespaces=ns)
    if first_add is None:
        first_add = etree.SubElement(first_measure, f"{{{ns['mei']}}}add")

    # Get all tempo tstamp.ges values as beats (sorted by appearance)
    beat_tstamps = [int(e.get('tstamp.ges')) for e in first_add.findall('mei:tempo', namespaces=ns)]
    if not beat_tstamps:
        # Fallback: use 1..N evenly spaced beats across measures
        beats_per_measure = len(beat_points) // num_measures if num_measures else 0
        if beats_per_measure == 0:
            raise ValueError("Cannot determine beats per measure (no tempo tags and no beats).")
        beat_tstamps = list(range(1, beats_per_measure+1))
    beats_per_measure = len(beat_tstamps)

    # -----------------------
    # Tempos (per interval)
    # -----------------------
    tempos = []
    for i in range(len(beat_points)-1):
        delta_sec = (beat_points[i+1][0] - beat_points[i][0]) / sample_rate
        tempos.append(60.0 / delta_sec if delta_sec > 0 else 0.0)
    tempos.append(tempos[-1] if tempos else 0.0)

    # -----------------------
    # Beat intervals (start,end) per SV interval
    # -----------------------
    beat_intervals = []
    for i in range(len(beat_points)-1):
        # interval from current beat to next beat
        beat_intervals.append((beat_points[i][0], beat_points[i+1][0]))
        if len(beat_points) == 1:
            beat_intervals = [(beat_points[0][0], beat_points[0][0] + 1)]

    def aggregate(points, start, end, mode='rms'):
        vals = [v for f, v, _ in points if v is not None and start <= f < end]
        if not vals:
            return None
        if mode == 'mean':
            return float(np.mean(vals))
        elif mode == 'rms':
            return float(np.sqrt(np.mean(np.square(vals))))
        return None

    # -----------------------
    # Helper: create/get child (preserves existing children if present)
    # -----------------------
    def get_or_create_measure_child(parent, tag, tstamp):
        child = parent.find(f"./mei:{tag}[@tstamp.ges='{tstamp}']", namespaces=ns)
        if child is None:
            child = etree.SubElement(parent, f"{{{ns['mei']}}}{tag}", **{'tstamp.ges': str(tstamp)})
        return child

    # -----------------------
    # Build timeline mapping: list of (interval_idx, measure_idx, tstamp)
    # interval_idx indexes beat_intervals/tempos/beat_points
    # measure_idx is index into measures list (0-based). measure 0 is pickup if pickup=True
    # -----------------------
    timeline = []

    total_intervals = len(beat_intervals)
    # If pickup, first SV interval is used for pickup measure (measure 0)
    interval_start_idx = 0
    if pickup:
        if total_intervals < 1:
            raise ValueError("Not enough intervals for pickup handling.")
        # map interval 0 -> pickup (measure 0) using last beat tstamp
        timeline.append({
            "interval_idx": 0,
            "measure_idx": 0,
            "tstamp": beat_tstamps[-1]
        })
        interval_start_idx = 1

    # remaining intervals are assigned to normal measures starting at measure index (0 or 1)
    normal_measure_offset = 1 if pickup else 0
    remaining_intervals = total_intervals - interval_start_idx

    # Map available intervals into measure/beat slots respecting beats_per_measure
    # For k from 0..remaining_intervals-1:
    #   measure  = normal_measure_offset + (k // beats_per_measure)
    #   beat_idx = k % beats_per_measure -> beat_tstamps[beat_idx]
    for k in range(remaining_intervals):
        interval_idx = interval_start_idx + k
        measure_rel = k // beats_per_measure
        beat_pos = k % beats_per_measure
        measure_idx = normal_measure_offset + measure_rel
        # guard against exceeding measure count
        if measure_idx >= num_measures:
            continue
        timeline.append({
            "interval_idx": interval_idx,
            "measure_idx": measure_idx,
            "tstamp": beat_tstamps[beat_pos]
        })

    # -----------------------
    # Iterate timeline and populate MEI accordingly
    # -----------------------
    for entry in timeline:
        interval_idx = entry["interval_idx"]
        measure_idx = entry["measure_idx"]
        tstamp_val = entry["tstamp"]
        tstamp_str = str(tstamp_val)

        if interval_idx >= len(beat_intervals):
            # defensive check
            continue

        start, end = beat_intervals[interval_idx]
        measure_el = measures[measure_idx]
        add_el = measure_el.find('mei:add', namespaces=ns)
        if add_el is None:
            add_el = etree.SubElement(measure_el, f"{{{ns['mei']}}}add")

        # If this entry is the pickup (measure 0 when pickup=True), then by rule:
        # populate only the last beat's spectral + dynamics; tempos should stay empty string.
        if pickup and measure_idx == 0:
            # Spectral
            val = aggregate(spectral_points, start, end, mode='mean') if spectral_points else None
            annot_el = get_or_create_measure_child(add_el, "annot", tstamp_str)
            annot_el.set("label", "spectral centroid (Hz)")
            annot_el.set("n", f"{val:.2f}" if val is not None else "")
            annot_el.set("type", "performed")

            # Dynamics
            vals = [v for f, v, _ in power_points if v is not None and start <= f < end] if power_points else []
            n_val = ""
            if vals:
                lin_vals = [10**(v/20) for v in vals]
                rms_lin = np.sqrt(np.mean(np.square(lin_vals)))
                val_db = 20 * np.log10(rms_lin)
                dyn_levels = ['ppp','pp','p','mp','mf','f','ff','fff']
                mf_index = dyn_levels.index('mf')
                level_values = {lvl: mf_db + (i - mf_index) * step_db for i, lvl in enumerate(dyn_levels)}
                if val_db < level_values['ppp'] or val_db > level_values['fff']:
                    n_val = "extreme"
                else:
                    closest_lvl, closest_val = min(level_values.items(), key=lambda x: abs(val_db - x[1]))
                    diff = int(round(val_db - closest_val))
                    n_val = closest_lvl if diff == 0 else f"{closest_lvl}{'+' if diff>0 else '-'}{abs(diff)}"
            dynam_el = get_or_create_measure_child(add_el, "dynam", tstamp_str)
            dynam_el.set("n", n_val)
            dynam_el.set("type", "performed")

            # Ensure tempo elements exist for pickup beats but leave empty mm
            # (we only ensure the tempo for that tstamp; other pickup tstamps handled below if needed)
            tempo_el = get_or_create_measure_child(add_el, "tempo", tstamp_str)
            tempo_el.set("mm", "")
            tempo_el.set("type", "performed")

            continue  # done with this pickup entry

        # --- Normal entries: fill tempo, spectral, dynamics ---
        # Tempo: always set (empty if no tempo value found)
        tempo_val = tempos[interval_idx] if interval_idx < len(tempos) else None
        tempo_el = get_or_create_measure_child(add_el, "tempo", tstamp_str)
        tempo_el.set("mm", f"{tempo_val:.2f}" if tempo_val is not None else "")
        tempo_el.set("type", "performed")

        # Spectral
        val = aggregate(spectral_points, start, end, mode='mean') if spectral_points else None
        annot_el = get_or_create_measure_child(add_el, "annot", tstamp_str)
        annot_el.set("label", "spectral centroid (Hz)")
        annot_el.set("n", f"{val:.2f}" if val is not None else "")
        annot_el.set("type", "performed")

        # Dynamics
        vals = [v for f, v, _ in power_points if v is not None and start <= f < end] if power_points else []
        n_val = ""
        if vals:
            lin_vals = [10**(v/20) for v in vals]
            rms_lin = np.sqrt(np.mean(np.square(lin_vals)))
            val_db = 20 * np.log10(rms_lin)
            dyn_levels = ['ppp','pp','p','mp','mf','f','ff','fff']
            mf_index = dyn_levels.index('mf')
            level_values = {lvl: mf_db + (i - mf_index) * step_db for i, lvl in enumerate(dyn_levels)}
            if val_db < level_values['ppp'] or val_db > level_values['fff']:
                n_val = "extreme"
            else:
                closest_lvl, closest_val = min(level_values.items(), key=lambda x: abs(val_db - x[1]))
                diff = int(round(val_db - closest_val))
                n_val = closest_lvl if diff == 0 else f"{closest_lvl}{'+' if diff>0 else '-'}{abs(diff)}"
        dynam_el = get_or_create_measure_child(add_el, "dynam", tstamp_str)
        dynam_el.set("n", n_val)
        dynam_el.set("type", "performed")

    # ---------------------------------
    # Beat count consistency warnings (mapping-aware, tail-end check)
    # ---------------------------------

    # Helper: count truly populated beats in a measure
    def count_populated_beats(measure):
        add_el = measure.find('mei:add', namespaces=ns)
        if add_el is None:
            return 0
        populated = 0
        # Check each tempo beat
        for tempo in add_el.findall('mei:tempo', namespaces=ns):
            if tempo.get('mm', '').strip() != '':
                populated += 1
        # Also check if dynam or annot are populated at tstamp without tempo?
        # Only needed if you want beats counted even if tempo is empty
        return populated

    # Step 1: Check last populated beat from the end
    last_measure_idx = num_measures - 1
    last_measure = measures[last_measure_idx]
    beats_in_last_measure = count_populated_beats(last_measure)

    if beats_in_last_measure == beats_per_measure:
        # Last measure is fully populated
        # Check if there are any extra SV intervals
        last_inserted_interval = timeline[-1]["interval_idx"] if timeline else -1
        extra_sv_intervals = max(0, len(beat_intervals) - (last_inserted_interval + 1))
        if extra_sv_intervals > 0:
            warnings.append(
                f"{extra_sv_intervals} SV interval{'s' if extra_sv_intervals>1 else ''} could not be inserted into MEI."
            )
    else:
        # Last measure not fully populated
        # Count trailing empty MEI beats
        empty_mei_beats = 0
        for m_idx in range(last_measure_idx, -1, -1):
            m = measures[m_idx]
            num_pop = count_populated_beats(m)
            empty_in_measure = beats_per_measure - num_pop
            empty_mei_beats += empty_in_measure
            if num_pop > 0:
                break  # found last populated beat

        if empty_mei_beats > 0:
            warnings.append(
                f"Your SV data leaves {empty_mei_beats} MEI beat{'s' if empty_mei_beats>1 else ''} empty at the end of the file."
            )

    preview_measures = [
        etree.tostring(
            deepcopy(m),    # deepcopy so original tree is untouched
            pretty_print=True,
            encoding=str
        )
        for m in measures[:5] + measures[-5:]
    ]

    modified_bytes = etree.tostring(mei_root, pretty_print=True, encoding='UTF-8')
    return modified_bytes, preview_measures, warnings

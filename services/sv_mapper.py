from lxml import etree
from typing import List, Tuple, Optional
import numpy as np
from services.sv_parser import find_datasets, extract_points
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
    pickup: bool = False,
    dyn_method: bool = True
    
) -> Tuple[bytes, List[str], List[str]]:

    warnings = []

    parser = etree.XMLParser(remove_blank_text=True)
    mei_root = etree.fromstring(mei_bytes, parser)

    # Detect namespace
    ns = {}
    if mei_root.tag.startswith("{"):
        uri = mei_root.tag.split("}")[0].strip("{")
        ns = {"mei": uri}

    # Find datasets
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

    # Find <measure> elements
    measures = mei_root.findall('.//mei:measure', namespaces=ns)
    if not measures:
        raise ValueError("MEI file contains no <measure> elements.")
    num_measures = len(measures)

    # Determine beats per measure from first measure
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

    # Tempos (per interval)
    tempos = []
    for i in range(len(beat_points)-1):
        delta_sec = (beat_points[i+1][0] - beat_points[i][0]) / sample_rate
        tempos.append(60.0 / delta_sec if delta_sec > 0 else 0.0)
    tempos.append(tempos[-1] if tempos else 0.0)

    # Beat intervals (start,end) per SV interval
    beat_intervals = []
    for i in range(len(beat_points)-1):
        beat_intervals.append((beat_points[i][0], beat_points[i+1][0]))
        if len(beat_points) == 1:
            beat_intervals = [(beat_points[0][0], beat_points[0][0] + 1)]

    # aggregate SC data and calculate average
    def aggregate_spectral_centroid(points, start, end):
        vals = [v for f, v, _ in points if v is not None and start <= f < end]
        if not vals:
            return None
        return float(np.mean(vals))
    
    # aggregate power data and a) calculate average or b) determine the closest value 100ms after marking    
    def determine_dynamics(points, start, end, use_average):
        vals = [v for f, v, _ in points if v is not None and start <= f < end]

        if not vals:
            return None, None

        if use_average:
            lin_vals = [10**(v/10) for v in vals]
            num_val = 10 * np.log10(np.mean(lin_vals))
        else:
            _, num_val, _ = min(
                points,
                key=lambda p: abs(p[0] - (start + 4410))
            )

        dyn_levels = ['ppp','pp','p','mp','mf','f','ff','fff']
        mf_index = dyn_levels.index('mf')

        level_values = {
            lvl: mf_db + (i - mf_index) * step_db
            for i, lvl in enumerate(dyn_levels)
        }

        if num_val < level_values['ppp'] or num_val > level_values['fff']:
            return str(num_val), "extreme"

        closest_lvl, closest_val = min(
            level_values.items(),
            key=lambda x: abs(num_val - x[1])
        )

        diff = int(round(num_val - closest_val))

        label = (
            closest_lvl if diff == 0
            else f"{closest_lvl}{'+' if diff > 0 else '-'}{abs(diff)}"
        )

        return str(np.round(num_val*100)/100), label    
    
    # Helper: create/get child (preserves existing children if present)
    def get_or_create_measure_child(parent, tag, tstamp):
        child = parent.find(f"./mei:{tag}[@tstamp.ges='{tstamp}']", namespaces=ns)
        if child is None:
            child = etree.SubElement(parent, f"{{{ns['mei']}}}{tag}", **{'tstamp.ges': str(tstamp)})
        return child

    # Build timeline mapping: list of (interval_idx, measure_idx, tstamp)
    # interval_idx indexes beat_intervals/tempos/beat_points
    # measure_idx is index into measures list (0-based). measure 0 is pickup if pickup=True
    timeline = []

    total_intervals = len(beat_intervals)
    interval_start_idx = 0
    if pickup:
        if total_intervals < 1:
            raise ValueError("Not enough intervals for pickup handling.")
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
        if measure_idx >= num_measures:
            continue
        timeline.append({
            "interval_idx": interval_idx,
            "measure_idx": measure_idx,
            "tstamp": beat_tstamps[beat_pos]
        })

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

        # If this entry is the pickup (measure 0 when pickup=True), populate therein only the last beat's spectral + dynamics; tempos should stay empty string
        if pickup and measure_idx == 0:
            # Spectral
            val = aggregate_spectral_centroid(spectral_points, start, end) if spectral_points else None
            annot_el = get_or_create_measure_child(add_el, "annot", tstamp_str)
            annot_el.set("label", "spectral centroid (Hz)")
            annot_el.set("n", f"{val:.2f}" if val is not None else "")
            annot_el.set("type", "performed")

            # Dynamics
            vals = determine_dynamics(power_points, start, end, dyn_method) if power_points else None
            dynam_el = get_or_create_measure_child(add_el, "dynam", tstamp_str)
            dynam_el.set("n", vals[0])
            dynam_el.set("label", vals[1])
            dynam_el.set("type", "performed")

            tempo_el = get_or_create_measure_child(add_el, "tempo", tstamp_str)
            tempo_el.set("mm", "")
            tempo_el.set("type", "performed")

            continue

        # Normal entries: fill tempo, spectral, dynamics

        tempo_val = tempos[interval_idx] if interval_idx < len(tempos) else None
        tempo_el = get_or_create_measure_child(add_el, "tempo", tstamp_str)
        tempo_el.set("mm", f"{tempo_val:.2f}" if tempo_val is not None else "")
        tempo_el.set("type", "performed")

        # Spectral
        val = aggregate_spectral_centroid(spectral_points, start, end) if spectral_points else None
        annot_el = get_or_create_measure_child(add_el, "annot", tstamp_str)
        annot_el.set("label", "spectral centroid (Hz)")
        annot_el.set("n", f"{val:.2f}" if val is not None else "")
        annot_el.set("type", "performed")

        # Dynamics
        vals = determine_dynamics(power_points, start, end, dyn_method) if power_points else None
        dynam_el = get_or_create_measure_child(add_el, "dynam", tstamp_str)
        dynam_el.set("n", vals[0])
        dynam_el.set("label", vals[1])
        dynam_el.set("type", "performed")

    # Beat count consistency warnings

    # Helper: count truly populated beats in a measure
    def count_populated_beats(measure):
        add_el = measure.find('mei:add', namespaces=ns)
        if add_el is None:
            return 0
        populated = 0
        for tempo in add_el.findall('mei:tempo', namespaces=ns):
            if tempo.get('mm', '').strip() != '':
                populated += 1
        return populated

    last_measure_idx = num_measures - 1
    last_measure = measures[last_measure_idx]
    beats_in_last_measure = count_populated_beats(last_measure)

    if beats_in_last_measure == beats_per_measure:
        last_inserted_interval = timeline[-1]["interval_idx"] if timeline else -1
        extra_sv_intervals = max(0, len(beat_intervals) - (last_inserted_interval + 1))
        if extra_sv_intervals > 0:
            warnings.append(
                f"{extra_sv_intervals} SV interval{'s' if extra_sv_intervals>1 else ''} could not be inserted into MEI."
            )
    else:
        empty_mei_beats = 0
        for m_idx in range(last_measure_idx, -1, -1):
            m = measures[m_idx]
            num_pop = count_populated_beats(m)
            empty_in_measure = beats_per_measure - num_pop
            empty_mei_beats += empty_in_measure
            if num_pop > 0:
                break

        if empty_mei_beats > 0:
            warnings.append(
                f"Your SV data leaves {empty_mei_beats} MEI beat{'s' if empty_mei_beats>1 else ''} empty at the end of the file."
            )

    preview_measures = [
        etree.tostring(
            deepcopy(m), 
            pretty_print=True,
            encoding=str
        )
        for m in measures[:5] + measures[-5:]
    ]

    modified_bytes = etree.tostring(mei_root, pretty_print=True, encoding='UTF-8')
    return modified_bytes, preview_measures, warnings
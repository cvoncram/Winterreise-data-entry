from lxml import etree
from typing import List, Dict, Tuple, Optional
import numpy as np
from backend.services.sv_parser import find_datasets, extract_points
from copy import deepcopy

def generate_layer_previews(sv_tree, max_points: int = 5) -> Tuple[Dict[str, str], Dict[str, Optional[str]]]:
    """
    Returns short XML previews for beat/spectral/power layers
    (model + dataset + first N <point> elements), 
    and detected dataset ids.
    """
    datasets = find_datasets(sv_tree)
    previews: Dict[str, str] = {}
    detected_layers: Dict[str, Optional[str]] = {}

    def preview_layer(layer: Dict) -> str:
        lines = []

        model_el = layer.get("model")
        if model_el is not None:
            model_txt = etree.tostring(model_el, pretty_print=True, encoding=str).strip()
            lines.append(model_txt)

        dataset_el = layer["element"]

        # first line of dataset opening tag
        dataset_open = etree.tostring(dataset_el, pretty_print=True, encoding=str).splitlines()[0]
        lines.append(dataset_open)

        # collect point text
        all_points = dataset_el.findall(".//point")
        for p in all_points[:max_points]:
            p_txt = etree.tostring(p, pretty_print=True, encoding=str).strip()
            lines.append("  " + p_txt)  # <-- indent

        # add "more" marker if needed
        if len(all_points) > max_points:
            lines.append("  <!-- ...more points... -->")

        # dataset closing tag
        lines.append("</dataset>")

        # no empty lines added here
        return "\n".join(lines)

    # Layer selection rules
    layer_specs = [
        ("beat", lambda d: d.get("dimensions") == "1" or (d.get("model_name") or "") == ""),
        ("spectral", lambda d: "spectral" in (d.get("model_name") or "").lower()),
        ("power", lambda d: "power" in (d.get("model_name") or "").lower())
    ]

    for name, rule in layer_specs:
        layer = next((d for d in datasets.values() if rule(d)), None)
        if layer:
            model_el = next(
                (m for m in sv_tree.findall(".//model") if m.get("dataset") == layer["element"].get("id")),
                None
            )
            layer["model"] = model_el
            previews[name] = preview_layer(layer)
            detected_layers[name] = layer["element"].get("id")
        else:
            previews[name] = "(not found)"
            detected_layers[name] = None

    return previews, detected_layers


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

    # -----------------------
    # Determine beats per measure from first measure
    # -----------------------
    first_measure = measures[0]
    first_add = first_measure.find('mei:add', namespaces=ns)
    if first_add is None:
        first_add = etree.SubElement(first_measure, f"{{{ns['mei']}}}add")

    # Get all tempo tstamp.ges values as beats
    beat_tstamps = [int(e.get('tstamp.ges')) for e in first_add.findall('mei:tempo', namespaces=ns)]
    if not beat_tstamps:
        # Fallback: use 1..N evenly spaced beats
        num_measures = len(measures)
        beats_per_measure = len(beat_points) // num_measures
        beat_tstamps = list(range(1, beats_per_measure+1))
    beats_per_measure = len(beat_tstamps)

    # -----------------------
    # Tempos
    # -----------------------
    tempos = []
    for i in range(len(beat_points)-1):
        delta_sec = (beat_points[i+1][0] - beat_points[i][0]) / sample_rate
        tempos.append(60.0 / delta_sec if delta_sec > 0 else 0.0)
    tempos.append(tempos[-1] if tempos else 0.0)

    # -----------------------
    # Beat intervals
    # -----------------------
    beat_intervals = []
    for i in range(len(beat_points)):
        if i < len(beat_points)-1:
            beat_intervals.append((beat_points[i][0], beat_points[i+1][0]))
        elif i > 0:
            prev_start, prev_end = beat_intervals[-1]
            interval_len = prev_end - prev_start
            beat_intervals.append((beat_points[i][0], beat_points[i][0] + interval_len))
        else:
            beat_intervals.append((beat_points[i][0], beat_points[i][0]+1))

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
    # Helper: create/get child
    # -----------------------
    def get_or_create_measure_child(parent, tag, tstamp):
        child = parent.find(f"./mei:{tag}[@tstamp.ges='{tstamp}']", namespaces=ns)
        if child is None:
            child = etree.SubElement(parent, f"{{{ns['mei']}}}{tag}", **{'tstamp.ges': tstamp})
        return child

    # -----------------------
    # Process each measure
    # -----------------------
    for m_idx, measure in enumerate(measures):
        add_el = measure.find('mei:add', namespaces=ns)
        if add_el is None:
            add_el = etree.SubElement(measure, f"{{{ns['mei']}}}add")

        # --- PICKUP logic only for first measure ---
        if pickup and m_idx == 0:
            last_idx = beats_per_measure - 1
            if last_idx < len(beat_intervals):
                start, end = beat_intervals[last_idx]
                tstamp_str = str(beat_tstamps[last_idx])

                # Spectral
                if spectral_points:
                    val = aggregate(spectral_points, start, end, mode='mean')
                    if val is not None:
                        annot_el = get_or_create_measure_child(add_el, "annot", tstamp_str)
                        annot_el.set("label", "spectral centroid (Hz)")
                        annot_el.set("n", f"{val:.2f}")
                        annot_el.set("type", "performed")

                # Dynamics
                if power_points:
                    vals = [v for f, v, _ in power_points if v is not None and start <= f < end]
                    if vals:
                        lin_vals = [10**(v/20) for v in vals]
                        rms_lin = np.sqrt(np.mean(np.square(lin_vals)))
                        val_db = 20 * np.log10(rms_lin)

                        dyn_levels = ['ppp','pp','p','mp','mf','f','ff','fff']
                        mf_index = dyn_levels.index('mf')
                        level_values = {lvl: mf_db + (i - mf_index) * step_db 
                                        for i, lvl in enumerate(dyn_levels)}
                        if val_db < level_values['ppp'] or val_db > level_values['fff']:
                            n_val = "extreme"
                        else:
                            closest_lvl, closest_val = min(
                                level_values.items(), key=lambda x: abs(val_db - x[1])
                            )
                            diff = int(round(val_db - closest_val))
                            if diff == 0:
                                n_val = closest_lvl
                            else:
                                sign = "+" if diff > 0 else "-"
                                n_val = f"{closest_lvl}{sign}{abs(diff)}"

                        dynam_el = get_or_create_measure_child(add_el, "dynam", tstamp_str)
                        dynam_el.set("n", n_val)
                        dynam_el.set("type", "performed")

            # Fill empty tempos for all beats
            for tstamp in beat_tstamps:
                tempo_el = get_or_create_measure_child(add_el, "tempo", str(tstamp))
                tempo_el.set("mm", "")
                tempo_el.set("type", "performed")

            continue  # skip normal beat processing for pickup measure

        # --- NORMAL measures ---
        for b_idx, tstamp in enumerate(beat_tstamps):
            idx = m_idx * beats_per_measure + b_idx
            if idx >= len(beat_points):
                continue
            start, end = beat_intervals[idx]
            tstamp_str = str(tstamp)

            # Tempo
            tempo_val = tempos[idx]
            tempo_el = get_or_create_measure_child(add_el, "tempo", tstamp_str)
            tempo_el.set("mm", f"{tempo_val:.2f}")
            tempo_el.set("type", "performed")

            # Spectral
            if spectral_points:
                val = aggregate(spectral_points, start, end, mode='mean')
                if val is not None:
                    annot_el = get_or_create_measure_child(add_el, "annot", tstamp_str)
                    annot_el.set("label", "spectral centroid (Hz)")
                    annot_el.set("n", f"{val:.2f}")
                    annot_el.set("type", "performed")

            # Dynamics
            if power_points:
                vals = [v for f,v,_ in power_points if v is not None and start <= f < end]
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
                        if diff == 0:
                            n_val = closest_lvl
                        else:
                            sign = "+" if diff > 0 else "-"
                            n_val = f"{closest_lvl}{sign}{abs(diff)}"

                    dynam_el = get_or_create_measure_child(add_el, "dynam", tstamp_str)
                    dynam_el.set("n", n_val)
                    dynam_el.set("type", "performed")

    # -----------------------
    # Preview (strip xmlns for display)
    # -----------------------
    def strip_ns(elem):
        for e in elem.iter():
            if isinstance(e.tag, str) and '}' in e.tag:
                e.tag = e.tag.split('}', 1)[1]
        for attr in list(elem.attrib):
            if attr.startswith("{"):
                elem.attrib.pop(attr)
        if 'xmlns' in elem.attrib:
            elem.attrib.pop('xmlns')
        return elem

    preview_measures = [
        etree.tostring(strip_ns(deepcopy(m)), pretty_print=True, encoding=str)
        for m in measures[:10] + measures[-10:]
    ]

    modified_bytes = etree.tostring(mei_root, pretty_print=True, encoding='UTF-8')
    return modified_bytes, preview_measures, warnings

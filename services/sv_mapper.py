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
    power_layer_name: Optional[str] = None
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
    # Find datasets from SV
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
    # Find <measure> elements (namespace-aware)
    # -----------------------
    measures = mei_root.findall('.//mei:measure', namespaces=ns)
    if not measures:
        raise ValueError("MEI file contains no <measure> elements.")

    # -----------------------
    # Beat mapping calculations
    # -----------------------
    num_measures = len(measures)
    num_beats = len(beat_points)
    beats_per_measure = num_beats / num_measures if num_measures else 0
    if beats_per_measure == 0:
        raise ValueError("Division by zero: no beats found.")
    if not beats_per_measure.is_integer():
        warnings.append(f"{num_beats} beats across {num_measures} measures (non-integer)")
    beats_per_measure = int(beats_per_measure)

    tempos = [60.0 / ((beat_points[i][0] - beat_points[i-1][0]) / sample_rate) if i>0 else 0.0 for i in range(len(beat_points))]
    beat_intervals = [(beat_points[i][0], beat_points[i+1][0] if i+1<len(beat_points) else beat_points[i][0]+1) for i in range(len(beat_points))]

    def aggregate(points, start, end, mode='mean'):
        vals = [v for f,v,_ in points if v is not None and start <= f < end]
        if not vals:
            return None
        if mode=='mean':
            return float(np.mean(vals))
        elif mode=='rms':
            return float(np.sqrt(np.mean(np.square(vals))))
        return None

    # -----------------------
    # Add annotations to MEI
    # -----------------------
    for m_idx, measure in enumerate(measures):
        add_el = measure.find('mei:add', namespaces=ns)
        if add_el is None:
            add_el = etree.SubElement(measure, f"{{{ns['mei']}}}add")
        for b in range(beats_per_measure):
            idx = m_idx * beats_per_measure + b
            if idx >= len(beat_points):
                continue
            start, end = beat_intervals[idx]
            tstamp = str(b+1)

            etree.SubElement(add_el, f"{{{ns['mei']}}}tempo", **{'tstamp.ges': tstamp}, type='performed', mm=str(int(tempos[idx])))

            if spectral_points:
                val = aggregate(spectral_points, start, end, mode='mean')
                if val is not None:
                    etree.SubElement(add_el, f"{{{ns['mei']}}}annot", **{'tstamp.ges': tstamp}, label='spectral centroid (Hz)', n=f"{val:.2f}", type='performed')

            if power_points:
                val = aggregate(power_points, start, end, mode='rms')
                if val is not None:
                    step = round((val-mf_db)/step_db)
                    n_val = f"mf{step:+}" if step!=0 else "mf"
                    etree.SubElement(add_el, f"{{{ns['mei']}}}dynam", **{'tstamp.ges': tstamp}, n=n_val, type='performed')

    # -----------------------
    # Build preview measures (namespace-stripped for display)
    # -----------------------
    def strip_ns(elem):
        """Strip namespaces for preview only."""
        for e in elem.iter():
            if isinstance(e.tag, str) and '}' in e.tag:
                e.tag = e.tag.split('}', 1)[1]
        return elem

    preview_measures = [
        etree.tostring(strip_ns(deepcopy(m)), pretty_print=True, encoding=str)
        for m in measures[:10] + measures[-10:]
    ]

    modified_bytes = etree.tostring(mei_root, pretty_print=True, encoding='UTF-8')
    return modified_bytes, preview_measures, warnings

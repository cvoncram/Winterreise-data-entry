from copy import deepcopy
from typing import Dict, Optional, Tuple
from lxml import etree

from services.sv_parser import find_datasets

def extract_preview_measures(mei_bytes: bytes, first: int = 5, last: int = 5):
    parser = etree.XMLParser(remove_blank_text=True)
    mei_root = etree.fromstring(mei_bytes, parser)

    measures = mei_root.xpath(
        "//*[local-name()='body']//*[local-name()='measure']"
    )

    print("DEBUG found measures:", len(measures))

    if not measures:
        return ["(No measures found)"]

    if len(measures) > first + last:
        selected = measures[:first] + measures[-last:]
    else:
        selected = measures

    preview = [
        etree.tostring(deepcopy(m), pretty_print=True, encoding="unicode")
        for m in selected
    ]

    return preview

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

        dataset_open = etree.tostring(dataset_el, pretty_print=True, encoding=str).splitlines()[0]
        lines.append(dataset_open)

        all_points = dataset_el.findall(".//point")
        for p in all_points[:max_points]:
            p_txt = etree.tostring(p, pretty_print=True, encoding=str).strip()
            lines.append("  " + p_txt)  # <-- indent

        if len(all_points) > max_points:
            lines.append("  <!-- ...more points... -->")

        lines.append("</dataset>")

        return "\n".join(lines)

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
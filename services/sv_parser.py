from lxml import etree
from typing import Dict, Any, List, Tuple, Optional

def parse_sv_bytes(sv_bytes: bytes):
    """Parse bytes of a .sv file, decompress if bzip2, return XML root."""
    import bz2
    try:
        if sv_bytes[:3] == b"BZh":
            sv_bytes = bz2.decompress(sv_bytes)
    except Exception:
        pass

    parser = etree.XMLParser(resolve_entities=False, no_network=True)
    root = etree.fromstring(sv_bytes, parser=parser)
    return root

def find_datasets(root) -> Dict[str, Dict[str, Any]]:
    """Return a mapping dataset_id -> { element, points, units, dimensions }"""
    datasets = {}

    # map model -> dataset
    model_map = {}
    for m in root.findall('.//model'):
        mid = m.get('id')
        ds = m.get('dataset')
        model_map[mid] = {
            'dataset': ds,
            'name': m.get('name'),
            'units': m.get('units'),
            'type': m.get('type'),
            'dimensions': m.get('dimensions')
        }

    # iterate datasets correctly
    for d in root.findall('.//dataset'):
        did = d.get('id')
        points = d.findall('.//point')
        datasets[did] = {
            'element': d,
            'num_points': len(points),
            'points': points,
            'units': None,
            'dimensions': None,
        }

    # augment with model metadata
    for mid, meta in model_map.items():
        ds = meta.get('dataset')
        if ds and ds in datasets:
            datasets[ds]['units'] = meta.get('units')
            datasets[ds]['dimensions'] = meta.get('dimensions')
            datasets[ds]['model_name'] = meta.get('name')

    return datasets


def extract_points(dataset_el) -> List[Tuple[int, Optional[float], Optional[str]]]:
    """From a dataset element, return list of (frame:int, value:float or None, label:str or None)"""
    pts = []
    for p in dataset_el.findall('.//point'):
        frame = p.get('frame')
        if frame is None:
            continue
        frame = int(frame)
        value = p.get('value')
        label = p.get('label')
        val = None
        if value is not None and value != "":
            try:
                val = float(value)
            except Exception:
                val = None
        pts.append((frame, val, label))
    return pts
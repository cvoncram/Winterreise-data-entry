import pandas as pd
from lxml import etree
from io import BytesIO
from backend.dependencies import read_csv_upload

NS = {"mei": "http://www.music-encoding.org/ns/mei"}

def local_name(tag):
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag

def get_measures(root):
    return root.xpath(".//mei:measure", namespaces=NS)

def find_measure(root, n):
    matches = root.xpath(f".//mei:measure[@n='{n}']", namespaces=NS)
    return matches[0] if matches else None

def get_or_create_add(measure):
    for child in measure:
        if local_name(child.tag) == "add":
            return child
    add = etree.Element("{http://www.music-encoding.org/ns/mei}add")
    measure.insert(0, add)
    return add

def find_elem(add, tag, tstamp):
    for child in add:
        if local_name(child.tag) == tag and child.get("tstamp.ges") == str(tstamp):
            return child
    return None

def insert_into_mei(mei_bytes, csv_bytes,
                    tempo_col, dynam_col, annot_col,
                    output_path):

    tree = etree.parse(BytesIO(mei_bytes))
    root = tree.getroot()
    df = read_csv_upload(csv_bytes)

    mb_col = next((c for c in df.columns if c.lower() in ("measure.beat","measure_beat","measure.beats")), None)
    if mb_col is None:
        raise ValueError("CSV missing measure.beat")

    for _, row in df.iterrows():
        mb = str(row[mb_col]).strip()
        measure_part, beat_part = (mb.split(".",1) + ["1"])[:2]

        m_el = find_measure(root, measure_part)
        if m_el is None:
            continue

        add = get_or_create_add(m_el)

        if tempo_col and tempo_col in df.columns and pd.notna(row[tempo_col]):
            el = find_elem(add, "tempo", beat_part)
            if el is None:
                el = etree.Element("{http://www.music-encoding.org/ns/mei}tempo")
                el.set("tstamp.ges", beat_part)
                add.append(el)
            el.set("mm", str(row[tempo_col]))
            el.set("type","performed")

        if dynam_col and dynam_col in df.columns and pd.notna(row[dynam_col]):
            el = find_elem(add, "dynam", beat_part)
            if el is None:
                el = etree.Element("{http://www.music-encoding.org/ns/mei}dynam")
                el.set("tstamp.ges", beat_part)
                add.append(el)
            el.set("n", str(row[dynam_col]))
            el.set("type","performed")

        if annot_col and annot_col in df.columns and pd.notna(row[annot_col]):
            el = find_elem(add, "annot", beat_part)
            if el is None:
                el = etree.Element("{http://www.music-encoding.org/ns/mei}annot")
                el.set("tstamp.ges", beat_part)
                add.append(el)
            el.set("n", str(row[annot_col]))
            el.set("label", "spectral centroid")
            el.set("type","performed")

    tree.write(output_path, encoding="utf-8", xml_declaration=True, pretty_print=True)

    # Return first 10 + last 10 measures as strings, stripping xmlns for preview
    measures = get_measures(root)
    preview_measures = []
    for m in (measures[:10] + measures[-10:]):
        m_copy = etree.tostring(m, encoding="unicode", pretty_print=True)
        # Remove the xmlns declaration for a cleaner preview
        m_copy = m_copy.replace(' xmlns="http://www.music-encoding.org/ns/mei"', '')
        preview_measures.append(m_copy)

    return preview_measures

import pandas as pd
from lxml import etree
from io import BytesIO

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
                    tempo_col, dynam_col, annot_col, annot_label,
                    output_path):

    tree = etree.parse(BytesIO(mei_bytes))
    root = tree.getroot()

    df = pd.read_csv(BytesIO(csv_bytes))

    mb_col = None
    for c in df.columns:
        if c.lower() in ("measure.beat", "measure_beat", "measure.beats"):
            mb_col = c
            break
    if mb_col is None:
        raise ValueError("CSV missing measure.beat")

    for _, row in df.iterrows():

        mb = str(row[mb_col]).strip()
        if "." in mb:
            measure_part, beat_part = mb.split(".", 1)
        else:
            measure_part = mb
            beat_part = "1"

        m_el = find_measure(root, measure_part)
        if m_el is None:
            continue

        add = get_or_create_add(m_el)

        # tempo
        if tempo_col and tempo_col in df.columns:
            val = row[tempo_col]
            if pd.notna(val):
                el = find_elem(add, "tempo", beat_part)
                if el is None:
                    el = etree.Element("{http://www.music-encoding.org/ns/mei}tempo")
                    el.set("tstamp.ges", beat_part)
                    add.append(el)
                el.set("mm", str(val))
                el.set("type", "performed")

        # dynam
        if dynam_col and dynam_col in df.columns:
            val = row[dynam_col]
            if pd.notna(val):
                el = find_elem(add, "dynam", beat_part)
                if el is None:
                    el = etree.Element("{http://www.music-encoding.org/ns/mei}dynam")
                    el.set("tstamp.ges", beat_part)
                    add.append(el)
                el.set("n", str(val))
                el.set("type", "performed")

        # annot
        if annot_col and annot_col in df.columns:
            val = row[annot_col]
            if pd.notna(val):
                el = find_elem(add, "annot", beat_part)
                if el is None:
                    el = etree.Element("{http://www.music-encoding.org/ns/mei}annot")
                    el.set("tstamp.ges", beat_part)
                    add.append(el)
                el.set("n", str(val))
                if annot_label:
                    el.set("label", annot_label)
                el.set("type", "performed")

    tree.write(output_path, encoding="utf-8", xml_declaration=True, pretty_print=True)


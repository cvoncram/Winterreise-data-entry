from copy import deepcopy
from lxml import etree
from typing import List

def extract_preview_measures(mei_bytes: bytes, first: int = 5, last: int = 5):
    parser = etree.XMLParser(remove_blank_text=True)
    mei_root = etree.fromstring(mei_bytes, parser)

    # ALWAYS find measures regardless of namespace
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

"""Build a winter-only YML feed using Python's standard library."""
import argparse
import json
import os
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

SOURCE_URL = "https://static.autorus.ru/feeds/arus_linglong.xml"
NON_WINTER = re.compile(r"\b(?:лет\w*|всесез\w*|summer|all[\s-]*season|4s)\b", re.I)
WINTER = re.compile(r"\b(?:winter|зим\w*|(?:не)?шип\w*)\b", re.I)


def season(name):
    if NON_WINTER.search(name):
        return "other"
    if WINTER.search(name):
        return "winter"
    raise ValueError(f"Cannot determine tyre season: {name!r}")


def filter_feed(source):
    # The standard YML external declaration is harmless: ElementTree never
    # downloads shops.dtd. Reject other DTDs and internal entity declarations.
    standard_dtd = b'<!DOCTYPE yml_catalog SYSTEM "shops.dtd">'
    without_dtd = source.replace(standard_dtd, b'')
    if re.search(br"<!\s*(?:DOCTYPE|ENTITY)\b", without_dtd, re.I):
        raise ValueError("Unexpected XML DTD/entity declaration")
    root = ET.fromstring(source)
    offers_node = root.find("./shop/offers")
    if root.tag != "yml_catalog" or offers_node is None:
        raise ValueError("Expected a YML catalog with shop/offers")
    offers = list(offers_node)
    if not offers or any(o.tag != "offer" for o in offers):
        raise ValueError("Missing or unexpected offers")
    ids = [o.get("id") for o in offers]
    if any(not oid for oid in ids) or len(ids) != len(set(ids)):
        raise ValueError("Missing or duplicate offer IDs")
    categories = {c.get("id") for c in root.findall("./shop/categories/category")}
    kept = []
    for offer in offers:
        vendor = re.sub(r"\s+", "", offer.findtext("vendor", "")).casefold()
        if vendor != "linglong":
            raise ValueError(f"Unexpected vendor in offer {offer.get('id')}")
        if season(offer.findtext("name", "")) != "winter":
            offers_node.remove(offer)
            continue
        if offer.findtext("categoryId") not in categories:
            raise ValueError(f"Unknown category in offer {offer.get('id')}")
        kept.append(offer.get("id"))
    if not kept:
        raise ValueError("No winter tyres found; refusing to publish an empty feed")
    result = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if standard_dtd in source:
        declaration, body = result.split(b'\n', 1)
        result = declaration + b'\n' + standard_dtd + b'\n' + body
    ET.fromstring(result)  # Validate output before writing it.
    return result, {"source_offers": len(offers), "winter_offers": len(kept),
                    "excluded_offers": len(offers) - len(kept)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Optional local source XML")
    parser.add_argument("--output", type=Path, default=Path("feed_winter.xml"))
    args = parser.parse_args()
    if args.input:
        source = args.input.read_bytes()
    else:
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "AutorusLinglongWinterFeed/1.0"})
        with urllib.request.urlopen(request, timeout=90) as response:
            source = response.read(20_000_001)
        if len(source) > 20_000_000:
            raise ValueError("Source feed exceeds 20 MB")
    result, report = filter_feed(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".xml.tmp")
    temporary.write_bytes(result)
    os.replace(temporary, args.output)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

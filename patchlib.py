"""Byte-preserving subset of the MTK schema-3 structural patch operations.

Source preparation only: this module has not been executed on target scripts.
"""
from __future__ import annotations


def decode(data: bytes):
    crlf = data.count(b"\r\n")
    if crlf and data.count(b"\n") != crlf:
        raise ValueError("Mixed line endings; refusing to normalize foreign content")
    eol = b"\r\n" if crlf else b"\n"
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r" in normalized:
        raise ValueError("CR-only line endings are unsupported")
    return normalized.decode("utf-8", errors="surrogateescape").split("\n"), eol


def encode(lines, eol):
    return "\n".join(lines).encode("utf-8", errors="surrogateescape").replace(b"\n", eol)


def matches(lines, sequence):
    if not sequence:
        raise ValueError("Empty structural anchor")
    return [i for i in range(len(lines) - len(sequence) + 1) if lines[i:i + len(sequence)] == sequence]


def migrate(lines, payload, uninstall):
    begin, end = payload["beginMarker"], payload["endMarker"]
    current = [begin] + payload["contentLines"] + [end]
    legacy = payload["legacyBlocks"]
    anchors = matches(lines, payload["anchorLines"])
    if len(anchors) != 1:
        raise ValueError(payload["name"] + ": missing/ambiguous anchor")
    starts, ends = matches(lines, [begin]), matches(lines, [end])
    position = payload["position"]
    if position not in ("before", "after"):
        raise ValueError("Invalid marked-block position")
    if not starts and not ends:
        if uninstall:
            return
        at = anchors[0] + (len(payload["anchorLines"]) if position == "after" else 0)
        lines[at:at] = current
        return
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError(payload["name"] + ": duplicate/partial block")
    if (position == "after" and starts[0] < anchors[0] + len(payload["anchorLines"])) or \
       (position == "before" and ends[0] >= anchors[0]):
        raise ValueError(payload["name"] + ": misplaced block")
    installed = lines[starts[0]:ends[0] + 1]
    if installed != current and installed not in legacy:
        raise ValueError(payload["name"] + ": modified/unknown installed block")
    lines[starts[0]:ends[0] + 1] = [] if uninstall else current


def replace(lines, payload, uninstall):
    replacements = payload["replacements"]
    if uninstall:
        replacements = list(reversed(replacements))
    for item in replacements:
        old, new = item["oldLines"], item["newLines"]
        a, b = matches(lines, old), matches(lines, new)
        legacy = [(i, block) for block in item.get("legacyNewLines", []) for i in matches(lines, block)]
        contained = len(b) == 1 and all(b[0] <= i and i + len(old) <= b[0] + len(new) for i in a)
        if contained and not legacy:
            if uninstall:
                lines[b[0]:b[0] + len(new)] = old
        elif len(a) == 1 and not b and not legacy:
            if not uninstall:
                lines[a[0]:a[0] + len(old)] = new
        elif not a and not b and len(legacy) == 1:
            i, block = legacy[0]
            lines[i:i + len(block)] = old if uninstall else new
        else:
            raise ValueError(item["name"] + ": ambiguous/modified replacement")


def apply(data: bytes, payload: dict, uninstall=False) -> bytes:
    lines, eol = decode(data)
    if payload["format"] == "migrate-marked-block-v1":
        migrate(lines, payload, uninstall)
    elif payload["format"] == "exact-text-replacements-v1":
        replace(lines, payload, uninstall)
    else:
        raise ValueError("Unsupported structural operation")
    return encode(lines, eol)

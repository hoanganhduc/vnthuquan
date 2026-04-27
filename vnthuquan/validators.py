"""File validators for downloaded assets."""

from __future__ import annotations

import hashlib
import html
import os
import re
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import ValidationResult

EPUB_MIMETYPE = "application/epub+zip"
DEMO_MARKER_RE = re.compile(
    r"(demo|sample|preview|trich doan|trích đoạn|xem thu|xem thử)",
    re.IGNORECASE,
)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(zf.read(name))


def validate_epub(path: str | Path, expected_size: int | None = None) -> ValidationResult:
    """Validate EPUB transfer and package structure."""

    epub_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    size = epub_path.stat().st_size if epub_path.exists() else None
    digest = sha256_file(epub_path) if epub_path.exists() else None
    transfer_complete = None if expected_size is None else size == expected_size
    if expected_size is not None and size != expected_size:
        errors.append(f"byte count mismatch: expected {expected_size}, got {size}")

    file_type_valid = False
    container_valid = False
    content_readable = False
    demo_suspected: bool | None = None
    metadata_title = None
    metadata_creator = None
    manifest_items = 0
    spine_items_count = 0
    toc_items = 0
    nav_items = 0
    spine_text_chars = 0

    try:
        with zipfile.ZipFile(epub_path) as zf:
            bad_member = zf.testzip()
            if bad_member:
                errors.append(f"ZIP integrity failed at {bad_member}")
            names = set(zf.namelist())
            if "mimetype" not in names:
                errors.append("missing mimetype")
            else:
                mimetype = zf.read("mimetype").decode("utf-8", errors="replace").strip()
                file_type_valid = mimetype == EPUB_MIMETYPE
                if not file_type_valid:
                    errors.append(f"unexpected EPUB mimetype: {mimetype}")

            if "META-INF/container.xml" not in names:
                errors.append("missing META-INF/container.xml")
            else:
                container = _read_xml(zf, "META-INF/container.xml")
                ns_container = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
                rootfile = container.find(".//c:rootfile", ns_container)
                opf_path = rootfile.attrib.get("full-path") if rootfile is not None else None
                if not opf_path:
                    errors.append("container.xml has no rootfile")
                elif opf_path not in names:
                    errors.append(f"OPF package not found: {opf_path}")
                else:
                    container_valid = True
                    opf_dir = os.path.dirname(opf_path)
                    opf = _read_xml(zf, opf_path)
                    ns_opf = {
                        "opf": "http://www.idpf.org/2007/opf",
                        "dc": "http://purl.org/dc/elements/1.1/",
                    }
                    title_elem = opf.find(".//dc:title", ns_opf)
                    creator_elem = opf.find(".//dc:creator", ns_opf)
                    metadata_title = title_elem.text if title_elem is not None else None
                    metadata_creator = creator_elem.text if creator_elem is not None else None

                    manifest = {
                        item.attrib.get("id"): item.attrib
                        for item in opf.findall(".//opf:manifest/opf:item", ns_opf)
                    }
                    manifest_items = len(manifest)
                    spine_ids = [
                        item.attrib.get("idref")
                        for item in opf.findall(".//opf:spine/opf:itemref", ns_opf)
                    ]
                    spine_items_count = len(spine_ids)
                    if not spine_ids:
                        errors.append("EPUB spine is empty")

                    missing_manifest_refs: list[str] = []
                    missing_files: list[str] = []
                    demo_hits = 0
                    readable_docs = 0
                    for attrs in manifest.values():
                        if "nav" in attrs.get("properties", ""):
                            nav_items += 1
                        if attrs.get("media-type") == "application/x-dtbncx+xml":
                            toc_items += 1

                    for idref in spine_ids:
                        attrs = manifest.get(idref)
                        if not attrs:
                            missing_manifest_refs.append(str(idref))
                            continue
                        href = attrs.get("href")
                        if not href:
                            missing_manifest_refs.append(str(idref))
                            continue
                        member = os.path.normpath(
                            os.path.join(opf_dir, urllib.parse.unquote(href))
                        ).replace("\\", "/")
                        if member not in names:
                            missing_files.append(member)
                            continue
                        ext = os.path.splitext(member)[1].lower()
                        if ext in {".xhtml", ".html", ".htm"}:
                            data = zf.read(member).decode("utf-8", errors="ignore")
                            text = re.sub(r"<[^>]+>", " ", data)
                            text = html.unescape(re.sub(r"\s+", " ", text)).strip()
                            spine_text_chars += len(text)
                            readable_docs += 1
                            if DEMO_MARKER_RE.search(text[:2000]) or DEMO_MARKER_RE.search(
                                text[-2000:]
                            ):
                                demo_hits += 1

                    if missing_manifest_refs:
                        errors.append(f"spine references missing manifest items: {missing_manifest_refs}")
                    if missing_files:
                        errors.append(f"spine files missing from archive: {missing_files}")
                    if not toc_items and not nav_items:
                        warnings.append("EPUB has no NCX TOC or nav item")
                    content_readable = bool(readable_docs) and not missing_files
                    demo_suspected = bool(demo_hits)
    except zipfile.BadZipFile:
        errors.append("file is not a valid ZIP/EPUB archive")
    except ET.ParseError as exc:
        errors.append(f"invalid EPUB XML: {exc}")
    except OSError as exc:
        errors.append(f"could not read file: {exc}")

    ok = (
        not errors
        and (transfer_complete is not False)
        and file_type_valid
        and container_valid
        and content_readable
    )
    return ValidationResult(
        path=str(epub_path),
        ok=ok,
        transfer_complete=transfer_complete,
        file_type_valid=file_type_valid,
        container_valid=container_valid,
        content_readable=content_readable,
        demo_suspected=demo_suspected,
        content_completeness="unknown",
        sha256=digest,
        size_bytes=size,
        expected_size_bytes=expected_size,
        metadata_title=metadata_title,
        metadata_creator=metadata_creator,
        manifest_items=manifest_items,
        spine_items=spine_items_count,
        toc_items=toc_items,
        nav_items=nav_items,
        spine_text_chars_approx=spine_text_chars,
        warnings=warnings,
        errors=errors,
    )


def validate_file(path: str | Path, format: str = "auto", expected_size: int | None = None) -> ValidationResult:
    """Validate a saved file. MVP supports EPUB."""

    fmt = format.lower()
    if fmt == "auto":
        suffix = Path(path).suffix.lower()
        fmt = "epub" if suffix == ".epub" else suffix.lstrip(".")
    if fmt != "epub":
        return ValidationResult(
            path=str(path),
            ok=False,
            transfer_complete=None,
            file_type_valid=False,
            container_valid=False,
            content_readable=False,
            demo_suspected=None,
            content_completeness="unknown",
            errors=[f"validation for format '{fmt}' is not supported in MVP"],
        )
    return validate_epub(path, expected_size=expected_size)

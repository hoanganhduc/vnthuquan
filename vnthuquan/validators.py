"""File validators for downloaded assets."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import urllib.parse
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import ValidationResult

EPUB_MIMETYPE = "application/epub+zip"
PDF_HEADER = b"%PDF-"
MP3_EXTENSIONS = {".mp3"}
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


def validate_epub(
    path: str | Path, expected_size: int | None = None, strict: bool = False
) -> ValidationResult:
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
                        errors.append(
                            f"spine references missing manifest items: {missing_manifest_refs}"
                        )
                    if missing_files:
                        errors.append(f"spine files missing from archive: {missing_files}")
                    if not toc_items and not nav_items:
                        warnings.append("EPUB has no NCX TOC or nav item")
                        if strict:
                            errors.append("EPUB has no NCX TOC or nav item")
                    content_readable = bool(readable_docs) and not missing_files
                    demo_suspected = bool(demo_hits)
                    if strict and demo_suspected:
                        errors.append("demo/sample markers found in EPUB text")
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


def validate_pdf(
    path: str | Path, expected_size: int | None = None, strict: bool = False
) -> ValidationResult:
    """Validate a PDF transfer with lightweight structural checks."""

    pdf_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    size = pdf_path.stat().st_size if pdf_path.exists() else None
    digest = sha256_file(pdf_path) if pdf_path.exists() else None
    transfer_complete = None if expected_size is None else size == expected_size
    if expected_size is not None and size != expected_size:
        errors.append(f"byte count mismatch: expected {expected_size}, got {size}")

    file_type_valid = False
    container_valid = False
    content_readable = False
    try:
        with pdf_path.open("rb") as handle:
            head = handle.read(1024)
            if not head.startswith(PDF_HEADER):
                errors.append("missing PDF header")
            else:
                file_type_valid = True
            if size and size > 0:
                handle.seek(max(size - 4096, 0))
                tail = handle.read()
            else:
                tail = b""
        container_valid = file_type_valid and b"%%EOF" in tail
        if file_type_valid and not container_valid:
            warnings.append("PDF EOF marker was not found near end of file")
            if strict:
                errors.append("PDF EOF marker was not found near end of file")
        content_readable = file_type_valid and bool(size and size > 1024)
    except OSError as exc:
        errors.append(f"could not read file: {exc}")

    return ValidationResult(
        path=str(pdf_path),
        ok=not errors and (transfer_complete is not False) and file_type_valid and content_readable,
        transfer_complete=transfer_complete,
        file_type_valid=file_type_valid,
        container_valid=container_valid,
        content_readable=content_readable,
        demo_suspected=None,
        content_completeness="unknown",
        sha256=digest,
        size_bytes=size,
        expected_size_bytes=expected_size,
        warnings=warnings,
        errors=errors,
    )


def validate_text(
    path: str | Path, expected_size: int | None = None, strict: bool = False
) -> ValidationResult:
    """Validate a generated UTF-8 text export."""

    text_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    size = text_path.stat().st_size if text_path.exists() else None
    digest = sha256_file(text_path) if text_path.exists() else None
    transfer_complete = None if expected_size is None else size == expected_size
    if expected_size is not None and size != expected_size:
        errors.append(f"byte count mismatch: expected {expected_size}, got {size}")

    text = ""
    try:
        text = text_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"text is not valid UTF-8: {exc}")
    except OSError as exc:
        errors.append(f"could not read file: {exc}")

    stripped = text.strip()
    file_type_valid = bool(stripped) and not errors
    content_readable = len(stripped) >= 200
    if file_type_valid and not content_readable:
        warnings.append("text export is very short")
    if "<html" in stripped[:1000].casefold():
        warnings.append("text export appears to contain HTML markup")
        if strict:
            errors.append("text export appears to contain HTML markup")
    demo_suspected = bool(DEMO_MARKER_RE.search(stripped[:2000])) if stripped else None
    if strict and demo_suspected:
        errors.append("demo/sample markers found in text export")

    return ValidationResult(
        path=str(text_path),
        ok=not errors and (transfer_complete is not False) and file_type_valid and content_readable,
        transfer_complete=transfer_complete,
        file_type_valid=file_type_valid,
        container_valid=file_type_valid,
        content_readable=content_readable,
        demo_suspected=demo_suspected,
        content_completeness="unknown",
        sha256=digest,
        size_bytes=size,
        expected_size_bytes=expected_size,
        spine_text_chars_approx=len(stripped) if stripped else 0,
        warnings=warnings,
        errors=errors,
    )


def _looks_like_mp3(data: bytes) -> bool:
    return data.startswith(b"ID3") or data[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}


def validate_audio(
    path: str | Path, expected_size: int | None = None, strict: bool = False
) -> ValidationResult:
    """Validate a downloaded audio bundle ZIP or a single MP3 file."""

    audio_path = Path(path)
    errors: list[str] = []
    warnings: list[str] = []
    size = audio_path.stat().st_size if audio_path.exists() else None
    digest = sha256_file(audio_path) if audio_path.exists() else None
    transfer_complete = None if expected_size is None else size == expected_size
    if expected_size is not None and size != expected_size:
        errors.append(f"byte count mismatch: expected {expected_size}, got {size}")

    suffix = audio_path.suffix.lower()
    file_type_valid = False
    container_valid = False
    content_readable = False
    manifest_items = 0

    if suffix in MP3_EXTENSIONS:
        try:
            with audio_path.open("rb") as handle:
                head = handle.read(16)
            file_type_valid = _looks_like_mp3(head)
            content_readable = file_type_valid and bool(size and size > 1024)
            container_valid = file_type_valid
            manifest_items = 1 if file_type_valid else 0
            if not file_type_valid:
                errors.append("file does not look like an MP3")
        except OSError as exc:
            errors.append(f"could not read file: {exc}")
    else:
        try:
            with zipfile.ZipFile(audio_path) as zf:
                bad_member = zf.testzip()
                if bad_member:
                    errors.append(f"ZIP integrity failed at {bad_member}")
                names = zf.namelist()
                mp3_names = [name for name in names if Path(name).suffix.lower() == ".mp3"]
                manifest_items = len(mp3_names)
                if not mp3_names:
                    errors.append("audio ZIP contains no MP3 files")
                bad_mp3s = []
                for name in mp3_names:
                    with zf.open(name) as handle:
                        head = handle.read(16)
                    if not _looks_like_mp3(head):
                        bad_mp3s.append(name)
                if bad_mp3s:
                    errors.append(f"audio entries do not look like MP3 files: {bad_mp3s}")
                if strict:
                    if "manifest.json" not in names:
                        errors.append("audio ZIP strict validation requires manifest.json")
                    else:
                        manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
                        manifest_entries = {
                            item.get("entry")
                            for item in manifest.get("assets", [])
                            if isinstance(item, dict) and item.get("entry")
                        }
                        missing_entries = sorted(set(mp3_names) - manifest_entries)
                        extra_entries = sorted(manifest_entries - set(mp3_names))
                        if missing_entries:
                            errors.append(f"audio manifest is missing entries: {missing_entries}")
                        if extra_entries:
                            errors.append(
                                f"audio manifest references missing MP3 files: {extra_entries}"
                            )
                file_type_valid = True
                container_valid = not errors
                content_readable = bool(mp3_names) and not bad_mp3s
        except zipfile.BadZipFile:
            errors.append("file is not a valid ZIP audio bundle")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"audio manifest is not valid JSON: {exc}")
        except OSError as exc:
            errors.append(f"could not read file: {exc}")

    if size == 0:
        errors.append("audio file is empty")
    if suffix not in MP3_EXTENSIONS and suffix != ".zip":
        warnings.append("audio validation expected a .zip bundle or .mp3 file")

    return ValidationResult(
        path=str(audio_path),
        ok=not errors and (transfer_complete is not False) and file_type_valid and content_readable,
        transfer_complete=transfer_complete,
        file_type_valid=file_type_valid,
        container_valid=container_valid,
        content_readable=content_readable,
        demo_suspected=None,
        content_completeness="unknown",
        sha256=digest,
        size_bytes=size,
        expected_size_bytes=expected_size,
        manifest_items=manifest_items,
        warnings=warnings,
        errors=errors,
    )


def validate_file(
    path: str | Path,
    format: str = "auto",
    expected_size: int | None = None,
    strict: bool = False,
) -> ValidationResult:
    """Validate a saved file."""

    fmt = format.lower()
    if fmt == "auto":
        suffix = Path(path).suffix.lower()
        fmt = "audio" if suffix == ".zip" else suffix.lstrip(".")
    if fmt == "epub":
        return validate_epub(path, expected_size=expected_size, strict=strict)
    if fmt == "pdf":
        return validate_pdf(path, expected_size=expected_size, strict=strict)
    if fmt == "text" or fmt == "txt":
        return validate_text(path, expected_size=expected_size, strict=strict)
    if fmt == "audio" or fmt == "mp3":
        return validate_audio(path, expected_size=expected_size, strict=strict)
    return ValidationResult(
        path=str(path),
        ok=False,
        transfer_complete=None,
        file_type_valid=False,
        container_valid=False,
        content_readable=False,
        demo_suspected=None,
        content_completeness="unknown",
        errors=[f"validation for format '{fmt}' is not supported"],
    )

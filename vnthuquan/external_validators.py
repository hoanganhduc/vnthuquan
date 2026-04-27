"""Optional external validation tools."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .models import ExternalValidationResult


def _run_tool(name: str, command: list[str], timeout: float = 120.0) -> ExternalValidationResult:
    executable = shutil.which(command[0])
    if executable is None:
        return ExternalValidationResult(
            name=name,
            command=command,
            ok=False,
            error=f"tool not found: {command[0]}",
        )
    full_command = [executable, *command[1:]]
    try:
        completed = subprocess.run(
            full_command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ExternalValidationResult(
            name=name,
            command=command,
            ok=False,
            error=str(exc),
        )
    return ExternalValidationResult(
        name=name,
        command=command,
        ok=completed.returncode == 0,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def select_external_validators(
    path: str | Path,
    format: str = "auto",
    external: bool = False,
    epubcheck: bool = False,
    ace: bool = False,
) -> list[str]:
    suffix = Path(path).suffix.lower()
    fmt = format.lower()
    if fmt == "auto":
        fmt = "epub" if suffix == ".epub" else suffix.lstrip(".")
    selected: list[str] = []
    if epubcheck or (external and fmt == "epub"):
        selected.append("epubcheck")
    if ace or (external and fmt == "epub"):
        selected.append("ace")
    return list(dict.fromkeys(selected))


def validate_external(
    path: str | Path,
    validators: list[str],
    timeout: float = 120.0,
) -> list[ExternalValidationResult]:
    target = str(Path(path).expanduser())
    results: list[ExternalValidationResult] = []
    for validator in validators:
        name = validator.casefold().strip()
        if name == "epubcheck":
            results.append(_run_tool("epubcheck", ["epubcheck", target], timeout=timeout))
        elif name == "ace":
            results.append(_run_tool("ace", ["ace", target], timeout=timeout))
        else:
            results.append(
                ExternalValidationResult(
                    name=validator,
                    command=[validator, target],
                    ok=False,
                    error=f"unsupported external validator: {validator}",
                )
            )
    return results

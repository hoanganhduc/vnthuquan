"""Configuration loading and persistence."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .mirrors import DEFAULT_MIRROR, normalize_mirror

APP_NAME = "vnthuquan"


@dataclass(slots=True)
class Config:
    default_mirror: str = DEFAULT_MIRROR
    download_dir: str | None = None
    timeout: float = 30.0
    retries: int = 2
    cache_ttl_seconds: float = 0.0
    request_interval_seconds: float = 0.2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base).expanduser() / APP_NAME / "config.json"
    return Path.home() / ".config" / APP_NAME / "config.json"


def load_config(path: str | Path | None = None) -> Config:
    config_path = Path(path).expanduser() if path else default_config_path()
    if not config_path.exists():
        return Config()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Could not read config file {config_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON config file {config_path}: {exc}") from exc

    config = Config(
        default_mirror=normalize_mirror(raw.get("default_mirror") or DEFAULT_MIRROR),
        download_dir=raw.get("download_dir"),
        timeout=float(raw.get("timeout", 30.0)),
        retries=int(raw.get("retries", 2)),
        cache_ttl_seconds=float(raw.get("cache_ttl_seconds", 0.0)),
        request_interval_seconds=float(raw.get("request_interval_seconds", 0.2)),
    )
    return config


def save_config(config: Config, path: str | Path | None = None) -> Path:
    config_path = Path(path).expanduser() if path else default_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(config.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        raise ConfigError(f"Could not write config file {config_path}: {exc}") from exc
    return config_path


def resolve_download_dir(cli_out: str | None, config: Config) -> Path:
    if cli_out:
        value = cli_out
    elif config.download_dir:
        value = config.download_dir
    elif os.environ.get("VNTHUQUAN_DOWNLOAD_DIR"):
        value = os.environ["VNTHUQUAN_DOWNLOAD_DIR"]
    else:
        value = "~/Downloads/vnthuquan"
    return Path(os.path.expandvars(value)).expanduser()


def set_config_value(key: str, value: str, path: str | Path | None = None) -> Config:
    config = load_config(path)
    if key == "default_mirror":
        config.default_mirror = normalize_mirror(value)
    elif key == "download_dir":
        config.download_dir = value
    elif key == "timeout":
        config.timeout = float(value)
    elif key == "retries":
        config.retries = int(value)
    elif key == "cache_ttl_seconds":
        config.cache_ttl_seconds = float(value)
    elif key == "request_interval_seconds":
        config.request_interval_seconds = float(value)
    else:
        raise ConfigError(f"Unsupported config key: {key}")
    save_config(config, path)
    return config


def unset_config_value(key: str, path: str | Path | None = None) -> Config:
    config = load_config(path)
    if key == "default_mirror":
        config.default_mirror = DEFAULT_MIRROR
    elif key == "download_dir":
        config.download_dir = None
    elif key == "timeout":
        config.timeout = 30.0
    elif key == "retries":
        config.retries = 2
    elif key == "cache_ttl_seconds":
        config.cache_ttl_seconds = 0.0
    elif key == "request_interval_seconds":
        config.request_interval_seconds = 0.2
    else:
        raise ConfigError(f"Unsupported config key: {key}")
    save_config(config, path)
    return config

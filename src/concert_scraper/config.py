from __future__ import annotations

from pathlib import Path

import yaml

from concert_scraper.models import AppConfig


def load_config(path: str = "venues.yaml") -> AppConfig:
    """Load and validate the venues.yaml configuration file.

    Args:
        path: Path to the YAML config file.

    Returns:
        Validated AppConfig instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Copy venues.example.yaml to venues.yaml and customize it."
        )

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    return AppConfig(**data)

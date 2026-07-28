"""Load and validate hardware/model parameters with explicit provenance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


HERE = Path(__file__).resolve().parent
DEFAULT_REGISTRY = HERE / "hardware_parameters.json"
REQUIRED_FIELDS = {"value", "unit", "status", "source"}


def load_parameter_registry(path: Path = DEFAULT_REGISTRY) -> Dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    allowed = set(registry["policy"]["allowed_statuses"])
    parameters = registry.get("parameters", {})
    if not parameters:
        raise ValueError("Parameter registry is empty")
    for name, entry in parameters.items():
        missing = REQUIRED_FIELDS.difference(entry)
        if missing:
            raise ValueError(f"Parameter {name!r} is missing {sorted(missing)}")
        if entry["status"] not in allowed:
            raise ValueError(
                f"Parameter {name!r} has unsupported status {entry['status']!r}"
            )
        if not str(entry["source"]).strip():
            raise ValueError(f"Parameter {name!r} needs a non-empty source")
        if "range" in entry:
            low, high = entry["range"]
            if low > high:
                raise ValueError(f"Parameter {name!r} has a reversed range")
    return registry


def unresolved_parameters(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Return parameters that still need physical measurement or verification."""
    return {
        name: entry
        for name, entry in registry["parameters"].items()
        if entry["status"] in {
            "assumed",
            "extracted_unverified",
            "inferred",
            "datasheet",
        }
    }


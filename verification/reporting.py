"""Portable file records and JSON output for verification commands."""
from fractions import Fraction
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def display_path(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def file_record(path):
    path = Path(path).resolve()
    return {"path": display_path(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def serial(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, Path):
        return display_path(value)
    if isinstance(value, (tuple, list)):
        return [serial(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serial(item) for key, item in value.items()}
    return value


def write_report(path, report):
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serial(report), indent=2) + "\n")
    return display_path(path)

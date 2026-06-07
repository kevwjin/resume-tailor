from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from resume_tailor.models import Profile


class ProfileLoadError(ValueError):
    pass


def load_profile(path: Path) -> Profile:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProfileLoadError(f"Profile not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ProfileLoadError(f"Invalid YAML in {path}: {exc}") from exc

    if raw is None:
        raise ProfileLoadError(f"Profile is empty: {path}")

    try:
        return Profile.model_validate(raw)
    except ValidationError as exc:
        raise ProfileLoadError(str(exc)) from exc


def load_job(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Job description not found: {path}") from exc

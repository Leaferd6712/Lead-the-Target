"""Versioned atomic saves with backup recovery and safe legacy migration."""
import json
import os
import math
import shutil
import sys
from pathlib import Path


SCHEMA = 2
ROOT = Path(__file__).resolve().parent
SAVE_PATH = (Path(os.getenv("APPDATA", str(Path.home())))/"LeadTheTarget"/"progress.json"
             if getattr(sys, "frozen", False) else ROOT/"save.json")
DEFAULT_SETTINGS = {"volume": 0.4, "muted": False, "reduced_motion": False,
                    "large_text": False, "window": [1280, 800], "high_contrast": False}


def validate(data):
    if not isinstance(data, dict) or data.get("schema", 1) not in (1, 2):
        return {}
    stage, currency = data.get("stage", 0), data.get("currency", 40)
    levels = data.get("upgrades", {})
    if (type(stage) is not int or not 0 <= stage <= 7 or type(currency) is not int
            or not 0 <= currency <= 1000000 or not isinstance(levels, dict)):
        return {}
    from lessons import UPGRADES
    upgrades = {k: min(len(v[1]), max(0, levels.get(k, 0)))
                if type(levels.get(k, 0)) is int else 0 for k, v in UPGRADES.items()}
    learning = data.get("learning", {})
    learning = {str(k): v for k, v in learning.items()
                if isinstance(k, str) and isinstance(v, dict)} if isinstance(learning, dict) else {}
    def number(value, default, low, high):
        return max(low, min(high, value)) if type(value) in (int, float) and math.isfinite(value) else default
    gains = data.get("gains", [4, 0, 0, 0])
    gains = gains if isinstance(gains, list) and len(gains) == 4 else [4, 0, 0, 0]
    gains = [number(v, d, 0, h) for v, d, h in zip(gains, (4, 0, 0, 0), (16, 5, 2, 3))]
    settings = dict(DEFAULT_SETTINGS)
    raw = data.get("settings", {})
    if isinstance(raw, dict):
        for k in ("muted", "reduced_motion", "large_text", "high_contrast"):
            settings[k] = raw.get(k) is True
        settings["volume"] = number(raw.get("volume"), 0.4, 0, 1)
        size = raw.get("window")
        if isinstance(size, list) and len(size) == 2 and all(type(v) is int for v in size):
            settings["window"] = [int(number(size[0], 1280, 800, 3840)), int(number(size[1], 800, 600, 2160))]
    algorithm = data.get("algorithm", 0)
    return {"schema": SCHEMA, "stage": stage, "currency": currency, "upgrades": upgrades,
            "won": data.get("won") is True, "learning": learning,
            "algorithm": algorithm if type(algorithm) is int and 0 <= algorithm <= 4 else 0,
            "lead": number(data.get("lead"), 0.3, 0, 2), "gains": gains, "settings": settings,
            "completion": data.get("completion") if isinstance(data.get("completion"), dict) else {},
            "legacy": data.get("schema", 1) == 1}


def load_status(path=SAVE_PATH):
    for candidate in (path, path.with_suffix(path.suffix+".bak")):
        try:
            data = validate(json.loads(candidate.read_text(encoding="utf-8")))
            if data:
                note = "Recovered the backup save. Your original file is preserved." if candidate != path else ""
                if data.get("legacy"):
                    note = "Updated save format. Credits and upgrades kept; guided skills await demonstration."
                return data, note
        except (OSError, ValueError, TypeError):
            pass
    if path.exists():
        return {}, "Save could not be read. Use Reset campaign to start safely; the old file is preserved."
    return {}, ""


def load_progress(path=SAVE_PATH):
    return load_status(path)[0]


def save_progress(stage, currency, upgrades, won=False, path=SAVE_PATH, **extra):
    data = {"schema": SCHEMA, "stage": stage, "currency": currency,
            "upgrades": upgrades, "won": won, **extra}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            old = path.read_text(encoding="utf-8")
            try:
                valid_old = bool(validate(json.loads(old)))
            except (ValueError, TypeError):
                valid_old = False
            suffix = ".bak" if valid_old else ".unreadable"
            shutil.copy2(path, path.with_suffix(path.suffix+suffix))
        temporary = path.with_suffix(path.suffix+".tmp")
        temporary.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
        os.replace(temporary, path)
        return True
    except (OSError, ValueError, TypeError):
        return False

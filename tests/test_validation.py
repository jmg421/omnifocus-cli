from pathlib import Path
import json
from typer.testing import CliRunner
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLI_DIR = PROJECT_ROOT / "omni-cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

from utils.data_loading import load_and_prepare_omnifocus_data


def _write_json(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "export.json"
    p.write_text(json.dumps(data))
    return p


def test_load_valid_export(tmp_path):
    valid = {
        "tasks": [],
        "inboxTasks": [],
        "projects": {},
        "folders": {},
        "tags": {},
    }
    f = _write_json(tmp_path, valid)
    parsed = load_and_prepare_omnifocus_data(str(f))
    assert parsed  # not empty dict


def test_load_invalid_export(tmp_path):
    invalid = {
        "badKey": "oops"  # missing required fields
    }
    f = _write_json(tmp_path, invalid)
    parsed = load_and_prepare_omnifocus_data(str(f))
    assert parsed == {} 
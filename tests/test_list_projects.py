# Small helper to import the CLI when the repo isn’t installed as a package.
from pathlib import Path
import sys
import json
from typer.testing import CliRunner

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# Add <repo_root>/omni-cli to sys.path so `import ofcli` works regardless of
# the current working directory or installation state.
CLI_DIR = PROJECT_ROOT / "omni-cli"
if str(CLI_DIR) not in sys.path:
    sys.path.insert(0, str(CLI_DIR))

# Now we can safely import.
from ofcli import app, fetch_projects_from_json

runner = CliRunner()

def _create_sample_export(tmp_path: Path) -> Path:
    """Write a minimal OmniFocus export JSON with two projects."""
    sample = {
        "projects": {
            "proj1": {"id": "proj1", "name": "Project One"},
            "proj2": {"id": "proj2", "name": "Project Two"},
        },
        "tasks": [],
        "folders": {}
    }
    file_path = tmp_path / "sample_of_export.json"
    file_path.write_text(json.dumps(sample))
    return file_path


def test_fetch_projects_from_json(tmp_path):
    sample_file = _create_sample_export(tmp_path)
    projects_map = fetch_projects_from_json(str(sample_file))
    assert list(projects_map.keys()) == ["proj1", "proj2"]
    assert projects_map["proj1"]["name"] == "Project One"


def test_cli_list_projects(tmp_path):
    sample_file = _create_sample_export(tmp_path)
    result = runner.invoke(app, ["list-projects", "--file", str(sample_file)])
    assert result.exit_code == 0
    assert "Project One" in result.stdout
    assert "proj1" in result.stdout 
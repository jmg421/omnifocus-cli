import os
from types import SimpleNamespace

import pytest

import importlib
import sys

MODULE_PATH = "omnifocus_api.apple_script_client"


def _patch_subprocess(monkeypatch, expected_assertion):
    """Patch subprocess.run to intercept the command list and simulate success."""

    def _fake_run(cmd, capture_output=True, text=True, check=False):  # noqa: D401
        # Delegate assertion to caller-provided function so each test can verify the cmd
        expected_assertion(cmd)
        return SimpleNamespace(returncode=0, stdout="OK", stderr="")

    monkeypatch.setattr("subprocess.run", _fake_run)


def _reload_client():
    """Reload module to ensure it picks up current env vars within the test."""
    if MODULE_PATH in sys.modules:  # pragma: no cover
        importlib.reload(sys.modules[MODULE_PATH])
    else:
        importlib.import_module(MODULE_PATH)
    return sys.modules[MODULE_PATH]


@pytest.mark.usefixtures("monkeypatch")
def test_default_path_uses_osascript(monkeypatch):
    # Ensure flag is not set
    os.environ.pop("OF_RUNNER_V2", None)

    def _assert_cmd(cmd):
        assert cmd[0] == "osascript" and "-l" not in cmd, cmd  # default path

    _patch_subprocess(monkeypatch, _assert_cmd)

    client = _reload_client()
    out = client.execute_omnifocus_applescript('return "OK"')
    assert out == "OK"


@pytest.mark.usefixtures("monkeypatch")
def test_runner_path(monkeypatch):
    os.environ["OF_RUNNER_V2"] = "1"

    def _assert_cmd(cmd):
        # expect python3 runner invocation
        assert cmd[0] == "python3" and "--script" in cmd, cmd

    _patch_subprocess(monkeypatch, _assert_cmd)

    client = _reload_client()
    out = client.execute_omnifocus_applescript('return "OK"')
    assert out == "OK" 
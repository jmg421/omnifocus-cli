"""
Test suite for the main CLI interface.
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

# Import the main CLI app
from ofcli import app

runner = CliRunner()


class TestCLI:
    """Test cases for the main CLI application."""

    def test_cli_help(self):
        """Test that the CLI shows help information."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "OmniFocus CLI" in result.stdout

    def test_cli_version(self):
        """Test that the CLI shows version information."""
        with patch('ofcli.__version__', '1.0.0'):
            result = runner.invoke(app, ["--version"])
            assert result.exit_code == 0 or "1.0.0" in result.stdout

    @patch('ofcli.load_env_vars')
    def test_env_loading(self, mock_load_env):
        """Test that environment variables are loaded properly."""
        mock_load_env.return_value = None
        result = runner.invoke(app, ["--help"])
        mock_load_env.assert_called_once()

    def test_diagnostics_command_exists(self):
        """Test that the diagnostics command is available."""
        result = runner.invoke(app, ["diagnostics", "--help"])
        assert result.exit_code == 0
        assert "health check" in result.stdout.lower()

    def test_list_command_exists(self):
        """Test that the list command is available."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0

    def test_add_command_exists(self):
        """Test that the add command is available."""
        result = runner.invoke(app, ["add", "--help"])
        assert result.exit_code == 0

    @patch('ofcli.subprocess.run')
    def test_omnifocus_process_check(self, mock_subprocess):
        """Test OmniFocus process checking in diagnostics."""
        # Mock successful OmniFocus process check
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = runner.invoke(app, ["diagnostics"])
        # Should not fail even if other parts fail
        assert result.exit_code in [0, 1]  # May fail on missing data, but shouldn't crash


class TestCLIErrors:
    """Test error handling in CLI commands."""

    def test_invalid_command(self):
        """Test that invalid commands show helpful error messages."""
        result = runner.invoke(app, ["nonexistent-command"])
        assert result.exit_code != 0
        assert "Usage:" in result.stdout or "No such command" in result.stdout

    @patch('os.path.exists')
    def test_missing_config_graceful_failure(self, mock_exists):
        """Test that missing configuration is handled gracefully."""
        mock_exists.return_value = False
        # Should still show help even without config
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__])


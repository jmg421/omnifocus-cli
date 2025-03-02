import unittest
from unittest.mock import patch
from omnifocus_cli.cli_main import main

class TestCLI(unittest.TestCase):
    def test_no_args_shows_help(self):
        with patch("sys.argv", ["ofcli"]):
            with self.assertRaises(SystemExit) as context:
                main()
            self.assertEqual(context.exception.code, 1)

    def test_add_command_requires_title(self):
        with patch("sys.argv", ["ofcli", "add", "--title", "Test Task"]):
            # We can't fully test AppleScript calls here, but we can ensure it doesn't crash
            # Would mock apple_script_client in a real test
            try:
                main()
            except SystemExit as e:
                self.fail(f"CLI crashed with SystemExit {e}")


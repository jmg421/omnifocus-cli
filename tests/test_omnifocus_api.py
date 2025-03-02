import unittest
from unittest.mock import patch
from omnifocus_cli.omnifocus_api.apple_script_client import fetch_tasks

class TestAppleScriptClient(unittest.TestCase):
    @patch("subprocess.run")
    def test_fetch_tasks_no_project(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "taskID1||Task1||Note1||false||2025-03-15\n"
        tasks = fetch_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].name, "Task1")


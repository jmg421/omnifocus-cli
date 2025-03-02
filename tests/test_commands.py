import unittest
from omnifocus_cli.commands.add_command import handle_add

class TestAddCommand(unittest.TestCase):
    def test_handle_add_minimal(self):
        # Mock the arguments object
        class Args:
            title = "Test Task"
            project = None
            note = None
            due = None

        # In a real test, you'd mock apple_script_client.create_task_via_applescript
        handle_add(Args())
        # Just ensure no exceptions
        self.assertTrue(True)


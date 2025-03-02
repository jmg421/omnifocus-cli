import unittest
from unittest.mock import patch
from omnifocus_cli.ai_integration.ai_utils import get_priority_suggestions

class TestAIIntegration(unittest.TestCase):
    @patch("omnifocus_cli.ai_integration.ai_utils.openai_completion")
    def test_get_priority_suggestions(self, mock_completion):
        mock_completion.return_value = "1. Task A\n2. Task B\n3. Task C"
        tasks = []
        result = get_priority_suggestions(tasks)
        self.assertIn("1. Task A", result[0])


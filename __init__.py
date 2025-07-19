"""
OmniFocus CLI: Command-line interface for OmniFocus with AI integration and Apple ecosystem support.

A powerful CLI tool that provides seamless integration between OmniFocus and AI services,
with comprehensive Apple ecosystem support including Calendar integration via EventKit.
"""

__version__ = "1.0.0"
__author__ = "OmniFocus CLI Team"
__email__ = "contact@omnifocus-cli.com"

# Import the main CLI app for entry point
from .ofcli import app

__all__ = ["app", "__version__"]


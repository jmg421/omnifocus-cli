from setuptools import setup, find_packages
import os

# Read the README file for long description
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
try:
    with open(readme_path, "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "OmniFocus CLI - Command-line interface for OmniFocus with AI integration"

# Read requirements from requirements.txt
requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
try:
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = []
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove inline comments and version constraints for basic deps
                req = line.split("#")[0].strip()
                if req:
                    requirements.append(req)
except FileNotFoundError:
    requirements = [
        "typer[all]>=0.9.0",
        "rich>=13.5.2",
        "openai>=1.0.0",
        "anthropic>=0.3.1",
        "requests>=2.28.0",
        "python-dotenv>=1.0.0",
        "thefuzz>=0.19.0",
        "python-dateutil>=2.8.2",
        "dateparser>=1.1.0",
        "pydantic>=2.0.0",
        "loguru>=0.6.0",
        "appscript>=1.2.5",
        "pyobjc-framework-EventKit>=9.0",
        "pyobjc-core>=9.0",
        "icalendar>=5.0.0",
        "recurring-ical-events>=2.1.0",
        "cryptography>=41.0.0",
    ]

setup(
    name="ofcli",
    version="1.0.0",
    author="OmniFocus CLI Team",
    author_email="contact@omnifocus-cli.com",
    description="OmniFocus CLI - Command-line interface for OmniFocus with AI integration and Apple ecosystem support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jmg421/omni-cli",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Environment :: Console",
        "Natural Language :: English",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.1.3",
            "pytest-mock>=3.10.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
        ],
        "docs": [
            "markdown2>=2.4.0",
            "pypandoc>=1.11",
        ],
    },
    entry_points={
        "console_scripts": [
            "ofcli=ofcli.ofcli:app",
        ],
    },
    keywords="omnifocus productivity task-management cli apple macos ai automation",
    project_urls={
        "Bug Reports": "https://github.com/jmg421/omni-cli/issues",
        "Source": "https://github.com/jmg421/omni-cli",
        "Documentation": "https://github.com/jmg421/omni-cli#readme",
    },
    zip_safe=False,  # Required for including data files
) 